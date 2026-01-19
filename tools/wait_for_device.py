import serial.tools.list_ports
import time
import sys

print("Searching for ESP32/USB Serial devices...")
print("Please plug in your ESP32 now...")

while True:
    ports = serial.tools.list_ports.comports()
    found = False
    for p in ports:
        # Ignore Bluetooth ports
        if "Bluetooth" in p.description:
            continue
            
        print(f"\n✅ FOUND DEVICE: {p.device} - {p.description}")
        print(f"HWID: {p.hwid}")
        found = True
        
    if found:
        print("\nDevice detected! You can now try running the app again.")
        break
        
    sys.stdout.write(".")
    sys.stdout.flush()
    time.sleep(1)
