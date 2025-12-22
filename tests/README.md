# Mirror Project Test System

## Quick Start

### Run Tests from Natural Language

```bash
# Simple issue description
python tooling/run_tests.py motors not moving

# More complex queries
python tooling/run_tests.py "LEDs not displaying silhouette in mode B"
python tooling/run_tests.py "ESP32 not connecting"

# Interactive mode
python tooling/run_tests.py
```

### Run Specific Test Files

```bash
python tooling/run_tests.py --files tests/hardware/esp/01_connection_test.py
```

---

## How It Works

### 1. Natural Language Routing

The NLP router understands plain English like:
- "motors are not moving" → Runs motor test suite
- "LEDs not updating" → Runs LED test suite  
- "human not detected" → Runs detection test suite
- "everything broken in mode B" → Runs full system tests

### 2. Firmware-First Rule

Before running hardware tests, the system reminds you to:
1. Flash correct firmware for the active mode (M/L/B)
2. Verify ESP32 connection
3. Then run diagnostic tests

### 3. Progressive Test Ordering

Tests always run in this order:
1. **Connection** - Is ESP32 connected?
2. **Power** - Is hardware powered?
3. **Communication** - Can we talk to ESP32?
4. **Unit Tests** - Do individual components work?
5. **Integration** - Does the full system work?

If early tests fail, later tests are skipped to save time.

### 4. JSON Output Standard

Every test returns structured results:
```json
{
  "test_name": "ESP32 Connection Test",
  "status": "pass|fail|skipped",
  "details": "ESP32 connected on COM3",
  "metrics": {"port": "COM3", "baud": 460800},
  "learns": {"last_good_port": "COM3"},
  "suggested_actions": [],
  "confidence": 1.0
}
```

### 5. Learning System

The system gets smarter over time by remembering:
- Last working COM port
- Optimal baud rate
- Successful configurations

Stored in `/settings/test_learns.json`

---

## Test Structure

```
/tests
  /hardware
    /esp
      01_connection_test.py     # ESP32 serial connection
      10_wifi_test.py          # WiFi connectivity (TODO)
      20_motor_driver_test.py  # Motor PWM signals (TODO)
  /gui
    01_startup_test.py         # GUI initialization (TODO)
    10_led_render_test.py      # LED rendering (TODO)
  /runtime
    01_cpu_sanity.py           # CPU usage check (TODO)

/tooling
  base_test.py                 # Base test class
  nlp_router.py                # Natural language router
  run_tests.py                 # Main test runner
```

---

## Writing New Tests

Create a new test by inheriting from `BaseTest`:

```python
from tooling.base_test import BaseTest

class MyTest(BaseTest):
    def __init__(self):
        super().__init__("My Test Name")
    
    def run(self):
        # Your test logic here
        if something_is_wrong:
            return self.fail_test(
                "Thing is broken",
                suggested_actions=["Fix the thing", "Try rebooting"],
                confidence=0.8
            )
        
        return self.pass_test(
            "Everything works!",
            learns={"last_good_value": 42},
            confidence=1.0
        )
```

---

## Examples

### Example 1: Check ESP32 Connection
```bash
python tooling/run_tests.py ESP32 not connecting
```

Output:
```
🔍 Interpreting query: "ESP32 not connecting"
✓ Detected 1 subsystem(s): connection
✓ Confidence: 90%

🧪 Running 1 test(s)...

Running: ESP32 Connection Test... ✓ PASS

======================================================================
TEST SUITE: NLP Query: ESP32 not connecting
======================================================================
Total: 1 | Passed: 1 | Failed: 0 | Skipped: 0
======================================================================
```

### Example 2: Motor Issues
```bash
python tooling/run_tests.py motors not moving in mode M
```

System detects:
- Mode: M (Motor mode)
- Subsystems: motor, connection
- Runs connection + motor test suite
- Reminds to flash Mode M firmware first

---

## Current Status

✅ **Implemented:**
- Base test framework with JSON output
- NLP router for natural language queries
- Main test runner with CLI
- ESP32 connection test
- Test result storage
- Learning system foundation

⏳ **TODO:**
- Additional hardware tests (motor, LED drivers)
- GUI tests (rendering, silhouette)
- Firmware flashing automation
- Auto-fix system
- Mode-specific test workflows

---

## Integration with PROMPT.md

This test system implements the specifications in `PROMPT.md`:
- ✅ Natural language test orchestration
- ✅ Progressive test ordering
- ✅ JSON test outputs
- ✅ Learning system
- ⏳ Firmware-first debugging (manual for now)
- ⏳ Auto-fix system (foundation ready)

---

For full specification, see [`PROMPT.md`](PROMPT.md)
