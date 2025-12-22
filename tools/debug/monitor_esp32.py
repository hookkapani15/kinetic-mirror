import serial
import time

def monitor_esp32():
    try:
        # Open serial connection
        ser = serial.Serial('COM5', 115200, timeout=1)
        print("Monitoring ESP32 output (press Ctrl+C to stop):\n")
        
        # Read and print output
        while True:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    print(line)
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\nStopped monitoring")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()

if __name__ == "__main__":
    monitor_esp32()
