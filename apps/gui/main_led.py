"""
LED Matrix Control - High Performance w/ Modern UI
Controls 32x64 LED wall based on camera body tracking
"""
import tkinter as tk
from tkinter import ttk
import time
import threading
import numpy as np
import serial
import os
import sys
import logging
import psutil
import signal
import cv2
import json

# ----------------- PATH SETUP -----------------
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

# ----------------- IMPORTS -----------------
from core.logging_config import setup_logging
from ui.theme import COLORS
from ui.widgets import ModernButton
from ui.visualizers import LEDSimulatorVisualizer
from ui.camera_panel import CameraPanel
from ui.connection_panel import ConnectionPanel
from ui.led_control_panel import LEDControlPanel
from packages.mirror_core.controllers.led_controller import LEDController
from packages.mirror_core.verification.visual_verifier import VisualVerifier

logger = setup_logging()

class LEDApp:
    def __init__(self, root):
        self.root = root
        self.root.configure(bg=COLORS['bg_dark'])
        self.root.title("Kinetic Mirror - LED Control")
        
        # Load settings
        self.settings = self._load_settings()
        disp = self.settings.get("display", {})
        
        self.led_controller = LEDController(
            width=disp.get("width", 32), 
            height=disp.get("height", 64), 
            mapping_mode=disp.get("mapping_mode", 3)
        )
        self.verifier = VisualVerifier(disp.get("width", 32), disp.get("height", 64))
        self.serial_port = None
        self.running = True
        self.frame_id = 0
        self._serial_lock = threading.Lock()
        self._feedback_running = False
        self._feedback_thread = None
        self._latest_packet = None
        self._latest_frame_id = None
        self._max_resend_attempts = 3
        self._resend_attempts = 0
        self._last_failsafe_ts = 0.0
        
        # Heartbeat state
        self._heartbeat_running = False
        self._heartbeat_thread = None
        
        self._terminal_paused = False
        
        # Calibration state
        self._manual_calib_mode = False
        self._manual_calib_pts = []
        
        self._is_capturing = False
        self._diag_dir = os.path.join(project_root, "diagnostics")
        if not os.path.exists(self._diag_dir):
            os.makedirs(self._diag_dir)
        
        self._create_ui()
        
    def _load_settings(self):
        """Load settings from config/settings.json"""
        config_path = os.path.join(project_root, "config", "settings.json")
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
        
        # Fallback defaults
        return {
            "display": {"width": 32, "height": 64, "mapping_mode": 3, "pixel_size": 3},
            "hardware": {"com_port": "COM7", "baud_rate": 115200}
        }
        
    def _create_ui(self):
        # === MAIN: Horizontal PanedWindow (Camera | Controls+Terminal) ===
        main_pane = tk.PanedWindow(self.root, orient='horizontal', bg='#555',
                                   sashwidth=6, sashrelief='raised')
        main_pane.pack(fill='both', expand=True, padx=2, pady=2)
        
        # LEFT PANE: Camera
        self.camera_panel = CameraPanel(main_pane, on_frame_ready=self._on_camera_frame)
        self.camera_panel.on_canvas_click = self._on_camera_click 
        main_pane.add(self.camera_panel, stretch='always', minsize=200)
        
        # RIGHT PANE: Vertical PanedWindow (Controls | Terminal)
        right_pane = tk.PanedWindow(main_pane, orient='vertical', bg='#555',
                                     sashwidth=6, sashrelief='raised')
        main_pane.add(right_pane, stretch='always', minsize=300)
        
        # --- RIGHT TOP: Controls (3 resizable sub-panes) ---
        controls_pane = tk.PanedWindow(right_pane, orient='vertical', bg='#444',
                                        sashwidth=5, sashrelief='raised')
        right_pane.add(controls_pane, stretch='always', minsize=200)
        
        # 1. LED Simulator pane
        viz_container = tk.Frame(controls_pane, bg=COLORS['bg_dark'])
        controls_pane.add(viz_container, stretch='always', minsize=100)
        
        # Viz Control Bar
        viz_controls = tk.Frame(viz_container, bg=COLORS['bg_medium'])
        viz_controls.pack(fill='x', side='top')
        
        tk.Label(viz_controls, text="📺 SIMULATOR", bg=COLORS['bg_medium'], fg=COLORS['text_primary'],
                 font=('Segoe UI', 8, 'bold')).pack(side='left', padx=5)
        
        self.viz_live_btn = tk.Button(viz_controls, text="Live", command=lambda: self._set_viz_mode("live"),
                                     bg=COLORS['success'], fg='white', bd=0, font=('Segoe UI', 7), padx=6)
        self.viz_live_btn.pack(side='left', padx=2, pady=2)
        
        self.viz_test_btn = tk.Button(viz_controls, text="Test", command=lambda: self._set_viz_mode("test"),
                                     bg=COLORS['bg_light'], fg='white', bd=0, font=('Segoe UI', 7), padx=6)
        self.viz_test_btn.pack(side='left', padx=2, pady=2)
        
        self.viz_cal_btn = tk.Button(viz_controls, text="Calib", command=lambda: self._set_viz_mode("calib"),
                                     bg=COLORS['bg_light'], fg='white', bd=0, font=('Segoe UI', 7), padx=6)
        self.viz_cal_btn.pack(side='left', padx=2, pady=2)

        # Resizing buttons
        tk.Label(viz_controls, text="|", bg=COLORS['bg_medium'], fg=COLORS['text_secondary']).pack(side='left', padx=2)
        
        for size_lbl, size_val in [("1/3", 0.33), ("2/3", 0.66), ("Full", 1.0)]:
            tk.Button(viz_controls, text=size_lbl, command=lambda s=size_val: self._resize_simulator(s),
                     bg='#333', fg='white', bd=0, font=('Segoe UI', 7), padx=4).pack(side='left', padx=1)

        viz_frame = tk.Frame(viz_container, bg='black')
        viz_frame.pack(expand=True, fill='both')
        self.led_viz = LEDSimulatorVisualizer(viz_frame, width=32, height=64, pixel_size=3)
        self.led_viz.pack(expand=True, fill='both')
        self._viz_container = viz_container # Save for resizing reference
        self._viz_mode = "live"

        
        # 2. Patterns / LED Controls pane
        ctrl_frame = tk.Frame(controls_pane, bg=COLORS['bg_medium'])
        controls_pane.add(ctrl_frame, stretch='always', minsize=60)
        self.led_panel = LEDControlPanel(ctrl_frame, on_frame_generated=self._on_test_frame, main_log=self._log)
        self.led_panel.cal_btn.command = self._run_calibration
        self.led_panel.man_btn.command = self._run_manual_calibration
        self.led_panel.on_sequential_step = self._on_sequential_step
        self.led_panel.pack(fill='both', expand=True, padx=3, pady=2)
        
        # 3. Hardware Connection pane
        hw_frame = tk.LabelFrame(controls_pane, text=" Hardware ", bg=COLORS['bg_medium'], fg='white')
        controls_pane.add(hw_frame, stretch='always', minsize=50)
        self.connection_panel = ConnectionPanel(hw_frame, on_connect=self._on_connect, main_log=self._log)
        self.connection_panel.pack(fill='both', expand=True)

        
        # --- RIGHT BOTTOM: Live Terminal ---
        term_frame = tk.Frame(right_pane, bg='#111')
        right_pane.add(term_frame, stretch='always', minsize=150)
        
        # Terminal Header Bar
        term_header = tk.Frame(term_frame, bg='#222')
        term_header.pack(fill='x')
        tk.Label(term_header, text=" > LIVE TERMINAL ", bg='#222', fg='#0f0',
                 font=('Consolas', 10, 'bold')).pack(side='left', padx=5)
        
        # Ping Button
        self.ping_btn = tk.Button(term_header, text="Ping", command=self._send_ping,
                                 bg='#0f3460', fg='white', font=('Segoe UI', 8, 'bold'), bd=0, padx=8, pady=2)
        self.ping_btn.pack(side='left', padx=4, pady=2)

        # Stop Button (Pause)
        self.pause_btn = tk.Button(term_header, text="Stop", command=self._toggle_terminal_pause,
                                  bg='#444', fg='white', font=('Segoe UI', 8, 'bold'), bd=0, padx=8, pady=2)
        self.pause_btn.pack(side='left', padx=4, pady=2)

        # Capture Button
        self.capture_btn = tk.Button(term_header, text="📸 Capture", command=self._start_diagnostic_capture,
                                    bg='#2a9d8f', fg='white', font=('Segoe UI', 8, 'bold'), bd=0, padx=8, pady=2)
        self.capture_btn.pack(side='left', padx=4, pady=2)
        
        # Clear Button
        tk.Button(term_header, text="Clear", command=self._clear_terminal,
                  bg='#444', fg='white', font=('Segoe UI', 8), bd=0, padx=8, pady=2).pack(side='right', padx=4, pady=2)

        # Terminal Text Area
        self.log_text = tk.Text(term_frame, bg='#000', fg='#0f0', font=('Consolas', 10), 
                               state='disabled', insertbackground='white')
        self.log_text.pack(fill='both', expand=True, padx=2, pady=2)

    def _clear_terminal(self):
        self.log_text.config(state='normal')
        self.log_text.delete('1.0', 'end')
        self.log_text.config(state='disabled')

    def _log(self, msg):
        try:
            timestamp = time.strftime("%H:%M:%S")
            logger.info(msg) # Always log to disk
            
            if self._terminal_paused:
                return # Don't update UI if paused
                
            self.log_text.config(state='normal')
            self.log_text.insert('end', f"[{timestamp}] {msg}\n")
            self.log_text.see('end')
            self.log_text.config(state='disabled')
        except: pass

    def _toggle_terminal_pause(self):
        self._terminal_paused = not self._terminal_paused
        if self._terminal_paused:
            self.pause_btn.config(text="Resume", bg=COLORS['success'])
            self._log("Terminal PAUSED")
        else:
            self.pause_btn.config(text="Stop", bg='#444')
            self._log("Terminal RESUMED")

    def _on_connect(self, port, is_sim):
        self.serial_port = port
        self._log(f"Connected: {port if port else 'SIM'}")
        if self.serial_port is not None:
            self._start_feedback_thread()
            self._start_heartbeat()
            # Send initial ping to verify connection
            self._send_ping()

    def _on_camera_frame(self, frame):
        """Called by CameraPanel when new frame is ready (approx 30fps)"""
        self.last_camera_frame = frame
        
        # Get LED mask from segmenter
        if self.led_panel.test_mode:
            return # Skip body-tracking in test mode, but frame is still saved above
            
        if self.camera_panel.body_segmenter:
            led_mask = self.camera_panel.body_segmenter.get_led_mask(frame)
            self._process_led_frame(led_mask)

    def _on_test_frame(self, frame):
        """Called by LEDControlPanel test patterns"""
        self._process_led_frame(frame)

    def _process_led_frame(self, frame):
        """
        Main Pipeline:
        1. Raw Frame -> Remap for Hardware (Source of Truth)
        2. Update Simulator (Visual Feedback)
        3. Pack & Send (Hardware Control)
        4. Verify (Closed Loop)
        """
        try:
            # 1. REMAP FOR HARDWARE (Single Source of Truth)
            remapped_frame = self.led_controller.remap_for_hardware(frame)
            
            # 2. UPDATE SIMULATOR with the appropriate source
            if self._viz_mode == "test":
                self.led_viz.update_leds(remapped_frame.flatten().tolist())
            
            # 3. SEND TO HARDWARE
            if self.serial_port:
                # Use 1-bit packing (0x03) - compatible with firmware v2.0
                self.frame_id = (self.frame_id + 1) % 65536
                packet = self.led_controller.pack_remapped_led_packet_1bit(remapped_frame)
                if self._safe_serial_write(packet):
                    self._latest_packet = packet
                    self._latest_frame_id = self.frame_id
                    self._resend_attempts = 0
            
            # 4. CLOSED-LOOP VERIFICATION & ADVANCED VIZ
            if self.running and self.camera_panel and self.camera_panel.camera_thread:
                cam_frame = self.camera_panel.camera_thread.last_frame
                if cam_frame is not None:
                    # Verify: Hardware Truth (remapped_frame) vs Observed (cam_frame)
                    metrics = self.verifier.verify_frame(cam_frame, remapped_frame)
                    
                    if metrics:
                        # Display metrics
                        ber = metrics.get('ber', 1.0)
                        if self.led_panel and hasattr(self.led_panel, 'update_ber'):
                            self.led_panel.update_ber(ber)
                        
                        # UPDATE SIMULATOR with physical feedback in Calib/Live modes
                        if self._viz_mode == "calib" and 'warped' in metrics:
                            # Show rectified physical feedback
                            warped = cv2.resize(metrics['warped'], (32, 64))
                            self.led_viz.update_leds(warped.flatten().tolist())
                        elif self._viz_mode == "live":
                            # Show segmented mask logic
                            self.led_viz.update_leds(remapped_frame.flatten().tolist())
                        
                        # Fail-safe Logic
                        if ber > 0.15: # 15% error threshold
                            self._trigger_failsafe(ber)
                            
        except Exception as e:
            # logger.error(f"Frame processing error: {e}")
            pass

    def _set_viz_mode(self, mode):
        self._viz_mode = mode
        # Update button colors
        self.viz_live_btn.config(bg=COLORS['success'] if mode == "live" else COLORS['bg_light'])
        self.viz_test_btn.config(bg=COLORS['accent'] if mode == "test" else COLORS['bg_light'])
        self.viz_cal_btn.config(bg=COLORS['warning'] if mode == "calib" else COLORS['bg_light'])
        
        # Sync with LED panel
        if mode == "live": self.led_panel._set_live_mode()
        elif mode == "test": self.led_panel._set_test_mode()
        
        self._log(f"Simulator mode: {mode.upper()}")

    def _resize_simulator(self, factor):
        """Resize the simulator pane within the controls_pane"""
        try:
            # We target the sash of the controls_pane
            parent = self._viz_container.master # controls_pane
            current_height = parent.winfo_height()
            new_pos = int(current_height * factor)
            # Find the index of the simulator pane (it's the first one)
            parent.sash_place(0, 0, new_pos)
            self._log(f"Simulator resized to {int(factor*100)}%")
        except Exception as e:
            self._log(f"Resize failed: {e}")

    def _trigger_failsafe(self, ber):
        """Called when verification fails (High BER)"""
        if self.frame_id % 30 == 0:
            self._log(f"High Error Rate: {ber*100:.1f}%")
        now = time.time()
        if now - self._last_failsafe_ts > 10.0:
            self._last_failsafe_ts = now
            self._log("Auto-recalibration triggered by failsafe")
            self.root.after(0, self._run_calibration)

    def _run_calibration(self):
        self._log("Starting Auto-Calibration...")
        # 1. Show ALL-WHITE pattern — bright rectangle easy to detect against dark room
        """Standard auto-calibration flow"""
        self._manual_calib_mode = False
        self._manual_calib_pts = []
        self.camera_panel.set_calib_points([])
        
        self._log("Starting AUTO calibration...")
        self._set_viz_mode("calib")
        self.led_panel._run_pattern("calib_white")
        
        # Wait for frame and calibrate
        self.root.after(1000, self._perform_auto_calib)

    def _run_manual_calibration(self):
        """Start interactive manual corner selection"""
        self._manual_calib_mode = True
        self._manual_calib_pts = []
        self.camera_panel.set_calib_points([])
        
        self._log("MANUAL CALIB: Click the 4 corners of the LED wall on the camera feed.")
        self._log("Order: Top-Left -> Top-Right -> Bottom-Right -> Bottom-Left")
        
        self._set_viz_mode("live")
        self.led_panel._run_pattern("calib_white")

    def _on_camera_click(self, x, y):
        """Callback from CameraPanel when user clicks on video"""
        if not self._manual_calib_mode:
            return
            
        # x, y are 0-1 normalized image coordinates
        # CameraPanel PROC is 192x144
        img_x = x * self.camera_panel.PROC_WIDTH
        img_y = y * self.camera_panel.PROC_HEIGHT
        
        self._manual_calib_pts.append((img_x, img_y))
        self.camera_panel.set_calib_points(self._manual_calib_pts)
        
        corner_names = ["Top-Left", "Top-Right", "Bottom-Right", "Bottom-Left"]
        idx = len(self._manual_calib_pts) - 1
        self._log(f"Point {idx+1} ({corner_names[idx]}): {img_x:.1f}, {img_y:.1f}")
        
        if len(self._manual_calib_pts) == 4:
            self._log("All 4 corners selected. Applying calibration...")
            self.verifier.set_calibration_points(self._manual_calib_pts)
            # Pass homography to camera for calibrated tracking
            self.camera_panel.set_homography(self.verifier.homography)
            
            self._manual_calib_mode = False
            self._log("Manual calibration SUCCESS!")
            self._set_viz_mode("calib")

    def _perform_auto_calib(self):
        if hasattr(self, 'last_camera_frame') and self.last_camera_frame is not None:
            rect = self.verifier.auto_calibrate(self.last_camera_frame)
            if rect is not None:
                self._log("Auto-calibration SUCCESS!")
                # Pass homography to camera for calibrated tracking
                if self.verifier.homography is not None:
                    self.camera_panel.set_homography(self.verifier.homography)
            else:
                self._log("Auto-calibration FAILED. Try Manual Calib.")
        else:
            self._log("Error: No camera frame for calibration.")

    def _on_test_frame(self, frame_32x64):
        """Called by LEDControlPanel test patterns"""
        self._process_led_frame(frame_32x64)

    def _start_diagnostic_capture(self):
        """Run sequential test and capture screenshots with countdown.
        
        Flow: Stop any existing sequence → countdown → enable capture_mode
        → restart sequence from step 1 → auto-stop after one pass.
        """
        if self.serial_port is None:
            self._log("❌ ERROR: Please connect to COM port before capturing!")
            return
        
        # Stop any running pattern first
        self.led_panel.scroll_active = False
        self.led_panel.capture_mode = False
            
        self._log("📸 DIAGNOSTIC CAPTURE INITIATED")
        self._log("⚠️ Make sure camera is correctly placed to take screenshots!")
        
        def countdown(count):
            if count > 0:
                self._log(f"Starting in {count}...")
                self.root.after(1000, lambda: countdown(count-1))
            else:
                self._log("🚀 CAPTURE STARTING! (5 steps × 5s each = 25s)")
                self._is_capturing = True
                # Enable capture mode and wire up auto-stop
                self.led_panel.capture_mode = True
                self.led_panel.on_capture_done = self._stop_diagnostic_capture
                # Restart the sequential pattern from step 1
                self.led_panel._run_pattern("sequential")

        countdown(3)

    def _stop_diagnostic_capture(self):
        """Called automatically when the capture loop completes one pass"""
        self._is_capturing = False
        self.led_panel.capture_mode = False
        self.led_panel._set_live_mode()
        self._log("📸 DIAGNOSTIC CAPTURE COMPLETE. Check /diagnostics folder.")

    def _on_sequential_step(self, step_name):
        """Callback from LEDControlPanel sequential test.
        
        In capture mode, the loop has already waited 2s for LED settle
        before calling this, so we can save immediately.
        """
        if self._is_capturing and hasattr(self, 'last_camera_frame') and self.last_camera_frame is not None:
            # Copy the frame to avoid race condition with camera thread
            frame_snapshot = self.last_camera_frame.copy()
            filepath = os.path.join(self._diag_dir, f"{step_name}.jpg")
            cv2.imwrite(filepath, frame_snapshot)
            self._log(f"📷 Saved: {step_name}.jpg")

    def _capture_calibration(self):
        # 2. Capture & Solve
        frame = self.last_camera_frame
        if frame is not None:
            h, w = frame.shape[:2]
            self._log(f"Capturing calibration frame ({w}x{h})...")
            rect = self.verifier.auto_calibrate(frame)
            if rect is not None:
                self._log(f"Calibration SUCCESS! Corners detected: {rect.tolist()}")
            else:
                self._log("Calibration FAILED. Check terminal output for diagnostics.")
        else:
            self._log("No camera frame available.")

    def _start_feedback_thread(self):
        if self._feedback_running:
            return
        self._feedback_running = True
        self._feedback_thread = threading.Thread(target=self._serial_feedback_loop, daemon=True)
        self._feedback_thread.start()

    def _serial_feedback_loop(self):
        """Listen for firmware feedback and retry latest frame on NACK."""
        while self.running and self._feedback_running:
            try:
                ser = self.serial_port
                if ser is None or not getattr(ser, "is_open", False):
                    time.sleep(0.1)
                    continue
                
                waiting = getattr(ser, "in_waiting", 0)
                if waiting <= 0:
                    time.sleep(0.01)
                    continue

                # Read raw bytes first, then try to decode
                raw = ser.read(min(waiting, 512))
                if not raw:
                    continue
                    
                # Try to decode as text lines
                try:
                    text = raw.decode("utf-8", errors="replace")
                    for line in text.splitlines():
                        line = line.strip()
                        if not line:
                            continue
                        # Log all non-empty lines from ESP32
                        self._log(f"ESP32: {line}")
                        
                        if line.startswith("NACK"):
                            self._handle_nack()
                        elif "PONG" in line:
                            self._log("SUCCESS: Two-way communication verified!")
                except Exception:
                    self._log(f"ESP32 raw: {raw.hex()}")
                    
            except (serial.SerialException, OSError) as e:
                self._log(f"Serial error: {e}")
                time.sleep(0.2)
            except Exception as e:
                self._log(f"Feedback error: {e}")
                time.sleep(0.05)

    def _handle_nack(self):
        if self._latest_packet is None or self.serial_port is None:
            return
        if self._resend_attempts >= self._max_resend_attempts:
            return
        self._resend_attempts += 1
        if self._safe_serial_write(self._latest_packet):
            self._log(
                f"NACK received, resent frame {self._latest_frame_id} "
                f"(attempt {self._resend_attempts}/{self._max_resend_attempts})"
            )

    def _start_heartbeat(self):
        """Start the heartbeat thread to keep LEDs alive (v2.0 firmware compatibility)"""
        if self._heartbeat_running:
            return
        self._heartbeat_running = True
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()
        self._log("LED Heartbeat started (100ms)")

    def _send_ping(self):
        """Send a PING packet to the ESP32 to verify two-way link."""
        ser = self.serial_port
        if ser:
            self._log(f"Sending PING [AA BB 05] to {getattr(ser, 'port', '?')}...")
            ok = self._safe_serial_write(bytes([0xAA, 0xBB, 0x05]))
            if ok:
                self._log("PING sent OK. Waiting for PONG...")
                # Also log how many bytes are waiting (diagnostic)
                try:
                    time.sleep(0.1)  # Give firmware time to respond
                    waiting = getattr(ser, 'in_waiting', 0)
                    self._log(f"Bytes waiting from ESP32: {waiting}")
                except: pass
            else:
                self._log("PING FAILED: serial write returned False!")
        else:
            self._log("Cannot ping: no serial port connected.")

    def _heartbeat_loop(self):
        """Continuously resend the latest packet every 100ms to prevent firmware timeout."""
        while self.running and self._heartbeat_running:
            try:
                if self.serial_port and self._latest_packet:
                    self._safe_serial_write(self._latest_packet)
            except Exception:
                pass
            time.sleep(0.1) # 10 FPS heartbeat

    def _safe_serial_write(self, packet):
        ser = self.serial_port
        if ser is None:
            return False
        try:
            with self._serial_lock:
                if not getattr(ser, "is_open", False):
                    return False
                ser.write(packet)
            return True
        except (serial.SerialTimeoutException, serial.SerialException, OSError):
            return False
        except Exception:
            return False
                
    def stop(self):
        self.running = False
        self._feedback_running = False
        self._heartbeat_running = False
        if self.camera_panel: self.camera_panel.stop()
        if self.connection_panel: self.connection_panel.monitor_running = False

def force_close_others():
    """Find and kill other instances of this app to free serial ports/cameras."""
    current_pid = os.getpid()
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # Check if it's a python process running main_led
            if 'python' in proc.info['name'].lower():
                cmdline = proc.info.get('cmdline')
                if cmdline and any('main_led' in arg for arg in cmdline):
                    if proc.info['pid'] != current_pid:
                        print(f"Force closing existing app instance (PID: {proc.info['pid']})")
                        proc.terminate()
                        proc.wait(timeout=3)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
            continue

if __name__ == "__main__":
    force_close_others()
    try:
        root = tk.Tk()
        root.title("Kinetic Mirror - LED Control (v2.1 Terminal Edition)")
        root.geometry("1200x800")
        try:
            root.state('zoomed')
        except: pass
        app = LEDApp(root)
        root.protocol("WM_DELETE_WINDOW", lambda: (app.stop(), root.destroy()))
        root.mainloop()
    except Exception as e:
        import traceback
        print("\n" + "="*50)
        print("CRITICAL STARTUP ERROR:")
        print("="*50)
        traceback.print_exc()
        print("="*50 + "\n")
        # Keep window open if possible, but Exit code 1 is the main signal
        sys.exit(1)
