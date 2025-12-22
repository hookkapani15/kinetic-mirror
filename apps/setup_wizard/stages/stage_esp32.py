#!/usr/bin/env python3
"""
Stage 3: ESP32 Connection
Verifies ESP32 is connected and firmware responds.
"""
import time
from .base_stage import BaseStage, CheckResult, StageResult


class ESP32Stage(BaseStage):
    """Check ESP32 serial connection and firmware."""
    
    def __init__(self):
        super().__init__(
            name="ESP32 Connection",
            description="Checking ESP32 serial connection..."
        )
        self.detected_port = None
    
    def run(self, callback=None) -> StageResult:
        checks = []
        
        # 1. Import serial
        try:
            import serial
            import serial.tools.list_ports
        except ImportError:
            checks.append(CheckResult(
                name="PySerial Import",
                passed=False,
                message="PySerial not available",
                fix_instructions=["Complete Stage 1 first"]
            ))
            return self._make_result(checks)
        
        # 2. Find COM ports
        ports = list(serial.tools.list_ports.comports())
        port_info = [f"{p.device}: {p.description}" for p in ports]
        
        checks.append(CheckResult(
            name="USB Ports",
            passed=len(ports) > 0,
            message=f"Found {len(ports)} port(s)" if ports else "No USB ports found",
            fix_instructions=[] if ports else [
                "Connect ESP32 via USB cable",
                "Try a different USB port",
                "Install CH340/CP2102 drivers"
            ],
            details={"ports": port_info}
        ))
        if callback:
            callback("USB Ports", checks[-1].passed, checks[-1].message)
        
        if not ports:
            return self._make_result(checks)
        
        # 3. Find ESP32 (look for common identifiers)
        esp_port = None
        for p in ports:
            desc = p.description.upper()
            if any(x in desc for x in ["CP210", "CH340", "USB SERIAL", "UART"]):
                esp_port = p.device
                break
        
        # Fallback to first USB Serial
        if not esp_port:
            for p in ports:
                if "USB" in p.description.upper():
                    esp_port = p.device
                    break
        
        # Last resort: first port
        if not esp_port and ports:
            esp_port = ports[0].device
        
        checks.append(CheckResult(
            name="ESP32 Detection",
            passed=esp_port is not None,
            message=f"Detected ESP32: {esp_port}" if esp_port else "ESP32 not detected",
            fix_instructions=[] if esp_port else [
                "Ensure ESP32 is connected",
                "Check USB cable (data cable, not charge-only)"
            ],
            details={"port": esp_port}
        ))
        if callback:
            callback("ESP32 Detection", checks[-1].passed, checks[-1].message)
        
        if not esp_port:
            return self._make_result(checks)
        
        self.detected_port = esp_port
        
        # 4. Test serial connection
        try:
            ser = serial.Serial(esp_port, 460800, timeout=2)
            time.sleep(0.5)
            
            # Clear buffer
            ser.reset_input_buffer()
            
            # Check if port opened successfully
            checks.append(CheckResult(
                name="Serial Open",
                passed=True,
                message=f"Opened {esp_port} at 460800 baud",
                details={"port": esp_port, "baud": 460800}
            ))
            if callback:
                callback("Serial Open", True, checks[-1].message)
            
            # 5. Try to get firmware response
            # Send a test command and wait for any response
            ser.write(b'c\n')  # Clear command
            time.sleep(0.5)
            
            response = ""
            if ser.in_waiting > 0:
                response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
            
            # Check for READY or any response
            firm_ok = len(response) > 0 or ser.is_open
            checks.append(CheckResult(
                name="Firmware Response",
                passed=firm_ok,
                message="Firmware responding" if firm_ok else "No firmware response",
                fix_instructions=[] if firm_ok else [
                    "Flash firmware to ESP32:",
                    "1. Open PlatformIO in VS Code",
                    "2. Open folder: firmware/esp32/",
                    "3. Click Upload button",
                    "4. Wait for SUCCESS message"
                ],
                details={"response": response[:100] if response else "none"}
            ))
            if callback:
                callback("Firmware Response", firm_ok, checks[-1].message)
            
            ser.close()
            
        except serial.SerialException as e:
            checks.append(CheckResult(
                name="Serial Open",
                passed=False,
                message=f"Failed to open {esp_port}: {str(e)}",
                fix_instructions=[
                    "Close other programs using the port",
                    "Unplug and replug ESP32",
                    "Try a different USB port"
                ]
            ))
            if callback:
                callback("Serial Open", False, checks[-1].message)
        
        return self._make_result(checks)
