"""
LED Control GUI for ESP32-S3 LED Panels
Provides a graphical interface to test LED patterns
"""
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import queue
import serial
import serial.tools.list_ports
from PIL import Image, ImageTk
import numpy as np
import io

import cv2
import mediapipe as mp
import time
from packages.mirror_core.controllers.led_controller import LEDController
from packages.mirror_core.controllers.motor_controller import MotorController
from packages.mirror_core.simulation.mock_serial import MockSerial

class LEDControlApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ESP32-S3 LED Control (Sim + Tracking)")
        # Position main window - WIDER for Side-by-Side
        self.root.geometry("1400x850+50+50")
        
        self.sim_visualizer = None
        
        # Serial connection
        self.serial_port = None
        self.serial_queue = queue.Queue()
        self.running = True
        
        # Tracking State
        self.tracking_active = False
        self.cap = None
        self.pose = None
        
        # Simulation Mode
        self.sim_modes = ["LED Only", "Motor Only", "Both"]
        self.current_mode = "LED Only"
        
        # Camera
        self.available_cameras = self.detect_cameras()
        self.current_camera_index = 0 if self.available_cameras else None
        
        # Controllers
        self.led_controller = LEDController(width=32, height=64)
        self.motor_controller = MotorController(num_servos=64)
        
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
        self.root.bind('<m>', lambda e: self.disconnect()) # Menu/Reset
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Auto-Start
        self.root.after(1000, self.auto_start)
    
    def auto_start(self):
        """Auto-connect to Simulator and start tracking"""
        try:
            # 1. Select Simulator
            if "SIMULATOR" in self.port_combo['values']:
                self.port_combo.set("SIMULATOR")
                self.connect()
                
            # 2. Start Tracking (Camera 0)
            if self.available_cameras:
                self.cam_combo.set(self.available_cameras[0])
                self.toggle_tracking()
        except:
            pass

    def detect_cameras(self):
        """Detect available cameras"""
        available = []
        for i in range(5):
            try:
                cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
                if cap.isOpened():
                    available.append(i)
                    cap.release()
            except: pass
        return available

    def create_widgets(self):
        # MAIN LAYOUT: Split Left (Controls/Vision) and Right (Simulation)
        main_container = ttk.Frame(self.root, padding="10")
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # --- LEFT PANEL: Controls & Vision ---
        left_panel = ttk.Frame(main_container)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # --- Connection Frame ---
        conn_frame = ttk.LabelFrame(left_panel, text="Connection", padding="10")
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
        
        # --- Camera/Tracking Frame ---
        track_frame = ttk.LabelFrame(left_panel, text="AI Vision Feed", padding="10")
        track_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        controls = ttk.Frame(track_frame)
        controls.pack(fill=tk.X)
        
        # Mode Selection
        ttk.Label(controls, text="Mode:").pack(side=tk.LEFT, padx=5)
        self.mode_combo = ttk.Combobox(controls, values=self.sim_modes, width=12, state="readonly")
        self.mode_combo.set(self.current_mode)
        self.mode_combo.pack(side=tk.LEFT, padx=5)
        self.mode_combo.bind("<<ComboboxSelected>>", self.update_mode)
        
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

        # --- Test Patterns Frame ---
        test_frame = ttk.LabelFrame(left_panel, text="Manual Controls", padding="10")
        test_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(test_frame, text="Clear All", command=lambda: self.send_command('c')).pack(side=tk.LEFT, padx=5)
        
        # --- Log Frame ---
        log_frame = ttk.LabelFrame(left_panel, text="Log", padding="10")
        log_frame.pack(fill=tk.X)
        
        self.log_text = tk.Text(log_frame, height=5, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # --- RIGHT PANEL: Simulator ---
        self.right_panel = ttk.LabelFrame(main_container, text="Simulator", padding="10")
        self.right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        # Placeholder
        self.sim_placeholder = ttk.Label(self.right_panel, text="Connect to SIMULATOR to start")
        self.sim_placeholder.pack(expand=True)
    
    def log(self, message):
        """Add a message to the log"""
        try:
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)
        except: pass
    
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
                # Use RAW mode for Simulator so visualization is simple
                self.led_controller.mapping_mode = 0 
                self.log("LED Mapping: RAW (Simulation)")
            else:
                self.serial_port = serial.Serial(
                    port=port,
                    baudrate=460800,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    timeout=1
                )
                # Use HARDWARE mode for Real Device
                self.led_controller.mapping_mode = 3
                self.log("LED Mapping: HARDWARE (Col Serpentine)")
            
            self.status_var.set(f"Status: Connected to {port}")
            self.connect_btn.config(text="Disconnect")
            self.log(f"Connected to {port}")
            
            # Launch Simulation Visualizer (Embed in Right Panel)
            if port == "SIMULATOR":
                self.launch_simulation()
            
            self.serial_port.reset_input_buffer()
            
        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed to connect to {port}: {e}")
            self.log(f"Error: Failed to connect to {port}")
    
    def disconnect(self):
        if self.tracking_active:
            self.toggle_tracking() # Stop tracking first
        
        if self.serial_port and self.serial_port.is_open:
            self.send_command('c')
            self.serial_port.close()
        
        # Close/Remove Simulation
        self.close_simulation()
        
        self.status_var.set("Status: Disconnected")
        self.connect_btn.config(text="Connect")
        self.log("Disconnected")

    def update_mode(self, event):
        self.current_mode = self.mode_combo.get()
        self.log(f"Mode switched to: {self.current_mode}")
        if self.sim_visualizer:
            self.sim_visualizer.set_mode(self.current_mode)
            
    def launch_simulation(self):
        """Embed the simulation visualizer in the right panel"""
        try:
            from apps.simulation.sim_visualizer import SimulationVisualizer
            
            if self.sim_visualizer:
                return 
            
            # Remove placeholder
            self.sim_placeholder.pack_forget()
            
            # Init Visualizer in Right Panel
            self.sim_visualizer = SimulationVisualizer(self.right_panel)
            # Set initial mode
            self.sim_visualizer.set_mode(self.current_mode)
            
            self.log("Simulation Visualizer started")
            
        except ImportError:
            self.log("Error: Simulation modules not found")
        except Exception as e:
            self.log(f"Error starting simulation: {e}")

    def close_simulation(self):
        if self.sim_visualizer:
             # Logic to destroy sim widgets? 
             # SimulationVisualizer creates widgets in self.root (which is right_panel)
             # Simplest is to destroy children of right_panel
             for widget in self.right_panel.winfo_children():
                 widget.destroy()
             
             self.sim_visualizer = None
             
             # Restore placeholder
             self.sim_placeholder = ttk.Label(self.right_panel, text="Connect to SIMULATOR to start")
             self.sim_placeholder.pack(expand=True)
    
    def send_command(self, command):
        if not self.serial_port or not self.serial_port.is_open:
             if command == 'c': return 
             messagebox.showerror("Error", "Not connected")
             return
        
        try:
            self.serial_port.write((command + '\n').encode('utf-8'))
            self.log(f"Sent: {command}")
        except Exception as e:
            self.log(f"Error sending command: {e}")
            
    def toggle_tracking(self):
        if self.tracking_active:
            self.tracking_active = False
            self.track_btn.config(text="Start Tracking")
            if self.cap:
                self.cap.release()
                self.cap = None
            self.log("Tracking Stopped")
        else:
            # Start
            if not self.serial_port or not self.serial_port.is_open:
                messagebox.showerror("Error", "Connect to Simulator first")
                return
            
            try:
                cam_idx = int(self.cam_combo.get())
            except:
                cam_idx = 0
            
            self.log(f"Starting tracking on camera {cam_idx}...")
            
            # Init MediaPipe with Segmentation (LITE MODEL for Speed)
            mp_pose = mp.solutions.pose
            
            self.pose = mp_pose.Pose(
                min_detection_confidence=0.5, 
                min_tracking_confidence=0.5,
                model_complexity=0, # Lite model for CPU optimization
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
        while self.tracking_active and self.cap.isOpened():
            success, image = self.cap.read()
            if not success:
                continue
            
            # Flip for mirror view
            image = cv2.flip(image, 1)
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Process Pose (including Segmentation)
            # Resize image for faster inference if valid/necessary
            # small_frame = cv2.resize(image_rgb, (320, 240)) # Optional optimization
            results = self.pose.process(image_rgb)
            
            motor_angles = [90] * 64
            led_frame = np.zeros((64, 32, 3), dtype=np.uint8) # Default Black
            
            # --- VISION FEED VISUALIZATION ---
            # Used to debug what the system sees on the screen
            debug_frame = image.copy()
            h, w, _ = debug_frame.shape
            
            # Info Text Setup
            cv2.putText(debug_frame, f"MODE: {self.current_mode.upper()}", (10, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
            
            # --- MOTOR LOGIC ---
            if self.current_mode in ["Motor Only", "Both"] and results.pose_landmarks:
                # 1. MOTOR LOGIC: Body Center X -> Wave Direction
                # Find center of mass (avg of hips or shoulders)
                landmarks = results.pose_landmarks.landmark
                
                # Get average X of hips (more stable than shoulders)
                # 23=left_hip, 24=right_hip
                x_avg = (landmarks[23].x + landmarks[24].x) / 2
                
                # Draw VERTICAL LINE for Motor Tracking
                motor_x = int(x_avg * w)
                cv2.line(debug_frame, (motor_x, 60), (motor_x, h), (0, 0, 255), 2)
                
                # Text Explanation
                info_text = f"MOTORS: Following Body X ({x_avg:.2f})"
                cv2.putText(debug_frame, info_text, (10, 60), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
                
                # Logic: Motors "look" at this X.
                center_idx = int(x_avg * 64)
                
                for i in range(64):
                    # Calculate distance from center (0-64)
                    dist = abs(i - center_idx)
                    
                    # Motor strength based on proximity to body center
                    # Close = Active (180), Far = Inactive (0-90)
                    strength = max(0, 1.0 - (dist / 10.0)) # Width of wave
                    
                    angle = 90 + (strength * 90) # 90..180
                    motor_angles[i] = angle
            else:
                 cv2.putText(debug_frame, "MOTORS: Waiting for Body...", (10, 60), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 1)
            
            # --- LED LOGIC ---
            if self.current_mode in ["LED Only", "Both"] and results.segmentation_mask is not None:
                # 2. LED LOGIC: Full "Fat" Silhouette
                # Use segmentation mask directly
                
                # --- LED MAPPING ---
                mask_resized = cv2.resize(results.segmentation_mask, (32, 64))
                led_pattern = (mask_resized > 0.2).astype(np.uint8) * 255
                led_frame[:, :, 1] = led_pattern # Green Channel
                
                # --- VISUALIZATION OVERLAY ---
                green_overlay = np.zeros_like(debug_frame)
                green_overlay[:, :, 1] = (results.segmentation_mask * 255).astype(np.uint8)
                
                # Add weighted overlay
                cv2.addWeighted(debug_frame, 1.0, green_overlay, 0.5, 0, debug_frame)
                
                # Text Explanation
                cv2.putText(debug_frame, "LEDS: Copying Body Silhouette", (10, 110), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            else:
                 cv2.putText(debug_frame, "LEDS: No Silhouette", (10, 110), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 1)
            
            # --- SEND PACKETS ---
            if self.current_mode in ["Motor Only", "Both"]:
                 self.send_motor_packet(motor_angles)
                 
            if self.current_mode in ["LED Only", "Both"]:
                 self.send_led_packet(led_frame)
            
            # --- UPDATE UI PREVIEW ---
            # Resize for UI
            preview = cv2.resize(debug_frame, (640, 480))
            preview_rgb = cv2.cvtColor(preview, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(preview_rgb)
            imgtk = ImageTk.PhotoImage(image=img)
            
            # Safe UI Update
            self.root.after(0, self.update_video_label, imgtk)
            
            # Limit FPS
            time.sleep(0.04) # ~25 FPS

    def update_video_label(self, imgtk):
        if self.video_label:
            self.video_label.imgtk = imgtk
            self.video_label.configure(image=imgtk)

    def send_motor_packet(self, angles):
        if self.serial_port and self.serial_port.is_open:
            try:
                packet = self.motor_controller.pack_servo_packet(angles)
                self.serial_port.write(packet)
            except:
                pass

    def send_led_packet(self, frame):
        if self.serial_port and self.serial_port.is_open:
             try:
                 packet = self.led_controller.pack_led_packet(frame)
                 self.serial_port.write(packet)
             except:
                 pass

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
             if self.cap: self.cap.release()
             
        self.disconnect()
        self.root.destroy()
    
if __name__ == "__main__":
    root = tk.Tk()
    app = LEDControlApp(root)
    root.mainloop()
