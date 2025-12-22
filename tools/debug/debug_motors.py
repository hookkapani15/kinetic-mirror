import time
import math
import sys
from packages.mirror_core.io.serial_manager import SerialManager
from packages.mirror_core.controllers.motor_controller import MotorController

def test_motors():
    print("Initialize Serial Manager...")
    serial = SerialManager(port='AUTO', baudrate=460800)
    serial.start()
    
    if not serial.connected:
        print("Failed to connect to ESP32!")
        return

    print("Initialize Motor Controller...")
    motor = MotorController(num_servos=32)
    
    print("\n--- MOTOR TEST START ---")
    print("Sending wave pattern to all 32 servos...")
    
    try:
        start_time = time.time()
        frame_count = 0
        
        while time.time() - start_time < 10:  # Run for 10 seconds
            t = time.time() - start_time
            
            # Generate wave pattern for 32 servos
            angles = []
            for i in range(32):
                # Sine wave with phase shift for each servo
                angle = 90 + 30 * math.sin(t * 3 + i * 0.2)
                angles.append(angle)
            
            packet = motor.pack_servo_packet(angles)
            
            if serial.send_servo(packet):
                print(f"\rSending packet {frame_count:04d} | T={t:.1f}s", end="")
                frame_count += 1
            else:
                print(f"\r[FAIL] Send failed at {t:.1f}s", end="")
            
            time.sleep(0.05)  # 20 FPS
            
        print("\n\n--- TEST COMPLETE ---")
        print("Did the motors move?")
        
        # Center motors before exit
        print("Centering motors...")
        packet = motor.pack_servo_packet([90] * 32)
        serial.send_servo(packet)
        time.sleep(0.5)
        
    except KeyboardInterrupt:
        print("\nTest interrupted")
    finally:
        serial.stop()

if __name__ == "__main__":
    test_motors()
