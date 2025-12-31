/**
 * Automated Test Script for ESP32 Mirror Body
 * Run: python tools/test_esp32.py --port COM3
 */

import serial
import time
import sys
import json
from datetime import datetime


class ESP32Tester:
    """Automated test suite for ESP32 firmware"""
    
    def __init__(self, port, baudrate=115200):
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self.tests_passed = 0
        self.tests_failed = 0
        self.tests_skipped = 0
    
    def connect(self):
        """Connect to ESP32"""
        print(f"Connecting to ESP32 on {self.port}...")
        self.ser = serial.Serial(self.port, self.baudrate, timeout=5)
        time.sleep(2)
        print("Connected!")
        self.ser.reset_input_buffer()
    
    def disconnect(self):
        """Disconnect from ESP32"""
        if self.ser:
            self.ser.close()
            print("Disconnected from ESP32")
    
    def send_command(self, command, timeout=2):
        """Send command and get response"""
        self.ser.write((command + "\n").encode())
        time.sleep(0.1)
        
        response = ""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.ser.in_waiting:
                line = self.ser.readline().decode().strip()
                response += line + "\n"
                if "OK" in line or "FAIL" in line:
                    break
        
        return response.strip()
    
    def run_test(self, test_name):
        """Run a single test"""
        print(f"  Running: {test_name}...", end=" ")
        
        response = self.send_command(f"TEST:{test_name}")
        
        if "PASS" in response:
            print("✓ PASS")
            self.tests_passed += 1
            return True
        elif "FAIL" in response:
            print(f"✗ FAIL")
            print(f"    Error: {response}")
            self.tests_failed += 1
            return False
        elif "SKIP" in response:
            print("⊘ SKIP")
            self.tests_skipped += 1
            return None
        else:
            print(f"? UNKNOWN")
            self.tests_failed += 1
            return False
    
    def run_led_tests(self):
        """Run LED controller tests"""
        print("\n" + "="*50)
        print("LED CONTROLLER TESTS")
        print("="*50)
        
        tests = [
            "LED_INIT",
            "LED_SINGLE",
            "LED_MULTIPLE",
            "LED_FILL",
            "LED_CLEAR",
            "LED_BRIGHTNESS",
            "LED_GRADIENT",
            "LED_BOUNDS",
            "LED_PERFORMANCE",
        ]
        
        for test in tests:
            self.run_test(test)
    
    def run_motor_tests(self):
        """Run motor controller tests"""
        print("\n" + "="*50)
        print("MOTOR CONTROLLER TESTS")
        print("="*50)
        
        tests = [
            "MOTOR_INIT",
            "MOTOR_SINGLE",
            "MOTOR_ALL",
            "MOTOR_LIMITS",
            "MOTOR_CALIBRATION",
            "MOTOR_SPEED",
            "MOTOR_ACCURACY",
        ]
        
        for test in tests:
            self.run_test(test)
    
    def run_protocol_tests(self):
        """Run serial protocol tests"""
        print("\n" + "="*50)
        print("SERIAL PROTOCOL TESTS")
        print("="*50)
        
        tests = [
            "PROTOCOL_LED",
            "PROTOCOL_MOTOR",
            "PROTOCOL_PATTERN",
            "PROTOCOL_INVALID",
            "PROTOCOL_CHECKSUM",
        ]
        
        for test in tests:
            self.run_test(test)
    
    def run_power_tests(self):
        """Run power monitoring tests"""
        print("\n" + "="*50)
        print("POWER MONITORING TESTS")
        print("="*50)
        
        tests = [
            "POWER_LED_ONLY",
            "POWER_MOTOR_ONLY",
            "POWER_COMBINED",
            "POWER_IDLE",
        ]
        
        for test in tests:
            self.run_test(test)
    
    def run_all_tests(self):
        """Run complete test suite"""
        print("\n" + "="*70)
        print("  ESP32 TEST SUITE - AUTOMATED TESTING")
        print("="*70)
        print(f"  Port: {self.port}")
        print(f"  Baudrate: {self.baudrate}")
        print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        self.connect()
        
        try:
            self.run_led_tests()
            self.run_motor_tests()
            self.run_protocol_tests()
            self.run_power_tests()
        finally:
            self.disconnect()
        
        print("\n" + "="*70)
        print("  TEST SUMMARY")
        print("="*70)
        total = self.tests_passed + self.tests_failed + self.tests_skipped
        print(f"  Total:   {total}")
        print(f"  Passed:  {self.tests_passed} ({self.tests_passed/total*100:.1f}%)")
        print(f"  Failed:  {self.tests_failed} ({self.tests_failed/total*100:.1f}%)")
        print(f"  Skipped: {self.tests_skipped} ({self.tests_skipped/total*100:.1f}%)")
        print("="*70)
        
        return self.tests_failed == 0
    
    def save_results(self, filename=None):
        """Save test results to file"""
        if filename is None:
            filename = f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "port": self.port,
            "baudrate": self.baudrate,
            "summary": {
                "total": self.tests_passed + self.tests_failed + self.tests_skipped,
                "passed": self.tests_passed,
                "failed": self.tests_failed,
                "skipped": self.tests_skipped,
            }
        }
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\nResults saved to: {filename}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='ESP32 Test Suite')
    parser.add_argument('--port', '-p', default='/dev/ttyUSB0', help='Serial port')
    parser.add_argument('--baud', '-b', default=115200, help='Baud rate')
    parser.add_argument('--led', action='store_true', help='Run LED tests only')
    parser.add_argument('--motor', action='store_true', help='Run motor tests only')
    parser.add_argument('--protocol', action='store_true', help='Run protocol tests only')
    parser.add_argument('--power', action='store_true', help='Run power tests only')
    
    args = parser.parse_args()
    
    tester = ESP32Tester(args.port, args.baud)
    
    if args.led:
        tester.connect()
        tester.run_led_tests()
    elif args.motor:
        tester.connect()
        tester.run_motor_tests()
    elif args.protocol:
        tester.connect()
        tester.run_protocol_tests()
    elif args.power:
        tester.connect()
        tester.run_power_tests()
    else:
        success = tester.run_all_tests()
        tester.save_results()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
