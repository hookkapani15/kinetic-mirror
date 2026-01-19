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
import time

# Note: Using OpenCV background subtraction for body detection
# MediaPipe solutions API is not available in newer versions for Python 3.12

# Import from organized structure
from leds.controllers.led_controller import LEDController
from shared.io.mock_serial import MockSerial
from apps.simulation.sim_visualizer import SimulationVisualizer


class LEDControlApp:
    """
    LED Control GUI Application
    
    Features:
    - Real-time body tracking with OpenCV background subtraction
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
        self.tracking_starting = False  # Prevents double-click during init
        self.cap = None
        self.pose = None  # Kept for compatibility but not used
        self.bg_subtractor = None  # OpenCV background subtractor
        self.current_camera_index = None
        self.sim_window = None
        self.sim_visualizer = None
        
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
        self.root.bind('<s>', lambda e: self.stop_tracking())
        
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
        print(f"[Camera Detection] Found cameras: {available}")
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
        
        self.start_btn = ttk.Button(controls, text="Start Tracking", command=self.start_tracking)
        self.start_btn.pack(side=tk.LEFT, padx=10)

        self.stop_btn = ttk.Button(controls, text="Stop Tracking", command=self.stop_tracking, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(controls, text="(q=Quit, m=Reset, s=Stop)").pack(side=tk.LEFT, padx=5)
        
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
        port_infos = list(serial.tools.list_ports.comports())
        ports = [p.device for p in port_infos]
        ports.append("SIMULATOR")
        self.port_combo['values'] = ports

        auto_port = self.auto_select_port(port_infos)
        if auto_port:
            self.port_combo.set(auto_port)
            self.log(f"Auto-selected port: {auto_port}")
        else:
            self.port_combo.set("SIMULATOR")
            self.log("Auto-selected SIMULATOR (no hardware port detected)")

    def auto_select_port(self, port_infos):
        """Pick the most likely ESP32 port using known USB bridge keywords"""
        keywords = ("cp210", "ch340", "usb", "silicon", "uart", "esp", "wch", "ftdi", "s3")
        for info in port_infos:
            desc = (info.description or "").lower()
            hwid = (getattr(info, "hwid", "") or "").lower()
            if any(keyword in desc or keyword in hwid for keyword in keywords):
                return info.device
        return port_infos[0].device if port_infos else None
    
    def toggle_connection(self):
        if self.serial_port and self.serial_port.is_open:
            self.disconnect()
        else:
            self.connect()
    
    def connect(self):
        port = self.port_var.get()
        if not port or port not in self.port_combo['values']:
            port_infos = list(serial.tools.list_ports.comports())
            port = self.auto_select_port(port_infos)
            if port:
                self.port_var.set(port)
                self.log(f"Auto-detected port for connection: {port}")
            else:
                self.port_var.set("SIMULATOR")
                port = "SIMULATOR"
                self.log("Falling back to SIMULATOR (no hardware port detected)")

        if not port:
            messagebox.showerror("Error", "Please select a port")
            return
        
        try:
            if port == "SIMULATOR":
                self.serial_port = MockSerial(port=port, baudrate=460800)
                self.led_controller.mapping_mode = 0  # RAW for simulation
                self.log("Connected to SIMULATOR (LED Mode)")
                try:
                    self.open_simulator_visualizer()
                except Exception as viz_err:
                    self.log(f"Warning: Could not open visualizer: {viz_err}")
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
            self.stop_tracking()
        
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        
        self.close_simulator_visualizer()
        self.status_var.set("Status: Disconnected")
        self.connect_btn.config(text="Connect")
        self.log("Disconnected")

    def open_simulator_visualizer(self):
        """Open the simulator visualizer window if not already visible."""
        try:
            if self.sim_window and self.sim_window.winfo_exists():
                self.log("Simulator window already exists")
                return

            self.log("Creating simulator visualizer window...")
            self.sim_window = tk.Toplevel(self.root)
            self.sim_window.title("Virtual ESP32 Visualizer")
            self.sim_window.geometry("800x600+100+100")
            self.sim_window.lift()
            self.sim_window.focus_force()
            self.log("Toplevel window created, initializing visualizer...")
            self.sim_visualizer = SimulationVisualizer(self.sim_window)
            self.log("Simulator visualizer launched successfully")
        except Exception as e:
            self.log(f"ERROR opening simulator: {e}")
            import traceback
            traceback.print_exc()

    def close_simulator_visualizer(self):
        """Close simulator visualizer if open."""
        if self.sim_window and self.sim_window.winfo_exists():
            self.sim_window.destroy()
        self.sim_window = None
        self.sim_visualizer = None
    
    def ensure_connection(self):
        """Ensure a serial connection exists before starting tracking."""
        if self.serial_port and getattr(self.serial_port, "is_open", False):
            return True

        self.log("Serial port not connected. Attempting automatic connection...")
        self.connect()
        if self.serial_port and getattr(self.serial_port, "is_open", False):
            self.log("Serial port connected successfully")
            return True
        self.log("Serial port connection attempt failed")
        return False

    def start_tracking(self):
        if self.tracking_active:
            self.log(f"Tracking already active on camera {self.current_camera_index}")
            return

        if self.tracking_starting:
            self.log("Already starting tracking, please wait...")
            return

        if not self.ensure_connection():
            messagebox.showerror("Error", "Unable to connect to ESP32 or simulator")
            self.log("Start aborted: no active serial connection")
            return

        combo_value = self.cam_combo.get()
        self.log(f"Camera combo value: '{combo_value}'")
        try:
            cam_idx = int(combo_value)
        except:
            cam_idx = 0
            self.log(f"Could not parse camera index, defaulting to 0")

        # Disable buttons immediately and set starting flag
        self.tracking_starting = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.DISABLED)
        self.log(f"Starting LED tracking on camera {cam_idx}...")

        # Run initialization in background thread to avoid blocking UI
        threading.Thread(target=self._init_tracking, args=(cam_idx,), daemon=True).start()

    def _init_tracking(self, cam_idx):
        """Background initialization of camera and OpenCV background subtractor."""
        try:
            self.log("Initializing OpenCV background subtractor...")
            # Use MOG2 background subtractor for body detection
            self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
                history=500,
                varThreshold=50,
                detectShadows=False
            )
            self.log("Background subtractor initialized")

            # Try preferred backend first, then fallback to default if needed
            self.log(f"Opening camera {cam_idx} with DirectShow...")
            self.cap = cv2.VideoCapture(cam_idx, cv2.CAP_DSHOW)
            if not self.cap or not self.cap.isOpened():
                self.log(f"DirectShow failed, trying default backend...")
                if self.cap:
                    self.cap.release()
                self.cap = cv2.VideoCapture(cam_idx)

            if not self.cap or not self.cap.isOpened():
                self.log(f"Error: Could not open camera {cam_idx}")
                if self.cap:
                    self.cap.release()
                self.cap = None
                self.bg_subtractor = None
                self.current_camera_index = None
                self.tracking_starting = False
                self.root.after(0, lambda: self.start_btn.config(state=tk.NORMAL))
                self.root.after(0, lambda: self.stop_btn.config(state=tk.DISABLED))
                return

            # Set camera properties for better performance
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce buffer to minimize latency

            self.current_camera_index = cam_idx
            self.tracking_active = True
            self.tracking_starting = False
            self.root.after(0, lambda: self.start_btn.config(state=tk.DISABLED))
            self.root.after(0, lambda: self.stop_btn.config(state=tk.NORMAL))
            self.log(f"Camera {cam_idx} opened successfully")
            self.log("Tracking thread started")

            # Run tracking loop directly in this thread
            self.tracking_loop()
        except Exception as e:
            self.log(f"Error initializing tracking: {e}")
            self.tracking_starting = False
            self.tracking_active = False
            self.root.after(0, lambda: self.start_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.stop_btn.config(state=tk.DISABLED))

    def stop_tracking(self):
        if not self.tracking_active:
            self.log("Tracking already stopped")
            return

        self.tracking_active = False
        if self.cap:
            self.cap.release()
            self.cap = None
        self.bg_subtractor = None
        self.pose = None
        self.current_camera_index = None
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.log("Tracking Stopped")
    
    def tracking_loop(self):
        """Main tracking loop - renders body silhouette on LED matrix using background subtraction"""
        try:
            while self.tracking_active and self.cap and self.cap.isOpened():
                success, image = self.cap.read()
                if not success:
                    continue

                # Flip for mirror view
                image = cv2.flip(image, 1)
                
                # Apply background subtraction to detect moving objects (person)
                fg_mask = self.bg_subtractor.apply(image)
                
                # Clean up the mask with morphological operations
                kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
                fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)
                fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)
                
                # Additional blur to smooth edges
                fg_mask = cv2.GaussianBlur(fg_mask, (5, 5), 0)
                
                # Threshold to create binary mask
                _, fg_mask = cv2.threshold(fg_mask, 127, 255, cv2.THRESH_BINARY)
                
                # Normalize mask to 0-1 range for LED controller
                seg_mask = fg_mask.astype(np.float32) / 255.0

                # Render LED frame using the segmentation mask
                led_frame = self.led_controller.render_frame(None, seg_mask)

                # Debug visualization
                debug_frame = image.copy()
                h, w, _ = debug_frame.shape

                cv2.putText(debug_frame, "LED CONTROL MODE (OpenCV)", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

                # LED Visualization Overlay - show detected silhouette in green
                if np.any(fg_mask > 0):
                    green_overlay = np.zeros_like(debug_frame)
                    green_overlay[:, :, 1] = fg_mask
                    cv2.addWeighted(debug_frame, 1.0, green_overlay, 0.5, 0, debug_frame)

                    cv2.putText(debug_frame, "LEDS: Displaying Body Silhouette", (10, 60),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                else:
                    cv2.putText(debug_frame, "LEDS: Waiting for movement...", (10, 60),
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
                time.sleep(0.033)  # ~30 FPS

        except Exception as e:
            self.log(f"Tracking error: {e}")
        finally:
            if self.tracking_active:
                self.root.after(0, self.stop_tracking)
    
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

