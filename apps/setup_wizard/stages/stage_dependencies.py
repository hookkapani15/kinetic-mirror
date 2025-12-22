#!/usr/bin/env python3
"""
Stage 1: Software Dependencies Check
Verifies all required Python packages are installed.
"""
import sys
from .base_stage import BaseStage, CheckResult, StageResult


class DependenciesStage(BaseStage):
    """Check that all required Python packages are installed."""
    
    def __init__(self):
        super().__init__(
            name="Software Dependencies",
            description="Checking required Python packages..."
        )
    
    def run(self, callback=None) -> StageResult:
        checks = []
        
        # 1. Python Version
        py_version = f"{sys.version_info.major}.{sys.version_info.minor}"
        py_ok = sys.version_info >= (3, 8)
        checks.append(CheckResult(
            name="Python Version",
            passed=py_ok,
            message=f"Python {py_version}" if py_ok else f"Python {py_version} (need 3.8+)",
            fix_instructions=[] if py_ok else [
                "Download Python 3.8+ from python.org",
                "Reinstall and add to PATH"
            ],
            details={"version": py_version}
        ))
        if callback:
            callback("Python Version", py_ok, checks[-1].message)
        
        # 2. MediaPipe
        try:
            import mediapipe as mp
            mp_version = mp.__version__
            checks.append(CheckResult(
                name="MediaPipe",
                passed=True,
                message=f"MediaPipe {mp_version}",
                details={"version": mp_version}
            ))
        except ImportError:
            checks.append(CheckResult(
                name="MediaPipe",
                passed=False,
                message="MediaPipe not installed",
                fix_instructions=["Run: pip install mediapipe"]
            ))
        if callback:
            callback("MediaPipe", checks[-1].passed, checks[-1].message)
        
        # 3. OpenCV
        try:
            import cv2
            cv_version = cv2.__version__
            checks.append(CheckResult(
                name="OpenCV",
                passed=True,
                message=f"OpenCV {cv_version}",
                details={"version": cv_version}
            ))
        except ImportError:
            checks.append(CheckResult(
                name="OpenCV",
                passed=False,
                message="OpenCV not installed",
                fix_instructions=["Run: pip install opencv-python"]
            ))
        if callback:
            callback("OpenCV", checks[-1].passed, checks[-1].message)
        
        # 4. PySerial
        try:
            import serial
            serial_version = serial.__version__
            checks.append(CheckResult(
                name="PySerial",
                passed=True,
                message=f"PySerial {serial_version}",
                details={"version": serial_version}
            ))
        except ImportError:
            checks.append(CheckResult(
                name="PySerial",
                passed=False,
                message="PySerial not installed",
                fix_instructions=["Run: pip install pyserial"]
            ))
        if callback:
            callback("PySerial", checks[-1].passed, checks[-1].message)
        
        # 5. NumPy
        try:
            import numpy as np
            np_version = np.__version__
            checks.append(CheckResult(
                name="NumPy",
                passed=True,
                message=f"NumPy {np_version}",
                details={"version": np_version}
            ))
        except ImportError:
            checks.append(CheckResult(
                name="NumPy",
                passed=False,
                message="NumPy not installed",
                fix_instructions=["Run: pip install numpy"]
            ))
        if callback:
            callback("NumPy", checks[-1].passed, checks[-1].message)
        
        # 6. Pillow
        try:
            from PIL import Image
            import PIL
            pil_version = PIL.__version__
            checks.append(CheckResult(
                name="Pillow",
                passed=True,
                message=f"Pillow {pil_version}",
                details={"version": pil_version}
            ))
        except ImportError:
            checks.append(CheckResult(
                name="Pillow",
                passed=False,
                message="Pillow not installed",
                fix_instructions=["Run: pip install Pillow"]
            ))
        if callback:
            callback("Pillow", checks[-1].passed, checks[-1].message)
        
        return self._make_result(checks)
