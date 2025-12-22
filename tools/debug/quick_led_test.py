"""
QUICK LED MAPPING TEST - Run this to verify the fix works!
============================================================
This script sends a simple test pattern to verify LED mapping is correct.

Run: python quick_led_test.py
"""

import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from packages.mirror_core.controllers.led_controller import LEDController
from packages.mirror_core.io.serial_manager import SerialManager
import numpy as np


def main():
    print("=" * 60)
    print("  QUICK LED MAPPING TEST")
    print("=" * 60)
    print()
    
    # Connect to ESP32
    print("Connecting to ESP32...")
    serial = SerialManager('AUTO', 460800)
    serial.start()
    time.sleep(2)
    
    if not serial.connected:
        print("❌ Failed to connect to ESP32!")
        print("Please check:")
        print("  1. ESP32 is connected via USB")
        print("  2. Correct COM port (try COM5)")
        print("  3. ESP32 firmware is running")
        return
    
    print(f"✅ Connected to {serial.port}")
    print()
    
    # Initialize LED controller
    led = LEDController(width=32, height=64)
    print(f"LED Controller Settings:")
    print(f"  flip_x = {led.flip_x}")
    print(f"  flip_y = {led.flip_y}")
    print()
    
    # Test patterns
    tests = [
        ("ALL WHITE", create_all_white),
        ("PANEL 1 ONLY (Top-Left)", lambda: create_single_panel(1)),
        ("PANEL 8 ONLY (Bottom-Right)", lambda: create_single_panel(8)),
        ("NUMBERS 1-8", create_numbers),
    ]
    
    for name, pattern_func in tests:
        print(f"📍 Testing: {name}")
        print("   Press ENTER to continue, or 'q' to quit...")
        
        pattern = pattern_func()
        packet = led.pack_led_packet(pattern)
        serial.send_led(packet)
        
        response = input("   > ").strip().lower()
        if response == 'q':
            break
    
    # Clear LEDs
    print("\nClearing LEDs...")
    clear = np.zeros((64, 32), dtype=np.uint8)
    serial.send_led(led.pack_led_packet(clear))
    
    serial.close()
    print("✅ Test complete!")
    print()
    print("If panels were in wrong positions:")
    print("  Edit: packages/mirror_core/controllers/led_controller.py")
    print("  Try:  flip_x = False  or  flip_y = False")


def create_all_white():
    """All LEDs white"""
    return np.full((64, 32), 255, dtype=np.uint8)


def create_single_panel(panel_id):
    """Light up a single panel"""
    pattern = np.zeros((64, 32), dtype=np.uint8)
    row = (panel_id - 1) // 2
    col = (panel_id - 1) % 2
    y_start, y_end = row * 16, (row + 1) * 16
    x_start, x_end = col * 16, (col + 1) * 16
    pattern[y_start:y_end, x_start:x_end] = 255
    return pattern


def create_numbers():
    """Display numbers 1-8 on each panel"""
    import cv2
    pattern = np.zeros((64, 32), dtype=np.uint8)
    
    for panel_id in range(1, 9):
        row = (panel_id - 1) // 2
        col = (panel_id - 1) % 2
        y_start = row * 16
        x_start = col * 16
        
        # Draw number
        text = str(panel_id)
        font = cv2.FONT_HERSHEY_SIMPLEX
        (tw, th), _ = cv2.getTextSize(text, font, 0.6, 2)
        x = x_start + (16 - tw) // 2
        y = y_start + (16 + th) // 2
        cv2.putText(pattern, text, (x, y), font, 0.6, 255, 2)
    
    return pattern


if __name__ == "__main__":
    main()
