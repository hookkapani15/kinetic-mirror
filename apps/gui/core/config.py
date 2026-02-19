import os

# ESP32-S3 USB VID/PIDs (common chips)
ESP32_S3_IDENTIFIERS = [
    (0x303A, 0x1001),  # ESP32-S3 native USB
    (0x303A, 0x0002),  # ESP32-S3 JTAG
    (0x10C4, 0xEA60),  # Silicon Labs CP210x
    (0x1A86, 0x7523),  # CH340
    (0x1A86, 0x55D4),  # CH9102
    (0x0403, 0x6001),  # FTDI FT232
    (0x0403, 0x6015),  # FTDI FT231X
]

# Firmware paths (relative to this file -> core -> gui -> apps -> root)
# Actually, relative to the main execution script usually, but we obtain it via __file__
# config.py is in apps/gui/core/
# We need to go up to apps/gui/core/../../.. -> root
# Then firmware/esp32

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
FIRMWARE_DIR = os.path.join(PROJECT_ROOT, 'firmware', 'esp32')

# ESP32 (regular) firmware
FIRMWARE_BIN_ESP32 = os.path.join(FIRMWARE_DIR, '.pio', 'build', 'esp32', 'firmware.bin')
BOOTLOADER_BIN_ESP32 = os.path.join(FIRMWARE_DIR, '.pio', 'build', 'esp32', 'bootloader.bin')
PARTITIONS_BIN_ESP32 = os.path.join(FIRMWARE_DIR, '.pio', 'build', 'esp32', 'partitions.bin')

# ESP32-S3 firmware
FIRMWARE_BIN_ESP32S3 = os.path.join(FIRMWARE_DIR, '.pio', 'build', 'esp32s3', 'firmware.bin')
BOOTLOADER_BIN_ESP32S3 = os.path.join(FIRMWARE_DIR, '.pio', 'build', 'esp32s3', 'bootloader.bin')
PARTITIONS_BIN_ESP32S3 = os.path.join(FIRMWARE_DIR, '.pio', 'build', 'esp32s3', 'partitions.bin')

# Chip-aware flash layouts
FLASH_LAYOUTS = {
    'esp32': {
        'firmware': FIRMWARE_BIN_ESP32,
        'bootloader': BOOTLOADER_BIN_ESP32,
        'partitions': PARTITIONS_BIN_ESP32,
        'bootloader_addr': '0x1000',
        'partitions_addr': '0x8000',
        'firmware_addr': '0x10000',
    },
    'esp32s3': {
        'firmware': FIRMWARE_BIN_ESP32S3,
        'bootloader': BOOTLOADER_BIN_ESP32S3,
        'partitions': PARTITIONS_BIN_ESP32S3,
        'bootloader_addr': '0x0',
        'partitions_addr': '0x8000',
        'firmware_addr': '0x10000',
    },
}

def has_any_firmware_binary():
    """True if at least one supported build artifact exists."""
    return os.path.exists(FIRMWARE_BIN_ESP32) or os.path.exists(FIRMWARE_BIN_ESP32S3)
