import serial
import time

def send_simple_pattern():
    try:
        # Open serial connection
        ser = serial.Serial('COM5', 460800, timeout=1)
        print("Connected to ESP32")
        
        # Switch to serial mode
        ser.write(b's\n')
        time.sleep(0.5)
        
        # Create a simple packet: 4 LEDs on in the top-left corner
        packet = bytearray([0xAA, 0xBB, 0x01])  # Header
        packet += bytes([255, 0, 0, 0] * 4)     # First 4 LEDs white, rest off
        packet += bytes([0] * (2048 - 4))       # Pad with zeros
        
        # Send the packet
        print("Sending test pattern...")
        ser.write(packet)
        ser.flush()
        print("Packet sent")
        
        # Close the connection
        time.sleep(2)
        ser.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    send_simple_pattern()
