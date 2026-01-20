"""
Motor Control Simulation - Modern Dark Theme
Controls 64 servo motors based on camera body tracking
ESP32-S3 hardware support with live camera feed and firmware flashing
"""

import tkinter as tk
from tkinter import ttk, messagebox
import time
import math
import threading
import serial
import serial.tools.list_ports
import cv2
from PIL import Image, ImageTk
import numpy as np
import subprocess
import os
import sys
from PIL import Image, ImageTk

# Try to import MediaPipe for body tracking
MEDIAPIPE_AVAILABLE = False
mp_pose = None
mp_drawing = None

try:
    import mediapipe as mp
    # Try standard access
    mp_pose = mp.solutions.pose
    mp_drawing = mp.solutions.drawing_utils
    MEDIAPIPE_AVAILABLE = True
    print("[OK] MediaPipe loaded via standard method")
except (ImportError, AttributeError):
    try:
        print("[WARN] Standard MediaPipe import failed, trying fallback...")
        import importlib
        mp_pose = importlib.import_module("mediapipe.python.solutions.pose")
        mp_drawing = importlib.import_module("mediapipe.python.solutions.drawing_utils")
        MEDIAPIPE_AVAILABLE = True
        print("[OK] MediaPipe loaded via fallback")
    except Exception as e:
        print(f"[ERROR] MediaPipe completely failed: {e}")
        MEDIAPIPE_AVAILABLE = False

try:
    from packages.mirror_core.simulation.mock_serial import get_virtual_device_instance
except ImportError:
    get_virtual_device_instance = None

# ============== MODERN DARK THEME ==============
COLORS = {
    'bg_dark': '#1a1a2e',
    'bg_medium': '#16213e',
    'bg_light': '#0f3460',
    'accent': '#e94560',
    'accent_secondary': '#00d4ff',
    'text_primary': '#ffffff',
    'text_secondary': '#a0a0a0',
    'success': '#00ff88',
    'warning': '#ffaa00',
    'error': '#ff4444',
    'motor_body': '#2d2d2d',
    'motor_horn': '#00d4ff',
    'motor_active': '#00ff88',
    'motor_neutral': '#666666',
    'grid_line': '#333355',
}

# ESP32-S3 USB VID/PIDs (common chips)
ESP32_S3_IDENTIFIERS = [
    (0x303A, 0x1001),  # ESP32-S3 native USB
    (0x303A, 0x0002),  # ESP32-S3 JTAG
    (0x10C4, 0xEA60),  # Silicon Labs CP210x
    (0x1A86, 0x7523),  # CH340
    (0x1A86, 0x55D4),  # CH9102
    (0x0403, 0x6001),  # FTDI FT232
    (0x0403, 0x6015),  # FTDI FT231X
]

# Firmware paths (relative to this file)
FIRMWARE_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'firmware', 'esp32')

# ESP32 (regular) firmware
FIRMWARE_BIN_ESP32 = os.path.join(FIRMWARE_DIR, '.pio', 'build', 'esp32', 'firmware.bin')
BOOTLOADER_BIN_ESP32 = os.path.join(FIRMWARE_DIR, '.pio', 'build', 'esp32', 'bootloader.bin')
PARTITIONS_BIN_ESP32 = os.path.join(FIRMWARE_DIR, '.pio', 'build', 'esp32', 'partitions.bin')

# ESP32-S3 firmware
FIRMWARE_BIN_ESP32S3 = os.path.join(FIRMWARE_DIR, '.pio', 'build', 'esp32s3', 'firmware.bin')
BOOTLOADER_BIN_ESP32S3 = os.path.join(FIRMWARE_DIR, '.pio', 'build', 'esp32s3', 'bootloader.bin')
PARTITIONS_BIN_ESP32S3 = os.path.join(FIRMWARE_DIR, '.pio', 'build', 'esp32s3', 'partitions.bin')

# Default to ESP32 (regular) - change to ESP32S3 if needed
FIRMWARE_BIN = FIRMWARE_BIN_ESP32
BOOTLOADER_BIN = BOOTLOADER_BIN_ESP32
PARTITIONS_BIN = PARTITIONS_BIN_ESP32



class BodySegmenter:
    """
    Optimized body segmentation from LED Branch (Secret Sauce)
    - Clean silhouette extraction
    - Temporal smoothing (reduces flicker)
    - Hole filling (solid body)
    - Edge smoothing
    """
    def __init__(self):
        # Local imports to avoid global dependency issues if not used
        import mediapipe as mp
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision as mp_vision
        from pathlib import Path
        import urllib.request
        import ssl
        
        # Ensure data dir exists
        model_path = Path("data/selfie_segmenter.tflite")
        model_path.parent.mkdir(exist_ok=True)
        
        if not model_path.exists():
            print("Downloading segmentation model...")
            url = "https://storage.googleapis.com/mediapipe-models/image_segmenter/selfie_segmenter/float16/latest/selfie_segmenter.tflite"
            # Bypass SSL for robust download
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            with urllib.request.urlopen(url, context=ctx) as u, open(model_path, 'wb') as f:
                f.write(u.read())
            print("Model downloaded")
        
        base_options = mp_python.BaseOptions(model_asset_path=str(model_path))
        options = mp_vision.ImageSegmenterOptions(
            base_options=base_options,
            running_mode=mp_vision.RunningMode.VIDEO,
            output_category_mask=True
        )
        self.segmenter = mp_vision.ImageSegmenter.create_from_options(options)
        self.frame_count = 0
        
        # Temporal smoothing buffers
        self.mask_buffer = None
        self.smoothing = 0.10  # LOWER = more snappy/crisp, higher = smoother/more lag
        
        # Morphology kernels (pre-computed for speed)
        self.kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        self.kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        self.kernel_dilate = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        
    def get_body_mask(self, frame):
        """
        Extract clean body silhouette with performance optimizations
        Returns binary mask (0 or 255)
        """
        self.frame_count += 1
        h, w = frame.shape[:2]
        
        # PERFORMANCE: Processing at lower resolution significantly reduces lag
        # model usually takes 256x256, so processing at that size is fine
        proc_w, proc_h = 256, 144 # 16:9 ratio approximately
        small_rgb = cv2.resize(frame, (proc_w, proc_h), interpolation=cv2.INTER_LINEAR)
        small_rgb = cv2.cvtColor(small_rgb, cv2.COLOR_BGR2RGB)
        
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=small_rgb)
        
        # Run segmentation
        timestamp_ms = int(self.frame_count * 33)
        result = self.segmenter.segment_for_video(mp_image, timestamp_ms)
        
        if result.category_mask is None:
            return np.zeros((h, w), dtype=np.uint8)
        
        # Get raw mask at processing resolution
        mask = result.category_mask.numpy_view()
        mask = (mask > 0).astype(np.float32)
        
        # Temporal smoothing at low res (faster)
        if self.mask_buffer is None:
            self.mask_buffer = mask.copy()
        else:
            self.mask_buffer = self.smoothing * self.mask_buffer + (1.0 - self.smoothing) * mask
        
        binary = (self.mask_buffer > 0.4).astype(np.uint8) * 255
        
        # Faster Morphology at lower resolution
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, self.kernel_close)
        
        # Solifidy (Fast at low res)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            largest = max(contours, key=cv2.contourArea)
            binary = np.zeros_like(binary)
            cv2.drawContours(binary, [largest], -1, 255, cv2.FILLED)
        
        binary = cv2.dilate(binary, self.kernel_dilate, iterations=1)
        
        # Upscale mask back to original size for display/matching
        return cv2.resize(binary, (w, h), interpolation=cv2.INTER_NEAREST)

    def close(self):
        if hasattr(self, 'segmenter'):
            self.segmenter.close()


class ModernButton(tk.Canvas):
    """Modern rounded button with hover effects"""
    def __init__(self, parent, text, command=None, width=120, height=36, 
                 bg=None, fg=None, **kwargs):
        if bg is None:
            bg = COLORS['accent']
        if fg is None:
            fg = COLORS['text_primary']
        super().__init__(parent, width=width, height=height, 
                        bg=COLORS['bg_dark'], highlightthickness=0, **kwargs)
        self.command = command
        self.text = text
        self.default_bg = bg
        self.current_bg = bg
        self.fg = fg
        self.width = width
        self.height = height
        self.enabled = True
        
        self._draw()
        self.bind('<Enter>', self._on_enter)
        self.bind('<Leave>', self._on_leave)
        self.bind('<Button-1>', self._on_click)
    
    def _draw(self):
        self.delete('all')
        r = 8
        x1, y1 = 2, 2
        x2, y2 = self.width - 2, self.height - 2
        
        self.create_arc(x1, y1, x1 + 2*r, y1 + 2*r, start=90, extent=90, 
                       fill=self.current_bg, outline='')
        self.create_arc(x2 - 2*r, y1, x2, y1 + 2*r, start=0, extent=90, 
                       fill=self.current_bg, outline='')
        self.create_arc(x1, y2 - 2*r, x1 + 2*r, y2, start=180, extent=90, 
                       fill=self.current_bg, outline='')
        self.create_arc(x2 - 2*r, y2 - 2*r, x2, y2, start=270, extent=90, 
                       fill=self.current_bg, outline='')
        self.create_rectangle(x1 + r, y1, x2 - r, y2, fill=self.current_bg, outline='')
        self.create_rectangle(x1, y1 + r, x2, y2 - r, fill=self.current_bg, outline='')
        
        self.create_text(self.width/2, self.height/2, text=self.text, 
                        fill=self.fg, font=('Segoe UI', 10, 'bold'))
    
    def _on_enter(self, e):
        if self.enabled:
            self.current_bg = self._lighten_color(self.default_bg, 0.2)
            self._draw()
    
    def _on_leave(self, e):
        self.current_bg = self.default_bg
        self._draw()
    
    def _on_click(self, e):
        if self.enabled and self.command:
            self.command()
    
    def _lighten_color(self, hex_color, factor):
        hex_color = hex_color.lstrip('#')
        r, g, b = int(hex_color[:2], 16), int(hex_color[2:4], 16), int(hex_color[4:], 16)
        r = min(255, int(r + (255 - r) * factor))
        g = min(255, int(g + (255 - g) * factor))
        b = min(255, int(b + (255 - b) * factor))
        return f'#{r:02x}{g:02x}{b:02x}'
    
    def set_enabled(self, enabled):
        self.enabled = enabled
        if not enabled:
            self.current_bg = COLORS['motor_neutral']
        else:
            self.current_bg = self.default_bg
        self._draw()
    
    def set_text(self, text):
        self.text = text
        self._draw()


