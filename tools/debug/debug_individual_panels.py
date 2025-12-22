"""
Debug individual panel test - verify pixel coordinates
"""
import numpy as np
import cv2
from packages.mirror_core.testing.led_panel_tester import LEDPanelTester

tester = LEDPanelTester()

print("="*60)
print("INDIVIDUAL PANEL DEBUG")
print("="*60)

for panel_id in range(1, 9):
    pattern = tester.generate_individual_panel_test(panel_id)
    
    # Calculate expected coordinates
    panel_idx = panel_id - 1
    row = panel_idx // 2
    col = panel_idx % 2
    
    y_start = row * 16
    y_end = y_start + 16
    x_start = col * 16
    x_end = x_start + 16
    
    # Count lit pixels
    total_lit = np.sum(pattern > 0)
    expected_lit = 16 * 16
    
    # Check if correct region is lit
    region = pattern[y_start:y_end, x_start:x_end]
    region_lit = np.sum(region > 0)
    
    print(f"\nPanel {panel_id}:")
    print(f"  Expected coords: Y[{y_start}:{y_end}], X[{x_start}:{x_end}]")
    print(f"  Expected lit pixels: {expected_lit}")
    print(f"  Total lit pixels: {total_lit}")
    print(f"  Region lit pixels: {region_lit}")
    print(f"  OK CORRECT" if total_lit == expected_lit and region_lit == expected_lit else f"  ERROR MISMATCH")
    
    # Save debug image
    # Scale up for visibility
    debug_img = cv2.resize(pattern, (320, 640), interpolation=cv2.INTER_NEAREST)
    
    # Draw grid
    for r in range(5):
        y = r * 160
        cv2.line(debug_img, (0, y), (320, y), 128, 1)
    for c in range(3):
        x = c * 160
        cv2.line(debug_img, (x, 0), (x, 640), 128, 1)
    
    cv2.imwrite(f"debug_panel_{panel_id}.png", debug_img)

print("\nOK Debug images saved: debug_panel_1.png through debug_panel_8.png")
