import sys
import time
import serial.tools.list_ports
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from packages.mirror_core.controllers.led_controller import LEDController
from packages.mirror_core.testing.led_panel_tester import LEDPanelTester

def find_esp32_port():
    """Find the ESP32 port by looking for the Silicon Labs CP210x USB-to-UART Bridge"""
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if 'Silicon Labs CP210x' in port.description:
            return port.device
    return None

def run_led_tests(port=None):
    print("=== LED Panel Test ===")
    print("Looking for ESP32...")
    
    # Use provided port or try to find ESP32
    if not port:
        port = find_esp32_port()
        if not port:
            print("[ERROR] ESP32 not found. Please specify port or check connection.")
            print("Available ports:")
            for p in serial.tools.list_ports.comports():
                print(f"- {p.device}: {p.description}")
            return
    
    print(f"Found ESP32 on {port}")
    
    try:
        # Initialize LED tester
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
            
            try:
                # Generate pattern
                pattern = pattern_func()
                
                # Convert to packet
                led = LEDController(width=32, height=64)
                packet = led.pack_led_packet(pattern)
                
                # Send to ESP32
                with serial.Serial(port, 460800, timeout=1) as ser:
                    ser.write(packet)
                    ser.flush()
                    print(f"Sent {len(packet)} bytes to {port}")
                    
                # Wait a bit between patterns
                time.sleep(2)
                    
            except Exception as e:
                print(f"[ERROR] in {name}: {e}")
                time.sleep(1)
                
    except Exception as e:
        print(f"[ERROR] Fatal error: {e}")
    finally:
        print("\nTest complete!")
        # Keep the program running for 30 seconds to view the last pattern
        time.sleep(30)

if __name__ == "__main__":
    import sys
    port = sys.argv[1] if len(sys.argv) > 1 else None
    run_led_tests(port)
