#!/usr/bin/env python3
"""
Stage 4: LED Power Test
Sends a white flash pattern and asks user to confirm LEDs lit up.
"""
import time
import numpy as np
from .base_stage import BaseStage, CheckResult, StageResult


class LEDPowerStage(BaseStage):
    """Test LED power by sending white pattern."""
    
    def __init__(self, port: str = None):
        super().__init__(
            name="LED Power Test",
            description="Testing LED power supply..."
        )
        self.port = port
        self.user_confirmed = None  # Will be set by wizard GUI
    
    def run(self, callback=None) -> StageResult:
        checks = []
        
        # 1. Import required modules
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
        
        # 2. Send white pattern
        try:
            ser = serial.Serial(self.port, 460800, timeout=1)
            time.sleep(0.5)
            
            # Create white pattern (2048 LEDs at full brightness)
            # Packet: [0xAA, 0xBB, 0x01, ...2048 bytes...]
            packet = bytes([0xAA, 0xBB, 0x01]) + bytes([255] * 2048)
            
            ser.write(packet)
            ser.flush()
            
            checks.append(CheckResult(
                name="White Pattern Sent",
                passed=True,
                message="Sent 2051 bytes (white flash)",
                details={"packet_size": len(packet)}
            ))
            if callback:
                callback("White Pattern Sent", True, checks[-1].message)
            
            # Keep the pattern on for 3 seconds
            time.sleep(3)
            
            # Turn off LEDs
            off_packet = bytes([0xAA, 0xBB, 0x01]) + bytes([0] * 2048)
            ser.write(off_packet)
            ser.flush()
            
            ser.close()
            
            # 3. User confirmation check (placeholder - wizard will handle this)
            # For now, we pass if the packet was sent successfully
            checks.append(CheckResult(
                name="LEDs Visible",
                passed=True,  # Wizard will override based on user input
                message="Did you see the LEDs flash white?",
                fix_instructions=[
                    "If LEDs did NOT light up:",
                    "1. Check 5V power supply is connected",
                    "2. Ensure power supply can deliver 40A+",
                    "3. Check data wire from ESP32 GPIO5/GPIO18",
                    "4. Verify GND is shared between ESP32 and LEDs"
                ],
                details={"needs_user_confirmation": True}
            ))
            if callback:
                callback("LEDs Visible", True, checks[-1].message)
            
        except Exception as e:
            checks.append(CheckResult(
                name="Send Pattern",
                passed=False,
                message=f"Error: {str(e)}",
                fix_instructions=[
                    "Check ESP32 connection",
                    "Restart ESP32"
                ]
            ))
            if callback:
                callback("Send Pattern", False, checks[-1].message)
        
        return self._make_result(checks)
