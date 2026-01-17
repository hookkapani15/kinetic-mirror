# Shared Utilities

## Overview

Common utilities and code shared between the Motors and LEDs systems. These modules are designed to be imported by both systems without creating dependencies between them.

## Structure

```
shared/
├── io/                  # Input/Output utilities
│   ├── serial_manager.py    # Threaded serial communication
│   └── mock_serial.py       # Mock serial for testing
├── simulation/          # Simulation utilities
│   └── virtual_esp32.py     # Virtual ESP32 for testing
└── README.md            # This file
```

## Usage

### Serial Manager

Threaded serial communication for ESP32:

```python
from shared.io.serial_manager import SerialManager

# Initialize
serial = SerialManager(port="COM8", baud=460800)
serial.start()

# Write data
serial.write(b"Hello ESP32")

# Read data (non-blocking)
data = serial.read()

# Cleanup
serial.stop()
```

### Mock Serial

For testing without hardware:

```python
from shared.io.mock_serial import MockSerial

# Initialize
mock = MockSerial(port="SIMULATOR", baud=460800)

# Use like real serial
mock.write(b"test")
data = mock.read()
```

### Virtual ESP32

Simulate ESP32 behavior:

```python
from shared.simulation.virtual_esp32 import VirtualESP32

# Initialize
esp32 = VirtualESP32()

# Process packets
esp32.process_packet(packet)
```

## Guidelines

1. **No system-specific code** - Shared code should work for both motors and LEDs
2. **Generic interfaces** - Use abstract interfaces, not concrete implementations
3. **Well-documented** - All shared code must have clear documentation
4. **Tested** - Shared code should have comprehensive tests
5. **Backward compatible** - Changes should not break existing code

## Adding New Shared Code

1. Determine if code is truly shared (used by both systems)
2. Place in appropriate subfolder (`io/`, `simulation/`, etc.)
3. Add comprehensive documentation
4. Write tests
5. Update this README

## Dependencies

Shared utilities should have minimal dependencies:
- Standard library preferred
- Common packages only (numpy, serial, etc.)
- No system-specific imports

