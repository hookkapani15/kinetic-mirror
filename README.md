# Mirror Hybrid (Prod-ready layout)

Body/hand-tracking GUI with ESP32 firmware for LED matrix + servos.

## Folder map
```
apps/
  gui/            GUI entrypoint (main.py), modes, startup wizard
  cli/            Command-line helpers (debug_crash.py)
packages/
  mirror_core/    Core controllers and tests
    controllers/  motor_controller.py, led_controller.py
    io/           serial_manager.py
    tests/        system_tests.py, automated/
config/           PC defaults (config.json)
firmware/
  esp32/          ESP32 source (MirrorHybrid_ESP32.ino)
  binaries/       Prebuilt bootloader/firmware/partitions
logs/             Runtime and health logs
docs/             (reserved for handoff docs)
requirements.txt  Python deps
```

## Quick start (PC)
```
pip install -r requirements.txt
python -m apps.gui.main --fast   # skip startup wizard
```
Controls: M motor, L LED, B both, R readme, C camera, D diagnostics, E emergency test, Q quit.

## Config
- PC config lives in `config/config.json` (auto-created on first run).

## Firmware upload
Source: `firmware/esp32/MirrorHybrid_ESP32.ino`
Prebuilt: `firmware/binaries/`

USB (recommended):
1) Plug ESP32 (note COM port, e.g., COM3).
2) Arduino IDE: open `MirrorHybrid_ESP32.ino`, select ESP32 DevKit board + port, Upload.
   or PlatformIO CLI: `pio run -d firmware/esp32 -t upload --upload-port COM3`

OTA (if prior OTA firmware is running on Wi‑Fi):
1) Ensure ESP32 is on the same network.
2) Upload via Arduino IDE network port (`MirrorHybrid-ESP32`) or Arduino/PIO OTA command.

## Packet formats (PC → ESP32)
- LED: `[0xAA, 0xBB, 0x01, 2048 bytes brightness]`
- Servo: `[0xAA, 0xBB, 0x02, 6 × uint16 big-endian (0–1000)]`

## Handoff notes
- Firmware binaries: `firmware/binaries`; sources: `firmware/esp32`.
- Logs: `logs/`; GUI health/diagnostics write here.
- Core code: `packages/mirror_core`; GUI: `apps/gui/main.py`; helpers: `apps/cli/`.
- Tests: `packages/mirror_core/tests/`.
