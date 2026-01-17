# Mirror Body Project - Structure Documentation

## 📁 Project Organization

This project is organized into **separate, independent systems** for Motors and LEDs. Each system can run independently without the other.

```
mirror-with-tests/
├── motors/                    # MOTOR SYSTEM (Independent)
│   ├── gui/                    # Motor GUI application
│   │   ├── motor_gui.py        # Main motor control GUI
│   │   └── __init__.py
│   ├── controllers/            # Motor control logic
│   │   ├── motor_controller.py # Servo angle calculations
│   │   └── __init__.py
│   ├── firmware/               # ESP32 motor firmware
│   │   └── esp32/
│   ├── simulation/             # Motor simulation/visualization
│   │   └── motor_sim.py
│   ├── tools/                  # Motor-specific utilities
│   ├── tests/                  # Motor tests
│   ├── docs/                   # Motor documentation
│   └── README.md               # Motor system guide
│
├── leds/                       # LED SYSTEM (Independent)
│   ├── gui/                    # LED GUI application
│   │   ├── led_gui.py          # Main LED control GUI
│   │   └── __init__.py
│   ├── controllers/            # LED control logic
│   │   ├── led_controller.py   # LED matrix rendering
│   │   └── __init__.py
│   ├── firmware/               # ESP32 LED firmware
│   │   └── esp32/
│   ├── simulation/             # LED simulation/visualization
│   │   └── led_sim.py
│   ├── tools/                  # LED-specific utilities
│   ├── tests/                  # LED tests
│   ├── docs/                   # LED documentation
│   └── README.md               # LED system guide
│
├── shared/                     # SHARED UTILITIES
│   ├── io/                     # Serial communication
│   │   ├── serial_manager.py  # Threaded serial I/O
│   │   └── mock_serial.py     # Simulation serial
│   ├── simulation/             # Shared simulation code
│   │   └── virtual_esp32.py   # Virtual ESP32 for testing
│   └── README.md               # Shared utilities guide
│
├── docs/                       # PROJECT DOCUMENTATION
│   ├── motors/                 # Motor system docs
│   ├── leds/                   # LED system docs
│   ├── shared/                 # Shared utilities docs
│   └── PROJECT_STRUCTURE.md    # This file
│
├── main.py                     # Legacy entry point (deprecated)
├── README.md                   # Main project README
└── requirements.txt            # Python dependencies
```

## 🎯 System Independence

### Motors System
- **Entry Point**: `motors/gui/motor_gui.py`
- **Purpose**: Control 32 servo motors via ESP32
- **Hardware**: ESP32-S3 + 2x PCA9685 (32 servos)
- **Protocol**: Serial @ 460800 baud, Packet type 0x02
- **Can run independently**: ✅ Yes

### LEDs System  
- **Entry Point**: `leds/gui/led_gui.py`
- **Purpose**: Control 2048 LED matrix via ESP32
- **Hardware**: ESP32-S3 + WS2812B panels (32x64)
- **Protocol**: Serial @ 460800 baud, Packet type 0x01
- **Can run independently**: ✅ Yes

### Shared Utilities
- **Purpose**: Common code used by both systems
- **Usage**: Imported by motors/ and leds/ systems
- **Examples**: Serial communication, mock hardware, utilities

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
# Terminal 1
cd motors/gui
python motor_gui.py

# Terminal 2
cd leds/gui
python led_gui.py
```

## 📝 Development Guidelines

### For AI Assistants
1. **Always check which system you're working on** (motors/ or leds/)
2. **Don't mix motor and LED code** - keep them separate
3. **Use shared/ utilities** for common functionality
4. **Update documentation** when making changes
5. **Test each system independently** before integration

### For Developers
1. **One system per folder** - motors/ and leds/ are independent
2. **Shared code goes in shared/** - don't duplicate
3. **Documentation in docs/** - system-specific docs in respective folders
4. **Tests in tests/** - each system has its own test suite
5. **Firmware in firmware/** - separate ESP32 code for each system

## 🔧 Import Paths

### From Motors System
```python
from motors.controllers.motor_controller import MotorController
from shared.io.serial_manager import SerialManager
```

### From LEDs System
```python
from leds.controllers.led_controller import LEDController
from shared.io.serial_manager import SerialManager
```

## 📚 Documentation Structure

- **System READMEs**: `motors/README.md`, `leds/README.md`
- **API Docs**: `docs/motors/`, `docs/leds/`
- **Hardware Guides**: In respective `docs/` folders
- **Troubleshooting**: In respective `docs/` folders

## ⚠️ Important Notes

1. **No cross-dependencies**: Motors code should NOT import from leds/ and vice versa
2. **Shared utilities only**: Both systems can use shared/ utilities
3. **Separate GUIs**: Each system has its own GUI - don't combine them
4. **Independent testing**: Test motors and LEDs separately
5. **Clear separation**: If unsure where code belongs, ask or check docs

## 🎨 Architecture Benefits

- ✅ **Clear separation** - Easy to understand what belongs where
- ✅ **Independent development** - Work on motors without affecting LEDs
- ✅ **Easy debugging** - Problems isolated to one system
- ✅ **Better testing** - Test each system independently
- ✅ **AI-friendly** - Clear structure helps AI understand context
- ✅ **Scalable** - Easy to add new systems (e.g., audio/, sensors/)

