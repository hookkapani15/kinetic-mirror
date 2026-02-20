# Firmware Flashing Feature Added

## Overview
Firmware flashing capability has been added to both GUI branches, allowing users to flash ESP32 firmware directly from the GUI interface.

## LED Branch (leds)
**Location:** `apps/gui/main.py`

**Firmware Used:** LED-only firmware
- Path: `firmware/esp32/.pio/build/esp32/firmware.bin`
- Features: LED matrix control (32x64), body silhouette display
- Bootloader: `bootloader.bin`
- Partitions: `partitions.bin`

**How to Flash:**
1. Select ESP32 port from dropdown (not SIMULATOR)
2. Click **[ FLASH ]** button in control panel
3. Follow instructions:
   - Hold BOOT button
   - Press RESET button  
   - Release RESET, then BOOT
4. Click "Yes" to confirm
5. Wait for flash to complete (progress shown in log)

**Features:**
- Auto-detects chip type (ESP32/ESP32-S3)
- Flashes bootloader + partitions + firmware
- Progress logging in GUI
- Automatic port detection
- Error handling and user confirmation

## Motors Branch (motors)
**Location:** `apps/gui/main.py` in ConnectionPanel

**Firmware Used:** Motor + LED unified firmware
- Path: `firmware/esp32/.pio/build/esp32/firmware.bin` (motors branch version)
- Features: LED matrix + PCA9685 servo control (64 servos)
- Supports: Both LED body tracking AND servo motor control

**How to Flash:**
1. Go to **HARDWARE** panel
2. Select ESP32 port from dropdown
3. Click **⚡ FIRMWARE** section
4. Click **[ 🔥 Flash ]** button
5. Follow boot mode instructions
6. Click "Yes" to confirm

**Features:**
- Auto-detects ESP32 vs ESP32-S3
- Shows firmware file size
- Progress bar with percentage
- Detailed flash log output
- Automatic chip type detection
- Disconnects before flashing if connected

## Key Differences Between Branches

| Feature | LED Branch | Motors Branch |
|---------|-----------|---------------|
| **Firmware** | LED only (2048 LEDs) | LED + Servos (LEDs + 64 servos) |
| **Flash Button** | In control panel | In Hardware panel |
| **UI Style** | AnimatedButton | ModernButton |
| **Progress** | Log text only | Progress bar + log |
| **Chip Detect** | ESP32/ESP32-S3 | ESP32/ESP32-S3 |

## Build Firmware

Before flashing, build the firmware:

```bash
cd firmware/esp32
pio run
```

This generates:
- `.pio/build/esp32/firmware.bin`
- `.pio/build/esp32/bootloader.bin`
- `.pio/build/esp32/partitions.bin`

## Safety Features

1. **Port Validation**: Won't flash SIMULATOR port
2. **Confirmation Dialog**: User must confirm before flashing
3. **Disconnect First**: Automatically disconnects if port is in use
4. **Boot Mode Instructions**: Clear steps to enter download mode
5. **Error Handling**: Catches and displays errors gracefully
6. **Progress Feedback**: Shows flash progress and status

## Rollback Option

Both GUIs have a **[ Rollback ]** button to restore the original UI if needed.

## Testing

Both branches tested and working:
- ✅ LED GUI: Launches successfully with flash button
- ✅ Motors GUI: Has existing flash functionality verified
- ✅ Auto-detection working for both ESP32 and ESP32-S3
- ✅ Progress logging functional
