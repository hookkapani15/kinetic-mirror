# AI Assistant Guide - Mirror Body Project

## 🎯 Purpose

This document helps AI assistants understand the project structure and work effectively with the codebase.

## 📁 Project Organization

The project is **strictly separated** into independent systems:

```
mirror-with-tests/
├── motors/          # MOTOR SYSTEM (Independent)
│   ├── gui/         # Motor GUI - ONLY motor code
│   ├── controllers/ # Motor logic - ONLY motor code
│   └── firmware/    # Motor firmware
│
├── leds/            # LED SYSTEM (Independent)
│   ├── gui/         # LED GUI - ONLY LED code
│   ├── controllers/ # LED logic - ONLY LED code
│   └── firmware/    # LED firmware
│
└── shared/          # SHARED CODE (Used by both)
    ├── io/          # Serial communication
    └── simulation/  # Simulation utilities
```

## ⚠️ Critical Rules

### 1. **NO CROSS-DEPENDENCIES**
- ❌ **NEVER** import from `leds/` in `motors/` code
- ❌ **NEVER** import from `motors/` in `leds/` code
- ✅ **ONLY** import from `shared/` in both systems

### 2. **System Independence**
- Motors and LEDs are **completely separate**
- Each has its own GUI, controller, and firmware
- They can run on different computers or processes

### 3. **File Locations**
- Motor code → `motors/` folder
- LED code → `leds/` folder
- Common code → `shared/` folder
- Documentation → `docs/` folder

## 🔍 How to Find Code

### Motor-Related Code
- **GUI**: `motors/gui/motor_gui.py`
- **Controller**: `motors/controllers/motor_controller.py`
- **Firmware**: `motors/firmware/esp32/`
- **Tests**: `motors/tests/`

### LED-Related Code
- **GUI**: `leds/gui/led_gui.py`
- **Controller**: `leds/controllers/led_controller.py`
- **Firmware**: `leds/firmware/esp32/`
- **Tests**: `leds/tests/`

### Shared Code
- **Serial**: `shared/io/serial_manager.py`
- **Mock Serial**: `shared/io/mock_serial.py`
- **Simulation**: `shared/simulation/virtual_esp32.py`

## 📝 Import Patterns

### From Motor Code
```python
# ✅ CORRECT
from motors.controllers.motor_controller import MotorController
from shared.io.serial_manager import SerialManager

# ❌ WRONG
from leds.controllers.led_controller import LEDController  # NO!
```

### From LED Code
```python
# ✅ CORRECT
from leds.controllers.led_controller import LEDController
from shared.io.serial_manager import SerialManager

# ❌ WRONG
from motors.controllers.motor_controller import MotorController  # NO!
```

## 🛠️ Common Tasks

### Adding Motor Feature
1. Check if code belongs in `motors/` folder
2. Use `shared/` utilities if needed
3. **Never** import from `leds/`
4. Update `motors/README.md` if needed

### Adding LED Feature
1. Check if code belongs in `leds/` folder
2. Use `shared/` utilities if needed
3. **Never** import from `motors/`
4. Update `leds/README.md` if needed

### Adding Shared Feature
1. Code must be used by **both** motors and LEDs
2. Place in `shared/` folder
3. Keep it generic (no system-specific code)
4. Update `shared/README.md`

## 🐛 Debugging Tips

### Motor Issues
- Check `motors/gui/motor_gui.py` for GUI problems
- Check `motors/controllers/motor_controller.py` for logic problems
- Check `motors/firmware/` for firmware problems
- **Don't** look in `leds/` folder

### LED Issues
- Check `leds/gui/led_gui.py` for GUI problems
- Check `leds/controllers/led_controller.py` for logic problems
- Check `leds/firmware/` for firmware problems
- **Don't** look in `motors/` folder

### Shared Issues
- Check `shared/io/` for serial problems
- Check `shared/simulation/` for simulation problems

## 📚 Documentation Files

- **Project Structure**: `PROJECT_STRUCTURE.md`
- **Motor System**: `motors/README.md`
- **LED System**: `leds/README.md`
- **Shared Utilities**: `shared/README.md`
- **This Guide**: `docs/AI_GUIDE.md`

## ✅ Checklist Before Making Changes

- [ ] Identified which system (motors/leds/shared) the change belongs to
- [ ] Verified no cross-dependencies (motors ↔ leds)
- [ ] Updated relevant documentation
- [ ] Tested the change independently
- [ ] Followed import patterns correctly

## 🎓 Key Concepts

1. **Separation**: Motors and LEDs are separate systems
2. **Independence**: Each system can run alone
3. **Shared Code**: Only truly common code goes in `shared/`
4. **Documentation**: Always update docs when making changes
5. **Testing**: Test each system independently

## 💡 Examples

### ✅ Good: Motor Feature
```python
# File: motors/gui/motor_gui.py
from motors.controllers.motor_controller import MotorController
from shared.io.serial_manager import SerialManager
```

### ❌ Bad: Mixing Systems
```python
# File: motors/gui/motor_gui.py
from leds.controllers.led_controller import LEDController  # WRONG!
```

### ✅ Good: Shared Utility
```python
# File: shared/io/serial_manager.py
# Generic serial code used by both motors and LEDs
```

## 🚨 Red Flags

If you see these, something is wrong:
- Import from `leds/` in `motors/` code
- Import from `motors/` in `leds/` code
- System-specific code in `shared/`
- Combined motor+LED GUI (should be separate)

## 📞 Need Help?

1. Check `PROJECT_STRUCTURE.md` for architecture
2. Check system-specific READMEs for details
3. Review this guide for patterns
4. When in doubt, keep systems separate!

