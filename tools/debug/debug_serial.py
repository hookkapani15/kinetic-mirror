#!/usr/bin/env python3
"""
Quick Serial Debug - Tests ESP32 connection and sends test packets
Run this STANDALONE to verify motors and LEDs work before using main GUI
"""
import sys
import time
import serial
import serial.tools.list_ports
import numpy as np
from pathlib import Path

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent / "packages"))

def list_ports():
    """List all available COM ports"""
    print("\n" + "="*60)
    print("  AVAILABLE SERIAL PORTS")
    print("="*60)
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        print("  [ERROR] No serial ports found!")
        return None
    
    esp_port = None
    for p in ports:
        marker = ""
        if "USB" in p.description or "CH340" in p.description or "CP210" in p.description:
            marker = " <-- LIKELY ESP32"
            if not esp_port:
                esp_port = p.device
        print(f"  {p.device}: {p.description}{marker}")
    
    return esp_port

def test_connection(port, baud=115200):
    """Test serial connection to ESP32"""
    print(f"\n" + "="*60)
    print(f"  TESTING CONNECTION: {port} @ {baud}")
    print("="*60)
    
    try:
        ser = serial.Serial(port, baud, timeout=2)
        print(f"  [OK] Opened {port}")
        
        # Reset ESP32
        print("  [..] Resetting ESP32...")
        ser.dtr = False
        ser.rts = False
        time.sleep(0.1)
        ser.dtr = True
        ser.rts = True
        time.sleep(0.1)
        ser.dtr = False
        ser.rts = False
        
        # Wait for boot messages
        print("  [..] Waiting for ESP32 boot (5s)...")
        time.sleep(2)
        
        # Read any output
        if ser.in_waiting:
            data = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
            print("\n  ESP32 Output:")
            for line in data.strip().split('\n'):
                if line.strip():
                    print(f"    {line.strip()}")
        
        # Check for READY
        start = time.time()
        ready = False
        while time.time() - start < 10:
            if ser.in_waiting:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    print(f"    {line}")
                if 'READY' in line:
                    ready = True
                    break
            time.sleep(0.1)
        
        if ready:
            print("\n  [OK] ESP32 is READY!")
        else:
            print("\n  [WARN] No READY signal, but connection is open")
        
        return ser
        
    except Exception as e:
        print(f"  [ERROR] Connection failed: {e}")
        return None

def test_leds(ser):
    """Send LED test packet"""
    print("\n" + "="*60)
    print("  TESTING LEDs - Sending WHITE flash")
    print("="*60)
    
    # Create white pattern (64x32 = 2048 pixels)
    pattern = np.full(2048, 255, dtype=np.uint8)
    
    # Pack packet: 0xAA 0xBB 0x01 + 2048 bytes
    packet = bytes([0xAA, 0xBB, 0x01]) + pattern.tobytes()
    
    print(f"  [INFO] Packet size: {len(packet)} bytes")
    print(f"  [INFO] Header: 0x{packet[0]:02X} 0x{packet[1]:02X} 0x{packet[2]:02X}")
    
    try:
        ser.write(packet)
        print("  [OK] LED packet sent!")
        print("  [CHECK] Look at your LED panels - they should be WHITE")
        time.sleep(1)
        
        # Send black to turn off
        pattern = np.zeros(2048, dtype=np.uint8)
        packet = bytes([0xAA, 0xBB, 0x01]) + pattern.tobytes()
        ser.write(packet)
        print("  [OK] LEDs turned off")
        
    except Exception as e:
        print(f"  [ERROR] LED send failed: {e}")

def test_motors(ser):
    """Send motor test packet"""
    print("\n" + "="*60)
    print("  TESTING MOTORS - Sending sweep")
    print("="*60)
    
    # 32 servos, each 2 bytes (big-endian uint16, 0-1000 maps to 0-180)
    # Center = 500 = 90
    
    def make_servo_packet(angles):
        """Create servo packet from list of 32 angles (0-180)"""
        packet = [0xAA, 0xBB, 0x02]
        for angle in angles:
            value = int((angle / 180.0) * 1000)
            value = max(0, min(1000, value))
            packet.append((value >> 8) & 0xFF)
            packet.append(value & 0xFF)
        return bytes(packet)
    
    try:
        # Center all
        print("  [INFO] Moving to CENTER (90 degrees)...")
        packet = make_servo_packet([90] * 32)
        print(f"  [INFO] Packet size: {len(packet)} bytes (expect 67)")
        ser.write(packet)
        time.sleep(1)
        
        # Min
        print("  [INFO] Moving to MIN (0 degrees)...")
        packet = make_servo_packet([0] * 32)
        ser.write(packet)
        time.sleep(1)
        
        # Max
        print("  [INFO] Moving to MAX (180 degrees)...")
        packet = make_servo_packet([180] * 32)
        ser.write(packet)
        time.sleep(1)
        
        # Back to center
        print("  [INFO] Moving back to CENTER...")
        packet = make_servo_packet([90] * 32)
        ser.write(packet)
        
        print("  [OK] Motor test complete!")
        print("  [CHECK] Did the servos move? If not, check PCA9685 wiring.")
        
    except Exception as e:
        print(f"  [ERROR] Motor send failed: {e}")

def main():
    print("\n" + "="*60)
    print("  [DEBUG] MIRROR BODY ANIMATIONS - SERIAL DEBUG TOOL")
    print("="*60)
    
    # Step 1: Find ports
    esp_port = list_ports()
    
    if not esp_port:
        print("\n[ERROR] No ESP32 found. Check USB connection!")
        return
    
    # Step 2: Connect
    ser = test_connection(esp_port)
    
    if not ser:
        print("\n[ERROR] Could not connect to ESP32!")
        return
    
    # Step 3: Test LEDs
    input("\n  Press ENTER to test LEDs...")
    test_leds(ser)
    
    # Step 4: Test Motors
    input("\n  Press ENTER to test Motors...")
    test_motors(ser)
    
    # Cleanup
    ser.close()
    print("\n" + "="*60)
    print("  [OK] DEBUG COMPLETE")
    print("="*60)
    print("\n  If LEDs and motors worked here but not in main GUI,")
    print("  the issue is in the GUI code, not hardware.")
    print("\n  If they didn't work here either, check:")
    print("    1. ESP32 firmware is flashed correctly")
    print("    2. Wiring to LED panels and PCA9685")
    print("    3. Power supply to panels/servos")

if __name__ == "__main__":
    main()
