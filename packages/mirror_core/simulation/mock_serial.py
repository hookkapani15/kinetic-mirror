
"""
Mock Serial Interface
Mimics serial.Serial for the Virtual ESP32
"""

import time
from .virtual_esp32 import VirtualESP32

# Global singleton to share state between the "serial port" and the visualizer
# This is necessary because SerialManager instantiates the class, but the Visualizer needs to peek inside.
_VIRTUAL_DEVICE = None

def get_virtual_device_instance():
    global _VIRTUAL_DEVICE
    if _VIRTUAL_DEVICE is None:
        _VIRTUAL_DEVICE = VirtualESP32()
    return _VIRTUAL_DEVICE

class MockSerial:
    def __init__(self, port, baudrate, timeout=1, write_timeout=0.1, **kwargs):
        self.port = port
        self.baudrate = baudrate
        self.is_open = True
        self.timeout = timeout
        self.device = get_virtual_device_instance()
        
        # Simulate connection time
        time.sleep(0.1)
        print(f"[MOCK] Connected to Virtual ESP32 on {port}")

    def write(self, data):
        if not self.is_open:
            raise OSError("Port is closed")
        self.device.write(data)
        return len(data)

    def read(self, size=1):
        if not self.is_open:
            raise OSError("Port is closed")
        # Simple non-blocking read simulation
        # In real serial, this would block potentially.
        # Here we just peek if there is data
        data = b''
        start_time = time.time()
        
        while len(data) < size:
            chunk = self.device.read()
            if chunk:
                data += chunk
            else:
                # If timeout passed, break
                if self.timeout and (time.time() - start_time > self.timeout):
                    break
                time.sleep(0.01)
                
        return data

    def readline(self):
        return self.read(100) # Simplified for simulated "READY" message

    @property
    def in_waiting(self):
        return not self.device.output_queue.empty()

    def close(self):
        self.is_open = False
        print("[MOCK] Serial closed")

    def open(self):
        self.is_open = True
        print("[MOCK] Serial opened")

    def reset_input_buffer(self):
        pass

    def reset_output_buffer(self):
        pass
        
    # Dummy properties for dtr/rts
    @property
    def dtr(self): return False
    @dtr.setter
    def dtr(self, value): pass
    
    @property
    def rts(self): return False
    @rts.setter
    def rts(self, value): pass
