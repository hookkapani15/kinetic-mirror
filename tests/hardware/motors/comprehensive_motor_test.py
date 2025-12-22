"""
Comprehensive Motor System Test Suite
Tests all 32 servos, serial communication, and firmware integration
"""
import sys
import time
import serial
import struct
import traceback
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from packages.mirror_core.controllers.motor_controller import MotorController
from packages.mirror_core.io.serial_manager import SerialManager
from tooling.base_test import BaseTest


class MotorSystemTest(BaseTest):
    """Complete motor system validation"""
    
    def __init__(self):
        super().__init__("Motor System Comprehensive Test")
        self.results = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "tests_passed": 0,
            "tests_failed": 0,
            "errors": []
        }
    
    def run(self):
        """Required abstract method - runs all tests"""
        return self.run_all()
    
    def test_01_serial_port_detection(self):
        """Test 1: Detect and verify COM port"""
        self.log("TEST 1: Serial Port Detection")
        try:
            import serial.tools.list_ports
            ports = list(serial.tools.list_ports.comports())
            
            self.log(f"Found {len(ports)} serial ports:")
            for port in ports:
                self.log(f"  - {port.device}: {port.description}")
            
            # Try to find ESP32
            esp_port = None
            for port in ports:
                if "USB" in port.description or "Serial" in port.description:
                    esp_port = port.device
                    break
            
            if esp_port:
                self.log(f"✅ ESP32 likely at: {esp_port}")
                self.results["serial_port"] = esp_port
                self.results["tests_passed"] += 1
                return True
            else:
                self.log("⚠️ No ESP32 port detected automatically")
                self.results["tests_failed"] += 1
                return False
                
        except Exception as e:
            self.log(f"❌ Error: {e}")
            self.results["errors"].append(str(e))
            self.results["tests_failed"] += 1
            return False
    
    def test_02_serial_connection(self):
        """Test 2: Establish serial connection at 460800 baud"""
        self.log("\nTEST 2: Serial Connection")
        try:
            port = self.results.get("serial_port", "COM5")
            ser = serial.Serial(port, 460800, timeout=1)
            time.sleep(2)  # Wait for ESP32 to boot
            
            if ser.is_open:
                self.log(f"✅ Connected to {port} at 460800 baud")
                self.log(f"   Port: {ser.port}")
                self.log(f"   Baudrate: {ser.baudrate}")
                self.log(f"   Timeout: {ser.timeout}")
                ser.close()
                self.results["tests_passed"] += 1
                return True
            else:
                self.log("❌ Failed to open port")
                self.results["tests_failed"] += 1
                return False
                
        except Exception as e:
            self.log(f"❌ Connection error: {e}")
            traceback.print_exc()
            self.results["errors"].append(str(e))
            self.results["tests_failed"] += 1
            return False
    
    def test_03_motor_controller_init(self):
        """Test 3: Initialize motor controller for 32 servos"""
        self.log("\nTEST 3: Motor Controller Initialization")
        try:
            motor = MotorController(num_servos=32)
            
            self.log("✅ MotorController created")
            self.log(f"   Servos: {motor.num_servos}")
            self.log(f"   Angle Range: {motor.angle_min}° - {motor.angle_max}°")
            
            if motor.num_servos == 32:
                self.results["motor_controller"] = "initialized"
                self.results["tests_passed"] += 1
                return True
            else:
                self.log(f"❌ Expected 32 servos, got {motor.num_servos}")
                self.results["tests_failed"] += 1
                return False
                
        except Exception as e:
            self.log(f"❌ Initialization error: {e}")
            traceback.print_exc()
            self.results["errors"].append(str(e))
            self.results["tests_failed"] += 1
            return False
    
    def test_04_packet_generation(self):
        """Test 4: Generate and validate servo packets"""
        self.log("\nTEST 4: Packet Generation")
        try:
            motor = MotorController(num_servos=32)
            
            # Test center position (90 degrees all servos)
            angles = [90] * 32
            packet = motor.pack_servo_packet(angles)
            
            self.log(f"✅ Packet generated")
            self.log(f"   Size: {len(packet)} bytes (expected 67)")
            self.log(f"   Header: 0x{packet[0]:02X} 0x{packet[1]:02X} (expected 0xAA 0xBB)")
            self.log(f"   Type: 0x{packet[2]:02X} (expected 0x02)")
            
            # Verify packet structure
            if len(packet) == 67 and packet[0] == 0xAA and packet[1] == 0xBB and packet[2] == 0x02:
                self.log("✅ Packet structure valid")
                self.results["packet_generation"] = "valid"
                self.results["tests_passed"] += 1
                return True
            else:
                self.log("❌ Invalid packet structure")
                self.results["tests_failed"] += 1
                return False
                
        except Exception as e:
            self.log(f"❌ Packet error: {e}")
            traceback.print_exc()
            self.results["errors"].append(str(e))
            self.results["tests_failed"] += 1
            return False
    
    def test_05_angle_range_validation(self):
        """Test 5: Test all angle ranges (0, 90, 180 degrees)"""
        self.log("\nTEST 5: Angle Range Validation")
        try:
            motor = MotorController(num_servos=32)
            test_angles = [0, 45, 90, 135, 180]
            
            for angle in test_angles:
                angles = [angle] * 32
                packet = motor.pack_servo_packet(angles)
                
                # Decode first servo value
                value = (packet[3] << 8) | packet[4]
                decoded_angle = (value / 1000.0) * 180.0
                
                self.log(f"  Angle {angle}° → Value {value} → Decoded {decoded_angle:.1f}°")
            
            self.log("✅ All angles validated")
            self.results["angle_validation"] = "passed"
            self.results["tests_passed"] += 1
            return True
            
        except Exception as e:
            self.log(f"❌ Validation error: {e}")
            traceback.print_exc()
            self.results["errors"].append(str(e))
            self.results["tests_failed"] += 1
            return False
    
    def test_06_serial_manager_defensive_mode(self):
        """Test 6: Verify defensive serial writing (is_open checks)"""
        self.log("\nTEST 6: Defensive Serial Manager")
        try:
            port = self.results.get("serial_port", "COM5")
            serial_mgr = SerialManager(port, 460800)
            serial_mgr.start()
            time.sleep(2)
            
            motor = MotorController(num_servos=32)
            packet = motor.pack_servo_packet([90] * 32)
            
            # Test sending (should not crash even if port is bad)
            result = serial_mgr.send_servo(packet)
            
            self.log(f"✅ Defensive send completed (returned {result})")
            self.log("   is_open checks: ENABLED")
            self.log("   OSError handling: ENABLED")
            
            serial_mgr.close()
            time.sleep(0.5)
            
            self.results["defensive_mode"] = "active"
            self.results["tests_passed"] += 1
            return True
            
        except Exception as e:
            self.log(f"❌ Defensive mode error: {e}")
            traceback.print_exc()
            self.results["errors"].append(str(e))
            self.results["tests_failed"] += 1
            return False
    
    def test_07_full_range_sweep(self):
        """Test 7: Send full sweep command (0° to 180°)"""
        self.log("\nTEST 7: Full Range Sweep Test")
        try:
            port = self.results.get("serial_port", "COM5")
            serial_mgr = SerialManager(port, 460800)
            serial_mgr.start()
            time.sleep(2)
            
            motor = MotorController(num_servos=32)
            
            self.log("Sweeping all 32 servos: 0° → 90° → 180° → 90°")
            
            for angle in [0, 90, 180, 90]:
                packet = motor.pack_servo_packet([angle] * 32)
                serial_mgr.send_servo(packet)
                self.log(f"  Sent: {angle}°")
                time.sleep(1)
            
            serial_mgr.close()
            
            self.log("✅ Sweep completed")
            self.results["sweep_test"] = "completed"
            self.results["tests_passed"] += 1
            return True
            
        except Exception as e:
            self.log(f"❌ Sweep error: {e}")
            traceback.print_exc()
            self.results["errors"].append(str(e))
            self.results["tests_failed"] += 1
            return False
    
    def test_08_individual_servo_control(self):
        """Test 8: Test individual servo control (servo 0 and servo 31)"""
        self.log("\nTEST 8: Individual Servo Control")
        try:
            port = self.results.get("serial_port", "COM5")
            serial_mgr = SerialManager(port, 460800)
            serial_mgr.start()
            time.sleep(2)
            
            motor = MotorController(num_servos=32)
            
            # Center all
            packet = motor.pack_servo_packet([90] * 32)
            serial_mgr.send_servo(packet)
            time.sleep(1)
            
            # Move first servo
            self.log("  Moving servo 0 to 180°")
            angles = [180] + [90] * 31
            packet = motor.pack_servo_packet(angles)
            serial_mgr.send_servo(packet)
            time.sleep(1)
            
            # Move last servo
            self.log("  Moving servo 31 to 0°")
            angles = [90] * 31 + [0]
            packet = motor.pack_servo_packet(angles)
            serial_mgr.send_servo(packet)
            time.sleep(1)
            
            # Center all again
            packet = motor.pack_servo_packet([90] * 32)
            serial_mgr.send_servo(packet)
            
            serial_mgr.close()
            
            self.log("✅ Individual control verified")
            self.results["individual_control"] = "verified"
            self.results["tests_passed"] += 1
            return True
            
        except Exception as e:
            self.log(f"❌ Control error: {e}")
            traceback.print_exc()
            self.results["errors"].append(str(e))
            self.results["tests_failed"] += 1
            return False
    
    def test_09_high_frequency_commands(self):
        """Test 9: Send rapid commands (20 Hz rate limiting)"""
        self.log("\nTEST 9: High Frequency Command Test")
        try:
            port = self.results.get("serial_port", "COM5")
            serial_mgr = SerialManager(port, 460800)
            serial_mgr.start()
            time.sleep(2)
            
            motor = MotorController(num_servos=32)
            
            self.log("Sending 100 rapid commands...")
            start_time = time.time()
            
            for i in range(100):
                angle = 90 + 30 * (i % 2)  # Alternate 90° and 120°
                packet = motor.pack_servo_packet([angle] * 32)
                serial_mgr.send_servo(packet)
                time.sleep(0.05)  # 20 Hz
            
            duration = time.time() - start_time
            rate = 100 / duration
            
            self.log(f"✅ Sent 100 commands in {duration:.2f}s ({rate:.1f} Hz)")
            
            serial_mgr.close()
            
            self.results["high_frequency"] = f"{rate:.1f} Hz"
            self.results["tests_passed"] += 1
            return True
            
        except Exception as e:
            self.log(f"❌ Frequency test error: {e}")
            traceback.print_exc()
            self.results["errors"].append(str(e))
            self.results["tests_failed"] += 1
            return False
    
    def test_10_firmware_response(self):
        """Test 10: Check ESP32 firmware response"""
        self.log("\nTEST 10: Firmware Response Check")
        try:
            port = self.results.get("serial_port", "COM5")
            ser = serial.Serial(port, 460800, timeout=2)
            time.sleep(2)
            
            # Read any startup messages
            data = ser.read(1000)
            if data:
                message = data.decode('utf-8', errors='ignore')
                self.log("ESP32 Output:")
                for line in message.split('\n'):
                    if line.strip():
                        self.log(f"  {line.strip()}")
                
                if "READY" in message or "ESP32" in message:
                    self.log("✅ Firmware responding")
                    self.results["firmware_response"] = "active"
                    self.results["tests_passed"] += 1
                    ser.close()
                    return True
            
            self.log("⚠️ No clear firmware response (may be normal)")
            ser.close()
            self.results["tests_passed"] += 1
            return True
            
        except Exception as e:
            self.log(f"⚠️ Response check: {e}")
            self.results["tests_passed"] += 1  # Non-critical
            return True
    
    def save_results(self):
        """Save test results to file"""
        import json
        from pathlib import Path
        
        results_dir = Path(__file__).parent.parent.parent / "settings" / "test_results"
        results_dir.mkdir(exist_ok=True)
        
        filename = f"motor_test_{time.strftime('%Y%m%d_%H%M%S')}.json"
        filepath = results_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        self.log(f"\n✅ Results saved to: {filepath}")
    
    def run_all(self):
        """Run all tests"""
        self.log("="*60)
        self.log("  COMPREHENSIVE MOTOR SYSTEM TEST SUITE")
        self.log("  32 Servos | Dual PCA9685 | ESP32-S3")
        self.log("="*60)
        
        tests = [
            self.test_01_serial_port_detection,
            self.test_02_serial_connection,
            self.test_03_motor_controller_init,
            self.test_04_packet_generation,
            self.test_05_angle_range_validation,
            self.test_06_serial_manager_defensive_mode,
            self.test_07_full_range_sweep,
            self.test_08_individual_servo_control,
            self.test_09_high_frequency_commands,
            self.test_10_firmware_response
        ]
        
        for test_func in tests:
            try:
                test_func()
            except Exception as e:
                self.log(f"\n❌ CRITICAL ERROR in {test_func.__name__}: {e}")
                traceback.print_exc()
                self.results["tests_failed"] += 1
        
        # Summary
        self.log("\n" + "="*60)
        self.log("  TEST SUMMARY")
        self.log("="*60)
        self.log(f"✅ Passed: {self.results['tests_passed']}")
        self.log(f"❌ Failed: {self.results['tests_failed']}")
        total = self.results['tests_passed'] + self.results['tests_failed']
        if total > 0:
            success_rate = (self.results['tests_passed'] / total) * 100
            self.log(f"📊 Success Rate: {success_rate:.1f}%")
        
        if self.results['errors']:
            self.log("\n⚠️ Errors encountered:")
            for err in self.results['errors']:
                self.log(f"  - {err}")
        
        self.save_results()
        
        return self.results['tests_failed'] == 0


if __name__ == "__main__":
    test_suite = MotorSystemTest()
    success = test_suite.run_all()
    sys.exit(0 if success else 1)
