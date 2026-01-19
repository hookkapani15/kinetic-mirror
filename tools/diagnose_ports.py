#!/usr/bin/env python3
"""
Deep COM Port Diagnostic Tool
Helps identify exactly what's happening with serial port detection
"""
import serial.tools.list_ports
import time
import sys

def get_detailed_port_info():
    """Get all available info about each port"""
    ports = []
    for p in serial.tools.list_ports.comports():
        info = {
            'device': p.device,
            'name': p.name if hasattr(p, 'name') else None,
            'description': p.description,
            'hwid': p.hwid,
            'vid': p.vid,  # Vendor ID
            'pid': p.pid,  # Product ID
            'serial_number': p.serial_number,
            'location': p.location if hasattr(p, 'location') else None,
            'manufacturer': p.manufacturer,
            'product': p.product,
            'interface': p.interface if hasattr(p, 'interface') else None,
        }
        ports.append(info)
    return ports

def identify_port_type(port_info):
    """Try to identify what type of device this is"""
    desc = (port_info['description'] or '').lower()
    hwid = (port_info['hwid'] or '').lower()
    manufacturer = (port_info['manufacturer'] or '').lower()
    
    # Check HWID patterns
    if 'bthenum' in hwid:
        return "BLUETOOTH_VIRTUAL", "Windows Bluetooth virtual port (persists even when device disconnected)"
    
    if 'usb' in hwid or 'vid_' in hwid:
        # USB device - check what type
        vid = port_info['vid']
        pid = port_info['pid']
        
        # Known USB-Serial chips
        known_chips = {
            (0x10C4, None): "Silicon Labs CP210x (common ESP32 USB-UART)",
            (0x1A86, 0x7523): "CH340 (common Arduino Nano/clone)",
            (0x1A86, 0x55D4): "CH9102 (newer USB-UART chip)",
            (0x0403, None): "FTDI (high-quality USB-UART)",
            (0x303A, 0x1001): "ESP32-S3 Native USB (CDC)",
            (0x303A, None): "Espressif device (ESP32 family)",
            (0x2341, None): "Arduino official",
            (0x239A, None): "Adafruit",
            (0x1B4F, None): "SparkFun",
        }
        
        for (known_vid, known_pid), chip_name in known_chips.items():
            if vid == known_vid:
                if known_pid is None or pid == known_pid:
                    return "USB_SERIAL", chip_name
        
        return "USB_UNKNOWN", f"USB device VID:0x{vid:04X} PID:0x{pid:04X}" if vid else "USB device (unknown)"
    
    # Check description patterns
    if 'bluetooth' in desc:
        return "BLUETOOTH_VIRTUAL", "Bluetooth virtual port"
    if 'ch340' in desc:
        return "USB_SERIAL", "CH340 USB-UART"
    if 'cp210' in desc:
        return "USB_SERIAL", "CP210x USB-UART"
    if 'ftdi' in desc:
        return "USB_SERIAL", "FTDI USB-UART"
    if 'usb' in desc:
        return "USB_SERIAL", "USB Serial device"
        
    return "UNKNOWN", "Unknown device type"

def print_port_details(port_info, port_type, type_desc):
    """Print detailed port information"""
    print(f"\n  [{port_info['device']}]")
    print(f"    Type: {port_type} - {type_desc}")
    print(f"    Description: {port_info['description']}")
    if port_info['vid'] and port_info['pid']:
        print(f"    VID:PID: 0x{port_info['vid']:04X}:0x{port_info['pid']:04X}")
    if port_info['manufacturer']:
        print(f"    Manufacturer: {port_info['manufacturer']}")
    if port_info['product']:
        print(f"    Product: {port_info['product']}")
    if port_info['serial_number']:
        print(f"    Serial: {port_info['serial_number']}")
    print(f"    HWID: {port_info['hwid']}")

def main():
    print("=" * 70)
    print("COM Port Diagnostic Tool")
    print("=" * 70)
    print()
    print("This tool will monitor COM ports and show exactly what Windows sees.")
    print("Please plug/unplug your devices to see what gets detected.")
    print()
    print("Press Ctrl+C to exit")
    print()
    
    last_ports = {}
    
    try:
        while True:
            current_ports = get_detailed_port_info()
            current_dict = {p['device']: p for p in current_ports}
            
            # Check for new ports
            for device, info in current_dict.items():
                if device not in last_ports:
                    port_type, type_desc = identify_port_type(info)
                    print(f"\n[+] NEW PORT DETECTED: {device}")
                    print_port_details(info, port_type, type_desc)
                    
                    if port_type == "BLUETOOTH_VIRTUAL":
                        print(f"\n    [!] This is a BLUETOOTH virtual port!")
                        print(f"    [!] It will persist even when device is unplugged.")
                        print(f"    [!] Your ESP32 is probably on a DIFFERENT port.")
                    elif port_type == "USB_SERIAL":
                        print(f"\n    [OK] This looks like a real USB serial device!")
                        print(f"    [OK] This is likely your ESP32/Arduino.")
            
            # Check for removed ports
            for device in last_ports:
                if device not in current_dict:
                    port_type, type_desc = identify_port_type(last_ports[device])
                    print(f"\n[-] PORT REMOVED: {device}")
                    print(f"    Was: {type_desc}")
            
            last_ports = current_dict
            
            # Status line
            usb_ports = [d for d, i in current_dict.items() 
                        if identify_port_type(i)[0] in ("USB_SERIAL", "USB_UNKNOWN")]
            bt_ports = [d for d, i in current_dict.items() 
                       if identify_port_type(i)[0] == "BLUETOOTH_VIRTUAL"]
            
            status = f"[{time.strftime('%H:%M:%S')}] USB: {usb_ports if usb_ports else 'None'} | Bluetooth: {len(bt_ports)} virtual ports"
            print(f"\r{status}", end="", flush=True)
            
            time.sleep(0.5)
            
    except KeyboardInterrupt:
        print("\n\nExiting...")
        
        # Print summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        
        ports = get_detailed_port_info()
        usb_ports = []
        bt_ports = []
        
        for p in ports:
            port_type, type_desc = identify_port_type(p)
            if port_type == "BLUETOOTH_VIRTUAL":
                bt_ports.append(p['device'])
            elif port_type in ("USB_SERIAL", "USB_UNKNOWN"):
                usb_ports.append((p['device'], type_desc))
        
        print(f"\nBluetooth virtual ports (can be ignored): {bt_ports}")
        print(f"USB Serial ports (your devices): {usb_ports if usb_ports else 'None detected'}")
        
        if not usb_ports:
            print("\n[!] No USB serial devices detected!")
            print("   Possible causes:")
            print("   1. Device not plugged in")
            print("   2. Bad USB cable (try a different one)")
            print("   3. Missing driver (check Device Manager)")
            print("   4. Device in wrong mode (try holding BOOT button while plugging in)")

if __name__ == "__main__":
    main()
