"""
Comprehensive LED System Test Suite
Tests all 2048 LEDs across 8 panels (16×16 each)
"""
import sys
import time
import serial
import numpy as np
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from packages.mirror_core.controllers.led_controller import LEDController
from packages.mirror_core.io.serial_manager import SerialManager
from packages.mirror_core.testing.led_panel_tester import LEDPanelTester
from tooling.base_test import BaseTest


class LEDSystemTest(BaseTest):
    """Complete LED system validation"""
    
    def __init__(self):
        super().__init__("LED System Comprehensive Test")
        self.results = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "tests_passed": 0,
            "tests_failed": 0,
            "errors": []
        }
    
    def run(self):
        """Required abstract method - runs all tests"""
        return self.run_all()
    
    def test_01_led_controller_init(self):
        """Test 1: Initialize LED controller for 2048 LEDs"""
        print("TEST 1: LED Controller Initialization")
        try:
            led = LEDController(width=32, height=64)
            
            print("[OK] LEDController created")
            print(f"   Width: {led.width}")
            print(f"   Height: {led.height}")
            print(f"   Total LEDs: {led.width * led.height}")
            
            if led.width == 32 and led.height == 64:
                self.results["led_controller"] = "initialized"
                self.results["tests_passed"] += 1
                return True
            else:
                print(f"[FAIL] Expected 32x64, got {led.width}x{led.height}")
                self.results["tests_failed"] += 1
                return False
                
        except Exception as e:
            print(f"[FAIL] Initialization error: {e}")
            self.results["errors"].append(str(e))
            self.results["tests_failed"] += 1
            return False
    
    def test_02_panel_tester_init(self):
        """Test 2: Initialize panel tester"""
        print("\nTEST 2: Panel Tester Initialization")
        try:
            tester = LEDPanelTester()
            info = tester.get_panel_info()
            
            print("[OK] LEDPanelTester created")
            for key, value in info.items():
                print(f"   {key}: {value}")
            
            if info["total_panels"] == 8:
                self.results["panel_tester"] = "initialized"
                self.results["tests_passed"] += 1
                return True
            else:
                print(f"[FAIL] Expected 8 panels, got {info['total_panels']}")
                self.results["tests_failed"] += 1
                return False
                
        except Exception as e:
            print(f"[FAIL] Initialization error: {e}")
            self.results["errors"].append(str(e))
            self.results["tests_failed"] += 1
            return False
    
    def test_03_panel_numbering_pattern(self):
        """Test 3: Generate panel numbering pattern (1-8)"""
        print("\nTEST 3: Panel Numbering Pattern")
        try:
            tester = LEDPanelTester()
            pattern = tester.generate_panel_test_pattern()
            
            print(f"[OK] Pattern generated")
            print(f"   Shape: {pattern.shape}")
            print(f"   Expected: (64, 32)")
            
            if pattern.shape == (64, 32):
                self.results["numbering_pattern"] = "valid"
                self.results["tests_passed"] += 1
                return True
            else:
                print(f"[FAIL] Invalid shape")
                self.results["tests_failed"] += 1
                return False
                
        except Exception as e:
            print(f"[FAIL] Pattern error: {e}")
            self.results["errors"].append(str(e))
            self.results["tests_failed"] += 1
            return False
    
    def test_04_individual_panel_patterns(self):
        """Test 4: Generate individual panel patterns (panels 1-8)"""
        print("\nTEST 4: Individual Panel Patterns")
        try:
            tester = LEDPanelTester()
            
            for panel_id in range(1, 9):
                pattern = tester.generate_individual_panel_test(panel_id)
                print(f"  Panel {panel_id}: Generated {pattern.shape}")
            
            print("[OK] All 8 individual patterns generated")
            self.results["individual_panels"] = "valid"
            self.results["tests_passed"] += 1
            return True
            
        except Exception as e:
            print(f"❌ Pattern error: {e}")
            self.results["errors"].append(str(e))
            self.results["tests_failed"] += 1
            return False
    
    def test_05_led_packet_generation(self):
        """Test 5: Generate and validate LED packets"""
        print("\nTEST 5: LED Packet Generation")
        try:
            led = LEDController(width=32, height=64)
            
            # Create test frame (white)
            test_frame = np.full((64, 32), 255, dtype=np.uint8)
            packet = led.pack_led_packet(test_frame)
            
            print(f"✅ Packet generated")
            print(f"   Size: {len(packet)} bytes (expected 2051)")
            print(f"   Header: 0x{packet[0]:02X} 0x{packet[1]:02X} (expected 0xAA 0xBB)")
            print(f"   Type: 0x{packet[2]:02X} (expected 0x01)")
            
            # Verify packet structure
            if len(packet) == 2051 and packet[0] == 0xAA and packet[1] == 0xBB and packet[2] == 0x01:
                print("[OK] Packet structure valid")
                self.results["packet_generation"] = "valid"
                self.results["tests_passed"] += 1
                return True
            else:
                print("[FAIL] Invalid packet structure")
                self.results["tests_failed"] += 1
                return False
                
        except Exception as e:
            print(f"[FAIL] Packet error: {e}")
            self.results["errors"].append(str(e))
            self.results["tests_failed"] += 1
            return False
    
    def test_06_color_patterns(self):
        """Test 6: Test solid color patterns (R, G, B, White)"""
        print("\nTEST 6: Color Patterns")
        try:
            tester = LEDPanelTester()
            colors = tester.generate_solid_color_test()
            
            for color_name in ['red', 'green', 'blue', 'white']:
                pattern = colors[color_name]
                print(f"  {color_name.upper()}: {pattern.shape}")
            
            print("[OK] All color patterns generated")
            self.results["color_patterns"] = "valid"
            self.results["tests_passed"] += 1
            return True
            
        except Exception as e:
            print(f"[FAIL] Color pattern error: {e}")
            self.results["errors"].append(str(e))
            self.results["tests_failed"] += 1
            return False
    
    def test_07_geometric_patterns(self):
        """Test 7: Test geometric patterns (gradient, checkerboard, borders)"""
        print("\nTEST 7: Geometric Patterns")
        try:
            tester = LEDPanelTester()
            
            gradient = tester.generate_gradient_test()
            print(f"  Gradient: {gradient.shape}")
            
            checkerboard = tester.generate_checkerboard_test()
            print(f"  Checkerboard: {checkerboard.shape}")
            
            borders = tester.generate_panel_border_test()
            print(f"  Panel Borders: {borders.shape}")
            
            print("[OK] All geometric patterns generated")
            self.results["geometric_patterns"] = "valid"
            self.results["tests_passed"] += 1
            return True
            
        except Exception as e:
            print(f"[FAIL] Geometric pattern error: {e}")
            self.results["errors"].append(str(e))
            self.results["tests_failed"] += 1
            return False
    
    def test_08_serial_led_transmission(self):
        """Test 8: Send LED data via serial"""
        print("\nTEST 8: Serial LED Transmission")
        try:
            port = self.results.get("serial_port", "COM5")
            serial_mgr = SerialManager(port, 460800)
            serial_mgr.start()
            time.sleep(2)
            
            led = LEDController(width=32, height=64)
            tester = LEDPanelTester()
            
            # Send panel numbering pattern
            pattern = tester.generate_panel_test_pattern()
            packet = led.pack_led_packet(pattern)
            
            print(f"  Sending {len(packet)} bytes...")
            serial_mgr.send_led(packet)
            time.sleep(0.5)
            
            print("[OK] LED data transmitted")
            
            serial_mgr.close()
            
            self.results["led_transmission"] = "success"
            self.results["tests_passed"] += 1
            return True
            
        except Exception as e:
            print(f"[FAIL] Transmission error: {e}")
            self.results["errors"].append(str(e))
            self.results["tests_failed"] += 1
            return False
    
    def test_09_sequential_panel_test(self):
        """Test 9: Light up panels 1-8 sequentially"""
        print("\nTEST 9: Sequential Panel Test")
        try:
            port = self.results.get("serial_port", "COM5")
            serial_mgr = SerialManager(port, 460800)
            serial_mgr.start()
            time.sleep(2)
            
            led = LEDController(width=32, height=64)
            tester = LEDPanelTester()
            
            print("Lighting panels 1 through 8 sequentially...")
            
            for panel_id in range(1, 9):
                pattern = tester.generate_individual_panel_test(panel_id)
                packet = led.pack_led_packet(pattern)
                serial_mgr.send_led(packet)
                print(f"  Panel {panel_id} lit")
                time.sleep(0.5)
            
            # All off
            pattern = np.zeros((64, 32), dtype=np.uint8)
            packet = led.pack_led_packet(pattern)
            serial_mgr.send_led(packet)
            
            serial_mgr.close()
            
            print("[OK] Sequential test completed")
            self.results["sequential_test"] = "completed"
            self.results["tests_passed"] += 1
            return True
            
        except Exception as e:
            print(f"[FAIL] Sequential test error: {e}")
            self.results["errors"].append(str(e))
            self.results["tests_failed"] += 1
            return False
    
    def test_10_brightness_levels(self):
        """Test 10: Test different brightness levels"""
        print("\nTEST 10: Brightness Levels Test")
        try:
            port = self.results.get("serial_port", "COM5")
            serial_mgr = SerialManager(port, 460800)
            serial_mgr.start()
            time.sleep(2)
            
            led = LEDController(width=32, height=64)
            
            brightness_levels = [25, 50, 100, 150, 200, 255]
            
            print("Testing brightness levels...")
            
            for brightness in brightness_levels:
                pattern = np.full((64, 32), brightness, dtype=np.uint8)
                packet = led.pack_led_packet(pattern)
                serial_mgr.send_led(packet)
                print(f"  Brightness: {brightness}/255")
                time.sleep(0.5)
            
            # All off
            pattern = np.zeros((64, 32), dtype=np.uint8)
            packet = led.pack_led_packet(pattern)
            serial_mgr.send_led(packet)
            
            serial_mgr.close()
            
            print("[OK] Brightness test completed")
            self.results["brightness_test"] = "completed"
            self.results["tests_passed"] += 1
            return True
            
        except Exception as e:
            print(f"[FAIL] Brightness test error: {e}")
            self.results["errors"].append(str(e))
            self.results["tests_failed"] += 1
            return False
    
    def save_results(self):
        """Save test results to file"""
        import json
        from pathlib import Path
        
        results_dir = Path(__file__).parent.parent.parent / "settings" / "test_results"
        results_dir.mkdir(exist_ok=True)
        
        filename = f"led_test_{time.strftime('%Y%m%d_%H%M%S')}.json"
        filepath = results_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\n[OK] Results saved to: {filepath}")
    
    def run_all(self):
        """Run all tests"""
        print("="*60)
        print("  COMPREHENSIVE LED SYSTEM TEST SUITE")
        print("  2048 LEDs | 8 Panels (16×16) | ESP32-S3")
        print("="*60)
        
        # Note: test_01_serial_port_detection would be identical to Motor tests, so we skip it
        # The serial_port is assumed to be COM5
        self.results["serial_port"] = "COM5"
        
        tests = [
            self.test_01_led_controller_init,
            self.test_02_panel_tester_init,
            self.test_03_panel_numbering_pattern,
            self.test_04_individual_panel_patterns,
            self.test_05_led_packet_generation,
            self.test_06_color_patterns,
            self.test_07_geometric_patterns,
            self.test_08_serial_led_transmission,
            self.test_09_sequential_panel_test,
            self.test_10_brightness_levels
        ]
        
        for test_func in tests:
            try:
                test_func()
            except Exception as e:
                print(f"\n[FAIL] CRITICAL ERROR in {test_func.__name__}: {e}")
                import traceback
                traceback.print_exc()
                self.results["tests_failed"] += 1
        
        # Summary
        print("\n" + "="*60)
        print("  TEST SUMMARY")
        print("="*60)
        print(f"[OK] Passed: {self.results['tests_passed']}")
        print(f"[FAIL] Failed: {self.results['tests_failed']}")
        total = self.results['tests_passed'] + self.results['tests_failed']
        if total > 0:
            success_rate = (self.results['tests_passed'] / total) * 100
            print(f"[STATS] Success Rate: {success_rate:.1f}%")
        
        if self.results['errors']:
            print("\n[WARN] Errors encountered:")
            for err in self.results['errors']:
                print(f"  - {err}")
        
        self.save_results()
        
        return self.results['tests_failed'] == 0


if __name__ == "__main__":
    test_suite = LEDSystemTest()
    success = test_suite.run_all()
    sys.exit(0 if success else 1)
