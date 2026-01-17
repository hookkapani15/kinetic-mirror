# Motor Control System

## Overview

Independent motor control system for 32 servo motors via ESP32-S3. This system operates completely independently from the LED system.

## Quick Start

```bash
# Install dependencies
pip install -r ../requirements.txt

# Run motor GUI
python gui/motor_gui.py
```

## Hardware

- **ESP32-S3 DevKit**
- **2x PCA9685 PWM Drivers** (I2C addresses 0x40, 0x41)
- **32 Servo Motors** (16 per PCA9685)
- **Serial Communication**: 460800 baud

## System Architecture

```
motors/
├── gui/              # User interface
├── controllers/      # Motor control logic
├── firmware/         # ESP32 firmware
├── simulation/       # Testing without hardware
├── tools/           # Utilities and debug tools
├── tests/           # Test suite
└── docs/            # Documentation
```

## Key Components

### Motor Controller (`controllers/motor_controller.py`)
- Calculates servo angles from body pose
- Packs data into ESP32-compatible packets
- Handles 32 servos (0-180° range)

### Motor GUI (`gui/motor_gui.py`)
- Real-time body tracking with MediaPipe
- Visual feedback and controls
- Connection management

### Firmware (`firmware/esp32/`)
- ESP32-S3 firmware for motor control
- Handles packet type 0x02 (servo data)
- Smooth servo movement with exponential smoothing

## Protocol

**Packet Format**: `[0xAA, 0xBB, 0x02, servo1_hi, servo1_lo, ..., servo32_hi, servo32_lo]`

- Header: `0xAA 0xBB`
- Type: `0x02` (servo/motor data)
- Data: 64 bytes (32 servos × 2 bytes each)
- Total: 67 bytes

**Angle Mapping**: 0-180° → 0-1000 → 2 bytes (big-endian)

## Usage

### Basic Usage
```python
from motors.controllers.motor_controller import MotorController
from shared.io.serial_manager import SerialManager

# Initialize
motor = MotorController(num_servos=32)
serial = SerialManager(port="COM8", baud=460800)

# Calculate angles from pose
angles = motor.calculate_angles(pose_results)

# Send to ESP32
packet = motor.pack_servo_packet(angles)
serial.write(packet)
```

### GUI Usage
1. Connect ESP32 (select COM port)
2. Start camera tracking
3. Motors will follow body position

## Configuration

- **Number of Servos**: 32 (default, can be changed in controller)
- **Angle Range**: 0-180° (hardware limit)
- **Baud Rate**: 460800 (firmware default)
- **Smoothing**: Exponential smoothing (alpha=0.3 in firmware)

## Troubleshooting

See `docs/troubleshooting.md` for common issues and solutions.

## Testing

```bash
# Run motor tests
python -m motors.tests.comprehensive_motor_test
```

## Documentation

- **API Reference**: `docs/api.md`
- **Hardware Setup**: `docs/hardware.md`
- **Troubleshooting**: `docs/troubleshooting.md`
- **Firmware Guide**: `docs/firmware.md`

