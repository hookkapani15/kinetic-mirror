import tkinter as tk
from tkinter import ttk, messagebox
import cv2
import threading
import queue
import numpy as np
from PIL import Image, ImageTk
import logging

from .theme import COLORS
from .widgets import ModernButton
from core.segmentation import BodySegmenter

logger = logging.getLogger("main")

class CameraPanel(tk.Frame):
    """Live camera feed panel with body tracking - HIGH PERFORMANCE VERSION"""
    
    # Processing resolution (lower = faster, but less detail)
    # Optimized for MediaPipe 0.10.x Performance
    PROC_WIDTH = 192
    PROC_HEIGHT = 144
    
    def __init__(self, parent, on_angle_change=None, on_frame_ready=None, **kwargs):
        super().__init__(parent, bg=COLORS['bg_dark'], **kwargs)
        self.on_angle_change = on_angle_change
        self.on_frame_ready = on_frame_ready
        self.on_canvas_click = None # Callback(x, y) 
        self.cap = None
        self.running = False
        self.current_camera = None
        self.body_segmenter = None
        self.body_x = 0.5
        self.body_detected = False
        self._calib_points = [] # List of (x, y) in image coords
        self.homography = None # cv2 homography matrix
        
        # Thread-safe queues for dual-pipeline architecture
        self._frame_queue = queue.Queue(maxsize=1)  # Always freshest frame
        self._seg_queue = queue.Queue(maxsize=1)    # Always freshest for segmentation
        self._display_scheduled = False
        
        # Shared state between threads
        self._last_seg_mask = None  # Last segmentation result for overlay
        self._last_imgtk = None     # Keep reference to prevent GC
        self.tracking_sync_mode = True  # Default: SYNC ALL
        self.tracking_invert = False
        self.on_detection_change = None # New callback for silhouette only
        
        # UI Attributes (declared here with types for linter)
        self.camera_var = tk.StringVar()
        self.camera_combo = None 
        self.video_canvas = None
        self.tracking_status = None
        self.position_label = None
        self.start_btn = None
        self._canvas_img_id = None
        self.frame_count = 0 
        
        self._create_widgets()
        self._detect_cameras()
        self.after(300, self._auto_start_camera)

    def _auto_start_camera(self):
        """Auto-start camera 1 if available, else camera 0"""
        cameras = self.camera_combo['values']
        if cameras and isinstance(cameras, (list, tuple)):
            if len(cameras) > 0:
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
        self.video_canvas.bind('<Button-1>', self._handle_click)
        
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
        """Detect available cameras (runs in background to avoid UI freeze)"""
        def _scan():
            cameras = []
            # Test camera indices 0-4 (5 is enough, 10 was too slow)
            for i in range(5):
                try:
                    cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
                    if cap.isOpened():
                        ret, frame = cap.read()
                        if ret and frame is not None:
                            cameras.append(f"Camera {i}")
                        cap.release()
                except Exception:
                    pass
            # Update UI on main thread
            self.after(0, lambda: self._apply_cameras(cameras))
        threading.Thread(target=_scan, daemon=True).start()
    
    def _apply_cameras(self, cameras):
        """Apply detected cameras to UI (must run on main thread)"""
        if cameras:
            self.camera_combo['values'] = cameras
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
        
        try:
            cam_idx = int(cam_str.split()[-1])
        except (ValueError, IndexError):
            cam_idx = 0
        
        # Open camera with DirectShow for Windows (faster)
        self.cap = cv2.VideoCapture(cam_idx, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(cam_idx)
            
        if not self.cap.isOpened():
            logger.error(f"❌ Failed to open camera {cam_idx}")
            messagebox.showerror("Camera Error", f"Failed to open camera {cam_idx}")
            return
        
        # PERFORMANCE: Set camera to capture at processing resolution directly
        # This avoids expensive resize operations
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.PROC_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.PROC_HEIGHT)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize buffer delay
        
        logger.info(f"📸 Camera {cam_idx} opened at {self.PROC_WIDTH}x{self.PROC_HEIGHT}")
        
        # Initialize BodySegmenter
        try:
            logger.info("⏳ Initializing BodySegmenter...")
            self.body_segmenter = BodySegmenter()
            logger.info("✅ BodySegmenter initialized")
        except Exception as e:
            logger.error(f"❌ BodySegmenter failed: {e}")
            self.body_segmenter = None
        
        # Clear queues
        while not self._frame_queue.empty():
            try:
                self._frame_queue.get_nowait()
            except:
                pass
        while not self._seg_queue.empty():
            try:
                self._seg_queue.get_nowait()
            except:
                pass
        
        # Reset shared state
        self._last_seg_mask = None
        
        self.running = True
        self._display_scheduled = False
        
        if self.start_btn:
            self.start_btn.text = "⏹ Stop"
            self.start_btn.default_bg = COLORS['error']
            self.start_btn.current_bg = COLORS['error']
            self.start_btn._draw()
        
        # Start capture thread (reads camera, feeds both queues)
        # Start capture thread (reads camera, feeds both queues)
        logger.info("🧵 Starting capture thread...")
        threading.Thread(target=self._capture_loop, daemon=True).start()
        
        # Start segmentation thread (processes frames for motor control)
        logger.info("🧵 Starting segmentation thread...")
        threading.Thread(target=self._segmentation_loop, daemon=True).start()
        
        # Start display update loop (runs on main thread via after())
        self._schedule_display_update()
    
    def _stop_camera(self):
        """Stop camera capture"""
        self.running = False
        self._display_scheduled = False
        
        if self.cap:
            self.cap.release()
            self.cap = None
        
        if self.body_segmenter:
            self.body_segmenter.close()
            self.body_segmenter = None
        
        # Clear queues
        while not self._frame_queue.empty():
            try:
                self._frame_queue.get_nowait()
            except:
                pass
        while not self._seg_queue.empty():
            try:
                self._seg_queue.get_nowait()
            except:
                pass
        
        if self.start_btn:
            self.start_btn.text = "▶ Start"
            self.start_btn.default_bg = COLORS['success']
            self.start_btn.current_bg = COLORS['success']
            self.start_btn._draw()
        
        if self.tracking_status:
            self.tracking_status.config(text="Status: Stopped", fg=COLORS['text_secondary'])
        if self.position_label:
            self.position_label.config(text="Position: --", fg=COLORS['text_secondary'])
        
        # Clear canvas
        if self.video_canvas:
            self.video_canvas.delete("all")
            # Draw placeholder
            self.video_canvas.create_text(
                96, 72,
                text="CAMERA OFF", 
                fill=COLORS['text_secondary'],
                font=('Segoe UI', 10, 'bold')
            )
        if hasattr(self, '_canvas_img_id'):
            delattr(self, '_canvas_img_id')
        self._last_imgtk = None
        
        self.video_canvas.create_text(
            self.video_canvas.winfo_width() // 2,
            self.video_canvas.winfo_height() // 2,
            text="Camera Stopped",
            fill=COLORS['text_secondary'],
            font=('Segoe UI', 14)
        )
    
    def _capture_loop(self):
        """
        ZERO-LAG capture loop:
        - Only reads camera and puts frames in queues
        - NO processing here - display and segmentation run in parallel
        - This loop runs as fast as the camera allows
        """
        while self.running and self.cap:
            try:
                if not self.cap.isOpened():
                    break
                ret, frame = self.cap.read()
                if not ret or frame is None:
                    continue
                
                # Flip for mirror effect
                frame = cv2.flip(frame, 1)
                
                # Put frame in DISPLAY queue (always, for smooth video)
                try:
                    # Clear old frame if queue is full (keep only latest)
                    if self._frame_queue.full():
                        try:
                            self._frame_queue.get_nowait()
                        except:
                            pass
                    self._frame_queue.put_nowait(frame.copy())
                except:
                    pass
                
                # Put frame in SEGMENTATION queue (for motor control)
                try:
                    # Clear old frame if queue is full (keep only latest)
                    if self._seg_queue.full():
                        try:
                            self._seg_queue.get_nowait()
                        except:
                            pass
                    self._seg_queue.put_nowait(frame)
                except:
                    pass
                    
            except Exception as e:
                logger.error(f"Capture error: {e}")
    
    def _segmentation_loop(self):
        """
        SEPARATE segmentation thread:
        - Runs body segmentation on frames from queue
        - Updates motors based on segmentation result
        - Doesn't block the display at all
        """
        # Lower threshold for more sensitive detection (0.1% of pixels)
        body_threshold = self.PROC_WIDTH * self.PROC_HEIGHT * 0.001 * 255
        frame_count = 0
        
        while self.running:
            try:
                # Wait for a frame (with timeout to allow clean shutdown)
                try:
                    frame = self._seg_queue.get(timeout=0.1)
                except:
                    continue
                
                if frame is None:
                    continue
                
                frame_count += 1
                h, w = frame.shape[:2]
                
                # Run segmentation
                seg_mask = None
                body_detected = False
                
                if self.body_segmenter:
                    seg_mask = self.body_segmenter.get_body_mask(frame)
                    mask_sum = np.sum(seg_mask)
                    
                    # Debug: print mask sum every 30 frames
                    if frame_count % 30 == 0:
                        logger.debug(f"[SEG] Mask sum: {mask_sum:.0f}, threshold: {body_threshold:.0f}")
                    
                    if mask_sum > body_threshold:
                        body_detected = True
                        
                        # Calculate raw Center of Gravity (average X)
                        coords = np.where(seg_mask > 50)
                        if len(coords[1]) > 0:
                            raw_x = np.mean(coords[1])
                            raw_y = np.mean(coords[0])
                            
                            # Apply Calibration Mapping if available
                            if self.homography is not None:
                                # Transform camera pixels to LED space (0-32, 0-64)
                                lx, ly = self._transform_point(raw_x, raw_y)
                                # Map to 0-1 range within the LED wall
                                self.body_x = max(0, min(1.0, lx / 32.0))
                            else:
                                # Standard mapping (relative to full frame)
                                self.body_x = raw_x / w
                
                # Update shared state for display
                self.body_detected = body_detected
                self._last_seg_mask = seg_mask
                
                # 1. ALWAYS calculate the silhouette for the DETECTION grid
                if seg_mask is not None:
                    mask_8x8 = cv2.resize(seg_mask, (8, 8), interpolation=cv2.INTER_AREA)
                    silhouette = (mask_8x8.flatten() > 50).astype(np.uint8) * 180
                    # Update detection UI independently
                    if hasattr(self, 'on_detection_change') and self.on_detection_change:
                        self.on_detection_change(silhouette.tolist())

                # 2. Calculate Motor Angles based on Mode
                if body_detected and seg_mask is not None:
                    if getattr(self, 'tracking_sync_mode', False):
                        # 🔗 Synchronized Movement Mode
                        # Use the already calculated/transformed self.body_x
                        x_center = self.body_x
                        
                        # Amplified mapping: 
                    else:
                        # 👤 Independent Silhouette Mode
                        # Apply Horizontal Flip to mask if Invert is enabled
                        if getattr(self, 'tracking_invert', False):
                            mask_8x8 = cv2.flip(mask_8x8, 1)
                            
                        motor_angles = (mask_8x8.flatten() > 50).astype(np.uint8) * 180
                        if self.on_angle_change:
                            self.on_angle_change(motor_angles.tolist())
                            
                elif frame_count % 10 == 0: # Idle reset
                    if self.on_angle_change:
                        self.on_angle_change([0] * 64)
                    if hasattr(self, 'on_detection_change') and self.on_detection_change:
                        self.on_detection_change([0] * 64)
                        
            except Exception as e:
                logger.error(f"Segmentation error: {e}")

    def set_tracking_params(self, sync_mode=None, invert=None, smoothing=None):
        """Update tracking engine parameters at runtime"""
        if sync_mode is not None:
            self.tracking_sync_mode = sync_mode
        if invert is not None:
            self.tracking_invert = invert
        if smoothing is not None and self.body_segmenter:
            self.body_segmenter.smoothing = smoothing

    
    def _schedule_display_update(self):
        """Schedule the next display update on main thread"""
        if self.running and not self._display_scheduled:
            self._display_scheduled = True
            # Update display at 30 FPS (33ms) for smooth video
            self.after(33, self._display_update)
    
    def _display_update(self):
        """
        Display update - raw camera feed only, no processing.
        """
        self._display_scheduled = False
        
        if not self.running:
            return
        
        try:
            # Get the LATEST frame only
            frame = None
            while not self._frame_queue.empty():
                try:
                    frame = self._frame_queue.get_nowait()
                except:
                    break
            
            if frame is not None:
                # Overlay segmentation mask as translucent cyan highlight
                seg_mask = self._last_seg_mask
                if seg_mask is not None:
                    try:
                        h, w = frame.shape[:2]
                        mask_resized = cv2.resize(seg_mask, (w, h), interpolation=cv2.INTER_NEAREST)
                        # Create cyan overlay where body is detected
                        overlay = frame.copy()
                        body_pixels = mask_resized > 50
                        overlay[body_pixels] = (
                            overlay[body_pixels] * 0.6 + 
                            np.array([180, 60, 0], dtype=np.uint8) * 0.4  # Cyan tint (BGR)
                        ).astype(np.uint8)
                        frame = overlay
                    except Exception:
                        pass  # Silently skip overlay on error
                
                # Add "BODY" indicator when detected
                if self.body_detected:
                    cv2.putText(frame, "BODY", (10, 20),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                
                self._render_frame(frame)
                self._update_tracking_ui_fast(self.body_detected)
                
                # External callback for LED processing
                if self.on_frame_ready:
                    self.on_frame_ready(frame)
                    
                # Overlay calibration points if active
                if self._calib_points:
                    for i, (px, py) in enumerate(self._calib_points):
                        # px, py are 0-1 normalized
                        cv2.circle(frame, (int(px*w), int(py*h)), 4, (0, 255, 255), -1)
                        cv2.putText(frame, str(i+1), (int(px*w)+5, int(py*h)-5), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
                    
                    if len(self._calib_points) == 4:
                        pts = np.array([[int(p[0]*w), int(p[1]*h)] for p in self._calib_points])
                        cv2.polylines(frame, [pts], True, (0, 255, 255), 2)
                
                self._render_frame(frame)
        
        except Exception as e:
            logger.error(f"Display error: {e}")
        
        # Schedule next update
        if self.running:
            self._display_scheduled = True
            self.after(33, self._display_update)
    
    def _render_frame(self, frame):
        """Render a frame to the canvas (ultra-optimized)"""
        try:
            canvas_w = self.video_canvas.winfo_width()
            canvas_h = self.video_canvas.winfo_height()
            
            if canvas_w < 10 or canvas_h < 10:
                return
            
            frame_h, frame_w = frame.shape[:2]
            
            # Calculate scale
            scale = min(canvas_w / frame_w, canvas_h / frame_h)
            new_w = int(frame_w * scale)
            new_h = int(frame_h * scale)
            
            # Resize if needed
            if new_w != frame_w or new_h != frame_h:
                display = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_NEAREST)
            else:
                display = frame
            
            # BGR to RGB
            rgb = cv2.cvtColor(display, cv2.COLOR_BGR2RGB)
            
            # Create PhotoImage
            im = Image.fromarray(rgb)
            imgtk = ImageTk.PhotoImage(image=im)
            
            # Update canvas
            if hasattr(self, '_canvas_img_id'):
                self.video_canvas.itemconfig(self._canvas_img_id, image=imgtk)
            else:
                self._canvas_img_id = self.video_canvas.create_image(
                    canvas_w // 2, canvas_h // 2, image=imgtk, anchor='center')
            
            self._last_imgtk = imgtk
            
        except Exception as e:
            print(f"Render error: {e}")
    
    def _update_tracking_ui_fast(self, body_detected):
        """Fast tracking UI update"""
        try:
            if body_detected:
                self.tracking_status.config(text="● Tracking: ON", fg=COLORS['success'])
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
    
    def _update_tracking_ui(self):
        """Legacy method"""
        self._update_tracking_ui_fast(self.body_detected)
    
    def set_calib_points(self, points):
        """Points should be list of (x, y) normalized 0-1"""
        self._calib_points = points

    def _handle_click(self, event):
        """Convert canvas click to normalized image coordinates"""
        if not self.running or not self.on_canvas_click:
            return
            
        cw = self.video_canvas.winfo_width()
        ch = self.video_canvas.winfo_height()
        
        # In _render_frame we center the image
        # We need the scaling factors used there
        frame_w, frame_h = self.PROC_WIDTH, self.PROC_HEIGHT
        scale = min(cw / frame_w, ch / frame_h)
        new_w = frame_w * scale
        new_h = frame_h * scale
        
        offset_x = (cw - new_w) / 2
        offset_y = (ch - new_h) / 2
        
        # Relative to image
        img_x = event.x - offset_x
        img_y = event.y - offset_y
        
        if 0 <= img_x <= new_w and 0 <= img_y <= new_h:
            norm_x = img_x / new_w
            norm_y = img_y / new_h
            self.on_canvas_click(norm_x, norm_y)

    def set_homography(self, matrix):
        """Set the 4x4 homography matrix from VisualVerifier"""
        self.homography = matrix

    def _transform_point(self, x, y):
        """Map camera pixels (x,y) to LED space using homography"""
        # x, y are PROC pixels
        p = np.array([[[x, y]]], dtype=np.float32)
        p_transformed = cv2.perspectiveTransform(p, self.homography)
        return p_transformed[0][0] # Returns [lx, ly]

    def stop(self):
        """Cleanup"""
        self._stop_camera()
