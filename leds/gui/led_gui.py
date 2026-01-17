"""
LED Control GUI for ESP32-S3 LED Panels
Independent GUI for controlling 2048 WS2812B LEDs via body tracking
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
from leds.controllers.led_controller import LEDController
from shared.io.mock_serial import MockSerial


class LEDControlApp:
    """
    LED Control GUI Application
    
    Features:
    - Real-time body tracking with MediaPipe
    - 2048 LED matrix control via ESP32 (32×64)
    - Body silhouette visualization
    - Simulation mode for testing without hardware
    """
    
    def __init__(self, root):
        self.root = root
        self.root.title("LED Control System - ESP32-S3 LED Matrix")
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
        
        # LED Controller
        self.led_controller = LEDController(width=32, height=64, mapping_mode=3)
        
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
        
        # Mapping Mode Selection
        mapping_frame = ttk.LabelFrame(main_container, text="LED Mapping Mode", padding="10")
        mapping_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(mapping_frame, text="Mode:").pack(side=tk.LEFT, padx=5)
        self.mapping_var = tk.StringVar(value="3")
        mapping_combo = ttk.Combobox(mapping_frame, textvariable=self.mapping_var,
                                     values=["0: RAW", "1: Row Split", "2: Column Split", 
                                            "3: Column Serpentine", "4: Custom"],
                                     width=20, state="readonly")
        mapping_combo.pack(side=tk.LEFT, padx=5)
        mapping_combo.bind("<<ComboboxSelected>>", self.update_mapping_mode)
        
        # Camera/Tracking Frame
        track_frame = ttk.LabelFrame(main_container, text="Body Tracking & LED Display", padding="10")
        track_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        controls = ttk.Frame(track_frame)
        controls.pack(fill=tk.X)
        
        ttk.Label(controls, text="Camera:").pack(side=tk.LEFT, padx=5)
        self.cam_combo = ttk.Combobox(controls, values=self.available_cameras, width=5)
        if self.available_cameras:
            self.cam_combo.set(self.available_cameras[0])
        self.cam_combo.pack(side=tk.LEFT, padx=5)
        
        self.track_btn = ttk.Button(controls, text="Start Tracking", command=self.toggle_tracking)
        self.track_btn.pack(side=tk.LEFT, padx=10)
        
        ttk.Label(controls, text="(q=Quit, m=Reset)").pack(side=tk.LEFT, padx=5)
        
        # Video Preview
        self.video_label = ttk.Label(track_frame)
        self.video_label.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Log Frame
        log_frame = ttk.LabelFrame(main_container, text="Log", padding="10")
        log_frame.pack(fill=tk.X)
        
        self.log_text = tk.Text(log_frame, height=5, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
    
    def update_mapping_mode(self, event):
        """Update LED mapping mode"""
        mode_str = self.mapping_var.get()
        mode = int(mode_str.split(':')[0])
        self.led_controller.mapping_mode = mode
        self.log(f"LED Mapping mode changed to: {mode}")
    
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
                self.led_controller.mapping_mode = 0  # RAW for simulation
                self.log("Connected to SIMULATOR (LED Mode)")
            else:
                self.serial_port = serial.Serial(
                    port=port,
                    baudrate=460800,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    timeout=1
                )
                self.led_controller.mapping_mode = 3  # Hardware mode
                self.log(f"Connected to {port} (LED Mode - Hardware Mapping)")
            
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
            self.tracking_active = False
            self.track_btn.config(text="Start Tracking")
            if self.cap:
                self.cap.release()
                self.cap = None
            self.log("Tracking Stopped")
        else:
            if not self.serial_port or not self.serial_port.is_open:
                messagebox.showerror("Error", "Please connect to ESP32 first")
                return
            
            try:
                cam_idx = int(self.cam_combo.get())
            except:
                cam_idx = 0
            
            self.log(f"Starting LED tracking on camera {cam_idx}...")
            
            # Init MediaPipe with Segmentation
            mp_pose = mp.solutions.pose
            self.pose = mp_pose.Pose(
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
                model_complexity=0,
                enable_segmentation=True
            )
            
            self.cap = cv2.VideoCapture(cam_idx, cv2.CAP_DSHOW)
            
            if not self.cap.isOpened():
                self.log("Error: Could not open camera")
                return
            
            self.tracking_active = True
            self.track_btn.config(text="Stop Tracking")
            
            # Start tracking loop
            threading.Thread(target=self.tracking_loop, daemon=True).start()
    
    def tracking_loop(self):
        """Main tracking loop - renders body silhouette on LED matrix"""
        while self.tracking_active and self.cap.isOpened():
            success, image = self.cap.read()
            if not success:
                continue
            
            # Flip for mirror view
            image = cv2.flip(image, 1)
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Process Pose with Segmentation
            results = self.pose.process(image_rgb)
            
            # Render LED frame
            seg_mask = results.segmentation_mask if results.segmentation_mask is not None else None
            led_frame = self.led_controller.render_frame(results, seg_mask)
            
            # Debug visualization
            debug_frame = image.copy()
            h, w, _ = debug_frame.shape
            
            cv2.putText(debug_frame, "LED CONTROL MODE", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # LED Visualization Overlay
            if seg_mask is not None:
                green_overlay = np.zeros_like(debug_frame)
                green_overlay[:, :, 1] = (seg_mask * 255).astype(np.uint8)
                cv2.addWeighted(debug_frame, 1.0, green_overlay, 0.5, 0, debug_frame)
                
                cv2.putText(debug_frame, "LEDS: Displaying Body Silhouette", (10, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            else:
                cv2.putText(debug_frame, "LEDS: Waiting for body detection...", (10, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 1)
            
            # Send LED packet
            self.send_led_packet(led_frame)
            
            # Update UI preview
            preview = cv2.resize(debug_frame, (640, 480))
            preview_rgb = cv2.cvtColor(preview, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(preview_rgb)
            imgtk = ImageTk.PhotoImage(image=img)
            
            self.root.after(0, self.update_video_label, imgtk)
            
            # Limit FPS
            time.sleep(0.04)  # ~25 FPS
    
    def update_video_label(self, imgtk):
        """Update video label in UI thread"""
        if self.video_label:
            self.video_label.imgtk = imgtk
            self.video_label.configure(image=imgtk)
    
    def send_led_packet(self, frame):
        """Send LED frame to ESP32"""
        if self.serial_port and self.serial_port.is_open:
            try:
                packet = self.led_controller.pack_led_packet(frame)
                self.serial_port.write(packet)
            except Exception as e:
                self.log(f"Error sending LED packet: {e}")
    
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
    app = LEDControlApp(root)
    root.mainloop()

