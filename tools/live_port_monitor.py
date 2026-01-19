#!/usr/bin/env python3
"""
Live port monitor - helps diagnose USB device detection
Run this and plug/unplug your devices to see what gets detected
"""
import serial.tools.list_ports
import time

def get_port_info():
    ports = serial.tools.list_ports.comports()
    info = []
    for p in ports:
        desc = p.description if p.description else "Unknown"
        hwid = p.hwid if hasattr(p, 'hwid') else "N/A"
        vid = getattr(p, 'vid', None)
        pid = getattr(p, 'pid', None)
        info.append({
            'port': p.device,
            'description': desc,
            'hwid': hwid,
            'vid': f"0x{vid:04x}" if vid else "N/A",
            'pid': f"0x{pid:04x}" if pid else "N/A",
        })
    return info

print("=" * 80)
print("Live Port Monitor - Plug/Unplug devices to see detection")
print("=" * 80)
print()

last_ports = {}

try:
    while True:
        current_ports = get_port_info()
        
        current_dict = {p['port']: p for p in current_ports}
        
        # Check for new ports
        for port, info in current_dict.items():
            if port not in last_ports:
                print(f"\n[+] DEVICE CONNECTED: {port}")
                print(f"    Description: {info['description']}")
                print(f"    HWID: {info['hwid']}")
                print(f"    VID:PID: {info['vid']}:{info['pid']}")
                
                # Identify device type
                desc = info['description'].lower()
                hwid = info['hwid'].lower()
                if 'ch340' in desc or 'ch340' in hwid:
                    print(f"    Type: Likely Arduino Nano (CH340 chip)")
                elif 'cp210' in desc or 'cp210' in hwid:
                    print(f"    Type: Likely ESP32 with CP210x USB-UART bridge")
                elif 'esp32' in desc or 'esp32' in hwid:
                    print(f"    Type: ESP32-S3 (native USB)")
                elif 'ftdi' in desc or 'ftdi' in hwid:
                    print(f"    Type: Device with FTDI chip")
        
        # Check for removed ports
        for port in last_ports:
            if port not in current_dict:
                print(f"\n[-] DEVICE DISCONNECTED: {port}")
        
        last_ports = current_dict
        print(f"\n[{time.strftime('%H:%M:%S')}] Monitoring... (Found {len(current_ports)} ports)", end='\r')
        
        time.sleep(0.5)
        
except KeyboardInterrupt:
    print("\n\nExiting...")
