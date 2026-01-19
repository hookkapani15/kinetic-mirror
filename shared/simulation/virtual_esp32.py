
"""
Virtual ESP32 Firmware
Mimics the behavior of the real ESP32 firmware for LEDs and Motors.
"""

import threading
import time
import queue

class VirtualESP32:
    def __init__(self):
        self.running = True
        self.led_state = [0] * (2048)  # 2048 LEDs (brightness)
        self.motor_angles = [90] * 64   # 64 Servos (0-180 degrees)
        self.buffer = []
        self.state_lock = threading.Lock()
        
        # Output queue (to send data back to PC, e.g. "READY")
        self.output_queue = queue.Queue()
        
        # Simulate boot delay
        self.boot_timer = threading.Timer(1.0, self._boot_complete)
        self.boot_timer.start()

    def _boot_complete(self):
        """Called when 'boot' is complete"""
        self.output_queue.put(b"READY\n")

    def write(self, data):
        """Receive data from PC (bytes)"""
        with self.state_lock:
            for byte in data:
                self.buffer.append(byte)
            self._process_buffer()

    def read(self):
        """Send data to PC"""
        try:
            return self.output_queue.get_nowait()
        except queue.Empty:
            return None

    def _process_buffer(self):
        """Parse the internal buffer for packets"""
        # Protocol: 
        #   Header: AA BB
        #   Type:   01 (LED 8-bit) or 02 (Servo) or 03 (LED 1-bit) or 04 (LED RLE)
        #   Data:   ...
        
        while len(self.buffer) > 2:
            # Look for Header AA BB
            if self.buffer[0] != 0xAA or self.buffer[1] != 0xBB:
                # Pop byte and continue
                self.buffer.pop(0)
                continue
            
            # Found Header
            if len(self.buffer) < 3:
                return # Need more data
                
            packet_type = self.buffer[2]
            
            if packet_type == 0x01:  # LED Packet (8-bit brightness)
                # Needs 2048 bytes + 3 header bytes = 2051 bytes
                if len(self.buffer) < 2051:
                    return # Wait for more data
                
                # Extract LED data
                led_data = self.buffer[3:2051]
                self.led_state = led_data
                
                # Consume packet
                self.buffer = self.buffer[2051:]
                
            elif packet_type == 0x03:  # LED Packet (1-bit packed)
                # Needs 256 bytes + 3 header bytes = 259 bytes
                if len(self.buffer) < 259:
                    return # Wait for more data
                
                # Extract packed bits and unpack to brightness
                packed_data = self.buffer[3:259]
                led_data = []
                for byte in packed_data:
                    for bit in range(7, -1, -1):  # MSB first
                        led_data.append(255 if (byte & (1 << bit)) else 0)
                
                self.led_state = led_data[:2048]  # Ensure exactly 2048
                
                # Consume packet
                self.buffer = self.buffer[259:]
                
            elif packet_type == 0x04:  # LED Packet (RLE compressed)
                # Header: AA BB 04 len_hi len_lo data...
                if len(self.buffer) < 5:
                    return # Need more data
                
                rle_len = (self.buffer[3] << 8) | self.buffer[4]
                total_size = 5 + rle_len
                
                if len(self.buffer) < total_size:
                    return # Wait for more data
                
                # Decode RLE
                rle_data = self.buffer[5:total_size]
                led_data = []
                i = 0
                while i < len(rle_data) - 1 and len(led_data) < 2048:
                    count = rle_data[i]
                    value = rle_data[i + 1]
                    led_data.extend([value] * count)
                    i += 2
                
                self.led_state = led_data[:2048]
                
                # Consume packet
                self.buffer = self.buffer[total_size:]
                
            elif packet_type == 0x02:  # Servo Packet
                # Needs 64 * 2 bytes + 3 header bytes = 131 bytes
                num_servos = 64
                payload_size = num_servos * 2
                total_size = payload_size + 3
                
                if len(self.buffer) < total_size:
                    return # Wait for more data
                
                # Extract Servo data
                # 64 servos, 2 bytes each (High byte, Low byte)
                # Value 0-1000 maps to 0-180 degrees
                new_angles = []
                for i in range(num_servos):
                    idx = 3 + (i * 2)
                    hi = self.buffer[idx]
                    lo = self.buffer[idx+1]
                    val = (hi << 8) | lo
                    
                    # Map 0-1000 -> 0-180
                    angle = (val / 1000.0) * 180.0
                    new_angles.append(angle)
                
                # Ensure we have enough slots
                if len(self.motor_angles) < num_servos:
                     self.motor_angles = [90] * num_servos

                for i in range(min(len(new_angles), len(self.motor_angles))):
                    self.motor_angles[i] = new_angles[i]
                
                # Consume packet
                self.buffer = self.buffer[total_size:]
                
            else:
                 # Unknown packet type, skip header
                self.buffer = self.buffer[2:]

    def get_server_state(self):
        """Thread-safe access to state for visualizer"""
        with self.state_lock:
            return {
                "leds": list(self.led_state),
                "motors": list(self.motor_angles)
            }
