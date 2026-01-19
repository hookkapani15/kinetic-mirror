#!/usr/bin/env python3
"""
LED Mapping Test Tool
Displays text, numbers, and patterns on the LED matrix to verify mapping is correct.

Usage:
    python tools/led_mapping_test.py

This will show test patterns on your 32x64 (8 panel) LED matrix.
"""

import serial
import serial.tools.list_ports
import numpy as np
import cv2
import time
import sys

# Matrix dimensions
WIDTH = 32
HEIGHT = 64

def find_esp32s3():
    """Find ESP32-S3 port"""
    for port in serial.tools.list_ports.comports():
        if port.hwid and "303a" in port.hwid.lower():
            print(f"Found ESP32-S3 on {port.device}")
            return port.device
    # Fallback
    ports = list(serial.tools.list_ports.comports())
    if ports:
        return ports[0].device
    return None

def pack_1bit_packet(frame):
    """Pack frame into 1-bit packet for ESP32"""
    # Ensure frame is 64x32
    if frame.shape != (HEIGHT, WIDTH):
        frame = cv2.resize(frame, (WIDTH, HEIGHT), interpolation=cv2.INTER_NEAREST)
    
    # Threshold to binary
    binary = (frame > 128).astype(np.uint8)
    flat = binary.flatten()
    
    # Pack 8 pixels per byte (MSB first)
    packed = []
    for i in range(0, len(flat), 8):
        byte = 0
        for bit in range(8):
            if i + bit < len(flat) and flat[i + bit]:
                byte |= (1 << (7 - bit))
        packed.append(byte)
    
    # Create packet: [0xAA, 0xBB, 0x03, ...256 bytes...]
    packet = bytes([0xAA, 0xBB, 0x03]) + bytes(packed)
    return packet

def create_text_frame(text, font_scale=0.8, thickness=1):
    """Create a frame with text"""
    frame = np.zeros((HEIGHT, WIDTH), dtype=np.uint8)
    
    # Get text size
    font = cv2.FONT_HERSHEY_SIMPLEX
    (text_width, text_height), baseline = cv2.getTextSize(text, font, font_scale, thickness)
    
    # Center text
    x = (WIDTH - text_width) // 2
    y = (HEIGHT + text_height) // 2
    
    cv2.putText(frame, text, (x, y), font, font_scale, 255, thickness)
    return frame

def create_number_frame(number, font_scale=2.0):
    """Create a frame with a large number"""
    frame = np.zeros((HEIGHT, WIDTH), dtype=np.uint8)
    text = str(number)
    font = cv2.FONT_HERSHEY_SIMPLEX
    (tw, th), _ = cv2.getTextSize(text, font, font_scale, 2)
    x = (WIDTH - tw) // 2
    y = (HEIGHT + th) // 2
    cv2.putText(frame, text, (x, y), font, font_scale, 255, 2)
    return frame

def create_panel_numbers():
    """Create frame showing panel numbers 1-8"""
    frame = np.zeros((HEIGHT, WIDTH), dtype=np.uint8)
    font = cv2.FONT_HERSHEY_SIMPLEX
    
    # Panel layout:
    # 1 2  (y: 0-15)
    # 3 4  (y: 16-31)
    # 5 6  (y: 32-47)
    # 7 8  (y: 48-63)
    
    panels = [
        (1, 4, 12),   # Panel 1: x=4, y=12
        (2, 20, 12),  # Panel 2: x=20, y=12
        (3, 4, 28),   # Panel 3
        (4, 20, 28),  # Panel 4
        (5, 4, 44),   # Panel 5
        (6, 20, 44),  # Panel 6
        (7, 4, 60),   # Panel 7
        (8, 20, 60),  # Panel 8
    ]
    
    for num, x, y in panels:
        cv2.putText(frame, str(num), (x, y), font, 0.5, 255, 1)
    
    return frame

def create_arrow_frame(direction):
    """Create frame with arrow pointing in direction"""
    frame = np.zeros((HEIGHT, WIDTH), dtype=np.uint8)
    cx, cy = WIDTH // 2, HEIGHT // 2
    
    if direction == "up":
        pts = np.array([[cx, cy-20], [cx-10, cy+10], [cx+10, cy+10]])
    elif direction == "down":
        pts = np.array([[cx, cy+20], [cx-10, cy-10], [cx+10, cy-10]])
    elif direction == "left":
        pts = np.array([[cx-15, cy], [cx+5, cy-10], [cx+5, cy+10]])
    elif direction == "right":
        pts = np.array([[cx+15, cy], [cx-5, cy-10], [cx-5, cy+10]])
    
    cv2.fillPoly(frame, [pts], 255)
    return frame

