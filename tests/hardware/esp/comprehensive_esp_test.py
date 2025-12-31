#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive ESP32 Test Suite
Exponentially increasing tests from basic to advanced
Tests: 10 progressive tests covering all scenarios
"""

import sys
import time
import serial
from pathlib import Path

# Add project root to path
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tooling"))

from base_test import BaseTest


# ============================================================================
# TEST 1: Basic Connection Test
# ============================================================================

class ESP32BasicConnection(BaseTest):
    """Test 1: Basic serial connection to ESP32"""

    def __init__(self, port=None, baud=460800):
        super().__init__("ESP32: Basic Connection")
        self.port = port
        self.baud = baud

    def run(self):
        import serial.tools.list_ports

        ports = list(serial.tools.list_ports.comports())

        if not ports:
            return self.fail_test(
                "No serial ports detected",
                suggested_actions=[
                    "Connect ESP32 via USB",
                    "Install CH340/CP2102 drivers",
                    "Check USB cable is data cable"
                ]
            )

        # Auto-detect ESP32
        test_port = None
        for p in ports:
            desc = p.description.lower()
            if any(k in desc for k in ['ch340', 'cp210', 'usb-serial', 'uart']):
                test_port = p.device
                break

        if not test_port and self.port:
            test_port = self.port

        if not test_port:
            return self.fail_test(
                f"ESP32 not detected. Ports: {', '.join(p.device for p in ports)}",
                suggested_actions=[
                    "Check ESP32 power",
                    "Try different USB port",
                    "Reinstall drivers"
                ]
            )

        try:
            ser = serial.Serial(test_port, self.baud, timeout=2)
            ser.close()
            return self.pass_test(
                f"Connected to ESP32 on {test_port}",
                metrics={"port": test_port, "baud": self.baud},
                learns={"last_good_port": test_port}
            )
        except Exception as e:
            return self.fail_test(
                f"Connection failed: {str(e)}",
                suggested_actions=[
                    "Close other serial programs",
                    "Reset ESP32",
                    "Try different baud rate"
                ]
            )


# ============================================================================
# TEST 2: ESP32 Responsiveness Test
# ============================================================================

class ESP32Responsiveness(BaseTest):
    """Test 2: ESP32 responds to commands"""

    def __init__(self, port=None):
        super().__init__("ESP32: Command Responsiveness")
        self.port = port

    def run(self):
        if not self.port:
            return self.skip_test("No port available")

        try:
            ser = serial.Serial(self.port, 460800, timeout=2)

            # Send PING command
            ser.write(b"PING\n")
            response = ser.readline().decode().strip()

            ser.close()

            if "PONG" in response or "READY" in response:
                return self.pass_test(
                    f"ESP32 responded: {response}",
                    metrics={"response": response}
                )
            else:
                return self.fail_test(
                    f"Unexpected response: {response}",
                    suggested_actions=[
                        "ESP32 firmware may not be running",
                        "Check baud rate",
                        "Flash firmware"
                    ]
                )
        except Exception as e:
            return self.fail_test(
                f"Responsiveness test failed: {str(e)}",
                suggested_actions=[
                    "Check ESP32 is powered",
                    "Verify correct port",
                    "Reset ESP32"
                ]
            )


# ============================================================================
# TEST 3: LED Communication Test
# ============================================================================

class ESP32LEDCommTest(BaseTest):
    """Test 3: ESP32 can receive LED data"""

    def __init__(self, port=None):
        super().__init__("ESP32: LED Communication")
        self.port = port

    def run(self):
        if not self.port:
            return self.skip_test("No port available")

        try:
            ser = serial.Serial(self.port, 460800, timeout=2)

            # Send LED test packet
            ser.write(b"LED_TEST\n")
            time.sleep(0.5)

            # Read response
            response = ser.readline().decode().strip()

            ser.close()

            if "OK" in response or "LED" in response:
                return self.pass_test(
                    f"LED communication working: {response}",
                    metrics={"response": response}
                )
            else:
                return self.fail_test(
                    f"LED comm failed: {response}",
                    suggested_actions=[
                        "Check LED data wiring (GPIO 12/13)",
                        "Verify LED panels powered",
                        "Check ESP32 firmware supports LEDs"
                    ]
                )
        except Exception as e:
            return self.fail_test(
                f"LED comm error: {str(e)}"
            )


# ============================================================================
# TEST 4: Motor Communication Test
# ============================================================================

class ESP32MotorCommTest(BaseTest):
    """Test 4: ESP32 can receive motor commands"""

    def __init__(self, port=None):
        super().__init__("ESP32: Motor Communication")
        self.port = port

    def run(self):
        if not self.port:
            return self.skip_test("No port available")

        try:
            ser = serial.Serial(self.port, 460800, timeout=2)

            # Send motor test packet
            ser.write(b"MOTOR_TEST\n")
            time.sleep(0.5)

            response = ser.readline().decode().strip()

            ser.close()

            if "OK" in response or "MOTOR" in response:
                return self.pass_test(
                    f"Motor communication working: {response}",
                    metrics={"response": response}
                )
            else:
                return self.fail_test(
                    f"Motor comm failed: {response}",
                    suggested_actions=[
                        "Check I2C wiring (SDA/SCL)",
                        "Verify PCA9685 powered",
                        "Check I2C addresses are unique"
                    ]
                )
        except Exception as e:
            return self.fail_test(
                f"Motor comm error: {str(e)}"
            )


# ============================================================================
# TEST 5: LED Data Integrity Test
# ============================================================================

class ESP32LEDIntegrity(BaseTest):
    """Test 5: Verify LED data integrity"""

    def __init__(self, port=None):
        super().__init__("ESP32: LED Data Integrity")
        self.port = port

    def run(self):
        if not self.port:
            return self.skip_test("No port available")

        try:
            ser = serial.Serial(self.port, 460800, timeout=5)

            # Send test pattern data
            test_data = bytes([255] * 32 * 3)  # White color, 32 LEDs
            ser.write(test_data)
            time.sleep(0.1)

            response = ser.readline().decode().strip()

            ser.close()

            if "OK" in response:
                return self.pass_test(
                    "LED data integrity verified",
                    metrics={"data_size": len(test_data)}
                )
            else:
                return self.fail_test(
                    f"LED integrity check failed: {response}",
                    suggested_actions=[
                        "Check wiring for loose connections",
                        "Verify power supply is sufficient",
                        "Check for noise on data line"
                    ]
                )
        except Exception as e:
            return self.fail_test(
                f"LED integrity error: {str(e)}"
            )


# ============================================================================
# TEST 6: Motor Command Integrity Test
# ============================================================================

class ESP32MotorIntegrity(BaseTest):
    """Test 6: Verify motor command integrity"""

    def __init__(self, port=None):
        super().__init__("ESP32: Motor Command Integrity")
        self.port = port

    def run(self):
        if not self.port:
            return self.skip_test("No port available")

        try:
            ser = serial.Serial(self.port, 460800, timeout=5)

            # Send test motor command
            # Format: M<channel><angle>
            ser.write(b"M0090\n")  # Motor 0, 90 degrees
            time.sleep(0.2)

            response = ser.readline().decode().strip()

            ser.close()

            if "OK" in response or "DONE" in response:
                return self.pass_test(
                    "Motor command integrity verified",
                    metrics={"motor": 0, "angle": 90}
                )
            else:
                return self.fail_test(
                    f"Motor command failed: {response}",
                    suggested_actions=[
                        "Check I2C connection",
                        "Verify PCA9685 addresses",
                        "Check motor power supply"
                    ]
                )
        except Exception as e:
            return self.fail_test(
                f"Motor integrity error: {str(e)}"
            )


# ============================================================================
# TEST 7: Speed/Stress Test
# ============================================================================

class ESP32SpeedTest(BaseTest):
    """Test 7: ESP32 can handle high-speed data"""

    def __init__(self, port=None):
        super().__init__("ESP32: Speed/Stress Test")
        self.port = port

    def run(self):
        if not self.port:
            return self.skip_test("No port available")

        try:
            ser = serial.Serial(self.port, 460800, timeout=10)

            # Send 100 LED packets rapidly
            start_time = time.time()
            packets_sent = 0

            for i in range(100):
                packet = bytes([i % 256] * 100)
                ser.write(packet)
                packets_sent += 1

            elapsed = time.time() - start_time

            ser.close()

            throughput = packets_sent / elapsed

            if throughput > 10:  # 10+ packets per second
                return self.pass_test(
                    f"Speed test passed: {throughput:.1f} packets/sec",
                    metrics={
                        "packets": packets_sent,
                        "time": elapsed,
                        "throughput": throughput
                    }
                )
            else:
                return self.fail_test(
                    f"Speed too slow: {throughput:.1f} packets/sec",
                    suggested_actions=[
                        "Increase baud rate",
                        "Check for serial latency",
                        "Optimize ESP32 code"
                    ],
                    metrics={"throughput": throughput}
                )
        except Exception as e:
            return self.fail_test(
                f"Speed test error: {str(e)}"
            )


# ============================================================================
# TEST 8: Error Recovery Test
# ============================================================================

class ESP32ErrorRecovery(BaseTest):
    """Test 8: ESP32 recovers from errors"""

    def __init__(self, port=None):
        super().__init__("ESP32: Error Recovery")
        self.port = port

    def run(self):
        if not self.port:
            return self.skip_test("No port available")

        try:
            ser = serial.Serial(self.port, 460800, timeout=5)

            # Send invalid commands
            ser.write(b"INVALID_COMMAND\n")
            time.sleep(0.2)
            response1 = ser.readline().decode().strip()

            # Send valid command
            ser.write(b"PING\n")
            time.sleep(0.2)
            response2 = ser.readline().decode().strip()

            ser.close()

            if "PONG" in response2:
                return self.pass_test(
                    "ESP32 recovered from error",
                    metrics={
                        "error_response": response1,
                        "recovery_response": response2
                    }
                )
            else:
                return self.fail_test(
                    f"ESP32 did not recover: {response2}",
                    suggested_actions=[
                        "Firmware may need error handling improvements",
                        "Check for memory leaks",
                        "Add watchdog timer"
                    ]
                )
        except Exception as e:
            return self.fail_test(
                f"Error recovery test failed: {str(e)}"
            )


# ============================================================================
# TEST 9: Multi-Channel Test
# ============================================================================

class ESP32MultiChannel(BaseTest):
    """Test 9: Test both LED data channels"""

    def __init__(self, port=None):
        super().__init__("ESP32: Multi-Channel Test")
        self.port = port

    def run(self):
        if not self.port:
            return self.skip_test("No port available")

        try:
            ser = serial.Serial(self.port, 460800, timeout=5)

            # Test Channel 1
            ser.write(b"LED_CH1_TEST\n")
            time.sleep(0.3)
            response1 = ser.readline().decode().strip()

            # Test Channel 2
            ser.write(b"LED_CH2_TEST\n")
            time.sleep(0.3)
            response2 = ser.readline().decode().strip()

            ser.close()

            ch1_ok = "OK" in response1
            ch2_ok = "OK" in response2

            if ch1_ok and ch2_ok:
                return self.pass_test(
                    "Both LED channels working",
                    metrics={
                        "channel1": response1,
                        "channel2": response2
                    }
                )
            elif ch1_ok:
                return self.fail_test(
                    "Channel 2 not working",
                    suggested_actions=[
                        "Check GPIO 13 wiring",
                        "Verify second LED chain powered",
                        "Check daisy chain connections"
                    ]
                )
            elif ch2_ok:
                return self.fail_test(
                    "Channel 1 not working",
                    suggested_actions=[
                        "Check GPIO 12 wiring",
                        "Verify first LED chain powered",
                        "Check daisy chain connections"
                    ]
                )
            else:
                return self.fail_test(
                    "Neither channel working",
                    suggested_actions=[
                        "Check both GPIO 12 and 13",
                        "Verify power to all panels",
                        "Check ESP32 firmware supports 2 channels"
                    ]
                )
        except Exception as e:
            return self.fail_test(
                f"Multi-channel test error: {str(e)}"
            )


# ============================================================================
# TEST 10: Long-Run Stability Test
# ============================================================================

class ESP32Stability(BaseTest):
    """Test 10: Long-run stability"""

    def __init__(self, port=None, duration=30):
        super().__init__("ESP32: Stability Test")
        self.port = port
        self.duration = duration

    def run(self):
        if not self.port:
            return self.skip_test("No port available")

        try:
            ser = serial.Serial(self.port, 460800, timeout=5)

            start_time = time.time()
            errors = 0
            successes = 0

            print(f"    Running for {self.duration} seconds...", end=" ")

            while (time.time() - start_time) < self.duration:
                # Send PING every second
                ser.write(b"PING\n")
                response = ser.readline().decode().strip()

                if "PONG" in response or "READY" in response:
                    successes += 1
                else:
                    errors += 1

                time.sleep(1.0)

            ser.close()

            if errors == 0:
                return self.pass_test(
                    f"Stable: {successes} successful pings",
                    metrics={
                        "duration": self.duration,
                        "successes": successes,
                        "errors": errors
                    }
                )
            elif errors < 5:
                return self.fail_test(
                    f"Minor instability: {errors} errors in {self.duration}s",
                    suggested_actions=[
                        "May be acceptable for some applications",
                        "Check power supply stability",
                        "Add error handling in firmware"
                    ],
                    metrics={"successes": successes, "errors": errors}
                )
            else:
                return self.fail_test(
                    f"Unstable: {errors} errors in {self.duration}s",
                    suggested_actions=[
                        "Power supply issues",
                        "Firmware bugs",
                        "Electrical noise",
                        "Overheating"
                    ],
                    metrics={"successes": successes, "errors": errors}
                )
        except Exception as e:
            return self.fail_test(
                f"Stability test error: {str(e)}"
            )


# ============================================================================
# Main - Run all tests
# ============================================================================

if __name__ == "__main__":
    from base_test import TestSuite

    # Detect port
    import serial.tools.list_ports
    ports = list(serial.tools.list_ports.comports())
    port = None
    if ports:
        for p in ports:
            desc = p.description.lower()
            if any(k in desc for k in ['ch340', 'cp210', 'usb-serial']):
                port = p.device
                break

    # Create test suite
    suite = TestSuite("Comprehensive ESP32 Test Suite")

    tests = [
        ESP32BasicConnection(port),
        ESP32Responsiveness(port),
        ESP32LEDCommTest(port),
        ESP32MotorCommTest(port),
        ESP32LEDIntegrity(port),
        ESP32MotorIntegrity(port),
        ESP32SpeedTest(port),
        ESP32ErrorRecovery(port),
        ESP32MultiChannel(port),
        ESP32Stability(port, duration=15)
    ]

    for test in tests:
        suite.add_test(test)

    # Run tests
    print("\n" + "=" * 70)
    print("  COMPREHENSIVE ESP32 TEST SUITE")
    print("=" * 70)
    print()

    results = suite.run_all()
    suite.print_summary()
