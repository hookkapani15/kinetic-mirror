import serial
import time

def send_test_pattern(port='COM5', baudrate=460800):
    try:
        # Open serial connection
        with serial.Serial(port, baudrate, timeout=1) as ser:
            print(f"Connected to {port} at {baudrate} baud")
            
            # Switch to serial mode
            ser.write(b's\n')
            time.sleep(0.5)
            
            # Create a simple pattern: top-left corner white
            packet = bytearray([0xAA, 0xBB, 0x01])  # Header
            packet += bytearray([255])  # First LED white
            packet += bytearray([0] * 2047)  # Rest black
            
            # Send the packet
            print("Sending test pattern...")
            ser.write(packet)
            ser.flush()
            print("Packet sent. Check if top-left LED is white.")
            
            # Keep the connection open
            input("Press Enter to exit...")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    send_test_pattern()
