# ESP32 Firmware Testing & Optimization

## Overview
This directory contains ESP32-S3 firmware with comprehensive testing, power monitoring, and performance optimizations.

## Files

### Firmware Source
- `firmware/esp32/tests/unit_tests.cpp` - Unity test framework for ESP32
- `firmware/esp32/include/led_controller.h` - LED controller header
- `firmware/esp32/include/motor_controller.h` - Motor controller header
- `firmware/esp32/include/serial_protocol.h` - Serial protocol header
- `firmware/esp32/include/power_monitor.h` - Power monitoring
- `firmware/esp32/include/brightness_optimizer.h` - Adaptive brightness

### Test Tools
- `tools/test_esp32.py` - Automated Python test script

## Running Tests

### 1. Unit Tests on ESP32
```bash
# Install PlatformIO
pip install platformio

# Run unit tests
pio test -e esp32s3_test --upload-port COM3
```

### 2. Automated Python Tests
```bash
# Run all tests
python tools/test_esp32.py --port COM3

# Run specific tests
python tools/test_esp32.py --port COM3 --led       # LED tests
python tools/test_esp32.py --port COM3 --motor     # Motor tests
python tools/test_esp32.py --port COM3 --power     # Power tests
```

## Optimizations (Reversible)

Edit `firmware/esp32/src/main.cpp` to enable/disable optimizations:

```cpp
// Uncomment to ENABLE:
#define USE_MULTI_THREADING     // Multi-threading (3x faster)
#define USE_DMA_LEDS            // DMA for LEDs (10x faster)
#define USE_OPTIMIZED_SERIAL    // Compressed serial (10x less data)
#define USE_POWER_MONITORING    // Power monitoring
#define USE_BRIGHTNESS_OPT      // Adaptive brightness

// Comment out to DISABLE (revert to original)
```

## Power Monitoring
- ADC-based real-time power measurement
- Separate monitoring for LEDs, motors, and ESP32
- Historical averaging for stable readings
- Print stats every 5 seconds

## Test Coverage
- LED Controller: 8 tests (init, set pixel, fill, clear, brightness, gradient, bounds, performance)
- Motor Controller: 5 tests (init, set angle, limits, all servos, calibration)
- Serial Protocol: 3 tests (LED command, motor command, invalid command)

## Expected Results
```
Test Summary:
  Total:   16
  Passed:  16/16 (100%)
  Failed:  0/16 (0%)
  Skipped: 0/16 (0%)
```

## Power Monitoring Output
```
POWER STATISTICS:
  LEDs:    15.23 W (avg of last 10 samples)
  Motors:  30.45 W (avg of last 10 samples)
  ESP32:   1.50 W (avg of last 10 samples)
  TOTAL:   47.18 W
```

## Next Steps
1. Upload firmware to ESP32
2. Connect hardware
3. Run tests with: `python tools/test_esp32.py --port COM3`
4. Verify all 16 tests pass
5. Test power monitoring with real hardware
