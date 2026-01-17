# Mirror Body Project

A full-body LED and motor simulation system for interactive art installations.

## 🎯 Project Structure

This project is **organized into separate, independent systems**:

- **`motors/`** - Motor control system (32 servos)
- **`leds/`** - LED control system (2048 LEDs)
- **`shared/`** - Shared utilities (serial, simulation)

Each system can run **independently** without the other.

## 🚀 Quick Start

### Run Motors Only
```bash
cd motors/gui
python motor_gui.py
```

### Run LEDs Only
```bash
cd leds/gui
python led_gui.py
```

### Run Both (Separate Processes)
```bash
# Terminal 1 - Motors
cd motors/gui
python motor_gui.py

# Terminal 2 - LEDs
cd leds/gui
python led_gui.py
```

## 📁 Project Organization

```
mirror-with-tests/
├── motors/          # Motor control system (independent)
│   ├── gui/         # Motor GUI application
│   ├── controllers/ # Motor control logic
│   ├── firmware/    # ESP32 motor firmware
│   └── README.md    # Motor system guide
│
├── leds/            # LED control system (independent)
│   ├── gui/         # LED GUI application
│   ├── controllers/ # LED control logic
│   ├── firmware/    # ESP32 LED firmware
│   └── README.md    # LED system guide
│
├── shared/          # Shared utilities
│   ├── io/          # Serial communication
│   └── simulation/  # Simulation code
│
└── docs/            # Project documentation
```

## 📚 Documentation

- **Project Structure**: See `PROJECT_STRUCTURE.md`
- **Motor System**: See `motors/README.md`
- **LED System**: See `leds/README.md`
- **Shared Utilities**: See `shared/README.md`

## 🔧 Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

## ⚠️ Important Notes

1. **Systems are independent** - Motors and LEDs run separately
2. **No cross-dependencies** - Motors code doesn't import from leds/ and vice versa
3. **Shared utilities only** - Both systems use `shared/` utilities
4. **Separate GUIs** - Each system has its own GUI application

## 🎨 Features

### Motor System
- 32 servo motors via ESP32-S3
- Real-time body tracking
- Wave effect from body position

### LED System
- 2048 WS2812B LEDs (32×64 matrix)
- Body silhouette visualization
- Multiple hardware mapping modes

## 📖 For AI Assistants

When working on this project:
1. **Check which system** you're working on (motors/ or leds/)
2. **Don't mix code** - keep motors and LEDs separate
3. **Use shared/ utilities** for common functionality
4. **Update documentation** when making changes
5. **Test each system independently**

See `PROJECT_STRUCTURE.md` for detailed architecture and guidelines.

## License

MIT
