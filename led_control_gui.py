"""
Dance Mirror - LED Control GUI
Real-time body silhouette tracking for LED wall

Camera always runs, LED output controlled by Launch/Stop
"""
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
from packages.mirror_core.controllers.led_controller import LEDController
from packages.mirror_core.simulation.mock_serial import MockSerial


class BodySegmenter:
    """
    Optimized body segmentation for LED wall
    - Clean silhouette extraction
    - Temporal smoothing (reduces flicker)
    - Hole filling (solid body)
    - Edge smoothing
    """
    def __init__(self):
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision as mp_vision
        from pathlib import Path
        import urllib.request
        
        model_path = Path("data/selfie_segmenter.tflite")
        model_path.parent.mkdir(exist_ok=True)
        
        if not model_path.exists():
            print("Downloading segmentation model...")
            url = "https://storage.googleapis.com/mediapipe-models/image_segmenter/selfie_segmenter/float16/latest/selfie_segmenter.tflite"
            urllib.request.urlretrieve(url, model_path)
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
        self.smoothing = 0.25  # Lower = more responsive, Higher = smoother
        
        # Morphology kernels (pre-computed for speed)
        self.kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        self.kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        self.kernel_dilate = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        
    def get_body_mask(self, frame):
        """
        Extract clean body silhouette optimized for LED display
        Returns binary mask (0 or 255)
        """
        self.frame_count += 1
        
        # Convert to RGB for MediaPipe
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        
        # Run segmentation
        timestamp_ms = int(self.frame_count * 33)
        result = self.segmenter.segment_for_video(mp_image, timestamp_ms)
        
        if result.category_mask is None:
            return np.zeros((frame.shape[0], frame.shape[1]), dtype=np.uint8)
        
        # Get raw mask
        mask = result.category_mask.numpy_view()
        mask = (mask > 0).astype(np.float32)
        
        # Temporal smoothing to reduce flicker
        if self.mask_buffer is None:
            self.mask_buffer = mask.copy()
        else:
            # Exponential moving average
            self.mask_buffer = self.smoothing * self.mask_buffer + (1.0 - self.smoothing) * mask
        
        # Threshold to binary (0.4 threshold catches more of the body)
        binary = (self.mask_buffer > 0.4).astype(np.uint8) * 255
        
        # === MORPHOLOGY PIPELINE FOR CLEAN SILHOUETTE ===
        
        # 1. Close: Fill small holes inside body
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, self.kernel_close)
        
        # 2. Fill ALL holes inside contours (solid body)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            # Keep only largest contour (the person)
            largest = max(contours, key=cv2.contourArea)
            binary = np.zeros_like(binary)
            cv2.drawContours(binary, [largest], -1, 255, cv2.FILLED)
        
        # 3. Open: Remove small noise/artifacts
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, self.kernel_open)
        
        # 4. Slight dilation to ensure full body coverage
        binary = cv2.dilate(binary, self.kernel_dilate, iterations=1)
        
        # 5. Gaussian blur + threshold for smooth edges
        binary = cv2.GaussianBlur(binary, (5, 5), 0)
        binary = (binary > 128).astype(np.uint8) * 255
        
        return binary
    
    def get_led_mask(self, frame, led_width=32, led_height=64):
        """
        Get body mask directly resized for LED matrix
        Optimized single-call for LED output
        """
        # Get full resolution mask
        body_mask = self.get_body_mask(frame)
        
        # Resize to LED dimensions with area interpolation (best for downscaling)
        led_mask = cv2.resize(body_mask, (led_width, led_height), interpolation=cv2.INTER_AREA)
        
        # Final threshold to ensure clean binary
        led_mask = (led_mask > 128).astype(np.uint8) * 255
        
        return led_mask
    
    def close(self):
        self.segmenter.close()


