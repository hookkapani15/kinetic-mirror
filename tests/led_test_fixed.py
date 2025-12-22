import sys
import time
import numpy as np
import cv2
import serial
from pathlib import Path
from serial.tools import list_ports

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from packages.mirror_core.controllers.led_controller import LEDController
from packages.mirror_core.testing.led_panel_tester import LEDPanelTester

def find_esp32_port():
    """Find the ESP32 port by looking for the Silicon Labs CP210x USB-to-UART Bridge"""
    ports = list_ports.comports()
    for port in ports:
        if 'Silicon Labs CP210x' in port.description:
            return port.device
    return None

def main():
    print("=== LED Panel Test ===")
    
    # Find ESP32 port
    port = find_esp32_port()
    if not port:
        print("ERROR: ESP32 not found. Please make sure it's connected.")
        print("Available ports:")
        for p in list_ports.comports():
            print(f"- {p.device}: {p.description}")
        return
    
    print(f"Found ESP32 on {port}")
    
    try:
        # Initialize LED controller and tester
        led = LEDController(width=32, height=64)
        tester = LEDPanelTester()
        
        # Test patterns
        patterns = [
            ("All White", tester.generate_panel_test_pattern),
            ("Panel 1", lambda: tester.generate_individual_panel_test(1)),
            ("Panel 2", lambda: tester.generate_individual_panel_test(2)),
            ("Panel 3", lambda: tester.generate_individual_panel_test(3)),
            ("Panel 4", lambda: tester.generate_individual_panel_test(4)),
            ("Panel 5", lambda: tester.generate_individual_panel_test(5)),
            ("Panel 6", lambda: tester.generate_individual_panel_test(6)),
            ("Panel 7", lambda: tester.generate_individual_panel_test(7)),
            ("Panel 8", lambda: tester.generate_individual_panel_test(8)),
            ("Gradient", tester.generate_gradient_test),
            ("Checkerboard", tester.generate_checkerboard_test),
            ("Borders", tester.generate_panel_border_test)
        ]
        
        # Test each pattern
        for name, pattern_func in patterns:
            print(f"\nTesting: {name}")
            print("Press 'n' for next, 'q' to quit")
            
            try:
                # Generate and send pattern
                pattern = pattern_func()
                packet = led.pack_led_packet(pattern)
                
                # Send to ESP32
                with serial.Serial(port, 460800, timeout=1) as ser:
                    # Switch to serial mode
                    ser.write(b's\n')
                    time.sleep(0.5)
                    
                    # Send pattern
                    ser.write(packet)
                    ser.flush()
                    print(f"Sent {len(packet)} bytes")
                
                # Wait for user input
                while True:
                    key = input("> ").lower()
                    if key == 'n':
                        break
                    elif key == 'q':
                        return
                    
            except Exception as e:
                print(f"ERROR in {name}: {e}")
                time.sleep(1)
                
    except Exception as e:
        print(f"FATAL ERROR: {e}")
    finally:
        print("\nTest complete!")

if __name__ == "__main__":
    main()
