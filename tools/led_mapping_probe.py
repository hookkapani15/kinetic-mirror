"""
LED MAPPING PROBE - Visual Diagnostic Tool
==============================================
This tool helps discover the ACTUAL physical LED wiring by lighting up
specific LED indices and observing where they appear.

Run: python tools/led_mapping_probe.py

Press keys to run different probes:
- 0-9: Light LED at index * 100 (0, 100, 200, ...)
- P: Test pin split (first half vs second half)
- S: Test serpentine (row direction)
- R: Row sweep (all of row 0, 1, 2...)
- C: Column sweep (all of column 0, 1, 2...)
- 1-8: Light specific panel
- Q: Quit
"""

import sys
import time
import numpy as np
import cv2
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from packages.mirror_core.controllers.led_controller import LEDController
from packages.mirror_core.io.serial_manager import SerialManager


class LEDMappingProbe:
    def __init__(self):
        self.width = 32
        self.height = 64
        self.total_leds = self.width * self.height
        
        # Initialize
        self.led = LEDController(width=self.width, height=self.height)
        # Temporarily disable the remapping fix to see raw behavior
        self.led.flip_x = False
        self.led.flip_y = False
        
        print("Connecting to ESP32...")
        self.serial = SerialManager('AUTO', 460800)
        self.serial.start()
        time.sleep(2)
        
        if not self.serial.connected:
            print("ERROR: Could not connect to ESP32!")
            sys.exit(1)
        print(f"Connected to {self.serial.port}")
        
        self.running = True
        
    def send_pattern(self, pattern, show_preview=True):
        """Send pattern to ESP32 and optionally show preview"""
        packet = bytes([0xAA, 0xBB, 0x01]) + pattern.flatten().tobytes()
        self.serial.ser.write(packet)
        
        if show_preview:
            # Show on-screen preview
            preview = cv2.resize(pattern, (320, 640), interpolation=cv2.INTER_NEAREST)
            preview_bgr = cv2.cvtColor(cv2.merge([preview, preview, preview]), cv2.COLOR_RGB2BGR)
            return preview_bgr
        return None
        
    def create_pattern_by_indices(self, indices, brightness=255):
        """Light specific LED indices (raw, no XY conversion)"""
        pattern = np.zeros((self.height, self.width), dtype=np.uint8)
        for idx in indices:
            if 0 <= idx < self.total_leds:
                y = idx // self.width
                x = idx % self.width
                pattern[y, x] = brightness
        return pattern
        
    def test_single_index(self, idx):
        """Light a single LED by index"""
        pattern = self.create_pattern_by_indices([idx])
        return pattern, f"Single LED Index {idx} (y={idx//32}, x={idx%32})"
        
    def test_pin_split(self):
        """Light first 1024 LEDs (indices 0-1023) to see PIN 5 coverage"""
        pattern = self.create_pattern_by_indices(range(0, 1024), 255)
        return pattern, "PIN 5 Only (indices 0-1023) - Should show which panels are on Pin 5"
        
    def test_second_pin(self):
        """Light second 1024 LEDs (indices 1024-2047) to see PIN 18 coverage"""
        pattern = self.create_pattern_by_indices(range(1024, 2048), 255)
        return pattern, "PIN 18 Only (indices 1024-2047) - Should show which panels are on Pin 18"
        
    def test_row(self, row_num):
        """Light all LEDs in a specific row"""
        start_idx = row_num * self.width
        end_idx = start_idx + self.width
        pattern = self.create_pattern_by_indices(range(start_idx, end_idx))
        return pattern, f"Row {row_num} (indices {start_idx}-{end_idx-1})"
        
    def test_first_panel_indices(self):
        """Light indices 0-255 (should be first panel on first pin)"""
        pattern = self.create_pattern_by_indices(range(0, 256), 255)
        return pattern, "First 256 LEDs (indices 0-255) - First panel on Pin 5"
        
    def test_serpentine_check(self):
        """Light pixels to detect serpentine pattern"""
        # Light specific pattern to detect serpentine
        # If serpentine: row 0 goes 0->15, row 1 goes 31->16
        pattern = np.zeros((self.height, self.width), dtype=np.uint8)
        
        # Light first 3 LEDs of row 0 (should appear left side)
        pattern[0, 0] = 255
        pattern[0, 1] = 200
        pattern[0, 2] = 150
        
        # Light first 3 LEDs of row 1 (if serpentine, they'll appear right side)
        pattern[1, 0] = 255
        pattern[1, 1] = 200
        pattern[1, 2] = 150
        
        return pattern, "Serpentine Test: 3 LEDs each on row 0 and row 1. If serpentine, row 1 will be on opposite side."
        
    def test_corners(self):
        """Light the 4 corners of the logical grid"""
        pattern = np.zeros((self.height, self.width), dtype=np.uint8)
        # Four corners
        pattern[0, 0] = 255      # Top-Left (should be index 0)
        pattern[0, 31] = 200     # Top-Right (should be index 31)
        pattern[63, 0] = 150     # Bottom-Left (should be index 2016)
        pattern[63, 31] = 100    # Bottom-Right (should be index 2047)
        return pattern, "4 Corners: TL(bright), TR, BL, BR(dim)"
        
    def sweep_indices(self):
        """Generator that sweeps through indices"""
        for i in range(0, self.total_leds, 32):
            yield i
            
    def run(self):
        """Run interactive diagnostic"""
        print("\n" + "="*60)
        print("LED MAPPING PROBE - DIAGNOSTIC TOOL")
        print("="*60)
        print("\nWATCH YOUR PHYSICAL LED PANELS!")
        print("\nControls:")
        print("  0-9: Light LED at index * 100")
        print("  P: Test Pin 5 (first 1024 LEDs)")
        print("  O: Test Pin 18 (second 1024 LEDs)")
        print("  F: First panel (indices 0-255)")
        print("  S: Serpentine check")
        print("  C: Corner test")
        print("  R: Row sweep (0, 1, 2...)")
        print("  SPACE: Clear all")
        print("  Q/ESC: Quit")
        
        cv2.namedWindow("LED Mapping Probe", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("LED Mapping Probe", 800, 600)
        
        current_row = 0
        info_text = "Press a key to start testing..."
        
        while self.running:
            # Create display
            display = np.zeros((600, 800, 3), dtype=np.uint8)
            
            # Instructions
            cv2.putText(display, "LED MAPPING PROBE", (20, 40), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
            cv2.putText(display, info_text, (20, 80), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            
            cv2.putText(display, "P=Pin5 | O=Pin18 | F=First256 | S=Serpentine | C=Corners", 
                       (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            cv2.putText(display, "R=RowSweep | 0-9=IndexProbe | SPACE=Clear | Q=Quit", 
                       (20, 145), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            
            # Show preview area
            cv2.rectangle(display, (500, 20), (780, 580), (50, 50, 50), 2)
            cv2.putText(display, "Preview", (600, 40), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
            
            cv2.imshow("LED Mapping Probe", display)
            
            key = cv2.waitKey(100) & 0xFF
            
            pattern = None
            
            if key == ord('q') or key == ord('Q') or key == 27:
                self.running = False
                
            elif key == ord(' '):
                pattern = np.zeros((self.height, self.width), dtype=np.uint8)
                info_text = "CLEARED all LEDs"
                
            elif key == ord('p') or key == ord('P'):
                pattern, info_text = self.test_pin_split()
                
            elif key == ord('o') or key == ord('O'):
                pattern, info_text = self.test_second_pin()
                
            elif key == ord('f') or key == ord('F'):
                pattern, info_text = self.test_first_panel_indices()
                
            elif key == ord('s') or key == ord('S'):
                pattern, info_text = self.test_serpentine_check()
                
            elif key == ord('c') or key == ord('C'):
                pattern, info_text = self.test_corners()
                
            elif key == ord('r') or key == ord('R'):
                pattern, info_text = self.test_row(current_row)
                current_row = (current_row + 1) % 64
                
            elif ord('0') <= key <= ord('9'):
                idx = (key - ord('0')) * 100
                pattern, info_text = self.test_single_index(idx)
                
            if pattern is not None:
                self.send_pattern(pattern)
                print(f">>> {info_text}")
        
        # Clear and close
        self.send_pattern(np.zeros((self.height, self.width), dtype=np.uint8))
        self.serial.close()
        cv2.destroyAllWindows()
        print("\nProbe complete!")


if __name__ == "__main__":
    probe = LEDMappingProbe()
    probe.run()
