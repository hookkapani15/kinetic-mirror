#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Firmware Communication Test
Tests if we can communicate with ESP32 firmware
"""

import sys
from pathlib import Path
import time

# Add project root to path
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "tooling"))
sys.path.insert(0, str(REPO_ROOT / "packages"))

from base_test import BaseTest


class FirmwareCommunicationTest(BaseTest):
    """Test communication with ESP32 firmware"""
    
    def __init__(self, port: str = None, baud: int = 460800):
        super().__init__("Firmware Communication Test")
        self.port = port
        self.baud = baud
    
    def run(self):
        # First check if serial port is available
        try:
            import serial
            import serial.tools.list_ports
        except ImportError:
            return self.fail_test(
                "pyserial not installed",
                suggested_actions=["Install pyserial: pip install pyserial"],
                confidence=1.0
            )
        
        # Find port
        ports = list(serial.tools.list_ports.comports())
        if not ports:
            return self.skip_test("No serial ports available")
        
        test_port = self.port
        if test_port is None:
            # Auto-detect
            for p in ports:
                desc = p.description.lower()
                if any(kw in desc for kw in ['ch340', 'cp210', 'usb-serial', 'uart']):
                    test_port = p.device
                    break
        
        if test_port is None:
            return self.skip_test("Could not auto-detect ESP32 port")
        
        # Try to communicate
        try:
            ser = serial.Serial(test_port, self.baud, timeout=2)
            time.sleep(0.5)  # Give ESP32 time to boot if just connected
            
            # Check if we're receiving any data
            ser.reset_input_buffer()
            time.sleep(1)
            waiting = ser.in_waiting
            
            if waiting > 0:
                # ESP32 is sending data
                sample_data = ser.read(min(waiting, 100))
                ser.close()
                
                return self.pass_test(
                    f"ESP32 is transmitting data on {test_port}",
                    metrics={
                        "port": test_port,
                        "baud": self.baud,
                        "bytes_waiting": waiting,
                        "sample_data_len": len(sample_data)
                    },
                    learns={
                        "firmware_responsive": True,
                        "last_comm_port": test_port
                    },
                    confidence=0.9
                )
            else:
                # No data, but port is open
                ser.close()
                
                return self.fail_test(
                    f"ESP32 connected on {test_port} but not transmitting data",
                    suggested_actions=[
                        "Check if firmware is flashed correctly",
                        "Verify ESP32 is powered and booted",
                        "Try resetting ESP32",
                        "Check if firmware is in infinite loop"
                    ],
                    metrics={
                        "port": test_port,
                        "baud": self.baud,
                        "bytes_waiting": 0
                    },
                    confidence=0.7
                )
        
        except serial.SerialException as e:
            return self.fail_test(
                f"Serial communication error: {str(e)}",
                suggested_actions=[
                    "Close other programs using the port",
                    "Reset ESP32",
                    "Try different baud rate"
                ],
                confidence=0.8
            )


if __name__ == "__main__":
    test = FirmwareCommunicationTest()
    result = test.execute()
    
    print(f"\n{result['test_name']}")
    print(f"Status: {result['status']}")
    print(f"Details: {result['details']}")
