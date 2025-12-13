#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MIRROR BODY ANIMATIONS - Interactive GUI with Multiple Modes
Modes: R (README), M (Motors), L (LEDs), B (Both), Q (Quit), C (Camera Switch), D (Diagnostics)

Usage:
  python -m apps.gui.main          # Full startup with hardware detection
  python -m apps.gui.main --fast   # Skip startup, use defaults
"""
import cv2
import time
import sys
import serial
import serial.tools.list_ports
import numpy as np
import json
import traceback
import faulthandler
import datetime
import os
from pathlib import Path

# Ensure stdout/stderr can emit UTF-8 (prevents Windows console crashes on emojis)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Repo paths
REPO_ROOT = Path(__file__).resolve().parents[2]
PKG_ROOT = REPO_ROOT / "packages"
LOG_DIR = REPO_ROOT / "logs"
CONFIG_DIR = REPO_ROOT / "config"
CONFIG_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

# Ensure packages on path
sys.path.insert(0, str(PKG_ROOT))

# Initialize MediaPipe (if available)
MEDIAPIPE_AVAILABLE = False
try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
    print("✅ MediaPipe available")
except ImportError:
    mp = None
    MEDIAPIPE_AVAILABLE = False
    print("⚠️ MediaPipe not available - running in demo mode")

# Check for --fast flag to skip startup screen
FAST_MODE = "--fast" in sys.argv or "-f" in sys.argv
print("\n" + "="*60)
print("🚀 MIRROR BODY ANIMATIONS")
print("="*60)

# ═══════════════════════════════════════════════════════════════════════════
# STARTUP - Either full screen or fast mode
# ═══════════════════════════════════════════════════════════════════════════

if FAST_MODE:
    # FAST MODE - Skip startup screen, use defaults
    print("\n⚡ FAST MODE - Skipping startup screen...")
    
    # Load config directly
    config_file = CONFIG_DIR / "config.json"
    if config_file.exists():
        with open(config_file) as f:
            config = json.load(f)
    else:
        config = {
            "serial_port": "AUTO",
            "baud_rate": 460800,
            "camera_index": 1,
            "camera_width": 640,
            "camera_height": 480,
            "led_width": 32,
            "led_height": 64,
            "num_servos": 6,
            "angle_min": 0,
            "angle_max": 180,
        }
    
    startup_result = {
        "esp32_port": config.get("serial_port", "AUTO"),
        "esp32_type": "Unknown",
        "cameras": [0, 1],
        "selected_camera": config.get("camera_index", 1),
        "ready": True,
        "config": config,
    }
    print(f"  Using camera: {startup_result['selected_camera']}")
    print(f"  Serial port: {config.get('serial_port', 'AUTO')}")
else:
    # FULL MODE - Run startup screen with visual detection
    from .startup.startup_screen import run_startup_screen
    startup_result = run_startup_screen()
    
    if startup_result is None:
        print("\n❌ Startup cancelled by user.")
        sys.exit(0)
    
    print(f"\n✓ Startup complete!")
    print(f"  ESP32: {startup_result['esp32_type']} on {startup_result['esp32_port']}")
    print(f"  Camera: {startup_result['selected_camera']}")
    print(f"  Ready: {'Yes' if startup_result['ready'] else 'Partial'}")
    
    # Use startup config
    config = startup_result['config']

# Ensure all required keys exist
config.setdefault("serial_port", "AUTO")
config.setdefault("baud_rate", 460800)
config.setdefault("camera_index", startup_result['selected_camera'])
config.setdefault("camera_width", 640)
config.setdefault("camera_height", 480)
config.setdefault("led_width", 32)
config.setdefault("led_height", 64)
config.setdefault("num_servos", 6)
config.setdefault("angle_min", 0)
config.setdefault("angle_max", 180)

# Import modules after startup (config is ready)
from mirror_core.controllers.motor_controller import MotorController
from mirror_core.controllers.led_controller import LEDController
from mirror_core.io.serial_manager import SerialManager
from mirror_core.tests.system_tests import SystemTester

# Configuration paths
BASE_DIR = Path(__file__).parent
CONFIG_FILE = CONFIG_DIR / "config.json"
HEALTH_LOG = LOG_DIR / "health_log.jsonl"

class MirrorGUI:
    def __init__(self):
        self.mode = "LED_TEST"  # Start in LED test mode to verify panel placement
        self.running = True
        self.camera_index = config['camera_index']
        self.available_cameras = []
        self.session_id = int(time.time())
        HEALTH_LOG.parent.mkdir(exist_ok=True)
        self.health_log_path = HEALTH_LOG
        
        # Rate limiting for serial
        self.last_serial_send_time = 0
        self.serial_min_interval = 0.05  # Max 20 packets per second
        
        # Initialize motor controller (32 servos across 2 PCA9685 boards)
        self.motor = MotorController(num_servos=32)
        print("✅ Motor controller initialized (32 servos)")
        self.led = LEDController(
            width=config['led_width'],
            height=config['led_height']
        )
        self.serial = SerialManager(config['serial_port'], config['baud_rate'])
        self.serial.start()
        
        # Initialize MediaPipe (if available)
        if MEDIAPIPE_AVAILABLE:
            mp_pose = mp.solutions.pose
            self.pose = mp_pose.Pose(
                min_detection_confidence=0.7,
                min_tracking_confidence=0.8,
                model_complexity=0,
                enable_segmentation=True,  # ENABLED for silhouette visualization
                smooth_landmarks=False
            )
        else:
            self.pose = None
            print("⚠️ Running without MediaPipe - demo mode only")
        
        # Camera
        self.cap = None
        self.open_camera(self.camera_index)
        
        # Diagnostics
        self.diagnostic_results = None
        self.running_diagnostics = False
        self.show_diagnostic_overlay = False
        self.diagnostic_overlay_time = 0
        
        # Stats tracking
        self.fps = 0
        self.frame_times = []
        self.last_fps_update = time.time()

        # Health/fault tracking
        self.last_fault = None  # store last exception info
        self.fault_history = []  # collect unexpected scenarios
        self.show_fault_overlay = False
        self.fault_overlay_time = 0

    # ═══════════════════════════════════════════════════════════════
    # Logging helpers
    # ═══════════════════════════════════════════════════════════════
    def log_event(self, kind: str, detail: dict):
        """Append structured event to health log (jsonl)."""
        entry = {
            "ts": datetime.datetime.now().isoformat(timespec='seconds'),
            "session": self.session_id,
            "kind": kind,
            **detail
        }
        try:
            with open(self.health_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            print(f"⚠ log_event failed: {e}")
        
    def open_camera(self, index):
        """Open camera by index"""
        if self.cap:
            self.cap.release()
        
        self.cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, config['camera_width'])
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config['camera_height'])
        self.camera_index = index
        
    def switch_camera(self):
        """Switch to next available camera"""
        # Detect cameras
        if not self.available_cameras:
            print("Detecting cameras...")
            for i in range(6):
                test_cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
                if test_cap.isOpened():
                    ret, _ = test_cap.read()
                    if ret:
                        self.available_cameras.append(i)
                test_cap.release()
        
        if len(self.available_cameras) > 1:
            current_idx = self.available_cameras.index(self.camera_index) if self.camera_index in self.available_cameras else 0
            next_idx = (current_idx + 1) % len(self.available_cameras)
            new_camera = self.available_cameras[next_idx]
            self.open_camera(new_camera)
            print(f"✓ Switched to camera {new_camera}")
        else:
            print("⚠ Only one camera available")
    
    def _generate_numbers_pattern(self):
        """Generate pattern with numbers 1-8 on each panel"""
        pattern = np.zeros((64, 32), dtype=np.uint8)
        
        for panel_id in range(1, 9):
            panel_idx = panel_id - 1
            row = panel_idx // 2
            col = panel_idx % 2
            
            y_start = row * 16
            x_start = col * 16
            
            # Draw number on panel
            panel_img = np.zeros((16, 16),dtype=np.uint8)
            text = str(panel_id)
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.7
            thickness = 2
            
            (text_width, text_height), baseline = cv2.getTextSize(text, font, font_scale, thickness)
            x = (16 - text_width) // 2
            y = (16 + text_height) // 2
            
            cv2.putText(panel_img, text, (x, y), font, font_scale, 255, thickness)
            pattern[y_start:y_start+16, x_start:x_start+16] = panel_img
        
        return pattern
    
    def _generate_human_silhouette(self, position='center'):
        """Generate simple human silhouette"""
        pattern = np.zeros((64, 32), dtype=np.uint8)
        
        if position == 'center':
            x_offset = 8
        elif position == 'left':
            x_offset = 2
        else:  # right
            x_offset = 18
        
        # Simple stick figure
        cv2.circle(pattern, (x_offset + 8, 8), 4, 200, -1)
        cv2.rectangle(pattern, (x_offset + 6, 12), (x_offset + 10, 30), 200, -1)
        cv2.line(pattern, (x_offset + 6, 16), (x_offset + 2, 24), 200, 2)
        cv2.line(pattern, (x_offset + 10, 16), (x_offset + 14, 24), 200, 2)
        cv2.line(pattern, (x_offset + 7, 30), (x_offset + 4, 45), 200, 2)
        cv2.line(pattern, (x_offset + 9, 30), (x_offset + 12, 45), 200, 2)
        
        return pattern
    
    def _generate_wave_pattern(self, offset=0):
        """Generate animated wave"""
        pattern = np.zeros((64, 32), dtype=np.uint8)
        
        for y in range(64):
            for x in range(32):
                wave_x = np.sin((x + offset) * 0.3) * 10 + 32
                wave_y = np.sin(y * 0.2) * 5 + 32
                dist = abs(y - wave_x) + abs(x - wave_y)
                brightness = max(0, 255 - int(dist * 8))
                pattern[y, x] = brightness
        
        return pattern
    
    def _generate_hello_text(self, text='HELLO'):
        """Generate text display pattern"""
        pattern = np.zeros((64, 32), dtype=np.uint8)
        
        font = cv2.FONT_HERSHEY_SIMPLEX
        
        if len(text) == 1:
            # Single letter - large and centered
            font_scale = 2.0
            thickness = 3
        else:
            # Full word - fit to width
            font_scale = 0.8
            thickness = 2
        
        # Get text size
        (text_width, text_height), baseline = cv2.getTextSize(text, font, font_scale, thickness)
        
        # Center text
        x = (32 - text_width) // 2
        y = (64 + text_height) // 2
        
        # Draw white text
        cv2.putText(pattern, text, (x, y), font, font_scale, 255, thickness)
        
        return pattern
    
    def run_diagnostics(self):
        """Run automated diagnostics using strict SystemTester"""
        try:
            self.running_diagnostics = True
            
            print("\n" + "="*70)
            print("🔧 RUNNING STRICT SYSTEM DIAGNOSTICS...")
            print("="*70)
            
            # Use strict system tester
            tester = SystemTester(self.serial)
            success = tester.run_full_suite()
            
            # Populate results for overlay (compatibility)
            self.diagnostic_results = {
                'serial': {'connected': self.serial.connected if self.serial else False},
                'camera': {'connected': self.cap.isOpened() if self.cap else False},
                'mediapipe': {'loaded': self.pose is not None},
                'performance': {'fps': self.fps},
                'system': {
                    'camera_index': self.camera_index,
                    'serial_port': config['serial_port'],
                    'mode': self.mode
                }
            }
            
            self.show_diagnostic_overlay = True
            self.diagnostic_overlay_time = time.time()
            self.running_diagnostics = False
            
            print("\n✓ Diagnostics Complete")
            print("="*70 + "\n")
            return
        except Exception as e:
            print(f"Diagnostics Failed: {e}")
            self.running_diagnostics = False

    def run_diagnostics_legacy(self):
        """Run automated diagnostics - gracefully handles missing hardware"""
        try:
            self.running_diagnostics = True
            results = {}
            
            print("\n" + "="*70)
            print("🔧 RUNNING SYSTEM DIAGNOSTICS...")
            print("="*70)
            
            # Test 1: Serial/Hardware Check
            print("\n[1/5] Serial/Hardware Check...")
            if self.serial and self.serial.ser and self.serial.ser.is_open:
                print("✓ Serial port connected")
                results['serial'] = {'connected': True}
            else:
                print("✗ No ESP32 connected - motors/LEDs won't work")
                results['serial'] = {'connected': False, 'error': 'No hardware connected'}
            
            # Test 2: Camera Detection (use cached info, don't re-scan)
            print("\n[2/5] Camera Detection...")
            try:
                # Use already detected cameras from startup, don't re-scan
                # Re-scanning can interfere with the active camera
                working_cameras = self.available_cameras if self.available_cameras else [self.camera_index]
                results['camera'] = {'working_cameras': working_cameras}
                if working_cameras:
                    print(f"✓ Using {len(working_cameras)} camera(s): {working_cameras}")
                else:
                    print("✗ No cameras found")
            except Exception as e:
                print(f"✗ Camera test failed: {e}")
                results['camera'] = {'error': str(e)}
            
            # Test 3: MediaPipe Performance (quick test)
            print("\n[3/5] MediaPipe Performance (1s)...")
            try:
                # Ensure camera is working
                if not self.cap or not self.cap.isOpened():
                    print("⚠ Camera not available - reopening...")
                    self.open_camera(self.camera_index)
                
                if not self.cap or not self.cap.isOpened():
                    print("⚠ Camera still not available - skipping performance test")
                    results['mediapipe'] = {'error': 'Camera not available'}
                else:
                    # Quick FPS test - just current FPS, don't run a loop
                    avg_fps = self.fps if self.fps > 0 else 15.0  # Use tracked FPS
                    results['mediapipe'] = {'avg_fps': avg_fps, 'frames': int(avg_fps)}
                    
                    if avg_fps >= 25:
                        print(f"✓ Performance OK: {avg_fps:.1f} fps")
                    elif avg_fps >= 15:
                        print(f"⚠ Performance moderate: {avg_fps:.1f} fps")
                    else:
                        print(f"✗ Performance slow: {avg_fps:.1f} fps")
            except Exception as e:
                print(f"✗ MediaPipe test failed: {e}")
                results['mediapipe'] = {'error': str(e)}
            
            # Test 4: Pose Detection Test (quick - single frame)
            print("\n[4/5] Pose Detection Test...")
            try:
                # Ensure camera is working
                if not self.cap or not self.cap.isOpened():
                    print("⚠ Camera not available - reopening...")
                    self.open_camera(self.camera_index)
                    
                if not self.cap or not self.cap.isOpened():
                    print("⚠ Camera not available - skipping pose test")
                    results['pose'] = {'error': 'Camera not available'}
                elif not MEDIAPIPE_AVAILABLE:
                    print("⚠ MediaPipe not available - pose detection disabled")
                    results['pose'] = {'error': 'MediaPipe not available', 'demo_mode': True}
                else:
                    # Quick single-frame test - don't loop and risk breaking camera
                    ret, frame = self.cap.read()
                    detection_count = 0
                    if ret and frame is not None:
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        pose_results = self.pose.process(frame_rgb)
                        if pose_results and pose_results.pose_landmarks:
                            detection_count = 1
                            print("✓ Pose detected - tracking is working!")
                        else:
                            print("⚠ No pose detected - stand in front of camera")
                    else:
                        print("⚠ Could not read frame from camera")
                    
                    results['pose'] = {'detections': detection_count, 'total': 1}
            except Exception as e:
                print(f"✗ Pose test failed: {e}")
                results['pose'] = {'error': str(e)}
            
            # Test 5: System Summary
            print("\n[5/5] System Summary...")
            results['system'] = {
                'camera_index': self.camera_index,
                'serial_port': config['serial_port'],
                'mode': self.mode
            }
            print(f"  Camera: {self.camera_index}")
            print(f"  Serial: {config['serial_port']}")
            print(f"  Mode: {self.mode}")
            
            # Generate summary
            print("\n" + "="*70)
            print("DIAGNOSTIC SUMMARY")
            print("="*70)
            
            issues = []
            
            if not results.get('serial', {}).get('connected'):
                issues.append("✗ ESP32 not connected - connect hardware to COM port")
            
            if not results.get('camera', {}).get('working_cameras'):
                issues.append("✗ No cameras detected - check webcam connection")
            
            if results.get('mediapipe', {}).get('avg_fps', 0) < 15:
                issues.append("⚠ MediaPipe too slow - performance may suffer")
            
            if results.get('pose', {}).get('detections', 0) == 0:
                issues.append("⚠ No pose detected - stand in front of camera")
            
            if issues:
                print("\n⚠ ISSUES DETECTED:")
                for issue in issues:
                    print(f"  {issue}")
            else:
                print("\n✓ ALL SYSTEMS OPERATIONAL")
            
            # === CAMERA RECOVERY ===
            # Ensure camera is still working after diagnostics
            if not self.cap or not self.cap.isOpened():
                print("\n🔧 Recovering camera...")
                self.open_camera(self.camera_index)
            
            self.diagnostic_results = results
            self.running_diagnostics = False
            self.show_diagnostic_overlay = True  # Show results on GUI
            self.diagnostic_overlay_time = time.time()  # Auto-hide after 5 seconds
            
            print("\n✓ Diagnostics complete - returning to normal operation")
            
        except Exception as e:
            print(f"\n✗ Diagnostics error: {e}")
            import traceback
            traceback.print_exc()
            self.running_diagnostics = False
            self.show_diagnostic_overlay = True
            self.diagnostic_results = {
                'serial': {'connected': False},
                'camera': {'working_cameras': []},
                'mediapipe': {'avg_fps': 0},
                'pose': {'detections': 0},
                'error': str(e)
            }
            self.diagnostic_overlay_time = time.time()

    def safe_run_diagnostics(self):
        """Run diagnostics with hard error guard so GUI never crashes"""
        try:
            self.log_event("diagnostics_start", {"mode": self.mode, "cam": self.camera_index})
            self.run_diagnostics()
            self.log_event("diagnostics_end", {"status": "ok"})
        except Exception as e:
            print(f"✗ Diagnostics crashed: {e}")
            import traceback
            traceback.print_exc()
            # Show overlay with error
            self.diagnostic_results = {
                'serial': {'connected': False},
                'camera': {'working_cameras': []},
                'mediapipe': {'avg_fps': 0},
                'pose': {'detections': 0},
                'error': str(e)
            }
            self.show_diagnostic_overlay = True
            self.diagnostic_overlay_time = time.time()
            self.running_diagnostics = False
            self.log_event("diagnostics_end", {"status": "error", "error": str(e)})
    
    def emergency_test(self):
        """
        EMERGENCY TEST (E key) - Send test signals to motors and LEDs
        to verify wire connections are working
        """
        print("\n" + "="*50)
        print("⚡ EMERGENCY HARDWARE TEST")
        print("="*50)
        
        if not self.serial or not self.serial.ser or not self.serial.ser.is_open:
            print("✗ No serial connection - cannot test hardware!")
            # Show overlay warning
            self.diagnostic_results = {
                'serial': {'connected': False},
                'camera': {'working_cameras': []},
                'mediapipe': {'avg_fps': self.fps},
                'pose': {'detections': 0},
                'emergency': 'No serial connection'
            }
            self.show_diagnostic_overlay = True
            self.diagnostic_overlay_time = time.time()
            return
        
        try:
            # Test 1: Flash all LEDs white
            print("\n[1/3] Flashing LEDs WHITE...")
            white_frame = np.ones((self.led.height, self.led.width, 3), dtype=np.uint8) * 255
            led_packet = self.led.pack_led_packet(white_frame)
            self.serial.send_led(led_packet)
            time.sleep(0.5)
            
            # Flash red
            print("[2/3] Flashing LEDs RED...")
            red_frame = np.zeros((self.led.height, self.led.width, 3), dtype=np.uint8)
            red_frame[:, :, 2] = 255  # Red channel
            led_packet = self.led.pack_led_packet(red_frame)
            self.serial.send_led(led_packet)
            time.sleep(0.5)
            
            # Test 2: Move all servos to center
            print("[3/3] Moving ALL servos to CENTER (90°)...")
            center_angles = [90] * self.motor.num_servos
            servo_packet = self.motor.pack_servo_packet(center_angles)
            self.serial.send_servo(servo_packet)
            time.sleep(0.5)
            
            # Move to min
            print("     Moving to MIN (0°)...")
            min_angles = [0] * self.motor.num_servos
            servo_packet = self.motor.pack_servo_packet(min_angles)
            self.serial.send_servo(servo_packet)
            time.sleep(0.5)
            
            # Back to center
            print("     Moving back to CENTER...")
            servo_packet = self.motor.pack_servo_packet(center_angles)
            self.serial.send_servo(servo_packet)
            
            # Clear LEDs
            black_frame = np.zeros((self.led.height, self.led.width, 3), dtype=np.uint8)
            led_packet = self.led.pack_led_packet(black_frame)
            self.serial.send_led(led_packet)
            
            print("\n✓ EMERGENCY TEST COMPLETE!")
            print("  If LEDs flashed and servos moved → Wires are connected!")
            print("  If nothing happened → Check your wiring!")
            print("="*50)
            # Show success overlay
            self.diagnostic_results = {
                'serial': {'connected': True},
                'camera': {'working_cameras': self.available_cameras or []},
                'mediapipe': {'avg_fps': self.fps},
                'pose': {'detections': 0},
                'emergency': 'OK'
            }
            self.show_diagnostic_overlay = True
            self.diagnostic_overlay_time = time.time()
            
        except Exception as e:
            print(f"✗ Emergency test failed: {e}")
            self.diagnostic_results = {
                'serial': {'connected': False},
                'camera': {'working_cameras': []},
                'mediapipe': {'avg_fps': self.fps},
                'pose': {'detections': 0},
                'emergency': f'Error: {e}'
            }
            self.show_diagnostic_overlay = True
            self.diagnostic_overlay_time = time.time()

    def safe_emergency_test(self):
        """Run emergency test with guard to avoid crashing GUI"""
        try:
            self.log_event("emergency_test", {"action": "start", "mode": self.mode})
            self.emergency_test()
            self.log_event("emergency_test", {"action": "end", "status": "ok"})
        except Exception as e:
            print(f"✗ Emergency test crashed: {e}")
            import traceback
            traceback.print_exc()
            self.log_event("emergency_test", {"action": "end", "status": "error", "error": str(e)})
    
    # ═══════════════════════════════════════════════════════════════
    # Fault handling / resilience
    # ═══════════════════════════════════════════════════════════════
    def handle_fault(self, err: Exception, context: str = "loop"):
        """Capture unexpected errors, keep app alive, and surface overlay."""
        import traceback, datetime
        err_str = str(err)
        print(f"\n✗ Unexpected error in {context}: {err_str}")
        traceback.print_exc()
        timestamp = datetime.datetime.now().isoformat(timespec='seconds')
        fault_info = {
            'time': timestamp,
            'context': context,
            'error': err_str,
            'mode': self.mode,
            'camera_index': self.camera_index,
            'serial_port': config.get('serial_port'),
        }
        self.log_event("fault", fault_info)
        self.last_fault = fault_info
        self.fault_history.append(fault_info)
        # Keep only last 20 faults
        if len(self.fault_history) > 20:
            self.fault_history.pop(0)
        # Show overlay for a few seconds
        self.show_fault_overlay = True
        self.fault_overlay_time = time.time()
        # Attempt soft recovery: switch to README and keep running
        self.mode = "README"
        # Try reopening camera if closed
        try:
            if not self.cap or not self.cap.isOpened():
                self.open_camera(self.camera_index)
        except Exception:
            pass

    def draw_fault_overlay(self, frame):
        """Overlay to show last unexpected error"""
        if not self.show_fault_overlay or not self.last_fault:
            return frame
        # Auto-hide after 5s
        if time.time() - self.fault_overlay_time > 5:
            self.show_fault_overlay = False
            return frame
        h, w = frame.shape[:2]
        overlay = frame.copy()
        cv2.rectangle(overlay, (40, 40), (w - 40, 180), (0, 0, 50), -1)
        cv2.addWeighted(overlay, 0.8, frame, 0.2, 0, frame)
        cv2.rectangle(frame, (40, 40), (w - 40, 180), (0, 0, 255), 2)
        cv2.putText(frame, "UNEXPECTED ERROR - auto-recovered", (60, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 1)
        cv2.putText(frame, f"Context: {self.last_fault.get('context', '')}", (60, 100),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        cv2.putText(frame, f"Error: {self.last_fault.get('error', '')[:50]}", (60, 125),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        cv2.putText(frame, "(App stays alive. Press R to continue)", (60, 150),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (128, 128, 128), 1)
        return frame

    def draw_stats_panel(self, frame):
        """Draw stats panel on right side of frame"""
        h, w = frame.shape[:2]
        panel_width = 200
        panel_x = w - panel_width - 10
        panel_y = 10
        panel_height = 180
        
        # Semi-transparent panel
        overlay = frame.copy()
        cv2.rectangle(overlay, (panel_x, panel_y), (w - 10, panel_y + panel_height),
                     (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
        
        # Border
        cv2.rectangle(frame, (panel_x, panel_y), (w - 10, panel_y + panel_height),
                     (0, 255, 255), 1)
        
        # Title
        cv2.putText(frame, "SYSTEM STATUS", (panel_x + 10, panel_y + 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        
        y = panel_y + 45
        line_h = 22
        
        # Device
        device_name = config.get('serial_port', 'AUTO')
        if self.serial and self.serial.ser and self.serial.ser.is_open:
            cv2.putText(frame, f"Device: {device_name}", (panel_x + 10, y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
        else:
            cv2.putText(frame, "Device: DISCONNECTED", (panel_x + 10, y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
        y += line_h
        
        # Baud rate
        baud = config.get('baud_rate', 460800)
        cv2.putText(frame, f"Baud: {baud}", (panel_x + 10, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
        y += line_h
        
        # Camera
        cv2.putText(frame, f"Camera: {self.camera_index}", (panel_x + 10, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
        y += line_h
        
        # WiFi (placeholder - could be expanded)
        cv2.putText(frame, "WiFi: Disabled", (panel_x + 10, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (128, 128, 128), 1)
        y += line_h
        
        # FPS
        fps_color = (0, 255, 0) if self.fps >= 25 else ((0, 255, 255) if self.fps >= 15 else (0, 0, 255))
        cv2.putText(frame, f"FPS: {self.fps:.1f}", (panel_x + 10, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, fps_color, 1)
        y += line_h
        
        # Mode
        cv2.putText(frame, f"Mode: {self.mode}", (panel_x + 10, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 255), 1)
        
        return frame
    
    def draw_diagnostic_overlay(self, frame):
        """Draw diagnostic results overlay on screen"""
        if not self.diagnostic_results:
            return frame
        
        # Auto-hide after 5 seconds
        if time.time() - self.diagnostic_overlay_time > 5:
            self.show_diagnostic_overlay = False
            return frame
        
        h, w = frame.shape[:2]
        
        # Semi-transparent overlay
        overlay = frame.copy()
        cv2.rectangle(overlay, (50, 50), (w - 50, 200), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.8, frame, 0.2, 0, frame)
        cv2.rectangle(frame, (50, 50), (w - 50, 200), (0, 255, 0), 2)
        
        # Title
        cv2.putText(frame, "SYSTEM DIAGNOSTICS - Press D to refresh", (70, 80),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)
        
        # Results
        y = 110
        results = self.diagnostic_results
        
        # Serial
        serial_ok = results.get('serial', {}).get('connected', False)
        cv2.putText(frame, f"Serial: {'OK' if serial_ok else 'NOT CONNECTED'}", (70, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0) if serial_ok else (0, 0, 255), 1)
        
        # Camera
        cams = results.get('camera', {}).get('working_cameras', [])
        cv2.putText(frame, f"Cameras: {len(cams)} found", (250, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0) if cams else (0, 0, 255), 1)
        
        y += 30
        
        # FPS
        fps = results.get('mediapipe', {}).get('avg_fps', 0)
        fps_color = (0, 255, 0) if fps >= 25 else ((0, 255, 255) if fps >= 15 else (0, 0, 255))
        cv2.putText(frame, f"MediaPipe: {fps:.1f} FPS", (70, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, fps_color, 1)
        
        # Pose
        pose_det = results.get('pose', {}).get('detections', 0)
        cv2.putText(frame, f"Pose: {pose_det}/30 detected", (250, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0) if pose_det > 0 else (0, 255, 255), 1)
        
        y += 30
        
        # Emergency status if present
        if 'emergency' in results:
            cv2.putText(frame, f"Emergency: {results['emergency']}", (70, y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 200, 255), 1)
            y += 20
        
        cv2.putText(frame, "[E] Emergency Test  |  Auto-hiding in " + 
                   str(int(5 - (time.time() - self.diagnostic_overlay_time))) + "s",
                   (70, y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (128, 128, 128), 1)
        
        return frame

    def draw_readme(self, frame):
        """Draw README mode with split-screen layout"""
        h, w = frame.shape[:2]
        
        # Create split-screen display: Left = Instructions, Right = Camera
        display_frame = np.zeros_like(frame)
        
        # Left side: Instructions overlay
        left_frame = np.zeros((h, w//2, 3), dtype=np.uint8)
        # Semi-transparent background
        cv2.rectangle(left_frame, (10, 10), (w//2-10, h-10), (0, 0, 0), -1)
        left_frame = cv2.addWeighted(left_frame, 0.7, np.zeros_like(left_frame), 0.3, 0)
        
        # Title
        cv2.putText(left_frame, "MIRROR BODY ANIMATIONS", (20, 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
        
        # Instructions
        instructions = [
            "",
            "KEYBOARD CONTROLS:",
            "",
            "R - README (this screen)",
            "M - MOTOR Mode (servos only)",
            "L - LED Mode (display only)",
            "B - BOTH Mode (servos + LEDs)",
            "C - Switch Camera",
            "D - Run DIAGNOSTICS",
            "E - EMERGENCY TEST (verify wires)",
            "Q - QUIT",
            "",
            f"Current Mode: {self.mode}",
            f"Camera: {self.camera_index}",
            f"Serial: {config['serial_port']} @ {config['baud_rate']}",
        ]
        
        y = 110
        for line in instructions:
            color = (0, 255, 0) if line.startswith(self.mode[0]) else (255, 255, 255)
            cv2.putText(left_frame, line, (30, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            y += 25
        
        # Right side: Camera feed
        display_frame[:, :w//2] = left_frame[:, :]      # Left: instructions
        display_frame[:, w//2:] = frame[:, w//2:]       # Right: camera feed
        
        # Add center divider line
        cv2.line(display_frame, (w//2, 0), (w//2, h), (0, 255, 255), 2)
        
        # Add labels
        cv2.putText(display_frame, "SYSTEM CONTROLS", (20, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        cv2.putText(display_frame, "CAMERA INPUT", (w//2 + 20, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        return display_frame
    
    def run(self):
        """Main GUI loop"""
        print("\n" + "="*70)
        print("MIRROR BODY ANIMATIONS - INTERACTIVE GUI")
        print("="*70)
        print(f"\nMode: {self.mode}")
        print("Press R for README, M for Motors, L for LEDs, B for Both")
        print("Press D for Diagnostics, C to switch camera, Q to quit\n")
        
        cv2.namedWindow("Mirror Body Animations", cv2.WINDOW_NORMAL)
        cv2.setWindowProperty("Mirror Body Animations", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        
        while self.running:
            frame_start = time.time()
            try:
                ret, frame = self.cap.read()
                if not ret:
                    continue
                
                # Process based on mode
                if self.mode == "LED_TEST":
                    # LED TEST MODE: Display simple geometric patterns (based on working patterns 10, 11)
                    from packages.mirror_core.testing.led_panel_tester import LEDPanelTester
                    from packages.mirror_core.testing import simple_led_patterns
                    
                    if not hasattr(self, 'led_tester'):
                        self.led_tester = LEDPanelTester()
                        self.test_pattern_index = 0
                        # Organized test patterns with category ranges
                        self.test_patterns = [
                            # STATIC BASELINE TESTS (0-4)
                            ('STATIC', 'all_white', 'All LEDs white - Full system check'),
                            ('STATIC', 'brightness_levels', 'Panels 1-8 brightness gradient (30→255)'),
                            ('STATIC', 'checkerboard', 'Checkerboard pattern - Pixel alignment test'),
                            ('STATIC', 'gradient', 'Horizontal gradient - Smooth transition test'),
                            ('STATIC', 'borders', 'Panel borders - 2×4 grid verification'),
                            
                            # GEOMETRIC TESTS (5-9)
                            ('GEOMETRIC', 'vertical_bars', 'Vertical stripes - Column wiring test'),
                            ('GEOMETRIC', 'horizontal_bars', 'Horizontal stripes - Row wiring test'),
                            ('GEOMETRIC', 'diagonal_gradient', 'Diagonal gradient - Cross-panel test'),
                            ('GEOMETRIC', 'concentric', 'Concentric squares - Radial pattern'),
                            ('GEOMETRIC', 'panel_corners', 'Corner markers - Panel identification'),
                            
                            # INDIVIDUAL PANEL TESTS (10-17)
                            ('INDIVIDUAL', 'panel_1', 'Panel 1 ONLY - Top-Left'),
                            ('INDIVIDUAL', 'panel_2', 'Panel 2 ONLY - Top-Right'),
                            ('INDIVIDUAL', 'panel_3', 'Panel 3 ONLY - Middle-Top-Left'),
                            ('INDIVIDUAL', 'panel_4', 'Panel 4 ONLY - Middle-Top-Right'),
                            ('INDIVIDUAL', 'panel_5', 'Panel 5 ONLY - Middle-Bottom-Left'),
                            ('INDIVIDUAL', 'panel_6', 'Panel 6 ONLY - Middle-Bottom-Right'),
                            ('INDIVIDUAL', 'panel_7', 'Panel 7 ONLY - Bottom-Left'),
                            ('INDIVIDUAL', 'panel_8', 'Panel 8 ONLY - Bottom-Right'),
                            
                            # NUMBERS TEST (18)
                            ('NUMBERS', 'numbers_1_8', 'Display numbers 1-8 on each panel'),
                            
                            # TEXT TESTS (19-23)
                            ('TEXT', 'hello_full', 'Display HELLO across full screen'),
                            ('TEXT', 'hello_letter_h', 'Display letter H only'),
                            ('TEXT', 'hello_letter_e', 'Display letter E only'),
                            ('TEXT', 'hello_letter_l', 'Display letter L only'),
                            ('TEXT', 'hello_letter_o', 'Display letter O only'),
                            
                            # HUMAN SIMULATION TESTS (24-27)
                            ('HUMAN_SIM', 'human_center', 'Human silhouette - Center position'),
                            ('HUMAN_SIM', 'human_left', 'Human silhouette - Left position'),
                            ('HUMAN_SIM', 'human_right', 'Human silhouette - Right position'),
                            ('HUMAN_SIM', 'human_wave', 'Animated wave pattern - Motion test'),
                        ]
                    
                    # Get current test pattern
                    category, pattern_name, description = self.test_patterns[self.test_pattern_index]
                    
                    # Generate pattern based on name
                    if pattern_name == 'all_white':
                        led_pattern = np.full((64, 32), 255, dtype=np.uint8)
                        what_to_see = "All LEDs bright white"
                    elif pattern_name == 'brightness_levels':
                        led_pattern = self.led_tester.generate_panel_test_pattern()
                        what_to_see = "8 panels from dim (top-left) to bright (bottom-right)"
                    elif pattern_name == 'checkerboard':
                        led_pattern = self.led_tester.generate_checkerboard_test()
                        what_to_see = "Alternating checkerboard squares"
                    elif pattern_name == 'gradient':
                        led_pattern = self.led_tester.generate_gradient_test()
                        what_to_see = "Smooth horizontal gradient left→right"
                    elif pattern_name == 'borders':
                        led_pattern = self.led_tester.generate_panel_border_test()
                        what_to_see = "White grid lines showing 2×4 panel layout"
                    elif pattern_name == 'vertical_bars':
                        led_pattern = simple_led_patterns.generate_vertical_bars()
                        what_to_see = "Alternating vertical columns (stripes)"
                    elif pattern_name == 'horizontal_bars':
                        led_pattern = simple_led_patterns.generate_horizontal_bars()
                        what_to_see = "Alternating horizontal rows (stripes)"
                    elif pattern_name == 'diagonal_gradient':
                        led_pattern = simple_led_patterns.generate_diagonal_gradient()
                        what_to_see = "Diagonal gradient from top-left to bottom-right"
                    elif pattern_name == 'concentric':
                        led_pattern = simple_led_patterns.generate_concentric_squares()
                        what_to_see = "Concentric squares expanding from center"
                    elif pattern_name == 'panel_corners':
                        led_pattern = simple_led_patterns.generate_panel_corners()
                        what_to_see = "Small bright markers in different corners of each panel"
                    elif pattern_name.startswith('panel_'):
                        # Individual panel tests
                        panel_id = int(pattern_name.split('_')[1])
                        led_pattern = self.led_tester.generate_individual_panel_test(panel_id)
                        what_to_see = f"ONLY Panel {panel_id} lit (solid white), all others dark"
                    elif pattern_name == 'numbers_1_8':
                        # Numbers test - draw actual numbers on panels
                        led_pattern = self._generate_numbers_pattern()
                        what_to_see = "Numbers 1-8 displayed on each panel"
                    elif pattern_name == 'hello_full':
                        led_pattern = self._generate_hello_text('HELLO')
                        what_to_see = "Text 'HELLO' across full display"
                    elif pattern_name == 'hello_letter_h':
                        led_pattern = self._generate_hello_text('H')
                        what_to_see = "Single letter 'H' displayed"
                    elif pattern_name == 'hello_letter_e':
                        led_pattern = self._generate_hello_text('E')
                        what_to_see = "Single letter 'E' displayed"
                    elif pattern_name == 'hello_letter_l':
                        led_pattern = self._generate_hello_text('L')
                        what_to_see = "Single letter 'L' displayed"
                    elif pattern_name == 'hello_letter_o':
                        led_pattern = self._generate_hello_text('O')
                        what_to_see = "Single letter 'O' displayed"
                    elif pattern_name == 'human_center':
                        led_pattern = self._generate_human_silhouette(position='center')
                        what_to_see = "Human silhouette in center of display"
                    elif pattern_name == 'human_left':
                        led_pattern = self._generate_human_silhouette(position='left')
                        what_to_see = "Human silhouette on left side"
                    elif pattern_name == 'human_right':
                        led_pattern = self._generate_human_silhouette(position='right')
                        what_to_see = "Human silhouette on right side"
                    elif pattern_name == 'human_wave':
                        # Animated wave - use time for animation
                        import math
                        offset = int((time.time() * 2) % 32)
                        led_pattern = self._generate_wave_pattern(offset)
                        what_to_see = "Animated wave moving across display"
                    else:
                        led_pattern = np.zeros((64, 32), dtype=np.uint8)
                        what_to_see = "Unknown pattern"
                    
                    # CRITICAL FIX: ESP32 firmware inverts X and Y coordinates in XY() function
                    # We must flip the pattern to compensate
                    # Flip Y axis (vertical), then X axis (horizontal)
                    led_pattern_flipped = np.flip(np.flip(led_pattern, axis=0), axis=1)
                    
                    # Send GRAYSCALE to ESP32 (firmware expects single byte per pixel)
                    packet = self.led.pack_led_packet(led_pattern_flipped)
                    self.serial.send_led(packet)
                    
                    # Create RGB for DISPLAY ONLY (not for ESP32)
                    led_rgb = np.stack([led_pattern, led_pattern, led_pattern], axis=2)
                    
                    # Create display frame
                    h, w = frame.shape[:2]
                    display_frame = np.zeros((h, w, 3), dtype=np.uint8)
                    
                    # Resize LED pattern for display (center it)
                    led_display = cv2.resize(led_rgb, (w//2, h//2))
                    y_offset = h//4
                    x_offset = w//4
                    display_frame[y_offset:y_offset+h//2, x_offset:x_offset+w//2] = led_display
                    
                    # Add instructions
                    test_num = self.test_pattern_index
                    total_tests = len(self.test_patterns)
                    
                    # Title
                    cv2.putText(display_frame, "LED PANEL TEST MODE", (20, 40),
                               cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 255), 3)
                    
                    # Category and test number
                    cv2.putText(display_frame, f"[{category}] Test {test_num}/{total_tests-1}", (20, 80),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 200, 0), 2)
                    
                    # Description
                    cv2.putText(display_frame, description, (20, 120),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    
                    # What you should see
                    cv2.putText(display_frame, "WHAT YOU SHOULD SEE:", (20, 160),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                    cv2.putText(display_frame, f"  {what_to_see}", (20, 190),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2)
                    
                    # Test category ranges
                    cv2.putText(display_frame, "TEST CATEGORIES:", (20, h-180),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
                    cv2.putText(display_frame, "  0-4: STATIC baseline tests", (20, h-155),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
                    cv2.putText(display_frame, "  5-9: GEOMETRIC pattern tests", (20, h-135),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
                    cv2.putText(display_frame, "  10-17: INDIVIDUAL panel tests", (20, h-115),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
                    cv2.putText(display_frame, "  18: NUMBERS test", (20, h-95),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
                    cv2.putText(display_frame, f"  19-{total_tests-1}: HUMAN simulation tests", (20, h-75),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
                    
                    # Controls
                    cv2.putText(display_frame, "Press SPACE to change pattern | T to exit test mode",
                               (20, h-40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                
                elif self.mode == "README":
                    display_frame = self.draw_readme(frame)
                
                elif self.mode == "MOTOR":
                    try:
                        # MOTOR MODE: Human position tracking
                        if not MEDIAPIPE_AVAILABLE:
                            # Demo mode - simulate motor movement based on human position
                            angles = [90 + 20 * np.sin(time.time() * 2 + i * 0.5) for i in range(6)]  # Simulate movement
                            packet = self.motor.pack_servo_packet(angles)
                            self.serial.send_servo(packet)
                            status = "DEMO MODE - Simulated Tracking"
                            # Create silhouette simulation
                            silhouette = np.zeros_like(frame)
                            # Draw animated silhouette
                            t = time.time()
                            center_x, center_y = frame.shape[1] // 4, frame.shape[0] // 2
                            for i in range(20):
                                angle = t * 2 + i * 0.3
                                x = int(center_x + 80 * np.cos(angle))
                                y = int(center_y + 120 * np.sin(angle * 0.7))
                                cv2.circle(silhouette, (x, y), 15, (255, 255, 255), -1)
                        else:
                            # Human position tracking with MediaPipe
                            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                            
                            try:
                                pose_results = self.pose.process(frame_rgb)
                            except Exception as e:
                                print(f"\nCRITICAL: MediaPipe processing error: {e}")
                                traceback.print_exc()
                                # Continue without crashing
                                pose_results = None

                            # Check for human detection
                            human_detected = False
                            human_x_position = 0.5
                            
                            if pose_results and pose_results.pose_landmarks:
                                visible = [lm for lm in pose_results.pose_landmarks.landmark if lm.visibility > 0.85]
                                if len(visible) >= 10:
                                    human_detected = True
                                    visible_x = [lm.x for lm in visible]
                                    human_x_position = sum(visible_x) / len(visible_x)
                            
                            if human_detected:
                                # Map X position (0.0-1.0) -> (0-180°)
                                target_angle = human_x_position * 180.0
                                target_angle = max(0, min(180, target_angle))
                                angles = [target_angle] * self.motor.num_servos
                                
                                # RATE LIMITING & VALIDATION
                                current_time = time.time()
                                if current_time - self.last_serial_send_time > self.serial_min_interval:
                                    try:
                                        # Validate angles before packing
                                        valid_angles = []
                                        for a in angles:
                                            if not np.isfinite(a): 
                                                a = 90  # Default to center if invalid
                                            a = max(0, min(180, int(a)))  # Clamp to valid range
                                            valid_angles.append(a)
                                        
                                        # Pre-send validation
                                        if len(valid_angles) != self.motor.num_servos:
                                            print(f"⚠ Angle count mismatch: {len(valid_angles)} != {self.motor.num_servos}")
                                            valid_angles = [90] * self.motor.num_servos
                                        
                                        packet = self.motor.pack_servo_packet(valid_angles)
                                        
                                        # Validate packet before sending
                                        if packet is None or len(packet) == 0:
                                            print("⚠ Invalid packet generated, skipping send")
                                        else:
                                            # DEFENSIVE: send_servo now handles all errors gracefully
                                            success = self.serial.send_servo(packet)
                                            if success:
                                                self.last_serial_send_time = current_time
                                    except ValueError as e:
                                        print(f"⚠ Servo value error: {e}")
                                    except Exception as e:
                                        print(f"⚠ Serial send error: {e}")
                                        traceback.print_exc()

                                status = f"TRACKING HUMAN - Position: {human_x_position:.2f} ({target_angle:.1f}°)"
                                
                                # Create silhouette using segmentation mask
                                silhouette = np.zeros_like(frame)
                                if pose_results.segmentation_mask is not None:
                                    # Use segmentation mask for full body silhouette
                                    mask = (pose_results.segmentation_mask > 0.5).astype(np.uint8) * 255
                                    silhouette[:, :, 0] = mask
                                    silhouette[:, :, 1] = mask
                                    silhouette[:, :, 2] = mask
                                else:
                                    # Fallback: landmarks as dots if segmentation unavailable
                                    if pose_results.pose_landmarks:
                                        h, w = frame.shape[:2]
                                        for landmark in pose_results.pose_landmarks.landmark:
                                            x, y = int(landmark.x * w), int(landmark.y * h)
                                            cv2.circle(silhouette, (x, y), 8, (255, 255, 255), -1)
                            else:
                                status = "NO HUMAN DETECTED - Motors Stationary"
                                silhouette = np.zeros_like(frame)
                        
                        # Create split-screen display: Left = Simulation/Silhouette, Right = Camera
                        # IMPORTANT: Detection happens on FULL frame, display shows both sides
                        h, w = frame.shape[:2]
                        half_w = w // 2
                        
                        # Resize both to half-width to fit side-by-side
                        silhouette_half = cv2.resize(silhouette, (half_w, h))
                        camera_half = cv2.resize(frame, (half_w, h))
                        
                        # Combine horizontally
                        display_frame = np.hstack([silhouette_half, camera_half])
                        
                        # Add center divider line
                        cv2.line(display_frame, (half_w, 0), (half_w, h), (0, 255, 255), 2)
                        
                        # Add labels
                        cv2.putText(display_frame, "COMPUTER SIMULATION", (20, 30), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                        cv2.putText(display_frame, "CAMERA INPUT", (w//2 + 20, 30), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                        
                        cv2.putText(display_frame, f"MODE: MOTOR", (20, 70), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                        cv2.putText(display_frame, status, (20, 100), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                        # Continue with overlays and display logic below
                    except Exception as e:
                        self.handle_fault(e, "MOTOR_MODE")
                        display_frame = self.draw_readme(frame)
                
                elif self.mode == "LED":
                    try:
                        # LED MODE: Display control
                        # No human detected → display static text: "HOOKKAPANI STUDIOS"
                        # Human detected → LEDs switch to human silhouette render mode
                        
                        if not MEDIAPIPE_AVAILABLE:
                            # Demo mode - show static text since no human detection available
                            led_frame = np.zeros((config['led_height'], config['led_width'], 3), dtype=np.uint8)
                            # Render "HOOKKAPANI STUDIOS" text on LED matrix
                            text = "HOOKKAPANI STUDIOS"
                            # Simple text rendering on LED matrix (center the text)
                            text_x = max(0, (config['led_width'] - len(text) * 6) // 2)
                            text_y = config['led_height'] // 2
                            for i, char in enumerate(text):
                                if text_x + i * 6 < config['led_width']:
                                    # Simple block character representation
                                    led_frame[text_y-2:text_y+2, text_x + i*6:text_x + i*6 + 4] = [255, 255, 255]
                            seg_mask = None
                            silhouette = np.zeros_like(frame)
                            status = "NO HUMAN - Showing Studio Text"
                            human_detected = False
                        else:
                            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                            pose_results = self.pose.process(frame_rgb)
                            
                            # Check for human detection
                            human_detected = False
                            if pose_results and pose_results.pose_landmarks:
                                # Check at least 10 landmarks with visibility > 0.85
                                visible = [lm for lm in pose_results.pose_landmarks.landmark if lm.visibility > 0.85]
                                if len(visible) >= 10:
                                    human_detected = True
                            
                            if human_detected:
                                # Human detected → show silhouette
                                seg_mask = pose_results.segmentation_mask if pose_results and hasattr(pose_results, 'segmentation_mask') else None
                                led_frame = self.led.render_frame(pose_results, seg_mask)
                                status = "HUMAN DETECTED - Showing Silhouette"
                            else:
                                # No human detected → show "HOOKKAPANI STUDIOS"
                                led_frame = np.zeros((config['led_height'], config['led_width'], 3), dtype=np.uint8)
                                # Render "HOOKKAPANI STUDIOS" text on LED matrix
                                text = "HOOKKAPANI STUDIOS"
                                # Simple text rendering on LED matrix (center the text)
                                text_x = max(0, (config['led_width'] - len(text) * 6) // 2)
                                text_y = config['led_height'] // 2
                                for i, char in enumerate(text):
                                    if text_x + i * 6 < config['led_width']:
                                        # Simple block character representation
                                        led_frame[text_y-2:text_y+2, text_x + i*6:text_x + i*6 + 4] = [255, 255, 255]
                                seg_mask = None
                                status = "NO HUMAN - Showing Studio Text"
                            
                            # Create silhouette for display
                            silhouette = np.zeros_like(frame)
                            if human_detected and pose_results and pose_results.pose_landmarks:
                                # Show silhouette when human detected
                                if seg_mask is not None:
                                    mask = (seg_mask > 0.5).astype(np.uint8) * 255
                                    silhouette[:, :, 0] = mask
                                    silhouette[:, :, 1] = mask
                                    silhouette[:, :, 2] = mask
                                else:
                                    # Fallback: draw pose landmarks as silhouette
                                    h, w = frame.shape[:2]
                                    for landmark in pose_results.pose_landmarks.landmark:
                                        x, y = int(landmark.x * w), int(landmark.y * h)
                                        cv2.circle(silhouette, (x, y), 8, (255, 255, 255), -1)
                        
                        packet = self.led.pack_led_packet(led_frame)
                        self.serial.send_led(packet)
                        
                        # Create split-screen display: Left = Simulation/Silhouette, Right = Camera
                        h, w = frame.shape[:2]
                        display_frame = np.zeros_like(frame)
                        display_frame[:, :w//2] = silhouette[:, :w//2]  # Left: silhouette/simulation
                        display_frame[:, w//2:] = frame[:, w//2:]      # Right: camera feed
                        
                        # Add center divider line
                        cv2.line(display_frame, (w//2, 0), (w//2, h), (0, 255, 255), 2)
                        
                        # Add labels
                        cv2.putText(display_frame, "COMPUTER SIMULATION", (20, 30), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                        cv2.putText(display_frame, "CAMERA INPUT", (w//2 + 20, 30), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                    except Exception as e:
                        self.handle_fault(e, "LED_MODE")
                        display_frame = self.draw_readme(frame)
                    
                    cv2.putText(display_frame, f"MODE: LED - Display Active", (20, 70), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
                    cv2.putText(display_frame, status, (20, 100), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255) if human_detected else (255, 165, 0), 2)
                elif self.mode == "BOTH":
                    # BOTH MODE: Full system operation
                    # LED detection takes precedence:
                    # - No human detected → motors stay still, LEDs show "HOOKKAPANI STUDIOS"
                    # - Human detected → motors track position, LEDs show silhouette
                    # Both systems run without blocking each other
                    
                    if not MEDIAPIPE_AVAILABLE:
                        # Demo mode - simulate both systems with LED precedence
                        # No human detection available, so motors stay still, LEDs show text
                        angles = [90] * 6  # Motors stay still (neutral position)
                        servo_packet = self.motor.pack_servo_packet(angles)
                        self.serial.send_servo(servo_packet)
                        
                        led_frame = np.zeros((config['led_height'], config['led_width'], 3), dtype=np.uint8)
                        # Render "HOOKKAPANI STUDIOS" text on LED matrix
                        text = "HOOKKAPANI STUDIOS"
                        text_x = max(0, (config['led_width'] - len(text) * 6) // 2)
                        text_y = config['led_height'] // 2
                        for i, char in enumerate(text):
                            if text_x + i * 6 < config['led_width']:
                                led_frame[text_y-2:text_y+2, text_x + i*6:text_x + i*6 + 4] = [255, 255, 255]
                        seg_mask = None
                        pose_results = None
                        silhouette = np.zeros_like(frame)
                        status = "NO HUMAN - Motors Still, Showing Studio Text"
                        human_detected = False
                    else:
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        pose_results = self.pose.process(frame_rgb)
                        
                        # Check for human detection (LED detection takes precedence)
                        human_detected = False
                        if pose_results and pose_results.pose_landmarks:
                            # Check at least 10 landmarks with visibility > 0.85
                            visible = [lm for lm in pose_results.pose_landmarks.landmark if lm.visibility > 0.85]
                            if len(visible) >= 10:
                                human_detected = True
                        
                        if human_detected:
                            # Human detected → both motors and LEDs activate
                            angles = self.motor.calculate_angles(pose_results)
                            servo_packet = self.motor.pack_servo_packet(angles)
                            self.serial.send_servo(servo_packet)
                            
                            seg_mask = pose_results.segmentation_mask if pose_results and hasattr(pose_results, 'segmentation_mask') else None
                            led_frame = self.led.render_frame(pose_results, seg_mask)
                            status = "HUMAN DETECTED - Motors Tracking, Showing Silhouette"
                        else:
                            # No human detected → motors stay still, LEDs show "HOOKKAPANI STUDIOS"
                            # STRICT MODE: Motors must remain still (no jitter/drift) -> Do NOT send packets
                            # angles = [90] * 6  # REMOVED: Centering causes movement
                            # servo_packet = self.motor.pack_servo_packet(angles)
                            # self.serial.send_servo(servo_packet)
                            
                            led_frame = np.zeros((config['led_height'], config['led_width'], 3), dtype=np.uint8)
                            # Render "HOOKKAPANI STUDIOS" text on LED matrix
                            text = "HOOKKAPANI STUDIOS"
                            text_x = max(0, (config['led_width'] - len(text) * 6) // 2)
                            text_y = config['led_height'] // 2
                            for i, char in enumerate(text):
                                if text_x + i * 6 < config['led_width']:
                                    led_frame[text_y-2:text_y+2, text_x + i*6:text_x + i*6 + 4] = [255, 255, 255]
                            seg_mask = None
                            status = "NO HUMAN - Motors Still, Showing Studio Text"
                        
                        # Create silhouette for display
                        silhouette = np.zeros_like(frame)
                        if human_detected and pose_results and pose_results.pose_landmarks:
                            # Show silhouette when human detected
                            if seg_mask is not None:
                                mask = (seg_mask > 0.5).astype(np.uint8) * 255
                                silhouette[:, :, 0] = mask
                                silhouette[:, :, 1] = mask
                                silhouette[:, :, 2] = mask
                            else:
                                # Fallback: draw pose landmarks as silhouette
                                h, w = frame.shape[:2]
                                for landmark in pose_results.pose_landmarks.landmark:
                                    x, y = int(landmark.x * w), int(landmark.y * h)
                                    cv2.circle(silhouette, (x, y), 8, (255, 255, 255), -1)
                    
                    led_packet = self.led.pack_led_packet(led_frame)
                    self.serial.send_led(led_packet)
                    
                    # Create split-screen display: Left = Simulation/Silhouette, Right = Camera
                    h, w = frame.shape[:2]
                    display_frame = np.zeros_like(frame)
                    display_frame[:, :w//2] = silhouette[:, :w//2]  # Left: silhouette/simulation
                    display_frame[:, w//2:] = frame[:, w//2:]      # Right: camera feed
                    
                    # Add center divider line
                    cv2.line(display_frame, (w//2, 0), (w//2, h), (0, 255, 255), 2)
                    
                    # Add labels
                    cv2.putText(display_frame, "COMPUTER SIMULATION", (20, 30), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                    cv2.putText(display_frame, "CAMERA INPUT", (w//2 + 20, 30), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                    
                    cv2.putText(display_frame, f"MODE: BOTH - Full System Active", (20, 70), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 255), 2)
                    cv2.putText(display_frame, status, (20, 100), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255) if human_detected else (255, 165, 0), 2)
                
                else:
                    display_frame = frame
                
                # Draw stats panel on right side (always visible)
                display_frame = self.draw_stats_panel(display_frame)
                
                # Draw diagnostic overlay if active
                if self.show_diagnostic_overlay:
                    display_frame = self.draw_diagnostic_overlay(display_frame)
                
                # Draw fault overlay if active
                display_frame = self.draw_fault_overlay(display_frame)
                
                # Calculate FPS
                frame_time = time.time() - frame_start
                self.frame_times.append(frame_time)
                if len(self.frame_times) > 30:
                    self.frame_times.pop(0)
                if time.time() - self.last_fps_update > 0.5:
                    avg_time = sum(self.frame_times) / len(self.frame_times)
                    self.fps = 1.0 / avg_time if avg_time > 0 else 0
                    self.last_fps_update = time.time()
                
                # Show frame
                cv2.imshow("Mirror Body Animations", display_frame)
                
                # Handle keyboard
                key = cv2.waitKey(1) & 0xFF
                
                if key == ord(' '):  # SPACE key - cycle LED test patterns (forward)
                    if self.mode == "LED_TEST" and hasattr(self, 'led_tester'):
                        self.test_pattern_index = (self.test_pattern_index + 1) % len(self.test_patterns)
                        print(f"→ Pattern: {self.test_patterns[self.test_pattern_index][1]}")
                elif key == 83 or key == ord('d'):  # RIGHT ARROW or D - Next pattern
                    if self.mode == "LED_TEST" and hasattr(self, 'led_tester'):
                        self.test_pattern_index = (self.test_pattern_index + 1) % len(self.test_patterns)
                        print(f"→ Next: {self.test_patterns[self.test_pattern_index][1]}")
                elif key == 81 or key == ord('a'):  # LEFT ARROW or A - Previous pattern
                    if self.mode == "LED_TEST" and hasattr(self, 'led_tester'):
                        self.test_pattern_index = (self.test_pattern_index - 1) % len(self.test_patterns)
                        print(f"<- Prev: {self.test_patterns[self.test_pattern_index][1]}")
                elif key == ord('t') or key == ord('T'):
                    self.mode = "LED_TEST"
                    print("Mode: LED_TEST")
                    self.log_event("mode_change", {"mode": self.mode})
                elif key == ord('r') or key == ord('R'):
                    self.mode = "README"
                    print("Mode: README")
                    self.log_event("mode_change", {"mode": self.mode})
                elif key == ord('m') or key == ord('M'):
                    self.mode = "MOTOR"
                    print("Mode: MOTOR (servos only)")
                    self.log_event("mode_change", {"mode": self.mode})
                elif key == ord('l') or key == ord('L'):
                    self.mode = "LED"
                    print("Mode: LED (display only)")
                    self.log_event("mode_change", {"mode": self.mode})
                elif key == ord('b') or key == ord('B'):
                    self.mode = "BOTH"
                    print("Mode: BOTH (full system)")
                    self.log_event("mode_change", {"mode": self.mode})
                elif key == ord('c') or key == ord('C'):
                    self.switch_camera()
                    self.log_event("camera_switch", {"camera": self.camera_index})
                elif key == ord('d') or key == ord('D'):
                    self.safe_run_diagnostics()
                elif key == ord('e') or key == ord('E'):
                    self.safe_emergency_test()  # Test motors/LEDs
                elif key == ord('q') or key == ord('Q'):
                    self.running = False
                    print("Quitting...")
                    self.log_event("quit", {})
            except Exception as err:
                self.handle_fault(err, context="main_loop")
                time.sleep(0.2)
        
        # Cleanup
        self.cap.release()
        cv2.destroyAllWindows()
        self.serial.stop()
        if self.pose:
            self.pose.close()
        print("✓ Shutdown complete")

if __name__ == "__main__":
    try:
        gui = MirrorGUI()
        gui.run()
    except KeyboardInterrupt:
        print("\n✓ Interrupted by user")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
