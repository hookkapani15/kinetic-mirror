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
        self.root.geometry("1200x800+50+50")
        
        # Serial connection
        self.serial_port = None
        self.serial_queue = queue.Queue()
        self.running = True
        
        # Tracking State
        self.tracking_active = False
        self.cap = None
        self.pose = None
        
        # Camera
        self.available_cameras = self.detect_cameras()
        self.current_camera_index = 0 if self.available_cameras else None
        
        # Motor Controller
        self.motor_controller = MotorController(num_servos=32)
        
        # UI Image
        self.current_image = None
        
        # Create GUI
        self.create_widgets()
        self.detect_ports()
        
        # Start serial thread
        self.serial_thread = threading.Thread(target=self.serial_worker, daemon=True)
        self.serial_thread.start()
        
        # Start GUI update loop
        self.update_gui()
        
        # Bind Keys
        self.root.bind('<q>', lambda e: self.on_close())
        self.root.bind('<m>', lambda e: self.disconnect())
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def detect_cameras(self):
        """Detect available cameras"""
        available = []
        for i in range(5):
            try:
                cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
                if cap.isOpened():
                    available.append(i)
                    cap.release()
            except:
                pass
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
        
        self.connect_btn = ttk.Button(conn_frame, text="Connect", command=self.toggle_connection)
        self.connect_btn.grid(row=0, column=3, padx=5, pady=5)
        
        self.status_var = tk.StringVar(value="Status: Disconnected")
        ttk.Label(conn_frame, textvariable=self.status_var).grid(row=0, column=4, padx=10, pady=5, sticky=tk.W)
        
        # Camera/Tracking Frame
        track_frame = ttk.LabelFrame(main_container, text="Body Tracking & Motor Control", padding="10")
        track_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        controls = ttk.Frame(track_frame)
        controls.pack(fill=tk.X)
        
        ttk.Label(controls, text="Camera:").pack(side=tk.LEFT, padx=5)
        self.cam_combo = ttk.Combobox(controls, values=self.available_cameras, width=5, state="readonly")
        if self.available_cameras:
            self.cam_combo.set(self.available_cameras[0])
        self.cam_combo.pack(side=tk.LEFT, padx=5)
        
        self.track_btn = ttk.Button(controls, text="Start Tracking", command=self.toggle_tracking)
        self.track_btn.pack(side=tk.LEFT, padx=10)
        
        ttk.Label(controls, text="(q=Quit, m=Reset)").pack(side=tk.LEFT, padx=5)
        
        # Video Preview
        self.video_label = ttk.Label(track_frame, text="Video preview will appear here when tracking starts")
        self.video_label.pack(fill=tk.BOTH, expand=True, pady=10)
        
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
            self.toggle_tracking()
        
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        
        self.status_var.set("Status: Disconnected")
        self.connect_btn.config(text="Connect")
        self.log("Disconnected")
    
    def toggle_tracking(self):
        if self.tracking_active:
            # Stop tracking
            self.tracking_active = False
            self.track_btn.config(text="Start Tracking", state="normal")
            self.cam_combo.config(state="readonly")  # Re-enable camera selection
            if self.cap:
                self.cap.release()
                self.cap = None
            if self.pose:
                self.pose.close()
                self.pose = None
            self.log("Tracking Stopped")
        else:
            # Start tracking - check if already active
            if self.tracking_active:
                self.log("Tracking already active - please stop first")
                return
                
            if not self.serial_port or not self.serial_port.is_open:
                messagebox.showerror("Error", "Please connect to ESP32 first")
                return
            
            try:
                cam_idx = int(self.cam_combo.get())
            except:
                cam_idx = 0
            
            self.log(f"Starting motor tracking on camera {cam_idx}...")
            
            # Stop any existing tracking first
            if self.cap:
                self.cap.release()
            if self.pose:
                self.pose.close()
            
            # Init MediaPipe Pose
            mp_pose = mp.solutions.pose
            self.pose = mp_pose.Pose(
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
                model_complexity=0
            )
            
            self.cap = cv2.VideoCapture(cam_idx, cv2.CAP_DSHOW)
            
            if not self.cap.isOpened():
                self.log(f"Error: Could not open camera {cam_idx}")
                messagebox.showerror("Camera Error", f"Could not open camera {cam_idx}")
                return
            
            self.tracking_active = True
            self.track_btn.config(text="Stop Tracking")
            self.cam_combo.config(state="disabled")  # Disable camera selection while tracking
            
            # Start tracking loop
            threading.Thread(target=self.tracking_loop, daemon=True).start()
    
    def tracking_loop(self):
        """Main tracking loop - calculates motor angles from body position"""
        frame_count = 0
        while self.tracking_active and self.cap and self.cap.isOpened():
            success, image = self.cap.read()
            if not success:
                self.log(f"Warning: Failed to read frame from camera")
                time.sleep(0.1)
                continue
            
            frame_count += 1
            
            # Flip for mirror view
            image = cv2.flip(image, 1)
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Process Pose
            results = self.pose.process(image_rgb)
            
            # Calculate motor angles
            motor_angles = [90] * self.motor_controller.num_servos
            
            # Debug visualization
            debug_frame = image.copy()
            h, w, _ = debug_frame.shape
            
            cv2.putText(debug_frame, "MOTOR CONTROL MODE", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Motor Logic: Body Center X -> Motor Wave
            if results.pose_landmarks:
                landmarks = results.pose_landmarks.landmark
                
                # Get average X of hips (more stable)
                x_avg = (landmarks[23].x + landmarks[24].x) / 2
                
                # Draw vertical line for motor tracking
                motor_x = int(x_avg * w)
                cv2.line(debug_frame, (motor_x, 60), (motor_x, h), (0, 0, 255), 3)
                
                # Calculate motor angles based on body position
                center_idx = int(x_avg * self.motor_controller.num_servos)
                
                for i in range(self.motor_controller.num_servos):
                    dist = abs(i - center_idx)
                    strength = max(0, 1.0 - (dist / 10.0))
                    angle = 90 + (strength * 90)
                    motor_angles[i] = angle
                
                info_text = f"Body X: {x_avg:.2f} | Center Motor: {center_idx}"
                cv2.putText(debug_frame, info_text, (10, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
            else:
                cv2.putText(debug_frame, "Waiting for body detection...", (10, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 1)
            
            # Send motor packet
            self.send_motor_packet(motor_angles)
            
            # Update UI preview (only every few frames to reduce load)
            if frame_count % 2 == 0:  # Update every 2nd frame
                try:
                    preview = cv2.resize(debug_frame, (640, 480))
                    preview_rgb = cv2.cvtColor(preview, cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(preview_rgb)
                    imgtk = ImageTk.PhotoImage(image=img)
                    self.root.after(0, self.update_video_label, imgtk)
                except Exception as e:
                    if frame_count % 30 == 0:  # Log error only occasionally
                        self.log(f"Video update error: {e}")
            
            # Limit FPS
            time.sleep(0.04)  # ~25 FPS
        
        # Cleanup when loop exits
        self.log("Tracking loop ended")
        if self.cap:
            self.cap.release()
            self.cap = None
    
    def update_video_label(self, imgtk):
        """Update video label in UI thread"""
        try:
            if self.video_label and self.tracking_active:
                self.video_label.imgtk = imgtk  # Keep reference to prevent garbage collection
                self.video_label.configure(image=imgtk)
        except Exception as e:
            pass  # Silently ignore if widget is destroyed
    
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
        if self.tracking_active:
            self.tracking_active = False
            if self.cap:
                self.cap.release()
        
        self.disconnect()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = MotorControlApp(root)
    root.mainloop()

