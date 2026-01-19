#!/usr/bin/env python3
"""
Auto-Flash Script for ESP32 Firmware
Automatically detects ESP32 and uploads firmware
"""

import os
import sys
import subprocess
import serial
import serial.tools.list_ports
from pathlib import Path
from typing import Optional

# Add project root to path
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


class ESP32Flasher:
    """Handles ESP32 firmware flashing"""

    def __init__(self, firmware_dir: Path = None):
        self.firmware_dir = firmware_dir or REPO_ROOT / "firmware" / "esp32"
        self.firmware_file = self.find_firmware()
        self.port: Optional[str] = None

    def find_firmware(self) -> Optional[Path]:
        """Find the firmware file"""
        possible_files = [
            self.firmware_dir / "firmware.bin",
            self.firmware_dir / "build" / "firmware.bin",
            self.firmware_dir / ".pio" / "build" / "esp32s3" / "firmware.bin",
        ]

        for f in possible_files:
            if f.exists():
                return f

        print("[!] No pre-built firmware found")
        print("[*] Attempting to build firmware...")

        # Try to build with PlatformIO
        if self.build_firmware():
            return self.find_firmware()

        return None

    def build_firmware(self) -> bool:
        """Build firmware using PlatformIO"""
        if not (self.firmware_dir / "platformio.ini").exists():
            print("[!] No platformio.ini found - cannot build firmware")
            return False

        print("[*] Building firmware with PlatformIO...")

        try:
            result = subprocess.run(
                [sys.executable, "-m", "platformio", "run"],
                cwd=str(self.firmware_dir),
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0:
                print("[OK] Firmware built successfully!")
                return True
            else:
                print(f"[!] Build failed: {result.stderr}")
                return False

        except FileNotFoundError:
            print("[!] PlatformIO (pio) not found")
            print("[*] Install PlatformIO: pip install platformio")
            return False

        except subprocess.TimeoutExpired:
            print("[!] Build timed out (5 minutes)")
            return False

        except Exception as e:
            print(f"[!] Build error: {e}")
            return False

    def detect_esp32(self) -> Optional[str]:
        """Auto-detect ESP32 port"""
        ports = list(serial.tools.list_ports.comports())

        if not ports:
            print("[!] No serial ports detected")
            return None

        print("[*] Detected serial ports:")
        for p in ports:
            print(f"    {p.device}: {p.description}")

        # Auto-detect ESP32
        for p in ports:
            desc = p.description.lower()
            if any(keyword in desc for keyword in ['ch340', 'cp210', 'usb-serial', 'usb serial', 'uart', 'esp32']):
                print(f"[OK] Auto-detected ESP32 on {p.device}")
                return p.device

        print("[!] Could not auto-detect ESP32")
        print("[*] Please select from the list above")

        # Manual selection
        if ports:
            print("\n[?] Select port number:")
            for i, p in enumerate(ports):
                print(f"    [{i+1}] {p.device} - {p.description}")

            try:
                choice = input("Enter number [1-{}]: ".format(len(ports)))
                idx = int(choice) - 1
                if 0 <= idx < len(ports):
                    return ports[idx].device
            except (ValueError, KeyboardInterrupt):
                pass

        return None

    def flash_firmware(self, port: str = None) -> bool:
        """Flash firmware to ESP32"""
        print(f"DEBUG: inside flash_firmware port={port}", flush=True)
        if not self.firmware_file:
            print("[!] No firmware file available")
            return False

        if not self.firmware_file.exists():
            print(f"[!] Firmware file not found: {self.firmware_file}")
            return False

        print("DEBUG: firmware file exists", flush=True)

        port = port or self.detect_esp32()
        if not port:
            print("[!] No ESP32 port specified")
            return False

        self.port = port

        print(f"\n[*] Flashing firmware...", flush=True)
        print(f"    Port: {port}", flush=True)
        print(f"    Firmware: {self.firmware_file}", flush=True)
        print("DEBUG: entering loop", flush=True)

        # Try different flash methods
        flashers = [
            # self.flash_with_esptool,
            self.flash_with_platformio,
            # self.flash_with_arduino
        ]

        for flasher in flashers:
            print(f"DEBUG: trying flasher {flasher.__name__}", flush=True)
            try:
                if flasher(port):
                    print("\n[OK] Firmware flashed successfully!")
                    print("[*] You can now run the setup wizard")
                    return True
            except Exception as e:
                print(f"[!] Flash method failed: {e}")
                continue

        print("\n[!] All flash methods failed")
        print("[*] Try flashing manually:")
        print(f"    esptool.py --chip esp32s3 --port {port} --baud 460800 write_flash -z 0x10000 {self.firmware_file}")
        return False

    def flash_with_esptool(self, port: str) -> bool:
        """Flash using esptool.py"""
        try:
            result = subprocess.run(
                [
                    "esptool.py",
                    "--chip", "esp32s3",
                    "--port", port,
                    "--baud", "460800",
                    "write_flash",
                    "-z",
                    "0x10000",
                    str(self.firmware_file)
                ],
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode == 0:
                print("[esptool] Flash successful!")
                return True
            else:
                print(f"[esptool] Failed: {result.stderr}")
                return False

        except FileNotFoundError:
            print("[esptool] esptool.py not found")
            return False

        except Exception as e:
            print(f"[esptool] Error: {e}")
            return False

    def flash_with_platformio(self, port: str) -> bool:
        """Flash using PlatformIO"""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "platformio", "run", "--target", "upload", "--upload-port", port],
                cwd=str(self.firmware_dir),
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode == 0:
                print("[PlatformIO] Flash successful!")
                return True
            else:
                print(f"[PlatformIO] Failed: {result.stderr}")
                return False

        except FileNotFoundError:
            print("[PlatformIO] PlatformIO (pio) not found")
            return False

        except Exception as e:
            print(f"[PlatformIO] Error: {e}")
            return False

    def flash_with_arduino(self, port: str) -> bool:
        """Flash using Arduino CLI"""
        try:
            result = subprocess.run(
                [
                    "arduino-cli",
                    "compile",
                    "--fqbn", "esp32:esp32:esp32s3",
                    "--upload",
                    "--port", port,
                    str(self.firmware_dir)
                ],
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0:
                print("[Arduino CLI] Flash successful!")
                return True
            else:
                print(f"[Arduino CLI] Failed: {result.stderr}")
                return False

        except FileNotFoundError:
            print("[Arduino CLI] arduino-cli not found")
            return False

        except Exception as e:
            print(f"[Arduino CLI] Error: {e}")
            return False

    def verify_flash(self) -> bool:
        """Verify firmware was uploaded successfully"""
        if not self.port:
            print("[!] No port to verify")
            return False

        print(f"[*] Verifying connection on {self.port}...")

        try:
            ser = serial.Serial(self.port, 460800, timeout=2)
            ser.write(b"PING\n")
            response = ser.readline().decode().strip()

            if "PONG" in response or "READY" in response:
                print("[OK] ESP32 responding!")
                return True
            else:
                print(f"[?] Unexpected response: {response}")
                return False

        except Exception as e:
            print(f"[!] Verification failed: {e}")
            return False

        finally:
            try:
                ser.close()
            except:
                pass


def main():
    """Main entry point"""
    print("=" * 70)
    print("  🔧 ESP32 Firmware Auto-Flasher")
    print("=" * 70)
    print()

    flasher = ESP32Flasher()

    if not flasher.firmware_file:
        print("\n[✗] Cannot proceed - no firmware available")
        print("\n[*] To fix this:")
        print("    1. Install PlatformIO: pip install platformio")
        print("    2. Or manually compile firmware in Arduino IDE")
        print("    3. Place firmware.bin in firmware/esp32/")
        sys.exit(1)

    print(f"[OK] Firmware ready: {flasher.firmware_file.name}")
    print()

    port = flasher.detect_esp32()
    if not port:
        print("\n[✗] Cannot proceed - no ESP32 detected")
        sys.exit(1)

    print("\n[?] Flash firmware to ESP32?")
    response = input("Press Enter to continue, or Ctrl+C to cancel: ")

    if flasher.flash_firmware(port):
        print("\n" + "=" * 70)
        print("[✓] Firmware flashing complete!")
        print("=" * 70)
        print()
        print("[*] Next steps:")
        print("    1. Run: python master_setup.py")
        print("    2. Or run: python setup_wizard.py")
        print("    3. Then run: python main.py")
        print()
    else:
        print("\n[✗] Flashing failed")
        print("[*] See errors above for troubleshooting")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[!] Cancelled by user")
        sys.exit(0)
