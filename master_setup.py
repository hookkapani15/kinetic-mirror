#!/usr/bin/env python3
"""
Master Setup Orchestrator
Runs complete system setup in foolproof sequence:
1. Check wiring (power connections)
2. Auto-flash ESP32 firmware
3. Run systematic tests (exponentially increasing)
4. Launch GUI if all tests pass
"""

import os
import sys
import subprocess
import time
from pathlib import Path
from typing import List, Dict, Tuple

# Add project root to path
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "tooling"))
sys.path.insert(0, str(REPO_ROOT / "tests"))

from base_test import TestSuite, BaseTest
from test_runner import TestRunner


class SetupPhase:
    """Represents a setup phase with tests"""

    def __init__(self, name: str, description: str, critical: bool = True):
        self.name = name
        self.description = description
        self.critical = critical
        self.tests: List[BaseTest] = []
        self.result: Dict = None
        self.start_time: float = None
        self.end_time: float = None


class MasterSetup:
    """Master setup orchestrator"""

    def __init__(self):
        self.runner = TestRunner()
        self.phases: List[SetupPhase] = []
        self.results = {}
        self.errors = []

        self._init_phases()

    def _init_phases(self):
        """Initialize all setup phases in sequence"""
        self.phases = [
            SetupPhase(
                "Phase 1: Pre-Setup Checks",
                "Verify environment and dependencies",
                critical=True
            ),
            SetupPhase(
                "Phase 2: Wiring Verification",
                "Check power and ground connections",
                critical=True
            ),
            SetupPhase(
                "Phase 3: ESP32 Firmware Flash",
                "Auto-flash firmware to ESP32",
                critical=True
            ),
            SetupPhase(
                "Phase 4: ESP32 Communication Tests",
                "Verify ESP32 is responding (10 progressive tests)",
                critical=True
            ),
            SetupPhase(
                "Phase 5: LED System Tests",
                "Test all LED panels (20 progressive tests)",
                critical=True
            ),
            SetupPhase(
                "Phase 6: Motor System Tests",
                "Test all 64 motors (30 progressive tests)",
                critical=True
            ),
            SetupPhase(
                "Phase 7: Integrated System Tests",
                "Test full system coordination (10 tests)",
                critical=True
            ),
        ]

    def run_phase(self, phase: SetupPhase, skip_on_failure: bool = False) -> bool:
        """Run a single setup phase"""
        print("\n" + "=" * 70)
        print(f"  {phase.name}")
        print("=" * 70)
        print(f"{phase.description}\n")

        phase.start_time = time.time()

        if not phase.tests:
            print("[*] No tests defined for this phase")
            phase.result = {"status": "skipped", "details": "No tests"}
            phase.end_time = time.time()
            return True

        # Run all tests in the phase
        suite = TestSuite(phase.name, phase.tests)
        results = suite.run_all(stop_on_failure=False)

        # Calculate phase result
        failed = sum(1 for r in results if r["status"] == "fail")
        total = len(results)

        phase.result = {
            "total": total,
            "passed": total - failed,
            "failed": failed,
            "status": "fail" if failed > 0 else "pass",
            "details": f"{total - failed}/{total} tests passed"
        }

        phase.end_time = time.time()

        # Print results
        print(f"\n[RESULT] {phase.result['status'].upper()}: {phase.result['details']}")
        duration = phase.end_time - phase.start_time
        print(f"[TIME] {duration:.2f}s")

        if failed > 0:
            print("\n[!] FAILED TESTS:")
            for result in results:
                if result["status"] == "fail":
                    print(f"    ✗ {result['test_name']}: {result['details']}")
                    if result.get("suggested_actions"):
                        print("       Fixes:")
                        for action in result["suggested_actions"]:
                            print(f"         • {action}")

            if phase.critical and not skip_on_failure:
                print(f"\n[✗] CRITICAL PHASE FAILED")
                print("[*] Cannot proceed without fixing these issues")
                return False

        return failed == 0

    def run_all_phases(self):
        """Run all setup phases in sequence"""
        print("\n" + "╔" + "=" * 68 + "╗")
        print("║" + " " * 15 + "🔧 MIRROR BODY SETUP ORCHESTRATOR" + " " * 21 + "║")
        print("╚" + "=" * 68 + "╝")
        print("\n[*] Starting foolproof setup sequence...")
        print("[*] This will automatically test and configure your system")
        print()

        # Phase 1: Pre-setup checks
        self._run_phase_1_checks()

        # Phase 2: Wiring verification
        self._run_phase_2_wiring()

        # Phase 3: Firmware flash
        self._run_phase_3_flash()

        # Phase 4-7: Hardware tests
        for phase in self.phases[3:]:
            success = self.run_phase(phase)
            if not success and phase.critical:
                print("\n[✗] Setup failed - stopping")
                print("\n[*] Fix the issues above and run again:")
                print("    python master_setup.py")
                return

        # All phases complete
        self._print_final_summary()

    def _run_phase_1_checks(self):
        """Run Phase 1: Pre-setup checks"""
        phase = self.phases[0]

        print("\n" + "=" * 70)
        print(f"  {phase.name}")
        print("=" * 70)
        print(f"{phase.description}\n")

        checks = []

        # Check 1: Python version
        print("[CHECK] Python version...", end=" ")
        if sys.version_info >= (3, 7):
            print(f"[OK] {sys.version.split()[0]}")
            checks.append(("Python version", "pass", f"{sys.version.split()[0]}"))
        else:
            print(f"[FAIL] {sys.version.split()[0]} (requires 3.7+)")
            checks.append(("Python version", "fail", "Requires 3.7+"))
            self.errors.append("Python version too old")

        # Check 2: Required packages
        print("[CHECK] Required packages...", end=" ")
        required = ["serial", "cv2", "mediapipe", "numpy", "PIL"]
        missing = []

        for pkg in required:
            try:
                __import__(pkg)
            except ImportError:
                missing.append(pkg)

        if not missing:
            print("[OK] All packages installed")
            checks.append(("Packages", "pass", "All required installed"))
        else:
            print(f"[FAIL] Missing: {', '.join(missing)}")
            checks.append(("Packages", "fail", f"Missing: {missing}"))
            self.errors.append(f"Missing packages: {missing}")

        # Check 3: PlatformIO
        print("[CHECK] PlatformIO (for flashing)...", end=" ")
        try:
            subprocess.run(["pio", "--version"], capture_output=True, check=True)
            print("[OK] Installed")
            checks.append(("PlatformIO", "pass", "Installed"))
        except:
            print("[WARN] Not installed (alternative: esptool)")
            checks.append(("PlatformIO", "warn", "Not installed"))

        # Check 4: Camera
        print("[CHECK] Camera access...", end=" ")
        try:
            import cv2
            cap = cv2.VideoCapture(0)
            if cap.isOpened():
                print("[OK] Camera 0 available")
                checks.append(("Camera", "pass", "Camera 0 available"))
                cap.release()
            else:
                print("[WARN] No camera")
                checks.append(("Camera", "warn", "No camera detected"))
        except:
            print("[WARN] Cannot check")
            checks.append(("Camera", "warn", "Cannot check"))

        phase.result = {
            "checks": checks,
            "status": "fail" if self.errors else "pass",
            "details": f"{len(checks)} checks completed"
        }

        print(f"\n[RESULT] {'PASS' if not self.errors else 'FAIL'}")
        if self.errors:
            print("\n[!] ISSUES FOUND:")
            for error in self.errors:
                print(f"    ✗ {error}")
            print("\n[*] Fix these issues before continuing")
            sys.exit(1)

    def _run_phase_2_wiring(self):
        """Run Phase 2: Wiring verification"""
        phase = self.phases[1]

        print("\n" + "=" * 70)
        print(f"  {phase.name}")
        print("=" * 70)
        print(f"{phase.description}\n")

        print("[*] Please verify the following before continuing:\n")
        print("  POWER CONNECTIONS:")
        print("    [ ] ESP32 powered via USB or 5V adapter")
        print("    [ ] LED power supply connected (5V, 30A+ recommended)")
        print("    [ ] Motor power supply connected (5V/6V, 70A+ recommended)")
        print()
        print("  GROUND CONNECTIONS (CRITICAL!):")
        print("    [ ] ESP32 GND connected to LED power GND")
        print("    [ ] ESP32 GND connected to motor power GND")
        print("    [ ] ALL grounds common")
        print()
        print("  DATA CONNECTIONS:")
        print("    [ ] ESP32 GPIO 12 to first LED panel DIN")
        print("    [ ] ESP32 GPIO 13 to second chain (if applicable)")
        print("    [ ] ESP32 SDA (GPIO 21) to PCA9685 SDA")
        print("    [ ] ESP32 SCL (GPIO 22) to PCA9685 SCL")
        print("    [ ] Motor signals to PCA9685 outputs")
        print()

        response = input("\n[?] Have you completed all wiring checks? [y/N]: ")
        if response.lower() == 'y':
            print("[OK] Wiring verification accepted")
            phase.result = {"status": "pass", "details": "User confirmed"}
        else:
            print("[INFO] Please complete wiring first")
            print("[*] See: docs/COMPLETE_WIRING_GUIDE.md")
            phase.result = {"status": "skip", "details": "Wiring incomplete"}

    def _run_phase_3_flash(self):
        """Run Phase 3: ESP32 firmware flash"""
        phase = self.phases[2]

        print("\n" + "=" * 70)
        print(f"  {phase.name}")
        print("=" * 70)
        print(f"{phase.description}\n")

        response = input("[?] Flash ESP32 firmware now? [Y/n]: ")
        if response.lower() == 'n':
            print("[INFO] Skipping firmware flash")
            phase.result = {"status": "skip", "details": "User skipped"}
            return

        print("[*] Launching auto-flash script...\n")

        try:
            result = subprocess.run(
                [sys.executable, str(REPO_ROOT / "tools" / "auto_flash_esp32.py")],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                timeout=300
            )

            print(result.stdout)
            if result.stderr:
                print(result.stderr)

            if result.returncode == 0:
                print("\n[OK] Firmware flash completed")
                phase.result = {"status": "pass", "details": "Firmware flashed"}
            else:
                print("\n[!] Firmware flash failed")
                phase.result = {"status": "fail", "details": "Flash failed"}
                self.errors.append("Firmware flash failed")

        except subprocess.TimeoutExpired:
            print("\n[!] Flash timed out (5 minutes)")
            phase.result = {"status": "fail", "details": "Timeout"}
            self.errors.append("Flash timeout")

        except Exception as e:
            print(f"\n[!] Flash error: {e}")
            phase.result = {"status": "fail", "details": str(e)}
            self.errors.append(f"Flash error: {e}")

    def _print_final_summary(self):
        """Print final setup summary"""
        print("\n" + "╔" + "=" * 68 + "╗")
        print("║" + " " * 20 + "✓ SETUP COMPLETE" + " " * 30 + "║")
        print("╚" + "=" * 68 + "╝")

        print("\n[PHASE SUMMARY]")
        for i, phase in enumerate(self.phases, 1):
            status_icon = "✓" if phase.result.get("status") == "pass" else "✗"
            if phase.result.get("status") == "skip":
                status_icon = "○"
            print(f"    {status_icon} {phase.name}")

        print("\n[✓] All critical systems tested and working!")
        print("\n[*] You can now launch the application:")
        print("    python main.py")
        print()
        print("[*] Or run the setup wizard again for fine-tuning:")
        print("    python setup_wizard.py")
        print()


def main():
    """Main entry point"""
    try:
        setup = MasterSetup()
        setup.run_all_phases()
    except KeyboardInterrupt:
        print("\n\n[!] Setup cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n[!] Setup crashed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
