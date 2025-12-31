#!/usr/bin/env python3
"""
Easy Setup Launcher - For "Dumbass" Users
One-click setup with visual feedback and guided instructions
Just run this and follow the prompts!
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import sys
import subprocess
import threading
import time
from pathlib import Path

# Add project root to path
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


class EasySetupLauncher:
    """One-click setup launcher with GUI"""

    def __init__(self, root):
        self.root = root
        self.root.title("🔧 Mirror Body - Easy Setup Launcher")
        self.root.geometry("800x700")
        self.root.resizable(False, False)

        # Setup progress
        self.current_step = 0
        self.total_steps = 7
        self.steps = [
            "Welcome & Overview",
            "Install Dependencies",
            "Check Wiring",
            "Flash ESP32 Firmware",
            "Run ESP32 Tests (10 tests)",
            "Run LED Tests (20 tests)",
            "Run Motor Tests (30 tests)",
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
            text="🔧 Mirror Body - Easy Setup Launcher",
            font=("Arial", 18, "bold")
        )
        title.pack(side=tk.LEFT)

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
        log_frame = ttk.LabelFrame(self.root, text="Setup Log", padding=10)
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
            text="Start Setup →",
            command=self.next_step
        )
        self.next_btn.pack(side=tk.RIGHT, padx=5)

        self.skip_btn = ttk.Button(
            button_frame,
            text="Skip",
            command=self.skip_step
        )
        self.skip_btn.pack(side=tk.RIGHT, padx=5)

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
        ║        Welcome to Mirror Body Easy Setup!                      ║
        ║                                                              ║
        ║        This launcher will guide you through:                    ║
        ║                                                              ║
        ║        ✓ Installing required software                         ║
        ║        ✓ Checking your wiring setup                           ║
        ║        ✓ Flashing ESP32 firmware automatically                ║
        ║        ✓ Running comprehensive tests                          ║
        ║        ✓ Launching the main application                       ║
        ║                                                              ║
        ║        Total time: ~15-20 minutes (if needed)               ║
        ║                                                              ║
        ║        Click "Start Setup" to begin!                         ║
        ║                                                              ║
        ╚════════════════════════════════════════════════════════════╝
        """

        ttk.Label(
            self.content_frame,
            text=welcome_text,
            font=("Consolas", 11),
            justify=tk.CENTER
        ).pack(pady=20)

        ttk.Label(
            self.content_frame,
            text="Don't worry - this setup is foolproof!",
            font=("Arial", 12, "bold"),
            foreground="green"
        ).pack(pady=10)

        self.back_btn.config(state='disabled')
        self.next_btn.config(text="Start Setup →")

    def step_dependencies(self):
        """Step 1: Install dependencies"""
        self.clear_content()

        ttk.Label(
            self.content_frame,
            text="📦 Installing Dependencies",
            font=("Arial", 14, "bold")
        ).pack(pady=10)

        ttk.Label(
            self.content_frame,
            text="This will install the required Python packages.",
            font=("Arial", 10)
        ).pack(pady=5)

        ttk.Label(
            self.content_frame,
            text="Required packages:",
            font=("Arial", 10, "bold")
        ).pack(pady=(20, 5))

        packages = [
            "pyserial - For ESP32 communication",
            "opencv-python - For camera input",
            "mediapipe - For AI body tracking",
            "pillow - For image processing",
            "numpy - For calculations"
        ]

        for pkg in packages:
            ttk.Label(self.content_frame, text=f"  • {pkg}").pack()

        self.back_btn.config(state='normal')
        self.next_btn.config(text="Install Packages →")

    def run_install_dependencies(self):
        """Actually install dependencies in background thread"""
        self.log("\n" + "="*70)
        self.log("INSTALLING DEPENDENCIES")
        self.log("="*70 + "\n")

        try:
            packages = ["pyserial", "opencv-python", "mediapipe", "pillow", "numpy"]

            for pkg in packages:
                self.log(f"[*] Installing {pkg}...")
                try:
                    result = subprocess.run(
                        ["pip", "install", pkg],
                        capture_output=True,
                        text=True,
                        timeout=180
                    )
                    if result.returncode == 0:
                        self.log(f"[OK] {pkg} installed successfully")
                    else:
                        self.log(f"[!] {pkg} installation failed")
                        self.log(f"    Error: {result.stderr}")
                        self.log(f"    Trying with --only-binary...")
                        result = subprocess.run(
                            ["pip", "install", pkg, "--only-binary=:all:"],
                            capture_output=True,
                            text=True,
                            timeout=180
                        )
                        if result.returncode == 0:
                            self.log(f"[OK] {pkg} installed with binary")
                        else:
                            self.log(f"[!] {pkg} still failed - skipping")
                except Exception as e:
                    self.log(f"[!] {pkg} error: {e}")
                self.root.update()

            self.log("\n[OK] Dependencies installation completed!")
            self.log("\n[?] Click 'Next' to continue...")

        except Exception as e:
            self.log(f"\n[!] Installation failed: {e}")
            messagebox.showerror("Error", f"Dependencies installation failed:\n{e}")

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
            text="Please verify your wiring before continuing.",
            font=("Arial", 10)
        ).pack(pady=5)

        checklist = ttk.LabelFrame(self.content_frame, text="Wiring Checklist", padding=10)
        checklist.pack(fill=tk.X, pady=20, padx=50)

        checks = [
            "ESP32 connected via USB",
            "LED power supply connected (5V, 30A+ recommended)",
            "Motor power supply connected (5V/6V, 70A+ recommended)",
            "ALL GROUNDS connected together (ESP32, LED, Motor)",
            "ESP32 GPIO 12 to first LED panel DIN",
            "ESP32 SDA/SCL to PCA9685",
            "Motor signals to PCA9685 outputs"
        ]

        for check in checks:
            ttk.Label(checklist, text=f"☐ {check}").pack(anchor=tk.W, pady=2)

        ttk.Button(
            checklist,
            text="📖 Open Full Wiring Guide",
            command=self.open_wiring_guide
        ).pack(pady=10)

        self.back_btn.config(state='normal')
        self.next_btn.config(text="I've Checked Wiring →")

    def open_wiring_guide(self):
        """Open the wiring guide"""
        guide_path = REPO_ROOT / "docs" / "COMPLETE_WIRING_GUIDE.md"
        if guide_path.exists():
            import os
            os.startfile(guide_path)
        else:
            messagebox.showinfo("Info", "Wiring guide not found. Please check docs folder.")

    def step_flash_firmware(self):
        """Step 3: Flash firmware"""
        self.clear_content()

        ttk.Label(
            self.content_frame,
            text="⚡ Flash ESP32 Firmware",
            font=("Arial", 14, "bold")
        ).pack(pady=10)

        ttk.Label(
            self.content_frame,
            text="This will automatically detect your ESP32 and flash the firmware.",
            font=("Arial", 10)
        ).pack(pady=5)

        info_frame = ttk.LabelFrame(self.content_frame, text="What will happen:", padding=10)
        info_frame.pack(fill=tk.X, pady=20, padx=50)

        steps = [
            "1. Auto-detect ESP32 USB connection",
            "2. Build firmware (if needed)",
            "3. Upload firmware to ESP32",
            "4. Verify communication"
        ]

        for step in steps:
            ttk.Label(info_frame, text=f"  {step}").pack(anchor=tk.W, pady=2)

        self.back_btn.config(state='normal')
        self.next_btn.config(text="Flash Now →")

    def run_flash_firmware(self):
        """Run firmware flash in background"""
        self.log("\n" + "="*70)
        self.log("FLASHING ESP32 FIRMWARE")
        self.log("="*70 + "\n")

        try:
            result = subprocess.run(
                ["python", str(REPO_ROOT / "tools" / "auto_flash_esp32.py")],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                timeout=300
            )

            self.log(result.stdout)
            if result.stderr:
                self.log(result.stderr)

            if result.returncode == 0:
                self.log("\n[OK] Firmware flashed successfully!")
            else:
                self.log("\n[!] Flashing failed. See errors above.")

            self.log("\n[?] Click 'Next' to continue...")

        except subprocess.TimeoutExpired:
            self.log("\n[!] Flashing timed out (5 minutes)")
        except Exception as e:
            self.log(f"\n[!] Flashing error: {e}")

    def step_esp_tests(self):
        """Step 4: ESP32 tests"""
        self.clear_content()

        ttk.Label(
            self.content_frame,
            text="🧪 ESP32 Tests (10 comprehensive tests)",
            font=("Arial", 14, "bold")
        ).pack(pady=10)

        ttk.Label(
            self.content_frame,
            text="This will run 10 progressive tests to verify ESP32 functionality:",
            font=("Arial", 10)
        ).pack(pady=5)

        test_list = ttk.LabelFrame(self.content_frame, text="Tests:", padding=10)
        test_list.pack(fill=tk.X, pady=20, padx=50)

        tests = [
            "Basic connection",
            "Command responsiveness",
            "LED communication",
            "Motor communication",
            "LED data integrity",
            "Motor command integrity",
            "Speed/stress test",
            "Error recovery",
            "Multi-channel test",
            "Long-run stability (15s)"
        ]

        for i, test in enumerate(tests, 1):
            ttk.Label(test_list, text=f"  {i}. {test}").pack(anchor=tk.W, pady=2)

        self.back_btn.config(state='normal')
        self.next_btn.config(text="Run ESP32 Tests →")

    def run_esp_tests(self):
        """Run ESP32 tests in background"""
        self.log("\n" + "="*70)
        self.log("RUNNING ESP32 TESTS (10 tests)")
        self.log("="*70 + "\n")

        try:
            result = subprocess.run(
                ["python", str(REPO_ROOT / "tests" / "hardware" / "esp" / "comprehensive_esp_test.py")],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                timeout=120
            )

            self.log(result.stdout)
            if result.stderr:
                self.log(result.stderr)

            self.log("\n[?] Click 'Next' to continue...")

        except subprocess.TimeoutExpired:
            self.log("\n[!] Tests timed out")
        except Exception as e:
            self.log(f"\n[!] Test error: {e}")

    def step_led_tests(self):
        """Step 5: LED tests"""
        self.clear_content()

        ttk.Label(
            self.content_frame,
            text="💡 LED Tests (20 comprehensive tests)",
            font=("Arial", 14, "bold")
        ).pack(pady=10)

        ttk.Label(
            self.content_frame,
            text="This will run 20 progressive tests to verify LED system:",
            font=("Arial", 10)
        ).pack(pady=5)

        test_list = ttk.LabelFrame(self.content_frame, text="Tests:", padding=10)
        test_list.pack(fill=tk.BOTH, expand=True, pady=20, padx=50)

        tests = [
            "Controller initialization",
            "Single LED control",
            "Color depth test",
            "Gradient pattern",
            "Row/column control",
            "Rectangle fill",
            "Full screen fill",
            "Clear screen",
            "Serial communication",
            "Pattern tests (checkerboard, diagonal, circle)",
            "Frame rate performance",
            "Brightness control",
            "RGB color mixing",
            "Memory usage",
            "Error handling",
            "Animation test",
            "Full integration"
        ]

        for test in tests:
            ttk.Label(test_list, text=f"  • {test}").pack(anchor=tk.W, pady=1)

        self.back_btn.config(state='normal')
        self.next_btn.config(text="Run LED Tests →")

    def run_led_tests(self):
        """Run LED tests in background"""
        self.log("\n" + "="*70)
        self.log("RUNNING LED TESTS (20 tests)")
        self.log("="*70 + "\n")

        try:
            result = subprocess.run(
                ["python", str(REPO_ROOT / "tests" / "hardware" / "leds" / "comprehensive_led_test_v2.py")],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                timeout=180
            )

            self.log(result.stdout)
            if result.stderr:
                self.log(result.stderr)

            self.log("\n[?] Click 'Next' to continue...")

        except subprocess.TimeoutExpired:
            self.log("\n[!] Tests timed out")
        except Exception as e:
            self.log(f"\n[!] Test error: {e}")

    def step_motor_tests(self):
        """Step 6: Motor tests"""
        self.clear_content()

        ttk.Label(
            self.content_frame,
            text="⚙️ Motor Tests (30 comprehensive tests)",
            font=("Arial", 14, "bold")
        ).pack(pady=10)

        ttk.Label(
            self.content_frame,
            text="This will run 30 progressive tests to verify motor system:",
            font=("Arial", 10)
        ).pack(pady=5)

        test_list = ttk.LabelFrame(self.content_frame, text="Tests:", padding=10)
        test_list.pack(fill=tk.BOTH, expand=True, pady=20, padx=50)

        tests = [
            "Controller initialization",
            "Single motor control",
            "Full range (0-180°)",
            "All motors individually",
            "Bank tests (16 per board)",
            "Synchronized movement",
            "Wave pattern",
            "Sequential activation",
            "Random positions",
            "Response speed",
            "Power consumption",
            "Stress test",
            "Center/min/max positions",
            "Advanced tests (17-30)"
        ]

        for test in tests:
            ttk.Label(test_list, text=f"  • {test}").pack(anchor=tk.W, pady=1)

        self.back_btn.config(state='normal')
        self.next_btn.config(text="Run Motor Tests →")

    def run_motor_tests(self):
        """Run motor tests in background"""
        self.log("\n" + "="*70)
        self.log("RUNNING MOTOR TESTS (30 tests)")
        self.log("="*70 + "\n")

        try:
            result = subprocess.run(
                ["python", str(REPO_ROOT / "tests" / "hardware" / "motors" / "comprehensive_motor_test_v2.py")],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                timeout=300
            )

            self.log(result.stdout)
            if result.stderr:
                self.log(result.stderr)

            self.log("\n[?] Click 'Next' to continue...")

        except subprocess.TimeoutExpired:
            self.log("\n[!] Tests timed out")
        except Exception as e:
            self.log(f"\n[!] Test error: {e}")

    def step_complete(self):
        """Step 7: Complete"""
        self.clear_content()

        ttk.Label(
            self.content_frame,
            text="🎉 Setup Complete!",
            font=("Arial", 18, "bold"),
            foreground="green"
        ).pack(pady=20)

        ttk.Label(
            self.content_frame,
            text="Your Mirror Body system is now ready to use!",
            font=("Arial", 12)
        ).pack(pady=10)

        ttk.Label(
            self.content_frame,
            text="Next steps:",
            font=("Arial", 10, "bold")
        ).pack(pady=(20, 5))

        steps = [
            "1. Click 'Launch Application' below to start the main app",
            "2. Connect your camera for body tracking",
            "3. Enjoy your Mirror Body installation!"
        ]

        for step in steps:
            ttk.Label(self.content_frame, text=step).pack(pady=2)

        ttk.Button(
            self.content_frame,
            text="🚀 Launch Application",
            command=self.launch_application,
            width=25
        ).pack(pady=20)

        self.back_btn.config(state='normal')
        self.next_btn.config(text="Finish", state='disabled')
        self.skip_btn.config(state='disabled')

    def launch_application(self):
        """Launch main application"""
        try:
            subprocess.Popen(
                ["python", "main.py"],
                cwd=str(REPO_ROOT)
            )
            messagebox.showinfo("Launched", "Application launched! You can close this window.")
            self.root.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch:\n{e}")

    def next_step(self):
        """Go to next step"""
        # Execute current step action
        if self.current_step == 0:
            # Moving from welcome to dependencies
            self.current_step = 1
            self.step_dependencies()

        elif self.current_step == 1:
            # Install dependencies
            self.next_btn.config(state='disabled')
            threading.Thread(target=self.run_install_dependencies, daemon=True).start()

        elif self.current_step == 2:
            # Check wiring
            self.current_step = 3
            self.step_wiring()

        elif self.current_step == 3:
            # Flash firmware
            self.current_step = 4
            self.step_flash_firmware()

        elif self.current_step == 4:
            # Run flash
            self.next_btn.config(state='disabled')
            threading.Thread(target=self.run_flash_firmware, daemon=True).start()

        elif self.current_step == 5:
            # ESP32 tests
            self.current_step = 6
            self.step_esp_tests()

        elif self.current_step == 6:
            # Run ESP32 tests
            self.next_btn.config(state='disabled')
            threading.Thread(target=self.run_esp_tests, daemon=True).start()

        elif self.current_step == 7:
            # LED tests
            self.current_step = 8
            self.step_led_tests()

        elif self.current_step == 8:
            # Run LED tests
            self.next_btn.config(state='disabled')
            threading.Thread(target=self.run_led_tests, daemon=True).start()

        elif self.current_step == 9:
            # Motor tests
            self.current_step = 10
            self.step_motor_tests()

        elif self.current_step == 10:
            # Run motor tests
            self.next_btn.config(state='disabled')
            threading.Thread(target=self.run_motor_tests, daemon=True).start()

        elif self.current_step == 11:
            # Complete
            self.current_step = 12
            self.step_complete()

        self.update_progress()

    def back_step(self):
        """Go back to previous step"""
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
            elif self.current_step == 5:
                self.step_led_tests()
            elif self.current_step == 6:
                self.step_motor_tests()

            self.update_progress()

    def skip_step(self):
        """Skip current step"""
        self.log("\n[*] Step skipped by user")
        self.next_step()

    def on_close(self):
        """Handle window close"""
        if messagebox.askyesno("Exit", "Are you sure you want to exit setup?"):
            self.root.destroy()
            sys.exit(0)


def main():
    """Main entry point"""
    root = tk.Tk()
    app = EasySetupLauncher(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
