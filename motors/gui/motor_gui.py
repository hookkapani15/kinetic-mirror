"""
Motor Control GUI for ESP32-S3 Servo Motors
Independent GUI for controlling 32 servo motors via body tracking
"""
import sys
import os
# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import queue
import serial
import serial.tools.list_ports
from PIL import Image, ImageTk
import numpy as np
import cv2
import mediapipe as mp

# Try different MediaPipe imports for compatibility
try:
    mp_pose = mp.solutions.pose
except AttributeError:
    try:
        mp_pose = mp.Pose
    except AttributeError:
        mp_pose = None
        print("MediaPipe Pose not available")
import time

# Import from organized structure
from motors.controllers.motor_controller import MotorController
from shared.io.mock_serial import MockSerial


class MotorControlApp:
    """
    Motor Control GUI Application
    
    Features:
    - Real-time body tracking with MediaPipe
    - 32 servo motor control via ESP32
    - Visual feedback and debugging
    - Simulation mode for testing without hardware
    """
    
    def __init__(self, root):
        self.root = root
        self.root.title("Motor Control System - ESP32-S3 Servo Motors")
        
        # Center window on screen
        window_width = 1200
        window_height = 800
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # Make sure window is visible
        self.root.update()
        self.root.deiconify()
        self.root.state('normal')
        
        # Serial connection
        self.serial_port = None
        self.serial_queue = queue.Queue()
        self.running = True
        
        # Tracking State
        self.tracking_active = False
        self.app_running = False
        self.cap = None
        self.pose = None
        
        # Camera
        self.available_cameras = []
        self.current_camera_index = None
        
        # Motor Controller
        self.motor_controller = MotorController(num_servos=64)
        
        # UI Image
        self.current_image = None
        
        # Create GUI (this creates log widget)
        self.create_widgets()
        
        # Detect cameras - do it synchronously now to ensure it works
        print("Starting camera detection...")
        self.log("Detecting cameras...")
        self.root.update()  # Force update to show log message
        self.available_cameras = self.detect_cameras()
        print(f"Camera detection complete. Found: {self.available_cameras}")
        
        # Set camera 1 as default if available, else use first available
        if 1 in self.available_cameras:
            self.current_camera_index = 1
        elif self.available_cameras:
            self.current_camera_index = self.available_cameras[0]
        else:
            self.current_camera_index = 0  # Fallback
        
        # Update camera combo
        if self.available_cameras:
            print(f"Updating camera combo with: {self.available_cameras}")
            self.cam_combo['values'] = self.available_cameras
            self.cam_combo.set(str(self.current_camera_index))
            self.log(f"Camera dropdown updated with: {self.available_cameras}, default: {self.current_camera_index}")
        else:
            print("No cameras found, setting No cameras option")
            self.cam_combo['values'] = ["No cameras"]
            self.cam_combo.set("No cameras")
            self.log("No cameras detected!")
        
        self.detect_ports()
        
        # Start serial thread
        self.serial_thread = threading.Thread(target=self.serial_worker, daemon=True)
        self.serial_thread.start()
        
        # Start GUI update loop
        self.update_gui()
        
        # Initialize motor visualization with default positions
        self.root.after(100, lambda: self.update_motor_visualization([90] * 64))
        
        # Auto-launch the app after 2 seconds if cameras are available
        if self.available_cameras:
            self.log("Auto-launching in 2 seconds...")
            self.root.after(2000, self.toggle_app)
        
        # Bind Keys
        self.root.bind('<q>', lambda e: self.on_close())
        self.root.bind('<m>', lambda e: self.disconnect())
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def detect_cameras(self):
        """Detect available cameras"""
        available = []
        try:
            self.log("=" * 50)
            self.log("Starting camera scan...")
        except:
            print("=" * 50)
            print("Starting camera scan...")
        
        print("Scanning for cameras...")
        
        # Try more cameras and all backends
        max_cameras = 10
        backends = [
            (cv2.CAP_DSHOW, "DirectShow"),
            (cv2.CAP_MSMF, "MSMF"),
            (cv2.CAP_ANY, "Default")
        ]
        
        for i in range(max_cameras):
            camera_found = False
            print(f"  Testing camera index {i}...")
            for backend_id, backend_name in backends:
                cap = None
                try:
                    print(f"    Trying {backend_name}...")
                    cap = cv2.VideoCapture(i, backend_id)
                    
                    if cap.isOpened():
                        print(f"      Opened successfully")
                        # Try to get properties
                        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        
                        # Try to read a frame
                        ret, frame = cap.read()
                        if ret and frame is not None and frame.size > 0:
                            frame_mean = frame.mean()
                            frame_shape = frame.shape
                            
                            print(f"      Frame read: {frame_shape}, mean={frame_mean:.2f}")
                            
                            if frame_mean > 5:  # More lenient threshold
                                if i not in available:
                                    available.append(i)
                                    try:
                                        self.log(f"✓ Camera {i} ({width}x{height}) found with {backend_name}")
                                    except:
                                        print(f"✓ Camera {i} ({width}x{height}) found with {backend_name}")
                                    camera_found = True
                                    break
                            else:
                                try:
                                    self.log(f"Camera {i}: black frame (mean={frame_mean:.2f})")
                                except:
                                    print(f"        Black frame")
                        else:
                            print(f"      Failed to read frame")
                        
                        cap.release()
                        cap = None
                    else:
                        print(f"      Failed to open")
                except Exception as e:
                    print(f"      Error: {e}")
                    if cap:
                        try:
                            cap.release()
                        except:
                            pass
                    continue
            
            if not camera_found:
                try:
                    self.log(f"Camera {i}: not accessible")
                except:
                    print(f"  Camera {i}: not accessible")
        
        try:
            if available:
                self.log(f"✓ Found {len(available)} camera(s): {available}")
            else:
                self.log("✗ No cameras found!")
            self.log("=" * 50)
        except:
            pass
        
        print(f"Camera detection complete. Available cameras: {available}")
        return available
    
    def create_widgets(self):
        """Create GUI widgets"""
        main_container = ttk.Frame(self.root, padding="10")
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Connection Frame
        conn_frame = ttk.LabelFrame(main_container, text="Connection", padding="10")
        conn_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(conn_frame, text="Port:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(conn_frame, textvariable=self.port_var, width=20)
        self.port_combo.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Button(conn_frame, text="Refresh", command=self.detect_ports).grid(row=0, column=2, padx=5, pady=5)
        
        self.launch_btn = ttk.Button(conn_frame, text="Launch App", command=self.toggle_app)
        self.launch_btn.grid(row=0, column=3, padx=5, pady=5)
        
        self.status_var = tk.StringVar(value="Status: Stopped")
        ttk.Label(conn_frame, textvariable=self.status_var).grid(row=0, column=4, padx=10, pady=5, sticky=tk.W)
        
        # Camera/Tracking Frame
        track_frame = ttk.LabelFrame(main_container, text="Body Tracking & Motor Control", padding="10")
        track_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        controls = ttk.Frame(track_frame)
        controls.pack(fill=tk.X)
        
        ttk.Label(controls, text="Camera:").pack(side=tk.LEFT, padx=5)
        self.cam_combo = ttk.Combobox(controls, values=[], width=5, state="readonly")
        self.cam_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(controls, text="(q=Quit, m=Reset)").pack(side=tk.LEFT, padx=5)
        
        # Video and Motor Preview Frame
        preview_frame = ttk.Frame(track_frame)
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Camera Preview
        camera_frame = ttk.Frame(preview_frame)
        camera_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        ttk.Label(camera_frame, text="Camera Preview", font=("Arial", 10, "bold")).pack()
        self.video_label = ttk.Label(camera_frame, text="Camera preview will appear here")
        self.video_label.pack(fill=tk.BOTH, expand=True)
        
        # Motor Visualization
        motor_frame = ttk.Frame(preview_frame)
        motor_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        ttk.Label(motor_frame, text="64 Motor Simulation", font=("Arial", 10, "bold")).pack()
        self.motor_canvas = tk.Canvas(motor_frame, width=300, height=480, bg="black")
        self.motor_canvas.pack(fill=tk.BOTH, expand=True)
        
        # Log Frame
        log_frame = ttk.LabelFrame(main_container, text="Log", padding="10")
        log_frame.pack(fill=tk.X)
        
        self.log_text = tk.Text(log_frame, height=5, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
    
    def log(self, message):
        """Add a message to the log"""
        try:
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)
        except:
            pass
    
    def detect_ports(self):
        """Detect available serial ports"""
        ports = [p.device for p in serial.tools.list_ports.comports()]
        ports.append("SIMULATOR")
        self.port_combo['values'] = ports
        if ports:
            self.port_combo.set(ports[0])
    
    def toggle_app(self):
        if self.app_running:
            self.stop_app()
        else:
            self.start_app()
    
    def start_app(self):
        """Launch the app - connect and start tracking"""
        port = self.port_var.get()
        if not port:
            messagebox.showerror("Error", "Please select a port")
            return
        
        try:
            # Connect
            if port == "SIMULATOR":
                self.serial_port = MockSerial(port=port, baudrate=460800)
                self.log("Connected to SIMULATOR (Motor Mode)")
            else:
                self.serial_port = serial.Serial(
                    port=port,
                    baudrate=460800,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    timeout=1
                )
                self.log(f"Connected to {port} (Motor Mode)")
            
            self.status_var.set(f"Status: Running - {port}")
            self.launch_btn.config(text="Stop App")
            self.app_running = True
            self.serial_port.reset_input_buffer()
            
            # Start camera preview immediately
            self.start_camera_preview()
            
            # Start tracking immediately (no delay)
            self.start_tracking()
            
        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed to connect to {port}: {e}")
            self.log(f"Error: Failed to connect to {port}")
    
    def stop_app(self):
        """Stop the app - disconnect and stop tracking"""
        if self.tracking_active:
            self.stop_tracking()
        
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        
        self.status_var.set("Status: Stopped (camera still running)")
        self.launch_btn.config(text="Launch App")
        self.app_running = False
        self.log("App stopped - camera preview continues")
    
    def start_camera_preview(self):
        """Start camera preview without tracking"""
        try:
            cam_idx = int(self.cam_combo.get())
        except:
            cam_idx = 0
        
        self.log(f"Starting camera preview for camera {cam_idx}...")
        
        if self.cap:
            self.cap.release()
        
        # Try different camera backends more thoroughly
        backends = [
            (cv2.CAP_DSHOW, "DirectShow"),
            (cv2.CAP_MSMF, "Microsoft Media Foundation"),
            (cv2.CAP_ANY, "Default")
        ]
        
        camera_opened = False
        for backend_id, backend_name in backends:
            try:
                self.log(f"Trying camera {cam_idx} with {backend_name}...")
                self.cap = cv2.VideoCapture(cam_idx, backend_id)
                
                if self.cap.isOpened():
                    self.log(f"Camera opened with {backend_name}")
                    
                    # Try different resolutions
                    resolutions = [(640, 480), (1280, 720), (320, 240)]
                    for width, height in resolutions:
                        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                        self.cap.set(cv2.CAP_PROP_FPS, 30)
                        
                        # Test multiple frames to ensure stability
                        valid_frames = 0
                        for _ in range(3):
                            ret, frame = self.cap.read()
                            if ret and frame is not None and frame.size > 0:
                                frame_mean = frame.mean()
                                if frame_mean > 10:
                                    valid_frames += 1
                                    if valid_frames >= 2:
                                        self.log(f"Camera {cam_idx} working at {width}x{height} with {backend_name}")
                                        self.log(f"Frame shape: {frame.shape}, Mean: {frame_mean:.2f}")
                                        camera_opened = True
                                        break
                            time.sleep(0.1)
                        
                        if camera_opened:
                            break
                    
                    if camera_opened:
                        break
                    else:
                        self.log(f"Camera {cam_idx} with {backend_name} - no valid frames at any resolution")
                        self.cap.release()
                else:
                    self.log(f"Camera {cam_idx} with {backend_name} - isOpened() returned False")
                    self.cap.release()
            except Exception as e:
                self.log(f"Error with {backend_name}: {e}")
                if self.cap:
                    try:
                        self.cap.release()
                    except:
                        pass
                continue
        
        if camera_opened:
            self.log("Camera preview thread starting...")
            threading.Thread(target=self.camera_preview_loop, daemon=True).start()
        else:
            self.log(f"CRITICAL: Failed to open camera {cam_idx}!")
            messagebox.showerror("Camera Error", 
                f"Failed to open camera {cam_idx}!\n\n"
                f"Common issues:\n"
                f"• Camera not connected\n"
                f"• Another app is using the camera\n"
                f"• No camera permissions\n"
                f"• Driver issues\n\n"
                f"Check the log for detailed error messages.")
    
    
    
    def camera_preview_loop(self):
        """Camera preview loop - shows video without body tracking"""
        frame_count = 0
        consecutive_errors = 0
        
        while self.running and not self.tracking_active:  # Changed from app_running to running
            try:
                if not self.cap or not self.cap.isOpened():
                    self.log("Camera not open in preview loop")
                    time.sleep(0.5)
                    continue
                
                success, image = self.cap.read()
                if not success:
                    consecutive_errors += 1
                    self.log(f"Failed to read frame (error #{consecutive_errors})")
                    time.sleep(0.1)
                    
                    if consecutive_errors > 10:
                        self.log("Too many consecutive errors, stopping preview")
                        break
                    continue
                
                consecutive_errors = 0  # Reset on success
                frame_count += 1
                
                # Check if frame is valid
                if image is None or image.size == 0:
                    self.log("Frame is None or empty")
                    time.sleep(0.1)
                    continue
                
                # Log frame info periodically
                if frame_count % 60 == 0:
                    self.log(f"Camera preview running - frame {frame_count}, shape: {image.shape}, mean: {image.mean():.2f}")
                
                # Flip for mirror view
                image = cv2.flip(image, 1)
                
                # Show preview text
                if self.app_running:
                    cv2.putText(image, "CAMERA PREVIEW", (10, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    
                    cv2.putText(image, "Tracking active...", (10, 60),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                else:
                    cv2.putText(image, "CAMERA PREVIEW", (10, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    
                    cv2.putText(image, "Click Launch App to start tracking", (10, 60),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 1)
                
                # Add frame counter
                cv2.putText(image, f"Frame: {frame_count}", (10, 90),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
                
                # Update UI preview
                try:
                    preview = cv2.resize(image, (640, 480))
                    preview_rgb = cv2.cvtColor(preview, cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(preview_rgb)
                    imgtk = ImageTk.PhotoImage(image=img)
                    self.root.after(0, self.update_video_label, imgtk)
                except Exception as e:
                    self.log(f"Video update error: {e}")
                
                time.sleep(0.04)  # ~25 FPS
                
            except Exception as e:
                self.log(f"Preview loop error: {e}")
                time.sleep(0.1)
        
        self.log("Camera preview loop ended")
    
    def start_tracking(self):
        """Start body tracking"""
        if not self.app_running:
            return
        
        self.log("Starting motor tracking...")
        self.tracking_active = True
        
        # Stop the preview loop and start tracking loop
        time.sleep(0.1)  # Give time for preview loop to stop
        
        # Start tracking loop
        threading.Thread(target=self.tracking_loop, daemon=True).start()
    
    def stop_tracking(self):
        """Stop body tracking"""
        self.tracking_active = False
        if self.pose:
            try:
                self.pose.close()
            except:
                pass
            self.pose = None
        self.log("Tracking stopped")
        
        # Reset motors to neutral position
        self.root.after(100, lambda: self.update_motor_visualization([90] * 64))
    
    def toggle_connection(self):
        if self.serial_port and self.serial_port.is_open:
            self.disconnect()
        else:
            self.connect()
    
    def connect(self):
        port = self.port_var.get()
        if not port:
            messagebox.showerror("Error", "Please select a port")
            return
        
        try:
            if port == "SIMULATOR":
                self.serial_port = MockSerial(port=port, baudrate=460800)
                self.log("Connected to SIMULATOR (Motor Mode)")
            else:
                self.serial_port = serial.Serial(
                    port=port,
                    baudrate=460800,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    timeout=1
                )
                self.log(f"Connected to {port} (Motor Mode)")
            
            self.status_var.set(f"Status: Connected to {port}")
            self.connect_btn.config(text="Disconnect")
            self.serial_port.reset_input_buffer()
            
        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed to connect to {port}: {e}")
            self.log(f"Error: Failed to connect to {port}")
    
    def disconnect(self):
        if self.tracking_active:
            self.stop_tracking()
        
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        
        self.status_var.set("Status: Disconnected")
        self.log("Disconnected")
    
    def toggle_tracking(self):
        # This function is now handled by start_app/stop_app
        pass
    
    def tracking_loop(self):
        """Main tracking loop - calculates motor angles from body position"""
        frame_count = 0
        self.log("Tracking loop started")
        
        # Initialize MediaPipe once
        self.pose = None
        mediapipe_available = False
        
        try:
            if mp_pose is not None:
                self.pose = mp_pose.Pose(
                    min_detection_confidence=0.5,
                    min_tracking_confidence=0.5,
                    model_complexity=0
                )
                mediapipe_available = True
                self.log("MediaPipe Pose initialized successfully")
            else:
                self.log("MediaPipe Pose not available in this version")
        except Exception as mp_init_error:
            self.log(f"MediaPipe not available: {mp_init_error}")
            self.log("Using motion detection fallback")
            mediapipe_available = False
        
        while self.tracking_active and self.app_running:
            try:
                if not self.cap or not self.cap.isOpened():
                    self.log("Camera not available in tracking loop")
                    time.sleep(0.5)
                    continue
                
                success, image = self.cap.read()
                if not success:
                    self.log(f"Warning: Failed to read frame from camera")
                    time.sleep(0.1)
                    continue
                
                frame_count += 1
                
                # Flip for mirror view
                image = cv2.flip(image, 1)
                
                # Initialize motor angles to neutral
                motor_angles = [90] * self.motor_controller.num_servos
                
                # Debug visualization
                debug_frame = image.copy()
                h, w, _ = debug_frame.shape
                
                cv2.putText(debug_frame, "MOTOR CONTROL MODE", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                body_x_normalized = 0.5  # Default center position
                
                # Try MediaPipe Pose if available
                if mediapipe_available and self.pose:
                    try:
                        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                        results = self.pose.process(image_rgb)
                        
                        # Motor Logic: Body Center X -> Motor Wave
                        if hasattr(results, 'pose_landmarks') and results.pose_landmarks:
                            landmarks = results.pose_landmarks.landmark
                            
                            # Get average X of hips (more stable)
                            x_avg = (landmarks[23].x + landmarks[24].x) / 2
                            body_x_normalized = x_avg
                            
                            # Draw vertical line for motor tracking
                            motor_x = int(x_avg * w)
                            cv2.line(debug_frame, (motor_x, 60), (motor_x, h), (0, 0, 255), 3)
                            
                            # Calculate motor angles based on body position
                            # When body moves left (lower x), motors on left move more
                            # When body moves right (higher x), motors on right move more
                            center_idx = int(x_avg * self.motor_controller.num_servos)
                            
                            for i in range(self.motor_controller.num_servos):
                                # Distance from body position
                                dist = abs(i - center_idx)
                                # Strength decreases with distance (0-1)
                                strength = max(0, 1.0 - (dist / 8.0))
                                # Angle: 90 (neutral) + strength * 90 (max movement)
                                angle = 90 + (strength * 90)
                                motor_angles[i] = angle
                            
                            info_text = f"Body X: {x_avg:.2f} | Center Motor: {center_idx}"
                            cv2.putText(debug_frame, info_text, (10, 60),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
                        else:
                            cv2.putText(debug_frame, "Waiting for body detection...", (10, 60),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 1)
                            # Default to center when no body
                            motor_angles = [90] * self.motor_controller.num_servos
                    except Exception as mp_process_error:
                        if frame_count % 60 == 0:
                            self.log(f"MediaPipe processing error: {mp_process_error}")
                        motor_angles = [90] * self.motor_controller.num_servos
                else:
                    # Fallback: Use motion detection or center position
                    cv2.putText(debug_frame, "Using center position (no MediaPipe)", (10, 60),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
                    
                    # Simple center-based wave
                    body_x_normalized = 0.5
                    center_idx = int(0.5 * self.motor_controller.num_servos)
                    
                    for i in range(self.motor_controller.num_servos):
                        dist = abs(i - center_idx)
                        strength = max(0, 1.0 - (dist / 15.0))
                        angle = 90 + (strength * 90)
                        motor_angles[i] = angle
                
                # Send motor packet
                self.send_motor_packet(motor_angles)
                
                # Update motor visualization
                self.root.after(0, self.update_motor_visualization, motor_angles)
                
                # Update UI preview
                if frame_count % 2 == 0:  # Update every 2nd frame
                    try:
                        preview = cv2.resize(debug_frame, (640, 480))
                        preview_rgb = cv2.cvtColor(preview, cv2.COLOR_BGR2RGB)
                        img = Image.fromarray(preview_rgb)
                        img = Image.fromarray(preview_rgb)
                        imgtk = ImageTk.PhotoImage(image=img)
                        self.root.after(0, self.update_video_label, imgtk)
                    except Exception as e:
                        if frame_count % 60 == 0:  # Log error only occasionally
                            self.log(f"Video update error: {e}")
                
                # Limit FPS
                time.sleep(0.04)  # ~25 FPS
                
            except Exception as e:
                self.log(f"Tracking loop error: {e}")
                time.sleep(0.1)
        
        # Cleanup when loop exits
        self.log("Tracking loop ended")
        if self.pose:
            try:
                self.pose.close()
            except:
                pass
            self.pose = None
    
    def update_video_label(self, imgtk):
        """Update video label in UI thread"""
        try:
            if self.video_label and self.app_running:
                self.video_label.imgtk = imgtk  # Keep reference to prevent garbage collection
                self.video_label.configure(image=imgtk)
        except Exception as e:
            pass  # Silently ignore if widget is destroyed
    
    def update_motor_visualization(self, motor_angles):
        """Update motor position visualization - realistic SG90 servos"""
        try:
            if not hasattr(self, 'motor_canvas') or not self.motor_canvas:
                return
            
            self.motor_canvas.delete("all")
            
            # Draw motor positions
            canvas_width = 300
            canvas_height = 480
            num_motors = len(motor_angles)
            
            # Layout: 4 rows of 16 motors (2x8 grid pattern)
            rows = 4
            cols_per_row = 16
            motors_per_row = num_motors // rows
            
            # Calculate grid spacing
            padding = 10
            available_width = canvas_width - 2 * padding
            available_height = canvas_height - 2 * padding - 30
            
            motor_radius = 8
            col_spacing = available_width / cols_per_row
            row_spacing = available_height / rows
            
            for i, angle in enumerate(motor_angles):
                # Calculate grid position
                row = i // motors_per_row
                col_in_row = i % motors_per_row
                
                # Calculate x position (alternate rows for 2x8 pattern)
                row_offset = col_in_row // 8  # 0 or 1 for the two 8-motor sections
                col_in_section = col_in_row % 8
                
                base_x = padding + row_offset * (col_spacing * 8) + col_in_section * col_spacing + col_spacing/2
                base_y = 40 + row * row_spacing + row_spacing/2
                
                # Draw SG90 servo body (round, black/gray)
                self.motor_canvas.create_oval(
                    base_x - motor_radius, base_y - motor_radius,
                    base_x + motor_radius, base_y + motor_radius,
                    fill="#333333", outline="#666666", width=1
                )
                
                # Draw mounting tabs (small rectangles on sides)
                self.motor_canvas.create_rectangle(
                    base_x - motor_radius - 3, base_y - 4,
                    base_x - motor_radius, base_y + 4,
                    fill="#666666", outline=""
                )
                self.motor_canvas.create_rectangle(
                    base_x + motor_radius, base_y - 4,
                    base_x + motor_radius + 3, base_y + 4,
                    fill="#666666", outline=""
                )
                
                # Draw servo horn (white/blue arm) - position based on angle
                horn_length = motor_radius + 5
                # Convert angle (0-180) to radians for arm rotation
                rad = np.radians(angle - 90)  # -90 to +90 degrees for visual range
                
                horn_end_x = base_x + horn_length * np.cos(rad)
                horn_end_y = base_y + horn_length * np.sin(rad)
                
                # Draw horn line
                self.motor_canvas.create_line(
                    base_x, base_y, horn_end_x, horn_end_y,
                    fill="#FFFFFF", width=3
                )
                
                # Draw horn circle at end
                self.motor_canvas.create_oval(
                    horn_end_x - 3, horn_end_y - 3,
                    horn_end_x + 3, horn_end_y + 3,
                    fill="#FFFFFF", outline="#CCCCCC"
                )
                
                # Draw motor number (small, below motor)
                if i % 2 == 0:
                    self.motor_canvas.create_text(
                        base_x, base_y + motor_radius + 8,
                        text=str(i), fill="#AAAAAA", font=("Arial", 6)
                    )
            
            # Draw title
            self.motor_canvas.create_text(
                canvas_width/2, 15,
                text="64 SG90 Servo Motors", fill="white", font=("Arial", 10, "bold")
            )
            
            # Draw angle indicator legend
            legend_y = canvas_height - 25
            self.motor_canvas.create_text(
                canvas_width/2, legend_y,
                text="← 90°  → 180°", fill="#888888", font=("Arial", 7)
            )
        except Exception as e:
            pass  # Silently handle errors to prevent UI freezing
    
    def send_motor_packet(self, angles):
        """Send motor angles to ESP32"""
        if self.serial_port and self.serial_port.is_open:
            try:
                packet = self.motor_controller.pack_servo_packet(angles)
                self.serial_port.write(packet)
            except Exception as e:
                self.log(f"Error sending motor packet: {e}")
    
    def serial_worker(self):
        """Background thread to read from serial port"""
        while self.running:
            if self.serial_port and self.serial_port.is_open:
                try:
                    if self.serial_port.in_waiting > 0:
                        line = self.serial_port.readline().decode('utf-8').strip()
                        if line:
                            self.serial_queue.put(line)
                except:
                    pass
            time.sleep(0.01)
    
    def update_gui(self):
        """Update the GUI with messages from the serial queue"""
        try:
            while True:
                message = self.serial_queue.get_nowait()
                self.log(f"< {message}")
        except queue.Empty:
            pass
        
        # Schedule the next update
        self.root.after(100, self.update_gui)
    
    def on_close(self):
        """Handle window close event"""
        self.running = False
        self.app_running = False
        if self.tracking_active:
            self.tracking_active = False
            if self.pose:
                self.pose.close()
        if self.cap:
            self.cap.release()
        
        self.disconnect()
        self.root.destroy()


if __name__ == "__main__":
    try:
        print("Creating main window...")
        root = tk.Tk()
        print("Main window created")
        
        print("Creating app...")
        app = MotorControlApp(root)
        print("App created")
        
        # Force window to be visible
        print("Making window visible...")
        root.deiconify()
        root.state('normal')
        root.lift()
        root.attributes('-topmost', True)
        root.after(100, lambda: root.attributes('-topmost', False))
        
        print("Starting mainloop...")
        print(f"Window geometry: {root.geometry()}")
        print(f"Window title: {root.title()}")
        
        root.mainloop()
    except Exception as e:
        print(f"Error launching GUI: {e}")
        import traceback
        traceback.print_exc()