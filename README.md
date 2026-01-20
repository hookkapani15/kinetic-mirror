# Mechanical Mirror (LEDs Branch)

This is the **LED Control** specialized branch of the Kinetic Mirror project. It is designed to control a 2048-LED matrix (32x64) using body tracking and interactive patterns.

## Features
- **LED Control**: Drives a 32x64 WS2812B LED matrix.
- **Body Tracking**: Maps human silhouette to the LED display.
- **Visualization**: Real-time GUI for monitoring and control.
- **Single App Architecture**: Consolidated GUI for simplified usage.

## Hardware Support
- **Microcontroller**: ESP32-S3 (or compatible).
- **Display**: 32x64 LED Matrix (WS2812B).
- **Camera**: Standard USB Webcam.

## Quick Start
### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Application
Simply double-click **`run.bat`** or run via command line:
```bash
python -m apps.gui.main
```
