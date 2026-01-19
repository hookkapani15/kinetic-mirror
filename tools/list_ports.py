#!/usr/bin/env python3
import serial.tools.list_ports

print("=" * 80)
print("Current Serial Ports Detected")
print("=" * 80)
print()

ports = serial.tools.list_ports.comports()
print(f"Total ports found: {len(ports)}")
print()

if len(ports) == 0:
    print("No serial ports detected!")
    print()
    print("Troubleshooting:")
    print("1. Make sure your ESP32/Arduino is connected via USB")
    print("2. Try a different USB cable (data cable, not charging only)")
    print("3. Try a different USB port")
    print("4. Install required drivers:")
    print("   - ESP32: CP210x driver (Windows)")
    print("   - Arduino: CH340 driver (Windows)")
    print("5. Check Device Manager on Windows for 'Other Devices'")
else:
    for i, p in enumerate(ports, 1):
        desc = p.description if p.description else "Unknown"
        hwid = p.hwid if hasattr(p, 'hwid') else "N/A"
        vid = getattr(p, 'vid', None)
        pid = getattr(p, 'pid', None)

        print(f"[{i}] Port: {p.device}")
        print(f"    Description: {desc}")
        print(f"    HWID: {hwid}")
        print(f"    VID:PID: {f'0x{vid:04x}:0x{pid:04x}' if vid and pid else 'N/A'}")

        # Identify device type
        desc_lower = desc.lower()
        hwid_lower = hwid.lower()
        device_type = "Unknown"
        if 'bluetooth' in desc_lower:
            device_type = "Bluetooth (will be skipped)"
        elif 'ch340' in desc_lower or 'ch340' in hwid_lower:
            device_type = "Arduino Nano (CH340)"
        elif 'cp210' in desc_lower or 'cp210' in hwid_lower:
            device_type = "ESP32 (CP210x bridge)"
        elif 'esp32' in desc_lower or 'esp32' in hwid_lower:
            device_type = "ESP32-S3 (native USB)"
        elif 'ftdi' in desc_lower or 'ftdi' in hwid_lower:
            device_type = "FTDI device"

        print(f"    Type: {device_type}")
        print()