def create_corner_markers():
    """Create frame with markers at each corner"""
    frame = np.zeros((HEIGHT, WIDTH), dtype=np.uint8)
    
    # Top-left: "TL"
    cv2.putText(frame, "TL", (1, 10), cv2.FONT_HERSHEY_SIMPLEX, 0.3, 255, 1)
    # Top-right: "TR"
    cv2.putText(frame, "TR", (20, 10), cv2.FONT_HERSHEY_SIMPLEX, 0.3, 255, 1)
    # Bottom-left: "BL"
    cv2.putText(frame, "BL", (1, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.3, 255, 1)
    # Bottom-right: "BR"
    cv2.putText(frame, "BR", (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.3, 255, 1)
    
    # Draw corner dots
    frame[0:3, 0:3] = 255      # Top-left
    frame[0:3, 29:32] = 255    # Top-right
    frame[61:64, 0:3] = 255    # Bottom-left
    frame[61:64, 29:32] = 255  # Bottom-right
    
    return frame

def create_grid_pattern():
    """Create a grid pattern to see panel boundaries"""
    frame = np.zeros((HEIGHT, WIDTH), dtype=np.uint8)
    
    # Horizontal lines at panel boundaries
    frame[0, :] = 255
    frame[15, :] = 255
    frame[16, :] = 255
    frame[31, :] = 255
    frame[32, :] = 255
    frame[47, :] = 255
    frame[48, :] = 255
    frame[63, :] = 255
    
    # Vertical line at panel boundary
    frame[:, 0] = 255
    frame[:, 15] = 255
    frame[:, 16] = 255
    frame[:, 31] = 255
    
    return frame

def create_scrolling_text(text, offset):
    """Create scrolling text frame"""
    # Create wide canvas for text
    font = cv2.FONT_HERSHEY_SIMPLEX
    (tw, th), _ = cv2.getTextSize(text, font, 0.6, 1)
    
    canvas = np.zeros((HEIGHT, tw + WIDTH * 2), dtype=np.uint8)
    cv2.putText(canvas, text, (WIDTH, HEIGHT // 2 + th // 2), font, 0.6, 255, 1)
    
    # Extract visible portion
    start_x = offset % (tw + WIDTH)
    frame = canvas[:, start_x:start_x + WIDTH]
    
    if frame.shape[1] < WIDTH:
        # Pad if needed
        padded = np.zeros((HEIGHT, WIDTH), dtype=np.uint8)
        padded[:, :frame.shape[1]] = frame
        frame = padded
    
    return frame

def create_vertical_bars():
    """Create vertical bars to test left/right pin split"""
    frame = np.zeros((HEIGHT, WIDTH), dtype=np.uint8)
    
    # Left half bars (GPIO 5)
    for x in range(0, 16, 4):
        frame[:, x:x+2] = 255
    
    # Right half bars (GPIO 18) - different pattern
    for x in range(16, 32, 2):
        frame[:, x] = 255
    
    return frame

def create_horizontal_bars():
    """Create horizontal bars to test row mapping"""
    frame = np.zeros((HEIGHT, WIDTH), dtype=np.uint8)
    
    for y in range(0, HEIGHT, 4):
        frame[y:y+2, :] = 255
    
    return frame

def create_checker_pattern(size=4):
    """Create checkerboard pattern"""
    frame = np.zeros((HEIGHT, WIDTH), dtype=np.uint8)
    
    for y in range(HEIGHT):
        for x in range(WIDTH):
            if ((x // size) + (y // size)) % 2 == 0:
                frame[y, x] = 255
    
    return frame

def create_single_pixel_test(x, y):
    """Create frame with single pixel lit"""
    frame = np.zeros((HEIGHT, WIDTH), dtype=np.uint8)
    if 0 <= x < WIDTH and 0 <= y < HEIGHT:
        frame[y, x] = 255
    return frame

def main():
    print("=" * 50)
    print("LED MAPPING TEST TOOL")
    print("=" * 50)
    print(f"Matrix: {WIDTH}x{HEIGHT} (8 panels of 16x16)")
    print()
    
    # Find port
    port = find_esp32s3()
    if not port:
        print("ERROR: No serial port found!")
        return
    
    print(f"Connecting to {port}...")
    
    try:
        ser = serial.Serial(port, 460800, timeout=2)
        ser.dtr = False
        ser.rts = False
        time.sleep(2)
        
        # Clear buffer and verify connection
        ser.reset_input_buffer()
        ser.write(bytes([0xAA, 0xBB, 0x05]))  # PING
        ser.flush()
        time.sleep(0.5)
        
        response = ""
        while ser.in_waiting:
            response += ser.readline().decode('utf-8', errors='ignore')
        
        if "PONG" not in response:
            print(f"WARNING: No PONG received (got: {response.strip()})")
        else:
            print("ESP32 connected and responding!")
        
        print()
        print("TEST PATTERNS:")
        print("-" * 50)
        print("1. Panel Numbers (1-8)")
        print("2. Corner Markers (TL, TR, BL, BR)")
        print("3. Grid Pattern")
        print("4. Arrow UP")
        print("5. Arrow DOWN")
        print("6. Arrow LEFT")
        print("7. Arrow RIGHT")
        print("8. Vertical Bars")
        print("9. Horizontal Bars")
        print("0. Checkerboard")
        print("T. Scrolling Text 'HOOKKAPANI STUDIO'")
        print("N. Count 1-8")
        print("P. Single Pixel Scan")
        print("A. All tests (cycle)")
        print("Q. Quit")
        print("-" * 50)
        
        while True:
            choice = input("\nEnter choice: ").strip().upper()
            
            if choice == 'Q':
                # Clear LEDs
                frame = np.zeros((HEIGHT, WIDTH), dtype=np.uint8)
                ser.write(pack_1bit_packet(frame))
                break
            
            elif choice == '1':
                print("Showing panel numbers...")
                frame = create_panel_numbers()
                ser.write(pack_1bit_packet(frame))
                
            elif choice == '2':
                print("Showing corner markers...")
                frame = create_corner_markers()
                ser.write(pack_1bit_packet(frame))
                
            elif choice == '3':
                print("Showing grid pattern...")
                frame = create_grid_pattern()
                ser.write(pack_1bit_packet(frame))
                
            elif choice == '4':
                print("Showing UP arrow...")
                frame = create_arrow_frame("up")
                ser.write(pack_1bit_packet(frame))
                
            elif choice == '5':
                print("Showing DOWN arrow...")
                frame = create_arrow_frame("down")
                ser.write(pack_1bit_packet(frame))
                
            elif choice == '6':
                print("Showing LEFT arrow...")
                frame = create_arrow_frame("left")
                ser.write(pack_1bit_packet(frame))
                
            elif choice == '7':
                print("Showing RIGHT arrow...")
                frame = create_arrow_frame("right")
                ser.write(pack_1bit_packet(frame))
                
            elif choice == '8':
                print("Showing vertical bars...")
                frame = create_vertical_bars()
                ser.write(pack_1bit_packet(frame))
                
            elif choice == '9':
                print("Showing horizontal bars...")
                frame = create_horizontal_bars()
                ser.write(pack_1bit_packet(frame))
                
            elif choice == '0':
                print("Showing checkerboard...")
                frame = create_checker_pattern()
                ser.write(pack_1bit_packet(frame))
                
            elif choice == 'T':
                print("Scrolling 'HOOKKAPANI STUDIO'... (Press Ctrl+C to stop)")
                try:
                    offset = 0
                    while True:
                        frame = create_scrolling_text("HOOKKAPANI STUDIO", offset)
                        ser.write(pack_1bit_packet(frame))
                        offset += 1
                        time.sleep(0.05)
                except KeyboardInterrupt:
                    print("\nStopped scrolling")
                    
            elif choice == 'N':
                print("Counting 1-8...")
                for i in range(1, 9):
                    frame = create_number_frame(i)
                    ser.write(pack_1bit_packet(frame))
                    time.sleep(1)
                print("Done counting")
                
            elif choice == 'P':
                print("Single pixel scan (Ctrl+C to stop)...")
                print("Watch where the pixel appears on your matrix")
                try:
                    for y in range(0, HEIGHT, 8):
                        for x in range(0, WIDTH, 4):
                            frame = create_single_pixel_test(x, y)
                            # Add coordinate text
                            cv2.putText(frame, f"{x},{y}", (2, 10), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.25, 255, 1)
                            ser.write(pack_1bit_packet(frame))
                            print(f"  Pixel at ({x}, {y})")
                            time.sleep(0.5)
                except KeyboardInterrupt:
                    print("\nStopped scan")
                    
            elif choice == 'A':
                print("Running all tests...")
                tests = [
                    ("Panel Numbers", create_panel_numbers()),
                    ("Corner Markers", create_corner_markers()),
                    ("Grid", create_grid_pattern()),
                    ("Arrow UP", create_arrow_frame("up")),
                    ("Arrow DOWN", create_arrow_frame("down")),
                    ("Arrow LEFT", create_arrow_frame("left")),
                    ("Arrow RIGHT", create_arrow_frame("right")),
                    ("Vertical Bars", create_vertical_bars()),
                    ("Horizontal Bars", create_horizontal_bars()),
                    ("Checkerboard", create_checker_pattern()),
                ]
                
                try:
                    for name, frame in tests:
                        print(f"  {name}...")
                        ser.write(pack_1bit_packet(frame))
                        time.sleep(2)
                except KeyboardInterrupt:
                    print("\nStopped")
                    
            else:
                print("Unknown choice")
        
        ser.close()
        print("Done!")
        
    except serial.SerialException as e:
        print(f"Serial error: {e}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
