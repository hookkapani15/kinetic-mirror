"""
LED Panel Test Pattern Generator
Displays numbers 1-8 on each 16x16 panel for placement verification
"""
import numpy as np
import cv2


class LEDPanelTester:
    """Test pattern generator for LED panels"""
    
    def __init__(self, total_width=32, total_height=64):
        """
        Initialize LED tester
        Args:
            total_width: Total LED matrix width (32)
            total_height: Total LED matrix height (64)
        """
        self.width = total_width
        self.height = total_height
        self.panel_size = 16  # Each panel is 16×16
        
        # Calculate panel layout (assuming 2 columns × 4 rows = 8 panels)
        self.panels_cols = 2
        self.panels_rows = 4
        
    def generate_number_pattern(self, number, size=16):
        """
        Generate a 16x16 pattern with a number
        Args:
            number: Number to display (1-8)
            size: Panel size (16x16)
        Returns:
            16x16 numpy array with the number drawn
        """
        # Create black background
        panel = np.zeros((size, size), dtype=np.uint8)
        
        # Draw number in center
        text = str(number)
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.8
        thickness = 2
        
        # Get text size to center it
        (text_width, text_height), baseline = cv2.getTextSize(text, font, font_scale, thickness)
        
        # Center position
        x = (size - text_width) // 2
        y = (size + text_height) // 2
        
        # Draw white number
        cv2.putText(panel, text, (x, y), font, font_scale, 255, thickness)
        
        return panel
    
    def generate_panel_test_pattern(self):
        """
        Generate full test pattern with all panels lit in white for mode #1
        Returns:
            32×64 numpy array with all panels in white
        """
        # Create full LED matrix with all white (255)
        full_matrix = np.full((self.height, self.width), 255, dtype=np.uint8)
        
        # Add panel numbers in black for identification
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.8
        thickness = 2
        
        panel_number = 1
        for row in range(self.panels_rows):
            for col in range(self.panels_cols):
                text = str(panel_number)
                (text_width, text_height), _ = cv2.getTextSize(text, font, font_scale, thickness)

                y_start = row * 16
                x_start = col * 16

                x = x_start + (16 - text_width) // 2
                y = y_start + (16 + text_height) // 2

                cv2.putText(full_matrix, text, (x, y), font, font_scale, 0, thickness)
                
                panel_number += 1
        
        return full_matrix

    def generate_panel_brightness_levels(self):
        pattern = np.zeros((self.height, self.width), dtype=np.uint8)
        brightness_levels = [30, 60, 90, 120, 150, 180, 210, 255]
        panel_number = 0

        for row in range(self.panels_rows):
            for col in range(self.panels_cols):
                y_start = row * 16
                y_end = y_start + 16
                x_start = col * 16
                x_end = x_start + 16
                pattern[y_start:y_end, x_start:x_end] = brightness_levels[panel_number]
                panel_number += 1

        return pattern
    
    def generate_solid_color_test(self):
        """
        Generate solid white test pattern for mode #1
        Returns:
            Dictionary with only 'white' pattern
        """
        patterns = {}
        # Only include white pattern for mode #1
        patterns['white'] = np.full((self.height, self.width, 3), 255, dtype=np.uint8)
        return patterns
    
    def generate_gradient_test(self):
        """Generate gradient test pattern"""
        gradient = np.zeros((self.height, self.width), dtype=np.uint8)
        
        # Horizontal gradient
        for x in range(self.width):
            value = int((x / self.width) * 255)
            gradient[:, x] = value
        
        return gradient
    
    def generate_checkerboard_test(self, square_size=4):
        """Generate checkerboard pattern"""
        pattern = np.zeros((self.height, self.width), dtype=np.uint8)
        
        for y in range(self.height):
            for x in range(self.width):
                if ((y // square_size) + (x // square_size)) % 2 == 0:
                    pattern[y, x] = 255
        
        return pattern
    
    def generate_panel_border_test(self):
        """Draw borders around each 16×16 panel"""
        pattern = np.zeros((self.height, self.width), dtype=np.uint8)
        
        # Draw borders
        for row in range(self.panels_rows + 1):
            y = row * 16
            if y < self.height:
                pattern[y, :] = 255
        
        for col in range(self.panels_cols + 1):
            x = col * 16
            if x < self.width:
                pattern[:, x] = 255
        
        return pattern
    
    def generate_individual_panel_test(self, panel_id):
        """
        Light up only one specific panel with the panel number
        Args:
            panel_id: Panel number 1-8
        Returns:
            Full matrix with only specified panel lit and numbered
        """
        pattern = np.zeros((self.height, self.width), dtype=np.uint8)
        
        # Calculate panel position (1-indexed)
        # Panel layout:
        # 1 2
        # 3 4
        # 5 6
        # 7 8
        row = (panel_id - 1) // 2
        col = (panel_id - 1) % 2
        
        # Light up that panel with max brightness
        y_start = row * 16
        y_end = y_start + 16
        x_start = col * 16
        x_end = x_start + 16
        
        # Fill panel with white
        pattern[y_start:y_end, x_start:x_end] = 255
        
        # Add panel number in black
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1.0
        thickness = 2
        
        # Draw the number in the center of the panel
        text = str(panel_id)
        (text_width, text_height), _ = cv2.getTextSize(text, font, font_scale, thickness)

        x = x_start + (16 - text_width) // 2
        y = y_start + (16 + text_height) // 2
        
        # Draw black number
        cv2.putText(pattern, text, (x, y), font, font_scale, 0, thickness)
        
        return pattern
    
    def get_panel_info(self):
        """Get information about panel layout"""
        return {
            "total_width": self.width,
            "total_height": self.height,
            "panel_size": self.panel_size,
            "panels_cols": self.panels_cols,
            "panels_rows": self.panels_rows,
            "total_panels": self.panels_cols * self.panels_rows,
            "total_leds": self.width * self.height,
            "leds_per_panel": self.panel_size * self.panel_size,
            "layout": f"{self.panels_cols}×{self.panels_rows} grid"
        }


if __name__ == "__main__":
    # Test the pattern generator
    tester = LEDPanelTester()
    
    print("LED Panel Tester")
    print("=" * 50)
    info = tester.get_panel_info()
    for key, value in info.items():
        print(f"  {key}: {value}")
    
    # Generate test pattern
    pattern = tester.generate_panel_test_pattern()
    
    # Save as image for preview
    cv2.imwrite("led_test_pattern.png", pattern)
    print("\n✅ Test pattern saved to led_test_pattern.png")
    
    # Show what it would look like
    import matplotlib.pyplot as plt
    plt.figure(figsize=(8, 16))
    plt.imshow(pattern, cmap='gray')
    plt.title("LED Panel Test Pattern (Numbers 1-8)")
    plt.axis('off')
    plt.tight_layout()
    plt.savefig("led_test_pattern_preview.png", dpi=150, bbox_inches='tight')
    print("✅ Preview saved to led_test_pattern_preview.png")
