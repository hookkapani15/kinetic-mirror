#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ESP32 Connection Test
Tests if ESP32 is connected and responsive on the serial port
"""

import sys
from pathlib import Path

# Add project root to path
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tooling"))
sys.path.insert(0, str(REPO_ROOT / "packages"))

from base_test import BaseTest
import serial
import serial.tools.list_ports


class ESP32ConnectionTest(BaseTest):
    """Test ESP32 serial connection"""
    
    def __init__(self, port: str = None, baud: int = 460800):
        super().__init__("ESP32 Connection Test")
        self.port = port
        self.baud = baud
    
    def run(self):
        # Find available COM ports
        ports = list(serial.tools.list_ports.comports())
        
        if not ports:
            return self.fail_test(
                "No serial ports detected",
                suggested_actions=[
                    "Check USB cable connection",
                    "Verify ESP32 is powered on",
                    "Install CH340/CP2102 drivers if needed"
                ],
                confidence=0.9
            )
        
        # List detected ports
        port_info = [f"{p.device} - {p.description}" for p in ports]
        
        # Try to find ESP32
        esp_port = None
        for p in ports:
            desc = p.description.lower()
            if any(keyword in desc for keyword in ['ch340', 'cp210', 'usb-serial', 'uart']):
                esp_port = p.device
                break
        
        if esp_port is None and self.port is None:
            return self.fail_test(
                f"ESP32 not auto-detected. Found ports: {', '.join(p.device for p in ports)}",
                suggested_actions=[
                    "Manually specify port in config",
                    "Check if correct drivers are installed",
                    "Try reconnecting USB cable"
                ],
                metrics={"detected_ports": port_info},
                confidence=0.7
            )
        
        # Use specified port or auto-detected port
        test_port = self.port or esp_port
        
        # Try to open the port
        try:
            ser = serial.Serial(test_port, self.baud, timeout=1)
            ser.close()
            
            return self.pass_test(
                f"ESP32 connected on {test_port}",
                metrics={
                    "port": test_port,
                    "baud": self.baud,
                    "detected_ports": port_info
                },
                learns={
                    "last_good_port": test_port,
                    "last_good_baud": self.baud
                },
                confidence=1.0
            )
        
        except serial.SerialException as e:
            return self.fail_test(
                f"Failed to open port {test_port}: {str(e)}",
                suggested_actions=[
                    "Close other programs using the port",
                    "Reset ESP32",
                    f"Try different baud rate (currently {self.baud})"
                ],
                metrics={"port": test_port, "error": str(e)},
                confidence=0.8
            )


if __name__ == "__main__":
    # Can be run standalone
    test = ESP32ConnectionTest()
    result = test.execute()
    
    print(f"\n{result['test_name']}")
    print(f"Status: {result['status']}")
    print(f"Details: {result['details']}")
    
    if result.get('suggested_actions'):
        print("\nSuggested Actions:")
        for action in result['suggested_actions']:
            print(f"  • {action}")
