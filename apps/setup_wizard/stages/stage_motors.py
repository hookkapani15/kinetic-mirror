#!/usr/bin/env python3
"""
Stage 6: Motor Test
Tests servo motor movement.
"""
import time
from .base_stage import BaseStage, CheckResult, StageResult


class MotorStage(BaseStage):
    """Test motor/servo functionality."""
    
    def __init__(self, port: str = None):
        super().__init__(
            name="Motor Test",
            description="Testing servo motors..."
        )
        self.port = port
    
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
            
            def make_servo_packet(angles):
                """Create servo packet from list of 64 angles (0-180)."""
                packet = [0xAA, 0xBB, 0x02]
                for angle in angles:
                    # Pack as single byte (0-180)
                    packet.append(max(0, min(180, int(angle))))
                return bytes(packet)
            
            # Test 1: Center all motors
            packet = make_servo_packet([90] * 64)
            ser.write(packet)
            ser.flush()
            time.sleep(1)
            
            checks.append(CheckResult(
                name="Center Position",
                passed=True,
                message="Sent center command (90°)",
                details={"angle": 90}
            ))
            if callback:
                callback("Center Position", True, "Motors at 90°")
            
            # Test 2: Sweep to min
            packet = make_servo_packet([45] * 64)
            ser.write(packet)
            ser.flush()
            time.sleep(1)
            
            checks.append(CheckResult(
                name="Sweep Left",
                passed=True,
                message="Sent left sweep (45°)",
                details={"angle": 45}
            ))
            if callback:
                callback("Sweep Left", True, "Motors at 45°")
            
            # Test 3: Sweep to max
            packet = make_servo_packet([135] * 64)
            ser.write(packet)
            ser.flush()
            time.sleep(1)
            
            checks.append(CheckResult(
                name="Sweep Right",
                passed=True,
                message="Sent right sweep (135°)",
                details={"angle": 135}
            ))
            if callback:
                callback("Sweep Right", True, "Motors at 135°")
            
            # Return to center
            packet = make_servo_packet([90] * 64)
            ser.write(packet)
            ser.flush()
            
            ser.close()
            
            # User confirmation
            checks.append(CheckResult(
                name="Motors Visible",
                passed=True,  # Wizard will handle user input
                message="Did the motors move?",
                fix_instructions=[
                    "If motors did NOT move:",
                    "1. Check PCA9685 I2C connection (SDA/SCL)",
                    "2. Ensure servo power supply is connected",
                    "3. Check servo signal wires",
                    "4. Verify I2C address (default 0x40)"
                ],
                details={"needs_user_confirmation": True}
            ))
            if callback:
                callback("Motors Visible", True, "Did motors move?")
            
        except Exception as e:
            checks.append(CheckResult(
                name="Motor Test",
                passed=False,
                message=f"Error: {str(e)}",
                fix_instructions=["Check ESP32 connection"]
            ))
        
        return self._make_result(checks)
