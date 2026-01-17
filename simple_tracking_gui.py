"""
Simple LED Tracking GUI
Uses MediaPipe for body tracking to control LED matrix
Camera on left, LED Simulator on right
"""
import tkinter as tk
from tkinter import ttk, messagebox
import cv2
import numpy as np
from PIL import Image, ImageTk
import time
import urllib.request
from pathlib import Path

# MediaPipe imports (new API)
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

# Project imports
from packages.mirror_core.controllers.led_controller import LEDController
from packages.mirror_core.simulation.mock_serial import MockSerial


class SimpleLEDTrackingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Mirror LED Tracking")
        self.root.geometry("1200x700")
        
        # State
        self.running = True
        self.tracking = False
        self.cap = None
        self.pose_landmarker = None
        self.serial_port = None
        self.frame_count = 0
        
        # LED Controller
        self.led_controller = LEDController(width=32, height=64)
        
        # Background subtractor for silhouette
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=500, varThreshold=16, detectShadows=False
        )
        
        # Build UI
        self.build_ui()
        
        # Connect to simulator automatically
        self.connect_simulator()
        
        # Start update loop
        self.update_frame()
        
        # Handle close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def build_ui(self):
        # Main container
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill=tk.BOTH, expand=True)
        
        # Top controls
        controls = ttk.Frame(main)
        controls.pack(fill=tk.X, pady=(0, 10))
        
        # Camera selection
        ttk.Label(controls, text="Camera:").pack(side=tk.LEFT, padx=5)
        self.cam_var = tk.StringVar(value="0")
        self.cam_combo = ttk.Combobox(controls, textvariable=self.cam_var, 
                                       values=["0", "1", "2"], width=5)
        self.cam_combo.pack(side=tk.LEFT, padx=5)
        
        # Start/Stop button
        self.track_btn = ttk.Button(controls, text="▶ Start Tracking", 
                                     command=self.toggle_tracking)
        self.track_btn.pack(side=tk.LEFT, padx=20)
        
        # Status
        self.status_var = tk.StringVar(value="Ready - Click Start Tracking")
        ttk.Label(controls, textvariable=self.status_var).pack(side=tk.RIGHT, padx=10)
        
        # Main content - Left and Right panels
        content = ttk.Frame(main)
        content.pack(fill=tk.BOTH, expand=True)
        
        # LEFT: Camera view
        left_frame = ttk.LabelFrame(content, text="Camera Feed", padding=5)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        self.camera_label = ttk.Label(left_frame, text="Camera preview will appear here\n\nClick 'Start Tracking' to begin")
        self.camera_label.pack(fill=tk.BOTH, expand=True)
        
        # RIGHT: LED visualization
        right_frame = ttk.LabelFrame(content, text="LED Matrix Simulation (32x64)", padding=5)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        self.led_canvas = tk.Canvas(right_frame, bg='black')
        self.led_canvas.pack(fill=tk.BOTH, expand=True)
        
        # LED frame data storage
        self.led_frame_data = np.zeros((64, 32, 3), dtype=np.uint8)
    
    def connect_simulator(self):
        """Connect to mock serial simulator"""
        try:
            self.serial_port = MockSerial(port="SIMULATOR", baudrate=460800)
            self.led_controller.mapping_mode = 0  # RAW mode for simulation
            self.status_var.set("Connected to Simulator")
            print("[App] Connected to simulator")
        except Exception as e:
            print(f"[App] Simulator error: {e}")
            self.status_var.set(f"Simulator error: {e}")
    
    def toggle_tracking(self):
        if self.tracking:
            self.stop_tracking()
        else:
            self.start_tracking()
    
    def start_tracking(self):
        """Start camera and pose detection"""
        cam_idx = int(self.cam_var.get())
        print(f"[App] Starting tracking on camera {cam_idx}...")
        self.status_var.set(f"Opening camera {cam_idx}...")
        self.root.update()
        
        # Open camera
        self.cap = cv2.VideoCapture(cam_idx, cv2.CAP_DSHOW)
        time.sleep(0.3)
        
        if not self.cap.isOpened():
            messagebox.showerror("Error", f"Cannot open camera {cam_idx}")
            self.status_var.set("Camera error!")
            return
        
        # Test read
        ret, frame = self.cap.read()
        if not ret:
            messagebox.showerror("Error", f"Camera {cam_idx} opened but cannot read frames")
            self.cap.release()
            self.status_var.set("Camera read error!")
            return
        
        print(f"[App] Camera opened: {frame.shape}")
        self.status_var.set("Initializing pose detection...")
        self.root.update()
        
        # Initialize MediaPipe
        try:
            model_path = Path("data/pose_landmarker_lite.task")
            model_path.parent.mkdir(exist_ok=True)
            
            if not model_path.exists():
                print("[App] Downloading pose model...")
                self.status_var.set("Downloading pose model (10MB)...")
                self.root.update()
                url = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"
                urllib.request.urlretrieve(url, model_path)
                print("[App] Model downloaded")
            
            base_options = mp_python.BaseOptions(model_asset_path=str(model_path))
            options = mp_vision.PoseLandmarkerOptions(
                base_options=base_options,
                running_mode=mp_vision.RunningMode.VIDEO,
                min_pose_detection_confidence=0.5,
                min_pose_presence_confidence=0.5,
                min_tracking_confidence=0.5
            )
            self.pose_landmarker = mp_vision.PoseLandmarker.create_from_options(options)
            print("[App] MediaPipe initialized")
        except Exception as e:
            print(f"[App] MediaPipe init error: {e}")
            self.pose_landmarker = None
        
        self.tracking = True
        self.track_btn.config(text="■ Stop Tracking")
        self.status_var.set("Tracking active!")
        self.frame_count = 0
        print("[App] Tracking started!")
    
    def stop_tracking(self):
        """Stop camera and tracking"""
        print("[App] Stopping tracking...")
        self.tracking = False
        
        if self.cap:
            self.cap.release()
            self.cap = None
        
        if self.pose_landmarker:
            self.pose_landmarker.close()
            self.pose_landmarker = None
        
        self.track_btn.config(text="▶ Start Tracking")
        self.status_var.set("Tracking stopped")
        
        # Clear camera view
        self.camera_label.config(image='', text="Camera stopped\n\nClick 'Start Tracking' to begin")
        print("[App] Tracking stopped")
    
    def update_frame(self):
        """Main update loop - called by tkinter"""
        if not self.running:
            return
        
        if self.tracking and self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                self.process_frame(frame)
        
        # Update LED visualization
        self.draw_leds()
        
        # Schedule next update (30 fps)
        self.root.after(33, self.update_frame)
    
    def process_frame(self, frame):
        """Process camera frame for LED silhouette"""
        self.frame_count += 1
        
        # Flip for mirror view
        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape
        
        # Reset LED frame
        self.led_frame_data = np.zeros((64, 32, 3), dtype=np.uint8)
        
        # Add info text
        cv2.putText(frame, "LED Silhouette Mode", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        
        # --- POSE DETECTION (for status display) ---
        person_detected = False
        if self.pose_landmarker:
            try:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
                timestamp_ms = int(self.frame_count * 33)
                
                result = self.pose_landmarker.detect_for_video(mp_image, timestamp_ms)
                
                if result and result.pose_landmarks:
                    person_detected = True
                    cv2.putText(frame, "Person detected!", (10, 60),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                else:
                    cv2.putText(frame, "No person detected", (10, 60),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (128, 128, 128), 1)
                    
            except Exception as e:
                cv2.putText(frame, f"Pose error: {str(e)[:30]}", (10, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
        
        # --- LED silhouette using background subtraction ---
        fg_mask = self.bg_subtractor.apply(frame)
        
        # Clean up mask
        kernel = np.ones((5, 5), np.uint8)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)
        
        # Resize for LED matrix (32 wide x 64 tall)
        mask_small = cv2.resize(fg_mask, (32, 64))
        
        # Set LED colors - green for silhouette
        self.led_frame_data[:, :, 1] = mask_small
        
        # Show silhouette overlay on camera view
        green_overlay = np.zeros_like(frame)
        green_overlay[:, :, 1] = fg_mask
        cv2.addWeighted(frame, 1.0, green_overlay, 0.3, 0, frame)
        
        cv2.putText(frame, "Green = LED silhouette", (10, h - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        # --- SEND TO SIMULATOR ---
        if self.serial_port and self.serial_port.is_open:
            try:
                packet = self.led_controller.pack_led_packet(self.led_frame_data)
                self.serial_port.write(packet)
            except:
                pass
        
        # --- UPDATE CAMERA VIEW ---
        frame_resized = cv2.resize(frame, (640, 480))
        frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb)
        imgtk = ImageTk.PhotoImage(image=img)
        
        self.camera_label.imgtk = imgtk  # Keep reference!
        self.camera_label.config(image=imgtk, text='')
    
    def draw_leds(self):
        """Draw LED matrix visualization"""
        self.led_canvas.delete("all")
        
        canvas_w = self.led_canvas.winfo_width()
        canvas_h = self.led_canvas.winfo_height()
        
        if canvas_w < 10 or canvas_h < 10:
            return
        
        # Calculate pixel size
        px_w = canvas_w / 32
        px_h = canvas_h / 64
        
        # Draw only non-black pixels for performance
        for y in range(64):
            for x in range(32):
                r, g, b = self.led_frame_data[y, x]
                if r > 10 or g > 10 or b > 10:
                    color = f"#{r:02x}{g:02x}{b:02x}"
                    self.led_canvas.create_rectangle(
                        x * px_w, y * px_h,
                        (x + 1) * px_w, (y + 1) * px_h,
                        fill=color, outline=""
                    )
    
    def on_close(self):
        """Handle window close"""
        print("[App] Closing...")
        self.running = False
        self.stop_tracking()
        
        if self.serial_port:
            self.serial_port.close()
        
        self.root.destroy()


def main():
    root = tk.Tk()
    app = SimpleLEDTrackingApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
