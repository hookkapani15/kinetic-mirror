# LED Control System

## Overview

Independent LED control system for 2048 WS2812B LEDs (32×64 matrix) via ESP32-S3. This system operates completely independently from the motor system.

## Quick Start

```bash
# Install dependencies
pip install -r ../requirements.txt

# Run LED GUI
python gui/led_gui.py
```

## Hardware

- **ESP32-S3 DevKit**
- **8× 16×16 WS2812B LED Panels** (2048 LEDs total)
- **GPIO 5**: Controls 1024 LEDs (left column)
- **GPIO 18**: Controls 1024 LEDs (right column)
- **Serial Communication**: 460800 baud

## System Architecture

```
leds/
├── gui/              # User interface
├── controllers/      # LED control logic
├── firmware/         # ESP32 firmware
├── simulation/       # Testing without hardware
├── tools/           # Utilities and debug tools
├── tests/           # Test suite
└── docs/            # Documentation
```

## Key Components

### LED Controller (`controllers/led_controller.py`)
- Renders body silhouette on LED matrix
- Handles hardware mapping (panel wiring)
- Packs data into ESP32-compatible packets

### LED GUI (`gui/led_gui.py`)
- Real-time body tracking with MediaPipe
- Visual preview and controls
- Connection management

### Firmware (`firmware/esp32/`)
- ESP32-S3 firmware for LED control
- Handles packet type 0x01 (LED data)
- FastLED library for WS2812B control

## Protocol

**Packet Format**: `[0xAA, 0xBB, 0x01, brightness_byte_0, ..., brightness_byte_2047]`

- Header: `0xAA 0xBB`
- Type: `0x01` (LED data)
- Data: 2048 bytes (one per LED, grayscale brightness)
- Total: 2051 bytes

## Mapping Modes

The LED controller supports multiple hardware mapping modes:

- **Mode 0**: RAW (no transformation)
- **Mode 1**: Row-based pin split
- **Mode 2**: Column-based pin split
- **Mode 3**: Column-based + serpentine (default)
- **Mode 4**: Full custom mapping
- **Mode 5**: Auto-calibrated (from calibration file)

## Usage

### Basic Usage
```python
from leds.controllers.led_controller import LEDController
from shared.io.serial_manager import SerialManager

# Initialize
led = LEDController(width=32, height=64, mapping_mode=3)
serial = SerialManager(port="COM8", baud=460800)

# Render frame from pose
frame = led.render_frame(pose_results, seg_mask)

# Send to ESP32
packet = led.pack_led_packet(frame)
serial.write(packet)
```

### GUI Usage
1. Connect ESP32 (select COM port)
2. Start camera tracking
3. LEDs will display body silhouette

## Configuration

- **Matrix Size**: 32×64 (2048 LEDs)
- **Panels**: 8 panels (2 columns × 4 rows)
- **Mapping Mode**: 3 (Column-based + serpentine)
- **Baud Rate**: 460800 (firmware default)

## Panel Layout

```
Physical Layout (2 columns × 4 rows):
┌─────┬─────┐
│  1  │  2  │  Row 0
├─────┼─────┤
│  3  │  4  │  Row 1
├─────┼─────┤
│  5  │  6  │  Row 2
├─────┼─────┤
│  7  │  8  │  Row 3
└─────┴─────┘

GPIO 5 (Left):  Panels 1, 3, 5, 7
GPIO 18 (Right): Panels 2, 4, 6, 8
```

## Troubleshooting

See `docs/troubleshooting.md` for common issues and solutions.

## Testing

```bash
# Run LED tests
python -m leds.tests.comprehensive_led_test
```

## Documentation

- **API Reference**: `docs/api.md`
- **Hardware Setup**: `docs/hardware.md`
- **Mapping Guide**: `docs/mapping.md`
- **Troubleshooting**: `docs/troubleshooting.md`
- **Firmware Guide**: `docs/firmware.md`

