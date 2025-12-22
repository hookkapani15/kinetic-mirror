"""
Quick Restore Script - 32 Servo Motor System
Restores the system to working state from snapshot
"""
import json
import subprocess
import sys
from pathlib import Path

def load_snapshot():
    """Load system snapshot"""
    snapshot_file = Path(__file__).parent / "settings" / "motor_system_snapshot.json"
    with open(snapshot_file, 'r') as f:
        return json.load(f)

def verify_hardware():
    """Verify hardware configuration"""
    print("=" * 60)
    print("  HARDWARE VERIFICATION")
    print("=" * 60)
    
    snapshot = load_snapshot()
    
    print("\n✓ Expected Configuration:")
    print(f"  ESP32: {snapshot['hardware']['esp32']['chip']}")
    print(f"  Servos: {snapshot['hardware']['servos']['total_count']}")
    print(f"  PCA9685 Boards: {snapshot['hardware']['servos']['pca9685_boards']}")
    print(f"    - Board 1: Address {snapshot['hardware']['servos']['board_1']['i2c_address']}")
    print(f"    - Board 2: Address {snapshot['hardware']['servos']['board_2']['i2c_address']}")
    print(f"  Serial Port: {snapshot['communication']['serial']['port']}")
    print(f"  Baud Rate: {snapshot['communication']['serial']['baud_rate']}")
    
    return snapshot

def upload_firmware(snapshot):
    """Upload ESP32 firmware"""
    print("\n" + "=" * 60)
    print("  FIRMWARE UPLOAD")
    print("=" * 60)
    
    port = snapshot['communication']['serial']['port']
    firmware_dir = Path(__file__).parent / "firmware" / "esp32"
    
    print(f"\n📤 Uploading firmware to {port}...")
    print(f"   Directory: {firmware_dir}")
    
    cmd = [
        "python", "-m", "platformio", "run",
        "--project-dir", str(firmware_dir),
        "--target", "upload",
        "--upload-port", port
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Firmware uploaded successfully!")
            return True
        else:
            print(f"❌ Upload failed:\n{result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def run_tests():
    """Run comprehensive test suite"""
    print("\n" + "=" * 60)
    print("  RUNNING TEST SUITE")
    print("=" * 60)
    
    test_file = Path(__file__).parent / "tests" / "hardware" / "motors" / "comprehensive_motor_test.py"
    
    print(f"\n🧪 Running tests from: {test_file}")
    
    cmd = ["python", str(test_file)]
    
    try:
        result = subprocess.run(cmd)
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False

def main():
    """Main restore process"""
    print("\n" + "=" * 70)
    print("  🔧 MIRROR BODY ANIMATIONS - 32 SERVO MOTOR SYSTEM RESTORE")
    print("=" * 70)
    
    # Load snapshot
    snapshot = verify_hardware()
    
    print("\n" + "=" * 60)
    print("  RESTORE OPTIONS")
    print("=" * 60)
    print("  1. Upload firmware only")
    print("  2. Run tests only")
    print("  3. Full restore (upload + test)")
    print("  4. Skip and show config")
    
    choice = input("\nChoice (1-4): ").strip()
    
    if choice == "1":
        upload_firmware(snapshot)
    elif choice == "2":
        run_tests()
    elif choice == "3":
        if upload_firmware(snapshot):
            print("\n⏳ Waiting 5 seconds for ESP32 to boot...")
            import time
            time.sleep(5)
            run_tests()
    elif choice == "4":
        print("\n✅ Configuration displayed above")
    
    print("\n" + "=" * 70)
    print("  Restore process complete!")
    print("  To run GUI: python -m apps.gui.main --fast")
    print("=" * 70)

if __name__ == "__main__":
    main()
