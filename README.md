# Mirror Body Simulation

A full-body LED and motor simulation system for interactive art installations.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the simulation
python main.py
```

## Features

- **LED Body Tracking**: Full human silhouette displayed on 16x16 LED panels.
- **Motor Wave Effect**: 64 motors respond to body position.
- **Real-time AI Vision**: MediaPipe-powered pose and segmentation.
- **Simulation Mode**: Test without hardware using built-in visualizer.

## Controls

| Key | Action |
|-----|--------|
| `q` | Quit |
| `m` | Reset / Menu |

## Modes

- **LED Only**: Display body silhouette (Default).
- **Motor Only**: Wave effect from body center.
- **Both**: Full system simulation.

## Project Structure

```
mirror-prod/
├── main.py              # Entry point
├── led_control_gui.py   # Main application
├── apps/                # Application modules
│   ├── gui/             # GUI components
│   └── simulation/      # Simulation visualizer
├── packages/            # Core libraries
│   └── mirror_core/     # Controllers, IO, Simulation
├── firmware/            # ESP32 firmware
├── tools/               # Utilities & debug scripts
└── tests/               # Test suites
```

## Hardware

- **ESP32-S3** with dual GPIO pins for WS2812B LEDs.
- **64 Servo Motors** for mechanical movement.
- **8x 16x16 LED Panels** (2048 LEDs total).

## License

MIT