class MotorVisualizer(tk.Canvas):
    """Beautiful 8x8 motor grid visualization - optimized to prevent flickering"""
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=COLORS['bg_dark'], highlightthickness=0, **kwargs)
        self.motor_angles = [90] * 64
        self.motor_active = [False] * 64
        self.cell_size = 55
        self._items_created = False
        self._motor_items = {}  # Cache canvas item IDs
        self.bind('<Configure>', self._on_resize)
    
    def _on_resize(self, event):
        margin = 60
        available_w = event.width - margin * 2
        available_h = event.height - margin * 2
        self.cell_size = min(available_w // 8, available_h // 8)
        self._items_created = False  # Force redraw on resize
        self.draw_motors()
    
    def update_angles(self, angles):
        """Update motor angles and redraw"""
        if len(angles) >= 64:
            for i in range(64):
                new_angle = angles[i]
                self.motor_active[i] = abs(new_angle - 90) > 5
                self.motor_angles[i] = new_angle
        self._update_motor_positions()
    
    def _update_motor_positions(self):
        """Update only the horn positions without recreating items"""
        if not self._items_created:
            self.draw_motors()
            return
        
        w = self.winfo_width()
        h = self.winfo_height()
        
        if w < 100 or h < 100:
            return
        
        margin_x = 40
        margin_y = 40
        grid_w = w - margin_x * 2
        grid_h = h - margin_y * 2
        cell_w = grid_w / 8
        cell_h = grid_h / 8
        size = cell_w * 0.38
        r = size * 0.6
        horn_length = r * 1.3
        
        for i in range(64):
            row = i // 8
            col = i % 8
            
            cx = margin_x + col * cell_w + cell_w/2
            cy = margin_y + row * cell_h + cell_h/2
            
            angle = self.motor_angles[i]
            active = self.motor_active[i]
            
            rad = math.radians(180 - angle)
            end_x = cx + horn_length * math.cos(rad)
            end_y = cy - horn_length * math.sin(rad)
            
            # Update colors and positions
            body_color = COLORS['motor_active'] if active else COLORS['motor_body']
            outline_color = COLORS['accent_secondary'] if active else COLORS['motor_neutral']
            horn_color = COLORS['motor_horn'] if active else '#888888'
            
            if f'body_{i}' in self._motor_items:
                self.itemconfig(self._motor_items[f'body_{i}'], fill=body_color, outline=outline_color)
                self.itemconfig(self._motor_items[f'inner_{i}'], outline=outline_color)
                self.coords(self._motor_items[f'horn_{i}'], cx, cy, end_x, end_y)
                self.itemconfig(self._motor_items[f'horn_{i}'], fill=horn_color)
                
                tip_r = 3
                self.coords(self._motor_items[f'tip_{i}'], end_x - tip_r, end_y - tip_r, end_x + tip_r, end_y + tip_r)
                self.itemconfig(self._motor_items[f'tip_{i}'], fill=horn_color)
                
                # Update angle text
                if active:
                    self.itemconfig(self._motor_items[f'angle_{i}'], text=f"{int(angle)}°", 
                                   fill=COLORS['accent_secondary'])
                else:
                    self.itemconfig(self._motor_items[f'angle_{i}'], text="")
    
    def draw_motors(self):
        """Draw the 8x8 motor grid - creates items once"""
        self.delete('all')
        self._motor_items = {}
        
        w = self.winfo_width()
        h = self.winfo_height()
        
        if w < 100 or h < 100:
            return
        
        margin_x = 40
        margin_y = 40
        grid_w = w - margin_x * 2
        grid_h = h - margin_y * 2
        cell_w = grid_w / 8
        cell_h = grid_h / 8
        
        # Draw title
        self.create_text(w/2, 15, text="🔧 64 SERVO MOTORS", 
                        fill=COLORS['text_primary'], font=('Segoe UI', 12, 'bold'))
        
        # Draw column headers
        for col in range(8):
            x = margin_x + col * cell_w + cell_w/2
            self.create_text(x, margin_y - 12, text=str(col + 1), 
                           fill=COLORS['text_secondary'], font=('Segoe UI', 8))
        
        # Draw row headers
        row_labels = 'ABCDEFGH'
        for row in range(8):
            y = margin_y + row * cell_h + cell_h/2
            self.create_text(margin_x - 15, y, text=row_labels[row], 
                           fill=COLORS['text_secondary'], font=('Segoe UI', 8))
        
        # Draw motors with cached item IDs
        size = cell_w * 0.38
        for i in range(64):
            row = i // 8
            col = i % 8
            
            cx = margin_x + col * cell_w + cell_w/2
            cy = margin_y + row * cell_h + cell_h/2
            
            self._create_servo(cx, cy, i, self.motor_angles[i], self.motor_active[i], size)
        
        self._items_created = True
    
    def _create_servo(self, cx, cy, index, angle, active, size):
        """Create a single SG90-style servo motor with cached items"""
        body_color = COLORS['motor_active'] if active else COLORS['motor_body']
        outline_color = COLORS['accent_secondary'] if active else COLORS['motor_neutral']
        
        r = size * 0.6
        
        # Body
        self._motor_items[f'body_{index}'] = self.create_oval(
            cx - r, cy - r, cx + r, cy + r, 
            fill=body_color, outline=outline_color, width=2
        )
        
        # Inner circle
        inner_r = r * 0.4
        self._motor_items[f'inner_{index}'] = self.create_oval(
            cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r,
            fill=COLORS['bg_light'], outline=outline_color, width=1
        )
        
        # Horn
        horn_length = r * 1.3
        rad = math.radians(180 - angle)
        end_x = cx + horn_length * math.cos(rad)
        end_y = cy - horn_length * math.sin(rad)
        
        horn_color = COLORS['motor_horn'] if active else '#888888'
        
        self._motor_items[f'horn_{index}'] = self.create_line(
            cx, cy, end_x, end_y, fill=horn_color, width=2, capstyle='round'
        )
        
        # Tip
        tip_r = 3
        self._motor_items[f'tip_{index}'] = self.create_oval(
            end_x - tip_r, end_y - tip_r, end_x + tip_r, end_y + tip_r,
            fill=horn_color, outline=''
        )
        
        # Angle text (empty initially if neutral)
        self._motor_items[f'angle_{index}'] = self.create_text(
            cx, cy + r + 10, text=f"{int(angle)}°" if active else "", 
            fill=COLORS['accent_secondary'], font=('Segoe UI', 7, 'bold')
        )


class CameraPanel(tk.Frame):
    """Live camera feed panel with body tracking"""
    def __init__(self, parent, on_angle_change=None, **kwargs):
        super().__init__(parent, bg=COLORS['bg_dark'], **kwargs)
        self.on_angle_change = on_angle_change
        self.cap = None
        self.running = False
        self.current_camera = None
        self.body_segmenter = None
        self.body_x = 0.5  # Normalized body position (0-1)
        self.body_detected = False
        self._create_widgets()
        self._detect_cameras()
        self.after(300, self._auto_start_camera)

    def _auto_start_camera(self):
        """Auto-start camera 1 if available, else camera 0"""
        cameras = self.camera_combo['values']
        if cameras and isinstance(cameras, (list, tuple)):
            if len(cameras) > 1:
                self.camera_combo.set(cameras[1])
            else:
                self.camera_combo.set(cameras[0])
        self._start_camera()
    
    def _create_widgets(self):
        # Header with camera selection
        header = tk.Frame(self, bg=COLORS['bg_medium'])
        header.pack(fill='x', padx=5, pady=5)
        
        tk.Label(header, text="📹 LIVE CAMERA", bg=COLORS['bg_medium'], 
                fg=COLORS['text_primary'], font=('Segoe UI', 11, 'bold')).pack(side='left', padx=5)
        
        # Camera dropdown
        cam_frame = tk.Frame(header, bg=COLORS['bg_medium'])
        cam_frame.pack(side='right', padx=5)
        
        tk.Label(cam_frame, text="Camera:", bg=COLORS['bg_medium'], 
                fg=COLORS['text_secondary'], font=('Segoe UI', 9)).pack(side='left')
        
        self.camera_var = tk.StringVar()
        self.camera_combo = ttk.Combobox(cam_frame, textvariable=self.camera_var, 
                                         width=25, state='readonly')
        self.camera_combo.pack(side='left', padx=5)
        self.camera_combo.bind('<<ComboboxSelected>>', self._on_camera_change)
        
        # Refresh cameras button
        refresh_btn = tk.Button(cam_frame, text="⟳", command=self._detect_cameras,
                               bg=COLORS['bg_light'], fg=COLORS['text_primary'],
                               font=('Segoe UI', 10), bd=0, padx=6, pady=2)
        refresh_btn.pack(side='left', padx=2)
        
        # Video display canvas
        self.video_canvas = tk.Canvas(self, bg='#000000', highlightthickness=0)
        self.video_canvas.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Info overlay frame
        info_frame = tk.Frame(self, bg=COLORS['bg_medium'])
        info_frame.pack(fill='x', padx=5, pady=(0, 5))
        
        self.tracking_status = tk.Label(info_frame, text="● Tracking: OFF", 
                                        bg=COLORS['bg_medium'], fg=COLORS['error'],
                                        font=('Segoe UI', 9))
        self.tracking_status.pack(side='left', padx=10)
        
        self.position_label = tk.Label(info_frame, text="Position: --", 
                                       bg=COLORS['bg_medium'], fg=COLORS['text_secondary'],
                                       font=('Segoe UI', 9))
        self.position_label.pack(side='left', padx=10)
        
        # Start/Stop button
        self.start_btn = ModernButton(info_frame, text="▶ Start", 
                                      command=self._toggle_camera,
                                      width=80, height=28,
                                      bg=COLORS['success'])
        self.start_btn.pack(side='right', padx=5)
    
    def _detect_cameras(self):
        """Detect available cameras"""
        cameras = []
        
        # Test camera indices 0-9
        for i in range(10):
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    # Get camera name if possible
                    cameras.append(f"Camera {i}")
                cap.release()
        
        if cameras:
            self.camera_combo['values'] = cameras
            # Default to camera 1 if available (external), else 0
            if len(cameras) > 1:
                self.camera_combo.set(cameras[1])
            else:
                self.camera_combo.set(cameras[0])
        else:
            self.camera_combo['values'] = ["No cameras found"]
            self.camera_combo.set("No cameras found")
    
    def _on_camera_change(self, event=None):
        """Handle camera selection change"""
        if self.running:
            self._stop_camera()
            self._start_camera()
    
    def _toggle_camera(self):
        if self.running:
            self._stop_camera()
        else:
            self._start_camera()
    
    def _start_camera(self):
        """Start camera capture"""
        cam_str = self.camera_var.get()
        if "No cameras" in cam_str:
            messagebox.showwarning("No Camera", "No cameras detected!")
            return
        
        # Extract camera index
        try:
            cam_idx = int(cam_str.split()[-1])
        except:
            cam_idx = 0
        
        # Try to open camera with backends if needed
        self.cap = cv2.VideoCapture(cam_idx, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(cam_idx) # Default backend
            
        if not self.cap.isOpened():
            print(f"❌ Failed to open camera {cam_idx}")
            messagebox.showerror("Camera Error", f"Failed to open camera {cam_idx}")
            return
        
        # Set resolution
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        
        print(f"📸 Camera {cam_idx} opened successfully")
        
        # Initialize BodySegmenter (The Secret Sauce)
        try:
            print("⏳ Initializing BodySegmenter...")
            self.body_segmenter = BodySegmenter()
            print("✅ BodySegmenter initialized")
        except Exception as e:
            print(f"❌ BodySegmenter failed: {e}")
            import traceback
            traceback.print_exc()
            self.body_segmenter = None
        
        self.running = True
        self.start_btn.text = "⏹ Stop"
        self.start_btn.default_bg = COLORS['error']
        self.start_btn.current_bg = COLORS['error']
        self.start_btn._draw()
        
        # Start capture thread
        print("🧵 Starting capture thread...")
        threading.Thread(target=self._capture_loop, daemon=True).start()
    
    def _stop_camera(self):
        """Stop camera capture"""
        self.running = False
        
        if self.cap:
            self.cap.release()
            self.cap = None
        
        if self.body_segmenter:
            self.body_segmenter.close()
            self.body_segmenter = None
        
        self.start_btn.text = "▶ Start"
        self.start_btn.default_bg = COLORS['success']
        self.start_btn.current_bg = COLORS['success']
        self.start_btn._draw()
        
        self.tracking_status.config(text="● Tracking: OFF", fg=COLORS['error'])
        self.position_label.config(text="Position: --")
        
        # Clear canvas
        self.video_canvas.delete('all')
        self.video_canvas.create_text(
            self.video_canvas.winfo_width() // 2,
            self.video_canvas.winfo_height() // 2,
            text="Camera Stopped",
            fill=COLORS['text_secondary'],
            font=('Segoe UI', 14)
        )
    
    def _capture_loop(self):
        """Main camera capture loop - Powered by BodySegmenter (New API)"""
        frame_count = 0
        while self.running and self.cap:
            try:
                ret, frame = self.cap.read()
                if not ret or frame is None:
                    frame_count += 1
                    continue
                
                frame_count += 1
                
                # Flip for mirror effect
                frame = cv2.flip(frame, 1)
                h, w = frame.shape[:2]
                
                # Process with BodySegmenter (Robust)
                self.body_detected = False
                h, w = frame.shape[:2]
                
                if self.body_segmenter:
                    # Get robust binary mask (0 or 255)
                    seg_mask = self.body_segmenter.get_body_mask(frame)
                    
                    # Check if body present (> 0.5% of pixels)
                    # seg_mask is 0 or 255.
                    if np.sum(seg_mask) > (w * h * 0.005 * 255):
                        self.body_detected = True
                else:
                    seg_mask = np.zeros((h, w), dtype=np.uint8)
                    self.body_detected = False

                if self.body_detected:
                     # Resize mask to 8x8 for the servo grid
                     # Use INTER_AREA for better downsampling (averaging) - prevents flickering
                     mask_8x8 = cv2.resize(seg_mask, (8, 8), interpolation=cv2.INTER_AREA)
                     
                     # Create 64-element angle array directly from mask
                     # Human (mask > 50) -> 180 degrees (Active)
                     # Background -> 0 degrees (Inactive)
                     angles = []
                     for row in range(8):
                         for col in range(8):
                             val = mask_8x8[row, col]
                             angle = 180 if val > 50 else 0
                             angles.append(angle)
                     
                     # Send directly to motors
                     if self.on_angle_change:
                         self.on_angle_change(angles)
                         
                     # VISUALIZATION: Optimized lower-res visualization
                     # Do tinting at 320x240 for speed
                     v_h, v_w = 240, 320
                     small_frame = cv2.resize(frame, (v_w, v_h), interpolation=cv2.INTER_LINEAR)
                     small_mask = cv2.resize(seg_mask, (v_w, v_h), interpolation=cv2.INTER_NEAREST)
                     
                     overlay = small_frame.copy()
                     overlay[small_mask == 0] = (255, 0, 0) # Blue
                     overlay[small_mask == 255] = (0, 255, 0) # Green
                     
                     blended = cv2.addWeighted(overlay, 0.4, small_frame, 0.6, 0)
                     frame = cv2.resize(blended, (w, h), interpolation=cv2.INTER_LINEAR)
                     
                     # Draw 8x8 Grid overlay
                     h, w = frame.shape[:2]
                     step_x = w / 8
                     step_y = h / 8
                     for r in range(8):
                         for c in range(8):
                             if mask_8x8[r, c] > 50:
                                 # Draw active grid cell outline in Green
                                 x1 = int(c * step_x)
                                 y1 = int(r * step_y)
                                 x2 = int((c + 1) * step_x)
                                 y2 = int((r + 1) * step_y)
                                 cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 1)
                     
                     # Update body_x for legacy
                     # Calculate center X
                     contours, _ = cv2.findContours(seg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                     if contours:
                         largest = max(contours, key=cv2.contourArea)
                         x, y, bw, bh = cv2.boundingRect(largest)
                         self.body_x = (x + bw/2) / w
                
                # Draw tracking indicator (Simple text only)
                if self.body_detected:
                    cv2.putText(frame, "BODY DETECTED", (10, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                # Only update labels every 10 frames to save UI thread
                if frame_count % 10 == 0:
                    self._update_tracking_ui()
                
                self._update_canvas(frame)
            
            except Exception as e:
                print(f"Capture error: {e}")
            
            time.sleep(0.033)
            

    
    def _update_canvas(self, frame):
        """Update canvas with new frame (optimized)"""
        try:
            # Get canvas size
            canvas_w = self.video_canvas.winfo_width()
            canvas_h = self.video_canvas.winfo_height()
            
            if canvas_w < 10 or canvas_h < 10:
                return
            
            # Resize frame to fit canvas
            frame_h, frame_w = frame.shape[:2]
            scale = min(canvas_w / frame_w, canvas_h / frame_h)
            new_w = int(frame_w * scale)
            new_h = int(frame_h * scale)
            
            # Using INTER_NEAREST for display resize is much faster
            resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_NEAREST)
            img = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
            im = Image.fromarray(img)
            imgtk = ImageTk.PhotoImage(image=im)
            
            if not hasattr(self, '_canvas_img_id'):
                self._canvas_img_id = self.video_canvas.create_image(
                    canvas_w // 2, canvas_h // 2, image=imgtk, anchor='center')
                self._canvas_imgtk = imgtk
            else:
                self.video_canvas.itemconfig(self._canvas_img_id, image=imgtk)
                self._canvas_imgtk = imgtk
        except Exception as e:
            print(f"Canvas update error: {e}")
    
    def _update_tracking_ui(self):
        """Update tracking status labels"""
        try:
            if self.body_detected:
                self.tracking_status.config(text="● Tracking: ON", fg=COLORS['success'])
                # Convert position to direction
                if self.body_x < 0.4:
                    direction = "◀ LEFT"
                elif self.body_x > 0.6:
                    direction = "RIGHT ▶"
                else:
                    direction = "CENTER"
                self.position_label.config(text=f"Position: {self.body_x:.2f} ({direction})")
            else:
                self.tracking_status.config(text="● Tracking: SEARCHING", fg=COLORS['warning'])
                self.position_label.config(text="Position: --")
        except:
            pass
    
    def stop(self):
        """Cleanup"""
        self._stop_camera()


class ConnectionPanel(tk.Frame):
    """ESP32-S3 connection panel with firmware flashing"""
    def __init__(self, parent, on_connect=None, on_disconnect=None, main_log=None, **kwargs):
        super().__init__(parent, bg=COLORS['bg_medium'], **kwargs)
        
        self.on_connect_callback = on_connect
        self.on_disconnect_callback = on_disconnect
        self.main_log = main_log  # Callback to main system log
        self.serial_port = None
        self.connected = False
        self.detected_port = None
        self.flashing = False
        
        self._create_widgets()
        self.monitor_running = True
        self.monitor_thread = threading.Thread(target=self._monitor_connection, daemon=True)
        self.monitor_thread.start()

    def _create_widgets(self):
        title = tk.Label(self, text="🔌 ESP32-S3", 
                        bg=COLORS['bg_medium'], fg=COLORS['text_primary'],
                        font=('Segoe UI', 10, 'bold'))
        title.pack(pady=(8, 10))
        
        port_frame = tk.Frame(self, bg=COLORS['bg_medium'])
        port_frame.pack(fill='x', padx=10)
        
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(port_frame, textvariable=self.port_var, 
                                       width=15, state='readonly')
        self.port_combo.pack(side='left', padx=(0, 5))
        
        refresh_btn = tk.Button(port_frame, text="⟳", command=self._refresh_ports,
                               bg=COLORS['bg_light'], fg=COLORS['text_primary'],
                               font=('Segoe UI', 9), bd=0, padx=5, pady=1)
        refresh_btn.pack(side='left')
        
        # Device info
        self.device_info = tk.Label(self, text="", bg=COLORS['bg_medium'], 
                                   fg=COLORS['text_secondary'], font=('Segoe UI', 7),
                                   wraplength=160)
        self.device_info.pack(pady=(5, 0))
        
        # Status
        status_frame = tk.Frame(self, bg=COLORS['bg_medium'])
        status_frame.pack(fill='x', padx=10, pady=(5, 5))
        
        self.status_indicator = tk.Canvas(status_frame, width=10, height=10, 
                                          bg=COLORS['bg_medium'], highlightthickness=0)
        self.status_indicator.pack(side='left')
        self._draw_status_dot(False)
        
        self.status_label = tk.Label(status_frame, text="Disconnected", 
                                     bg=COLORS['bg_medium'], fg=COLORS['text_secondary'],
                                     font=('Segoe UI', 8))
        self.status_label.pack(side='left', padx=(5, 0))
        
        # Connect button
        self.connect_btn = ModernButton(self, text="Connect", 
                                        command=self._toggle_connection,
                                        width=90, height=28,
                                        bg=COLORS['success'])
        self.connect_btn.pack(pady=(5, 5))
        
        # Separator
        sep = tk.Frame(self, bg=COLORS['grid_line'], height=1)
        sep.pack(fill='x', padx=10, pady=5)
        
        # Firmware section
        fw_title = tk.Label(self, text="⚡ FIRMWARE", 
                   bg=COLORS['bg_medium'], fg=COLORS['text_primary'],
                   font=('Segoe UI', 9, 'bold'))
        fw_title.pack(pady=(5, 5))
        # Firmware status
        self.fw_status = tk.Label(self, text="", bg=COLORS['bg_medium'], 
                     fg=COLORS['text_secondary'], font=('Segoe UI', 7),
                     wraplength=160)
        self.fw_status.pack()
        # Flash button (create before _check_firmware)
        self.flash_btn = ModernButton(self, text="🔥 Flash", 
                  command=self._start_flash_instructions,
                  width=90, height=28,
                  bg=COLORS['warning'])
        self.flash_btn.pack(pady=(5, 2))
        
        # Progress bar (hidden initially)
        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(self, variable=self.progress_var, maximum=100, length=150)
        
        # Flash log (hidden initially)
        self.flash_log = tk.Text(self, height=3, width=22, bg=COLORS['bg_dark'],
                                fg=COLORS['text_secondary'], font=('Consolas', 7),
                                state='disabled')
        
        # Initial port refresh
        self._refresh_ports()

    def _toggle_connection(self):
        if self.connected:
            self._disconnect()
        else:
            self._connect()
    
    def _connect(self):
        port_str = self.port_var.get()
        if not port_str:
            return
        
        port = port_str.replace('★', '').strip()
        
        try:
            if port == "SIMULATOR":
                self.serial_port = None
                self.connected = True
                self._update_ui_connected(port)
                if self.on_connect_callback:
                    self.on_connect_callback(None, True)
            else:
                # Try to connect with retry
                max_retries = 3
                last_error = None
                
                for attempt in range(max_retries):
                    try:
                        self.serial_port = serial.Serial(port=port, baudrate=460800, timeout=1)
                        time.sleep(0.3)
                        self.connected = True
                        self._update_ui_connected(port)
                        if self.on_connect_callback:
                            self.on_connect_callback(self.serial_port, False)
                        return  # Success!
                    except serial.SerialException as e:
                        last_error = e
                        time.sleep(0.5)  # Wait before retry
                
                # All retries failed
                error_msg = str(last_error) if last_error else "Unknown error"
                if "Access is denied" in error_msg or "PermissionError" in error_msg:
                    messagebox.showerror("Port Busy", 
                        f"Cannot access {port}.\n\n"
                        f"Please check:\n"
                        f"• Close Arduino IDE or Serial Monitor\n"
                        f"• Close any other program using {port}\n"
                        f"• Unplug and replug the USB cable\n\n"
                        f"Error: {error_msg}")
                else:
                    messagebox.showerror("Connection Error", f"Failed: {error_msg}")
                    
        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed: {e}")
    
    def _disconnect(self):
        if self.serial_port:
            try:
                self.serial_port.close()
            except:
                pass
            self.serial_port = None
        
        self.connected = False
        self._update_ui_disconnected()
        if self.on_disconnect_callback:
            self.on_disconnect_callback()
    
    def _update_ui_connected(self, port):
        self._draw_status_dot(True)
        self.status_label.config(text=f"Connected", fg=COLORS['success'])
        self.connect_btn.text = "Disconnect"
        self.connect_btn.default_bg = COLORS['error']
        self.connect_btn.current_bg = COLORS['error']
        self.connect_btn._draw()
    
    def _update_ui_disconnected(self):
        self._draw_status_dot(False)
        self.status_label.config(text="Disconnected", fg=COLORS['text_secondary'])
        self.connect_btn.text = "Connect"
        self.connect_btn.default_bg = COLORS['success']
        self.connect_btn.current_bg = COLORS['success']
        self.connect_btn._draw()
    def _check_firmware(self):
        """Check if firmware files exist"""
        if os.path.exists(FIRMWARE_BIN):
            size_kb = os.path.getsize(FIRMWARE_BIN) / 1024
            self.fw_status.config(text=f"✓ firmware.bin ({size_kb:.0f}KB)", fg=COLORS['success'])
            self.flash_btn.set_enabled(True)
        else:
            self.fw_status.config(text="✗ firmware.bin not found", fg=COLORS['error'])
            self.flash_btn.set_enabled(False)

    def _draw_status_dot(self, connected):
        self.status_indicator.delete('all')
        color = COLORS['success'] if connected else COLORS['error']
        self.status_indicator.create_oval(1, 1, 9, 9, fill=color, outline='')

    def _monitor_connection(self):
        """Monitor connection status and port availability"""
        last_port_count = 0
        
        while self.monitor_running:
            try:
                # Get current ports
                current_ports = serial.tools.list_ports.comports()
                current_port_names = [p.device for p in current_ports]
                
                # 1. Check if connected port still exists (Auto-disconnect)
                if self.connected and self.serial_port:
                    connected_port = self.serial_port.port
                    if connected_port not in current_port_names:
                        self.after(0, lambda: self._handle_force_disconnect("Device disconnected"))
                
                # 2. Check for port changes (Auto-refresh)
                if len(current_ports) != last_port_count:
                    # Only refresh if dropdown is not open/active? 
                    # Hard to detect, but safe to update 'values'
                    self.after(0, self._refresh_ports)
                    last_port_count = len(current_ports)
                
            except Exception as e:
                print(f"Monitor error: {e}")
            
            time.sleep(1.0)

    def _handle_force_disconnect(self, reason):
        """Force disconnect and switch to simulation"""
        if not self.connected:
            return
            
        self._disconnect()
        messagebox.showwarning("Connection Lost", f"{reason}\nSwitching to Simulation Mode.")
        
        # Auto-switch to simulator
        self.port_combo.set("SIMULATOR")
        self._toggle_connection()

    def _flash_firmware(self):
        """Flash firmware to ESP32-S3"""
        if self.flashing:
            return
        
        # Get port
        port_str = self.port_var.get()
        if not port_str or port_str == "SIMULATOR":
            messagebox.showwarning("Flash Error", "Select a real ESP32 port first!")
            return
        
        port = port_str.replace('★', '').strip()
        
        # FORCE CLOSE any existing connection to this port
        if self.connected and self.serial_port and self.serial_port.port == port:
            self._disconnect()
            
        # Check firmware exists
        if not os.path.exists(FIRMWARE_BIN):
            messagebox.showerror("Flash Error", f"Firmware not found:\n{FIRMWARE_BIN}")
            return
        
        # Disconnect if connected
        if self.connected:
            self._disconnect()
        
        # Confirm
        if not messagebox.askyesno("Flash Firmware", 
            f"Flash firmware to {port}?\n\n"
            f"This will upload:\n"
            f"• firmware.bin\n\n"
            f"The ESP32-S3 will restart after flashing."):
            return
        
        # Show progress
        self.progress.pack(pady=5)
        self.flash_log.pack(pady=5, padx=5, fill='x')
        self.flash_btn.set_enabled(False)
        self.connect_btn.set_enabled(False)
        
        # Start flash thread
        self.flashing = True
        threading.Thread(target=self._do_flash, args=(port,), daemon=True).start()
    
    def _refresh_ports(self):
        ports = list(serial.tools.list_ports.comports())
        port_list = []
        
        # Extended identifiers for both ESP32 and ESP32-S3
        ESP_IDENTIFIERS = [
            (0x303A, 0x1001), # ESP32-S3
            (0x303A, 0x0002), # ESP32-S3 JTAG
            (0x10C4, 0xEA60), # CP210x (Common)
            (0x1A86, 0x7523), # CH340 (Common)
            (0x1A86, 0x55D4), # CH9102 (Common)
            (0x0403, 0x6001), # FTDI
            (0x303A, 0x80C0), # ESP32-C3
        ]
        
        for p in ports:
            port_info = p.device
            is_esp = False
            
            if p.vid and p.pid:
                for vid, pid in ESP_IDENTIFIERS:
                    if p.vid == vid and p.pid == pid:
                        is_esp = True
                        break
            
            desc = f"{port_info}"
            if is_esp:
                desc += " ★" # Mark as likely candidate
            port_list.append(desc)
        
        # Always add SIMULATOR option
        port_list.append("SIMULATOR")
            
        if port_list:
            self.port_combo['values'] = port_list
            # Select first prioritized port (ESP device)
            for p in port_list:
                if "★" in p:
                    self.port_combo.set(p)
                    break
            else:
                # Default to first real port or SIMULATOR
                self.port_combo.set(port_list[0])
        else:
            self.port_combo['values'] = ["SIMULATOR"]
            self.port_combo.set("SIMULATOR")

    def _start_flash_instructions(self):
        """Simplified flash process - directly start flashing"""
        port_str = self.port_var.get()
        
        if not port_str or port_str == "SIMULATOR":
            messagebox.showerror("Flash Error", "Cannot flash SIMULATOR.\nPlease select a real ESP32 port.")
            return
            
        if "No ports" in port_str:
            messagebox.showerror("Flash Error", "No COM port available.\nPlease connect your ESP32.")
            return

        port = port_str.replace('★', '').strip()
        
        # Check firmware exists
        if not os.path.exists(FIRMWARE_BIN):
            messagebox.showerror("Flash Error", f"Firmware not found:\n{FIRMWARE_BIN}\n\nPlease build the firmware first.")
            return
        
        # Disconnect if connected to this port
        if self.connected and self.serial_port:
            try:
                if self.serial_port.port == port:
                    self._disconnect()
                    time.sleep(0.3)
            except:
                pass
        
        # Confirm
        result = messagebox.askyesno("Flash Firmware", 
            f"Flash firmware to {port}?\n\n"
            f"IMPORTANT: Put ESP32 into download mode:\n"
            f"1. Hold BOOT button\n"
            f"2. Press RESET button\n"
            f"3. Release RESET, then BOOT\n\n"
            f"Ready to flash?")
        
        if not result:
            return
        
        # Show progress UI
        self.progress.pack(pady=5)
        self.flash_log.pack(pady=5, padx=5, fill='x')
        self.flash_btn.set_enabled(False)
        self.connect_btn.set_enabled(False)
        
        # Start flash in background thread
        self.flashing = True
        threading.Thread(target=self._do_flash, args=(port,), daemon=True).start()



    def _do_flash(self, port):
        """Perform the actual firmware flash with auto-detection"""
        try:
            self._log_flash("=" * 40)
            self._log_flash("STARTING FLASH PROCESS")
            self._log_flash("=" * 40)
            self.progress_var.set(5)
            
            # Log firmware path
            self._log_flash(f"Port: {port}")
            self._log_flash(f"Firmware: {FIRMWARE_BIN}")
            self._log_flash(f"Firmware exists: {os.path.exists(FIRMWARE_BIN)}")
            
            if os.path.exists(FIRMWARE_BIN):
                size_kb = os.path.getsize(FIRMWARE_BIN) / 1024
                self._log_flash(f"Firmware size: {size_kb:.1f} KB")
            
            # Setup esptool
            esptool_cmd = [sys.executable, '-m', 'esptool']
            try:
                import esptool
                self._log_flash("esptool: installed ✓")
            except ImportError:
                self._log_flash("Installing esptool...")
                subprocess.run([sys.executable, '-m', 'pip', 'install', 'esptool', '-q'], capture_output=True)
            
            # AUTO-DETECT chip type using esptool
            self._log_flash("Auto-detecting chip type...")
            detect_cmd = esptool_cmd + ['--port', port, 'chip_id']
            self._log_flash(f"Running: {' '.join(detect_cmd)}")
            
            detect_result = subprocess.run(detect_cmd, capture_output=True, text=True, timeout=30)
            detect_output = detect_result.stdout + detect_result.stderr
            self._log_flash(f"Chip detect output:")
            for line in detect_output.split('\n'):
                if line.strip():
                    self._log_flash(f"  {line.strip()}")
            
            # Parse chip type from detection
            chip_type = 'esp32'  # Default
            flash_binary = FIRMWARE_BIN_ESP32
            
            if 'esp32-s3' in detect_output.lower() or 'esp32s3' in detect_output.lower():
                chip_type = 'esp32s3'
                flash_binary = FIRMWARE_BIN_ESP32S3
                self._log_flash("✓ Detected: ESP32-S3")
            elif 'esp32' in detect_output.lower():
                chip_type = 'esp32'
                flash_binary = FIRMWARE_BIN_ESP32
                self._log_flash("✓ Detected: ESP32 (regular)")
            else:
                self._log_flash("⚠ Could not detect chip, using ESP32 default")
            
            # Check if firmware exists for detected chip
            if not os.path.exists(flash_binary):
                self._log_flash(f"✗ Firmware not found: {flash_binary}")
                messagebox.showerror("Error", f"Firmware for {chip_type.upper()} not found.\n\nBuild it using: pio run -e {chip_type}")
                return
            
            self.progress_var.set(20)
            
            size_kb = os.path.getsize(flash_binary) / 1024
            self._log_flash(f"Using firmware: {flash_binary}")
            self._log_flash(f"Firmware size: {size_kb:.1f} KB")
            
            # Build flash command - SIMPLIFIED for just firmware.bin
            # Using lower baud for reliability
            cmd = esptool_cmd + [
                '--chip', chip_type,
                '--port', port,
                '--baud', '115200',  # Lower baud for reliability
                '--before', 'default_reset',
                '--after', 'hard_reset',
                '--no-stub',  # Don't use stub loader (more compatible)
                'write_flash',
                '--flash_mode', 'dio',
                '--flash_freq', '40m',
                '--flash_size', 'detect',
                '0x10000', flash_binary
            ]
            
            # Log full command
            self._log_flash("-" * 40)
            self._log_flash("EXECUTING COMMAND:")
            cmd_str = ' '.join(cmd)
            self._log_flash(cmd_str[:100])
            if len(cmd_str) > 100:
                self._log_flash(cmd_str[100:])
            self._log_flash("-" * 40)
            
            self.progress_var.set(30)
            self._log_flash("Running esptool...")
            
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            
            for line in process.stdout:
                line = line.strip()
                if line:
                    # Log FULL line, not truncated
                    self._log_flash(line)
                    if 'Writing' in line:
                        self.progress_var.set(50)
                    if 'Hash of data' in line:
                        self.progress_var.set(80)
            
            process.wait()
            
            self._log_flash(f"Exit code: {process.returncode}")
            
            if process.returncode == 0:
                self.progress_var.set(100)
                self._log_flash("=" * 40)
                self._log_flash("✓ FLASH SUCCESS!")
                self._log_flash("=" * 40)
                messagebox.showinfo("Success", f"Flashed {chip_type.upper()} successfully!\n\nDevice will restart.")
            else:
                self._log_flash("=" * 40)
                self._log_flash("✗ FLASH FAILED")
                self._log_flash("=" * 40)
                messagebox.showerror("Error", "Flash failed. Check system log for details.")

        except Exception as e:
            self._log_flash(f"EXCEPTION: {e}")
            import traceback
            self._log_flash(traceback.format_exc())
            messagebox.showerror("Error", str(e))
        finally:
            self.flashing = False
            self.after(100, self._flash_complete)
    
    def _log_flash(self, text):
        """Log to flash output and main system log"""
        try:
            # Log to local flash log widget
            self.flash_log.config(state='normal')
            self.flash_log.insert('end', text + '\n')
            self.flash_log.see('end')
            self.flash_log.config(state='disabled')
            
            # Also log to main system log
            if self.main_log:
                self.main_log(f"[FLASH] {text}")
        except Exception as e:
            print(f"Log error: {e}")
    
    def _flash_complete(self):
        """Clean up after flash"""
        self.flash_btn.set_enabled(True)
        self.connect_btn.set_enabled(True)
        self.after(3000, self._hide_flash_ui)
        self._refresh_ports()
    
    def _hide_flash_ui(self):
        """Hide flash progress UI"""
        self.progress.pack_forget()
        self.flash_log.pack_forget()
        self.progress_var.set(0)
        self.flash_log.config(state='normal')
        self.flash_log.delete('1.0', 'end')
        self.flash_log.config(state='disabled')


class ManualControlPanel(tk.Frame):
    """Compact manual control panel"""
    def __init__(self, parent, on_angle_change=None, **kwargs):
        super().__init__(parent, bg=COLORS['bg_medium'], **kwargs)
        
        self.on_angle_change = on_angle_change
        self.current_angles = [90] * 64
        
        self._create_widgets()
    
    def _create_widgets(self):
        title = tk.Label(self, text="🎛️ MANUAL", 
                        bg=COLORS['bg_medium'], fg=COLORS['text_primary'],
                        font=('Segoe UI', 10, 'bold'))
        title.pack(pady=(8, 5))
        
        # Angle display
        self.angle_display = tk.Label(self, text="90°", 
                                      bg=COLORS['bg_medium'], fg=COLORS['accent_secondary'],
                                      font=('Segoe UI', 18, 'bold'))
        self.angle_display.pack(pady=5)
        
        # Slider
        self.slider = tk.Scale(self, from_=0, to=180, orient='horizontal',
                               bg=COLORS['bg_light'], fg=COLORS['text_primary'],
                               troughcolor=COLORS['bg_dark'], 
                               highlightthickness=0, length=150,
                               command=self._on_slider)
        self.slider.set(90)
        self.slider.pack(padx=10, pady=5)
        
        # Presets
        presets_frame = tk.Frame(self, bg=COLORS['bg_medium'])
        presets_frame.pack(fill='x', padx=10, pady=5)
        
        for text, angle in [("0°", 0), ("90°", 90), ("180°", 180)]:
            btn = tk.Button(presets_frame, text=text, 
                           command=lambda a=angle: self._set_angle(a),
                           bg=COLORS['bg_light'], fg=COLORS['text_primary'],
                           font=('Segoe UI', 8), bd=0, padx=8, pady=3)
            btn.pack(side='left', padx=2, expand=True, fill='x')
        
        # Wave button
        self.wave_btn = ModernButton(self, text="🌊 Wave", 
                                     command=self._start_wave,
                                     width=80, height=26,
                                     bg=COLORS['accent_secondary'])
        self.wave_btn.pack(pady=5)
        
        # Test Motors button
        self.test_btn = ModernButton(self, text="🔧 Test", 
                                    command=self._test_motors,
                                    width=80, height=26,
                                    bg=COLORS['success'])
        self.test_btn.pack(pady=3)
    
    def _on_slider(self, value):
        angle = int(float(value))
        self.angle_display.config(text=f"{angle}°")
        self._set_angle(angle)
    
    def _set_angle(self, angle):
        self.current_angles = [angle] * 64
        self.slider.set(angle)
        self.angle_display.config(text=f"{angle}°")
        if self.on_angle_change:
            self.on_angle_change(self.current_angles)
    
    def _start_wave(self):
        threading.Thread(target=self._wave_animation, daemon=True).start()
    
    def _wave_animation(self):
        for frame in range(60):
            angles = []
            for i in range(64):
                row = i // 8
                col = i % 8
                wave = math.sin((frame + col + row) * 0.3) * 45 + 90
                angles.append(int(wave))
            
            self.current_angles = angles
            if self.on_angle_change:
                self.on_angle_change(angles)
            time.sleep(0.05)
        
        self._set_angle(90)
    
    def _test_motors(self):
        """Toggle continuous motor test"""
        if hasattr(self, 'testing') and self.testing:
            # Stop testing
            self.testing = False
            self.test_btn.text = "🔧 Test"
            self.test_btn.default_bg = COLORS['success']
            self.test_btn.current_bg = COLORS['success']
            self.test_btn._draw()
        else:
            # Start testing
            self.testing = True
            self.test_btn.text = "⏹ Stop"
            self.test_btn.default_bg = COLORS['error']
            self.test_btn.current_bg = COLORS['error']
            self.test_btn._draw()
            threading.Thread(target=self._test_animation, daemon=True).start()
    
    def _test_animation(self):
        """Sweep all motors continuously: 90 -> 0 -> 180 -> 90 (loop)"""
        while hasattr(self, 'testing') and self.testing:
            # Go to 0
            for angle in range(90, -1, -5):
                if not self.testing:
                    break
                self.current_angles = [angle] * 64
                if self.on_angle_change:
                    self.on_angle_change(self.current_angles)
                time.sleep(0.05)
            
            if not self.testing:
                break
            time.sleep(0.3)
            
            # Go to 180
            for angle in range(0, 181, 5):
                if not self.testing:
                    break
                self.current_angles = [angle] * 64
                if self.on_angle_change:
                    self.on_angle_change(self.current_angles)
                time.sleep(0.05)
            
            if not self.testing:
                break
            time.sleep(0.3)
            
            # Back to 90
            for angle in range(180, 89, -5):
                if not self.testing:
                    break
                self.current_angles = [angle] * 64
                if self.on_angle_change:
                    self.on_angle_change(self.current_angles)
                time.sleep(0.05)
            
            time.sleep(0.3)
        
        # Reset to center when stopped
        self._set_angle(90)


class SimulationVisualizer:
    """Main Motor Control Application with Camera Tracking"""
    
    def __init__(self, root):
        self.root = root
        self.root.configure(bg=COLORS['bg_dark'])
        self.virtual_device = None
        if get_virtual_device_instance:
            try:
                self.virtual_device = get_virtual_device_instance()
            except:
                pass
        self.serial_port = None
        self.simulation_mode = True
        self.running = True
        self.tracking_enabled = True
        self.control_mode = tk.StringVar(value="Test")  # "Live" or "Test"
        self._create_widgets()
        self._update_loop()
    
    def _create_widgets(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TCombobox', fieldbackground=COLORS['bg_light'],
                       background=COLORS['bg_light'])
        # Main container
        main = tk.Frame(self.root, bg=COLORS['bg_dark'])
        main.pack(fill='both', expand=True, padx=8, pady=8)
        # Header
        header = tk.Frame(main, bg=COLORS['bg_dark'])
        header.pack(fill='x', pady=(0, 8))
        title = tk.Label(header, text="🪞 MOTOR CONTROL SYSTEM", 
                        bg=COLORS['bg_dark'], fg=COLORS['text_primary'],
                        font=('Segoe UI', 16, 'bold'))
        title.pack(side='left')
        # Mode selector
        mode_frame = tk.Frame(header, bg=COLORS['bg_dark'])
        mode_frame.pack(side='right', padx=10)
        tk.Label(mode_frame, text="Mode:", bg=COLORS['bg_dark'], fg=COLORS['text_secondary'], font=('Segoe UI', 10)).pack(side='left')
        mode_combo = ttk.Combobox(mode_frame, textvariable=self.control_mode, values=["Live", "Test"], state='readonly', width=7)
        mode_combo.pack(side='left', padx=4)
        mode_combo.bind('<<ComboboxSelected>>', self._on_mode_change)
        self.mode_label = tk.Label(mode_frame, text="[ LIVE ]", 
                                   bg=COLORS['bg_dark'], fg=COLORS['success'],
                                   font=('Segoe UI', 10))
        self.mode_label.pack(side='left', padx=8)
        
        # Diagram button
        diagram_btn = ModernButton(mode_frame, text="📊 Diagram", 
                                   command=self._show_wiring_diagram,
                                   width=100, height=28,
                                   bg=COLORS['accent_secondary'])
        diagram_btn.pack(side='left', padx=8)
        # Content - 3 columns
        content = tk.Frame(main, bg=COLORS['bg_dark'])
        content.pack(fill='both', expand=True)
        # Left: Camera (largest)
        self.camera_panel = CameraPanel(content, on_angle_change=self._on_angle_change)
        self.camera_panel.pack(side='left', fill='both', expand=True, padx=(0, 8))
        # Right side panel
        right_panel = tk.Frame(content, bg=COLORS['bg_dark'], width=380)
        right_panel.pack(side='right', fill='y')
        right_panel.pack_propagate(False)
        # Controls (bottom right)
        controls_frame = tk.Frame(right_panel, bg=COLORS['bg_dark'])
        controls_frame.pack(side='bottom', fill='x')
        
        # Motor visualization (top right)
        motor_frame = tk.Frame(right_panel, bg=COLORS['bg_dark'])
        motor_frame.pack(side='top', fill='both', expand=True, pady=(0, 8))
        self.motor_viz = MotorVisualizer(motor_frame)
        self.motor_viz.pack(fill='both', expand=True)
        # Connection panel - main_log will be set after _create_widgets
        self.connection_panel = ConnectionPanel(
            controls_frame, 
            on_connect=self._on_connect,
            on_disconnect=self._on_disconnect,
            main_log=lambda msg: self._log(msg) if hasattr(self, 'log_text') else print(msg)
        )
        self.connection_panel.pack(side='left', fill='y', padx=(0, 8))
        # Manual control panel
        self.control_panel = ManualControlPanel(
            controls_frame,
            on_angle_change=self._on_angle_change
        )
        self.control_panel.pack(side='left', fill='y')
        
        # LIVE LOG PANEL - shows all system events
        log_frame = tk.Frame(main, bg=COLORS['bg_medium'])
        log_frame.pack(fill='x', pady=(8, 0))
        
        log_header = tk.Frame(log_frame, bg=COLORS['bg_medium'])
        log_header.pack(fill='x')
        tk.Label(log_header, text="📋 SYSTEM LOG", bg=COLORS['bg_medium'], fg=COLORS['text_primary'],
                font=('Segoe UI', 9, 'bold')).pack(side='left', padx=10, pady=4)
        
        # Clear log button
        clear_btn = tk.Button(log_header, text="Clear", command=self._clear_log,
                             bg=COLORS['bg_light'], fg=COLORS['text_secondary'],
                             font=('Segoe UI', 8), bd=0, padx=8)
        clear_btn.pack(side='right', padx=10)
        
        # Log text area
        self.log_text = tk.Text(log_frame, height=6, bg=COLORS['bg_dark'],
                               fg=COLORS['text_secondary'], font=('Consolas', 9),
                               state='disabled', wrap='word')
        self.log_text.pack(fill='x', padx=10, pady=(0, 8))
        
        # Status bar
        status_bar = tk.Frame(main, bg=COLORS['bg_medium'], height=28)
        status_bar.pack(fill='x')
        self.status_text = tk.Label(status_bar, text="Camera feed always running. Select mode to control motors.", 
                                    bg=COLORS['bg_medium'], fg=COLORS['text_secondary'],
                                    font=('Segoe UI', 9))
        self.status_text.pack(side='left', padx=10, pady=4)
        mp_status = "MediaPipe: ✓" if MEDIAPIPE_AVAILABLE else "MediaPipe: ✗ (install for tracking)"
        mp_color = COLORS['success'] if MEDIAPIPE_AVAILABLE else COLORS['warning']
        tk.Label(status_bar, text=mp_status, bg=COLORS['bg_medium'], fg=mp_color,
                font=('Segoe UI', 8)).pack(side='right', padx=10, pady=4)
        
        # Log initial message
        self._log("System started. Ready.")
    
    def _log(self, message):
        """Add a message to the live log"""
        try:
            timestamp = time.strftime("%H:%M:%S")
            self.log_text.config(state='normal')
            self.log_text.insert('end', f"[{timestamp}] {message}\n")
            self.log_text.see('end')
            self.log_text.config(state='disabled')
        except:
            pass
    
    def _clear_log(self):
        """Clear the log"""
        try:
            self.log_text.config(state='normal')
            self.log_text.delete('1.0', 'end')
            self.log_text.config(state='disabled')
        except:
            pass
    
    def _on_mode_change(self, event=None):
        mode = self.control_mode.get()
        if mode == "Live":
            self.mode_label.config(text="[ LIVE ]", fg=COLORS['success'])
            self.status_text.config(text="Live mode: Motors follow camera body tracking.")
        else:
            self.mode_label.config(text="[ TEST ]", fg=COLORS['accent_secondary'])
            self.status_text.config(text="Test mode: Use manual controls to move motors.")
    
    def _on_body_position(self, x_position):
        """Handle body position change from camera tracking"""
        if not self.tracking_enabled:
            return
        if self.control_mode.get() != "Live":
            return
        # Map body X position (0-1) to motor angles
        target_angle = x_position * 180
        angles = []
        center_motor = int(x_position * 8)
        for i in range(64):
            row = i // 8
            col = i % 8
            dist = abs(col - center_motor)
            strength = max(0, 1.0 - (dist / 4.0))
            angle = 90 + (x_position - 0.5) * 180 * strength
            angle = max(0, min(180, angle))
            angles.append(int(angle))
        self._on_angle_change(angles)
    
    def _on_connect(self, serial_port, is_simulation):
        self.serial_port = serial_port
        self.simulation_mode = is_simulation
        
        if is_simulation:
            self.mode_label.config(text="[ SIMULATION ]", fg=COLORS['warning'])
            self.status_text.config(text="Simulation mode - motors visualized only")
        else:
            self.mode_label.config(text="[ HARDWARE ]", fg=COLORS['success'])
            self.status_text.config(text="Connected to ESP32 - motors active!")
            self._log("Connected to hardware!")
            
            # Auto-switch to Live mode
            self.control_mode.set("Live")
            self._on_mode_change()
            self._log("Switched to Live mode")
    
    def _show_wiring_diagram(self):
        """Show wiring diagram in a new window"""
        diagram_window = tk.Toplevel(self.root)
        diagram_window.title("Wiring Diagram - ESP32 + PCA9685")
        diagram_window.geometry("800x600")
        diagram_window.configure(bg=COLORS['bg_dark'])
        
        # Center the window
        diagram_window.update_idletasks()
        x = (diagram_window.winfo_screenwidth() - 800) // 2
        y = (diagram_window.winfo_screenheight() - 600) // 2
        diagram_window.geometry(f"+{x}+{y}")
        
        # Title
        title = tk.Label(diagram_window, text="🔌 ESP32 + PCA9685 Wiring Diagram",
                        bg=COLORS['bg_dark'], fg=COLORS['text_primary'],
                        font=('Segoe UI', 16, 'bold'))
        title.pack(pady=10)
        
        # Canvas for diagram
        canvas = tk.Canvas(diagram_window, width=760, height=450, 
                          bg=COLORS['bg_medium'], highlightthickness=0)
        canvas.pack(pady=10)
        
        # Draw ESP32
        esp_x, esp_y = 150, 100
        esp_w, esp_h = 120, 200
        canvas.create_rectangle(esp_x, esp_y, esp_x+esp_w, esp_y+esp_h, 
                               fill='#2D4A3E', outline='#4CAF50', width=2)
        canvas.create_text(esp_x+esp_w//2, esp_y+20, text="ESP32", 
                          fill='white', font=('Segoe UI', 12, 'bold'))
        
        # ESP32 Pins
        esp_pins = [
            ("3.3V", 40), ("GND", 60), ("D18 (SDA)", 100), ("D19 (SCL)", 120),
            ("D5 (LED1)", 160), ("VIN (5V)", 80)
        ]
        for pin_name, y_off in esp_pins:
            canvas.create_text(esp_x+esp_w+10, esp_y+y_off, text=pin_name,
                              fill='#4CAF50', font=('Consolas', 9), anchor='w')
            canvas.create_oval(esp_x+esp_w-5, esp_y+y_off-3, esp_x+esp_w+5, esp_y+y_off+3,
                              fill='#4CAF50', outline='')
        
        # Draw PCA9685 boards (smaller, 4 in 2x2 grid)
        pca_w, pca_h = 120, 70
        
        # PCA9685 #1 (0x40)
        pca1_x, pca1_y = 400, 60
        canvas.create_rectangle(pca1_x, pca1_y, pca1_x+pca_w, pca1_y+pca_h,
                               fill='#4A2D4A', outline='#9C27B0', width=2)
        canvas.create_text(pca1_x+pca_w//2, pca1_y+15, text="PCA9685 #1",
                          fill='white', font=('Segoe UI', 9, 'bold'))
        canvas.create_text(pca1_x+pca_w//2, pca1_y+35, text="0x40 | Servos 0-15",
                          fill='#CE93D8', font=('Consolas', 8))
        
        # PCA9685 #2 (0x41)
        pca2_x, pca2_y = 550, 60
        canvas.create_rectangle(pca2_x, pca2_y, pca2_x+pca_w, pca2_y+pca_h,
                               fill='#4A2D3E', outline='#E91E63', width=2)
        canvas.create_text(pca2_x+pca_w//2, pca2_y+15, text="PCA9685 #2",
                          fill='white', font=('Segoe UI', 9, 'bold'))
        canvas.create_text(pca2_x+pca_w//2, pca2_y+35, text="0x41 | Servos 16-31",
                          fill='#F48FB1', font=('Consolas', 8))
        
        # PCA9685 #3 (0x42)
        pca3_x, pca3_y = 400, 150
        canvas.create_rectangle(pca3_x, pca3_y, pca3_x+pca_w, pca3_y+pca_h,
                               fill='#2D4A4A', outline='#00BCD4', width=2)
        canvas.create_text(pca3_x+pca_w//2, pca3_y+15, text="PCA9685 #3",
                          fill='white', font=('Segoe UI', 9, 'bold'))
        canvas.create_text(pca3_x+pca_w//2, pca3_y+35, text="0x42 | Servos 32-47",
                          fill='#80DEEA', font=('Consolas', 8))
        
        # PCA9685 #4 (0x43)
        pca4_x, pca4_y = 550, 150
        canvas.create_rectangle(pca4_x, pca4_y, pca4_x+pca_w, pca4_y+pca_h,
                               fill='#4A4A2D', outline='#CDDC39', width=2)
        canvas.create_text(pca4_x+pca_w//2, pca4_y+15, text="PCA9685 #4",
                          fill='white', font=('Segoe UI', 9, 'bold'))
        canvas.create_text(pca4_x+pca_w//2, pca4_y+35, text="0x43 | Servos 48-63",
                          fill='#E6EE9C', font=('Consolas', 8))
        
        # Draw wires
        # I2C Bus line (SDA + SCL combined for simplicity)
        canvas.create_line(esp_x+esp_w+5, esp_y+100, 330, esp_y+100,
                          fill='#2196F3', width=3)
        canvas.create_text(330, esp_y+100-10, text="SDA (D18)", fill='#2196F3',
                          font=('Consolas', 8))
        
        canvas.create_line(esp_x+esp_w+5, esp_y+120, 330, esp_y+120,
                          fill='#FF9800', width=3)
        canvas.create_text(330, esp_y+120-10, text="SCL (D19)", fill='#FF9800',
                          font=('Consolas', 8))
        
        # I2C bus to all PCA boards
        canvas.create_line(330, esp_y+100, 330, pca3_y+pca_h+10,
                          fill='#2196F3', width=2)
        canvas.create_line(350, esp_y+120, 350, pca3_y+pca_h+10,
                          fill='#FF9800', width=2)
        
        # Connect to each PCA
        for pca_x, pca_y_pos in [(pca1_x, pca1_y+pca_h//2), (pca2_x, pca2_y+pca_h//2),
                                 (pca3_x, pca3_y+pca_h//2), (pca4_x, pca4_y+pca_h//2)]:
            canvas.create_line(330, pca_y_pos, pca_x, pca_y_pos,
                              fill='#2196F3', width=1, dash=(2, 2))
        
        # VCC/GND indicators
        canvas.create_text(pca1_x+pca_w//2, pca1_y+pca_h-10, text="VCC|GND|V+",
                          fill='#9E9E9E', font=('Consolas', 7))
        
        # I2C chain indicator
        canvas.create_text(475, 130, text="I2C Bus (all share SDA/SCL)",
                          fill='#9E9E9E', font=('Consolas', 8))
        
        # Legend
        legend_y = 390
        canvas.create_text(50, legend_y, text="WIRING LEGEND:", 
                          fill='white', font=('Segoe UI', 10, 'bold'), anchor='w')
        
        legend_items = [
            ("SDA (GPIO 18)", '#2196F3', 50),
            ("SCL (GPIO 19)", '#FF9800', 200),
            ("VCC (3.3V)", '#F44336', 350),
            ("GND", '#424242', 470),
        ]
        for text, color, x_pos in legend_items:
            canvas.create_rectangle(x_pos, legend_y+20, x_pos+20, legend_y+30, fill=color)
            canvas.create_text(x_pos+25, legend_y+25, text=text, fill='white',
                              font=('Consolas', 9), anchor='w')
        
        # Instructions
        instructions = tk.Text(diagram_window, height=4, width=90, bg=COLORS['bg_light'],
                              fg=COLORS['text_secondary'], font=('Consolas', 9),
                              state='normal', wrap='word')
        instructions.pack(pady=10, padx=20)
        instructions.insert('1.0', """CONNECTIONS:
ESP32 D18 (SDA) → PCA9685 SDA pins (both boards)
ESP32 D19 (SCL) → PCA9685 SCL pins (both boards)
ESP32 GND → PCA9685 GND (both boards)
ESP32 VIN (5V) → Servo power supply (external recommended for 32 servos)
PCA9685 VCC → 3.3V (logic) | V+ → 5V (servo power)""")
        instructions.config(state='disabled')
        
        # Close button
        close_btn = ModernButton(diagram_window, text="Close", 
                                command=diagram_window.destroy,
                                width=100, height=32, bg=COLORS['error'])
        close_btn.pack(pady=10)
    
    def _on_disconnect(self):
        self.serial_port = None
        self.simulation_mode = True
        self.mode_label.config(text="[ DISCONNECTED ]", fg=COLORS['error'])
        self.status_text.config(text="Disconnected")
        
        # Auto-switch to Test mode
        self.control_mode.set("Test")
        self._on_mode_change()
        self._log("Switched to Test mode")
    
    def _on_angle_change(self, angles):
        """Handle angle changes from any source"""
        self.motor_viz.update_angles(angles)
        
        # Always try to send if we have a serial port (hardware mode)
        if self.serial_port:
            self._send_motor_packet(angles)
        
        if self.simulation_mode and self.virtual_device:
            try:
                self.virtual_device._motors = list(angles)
            except:
                pass
    
    def _send_motor_packet(self, angles):
        """Send motor angles to ESP32"""
        if not self.serial_port:
            self._log("No serial port - cannot send")
            return
        
        try:
            # Protocol: 0xAA 0xBB 0x02 + 128 bytes (64 servos * 2 bytes)
            packet = bytearray([0xAA, 0xBB, 0x02])
            
            # Ensure we have 64 angles (pad with 90 if needed)
            motor_angles = list(angles[:64]) + [90] * max(0, 64 - len(angles))
            
            for angle in motor_angles:
                angle = max(0, min(180, int(angle)))
                value = int((angle / 180.0) * 1000)  # Map 0-180 to 0-1000
                packet.append((value >> 8) & 0xFF)  # High byte
                packet.append(value & 0xFF)         # Low byte
            
            # Write packet
            self.serial_port.write(packet)
            self.serial_port.flush()
            
        except Exception as e:
            # Log only on real failure
            print(f"Send error: {e}")
    
    def _update_loop(self):
        """Main update loop for simulation sync"""
        if not self.running:
            return
        
        # Sync from virtual device if needed
        if self.simulation_mode and self.virtual_device:
            try:
                state = self.virtual_device.get_server_state()
                # Only update if not being controlled by camera
                if not self.camera_panel.running:
                    motor_angles = state.get('motors', [90] * 64)
                    self.motor_viz.update_angles(motor_angles)
            except:
                pass
        
        self.root.after(50, self._update_loop)
    
    def stop(self):
        """Stop the application"""
        self.running = False
        self.camera_panel.stop()
        if self.serial_port:
            try:
                self.serial_port.close()
            except:
                pass

def kill_duplicate_processes():
    """Kill any other instances of this script running"""
    try:
        import psutil
    except ImportError:
        # Install psutil if not available
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'psutil', '-q'], capture_output=True)
        import psutil
    
    current_pid = os.getpid()
    script_name = 'sim_visualizer'
    killed_count = 0
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['pid'] == current_pid:
                continue
            
            cmdline = proc.info.get('cmdline') or []
            cmdline_str = ' '.join(cmdline).lower()
            
            # Check if this is another instance of our script
            if 'python' in proc.info.get('name', '').lower():
                if script_name in cmdline_str or 'sim_visualizer' in cmdline_str:
                    print(f"Killing duplicate process: PID {proc.info['pid']}")
                    proc.kill()
                    killed_count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    
    return killed_count


if __name__ == "__main__":
    # AUTO-KILL: Terminate any other running instances first
    killed = kill_duplicate_processes()
    if killed > 0:
        print(f"[AUTO-KILL] Terminated {killed} duplicate instance(s)")
        time.sleep(0.5)  # Allow resources to be released
    
    root = tk.Tk()
    root.title("Motor Control System")
    root.geometry("1200x700")
    root.configure(bg=COLORS['bg_dark'])
    
    root.update_idletasks()
    x = (root.winfo_screenwidth() - 1200) // 2
    y = (root.winfo_screenheight() - 700) // 2
    root.geometry(f"+{x}+{y}")
    
    app = SimulationVisualizer(root)
    
    def on_close():
        app.stop()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()
