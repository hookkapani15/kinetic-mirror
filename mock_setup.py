#!/usr/bin/env python3
"""
Mock Setup Simulator
Demonstrates the full setup flow without actual hardware
Perfect for testing the setup system before you have all the hardware
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import time
import threading
from pathlib import Path

# Add project root to path
REPO_ROOT = Path(__file__).resolve().parents[1]


class MockSetupLauncher:
    """Mock setup that simulates all steps without hardware"""

    def __init__(self, root):
        self.root = root
        self.root.title("🔧 Mock Setup Simulator (No Hardware Required)")
        self.root.geometry("800x700")
        self.root.resizable(False, False)

        self.current_step = 0
        self.total_steps = 7
        self.steps = [
            "Welcome to Mock Setup",
            "Install Dependencies (Simulated)",
            "Check Wiring (Visual Guide)",
            "Flash ESP32 Firmware (Simulated)",
            "Run ESP32 Tests (Simulated)",
            "Run LED Tests (Simulated)",
            "Run Motor Tests (Simulated)",
        ]

        self.create_widgets()
        self.show_welcome()

    def create_widgets(self):
        """Create GUI elements"""
        # Header
        header_frame = ttk.Frame(self.root, padding=10)
        header_frame.pack(fill=tk.X)

        title = ttk.Label(
            header_frame,
            text="🔧 MOCK SETUP SIMULATOR",
            font=("Arial", 16, "bold"),
            foreground="blue"
        )
        title.pack(side=tk.LEFT)

        note = ttk.Label(
            header_frame,
            text="(No Hardware Required)",
            font=("Arial", 10, "italic")
        )
        note.pack(side=tk.RIGHT)

        # Progress
        progress_frame = ttk.Frame(self.root, padding=10)
        progress_frame.pack(fill=tk.X)

        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=self.total_steps,
            length=760
        )
        self.progress_bar.pack(fill=tk.X)

        self.progress_label = ttk.Label(
            progress_frame,
            text=f"Step 0/{self.total_steps}: Getting started..."
        )
        self.progress_label.pack(pady=5)

        # Main content
        self.content_frame = ttk.Frame(self.root, padding=10)
        self.content_frame.pack(fill=tk.BOTH, expand=True)

        # Log output
        log_frame = ttk.LabelFrame(self.root, text="Setup Log (Simulated)", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=12,
            state='disabled',
            font=("Consolas", 9)
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # Buttons
        button_frame = ttk.Frame(self.root, padding=10)
        button_frame.pack(fill=tk.X)

        self.back_btn = ttk.Button(
            button_frame,
            text="← Back",
            command=self.back_step,
            state='disabled'
        )
        self.back_btn.pack(side=tk.LEFT, padx=5)

        self.next_btn = ttk.Button(
            button_frame,
            text="Start Mock Setup →",
            command=self.next_step
        )
        self.next_btn.pack(side=tk.RIGHT, padx=5)

    def log(self, message):
        """Add message to log"""
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')
        self.root.update()

    def update_progress(self):
        """Update progress bar"""
        self.progress_var.set(self.current_step)
        step_name = self.steps[self.current_step] if self.current_step < len(self.steps) else "Complete"
        self.progress_label.config(text=f"Step {self.current_step}/{self.total_steps}: {step_name}")
        self.root.update()

    def clear_content(self):
        """Clear content frame"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def show_welcome(self):
        """Show welcome screen"""
        self.clear_content()

        welcome_text = """
        ╔════════════════════════════════════════════════════════════╗
        ║                                                              ║
        ║        Welcome to MOCK SETUP SIMULATOR!                        ║
        ║                                                              ║
        ║        This simulates the complete setup process WITHOUT          ║
        ║        needing any physical hardware!                          ║
        ║                                                              ║
        ║        You'll see:                                           ║
        ║                                                              ║
        ║        ✓ How dependencies would be installed                    ║
        ║        ✓ How firmware would be flashed                        ║
        ║        ✓ How 60 tests would run                               ║
        ║        ✓ What the real setup experience is like                ║
        ║                                                              ║
        ║        Perfect for:                                           ║
        ║        - Understanding the setup flow                           ║
        ║        - Testing the setup system                              ║
        ║        - Learning what to expect with real hardware             ║
        ║                                                              ║
        ╚════════════════════════════════════════════════════════════╝
        """

        ttk.Label(
            self.content_frame,
            text=welcome_text,
            font=("Consolas", 10),
            justify=tk.CENTER
        ).pack(pady=20)

        ttk.Label(
            self.content_frame,
            text="🔮 This is a SIMULATION - No actual hardware needed!",
            font=("Arial", 12, "bold"),
            foreground="orange"
        ).pack(pady=10)

        self.back_btn.config(state='disabled')
        self.next_btn.config(text="Start Mock Setup →")

    def step_dependencies(self):
        """Step 1: Dependencies (simulated)"""
        self.clear_content()

        ttk.Label(
            self.content_frame,
            text="📦 Installing Dependencies (Simulated)",
            font=("Arial", 14, "bold")
        ).pack(pady=10)

        ttk.Label(
            self.content_frame,
            text="In real setup, these packages would be installed:",
            font=("Arial", 10)
        ).pack(pady=5)

        packages = [
            "pyserial - ESP32 communication",
            "opencv-python - Camera input",
            "mediapipe - AI body tracking",
            "pillow - Image processing",
            "numpy - Calculations"
        ]

        for pkg in packages:
            ttk.Label(self.content_frame, text=f"  • {pkg}").pack()

        ttk.Button(
            self.content_frame,
            text="Simulate Installation",
            command=self.run_dependencies_simulation
        ).pack(pady=20)

    def run_dependencies_simulation(self):
        """Simulate dependency installation"""
        self.log("\n" + "="*70)
        self.log("SIMULATING DEPENDENCY INSTALLATION")
        self.log("="*70 + "\n")

        packages = [
            ("pyserial", "3.5"),
            ("opencv-python", "4.9.0"),
            ("mediapipe", "0.10.31"),
            ("pillow", "10.0.0"),
            ("numpy", "1.26.4")
        ]

        for pkg, version in packages:
            self.log(f"[*] Installing {pkg}...")
            time.sleep(0.3)
            self.log(f"[OK] {pkg} {version} installed successfully")
            self.root.update()

        self.log("\n[OK] All dependencies installed!")
        self.log("\n[?] Click 'Next' to continue...")

        self.next_btn.config(state='normal', text="Next Step →")

    def step_wiring(self):
        """Step 2: Wiring check"""
        self.clear_content()

        ttk.Label(
            self.content_frame,
            text="🔌 Wiring Verification",
            font=("Arial", 14, "bold")
        ).pack(pady=10)

        ttk.Label(
            self.content_frame,
            text="In real setup, you would verify this wiring:",
            font=("Arial", 10)
        ).pack(pady=5)

        checklist = ttk.LabelFrame(self.content_frame, text="Wiring Checklist", padding=10)
        checklist.pack(fill=tk.X, pady=20, padx=50)

        checks = [
            "✓ ESP32 connected via USB (will auto-detect)",
            "✓ LED power supply (5V, 30A+)",
            "✓ Motor power supply (5V/6V, 70A+)",
            "✓ ALL GROUNDS connected together",
            "✓ ESP32 GPIO 12 to LED panel DIN",
            "✓ ESP32 SDA/SCL to PCA9685",
            "✓ Motor signals to PCA9685"
        ]

        for check in checks:
            ttk.Label(checklist, text=check).pack(anchor=tk.W, pady=2)

        ttk.Button(
            checklist,
            text="📖 Open Full Wiring Guide",
            command=self.open_wiring_guide
        ).pack(pady=10)

    def open_wiring_guide(self):
        """Open wiring guide"""
        guide_path = REPO_ROOT / "docs" / "COMPLETE_WIRING_GUIDE.md"
        if guide_path.exists():
            import os
            os.startfile(guide_path)
        else:
            messagebox.showinfo("Info", "Wiring guide available at: docs/COMPLETE_WIRING_GUIDE.md")

    def step_flash_firmware(self):
        """Step 3: Flash firmware (simulated)"""
        self.clear_content()

        ttk.Label(
            self.content_frame,
            text="⚡ Flash ESP32 Firmware (Simulated)",
            font=("Arial", 14, "bold")
        ).pack(pady=10)

        ttk.Label(
            self.content_frame,
            text="In real setup, this would:",
            font=("Arial", 10)
        ).pack(pady=5)

        info_frame = ttk.LabelFrame(self.content_frame, text="Auto-Flash Process:", padding=10)
        info_frame.pack(fill=tk.X, pady=20, padx=50)

        steps = [
            "1. Auto-detect ESP32 USB connection",
            "2. Build firmware with PlatformIO (if needed)",
            "3. Upload firmware via esptool/PlatformIO",
            "4. Verify communication with PING/PONG",
            "5. Report success/failure with details"
        ]

        for step in steps:
            ttk.Label(info_frame, text=f"  {step}").pack(anchor=tk.W, pady=2)

        ttk.Button(
            self.content_frame,
            text="Simulate Flashing",
            command=self.run_flash_simulation
        ).pack(pady=20)

    def run_flash_simulation(self):
        """Simulate firmware flashing"""
        self.log("\n" + "="*70)
        self.log("SIMULATING ESP32 FIRMWARE FLASH")
        self.log("="*70 + "\n")

        self.log("[*] Scanning for ESP32...")
        time.sleep(0.5)
        self.log("[OK] ESP32 detected on COM3 (simulated)")
        self.log()

        self.log("[*] Checking for firmware...")
        time.sleep(0.3)
        self.log("[OK] Found firmware.bin (simulated)")
        self.log()

        self.log("[*] Uploading firmware (using esptool)...")
        time.sleep(1.0)
        self.log("[OK] Firmware uploaded successfully!")
        self.log()

        self.log("[*] Verifying communication...")
        time.sleep(0.3)
        self.log("[OK] ESP32 responded: PONG")
        self.log()

        self.log("[OK] Firmware flash complete!")
        self.log("\n[?] Click 'Next' to continue...")

        self.next_btn.config(state='normal', text="Next Step →")

    def step_esp_tests(self):
        """Step 4: ESP32 tests (simulated)"""
        self.clear_content()

        ttk.Label(
            self.content_frame,
            text="🧪 ESP32 Tests (Simulated)",
            font=("Arial", 14, "bold")
        ).pack(pady=10)

        ttk.Label(
            self.content_frame,
            text="Would run 10 progressive tests in real setup:",
            font=("Arial", 10)
        ).pack(pady=5)

        test_list = ttk.LabelFrame(self.content_frame, text="10 ESP32 Tests:", padding=10)
        test_list.pack(fill=tk.BOTH, expand=True, pady=20, padx=50)

        tests = [
            ("1", "Basic Connection", "✓ Check ESP32 serial connection"),
            ("2", "Command Responsiveness", "✓ ESP32 responds to PING"),
            ("3", "LED Communication", "✓ Can send LED data"),
            ("4", "Motor Communication", "✓ Can send motor commands"),
            ("5", "LED Data Integrity", "✓ LED packets arrive correctly"),
            ("6", "Motor Command Integrity", "✓ Motor commands work"),
            ("7", "Speed/Stress Test", "✓ Handle 100 packets/sec"),
            ("8", "Error Recovery", "✓ Recover from errors"),
            ("9", "Multi-Channel Test", "✓ Both LED channels work"),
            ("10", "Long-Run Stability", "✓ Stable for 15 seconds")
        ]

        for num, name, desc in tests:
            frame = ttk.Frame(test_list)
            frame.pack(fill=tk.X, pady=2)
            ttk.Label(frame, text=f"{num}.", width=3).pack(side=tk.LEFT)
            ttk.Label(frame, text=f"{name}", width=25, font=("Arial", 9, "bold")).pack(side=tk.LEFT)
            ttk.Label(frame, text=desc, foreground="green").pack(side=tk.LEFT)

        ttk.Button(
            self.content_frame,
            text="Simulate ESP32 Tests",
            command=self.run_esp_tests_simulation
        ).pack(pady=20)

    def run_esp_tests_simulation(self):
        """Simulate ESP32 tests"""
        self.log("\n" + "="*70)
        self.log("SIMULATING 10 ESP32 TESTS")
        self.log("="*70 + "\n")

        tests = [
            ("Basic Connection", "✓ PASS", "Connected to ESP32 on COM3"),
            ("Command Responsiveness", "✓ PASS", "ESP32 responded: PONG"),
            ("LED Communication", "✓ PASS", "LED data transmission OK"),
            ("Motor Communication", "✓ PASS", "Motor commands OK"),
            ("LED Data Integrity", "✓ PASS", "100% data integrity"),
            ("Motor Command Integrity", "✓ PASS", "All commands executed"),
            ("Speed/Stress Test", "✓ PASS", "15.2 packets/sec"),
            ("Error Recovery", "✓ PASS", "Recovered from invalid command"),
            ("Multi-Channel Test", "✓ PASS", "Both channels working"),
            ("Long-Run Stability", "✓ PASS", "Stable for 15s, 0 errors")
        ]

        for test_name, status, details in tests:
            self.log(f"Running: {test_name}...", end=" ")
            time.sleep(0.2)
            self.log(f"{status}")
            if details:
                self.log(f"    Details: {details}")
            self.root.update()

        self.log(f"\n[OK] All 10 ESP32 tests passed!")
        self.log("\n[?] Click 'Next' to continue...")

        self.next_btn.config(state='normal', text="Next Step →")

    def step_led_tests(self):
        """Step 5: LED tests (simulated)"""
        self.clear_content()

        ttk.Label(
            self.content_frame,
            text="💡 LED Tests (Simulated)",
            font=("Arial", 14, "bold")
        ).pack(pady=10)

        ttk.Label(
            self.content_frame,
            text="Would run 20 progressive tests in real setup:",
            font=("Arial", 10)
        ).pack(pady=5)

        test_list = ttk.LabelFrame(self.content_frame, text="20 LED Tests:", padding=10)
        test_list.pack(fill=tk.BOTH, expand=True, pady=20, padx=50)

        tests = [
            "1. Controller Initialization",
            "2. Single LED Control",
            "3. Color Depth (6 colors)",
            "4. Gradient Pattern",
            "5. Row Control",
            "6. Column Control",
            "7. Rectangle Fill",
            "8. Full Screen (2048 LEDs)",
            "9. Clear Screen",
            "10. Serial to ESP32",
            "11. Checkerboard Pattern",
            "12. Diagonal Line",
            "13. Circle Pattern",
            "14. Frame Rate Test",
            "15. Brightness Control",
            "16. RGB Color Mixing",
            "17. Memory Usage",
            "18. Error Handling",
            "19. Simple Animation",
            "20. Full Integration"
        ]

        for test in tests:
            ttk.Label(test_list, text=f"  • {test}").pack(anchor=tk.W, pady=1)

        ttk.Button(
            self.content_frame,
            text="Simulate LED Tests",
            command=self.run_led_tests_simulation
        ).pack(pady=20)

    def run_led_tests_simulation(self):
        """Simulate LED tests"""
        self.log("\n" + "="*70)
        self.log("SIMULATING 20 LED TESTS")
        self.log("="*70 + "\n")

        tests = [
            ("Controller Initialization", "✓ PASS", "32x64 = 2048 LEDs ready"),
            ("Single LED", "✓ PASS", "Pixel (0,0) set to red"),
            ("Color Depth", "✓ PASS", "6 colors tested"),
            ("Gradient", "✓ PASS", "32-step gradient"),
            ("Row", "✓ PASS", "Row 0 set (32 LEDs)"),
            ("Column", "✓ PASS", "Column 0 set (64 LEDs)"),
            ("Rectangle", "✓ PASS", "10x10 rectangle filled"),
            ("Full Screen", "✓ PASS", "All 2048 LEDs red"),
            ("Clear", "✓ PASS", "Screen cleared"),
            ("Serial", "✓ PASS", "Data sent to ESP32"),
            ("Checkerboard", "✓ PASS", "Pattern created"),
            ("Diagonal", "✓ PASS", "32-pixel diagonal"),
            ("Circle", "✓ PASS", "Radius 15 circle"),
            ("Frame Rate", "✓ PASS", "45.2 FPS"),
            ("Brightness", "✓ PASS", "7 levels tested"),
            ("RGB Mixing", "✓ PASS", "6 transitions"),
            ("Memory", "✓ PASS", "Stable memory usage"),
            ("Error Handling", "✓ PASS", "Bounds checking works"),
            ("Animation", "✓ PASS", "20-frame scan line"),
            ("Integration", "✓ PASS", "Full workflow OK")
        ]

        for test_name, status, details in tests:
            self.log(f"Running: {test_name}...", end=" ")
            time.sleep(0.1)
            self.log(f"{status}")
            if details:
                self.log(f"    Details: {details}")
            self.root.update()

        self.log(f"\n[OK] All 20 LED tests passed!")
        self.log("\n[?] Click 'Next' to continue...")

        self.next_btn.config(state='normal', text="Next Step →")

    def step_motor_tests(self):
        """Step 6: Motor tests (simulated)"""
        self.clear_content()

        ttk.Label(
            self.content_frame,
            text="⚙️ Motor Tests (Simulated)",
            font=("Arial", 14, "bold")
        ).pack(pady=10)

        ttk.Label(
            self.content_frame,
            text="Would run 30 progressive tests in real setup:",
            font=("Arial", 10)
        ).pack(pady=5)

        test_list = ttk.LabelFrame(self.content_frame, text="30 Motor Tests:", padding=10)
        test_list.pack(fill=tk.BOTH, expand=True, pady=20, padx=50)

        tests = [
            "1. Controller Initialization (64 servos)",
            "2. Single Motor (0 to 90°)",
            "3. Full Range (0→45→90→135→180→90→0)",
            "4. All Motors Individually",
            "5. Bank Test (4 banks of 16)",
            "6. Synchronized (all 0→90→180)",
            "7. Wave Pattern",
            "8. Sequential Activation",
            "9. Random Positions (10x)",
            "10. Response Speed",
            "11. Power Consumption (load test)",
            "12. Stress Test (10s)",
            "13. Center Position (90°)",
            "14. Min Position (0°)",
            "15. Max Position (180°)",
            "16-30. Advanced Patterns & Edge Cases"
        ]

        for test in tests:
            ttk.Label(test_list, text=f"  • {test}").pack(anchor=tk.W, pady=1)

        ttk.Button(
            self.content_frame,
            text="Simulate Motor Tests",
            command=self.run_motor_tests_simulation
        ).pack(pady=20)

    def run_motor_tests_simulation(self):
        """Simulate motor tests"""
        self.log("\n" + "="*70)
        self.log("SIMULATING 30 MOTOR TESTS")
        self.log("="*70 + "\n")

        tests = [
            ("Controller Init", "✓ PASS", "64 servos ready"),
            ("Single Motor", "✓ PASS", "Motor 0 → 90°"),
            ("Full Range", "✓ PASS", "0-180° full sweep"),
            ("All Individually", "✓ PASS", "64 motors tested"),
            ("Bank Test", "✓ PASS", "4 banks OK"),
            ("Synchronized", "✓ PASS", "All move together"),
            ("Wave Pattern", "✓ PASS", "10-phase wave"),
            ("Sequential", "✓ PASS", "One-by-one activation"),
            ("Random", "✓ PASS", "10 random patterns"),
            ("Speed", "✓ PASS", "125 movements/sec"),
            ("Power", "✓ PASS", "Load test OK"),
            ("Stress", "✓ PASS", "Stable for 10s"),
            ("Center", "✓ PASS", "All at 90°"),
            ("Min", "✓ PASS", "All at 0°"),
            ("Max", "✓ PASS", "All at 180°"),
        ] + [("Test {}".format(i), "✓ PASS", "OK") for i in range(16, 31)]

        for test_name, status, details in tests:
            self.log(f"Running: {test_name}...", end=" ")
            time.sleep(0.08)
            self.log(f"{status}")
            if details:
                self.log(f"    Details: {details}")
            self.root.update()

        self.log(f"\n[OK] All 30 motor tests passed!")
        self.log("\n[?] Click 'Next' to continue...")

        self.next_btn.config(state='normal', text="Next Step →")

    def step_complete(self):
        """Step 7: Complete"""
        self.clear_content()

        ttk.Label(
            self.content_frame,
            text="🎉 Mock Setup Complete!",
            font=("Arial", 18, "bold"),
            foreground="green"
        ).pack(pady=20)

        ttk.Label(
            self.content_frame,
            text="In real setup, your system would now be ready!",
            font=("Arial", 12)
        ).pack(pady=10)

        ttk.Label(
            self.content_frame,
            text="Summary:",
            font=("Arial", 10, "bold")
        ).pack(pady=(20, 5))

        summary = """
        ✓ Dependencies installed (5 packages)
        ✓ Wiring verified
        ✓ ESP32 firmware flashed
        ✓ 10 ESP32 tests passed
        ✓ 20 LED tests passed
        ✓ 30 Motor tests passed
        ─────────────────────────────
        TOTAL: 60/60 tests passed!
        """

        ttk.Label(
            self.content_frame,
            text=summary,
            font=("Consolas", 11),
            justify=tk.CENTER,
            foreground="blue"
        ).pack(pady=10)

        ttk.Label(
            self.content_frame,
            text="What happens next with real hardware:",
            font=("Arial", 10, "bold")
        ).pack(pady=(20, 5))

        next_steps = [
            "1. Launch main application: python main.py",
            "2. Connect camera for body tracking",
            "3. See human silhouette on LED panels",
            "4. Watch motor wave effects respond to body",
            "5. Enjoy your Mirror Body installation!"
        ]

        for step in next_steps:
            ttk.Label(self.content_frame, text=step).pack(pady=2)

        ttk.Button(
            self.content_frame,
            text="🚀 Launch Simulation (Mock Mode)",
            command=self.launch_simulation,
            width=30
        ).pack(pady=20)

        ttk.Label(
            self.content_frame,
            text="This will launch the main app in SIMULATION mode",
            font=("Arial", 9, "italic"),
            foreground="gray"
        ).pack()

        self.back_btn.config(state='normal')
        self.next_btn.config(text="Finish", state='disabled')
        self.skip_btn = ttk.Button(
            self.root.children['!frame4'].children['!frame'],
            text="Skip",
            command=self.skip_step
        )
        self.skip_btn.pack(side=tk.RIGHT, padx=5)
        self.skip_btn.config(state='disabled')

    def launch_simulation(self):
        """Launch the main application in simulation mode"""
        try:
            import subprocess
            subprocess.Popen(
                ["python", "main.py"],
                cwd=str(REPO_ROOT)
            )
            messagebox.showinfo("Launched", "Simulation launched!\n\nYou'll see the GUI with motor gauges and LED matrix.\nNo hardware needed!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch:\n{e}")

    def next_step(self):
        """Go to next step"""
        # Check if we need to run simulation first
        if self.current_step == 1:
            # Dependencies step - user clicked without simulating
            if not self.log_text.get("1.0", tk.END).strip():
                return  # Don't proceed if not simulated
        elif self.current_step == 3:
            # Flash step - user clicked without simulating
            if "SIMULATING ESP32 FIRMWARE FLASH" not in self.log_text.get("1.0", tk.END):
                return
        elif self.current_step == 4:
            if "SIMULATING 10 ESP32 TESTS" not in self.log_text.get("1.0", tk.END):
                return
        elif self.current_step == 6:
            if "SIMULATING 20 LED TESTS" not in self.log_text.get("1.0", tk.END):
                return
        elif self.current_step == 8:
            if "SIMULATING 30 MOTOR TESTS" not in self.log_text.get("1.0", tk.END):
                return

        # Proceed to next step
        if self.current_step == 0:
            self.current_step = 1
            self.step_dependencies()

        elif self.current_step == 1:
            self.current_step = 2
            self.step_wiring()

        elif self.current_step == 2:
            self.current_step = 3
            self.step_flash_firmware()

        elif self.current_step == 3:
            self.current_step = 4
            self.step_esp_tests()

        elif self.current_step == 4:
            self.current_step = 6
            self.step_led_tests()

        elif self.current_step == 6:
            self.current_step = 8
            self.step_motor_tests()

        elif self.current_step == 8:
            self.current_step = 10
            self.step_complete()

        self.update_progress()

    def back_step(self):
        """Go back"""
        if self.current_step > 0:
            self.current_step -= 1

            if self.current_step == 0:
                self.show_welcome()
            elif self.current_step == 1:
                self.step_dependencies()
            elif self.current_step == 2:
                self.step_wiring()
            elif self.current_step == 3:
                self.step_flash_firmware()
            elif self.current_step == 4:
                self.step_esp_tests()
            elif self.current_step == 6:
                self.step_led_tests()
            elif self.current_step == 8:
                self.step_motor_tests()

            self.update_progress()

    def skip_step(self):
        """Skip current step"""
        self.log("\n[*] Step skipped")
        self.next_step()


def main():
    """Main entry point"""
    root = tk.Tk()
    app = MockSetupLauncher(root)
    root.mainloop()


if __name__ == "__main__":
    main()
