import serial
import time
import numpy as np

def create_led_packet(pattern_type=0, panel_id=1):
    """
    Create an LED packet in the format expected by the ESP32
    Format: [0xAA, 0xBB, 0x01, 2048 bytes of data]
    """
    # Start with header
    packet = bytearray([0xAA, 0xBB, 0x01])
    
    # Create a 32x64 = 2048 LED array
    leds = np.zeros((64, 32), dtype=np.uint8)
    
    if pattern_type == 0:  # All white with numbers
        leds.fill(255)  # All white
        # Add panel numbers (0-255, where 0=black, 255=white)
        for panel in range(8):
            row = (panel // 2) * 16 + 8
            col = (panel % 2) * 16 + 4
            leds[row:row+8, col:col+8] = 0  # Black number
    
    elif 1 <= pattern_type <= 8:  # Individual panel
        row_start = ((pattern_type - 1) // 2) * 16
        col_start = ((pattern_type - 1) % 2) * 16
        leds[row_start:row_start+16, col_start:col_start+16] = 255
    
    # Flatten the array and add to packet
    packet.extend(leds.flatten().tobytes())
    
    return packet

def main():
    port = 'COM5'  # Change this to your ESP32 port
    baudrate = 460800
    
    try:
        # Open serial connection
        ser = serial.Serial(port, baudrate, timeout=1)
        print(f"Connected to {port} at {baudrate} baud")
        
        # Wait for ESP32 to initialize
        time.sleep(2)
        
        # Clear any existing data
        ser.reset_input_buffer()
        
        # Send command to switch to serial mode
        print("Switching to serial mode...")
        ser.write(b's\n')
        time.sleep(0.5)
        
        # Send pattern 0 (all white with numbers)
        print("Sending pattern 0 (all white with numbers)...")
        packet = create_led_packet(0)
        ser.write(packet)
        ser.flush()
        print(f"Sent {len(packet)} bytes")
        
        # Wait a bit
        time.sleep(2)
        
        # Test individual panels
        for panel in range(1, 9):
            print(f"Testing panel {panel}...")
            packet = create_led_packet(panel)
            ser.write(packet)
            ser.flush()
            time.sleep(1)
        
        # Clear at the end
        print("Clearing all LEDs...")
        ser.write(b'c\n')
        
        # Close the connection
        ser.close()
        print("Test completed")
        
    except Exception as e:
        print(f"Error: {e}")
        if 'ser' in locals() and ser.is_open:
            ser.close()

if __name__ == "__main__":
    main()
