import serial
import time

def test_esp32_connection(port='COM5', baudrate=460800):
    try:
        # Open serial connection
        ser = serial.Serial(port, baudrate, timeout=1)
        print(f"Connected to {port} at {baudrate} baud")
        
        # Wait for ESP32 to initialize
        time.sleep(2)
        
        # Clear any existing data
        ser.reset_input_buffer()
        
        # Send test command (clear all LEDs)
        print("Sending 'c' command to clear LEDs...")
        ser.write(b'c\n')
        time.sleep(0.5)
        
        # Send pattern 0 (all white with numbers)
        print("Sending pattern 0 (all white with numbers)...")
        ser.write(b'0\n')
        time.sleep(1)
        
        # Read any response
        while ser.in_waiting > 0:
            response = ser.readline().decode('utf-8').strip()
            print(f"Response: {response}")
            
        ser.close()
        print("Test completed")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_esp32_connection()
