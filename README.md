# Mechanical Mirror (Motors Branch)

This is the **Motor Control** specialized branch of the Kinetic Mirror project. It is designed to control a 64-motor array using computer vision to mirror a human silhouette.

## Features
- **Robust Tracking**: Uses MediaPipe Pose Segmentation with a seamless fallback to **MOG2 Background Subtraction**.
- **Static Detection**: Detects human presence even when standing still (detects "blocked" areas).
- **Visualization**: High-contrast "Blue Film" background with "Green Body" silhouette for clear feedback.
- **Motor Control**: Maps the 64-motor grid (8x8) directly to the detected silhouette.
- **Single App Architecture**: Consolidated GUI for simplified usage.

## Hardware Support
- **Microcontroller**: ESP32-S3 (or compatible).
- **Motors**: 64x SG90 Servos (via PCA9685 drivers).
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

## Usage
1.  **Launch the App**: The window will open showing the camera feed.
2.  **Calibration**: Step out of the frame for 1 second to let the specific background subtractor learn the empty room.
3.  **Step In**: Walk into the frame. You will see your body highlighted in **Green** against a **Blue** background.
4.  **Interaction**: The 64 simulated (or real) motors will react to your presence immediately.
