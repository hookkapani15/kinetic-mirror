#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive LED Test Suite
20 progressive tests covering all LED scenarios
Tests individual LEDs, patterns, colors, and full system
"""

import sys
import time
import serial
from pathlib import Path

# Add project root to path
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tooling"))
sys.path.insert(0, str(REPO_ROOT / "packages"))

from base_test import BaseTest
try:
    from packages.mirror_core.controllers.led_controller import LEDController
except:
    LEDController = None


# ============================================================================
# TEST 1: LED Controller Initialization
# ============================================================================

class LEDInit(BaseTest):
    """Test 1: Initialize LED controller"""

    def __init__(self):
        super().__init__("LED: Controller Initialization")
        self.controller = None

    def run(self):
        if LEDController is None:
            return self.fail_test(
                "LEDController module not found",
                suggested_actions=[
                    "Check packages/mirror_core/ is in path",
                    "Verify led_controller.py exists"
                ]
            )

        try:
            self.controller = LEDController(width=32, height=64)
            return self.pass_test(
                "LED controller initialized",
                metrics={
                    "width": self.controller.width,
                    "height": self.controller.height,
                    "total_leds": self.controller.width * self.controller.height
                }
            )
        except Exception as e:
            return self.fail_test(
                f"Init failed: {str(e)}",
                suggested_actions=[
                    "Check LEDController constructor",
                    "Verify dimensions are valid"
                ]
            )


# ============================================================================
# TEST 2: Single LED Test
# ============================================================================

class LEDSingleTest(BaseTest):
    """Test 2: Set single LED"""

    def __init__(self, controller):
        super().__init__("LED: Single LED Control")
        self.controller = controller

    def run(self):
        if not self.controller:
            return self.skip_test("No controller")

        try:
            # Set LED at position (0,0) to red
            self.controller.set_pixel(0, 0, 255, 0, 0)
            return self.pass_test(
                "Single LED set successfully",
                metrics={"x": 0, "y": 0, "r": 255, "g": 0, "b": 0}
            )
        except Exception as e:
            return self.fail_test(
                f"Single LED failed: {str(e)}",
                suggested_actions=[
                    "Check set_pixel method",
                    "Verify coordinate system"
                ]
            )


# ============================================================================
# TEST 3: Color Depth Test
# ============================================================================

class LEDColorDepth(BaseTest):
    """Test 3: Test different color depths"""

    def __init__(self, controller):
        super().__init__("LED: Color Depth Test")
        self.controller = controller

    def run(self):
        if not self.controller:
            return self.skip_test("No controller")

        try:
            colors = [
                (0, 0, 0),      # Black
                (255, 0, 0),    # Red
                (0, 255, 0),    # Green
                (0, 0, 255),    # Blue
                (255, 255, 255), # White
                (128, 128, 128), # Gray
            ]

            for i, (r, g, b) in enumerate(colors):
                self.controller.set_pixel(i, 0, r, g, b)

            return self.pass_test(
                f"Color depth tested ({len(colors)} colors)",
                metrics={"colors_tested": len(colors)}
            )
        except Exception as e:
            return self.fail_test(
                f"Color depth failed: {str(e)}"
            )


# ============================================================================
# TEST 4: Gradient Test
# ============================================================================

class LEDGradient(BaseTest):
    """Test 4: Create color gradient"""

    def __init__(self, controller):
        super().__init__("LED: Gradient Pattern")
        self.controller = controller

    def run(self):
        if not self.controller:
            return self.skip_test("No controller")

        try:
            # Create red gradient
            for x in range(32):
                intensity = int((x / 31) * 255)
                self.controller.set_pixel(x, 0, intensity, 0, 0)

            return self.pass_test(
                "Gradient pattern created",
                metrics={"gradient_steps": 32}
            )
        except Exception as e:
            return self.fail_test(
                f"Gradient failed: {str(e)}"
            )


# ============================================================================
# TEST 5: Row Test
# ============================================================================

class LEDRowTest(BaseTest):
    """Test 5: Set entire row"""

    def __init__(self, controller):
        super().__init__("LED: Row Control")
        self.controller = controller

    def run(self):
        if not self.controller:
            return self.skip_test("No controller")

        try:
            # Set row 0 to white
            self.controller.set_row(0, 255, 255, 255)
            return self.pass_test(
                "Row set successfully",
                metrics={"row": 0, "leds": 32}
            )
        except Exception as e:
            return self.fail_test(
                f"Row set failed: {str(e)}",
                suggested_actions=[
                    "Check set_row method",
                    "Verify row indexing"
                ]
            )


# ============================================================================
# TEST 6: Column Test
# ============================================================================

class LEDColumnTest(BaseTest):
    """Test 6: Set entire column"""

    def __init__(self, controller):
        super().__init__("LED: Column Control")
        self.controller = controller

    def run(self):
        if not self.controller:
            return self.skip_test("No controller")

        try:
            # Set column 0 to blue
            self.controller.set_column(0, 0, 0, 255)
            return self.pass_test(
                "Column set successfully",
                metrics={"column": 0, "leds": 64}
            )
        except Exception as e:
            return self.fail_test(
                f"Column set failed: {str(e)}"
            )


# ============================================================================
# TEST 7: Rectangle Fill Test
# ============================================================================

class LEDRectangle(BaseTest):
    """Test 7: Fill rectangle"""

    def __init__(self, controller):
        super().__init__("LED: Rectangle Fill")
        self.controller = controller

    def run(self):
        if not self.controller:
            return self.skip_test("No controller")

        try:
            # Fill 10x10 rectangle with green
            self.controller.fill_rect(5, 5, 15, 15, 0, 255, 0)
            return self.pass_test(
                "Rectangle filled",
                metrics={"x1": 5, "y1": 5, "x2": 15, "y2": 15}
            )
        except Exception as e:
            return self.fail_test(
                f"Rectangle fill failed: {str(e)}"
            )


# ============================================================================
# TEST 8: Full Screen Test
# ============================================================================

class LEDFullScreen(BaseTest):
    """Test 8: Fill entire screen"""

    def __init__(self, controller):
        super().__init__("LED: Full Screen Fill")
        self.controller = controller

    def run(self):
        if not self.controller:
            return self.skip_test("No controller")

        try:
            # Fill entire screen with red
            self.controller.fill(255, 0, 0)
            return self.pass_test(
                "Full screen filled",
                metrics={
                    "width": self.controller.width,
                    "height": self.controller.height,
                    "total_leds": self.controller.width * self.controller.height
                }
            )
        except Exception as e:
            return self.fail_test(
                f"Full screen fill failed: {str(e)}"
            )


# ============================================================================
# TEST 9: Clear Screen Test
# ============================================================================

class LEDClear(BaseTest):
    """Test 9: Clear screen"""

    def __init__(self, controller):
        super().__init__("LED: Clear Screen")
        self.controller = controller

    def run(self):
        if not self.controller:
            return self.skip_test("No controller")

        try:
            # Fill first, then clear
            self.controller.fill(255, 0, 0)
            self.controller.clear()
            return self.pass_test(
                "Screen cleared successfully"
            )
        except Exception as e:
            return self.fail_test(
                f"Clear failed: {str(e)}"
            )


# ============================================================================
# TEST 10: Serial Communication Test
# ============================================================================

class LEDSerialComm(BaseTest):
    """Test 10: Serial communication to ESP32"""

    def __init__(self, controller, port=None):
        super().__init__("LED: Serial Communication")
        self.controller = controller
        self.port = port

    def run(self):
        if not self.controller:
            return self.skip_test("No controller")

        if not self.port:
            return self.skip_test("No serial port configured")

        try:
            # Create test pattern
            self.controller.fill(100, 100, 100)

            # Send to ESP32
            success = self.controller.send_to_esp32()

            if success:
                return self.pass_test(
                    "LED data sent to ESP32",
                    metrics={"port": self.port}
                )
            else:
                return self.fail_test(
                    "Failed to send LED data",
                    suggested_actions=[
                        "Check ESP32 connection",
                        "Verify port is open",
                        "Check baud rate"
                    ]
                )
        except Exception as e:
            return self.fail_test(
                f"Serial comm failed: {str(e)}"
            )


# ============================================================================
# TEST 11: Pattern - Checkerboard
# ============================================================================

class LEDPatternCheckerboard(BaseTest):
    """Test 11: Checkerboard pattern"""

    def __init__(self, controller):
        super().__init__("LED: Pattern - Checkerboard")
        self.controller = controller

    def run(self):
        if not self.controller:
            return self.skip_test("No controller")

        try:
            for y in range(self.controller.height):
                for x in range(self.controller.width):
                    if (x + y) % 2 == 0:
                        self.controller.set_pixel(x, y, 255, 255, 255)
                    else:
                        self.controller.set_pixel(x, y, 0, 0, 0)

            return self.pass_test(
                "Checkerboard pattern created"
            )
        except Exception as e:
            return self.fail_test(
                f"Checkerboard failed: {str(e)}"
            )


# ============================================================================
# TEST 12: Pattern - Diagonal
# ============================================================================

class LEDPatternDiagonal(BaseTest):
    """Test 12: Diagonal line pattern"""

    def __init__(self, controller):
        super().__init__("LED: Pattern - Diagonal")
        self.controller = controller

    def run(self):
        if not self.controller:
            return self.skip_test("No controller")

        try:
            # Draw diagonal from top-left to bottom-right
            min_dim = min(self.controller.width, self.controller.height)
            for i in range(min_dim):
                self.controller.set_pixel(i, i, 255, 0, 0)

            return self.pass_test(
                "Diagonal pattern created",
                metrics={"length": min_dim}
            )
        except Exception as e:
            return self.fail_test(
                f"Diagonal failed: {str(e)}"
            )


# ============================================================================
# TEST 13: Pattern - Circle
# ============================================================================

class LEDPatternCircle(BaseTest):
    """Test 13: Circle pattern"""

    def __init__(self, controller):
        super().__init__("LED: Pattern - Circle")
        self.controller = controller

    def run(self):
        if not self.controller:
            return self.skip_test("No controller")

        try:
            import math
            cx, cy = self.controller.width // 2, self.controller.height // 2
            radius = min(cx, cy) - 2

            for angle in range(0, 360, 10):
                rad = math.radians(angle)
                x = int(cx + radius * math.cos(rad))
                y = int(cy + radius * math.sin(rad))
                if 0 <= x < self.controller.width and 0 <= y < self.controller.height:
                    self.controller.set_pixel(x, y, 0, 255, 0)

            return self.pass_test(
                "Circle pattern created",
                metrics={"radius": radius}
            )
        except Exception as e:
            return self.fail_test(
                f"Circle failed: {str(e)}"
            )


# ============================================================================
# TEST 14: Frame Rate Test
# ============================================================================

class LEDFrameRate(BaseTest):
    """Test 14: Frame rate performance"""

    def __init__(self, controller):
        super().__init__("LED: Frame Rate Test")
        self.controller = controller

    def run(self):
        if not self.controller:
            return self.skip_test("No controller")

        try:
            # Run 50 frame updates
            frames = 50
            start_time = time.time()

            for i in range(frames):
                self.controller.fill(i * 5 % 256, i * 3 % 256, i * 7 % 256)

            elapsed = time.time() - start_time
            fps = frames / elapsed

            if fps > 30:
                return self.pass_test(
                    f"Frame rate: {fps:.1f} FPS",
                    metrics={"frames": frames, "time": elapsed, "fps": fps}
                )
            else:
                return self.fail_test(
                    f"Frame rate too low: {fps:.1f} FPS",
                    suggested_actions=[
                        "Optimize LED controller code",
                        "Check for bottlenecks",
                        "Consider using lower resolution"
                    ],
                    metrics={"fps": fps}
                )
        except Exception as e:
            return self.fail_test(
                f"Frame rate test failed: {str(e)}"
            )


# ============================================================================
# TEST 15: Brightness Test
# ============================================================================

class LEDBrightness(BaseTest):
    """Test 15: Brightness control"""

    def __init__(self, controller):
        super().__init__("LED: Brightness Control")
        self.controller = controller

    def run(self):
        if not self.controller:
            return self.skip_test("No controller")

        try:
            # Test different brightness levels
            brightness_levels = [25, 50, 75, 100, 150, 200, 255]

            for i, brightness in enumerate(brightness_levels):
                self.controller.fill(brightness, brightness, brightness)
                time.sleep(0.1)

            return self.pass_test(
                f"Brightness control tested ({len(brightness_levels)} levels)",
                metrics={"levels": len(brightness_levels)}
            )
        except Exception as e:
            return self.fail_test(
                f"Brightness test failed: {str(e)}"
            )


# ============================================================================
# TEST 16: RGB Mixing Test
# ============================================================================

class LEDRGBMixing(BaseTest):
    """Test 16: RGB color mixing"""

    def __init__(self, controller):
        super().__init__("LED: RGB Color Mixing")
        self.controller = controller

    def run(self):
        if not self.controller:
            return self.skip_test("No controller")

        try:
            # Test color transitions
            colors = [
                (255, 0, 0),    # Red
                (255, 255, 0),  # Yellow
                (0, 255, 0),    # Green
                (0, 255, 255),  # Cyan
                (0, 0, 255),    # Blue
                (255, 0, 255),  # Magenta
                (255, 0, 0),    # Back to red
            ]

            for i, (r, g, b) in enumerate(colors):
                self.controller.fill(r, g, b)
                time.sleep(0.2)

            return self.pass_test(
                "RGB mixing tested",
                metrics={"transitions": len(colors)}
            )
        except Exception as e:
            return self.fail_test(
                f"RGB mixing failed: {str(e)}"
            )


# ============================================================================
# TEST 17: Memory Test
# ============================================================================

class LEDMemory(BaseTest):
    """Test 17: Memory usage test"""

    def __init__(self, controller):
        super().__init__("LED: Memory Usage")
        self.controller = controller

    def run(self):
        if not self.controller:
            return self.skip_test("No controller")

        try:
            import sys

            # Get memory before
            mem_before = sys.getsizeof(self.controller.leds) if hasattr(self.controller, 'leds') else 0

            # Create multiple patterns
            for i in range(10):
                self.controller.fill(i * 25, i * 25, i * 25)

            # Get memory after
            mem_after = sys.getsizeof(self.controller.leds) if hasattr(self.controller, 'leds') else 0

            return self.pass_test(
                f"Memory test passed",
                metrics={
                    "memory_before": mem_before,
                    "memory_after": mem_after,
                    "delta": mem_after - mem_before
                }
            )
        except Exception as e:
            return self.fail_test(
                f"Memory test failed: {str(e)}"
            )


# ============================================================================
# TEST 18: Error Handling Test
# ============================================================================

class LEDErrorHandling(BaseTest):
    """Test 18: Error handling"""

    def __init__(self, controller):
        super().__init__("LED: Error Handling")
        self.controller = controller

    def run(self):
        if not self.controller:
            return self.skip_test("No controller")

        try:
            # Test out of bounds access
            try:
                self.controller.set_pixel(-1, 0, 255, 0, 0)
                return self.fail_test(
                    "Should have thrown error for negative coordinate"
                )
            except:
                pass  # Expected

            try:
                self.controller.set_pixel(999, 999, 255, 0, 0)
                return self.fail_test(
                    "Should have thrown error for out of bounds"
                )
            except:
                pass  # Expected

            return self.pass_test(
                "Error handling working correctly"
            )
        except Exception as e:
            return self.fail_test(
                f"Error handling test failed: {str(e)}"
            )


# ============================================================================
# TEST 19: Animation Test
# ============================================================================

class LEDAnimation(BaseTest):
    """Test 19: Simple animation"""

    def __init__(self, controller):
        super().__init__("LED: Simple Animation")
        self.controller = controller

    def run(self):
        if not self.controller:
            return self.skip_test("No controller")

        try:
            # Create scanning line animation
            frames = 20
            start_time = time.time()

            for i in range(frames):
                self.controller.clear()
                x = (i * 32) // frames
                self.controller.set_column(x, 255, 255, 255)
                time.sleep(0.05)

            elapsed = time.time() - start_time

            return self.pass_test(
                f"Animation test passed ({frames} frames)",
                metrics={"frames": frames, "time": elapsed}
            )
        except Exception as e:
            return self.fail_test(
                f"Animation test failed: {str(e)}"
            )


# ============================================================================
# TEST 20: Integration Test
# ============================================================================

class LEDIntegration(BaseTest):
    """Test 20: Full integration test"""

    def __init__(self, controller, port=None):
        super().__init__("LED: Full Integration")
        self.controller = controller
        self.port = port

    def run(self):
        if not self.controller:
            return self.skip_test("No controller")

        try:
            # Complete workflow test
            operations = []

            # 1. Clear
            self.controller.clear()
            operations.append("clear")

            # 2. Draw pattern
            for y in range(self.controller.height):
                for x in range(self.controller.width):
                    if (x + y) % 2 == 0:
                        self.controller.set_pixel(x, y, 255, 255, 255)
            operations.append("pattern")

            # 3. Send to ESP32
            if self.port:
                self.controller.send_to_esp32()
                operations.append("transmit")

            # 4. Clear
            self.controller.clear()
            operations.append("clear")

            return self.pass_test(
                f"Integration test passed ({len(operations)} operations)",
                metrics={"operations": operations}
            )
        except Exception as e:
            return self.fail_test(
                f"Integration test failed: {str(e)}",
                suggested_actions=[
                    "Review all LED operations",
                    "Check serial transmission",
                    "Verify ESP32 firmware"
                ]
            )


# ============================================================================
# Main - Run all tests
# ============================================================================

if __name__ == "__main__":
    from base_test import TestSuite

    # Create controller
    controller = None
    try:
        controller = LEDController(width=32, height=64)
    except Exception as e:
        print(f"[!] Cannot create LED controller: {e}")
        sys.exit(1)

    # Get port
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
    suite = TestSuite("Comprehensive LED Test Suite")

    tests = [
        LEDInit(),
        LEDSingleTest(controller),
        LEDColorDepth(controller),
        LEDGradient(controller),
        LEDRowTest(controller),
        LEDColumnTest(controller),
        LEDRectangle(controller),
        LEDFullScreen(controller),
        LEDClear(controller),
        LEDSerialComm(controller, port),
        LEDPatternCheckerboard(controller),
        LEDPatternDiagonal(controller),
        LEDPatternCircle(controller),
        LEDFrameRate(controller),
        LEDBrightness(controller),
        LEDRGBMixing(controller),
        LEDMemory(controller),
        LEDErrorHandling(controller),
        LEDAnimation(controller),
        LEDIntegration(controller, port),
    ]

    for test in tests:
        suite.add_test(test)

    # Run tests
    print("\n" + "=" * 70)
    print("  COMPREHENSIVE LED TEST SUITE (20 TESTS)")
    print("=" * 70)
    print()

    results = suite.run_all()
    suite.print_summary()
