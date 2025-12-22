"""
LED Pattern Visualizer
Run this script to visualize the LED patterns
"""
import cv2
import numpy as np
from packages.mirror_core.testing.led_panel_tester import LEDPanelTester

def display_pattern(name, pattern):
    """Display a pattern with a title"""
    # Scale up for better visibility (32x64 is too small to see)
    scale = 10
    display = cv2.resize(pattern, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)
    
    # Add title
    title = f"LED Pattern: {name}"
    cv2.putText(display, title, (10, 30), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    
    cv2.imshow('LED Pattern', display)
    cv2.waitKey(0)

def main():
    # Initialize the LED tester
    tester = LEDPanelTester()
    
    print("Testing LED patterns...")
    
    try:
        # Test 1: All panels white with numbers
        print("\n1. Testing all panels (white with numbers)")
        pattern = tester.generate_panel_test_pattern()
        display_pattern("All Panels (White with Numbers)", pattern)
        
        # Test 2: Individual panel tests
        print("\n2. Testing individual panels")
        for panel_id in range(1, 9):
            print(f"   Panel {panel_id}")
            pattern = tester.generate_individual_panel_test(panel_id)
            display_pattern(f"Panel {panel_id}", pattern)
        
        # Test 3: Solid white test
        print("\n3. Testing solid white")
        patterns = tester.generate_solid_color_test()
        display_pattern("Solid White", patterns['white'])
        
        print("\nAll tests completed!")
        
    except Exception as e:
        print(f"Error during testing: {e}")
    finally:
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
