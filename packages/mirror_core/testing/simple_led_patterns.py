"""
Additional simple LED test patterns based on working checkerboard/gradient
"""
import numpy as np


def generate_vertical_bars(width=32, height=64):
    """Vertical bars pattern - alternating columns"""
    pattern = np.zeros((height, width), dtype=np.uint8)
    for x in range(width):
        if x % 2 == 0:
            pattern[:, x] = 255
    return pattern


def generate_horizontal_bars(width=32, height=64):
    """Horizontal bars pattern - alternating rows"""
    pattern = np.zeros((height, width), dtype=np.uint8)
    for y in range(height):
        if y % 2 == 0:
            pattern[y, :] = 255
    return pattern


def generate_diagonal_gradient(width=32, height=64):
    """Diagonal gradient pattern"""
    pattern = np.zeros((height, width), dtype=np.uint8)
    max_dist = np.sqrt(width**2 + height**2)
    for y in range(height):
        for x in range(width):
            dist = np.sqrt(x**2 + y**2)
            value = int((dist / max_dist) * 255)
            pattern[y, x] = value
    return pattern


def generate_concentric_squares(width=32, height=64):
    """Concentric squares from center"""
    pattern = np.zeros((height, width), dtype=np.uint8)
    center_x = width // 2
    center_y = height // 2
    
    for y in range(height):
        for x in range(width):
            dist = max(abs(x - center_x), abs(y - center_y))
            max_dist = max(center_x, center_y)
            value = int((dist / max_dist) * 255)
            pattern[y, x] = value
    return pattern


def generate_panel_brightness_test(width=32, height=64):
    """
    8 panels with different brightness levels (similar to working patterns)
    Panel 1 = 30, Panel 2 = 60, ..., Panel 8 = 255
    """
    pattern = np.zeros((height, width), dtype=np.uint8)
    
    brightness_levels = [30, 60, 90, 120, 150, 180, 210, 255]
    panel_idx = 0
    
    # 2 columns × 4 rows
    for row in range(4):
        for col in range(2):
            y_start = row * 16
            y_end = y_start + 16
            x_start = col * 16
            x_end = x_start + 16
            
            pattern[y_start:y_end, x_start:x_end] = brightness_levels[panel_idx]
            panel_idx += 1
    
    return pattern


def generate_panel_corners(width=32, height=64):
    """
    Each panel has a bright corner to identify it
    Panel 1 = top-left corner, Panel 2 = top-right, etc.
    """
    pattern = np.zeros((height, width), dtype=np.uint8)
    
    corner_patterns = [
        (0, 0),    # Top-left
        (0, 12),   # Top-right
        (12, 0),   # Bottom-left
        (12, 12),  # Bottom-right
        (6, 6),    # Center
        (0, 6),    # Top-center
        (6, 0),    # Left-center
        (6, 12),   # Right-center
    ]
    
    panel_idx = 0
    
    # 2 columns × 4 rows
    for row in range(4):
        for col in range(2):
            y_start = row * 16
            x_start = col * 16
            
            # Draw a 4×4 bright square at specific corner
            cy, cx = corner_patterns[panel_idx]
            for dy in range(4):
                for dx in range(4):
                    y = y_start + cy + dy
                    x = x_start + cx + dx
                    if y < height and x < width:
                        pattern[y, x] = 255
            
            panel_idx += 1
    
    return pattern


def generate_pulse_wave(width=32, height=64, frequency=4):
    """Horizontal pulse wave pattern"""
    pattern = np.zeros((height, width), dtype=np.uint8)
    for x in range(width):
        value = int((np.sin(x * frequency * 2 * np.pi / width) + 1) * 127.5)
        pattern[:, x] = value
    return pattern


if __name__ == "__main__":
    import cv2
    
    patterns = {
        'vertical_bars': generate_vertical_bars(),
        'horizontal_bars': generate_horizontal_bars(),
        'diagonal_gradient': generate_diagonal_gradient(),
        'concentric_squares': generate_concentric_squares(),
        'brightness_test': generate_panel_brightness_test(),
        'panel_corners': generate_panel_corners(),
        'pulse_wave': generate_pulse_wave()
    }
    
    for name, pattern in patterns.items():
        cv2.imwrite(f"led_pattern_{name}.png", pattern)
        print(f"✅ Saved {name}: {pattern.shape}")
