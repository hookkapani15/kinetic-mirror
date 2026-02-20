#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LED Controller for Mirror Body Animations
Handles LED matrix rendering and packet packing for ESP32 control

Hardware Configuration:
- 8 panels of 16x16 LEDs = 2048 total LEDs  
- GPIO 5 (LEFT): Controls 1024 LEDs
- GPIO 18 (RIGHT): Controls 1024 LEDs
- WS2812B panels in a 2-column x 4-row grid

MAPPING MODES:
- Mode 0: RAW (no transformation)
- Mode 1: Row-based pin split (rows 0-31 → Pin5, rows 32-63 → Pin18)
- Mode 2: Column-based pin split (left column → Pin5, right column → Pin18)
- Mode 3: Column-based + serpentine within panels
- Mode 4: Full custom mapping
"""

import numpy as np
import cv2
import struct
try:
    from ..utils.crc import crc16_ccitt
except ImportError:
    # Fallback if utils not found (e.g. running standalone)
    def crc16_ccitt(data): return 0


class LEDController:
    # Panel configuration
    PANEL_WIDTH = 16
    PANEL_HEIGHT = 16
    PANELS_COLS = 2
    PANELS_ROWS = 4
    LEDS_PER_PIN = 1024
    
    # Mapping modes
    MODE_RAW = 0
    MODE_ROW_SPLIT = 1
    MODE_COLUMN_SPLIT = 2
    MODE_COLUMN_SERPENTINE = 3
    MODE_FULL_CUSTOM = 4
    
    def __init__(self, width=32, height=64, mapping_mode=3):
        self.width = width
        self.height = height
        
        # MAPPING CONFIGURATION
        # Try different modes until you find the one that works!
        self.mapping_mode = mapping_mode
        
        # Legacy settings (used by some modes)
        self.flip_x = False
        self.flip_y = False
        
        # Per-panel serpentine (common in WS2812B matrices)
        self.serpentine_rows = True
        
        # Panel order on each pin (for MODE_COLUMN_SPLIT and MODE_COLUMN_SERPENTINE)
        # Left pin (GPIO 5) has panels 1,3,5,7 from top to bottom
        # Right pin (GPIO 18) has panels 2,4,6,8 from top to bottom
        self.left_pin_panels = [1, 3, 5, 7]   # Panels on GPIO 5
        self.right_pin_panels = [2, 4, 6, 8]  # Panels on GPIO 18
        
        # Auto-detected mapping (loaded from file if exists)
        self.panel_mapping = None
        self._load_calibration_mapping()
        
        # Print current mode
        mode_names = {0: "RAW", 1: "ROW_SPLIT", 2: "COLUMN_SPLIT", 
                      3: "COLUMN_SERPENTINE", 4: "FULL_CUSTOM", 5: "AUTO_CALIBRATED"}
        if self.panel_mapping:
            self.mapping_mode = 5  # Use auto-calibrated mode
        print(f"[LEDController] Mapping mode: {mode_names.get(self.mapping_mode, 'UNKNOWN')}")
    
    def _load_calibration_mapping(self):
        """Load auto-calibrated mapping from JSON file if it exists."""
        import json
        from pathlib import Path
        
        # Look for mapping file in data directory
        possible_paths = [
            Path(__file__).parents[3] / "data" / "led_mapping.json",
            Path("data/led_mapping.json"),
        ]
        
        for mapping_path in possible_paths:
            if mapping_path.exists():
                try:
                    with open(mapping_path, 'r') as f:
                        config = json.load(f)
                    
                    if "mapping" in config:
                        self.panel_mapping = {
                            int(k): v for k, v in config["mapping"].items()
                        }
                        print(f"[LEDController] Loaded calibration from {mapping_path}")
                        print(f"[LEDController] Mapping: {self.panel_mapping}")
                        return
                except Exception as e:
                        print(f"[LEDController] Failed to load mapping: {e}")

    def get_panel_rect(self, panel_index):
        """
        Get the bounding box (x, y, w, h) for a specific logical panel (0-7).
        Panel Layout (0-7):
        0 1
        2 3
        4 5
        6 7
        """
        if not (0 <= panel_index < 8):
            raise ValueError("Panel index must be 0-7")
            
        row = panel_index // 2
        col = panel_index % 2
        
        x = col * self.PANEL_WIDTH
        y = row * self.PANEL_HEIGHT
        
        return (x, y, self.PANEL_WIDTH, self.PANEL_HEIGHT)

    def draw_on_panel(self, frame, panel_index, draw_func):
        """
        Execute drawing operations on a specific panel's ROI.
        
        Args:
            frame: The full 32x64 frame to draw on
            panel_index: Index of the panel (0-7)
            draw_func: Function that accepts an ROI (numpy slice) as argument
                       e.g. lambda roi: roi[:] = 255
        """
        x, y, w, h = self.get_panel_rect(panel_index)
        
        # Extract ROI (Region of Interest)
        # Note: numpy uses [y:y+h, x:x+w]
        roi = frame[y:y+h, x:x+w]
        
        # Execute drawing function on this slice
        # The slice is a view, so modifying it modifies original frame
        draw_func(roi)

    def remap_for_hardware(self, frame):
        """
        Remap LED frame to match physical hardware wiring.
        
        Args:
            frame: 64x32 numpy array (height x width)
        Returns:
            Remapped 64x32 numpy array ready for transmission
        """
        if self.mapping_mode == self.MODE_RAW:
            return frame.copy()
            
        elif self.mapping_mode == self.MODE_ROW_SPLIT:
            # Original simple mapping with optional flips
            remapped = frame.copy()
            if self.flip_y:
                remapped = np.flip(remapped, axis=0)
            if self.flip_x:
                remapped = np.flip(remapped, axis=1)
            return remapped
            
        elif self.mapping_mode == self.MODE_COLUMN_SPLIT:
            # Column-based pin split (left column → first 1024, right column → second 1024)
            return self._remap_column_split(frame, serpentine=False)
            
        elif self.mapping_mode == self.MODE_COLUMN_SERPENTINE:
            # Column-based + serpentine within panels
            return self._remap_column_split(frame, serpentine=True)
            
        elif self.mapping_mode == self.MODE_FULL_CUSTOM:
            return self._remap_full_custom(frame)
        
        elif self.mapping_mode == 5 and self.panel_mapping:
            # AUTO_CALIBRATED mode: use detected panel mapping
            return self._remap_auto_calibrated(frame)
            
        else:
            return frame.copy()
    
    def _remap_auto_calibrated(self, frame):
        """
        Remap frame using auto-calibrated panel positions.
        Uses self.panel_mapping: {logical_panel -> physical_position}
        """
        output = np.zeros_like(frame)
        
        for logical_panel in range(1, 9):
            physical_pos = self.panel_mapping.get(logical_panel, logical_panel)
            
            # Source: where we READ from (logical layout)
            src_row = (logical_panel - 1) // 2
            src_col = (logical_panel - 1) % 2
            src_y = src_row * 16
            src_x = src_col * 16
            
            # Destination: where we WRITE to (physical layout)
            dst_row = (physical_pos - 1) // 2
            dst_col = (physical_pos - 1) % 2
            dst_y = dst_row * 16
            dst_x = dst_col * 16
            
            # Copy panel
            output[dst_y:dst_y+16, dst_x:dst_x+16] = frame[src_y:src_y+16, src_x:src_x+16]
        
        return output
    
    def _remap_column_split(self, frame, serpentine=True):
        """
        Remap for column-based pin split.
        
        Firmware data layout (row-major in 32-wide frame):
          - Flat indices 0-1023  (rows 0-31)  → GPIO 5  → left physical column
          - Flat indices 1024-2047 (rows 32-63) → GPIO 18 → right physical column
        
        Each physical column is 64 tall × 16 wide (4 panels of 16×16).
        The firmware reads 32 pixels per row, but each physical column is only
        16 wide, so 2 consecutive physical rows get packed into each 32-pixel
        output row.
        
        Output layout (rows 0-31 = left column):
          Row 0:  [left_panel1_physRow0 (16px)] [left_panel1_physRow1 (16px)]
          Row 1:  [left_panel1_physRow2 (16px)] [left_panel1_physRow3 (16px)]
          ...
          Row 7:  [left_panel1_physRow14]       [left_panel1_physRow15]
          Row 8:  [left_panel3_physRow0]        [left_panel3_physRow1]
          ...
          Row 31: [left_panel7_physRow14]       [left_panel7_physRow15]

        Output layout (rows 32-63 = right column):
          Same structure for right_pin_panels.
        """
        output = np.zeros((self.height, self.width), dtype=np.uint8)
        
        def pack_column(pin_panels, output_row_offset):
            """Pack 4 panels (64×16 physical) into 32 output rows (32 wide each)."""
            for panel_idx, panel_num in enumerate(pin_panels):
                # Source: where this panel lives in the logical frame
                src_row = (panel_num - 1) // 2  # Panel row (0-3)
                src_col = (panel_num - 1) % 2   # Panel col (0=left, 1=right)
                src_y_start = src_row * self.PANEL_HEIGHT
                src_x_start = src_col * self.PANEL_WIDTH
                
                # Each panel has 16 physical rows of 16 pixels.
                # Two physical rows pack into one 32-wide output row.
                # So 16 physical rows → 8 output rows per panel.
                for local_y in range(self.PANEL_HEIGHT):
                    # Which output row does this physical row go to?
                    # panel_idx * 8 = base output row for this panel
                    # local_y // 2 = which pair of physical rows
                    dst_row = output_row_offset + panel_idx * 8 + (local_y // 2)
                    
                    # Even physical rows go to left half (x=0-15)
                    # Odd physical rows go to right half (x=16-31) 
                    x_offset = 0 if (local_y % 2 == 0) else 16
                    
                    for local_x in range(self.PANEL_WIDTH):
                        src_y = src_y_start + local_y
                        src_x = src_x_start + local_x
                        
                        # Apply serpentine within panel if needed
                        if serpentine and (local_y & 1):  # Odd rows reversed
                            dst_x = x_offset + (self.PANEL_WIDTH - 1 - local_x)
                        else:
                            dst_x = x_offset + local_x
                        
                        output[dst_row, dst_x] = frame[src_y, src_x]
        
        # Left column panels → output rows 0-31
        pack_column(self.left_pin_panels, 0)
        # Right column panels → output rows 32-63  
        pack_column(self.right_pin_panels, 32)
        
        return output
    
    def _remap_full_custom(self, frame):
        """
        Full custom pixel-by-pixel remapping.
        Override this method for completely custom wiring.
        """
        # For now, just apply flips
        remapped = frame.copy()
        if self.flip_y:
            remapped = np.flip(remapped, axis=0)
        if self.flip_x:
            remapped = np.flip(remapped, axis=1)
        return remapped

    def render_frame(self, pose_results, seg_mask):
        """
        Render LED frame from pose results and segmentation mask
        Creates a silhouette for the LED matrix
        """
        led_frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)

        try:
            if pose_results and pose_results.pose_landmarks:
                # Use segmentation mask if available and valid
                if seg_mask is not None and hasattr(seg_mask, 'shape') and len(seg_mask.shape) >= 2:
                    try:
                        # Resize with explicit type handling
                        mask_resized = cv2.resize(seg_mask, (self.width, self.height), interpolation=cv2.INTER_NEAREST)
                        binary_mask = (mask_resized > 0.5).astype(np.uint8) * 255
                        led_frame[:, :, 0] = binary_mask
                        led_frame[:, :, 1] = binary_mask
                        led_frame[:, :, 2] = binary_mask
                    except Exception as e:
                        print(f"[LEDController] Mask resize failed: {e}")
                        # Fallback to landmarks
                        self._render_landmarks(led_frame, pose_results)
                else:
                    # Fallback: draw pose landmarks as silhouette
                    self._render_landmarks(led_frame, pose_results)
        except Exception as e:
            print(f"[LEDController] render_frame error: {e}")
            
        return led_frame

    def _render_landmarks(self, led_frame, pose_results):
        """Helper to render landmarks when mask fails"""
        h, w = self.height, self.width
        for landmark in pose_results.pose_landmarks.landmark:
            if landmark.visibility > 0.6:  # Lowered threshold slightly
                x = int(landmark.x * w)
                y = int(landmark.y * h)
                # Expand to 3x3 dot for visibility
                if 0 <= x < w and 0 <= y < h:
                    led_frame[y, x] = [255, 255, 255]
                    # Draw minimal cross pattern
                    if x > 0: led_frame[y, x-1] = [100, 100, 100]
                    if x < w-1: led_frame[y, x+1] = [100, 100, 100]
                    if y > 0: led_frame[y-1, x] = [100, 100, 100]
                    if y < h-1: led_frame[y+1, x] = [100, 100, 100]

    def pack_led_packet(self, led_frame):
        """
        Pack LED frame into firmware-compatible packet.
        Firmware expects:
          [0xAA, 0xBB, 0x01, 2048 bytes of brightness]
        """
        if led_frame.shape[:2] != (self.height, self.width):
            raise ValueError(f"LED frame must be {self.height}x{self.width}, got {led_frame.shape[:2]}")

        # Convert to grayscale brightness
        if led_frame.ndim == 3 and led_frame.shape[2] == 3:
            brightness = led_frame.max(axis=2)
        else:
            brightness = led_frame

        brightness = np.clip(brightness, 0, 255).astype(np.uint8)
        
        # Apply hardware mapping before transmission
        brightness = self.remap_for_hardware(brightness)

        # Fast path: use numpy tobytes() instead of Python list iteration
        flat = brightness.flatten()
        if flat.size != self.width * self.height:
            raise ValueError("LED frame does not contain expected number of pixels")

        header = b'\xAA\xBB\x01'
        return header + flat.tobytes()

    def pack_led_packet_1bit(self, led_frame, threshold=128):
        """
        Pack LED frame into 1-bit compressed packet.
        8x smaller than full brightness! (256 bytes vs 2048 bytes)
        
        Firmware expects:
          [0xAA, 0xBB, 0x03, 256 bytes of packed bits]
        
        Each byte contains 8 pixels (MSB first)
        Pixel order: row-major, left to right, top to bottom
        """
        if led_frame.shape[:2] != (self.height, self.width):
            raise ValueError(f"LED frame must be {self.height}x{self.width}")

        # Convert to grayscale if needed
        if led_frame.ndim == 3 and led_frame.shape[2] == 3:
            brightness = led_frame.max(axis=2)
        else:
            brightness = led_frame

        # Apply hardware mapping
        brightness = self.remap_for_hardware(brightness)
        
        # Threshold to binary
        binary = (brightness > threshold).astype(np.uint8)
        flat = binary.flatten()
        
        # Pack 8 pixels per byte
        packed = []
        for i in range(0, len(flat), 8):
            byte_val = 0
            for bit in range(8):
                if i + bit < len(flat) and flat[i + bit]:
                    byte_val |= (1 << (7 - bit))
            packed.append(byte_val)
        
        # Header: 0xAA 0xBB 0x03 (0x03 = 1-bit mode)
        packet = bytes([0xAA, 0xBB, 0x03]) + bytes(packed)
        return packet

    def pack_led_packet_rle(self, led_frame, threshold=128):
        """
        Pack LED frame using Run-Length Encoding.
        Extremely efficient for silhouettes with large solid areas.
        
        Firmware expects:
          [0xAA, 0xBB, 0x04, length_hi, length_lo, RLE data...]
        
        RLE format: alternating (count, value) pairs
        - count: 1-255 (0 = end marker)
        - value: 0 or 255
        """
        if led_frame.shape[:2] != (self.height, self.width):
            raise ValueError(f"LED frame must be {self.height}x{self.width}")

        # Convert to grayscale if needed
        if led_frame.ndim == 3 and led_frame.shape[2] == 3:
            brightness = led_frame.max(axis=2)
        else:
            brightness = led_frame

        # Apply hardware mapping
        brightness = self.remap_for_hardware(brightness)
        
        # Threshold to binary (0 or 255)
        binary = ((brightness > threshold).astype(np.uint8)) * 255
        flat = binary.flatten()
        
        # RLE encode
        rle = []
        i = 0
        while i < len(flat):
            val = flat[i]
            count = 0
            while i < len(flat) and flat[i] == val and count < 255:
                count += 1
                i += 1
            rle.extend([count, val])
        
        # Header: 0xAA 0xBB 0x04 length(2 bytes) data...
        rle_len = len(rle)
        packet = bytes([0xAA, 0xBB, 0x04, (rle_len >> 8) & 0xFF, rle_len & 0xFF]) + bytes(rle)
        return packet

    def pack_led_packet_1bit_crc(self, led_frame, frame_id: int):
        """
        Pack 1-bit LED packet with CRC and Frame ID for integrity.
        Structure:
          [AA BB 07] [FrameID(2)] [Data(256)] [CRC(2)]
          Total: 3 + 2 + 256 + 2 = 263 bytes
          (Type 0x07 = 1-bit + CRC)
        """
        # reusing logic from pack_led_packet_1bit but modifying resizing/packing
        if led_frame.shape[:2] != (self.height, self.width):
             # Resize/Threshold on the fly if needed
             if led_frame.ndim == 3: led_frame = led_frame.max(axis=2)
             led_frame = cv2.resize(led_frame, (self.width, self.height), interpolation=cv2.INTER_NEAREST)

        # Threshold to binary
        binary = (led_frame > 128).astype(np.uint8)
        flat = binary.flatten()
        
        # Pack 8 pixels per byte
        packed = bytearray(256)
        # Fast packing using numpy
        # Reshape to (256, 8)
        # bit_weights = np.array([128, 64, 32, 16, 8, 4, 2, 1], dtype=np.uint8)
        # This is getting complex to vectorise correctly with simple numpy without lookups
        # Fallback to loop for safety (it's only 256 iterations)
        
        byte_idx = 0
        for i in range(0, 2048, 8):
            byte_val = 0
            for bit in range(8):
                if flat[i + bit]:
                    byte_val |= (1 << (7 - bit))
            packed[byte_idx] = byte_val
            byte_idx += 1
            
        # Build payload for CRC calculation
        # Payload = Type(1) + FrameID(2) + Data(256)
        # Actually header is usually excluded from CRC in some protocols, 
        # but here we'll include Type+ID+Data to be safe.
        
        type_byte = 0x07 # New type for CRC packet
        fid_hi = (frame_id >> 8) & 0xFF
        fid_lo = frame_id & 0xFF
        
        payload = bytearray([type_byte, fid_hi, fid_lo]) + packed
        crc = crc16_ccitt(payload)
        
        packet = bytearray([0xAA, 0xBB]) + payload + bytearray([(crc >> 8) & 0xFF, crc & 0xFF])
        return bytes(packet)

    def pack_remapped_led_packet_1bit(self, remapped_frame):
        """
        Pack an ALREADY REMAPPED frame into 1-bit format (Type 0x03).
        Compatible with firmware v2.0+.
        
        Args:
            remapped_frame (np.array): 64x32 frame, already remapped for hardware
        Returns:
            bytes: 259-byte packet [0xAA, 0xBB, 0x03, 256 bytes data]
        """
        # Threshold to binary
        if remapped_frame.max() > 1:
            binary = (remapped_frame > 127).astype(np.uint8)
        else:
            binary = remapped_frame.astype(np.uint8)
            
        flat = binary.flatten()
        
        # Pack 8 pixels per byte (MSB first)
        packed = bytearray(256)
        byte_idx = 0
        for i in range(0, min(len(flat), 2048), 8):
            byte_val = 0
            for bit in range(8):
                if i + bit < len(flat) and flat[i + bit]:
                    byte_val |= (1 << (7 - bit))
            packed[byte_idx] = byte_val
            byte_idx += 1
        
        return bytes([0xAA, 0xBB, 0x03]) + bytes(packed)

    def pack_remapped_led_packet_1bit_crc(self, remapped_frame, frame_id: int):
        """
        Pack an ALREADY REMAPPED frame into 1-bit format with CRC.
        USE THIS for "What You See Is What You Send" verification.
        
        Args:
            remapped_frame (np.array): 32x64 frame, already remapped for hardware
            frame_id (int): 16-bit frame ID
        """
        # Ensure binary (0 or 1)
        # We assume input is already decent, but let's be safe
        if remapped_frame.max() > 1:
            threshold = 127
            if remapped_frame.dtype == np.uint8:
                 binary = (remapped_frame > threshold).astype(np.uint8)
            else:
                 binary = (remapped_frame > 0.5).astype(np.uint8)
        else:
            binary = remapped_frame.astype(np.uint8)
            
        flat = binary.flatten()
        
        # Pack 8 pixels per byte (MSB first)
        # Firmware expects 256 bytes for 2048 LEDs
        packed = bytearray(256)
        
        byte_idx = 0
        pixel_idx = 0
        max_pixels = 2048
        
        while pixel_idx < max_pixels and byte_idx < 256:
            byte_val = 0
            for bit in range(8):
                if pixel_idx + bit < len(flat) and flat[pixel_idx + bit]:
                    byte_val |= (1 << (7 - bit))
            packed[byte_idx] = byte_val
            byte_idx += 1
            pixel_idx += 8
            
        # Build payload for CRC calculation
        # Payload = Type(1) + FrameID(2) + Data(256)
        # Type is 0x07
        
        type_byte = 0x07 
        fid_hi = (frame_id >> 8) & 0xFF
        fid_lo = frame_id & 0xFF
        
        payload = bytearray([type_byte, fid_hi, fid_lo]) + packed
        
        # Calculate CRC
        from ..utils.crc import crc16_ccitt # Ensure import if not at top level, though it is
        crc = crc16_ccitt(payload)
        
        # Construct final packet: Header(2) + Payload(259) + CRC(2)
        packet = bytearray([0xAA, 0xBB]) + payload + bytearray([(crc >> 8) & 0xFF, crc & 0xFF])
        return bytes(packet)


# Quick test
if __name__ == "__main__":
    print("Testing LED Controller modes...")
    
    for mode in range(5):
        led = LEDController(mapping_mode=mode)
        pattern = np.zeros((64, 32), dtype=np.uint8)
        pattern[0:16, 0:16] = 255  # Light panel 1
        packet = led.pack_led_packet(pattern)
        print(f"  Mode {mode}: Packet size = {len(packet)}")
    
    print("Done!")
