#!/usr/bin/env python3
"""
Stage 5: LED Mapping Test
Tests each panel individually for correct wiring.
"""
import time
import numpy as np
from .base_stage import BaseStage, CheckResult, StageResult


class LEDMappingStage(BaseStage):
    """Test LED panel mapping by lighting each panel individually."""
    
    def __init__(self, port: str = None):
        super().__init__(
            name="LED Panel Mapping",
            description="Testing individual LED panels..."
        )
        self.port = port
        self.panel_results = {}  # Panel number -> user confirmed position
    
    def run(self, callback=None) -> StageResult:
        checks = []
        
        try:
            import serial
        except ImportError:
            checks.append(CheckResult(
                name="PySerial Import",
                passed=False,
                message="PySerial not available",
                fix_instructions=["Complete Stage 1 first"]
            ))
            return self._make_result(checks)
        
        if not self.port:
            checks.append(CheckResult(
                name="Port Configuration",
                passed=False,
                message="No port specified",
                fix_instructions=["Complete Stage 3 first"]
            ))
            return self._make_result(checks)
        
        try:
            ser = serial.Serial(self.port, 460800, timeout=1)
            time.sleep(0.5)
            
            # Test each panel (1-8)
            panel_positions = {
                1: "Top-Left",
                2: "Top-Right", 
                3: "Upper-Mid-Left",
                4: "Upper-Mid-Right",
                5: "Lower-Mid-Left",
                6: "Lower-Mid-Right",
                7: "Bottom-Left",
                8: "Bottom-Right"
            }
            
            for panel_num in range(1, 9):
                # Create pattern that lights only this panel
                frame = np.zeros(2048, dtype=np.uint8)
                
                # Calculate panel position in the 32x64 grid
                # Panels are 16x16, arranged as 2 columns x 4 rows
                panel_row = (panel_num - 1) // 2
                panel_col = (panel_num - 1) % 2
                
                # Light up this panel only
                for y in range(16):
                    for x in range(16):
                        global_x = panel_col * 16 + x
                        global_y = panel_row * 16 + y
                        idx = global_y * 32 + global_x
                        if idx < 2048:
                            frame[idx] = 255
                
                # Send packet
                packet = bytes([0xAA, 0xBB, 0x01]) + frame.tobytes()
                ser.write(packet)
                ser.flush()
                
                expected_pos = panel_positions.get(panel_num, "Unknown")
                checks.append(CheckResult(
                    name=f"Panel {panel_num}",
                    passed=True,  # Wizard will verify with user
                    message=f"Expected: {expected_pos}",
                    fix_instructions=[
                        f"If Panel {panel_num} is NOT at {expected_pos}:",
                        "1. Note actual position",
                        "2. Check wiring order",
                        "3. Update LED mapping in config"
                    ],
                    details={
                        "panel": panel_num,
                        "expected_position": expected_pos,
                        "needs_user_confirmation": True
                    }
                ))
                if callback:
                    callback(f"Panel {panel_num}", True, f"Expected: {expected_pos}")
                
                time.sleep(1.5)  # Show each panel briefly
            
            # Turn off all LEDs
            off_packet = bytes([0xAA, 0xBB, 0x01]) + bytes([0] * 2048)
            ser.write(off_packet)
            ser.flush()
            ser.close()
            
        except Exception as e:
            checks.append(CheckResult(
                name="Panel Test",
                passed=False,
                message=f"Error: {str(e)}",
                fix_instructions=["Check ESP32 connection"]
            ))
        
        return self._make_result(checks)