class LEDSimulatorPanel:
    """Embedded LED Simulator display"""
    def __init__(self, parent):
        self.parent = parent
        self.led_state = [0] * 2048
        
        self.pixel_size = 6
        self.canvas = tk.Canvas(parent, width=32*6, height=64*6, bg="black")
        self.canvas.pack(pady=10, expand=True)
        self._update_loop()
    
    def update_leds(self, led_data):
        if led_data and len(led_data) == 2048:
            self.led_state = list(led_data)
    
    def clear(self):
        self.led_state = [0] * 2048
    
    def _update_loop(self):
        try:
            self.canvas.delete("all")
            for i, b in enumerate(self.led_state):
                if b > 5:
                    x, y = i % 32, i // 32
                    if y >= 64: break
                    c = int(min(255, max(0, b)))
                    color = f"#{c:02x}{c:02x}{c:02x}"
                    x1, y1 = x * self.pixel_size, y * self.pixel_size
                    self.canvas.create_rectangle(x1, y1, x1+5, y1+5, fill=color, outline="")
        except: pass
        self.parent.after(33, self._update_loop)


class LEDControlApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Dance Mirror")
        self.root.geometry("1100x650+50+50")
        
        # State
        self.running = True
        self.camera_running = False
        self.led_output_active = False
        self.serial_port = None
        self.cap = None
        self.body_segmenter = None
        
        # LED Controller
        self.led_controller = LEDController(width=32, height=64)
        
        # Detect hardware
        self.available_cameras = self._detect_cameras()
        self.available_ports = self._detect_ports()
        
        # Build UI
        self._create_ui()
        
        # Auto-start camera
        self.root.after(500, self._start_camera)
        
        # Cleanup on close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _detect_cameras(self):
        """Find available cameras"""
        cameras = []
        for i in range(5):
            try:
                cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
                if cap.isOpened():
                    ret, _ = cap.read()
                    if ret:
                        cameras.append(i)
                    cap.release()
            except: pass
        return cameras if cameras else [0]

    def _detect_ports(self):
        """Find serial ports"""
        ports = [p.device for p in serial.tools.list_ports.comports()]
        ports.append("SIMULATOR")
        return ports

    def _create_ui(self):
        """Build the UI"""
        main = ttk.Frame(self.root, padding="10")
        main.pack(fill=tk.BOTH, expand=True)
        
        # === LEFT: Controls + Camera ===
        left = ttk.Frame(main)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0,10))
        
        # --- Launch Controls (single row) ---
        ctrl_frame = ttk.LabelFrame(left, text="Launch Controls", padding="10")
        ctrl_frame.pack(fill=tk.X, pady=(0,10))
        
        # Port
        ttk.Label(ctrl_frame, text="Port:").pack(side=tk.LEFT, padx=(0,5))
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(ctrl_frame, textvariable=self.port_var, width=12, values=self.available_ports)
        self.port_combo.set("SIMULATOR" if "SIMULATOR" in self.available_ports else self.available_ports[0])
        self.port_combo.pack(side=tk.LEFT, padx=(0,15))
        
        # Camera
        ttk.Label(ctrl_frame, text="Camera:").pack(side=tk.LEFT, padx=(0,5))
        self.cam_var = tk.StringVar()
        self.cam_combo = ttk.Combobox(ctrl_frame, textvariable=self.cam_var, width=5, values=self.available_cameras)
        self.cam_combo.set(self.available_cameras[0])
        self.cam_combo.pack(side=tk.LEFT, padx=(0,15))
        
        # Launch Button
        self.launch_btn = ttk.Button(ctrl_frame, text="▶ LAUNCH", command=self._toggle_output, width=12)
        self.launch_btn.pack(side=tk.LEFT, padx=(0,10))
        
        # Status
        self.status_var = tk.StringVar(value="Ready")
        self.status_label = ttk.Label(ctrl_frame, textvariable=self.status_var, foreground="gray")
        self.status_label.pack(side=tk.LEFT, padx=10)
        
        # --- Camera Feed ---
        cam_frame = ttk.LabelFrame(left, text="Camera Feed (Always On)", padding="5")
        cam_frame.pack(fill=tk.BOTH, expand=True, pady=(0,10))
        
        self.video_label = ttk.Label(cam_frame, text="Starting camera...")
        self.video_label.pack(fill=tk.BOTH, expand=True)
        
        # --- Log ---
        log_frame = ttk.LabelFrame(left, text="Log", padding="5")
        log_frame.pack(fill=tk.X)
        
        self.log_text = tk.Text(log_frame, height=3, wrap=tk.WORD)
        self.log_text.pack(fill=tk.X)
        
        # === RIGHT: LED Simulator ===
        right = ttk.LabelFrame(main, text="LED Output (32x64)", padding="10")
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        self.led_simulator = LEDSimulatorPanel(right)
        
        self.output_info_var = tk.StringVar(value="Press LAUNCH to start")
        ttk.Label(right, textvariable=self.output_info_var).pack(pady=5)

    def _log(self, msg):
        try:
            self.log_text.insert(tk.END, f"{msg}\n")
            self.log_text.see(tk.END)
            if int(self.log_text.index('end-1c').split('.')[0]) > 30:
                self.log_text.delete('1.0', '2.0')
        except: pass

    def _start_camera(self):
        """Start camera feed (runs continuously)"""
        try:
            cam_idx = int(self.cam_combo.get())
        except:
            cam_idx = 0
        
        self.cap = cv2.VideoCapture(cam_idx, cv2.CAP_DSHOW)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        if not self.cap.isOpened():
            self._log(f"Failed to open camera {cam_idx}")
            return
        
        # Init segmenter
        try:
            self.body_segmenter = BodySegmenter()
            self._log("Segmentation ready")
        except Exception as e:
            self._log(f"Segmenter error: {e}")
            self.body_segmenter = None
        
        self.camera_running = True
        self._log(f"Camera {cam_idx} started")
        
        # Start camera loop
        threading.Thread(target=self._camera_loop, daemon=True).start()

    def _camera_loop(self):
        """Camera processing loop - always runs"""
        while self.running and self.camera_running and self.cap:
            try:
                self.cap.grab()
                ret, frame = self.cap.retrieve()
                if not ret:
                    continue
                
                frame = cv2.flip(frame, 1)  # Mirror
                
                # Get body mask (full res for preview)
                if self.body_segmenter:
                    body_mask = self.body_segmenter.get_body_mask(frame)
                    # Get LED-sized mask directly (optimized)
                    led_mask = cv2.resize(body_mask, (32, 64), interpolation=cv2.INTER_AREA)
                    led_mask = (led_mask > 128).astype(np.uint8) * 255
                else:
                    body_mask = np.zeros((frame.shape[0], frame.shape[1]), dtype=np.uint8)
                    led_mask = np.zeros((64, 32), dtype=np.uint8)
                
                # If LED output is active, send to LEDs
                if self.led_output_active:
                    # Update simulator
                    self.led_simulator.update_leds(led_mask.flatten().tolist())
                    
                    # Send to hardware with optimized 1-bit packet
                    if self.serial_port:
                        try:
                            # Use 1-bit packet for ESP32 (8x smaller: 259 bytes vs 2051)
                            packet = self.led_controller.pack_led_packet_1bit(led_mask)
                            self.serial_port.write(packet)
                        except: pass
                
                # Create preview
                preview = frame.copy()
                
                # Overlay body mask in green
                if self.body_segmenter and body_mask is not None:
                    green = np.zeros_like(preview)
                    green[:, :, 1] = body_mask
                    cv2.addWeighted(preview, 0.7, green, 0.4, 0, preview)
                    
                    # Draw contours
                    contours, _ = cv2.findContours(body_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    cv2.drawContours(preview, contours, -1, (0, 255, 0), 2)
                
                # Status text
                status = "● LIVE" if self.led_output_active else "○ STANDBY"
                color = (0, 255, 0) if self.led_output_active else (128, 128, 128)
                cv2.putText(preview, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
                
                # Update UI
                preview_small = cv2.resize(preview, (480, 360))
                preview_rgb = cv2.cvtColor(preview_small, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(preview_rgb)
                imgtk = ImageTk.PhotoImage(image=img)
                self.root.after(0, self._update_video, imgtk)
                
            except Exception as e:
                pass

    def _update_video(self, imgtk):
        try:
            self.video_label.imgtk = imgtk
            self.video_label.configure(image=imgtk)
        except: pass

    def _toggle_output(self):
        """Toggle LED output on/off"""
        if self.led_output_active:
            self._stop_output()
        else:
            self._start_output()

    def _start_output(self):
        """Start LED output - with handshake verification for COM ports"""
        port = self.port_var.get()
        
        try:
            if port == "SIMULATOR":
                self.serial_port = MockSerial(port=port, baudrate=460800)
                self.led_controller.mapping_mode = 0
                self._log("Connected: SIMULATOR")
            else:
                # Connect to real COM port
                self.status_var.set(f"Connecting to {port}...")
                self.root.update()
                
                ser = serial.Serial(
                    port=port, baudrate=460800,
                    bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE, timeout=2
                )
                
                # Wait for ESP32 to boot (if just connected)
                time.sleep(0.5)
                ser.reset_input_buffer()
                
                # Send PING packet to verify connection
                self._log(f"Verifying ESP32 on {port}...")
                ping_packet = bytes([0xAA, 0xBB, 0x05])  # Header + PING type
                ser.write(ping_packet)
                ser.flush()
                
                # Wait for PONG response
                response = ""
                start_time = time.time()
                while time.time() - start_time < 2.0:
                    if ser.in_waiting > 0:
                        data = ser.readline().decode('utf-8', errors='ignore').strip()
                        self._log(f"ESP32: {data}")
                        if "PONG" in data:
                            response = data
                            break
                        response += data
                    time.sleep(0.05)
                
                if "PONG" not in response:
                    ser.close()
                    self._log(f"No response from ESP32 (got: '{response}')")
                    messagebox.showerror("Connection Failed", 
                        f"ESP32 not responding on {port}.\n\n"
                        "Check:\n"
                        "• Is the ESP32-S3 powered on?\n"
                        "• Is the correct COM port selected?\n"
                        "• Is the firmware flashed?")
                    self.status_var.set("Connection failed")
                    return
                
                self._log(f"ESP32 verified on {port}")
                self.serial_port = ser
                self.led_controller.mapping_mode = 3
                self._log(f"Connected: {port}")
            
            self.serial_port.reset_input_buffer()
            self.led_output_active = True
            
            self.launch_btn.config(text="■ STOP")
            self.status_var.set(f"LIVE → {port}")
            self.status_label.config(foreground="green")
            self.output_info_var.set(f"Outputting to {port}")
            
            # Disable port/camera selection while active
            self.port_combo.config(state="disabled")
            self.cam_combo.config(state="disabled")
            
        except serial.SerialException as e:
            messagebox.showerror("Serial Error", f"Cannot open {port}:\n{e}")
            self._log(f"Serial error: {e}")
            self.status_var.set("Error")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to connect: {e}")
            self._log(f"Error: {e}")
            self.status_var.set("Error")

    def _stop_output(self):
        """Stop LED output"""
        self.led_output_active = False
        
        # Clear LEDs
        self.led_simulator.clear()
        
        # Close serial
        if self.serial_port:
            try:
                # Send black frame
                frame = np.zeros((64, 32, 3), dtype=np.uint8)
                packet = self.led_controller.pack_led_packet(frame)
                self.serial_port.write(packet)
                self.serial_port.close()
            except: pass
            self.serial_port = None
        
        self.launch_btn.config(text="▶ LAUNCH")
        self.status_var.set("Ready")
        self.status_label.config(foreground="gray")
        self.output_info_var.set("Press LAUNCH to start")
        
        # Re-enable selection
        self.port_combo.config(state="normal")
        self.cam_combo.config(state="normal")
        
        self._log("Output stopped")

    def _on_close(self):
        """Clean shutdown"""
        self.running = False
        self.camera_running = False
        self.led_output_active = False
        
        if self.body_segmenter:
            try: self.body_segmenter.close()
            except: pass
        
        if self.cap:
            try: self.cap.release()
            except: pass
        
        if self.serial_port:
            try: self.serial_port.close()
            except: pass
        
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = LEDControlApp(root)
    root.mainloop()
