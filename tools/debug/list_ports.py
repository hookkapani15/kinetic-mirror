import serial.tools.list_ports

print("Available COM ports:")
ports = serial.tools.list_ports.comports()
for port in ports:
    print(f"- {port.device}: {port.description}")

input("Press Enter to exit...")
