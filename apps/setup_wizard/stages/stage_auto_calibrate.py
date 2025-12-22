#!/usr/bin/env python3
"""
LED Auto-Calibration Stage
Uses camera to automatically detect panel positions and generate mapping config.
"""
import time
import json
import os
from datetime import datetime
from pathlib import Path
import numpy as np
from .base_stage import BaseStage, CheckResult, StageResult


class AutoCalibrationStage(BaseStage):
    """Auto-detect LED panel mapping using camera."""
    
    def __init__(self, port: str = None):
        super().__init__(
            name="LED Auto-Calibration",
            description="Using camera to detect panel positions..."
        )
        self.port = port
        self.mapping = {}  # logical_panel -> physical_position
        self.confidence = []
    
    def run(self, callback=None) -> StageResult:
        checks = []
        
        # Import dependencies
        try:
            import cv2
            import serial
        except ImportError as e:
            checks.append(CheckResult(
                name="Dependencies",
                passed=False,
                message=f"Missing: {e}",
                fix_instructions=["pip install opencv-python pyserial"]
            ))
            return self._make_result(checks)
        
        if not self.port:
            checks.append(CheckResult(
                name="Port",
                passed=False,
                message="No ESP32 port configured",
                fix_instructions=["Complete ESP32 connection stage first"]
            ))
            return self._make_result(checks)
        
        # Open camera
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            checks.append(CheckResult(
                name="Camera",
                passed=False,
                message="Cannot open camera",
                fix_instructions=["Connect webcam", "Close other apps using camera"]
            ))
            return self._make_result(checks)
        
        # Set camera properties for better detection
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        checks.append(CheckResult(
            name="Camera",
            passed=True,
            message="Camera ready"
        ))
        if callback:
            callback("Camera", True, "Camera ready")
        
        # Open serial
        try:
            ser = serial.Serial(self.port, 460800, timeout=1)
            time.sleep(0.5)
            checks.append(CheckResult(
                name="Serial",
                passed=True,
                message=f"Connected to {self.port}"
            ))
            if callback:
                callback("Serial", True, f"Connected to {self.port}")
        except Exception as e:
            cap.release()
            checks.append(CheckResult(
                name="Serial",
                passed=False,
                message=str(e),
                fix_instructions=["Check ESP32 connection"]
            ))
            return self._make_result(checks)
        
        try:
            # Step 1: Capture baseline (all LEDs off)
            self._send_all_off(ser)
            time.sleep(0.3)
            
            # Warm up camera (discard first few frames)
            for _ in range(5):
                cap.read()
            
            ret, baseline = cap.read()
            if not ret:
                checks.append(CheckResult(
                    name="Baseline",
                    passed=False,
                    message="Failed to capture baseline",
                    fix_instructions=["Check camera connection"]
                ))
                return self._make_result(checks)
            
            baseline_gray = cv2.cvtColor(baseline, cv2.COLOR_BGR2GRAY)
            baseline_gray = cv2.GaussianBlur(baseline_gray, (21, 21), 0)
            
            checks.append(CheckResult(
                name="Baseline Capture",
                passed=True,
                message="Captured dark reference frame"
            ))
            if callback:
                callback("Baseline", True, "Dark reference captured")
            
            # Step 2: Test each logical panel
            detected_positions = {}
            
            for logical_panel in range(1, 9):
                # Light up this logical panel
                self._light_panel(ser, logical_panel)
                time.sleep(0.4)  # Wait for LEDs to stabilize
                
                # Capture frame
                for _ in range(3):  # Skip a few frames for camera to adjust
                    cap.read()
                ret, frame = cap.read()
                
                if not ret:
                    continue
                
                # Convert to grayscale
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gray = cv2.GaussianBlur(gray, (21, 21), 0)
                
                # Subtract baseline to find bright region
                diff = cv2.absdiff(gray, baseline_gray)
                _, thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)
                
                # Find contours
                contours, _ = cv2.findContours(
                    thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
                )
                
                if contours:
                    # Find largest contour
                    largest = max(contours, key=cv2.contourArea)
                    
                    # Get centroid
                    M = cv2.moments(largest)
                    if M["m00"] > 0:
                        cx = int(M["m10"] / M["m00"])
                        cy = int(M["m01"] / M["m00"])
                        
                        # Map centroid to physical panel position (1-8)
                        # 2 columns x 4 rows
                        h, w = frame.shape[:2]
                        col = 0 if cx < w / 2 else 1
                        row = min(3, int(cy / (h / 4)))
                        
                        physical_pos = row * 2 + col + 1
                        
                        detected_positions[logical_panel] = physical_pos
                        confidence = min(1.0, cv2.contourArea(largest) / 5000)
                        self.confidence.append(confidence)
                        
                        match = "✓" if logical_panel == physical_pos else "→"
                        checks.append(CheckResult(
                            name=f"Panel {logical_panel}",
                            passed=True,
                            message=f"{match} Detected at position {physical_pos}",
                            details={
                                "logical": logical_panel,
                                "physical": physical_pos,
                                "centroid": (cx, cy),
                                "confidence": confidence
                            }
                        ))
                        if callback:
                            callback(f"Panel {logical_panel}", True, 
                                     f"Detected at position {physical_pos}")
                    else:
                        checks.append(CheckResult(
                            name=f"Panel {logical_panel}",
                            passed=False,
                            message="Could not find centroid",
                            fix_instructions=["Ensure camera can see LED panels"]
                        ))
                else:
                    checks.append(CheckResult(
                        name=f"Panel {logical_panel}",
                        passed=False,
                        message="No bright region detected",
                        fix_instructions=[
                            "Ensure LEDs are powered",
                            "Aim camera at LED panels",
                            "Reduce ambient lighting"
                        ]
                    ))
                
                # Brief pause between panels
                self._send_all_off(ser)
                time.sleep(0.2)
            
            # Step 3: Generate and save mapping
            self.mapping = detected_positions
            
            if len(detected_positions) >= 6:  # At least 6 panels detected
                # Save mapping
                mapping_file = self._save_mapping(detected_positions)
                
                checks.append(CheckResult(
                    name="Mapping Saved",
                    passed=True,
                    message=f"Config saved to {mapping_file}",
                    details={"mapping": detected_positions}
                ))
                if callback:
                    callback("Save", True, f"Saved to {mapping_file}")
            else:
                checks.append(CheckResult(
                    name="Mapping",
                    passed=False,
                    message=f"Only {len(detected_positions)}/8 panels detected",
                    fix_instructions=[
                        "Ensure all panels are powered",
                        "Adjust camera position",
                        "Reduce ambient light"
                    ]
                ))
            
        except Exception as e:
            checks.append(CheckResult(
                name="Calibration",
                passed=False,
                message=f"Error: {str(e)}",
                fix_instructions=["Try again", "Check connections"]
            ))
        finally:
            self._send_all_off(ser)
            ser.close()
            cap.release()
        
        return self._make_result(checks)
    
    def _send_all_off(self, ser):
        """Turn off all LEDs."""
        packet = bytes([0xAA, 0xBB, 0x01]) + bytes([0] * 2048)
        ser.write(packet)
        ser.flush()
    
    def _light_panel(self, ser, logical_panel: int):
        """Light up a single logical panel (1-8)."""
        frame = np.zeros(2048, dtype=np.uint8)
        
        # Calculate panel position in 32x64 grid
        # Panels are 16x16, arranged as 2 cols x 4 rows
        panel_row = (logical_panel - 1) // 2
        panel_col = (logical_panel - 1) % 2
        
        # Light up this panel
        for y in range(16):
            for x in range(16):
                global_x = panel_col * 16 + x
                global_y = panel_row * 16 + y
                idx = global_y * 32 + global_x
                if idx < 2048:
                    frame[idx] = 255
        
        packet = bytes([0xAA, 0xBB, 0x01]) + frame.tobytes()
        ser.write(packet)
        ser.flush()
    
    def _save_mapping(self, mapping: dict) -> str:
        """Save mapping to JSON file."""
        # Get project data directory
        project_root = Path(__file__).parents[3]
        data_dir = project_root / "data"
        data_dir.mkdir(exist_ok=True)
        
        mapping_file = data_dir / "led_mapping.json"
        
        config = {
            "version": 1,
            "detected_at": datetime.now().isoformat(),
            "mapping": {str(k): v for k, v in mapping.items()},
            "confidence": self.confidence,
            "description": "Auto-detected LED panel mapping. logical_panel -> physical_position"
        }
        
        with open(mapping_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        return str(mapping_file)
