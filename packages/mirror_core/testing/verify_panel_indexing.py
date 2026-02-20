
import sys
import os
import time
import numpy as np
import cv2

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
if project_root not in sys.path:
    sys.path.append(project_root)

from packages.mirror_core.controllers.led_controller import LEDController

def test_panel_indexing():
    print("Testing LED Panel Indexing...")
    
    # Initialize controller
    # Use MODE_RAW to verify logical mapping before hardware remapping
    led = LEDController(width=32, height=64, mapping_mode=0)
    
    # 1. Test get_panel_rect
    print("\n[Test 1] Verifying Panel Rectangles (0-7)...")
    expected_rects = {
        0: (0, 0, 16, 16),   # Top-Left
        1: (16, 0, 16, 16),  # Top-Right
        2: (0, 16, 16, 16),  # 2nd Row-Left
        3: (16, 16, 16, 16), # 2nd Row-Right
        4: (0, 32, 16, 16),
        5: (16, 32, 16, 16),
        6: (0, 48, 16, 16),
        7: (16, 48, 16, 16)
    }
    
    passed_rects = True
    for i in range(8):
        try:
            rect = led.get_panel_rect(i)
            print(f"  Panel {i}: {rect}", end="")
            if rect == expected_rects[i]:
                print(" [OK]")
            else:
                print(f" [FAIL] Expected {expected_rects[i]}")
                passed_rects = False
        except AttributeError:
            print(f"\n[FAIL] method get_panel_rect not implemented yet!")
            passed_rects = False
            break
            
    if not passed_rects:
        print("❌ Rectangle verification failed.")
        return
        
    print("✅ Rectangle verification passed.")

    # 2. Test draw_on_panel
    print("\n[Test 2] Verifying Drawing on Panels...")
    frame = np.zeros((64, 32), dtype=np.uint8)
    
    def draw_cross(roi):
        # Draw a cross on the ROI
        h, w = roi.shape[:2]
        cv2.line(roi, (0, 0), (w-1, h-1), 255, 1)
        cv2.line(roi, (w-1, 0), (0, h-1), 255, 1)
        
    try:
        # Draw cross on Panel 0 and Panel 7
        led.draw_on_panel(frame, 0, draw_cross)
        led.draw_on_panel(frame, 7, draw_cross)
        
        # Verify pixels
        # Panel 0 center (approx 8,8) should be white
        # Panel 7 center (approx 8+16, 48+8) -> (24, 56) should be white
        
        # Check Panel 0
        p0_check = frame[8, 8] > 0
        p7_check = frame[56, 24] > 0
        
        if p0_check and p7_check:
             print("✅ Drawing verification passed.")
        else:
             print(f"❌ Drawing verification failed. P0:{p0_check}, P7:{p7_check}")
             
    except AttributeError:
        print("\n[FAIL] method draw_on_panel not implemented yet!")
        return

if __name__ == "__main__":
    test_panel_indexing()
