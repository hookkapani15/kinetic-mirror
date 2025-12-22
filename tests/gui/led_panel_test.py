"""
Standalone LED Panel Test GUI - REDESIGNED
Beautiful modern interface with gradients, animations, and premium styling
Run: python tests/gui/led_panel_test.py
"""
import sys
import time
import numpy as np
import cv2
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from packages.mirror_core.controllers.led_controller import LEDController
from packages.mirror_core.io.serial_manager import SerialManager
from packages.mirror_core.testing.led_panel_tester import LEDPanelTester
from packages.mirror_core.testing import simple_led_patterns


class LEDPanelTestGUI:
    """Standalone LED panel test application with stunning UI"""
    
    def __init__(self):
        self.running = True
        self.test_pattern_index = 0
        self._last_sent_pattern_index = None
        self._last_send_ok = True
        self._last_send_time = 0.0
        self._send_fail_count = 0
        
        # Initialize controllers
        self.led = LEDController(width=32, height=64)
        self.serial = SerialManager('AUTO', 460800)
        self.serial.start()
        time.sleep(2)

        if getattr(self.serial, "connected", False) and getattr(self.serial, "ser", None):
            try:
                self.serial.ser.write(b's')
                time.sleep(0.05)
                self.serial.ser.write(b'c')
                time.sleep(0.05)
            except Exception:
                pass
        
        self.led_tester = LEDPanelTester()
        
        # Test patterns
        self.test_patterns = [
            # STATIC BASELINE TESTS (0-4)
            ('STATIC', 'all_white', 'All LEDs white - Full system check'),
            ('STATIC', 'brightness_levels', 'Panels 1-8 brightness gradient (30→255)'),
            ('STATIC', 'checkerboard', 'Checkerboard pattern - Pixel alignment test'),
            ('STATIC', 'gradient', 'Horizontal gradient - Smooth transition test'),
            ('STATIC', 'borders', 'Panel borders - 2×4 grid verification'),
            
            # GEOMETRIC TESTS (5-9)
            ('GEOMETRIC', 'vertical_bars', 'Vertical stripes - Column wiring test'),
            ('GEOMETRIC', 'horizontal_bars', 'Horizontal stripes - Row wiring test'),
            ('GEOMETRIC', 'diagonal_gradient', 'Diagonal gradient - Cross-panel test'),
            ('GEOMETRIC', 'concentric', 'Concentric squares - Radial pattern'),
            ('GEOMETRIC', 'panel_corners', 'Corner markers - Panel identification'),

            # ANIMATED TESTS
            ('ANIMATED', 'wavy_vertical', 'Wavy vertical brightness - Temporal + mapping test'),
            ('ANIMATED', 'wavy_horizontal', 'Wavy horizontal brightness - Temporal + mapping test'),
            
            # INDIVIDUAL PANEL TESTS (10-17)
            ('INDIVIDUAL', 'panel_1', 'Panel 1 ONLY - Top-Left'),
            ('INDIVIDUAL', 'panel_2', 'Panel 2 ONLY - Top-Right'),
            ('INDIVIDUAL', 'panel_3', 'Panel 3 ONLY - Middle-Top-Left'),
            ('INDIVIDUAL', 'panel_4', 'Panel 4 ONLY - Middle-Top-Right'),
            ('INDIVIDUAL', 'panel_5', 'Panel 5 ONLY - Middle-Bottom-Left'),
            ('INDIVIDUAL', 'panel_6', 'Panel 6 ONLY - Middle-Bottom-Right'),
            ('INDIVIDUAL', 'panel_7', 'Panel 7 ONLY - Bottom-Left'),
            ('INDIVIDUAL', 'panel_8', 'Panel 8 ONLY - Bottom-Right'),
            
            # NUMBERS TEST (18)
            ('NUMBERS', 'numbers_1_8', 'Display numbers 1-8 on each panel'),
            
            # TEXT TESTS (19-23)
            ('TEXT', 'hello_full', 'Display HELLO across full screen'),
            ('TEXT', 'hello_letter_h', 'Display letter H only'),
            ('TEXT', 'hello_letter_e', 'Display letter E only'),
            ('TEXT', 'hello_letter_l', 'Display letter L only'),
            ('TEXT', 'hello_letter_o', 'Display letter O only'),

            # BENCHMARK TESTS (The Golden Standards)
            ('BENCHMARK', 'bench_1_tl', 'Benchmark: Number "1" on Panel 1 (Top-Left) ONLY'),
            ('BENCHMARK', 'bench_1_all', 'Benchmark: Number "1" on ALL 8 Panels'),
            ('BENCHMARK', 'bench_corners', 'Benchmark: 4 Corners of each panel (Grid Box)'),
            ('BENCHMARK', 'bench_cross', 'Benchmark: Center Cross (+) on each panel'),
            ('BENCHMARK', 'bench_1_to_8_tiny', 'Benchmark: Tiny 3x5 Numbers 1-8'),

            # DEBUG HARDWARE MAPPING PROBE (24-30) - RAWWWW DATA
            ('DEBUG_MAPPING', 'debug_pixel_0_0', 'RAW: Pixel at (0,0) [Top-Left?]'),
            ('DEBUG_MAPPING', 'debug_pixel_31_0', 'RAW: Pixel at (31,0) [Top-Right?]'),
            ('DEBUG_MAPPING', 'debug_pixel_0_63', 'RAW: Pixel at (0,63) [Bottom-Left?]'),
            ('DEBUG_MAPPING', 'debug_pixel_31_63', 'RAW: Pixel at (31,63) [Bottom-Right?]'),
            ('DEBUG_MAPPING', 'debug_sweep_x', 'RAW: Dot moving along X axis (Row 0)'),
            ('DEBUG_MAPPING', 'debug_sweep_y', 'RAW: Dot moving along Y axis (Col 0)'),
            ('DEBUG_MAPPING', 'debug_zigzag', 'RAW: First 32 pixels (Check wiring order)'),
        ]
        # Mapping Modes for Decoder Ring
        self.mapping_modes = [
            'RAW_LINEAR',
            'INVERT_X',
            'INVERT_Y',
            'INVERT_XY',
            'ZIGZAG_H_ROW_ODD_INV',    # Standard: Even=L->R, Odd=R->L
            'ZIGZAG_H_ROW_EVEN_INV',   # Weird: Even=R->L, Odd=L->R
            'ZIGZAG_V_COL_ODD_INV',    # Vertical: Even=T->B, Odd=B->T
            'ZIGZAG_V_COL_EVEN_INV',   # Vertical: Even=B->T, Odd=T->B
            'PANEL_GRID_OLD'
        ]
        self.mapping_mode_index = 0
        self.paused = False
        self._last_generated_pattern = None
        self._last_generated_what_to_see = ""
        self._last_generated_index = -1
    
        # Pixel-perfect 5x7 bitmaps
        self.digit_bitmaps = {
             1: [[0,0,1,0],[0,1,1,0],[0,0,1,0],[0,0,1,0],[0,0,1,0],[0,0,1,0],[0,1,1,1]],
             2: [[0,1,1,0],[1,0,0,1],[0,0,0,1],[0,0,1,0],[0,1,0,0],[1,0,0,0],[1,1,1,1]],
             3: [[1,1,1,0],[0,0,0,1],[0,0,1,0],[0,0,0,1],[0,0,0,1],[1,0,0,1],[0,1,1,0]],
             4: [[0,0,1,0],[0,1,1,0],[1,0,1,0],[1,0,1,0],[1,1,1,1],[0,0,1,0],[0,0,1,0]],
             5: [[1,1,1,1],[1,0,0,0],[1,1,1,0],[0,0,0,1],[0,0,0,1],[1,0,0,1],[0,1,1,0]],
             6: [[0,0,1,0],[0,1,0,0],[1,0,0,0],[1,1,1,0],[1,0,0,1],[1,0,0,1],[0,1,1,0]],
             7: [[1,1,1,1],[0,0,0,1],[0,0,1,0],[0,1,0,0],[0,1,0,0],[0,1,0,0],[0,1,0,0]],
             8: [[0,1,1,0],[1,0,0,1],[1,0,0,1],[0,1,1,0],[1,0,0,1],[1,0,0,1],[0,1,1,0]]
        }

        # Tiny 3x5 bitmaps for maximum clarity
        self.tiny_digits = {
            1: [[0,1,0],[1,1,0],[0,1,0],[0,1,0],[1,1,1]],
            2: [[1,1,1],[0,0,1],[1,1,1],[1,0,0],[1,1,1]],
            3: [[1,1,1],[0,0,1],[0,1,1],[0,0,1],[1,1,1]],
            4: [[1,0,1],[1,0,1],[1,1,1],[0,0,1],[0,0,1]],
            5: [[1,1,1],[1,0,0],[1,1,1],[0,0,1],[1,1,1]],
            6: [[1,1,1],[1,0,0],[1,1,1],[1,0,1],[1,1,1]],
            7: [[1,1,1],[0,0,1],[0,1,0],[0,1,0],[0,1,0]],
            8: [[1,1,1],[1,0,1],[1,1,1],[1,0,1],[1,1,1]]
        }
        
    def generate_pattern(self, pattern_name):
        """Generate LED pattern based on name"""
        if pattern_name == 'all_white':
            return np.full((64, 32), 255, dtype=np.uint8), "All LEDs bright white"
        elif pattern_name == 'brightness_levels':
            return self.led_tester.generate_panel_brightness_levels(), "8 panels from dim to bright"
        elif pattern_name == 'checkerboard':
            return self.led_tester.generate_checkerboard_test(), "Alternating checkerboard squares"
        elif pattern_name == 'gradient':
            return self.led_tester.generate_gradient_test(), "Smooth horizontal gradient"
        elif pattern_name == 'borders':
            return self.led_tester.generate_panel_border_test(), "White grid lines"
        elif pattern_name == 'vertical_bars':
            return simple_led_patterns.generate_vertical_bars(), "Vertical stripes"
        elif pattern_name == 'horizontal_bars':
            return simple_led_patterns.generate_horizontal_bars(), "Horizontal stripes"
        elif pattern_name == 'diagonal_gradient':
            return simple_led_patterns.generate_diagonal_gradient(), "Diagonal gradient"
        elif pattern_name == 'concentric':
            return simple_led_patterns.generate_concentric_squares(), "Concentric squares"
        elif pattern_name == 'panel_corners':
            return simple_led_patterns.generate_panel_corners(), "Corner markers"
        elif pattern_name == 'wavy_vertical':
            t = time.time()
            x = np.arange(32, dtype=np.float32)[None, :]
            y = np.arange(64, dtype=np.float32)[:, None]
            v = (np.sin((x / 32.0) * 2 * np.pi * 3 + t * 2.2) + 1.0) * 127.5
            v = v + (np.sin((y / 64.0) * 2 * np.pi * 1 + t * 1.4) + 1.0) * 40.0
            return np.clip(v, 0, 255).astype(np.uint8), "Animated wave (vertical)"
        elif pattern_name == 'wavy_horizontal':
            t = time.time()
            x = np.arange(32, dtype=np.float32)[None, :]
            y = np.arange(64, dtype=np.float32)[:, None]
            v = (np.sin((y / 64.0) * 2 * np.pi * 4 + t * 2.0) + 1.0) * 127.5
            v = v + (np.sin((x / 32.0) * 2 * np.pi * 1 + t * 1.1) + 1.0) * 40.0
            return np.clip(v, 0, 255).astype(np.uint8), "Animated wave (horizontal)"
        elif pattern_name.startswith('panel_'):
            panel_id = int(pattern_name.split('_')[1])
            return self.led_tester.generate_individual_panel_test(panel_id), f"ONLY Panel {panel_id} lit"
        elif pattern_name == 'numbers_1_8':
            return self.generate_numbers(), "Numbers 1-8 on each panel"
        elif pattern_name.startswith('hello_'):
            text = pattern_name.replace('hello_', '').replace('letter_', '').upper()
            return self.generate_text(text), f"Text: {text}"

        # BENCHMARK TESTS
        elif pattern_name == 'bench_1_tl':
            p = np.zeros((64, 32), dtype=np.uint8)
            self.draw_number_on_panel(p, 1, 1) # Draw '1' on Panel 1
            return p, "Number '1' on TOP-LEFT panel only"
            
        elif pattern_name == 'bench_1_all':
            p = np.zeros((64, 32), dtype=np.uint8)
            for i in range(1, 9):
                self.draw_number_on_panel(p, i, 1) # Draw '1' on Panel i
            return p, "Number '1' on ALL 8 panels"
            
        elif pattern_name == 'bench_corners':
            p = np.zeros((64, 32), dtype=np.uint8)
            # Draw corners for all 8 panels (16x16)
            for i in range(1, 9):
                row = (i - 1) // 2
                col = (i - 1) % 2
                y0, x0 = row * 16, col * 16
                p[y0, x0] = 255         # Top-Left
                p[y0, x0+15] = 255      # Top-Right
                p[y0+15, x0] = 255      # Bottom-Left
                p[y0+15, x0+15] = 255   # Bottom-Right
            return p, "4 Corners of each 16x16 panel (Should look like boxes)"
            
        elif pattern_name == 'bench_cross':
            p = np.zeros((64, 32), dtype=np.uint8)
            # Draw center cross for all 8 panels
            for i in range(1, 9):
                row = (i - 1) // 2
                col = (i - 1) % 2
                y0, x0 = row * 16, col * 16
                # Center is around 7,7 and 8,8
                p[y0+7:y0+9, x0+7:y0+9] = 255 # 2x2 center block
                p[y0+7:y0+9, x0+4:x0+12] = 255 # Horiz bar
                p[y0+4:y0+12, x0+7:x0+9] = 255 # Vert bar
            return p, "Center Cross (+) on each panel"
            
        elif pattern_name == 'bench_1_to_8_tiny':
            p = np.zeros((64, 32), dtype=np.uint8)
            for i in range(1, 9):
                self.draw_number_on_panel(p, i, i, tiny=True)
            return p, "Tiny Numbers 1-8 (3x5 font)"
            
        elif pattern_name == 'bench_1_to_8':
            # Panels 1-8 with numbers 1-8
            return self.generate_numbers(), "Numbers 1-8 in correct order"

            
        # DEBUG PATTERNS
        elif pattern_name == 'debug_pixel_0_0':
            p = np.zeros((64, 32), dtype=np.uint8)
            p[0, 0] = 255
            return p, "Single pixel at Y=0, X=0"
        elif pattern_name == 'debug_pixel_31_0':
            p = np.zeros((64, 32), dtype=np.uint8)
            p[0, 31] = 255
            return p, "Single pixel at Y=0, X=31"
        elif pattern_name == 'debug_pixel_0_63':
            p = np.zeros((64, 32), dtype=np.uint8)
            p[63, 0] = 255
            return p, "Single pixel at Y=63, X=0"
        elif pattern_name == 'debug_pixel_31_63':
            p = np.zeros((64, 32), dtype=np.uint8)
            p[63, 31] = 255
            return p, "Single pixel at Y=63, X=31"
        elif pattern_name == 'debug_sweep_x':
            p = np.zeros((64, 32), dtype=np.uint8)
            x = int(time.time() * 10) % 32
            p[0, x] = 255
            return p, f"Dot moving X axis at Y=0 (Current X={x})"
        elif pattern_name == 'debug_sweep_y':
            p = np.zeros((64, 32), dtype=np.uint8)
            y = int(time.time() * 10) % 64
            p[y, 0] = 255
            return p, f"Dot moving Y axis at X=0 (Current Y={y})"
        elif pattern_name == 'debug_zigzag':
            p = np.zeros((64, 32), dtype=np.uint8)
            step = int(time.time() * 2) % 4
            if step == 0: p[0, 0:16] = 255     # First half row 0
            elif step == 1: p[0, 16:32] = 255  # Second half row 0
            elif step == 2: p[1, 0:16] = 255   # First half row 1
            elif step == 3: p[1, 16:32] = 255  # Second half row 1
            return p, "Blinking first 2 rows (check zigzag)"
            
        else:
            return np.zeros((64, 32), dtype=np.uint8), "Unknown"
    
    def draw_number_on_panel(self, canvas, panel_idx, number, tiny=False):
        """Helper to draw a pixel-perfect number on a specific panel"""
        row = (panel_idx - 1) // 2
        col = (panel_idx - 1) % 2
        y_start, x_start = row * 16, col * 16
        
        # Get bitmap
        if tiny:
            bitmap = self.tiny_digits.get(number, self.tiny_digits[8])
        else:
            bitmap = self.digit_bitmaps.get(number, self.digit_bitmaps[8]) # Fallback to 8
            
        h = len(bitmap)
        w = len(bitmap[0])
        
        # Center in 16x16
        offset_y = (16 - h) // 2
        offset_x = (16 - w) // 2
        
        for r, row_pixels in enumerate(bitmap):
            for c, val in enumerate(row_pixels):
                if val:
                    canvas[y_start + offset_y + r, x_start + offset_x + c] = 255


    def generate_numbers(self):
        """Generate numbers 1-8 pattern"""
        pattern = np.zeros((64, 32), dtype=np.uint8)
        for panel_id in range(1, 9):
            self.draw_number_on_panel(pattern, panel_id, panel_id)
        return pattern
    
    def generate_text(self, text='HELLO'):
        """Generate text pattern"""
        pattern = np.zeros((64, 32), dtype=np.uint8)
        font_scale = 2.0 if len(text) == 1 else 0.8
        thickness = 3 if len(text) == 1 else 2
        (tw, th), baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
        x, y = (32 - tw) // 2, ((64 + th) // 2) - baseline
        cv2.putText(pattern, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, font_scale, 255, thickness)
        return pattern

    def apply_mapping(self, pattern, mode):
        """Apply coordinate transformations to solve wiring puzzles"""
        decoded = pattern.copy()

        if mode == 'RAW_LINEAR':
            return decoded
            
        elif mode == 'INVERT_X':
            return np.flip(decoded, axis=1)
            
        elif mode == 'INVERT_Y':
            return np.flip(decoded, axis=0)
            
        elif mode == 'INVERT_XY':
            return np.flip(np.flip(decoded, axis=0), axis=1)
            
        elif mode == 'ZIGZAG_H_ROW_ODD_INV':
            # Standard: Odd rows reversed
            decoded[1::2] = decoded[1::2, ::-1]
            return decoded
            
        elif mode == 'ZIGZAG_H_ROW_EVEN_INV':
             # Weird: Even rows reversed
            decoded[0::2] = decoded[0::2, ::-1]
            return decoded
            
        elif mode == 'ZIGZAG_V_COL_ODD_INV':
            # Vertical: Odd cols reversed
            decoded[:, 1::2] = decoded[::-1, 1::2]
            return decoded
            
        elif mode == 'ZIGZAG_V_COL_EVEN_INV':
            # Vertical: Even cols reversed
            decoded[:, 0::2] = decoded[::-1, 0::2]
            return decoded
            
        elif mode == 'PANEL_GRID_OLD':
            # Simulate the complex 8-panel grid reordering
            # This is complex to implement fully in numpy vectorization rapidly
            # Simplifying to a basic block swap for now to see if chunks move
            # Try swapping top/bottom halves (simulate pin swap)
            top = decoded[0:32, :]
            bot = decoded[32:64, :]
            return np.vstack((bot, top)) # Swap top/bottom
            
        return decoded
    
    def run(self):
        print(f"Starting LED Panel Test GUI on {self.serial.port}")
        
        cv2.namedWindow("LED Panel Test", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("LED Panel Test", 1200, 900)
        
        print("\nControls:")
        print("  SPACE / D : Next Pattern")
        print("  A         : Previous Pattern")
        print("  P         : PAUSE / UNPAUSE")
        print("  M         : Change Mapping Mode (DECODER)")
        print("  R         : Reconnect Serial")
        print("  Q / ESC   : Quit")
        
        while self.running:
            # Handle Pause Logic
            category, pattern_name, description = self.test_patterns[self.test_pattern_index]
            
            # Determine if we should update the pattern
            # Only update if:
            # 1. It's a new pattern selection
            # 2. It's an ANIMATED pattern (and not paused)
            # 3. It's a DEBUG pattern (which might have internal animation like sweep)
            
            is_new_pattern = self.test_pattern_index != self._last_generated_index
            is_animated_category = category == 'ANIMATED' or category == 'DEBUG_MAPPING'
            # Note: ZIGZAG mappings are static re-mappings of the source, they don't animate the source.
            
            should_compue_frame = is_new_pattern or (is_animated_category and not self.paused)
            
            if should_compue_frame:
                led_pattern, what_to_see = self.generate_pattern(pattern_name)
                self._last_generated_pattern = led_pattern
                self._last_generated_what_to_see = what_to_see
                self._last_generated_index = self.test_pattern_index
            else:
                led_pattern = self._last_generated_pattern
                what_to_see = self._last_generated_what_to_see
                
            # APPLY DYNAMIC MAPPING (The Decoder Ring)
            current_mode = self.mapping_modes[self.mapping_mode_index]
            
            # Special case: DEBUG_MAPPING always forces RAW to avoid confusion?
            # User said "Add more mapping debugging mode", implying they want to map even the debug stuff?
            # Actually, if I use debug_pixel_0_0 and apply 'INVERT_X', I expect the pixel to move. 
            # So applying mapping to everything is consistent.
            led_pattern_sent = self.apply_mapping(led_pattern, current_mode)
            
            # Send to ESP32
            # Always send if we regenerated, or if paused but mapping changed (allows exploring frozen frame)
            mapping_changed = False
            if hasattr(self, '_last_mapping_index'):
                if self._last_mapping_index != self.mapping_mode_index:
                    mapping_changed = True
            else:
                self._last_mapping_index = self.mapping_mode_index

            now = time.time()
            # If paused, we only send if mapping changed or new pattern selected
            should_send = should_compue_frame or mapping_changed
            
            should_retry = (not self._last_send_ok) and (now - self._last_send_time > 0.25)

            if should_send or should_retry:
                packet = self.led.pack_led_packet(led_pattern_sent)
                ok = self.serial.send_led(packet)
                self._last_send_ok = bool(ok)
                self._last_send_time = now
                if ok:
                    self._send_fail_count = 0
                    self._last_sent_pattern_index = self.test_pattern_index
                    self._last_mapping_index = self.mapping_mode_index
                else:
                    self._send_fail_count += 1
            
            # ==================== BEAUTIFUL UI RENDERING ====================
            
            # LED Preview (Shows TARGET pattern, not the scrambled sent one, 
            # unless we want to visualize the mapping? 
            # Better to show TARGET so user knows "I am trying to show F"
            # And expects to see "F" on mirror.
            # But maybe show "Mapped Preview" small?)
            
            # Let's show the SENT pattern in main preview but maybe unisolating it?
            # No, keep showing the ORIGINAL pattern as main, so user knows what SHOULD be there.
            led_rgb = np.stack([led_pattern, led_pattern, led_pattern], axis=2)
            preview = cv2.resize(led_rgb, (450, 900), interpolation=cv2.INTER_NEAREST)
            
            # Add glow effect to preview
            preview_glow = cv2.GaussianBlur(preview, (21, 21), 0)
            preview = cv2.addWeighted(preview, 0.7, preview_glow, 0.3, 0)
            
            # DEBUG OVERLAY
            if category == 'DEBUG_MAPPING':
                cv2.rectangle(preview, (0, 400), (450, 500), (0, 0, 0), -1)
                cv2.putText(preview, "LOOK AT MIRROR", (20, 440), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
                cv2.putText(preview, "WHERE IS DOT?", (40, 480), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
            
            # PAUSED OVERLAY
            if self.paused:
                cv2.rectangle(preview, (100, 350), (350, 450), (0, 0, 0), -1)
                cv2.putText(preview, "PAUSED", (120, 415), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 255), 3)

            # Sidebar with gradient background
            sidebar_w = 650
            sidebar = np.zeros((900, sidebar_w, 3), dtype=np.uint8)
            
            # Awesome gradient background
            if category == 'DEBUG_MAPPING':
                # Special red/black gradient for DEBUG mode
                for i in range(900):
                    t = i / 900.0
                    r = int(60 + 40 * np.sin(t * np.pi))
                    g = int(10)
                    b = int(10)
                    sidebar[i, :] = (b, g, r)
            else:
                for i in range(900):
                    t = i / 900.0
                    # Purple to blue gradient
                    r = int(25 + 15 * np.sin(t * np.pi))
                    g = int(20 + 15 * np.sin(t * np.pi + 1.0))
                    b = int(40 + 20 * np.sin(t * np.pi + 2.0))
                    sidebar[i, :] = (b, g, r)
            
            # Neon colors
            neon_cyan = (255, 255, 0)       # Bright cyan
            neon_pink = (255, 0, 255)        # Magenta
            neon_green = (0, 255, 150)       # Bright green
            neon_orange = (0, 165, 255)      # Orange
            neon_red = (0, 100, 255)         # Red
            bright_white = (255, 255, 255)
            soft_gray = (200, 200, 200)
            
            # Current category color
            category_colors = {
                'STATIC': neon_cyan,
                'GEOMETRIC': neon_orange,
                'ANIMATED': neon_pink,
                'INDIVIDUAL': neon_green,
                'NUMBERS': (255, 200, 0),
                'TEXT': (200, 100, 255),
                'DEBUG_MAPPING': (50, 50, 255) # Bright Red
            }
            cat_color = category_colors.get(category, neon_cyan)
            
            # Draw Sidebar Text
            y = 50
            
            # MAPPING MODE DISPLAY (Very Prominent)
            cv2.rectangle(sidebar, (30, y-10), (615, y+50), (50, 50, 50), -1)
            cv2.putText(sidebar, f"MAPPING: {current_mode}", (45, y+35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            y += 80

            cv2.putText(sidebar, "MIRROR LED TESTER", (30, y), cv2.FONT_HERSHEY_SIMPLEX, 1.5, bright_white, 2) # Thinner font
            y += 60
            
            # Connection Status
            status_color = neon_green if self.serial.connected else neon_red
            status_text = f"CONNECTED ({self.serial.port})" if self.serial.connected else "DISCONNECTED"
            cv2.putText(sidebar, status_text, (30, y), cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2)
            y += 40
            
            # Category Badge
            cv2.rectangle(sidebar, (30, y), (300, y + 40), cat_color, -1)
            cv2.putText(sidebar, category, (40, y + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
            
            # PAUSED INDICATOR
            if self.paused:
                cv2.putText(sidebar, "[PAUSED]", (330, y + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

            y += 70
            
            test_num = self.test_pattern_index
            total = len(self.test_patterns)
            cv2.putText(sidebar, f"Test {test_num + 1} / {total}", (450, y + 45), cv2.FONT_HERSHEY_SIMPLEX, 0.65, bright_white, 2)
            
            y += 75
            
            # Pattern name
            cv2.putText(sidebar, "PATTERN", (45, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, soft_gray, 1)
            y += 25
            pattern_display = pattern_name.replace('_', ' ').upper()
            cv2.putText(sidebar, pattern_display[:30], (45, y), cv2.FONT_HERSHEY_SIMPLEX, 0.65, bright_white, 2)
            y += 35
            
            # Description
            cv2.putText(sidebar, "DESCRIPTION", (45, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, soft_gray, 1)
            y += 22
            desc_lines = [description[i:i+50] for i in range(0, len(description), 50)][:2]
            for line in desc_lines:
                cv2.putText(sidebar, line, (45, y), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (220, 220, 220), 1)
                y += 22
            
            y += 10
            cv2.putText(sidebar, "WHAT YOU SHOULD SEE", (45, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, soft_gray, 1)
            y += 22
            see_lines = [what_to_see[i:i+50] for i in range(0, len(what_to_see), 50)][:2]
            for line in see_lines:
                cv2.putText(sidebar, line, (45, y), cv2.FONT_HERSHEY_SIMPLEX, 0.50, cat_color, 1)
                y += 22
            
            y += 50
            
            # Navigation controls
            y = 810
            cv2.rectangle(sidebar, (30, y - 10), (615, y + 70), (20, 20, 25), -1)
            cv2.putText(sidebar, "CONTROLS", (45, y + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.6, neon_cyan, 2)
            y += 40
            cv2.putText(sidebar, "SPACE / D = Next", (45, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, soft_gray, 1)
            cv2.putText(sidebar, "P = PAUSE", (220, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2)
            cv2.putText(sidebar, "M = MAP", (340, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)
            cv2.putText(sidebar, "R = RECONNECT", (440, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, bright_white, 1)
            y += 25
            cv2.putText(sidebar, "Q / ESC = Quit", (45, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, soft_gray, 1)
            
            # Combine preview and sidebar
            display = np.concatenate([preview, sidebar], axis=1)
            
            # Add border frame
            cv2.rectangle(display, (0, 0), (display.shape[1]-1, display.shape[0]-1), neon_cyan, 3)
            
            cv2.imshow("LED Panel Test", display)
            
            # Handle keyboard
            key = cv2.waitKey(20) & 0xFF # Faster response
            if key == ord(' ') or key == ord('d') or key == 83:  # SPACE, D, or RIGHT
                self.test_pattern_index = (self.test_pattern_index + 1) % len(self.test_patterns)
                print(f"-> Next: {self.test_patterns[self.test_pattern_index][1]}")
            elif key == ord('a') or key == 81:  # A or LEFT
                self.test_pattern_index = (self.test_pattern_index - 1) % len(self.test_patterns)
                print(f"<- Prev: {self.test_patterns[self.test_pattern_index][1]}")
            elif key == ord('r') or key == ord('R'):  # RECONNECT
                print("\n[USER REQ] Reconnecting to ESP32...")
                self.serial.close()
                time.sleep(0.5)
                self.serial.connect()
                print(f"Reconnection Status: {self.serial.connected}")
            elif key == ord('p') or key == ord('P'):  # PAUSE
                self.paused = not self.paused
                print(f"[PAUSE] Paused: {self.paused}")
            elif key == ord('m') or key == ord('M'): # MAPPING
                self.mapping_mode_index = (self.mapping_mode_index + 1) % len(self.mapping_modes)
                print(f"[MAPPING CHANGED] New Mode: {self.mapping_modes[self.mapping_mode_index]}")
            elif key == ord('q') or key == ord('Q') or key == 27:  # Q, q, or ESC
                print(f"Quit key pressed")
                self.running = False
        
        cv2.destroyAllWindows()
        self.serial.close()
        print("\nLED Panel Test Complete!")


if __name__ == "__main__":
    app = LEDPanelTestGUI()
    app.run()
