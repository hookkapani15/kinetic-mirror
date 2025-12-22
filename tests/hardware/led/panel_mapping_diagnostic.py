"""
LED MAPPING DIAGNOSTIC TOOL
============================
This tool helps you discover the ACTUAL physical wiring of your 8 LED panels.

HARDWARE SETUP:
- 8 x 16x16 LED panels (WS2812B)
- Connected via GPIO 5 (LEFT - 1024 LEDs) and GPIO 18 (RIGHT - 1024 LEDs)
- Total: 2048 LEDs in a 32x64 grid

CURRENT PROBLEM:
- Panels don't light up in expected positions
- Need to map which panel number corresponds to which physical position

HOW TO USE:
1. Run this script
2. For each test (1-8), note which PHYSICAL panel lights up
3. Fill in the mapping table at the end
"""

import serial
import time
import numpy as np

# Serial configuration
PORT = "COM5"  # Change to your ESP32 port
BAUD = 460800

# LED grid configuration
TOTAL_WIDTH = 32
TOTAL_HEIGHT = 64
PANEL_WIDTH = 16
PANEL_HEIGHT = 16

def create_led_packet(pattern):
    """Create LED packet with header"""
    header = bytes([0xAA, 0xBB, 0x01])  # 0x01 = LED packet type
    data = pattern.flatten().tobytes()
    return header + data

def test_single_panel(panel_num):
    """
    Light up a single panel (1-8) to identify its physical location.
    
    Panel numbering (LOGICAL):
    1  2  (top row)
    3  4
    5  6
    7  8  (bottom row)
    
    Grid coordinates:
    Panel 1: x[0:16], y[0:16]   - Top-Left
    Panel 2: x[16:32], y[0:16]  - Top-Right
    Panel 3: x[0:16], y[16:32]  - Mid-Top-Left
    Panel 4: x[16:32], y[16:32] - Mid-Top-Right
    Panel 5: x[0:16], y[32:48]  - Mid-Bottom-Left
    Panel 6: x[16:32], y[32:48] - Mid-Bottom-Right
    Panel 7: x[0:16], y[48:64]  - Bottom-Left
    Panel 8: x[16:32], y[48:64] - Bottom-Right
    """
    pattern = np.zeros((TOTAL_HEIGHT, TOTAL_WIDTH), dtype=np.uint8)
    
    # Panel coordinates (x_start, y_start)
    panel_coords = {
        1: (0, 0),    # Top-Left
        2: (16, 0),   # Top-Right
        3: (0, 16),   # Mid-Top-Left
        4: (16, 16),  # Mid-Top-Right
        5: (0, 32),   # Mid-Bottom-Left
        6: (16, 32),  # Mid-Bottom-Right
        7: (0, 48),   # Bottom-Left
        8: (16, 48),  # Bottom-Right
    }
    
    if panel_num not in panel_coords:
        print(f"Invalid panel number: {panel_num}")
        return pattern
    
    x_start, y_start = panel_coords[panel_num]
    
    # Fill entire panel with white
    pattern[y_start:y_start+16, x_start:x_start+16] = 255
    
    # Draw large number in the center (simplified - just fill brighter for now)
    # You could add actual number rendering here
    pattern[y_start+6:y_start+10, x_start+6:x_start+10] = 255
    
    return pattern

def main():
    print("=" * 60)
    print("LED MAPPING DIAGNOSTIC TOOL")
    print("=" * 60)
    print()
    print("This will test each panel (1-8) individually.")
    print("For each test, note which PHYSICAL panel lights up.")
    print()
    
    # Connect to ESP32
    try:
        ser = serial.Serial(PORT, BAUD, timeout=1)
        print(f"✅ Connected to {PORT} at {BAUD} baud")
        time.sleep(2)  # Wait for ESP32 to be ready
    except Exception as e:
        print(f"❌ Failed to connect to {PORT}: {e}")
        print("\nPlease check:")
        print("1. ESP32 is connected")
        print("2. Correct COM port")
        print("3. ESP32 firmware is running")
        return
    
    print()
    print("=" * 60)
    print("STARTING PANEL TESTS")
    print("=" * 60)
    print()
    
    results = {}
    
    for panel_num in range(1, 9):
        print(f"\n📍 TEST {panel_num}/8: Lighting Panel {panel_num}")
        print(f"   Expected position: {get_panel_name(panel_num)}")
        print("-" * 60)
        
        # Create pattern for this panel
        pattern = test_single_panel(panel_num)
        
        # Send to ESP32
        packet = create_led_packet(pattern)
        ser.write(packet)
        
        # Ask user where they see the light
        print("\n❓ Which PHYSICAL position lit up?")
        print("   1=Top-Left, 2=Top-Right, 3=Mid-Top-L, 4=Mid-Top-R")
        print("   5=Mid-Bot-L, 6=Mid-Bot-R, 7=Bottom-L, 8=Bottom-R")
        
        response = input("   Enter position (1-8) or 's' to skip: ").strip()
        
        if response.isdigit():
            physical_pos = int(response)
            results[panel_num] = physical_pos
            print(f"   ✅ Recorded: Panel {panel_num} → Physical position {physical_pos}")
        else:
            results[panel_num] = "?"
            print(f"   ⏭️  Skipped panel {panel_num}")
        
        time.sleep(0.5)
    
    # Clear LEDs
    clear_pattern = np.zeros((TOTAL_HEIGHT, TOTAL_WIDTH), dtype=np.uint8)
    ser.write(create_led_packet(clear_pattern))
    
    # Show results
    print("\n" + "=" * 60)
    print("MAPPING RESULTS")
    print("=" * 60)
    print()
    print("Logical Panel → Physical Position")
    print("-" * 40)
    
    for panel, physical in results.items():
        expected = get_panel_name(panel)
        actual = get_panel_name(physical) if isinstance(physical, int) else "Unknown"
        match = "✅" if panel == physical else "❌"
        print(f"{match} Panel {panel} ({expected:15s}) → Position {physical} ({actual})")
    
    print()
    print("=" * 60)
    print("INSTRUCTIONS:")
    print("=" * 60)
    print("If any panels show ❌, your wiring doesn't match the expected layout.")
    print("Save this mapping - we'll use it to fix the LED code!")
    print()
    
    ser.close()

def get_panel_name(num):
    """Get human-readable panel name"""
    names = {
        1: "Top-Left",
        2: "Top-Right",
        3: "Mid-Top-Left",
        4: "Mid-Top-Right",
        5: "Mid-Bottom-Left",
        6: "Mid-Bottom-Right",
        7: "Bottom-Left",
        8: "Bottom-Right",
    }
    return names.get(num, "Unknown")

if __name__ == "__main__":
    main()
