"""
ESP32-S3 LED Test Script
Tests LED patterns by sending commands to ESP32-S3 over serial
"""
import sys
import time
import serial
import serial.tools.list_ports
import numpy as np
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

class ESP32LEDTester:
    def __init__(self, port=None, baudrate=460800):
        self.port = port
        self.baudrate = baudrate
        self.serial = None
        
    def connect(self):
        """Connect to the ESP32"""
        if not self.port:
            # Try to auto-detect ESP32-S3
            ports = serial.tools.list_ports.comports()
            esp_ports = [p for p in ports if 'Silicon Labs CP210x' in p.description]
            
            if not esp_ports:
                print("❌ No ESP32-S3 found. Please specify port manually.")
                return False
                
            self.port = esp_ports[0].device
        
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1
            )
            
            # Wait for ESP32 to boot
            time.sleep(2)
            
            # Clear any existing data
            self.serial.reset_input_buffer()
            
            # Read welcome message
            while self.serial.in_waiting > 0:
                line = self.serial.readline().decode('utf-8').strip()
                print(f"< {line}")
                if "Ready" in line:
                    break
                    
            print(f"✅ Connected to ESP32 on {self.port}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to connect to {self.port}: {e}")
            return False
    
    def send_command(self, cmd):
        """Send a command to the ESP32"""
        if not self.serial or not self.serial.is_open:
            print("❌ Not connected to ESP32")
            return False
            
        try:
            self.serial.write((cmd + '\n').encode('utf-8'))
            time.sleep(0.1)  # Small delay for command processing
            
            # Read response
            response = []
            while self.serial.in_waiting > 0:
                line = self.serial.readline().decode('utf-8').strip()
                response.append(line)
                print(f"< {line}")
                
            return response
            
        except Exception as e:
            print(f"❌ Error sending command: {e}")
            return None
    
    def run_test_pattern(self, pattern_num):
        """Run a built-in test pattern on the ESP32"""
        if not (0 <= pattern_num <= 9):
            print("❌ Pattern number must be between 0 and 9")
            return False
            
        print(f"\n=== Running Test Pattern {pattern_num} ===")
        return self.send_command(str(pattern_num))
    
    def send_led_packet(self, data):
        """Send a custom LED packet to the ESP32"""
        if not self.serial or not self.serial.is_open:
            print("❌ Not connected to ESP32")
            return False
            
        try:
            # Switch to serial mode if not already
            self.send_command('s')
            
            # Create packet: 0xAA 0xBB 0x01 [2048 bytes of data]
            packet = bytes([0xAA, 0xBB, 0x01]) + bytes(data)
            
            # Send packet
            self.serial.write(packet)
            self.serial.flush()
            
            print(f"✅ Sent LED packet ({len(packet)} bytes)")
            return True
            
        except Exception as e:
            print(f"❌ Error sending LED packet: {e}")
            return False
    
    def clear_leds(self):
        """Clear all LEDs"""
        print("\n=== Clearing LEDs ===")
        return self.send_command('c')
    
    def close(self):
        """Close the serial connection"""
        if self.serial and self.serial.is_open:
            self.serial.close()
            print("\nDisconnected from ESP32")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Test ESP32-S3 LED Patterns')
    parser.add_argument('--port', type=str, help='Serial port (e.g., COM5 or /dev/ttyUSB0)')
    parser.add_argument('--pattern', type=int, choices=range(10), 
                       help='Test pattern number (0-9)')
    
    args = parser.parse_args()
    
    # Initialize tester
    tester = ESP32LEDTester(port=args.port)
    
    try:
        # Connect to ESP32
        if not tester.connect():
            return
        
        # Run specific pattern if specified
        if args.pattern is not None:
            tester.run_test_pattern(args.pattern)
            input("Press Enter to continue...")
            return
        
        # Interactive mode
        print("\n=== ESP32 LED Tester ===")
        print("0-9: Run test pattern")
        print("c: Clear LEDs")
        print("q: Quit")
        
        while True:
            cmd = input("\nEnter command: ").strip().lower()
            
            if cmd == 'q':
                break
            elif cmd == 'c':
                tester.clear_leds()
            elif cmd.isdigit() and 0 <= int(cmd) <= 9:
                tester.run_test_pattern(int(cmd))
            else:
                print("❌ Invalid command")
                
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
    finally:
        tester.close()

if __name__ == "__main__":
    main()
