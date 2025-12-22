import numpy as np
import serial
import time
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from packages.mirror_core.controllers.led_controller import LEDController

def generate_panel_pattern(panel_num):
    """Generate a pattern with only one panel lit"""
    pattern = np.zeros((64, 32, 3), dtype=np.uint8)
    
    # Calculate panel position (2x4 grid)
    row = (panel_num - 1) // 2
    col = (panel_num - 1) % 2
    
    # Set panel to white
    start_row = row * 16
    start_col = col * 16
    pattern[start_row:start_row+16, start_col:start_col+16] = [255, 255, 255]
    
    # Add panel number in black
    if 1 <= panel_num <= 8:
        num_row = start_row + 4
        num_col = start_col + 6
        pattern[num_row:num_row+8, num_col:num_col+4] = 0
    
    return pattern

def generate_gradient_pattern():
    """Generate a gradient pattern"""
    pattern = np.zeros((64, 32, 3), dtype=np.uint8)
    for y in range(64):
        for x in range(32):
            # Simple gradient from top to bottom
            intensity = int((y / 63) * 255)
            pattern[y, x] = [intensity, intensity, intensity]
    return pattern

def generate_checkerboard_pattern():
    """Generate a checkerboard pattern"""
    pattern = np.zeros((64, 32, 3), dtype=np.uint8)
    for y in range(64):
        for x in range(32):
            if (x + y) % 2 == 0:
                pattern[y, x] = [255, 255, 255]  # White
            else:
                pattern[y, x] = [0, 0, 0]  # Black
    return pattern

def generate_border_pattern():
    """Generate a pattern with panel borders"""
    pattern = np.zeros((64, 32, 3), dtype=np.uint8)
    
    # Draw vertical borders
    pattern[:, 15:17] = [255, 0, 0]  # Red border between panels
    
    # Draw horizontal borders
    for row in [15, 31, 47]:
        pattern[row:row+2, :] = [0, 0, 255]  # Blue borders
    
    return pattern

def run_led_test(port='COM5'):
    print("=== LED Panel Test ===")
    print(f"Testing on {port}")
    
    # Test patterns
    patterns = [
        ("All White", lambda: np.ones((64, 32, 3), dtype=np.uint8) * 255),
        ("Panel 1", lambda: generate_panel_pattern(1)),
        ("Panel 2", lambda: generate_panel_pattern(2)),
        ("Panel 3", lambda: generate_panel_pattern(3)),
        ("Panel 4", lambda: generate_panel_pattern(4)),
        ("Panel 5", lambda: generate_panel_pattern(5)),
        ("Panel 6", lambda: generate_panel_pattern(6)),
        ("Panel 7", lambda: generate_panel_pattern(7)),
        ("Panel 8", lambda: generate_panel_pattern(8)),
        ("Gradient", generate_gradient_pattern),
        ("Checkerboard", generate_checkerboard_pattern),
        ("Borders", generate_border_pattern)
    ]
    
    try:
        # Initialize LED controller
        led = LEDController(width=32, height=64)
        
        # Test each pattern
        for name, pattern_func in patterns:
            print(f"\nTesting: {name}")
            
            try:
                # Generate and send pattern
                pattern = pattern_func()
                packet = led.pack_led_packet(pattern)
                
                # Send to ESP32
                with serial.Serial(port, 460800, timeout=1) as ser:
                    ser.write(packet)
                    ser.flush()
                    print(f"Sent {len(packet)} bytes to {port}")
                
                # Wait to see the pattern
                time.sleep(3)
                
            except Exception as e:
                print(f"Error in {name}: {e}")
                time.sleep(1)
                
    except Exception as e:
        print(f"Fatal error: {e}")
    
    print("\nTest complete!")
    input("Press Enter to exit...")

if __name__ == "__main__":
    port = sys.argv[1] if len(sys.argv) > 1 else 'COM5'
    run_led_test(port)
