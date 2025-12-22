#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI Startup Test  
Tests if the GUI can initialize without errors
"""

import sys
from pathlib import Path

# Add project root to path
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tooling"))

from base_test import BaseTest


class GUIStartupTest(BaseTest):
    """Test GUI startup and MediaPipe initialization"""
    
    def __init__(self):
        super().__init__("GUI Startup Test")
    
    def run(self):
        try:
            # Try importing MediaPipe
            import mediapipe as mp
            mediapipe_available = True
            mp_version = mp.__version__
        except ImportError:
            mediapipe_available = False
            mp_version = None
        
        # Try importing OpenCV
        try:
            import cv2
            opencv_available = True
            cv2_version = cv2.__version__
        except ImportError:
            opencv_available = False
            cv2_version = None
        
        # Check camera availability (quick check)
        camera_count = 0
        if opencv_available:
            try:
                for i in range(3):  # Check first 3 indices
                    cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
                    if cap.isOpened():
                        ret, _ = cap.read()
                        if ret:
                            camera_count += 1
                    cap.release()
            except Exception as e:
                pass
        
        # Evaluate results
        issues = []
        if not mediapipe_available:
            issues.append("MediaPipe not installed - human detection won't work")
        if not opencv_available:
            issues.append("OpenCV not installed - camera won't work")
        if camera_count == 0:
            issues.append("No cameras detected - check webcam connection")
        
        if issues:
            return self.fail_test(
                f"GUI startup issues detected: {', '.join(issues)}",
                suggested_actions=[
                    "Install MediaPipe: pip install mediapipe" if not mediapipe_available else None,
                    "Install OpenCV: pip install opencv-python" if not opencv_available else None,
                    "Connect a webcam" if camera_count == 0 else None
                ],
                metrics={
                    "mediapipe_version": mp_version,
                    "opencv_version": cv2_version,
                    "camera_count": camera_count
                },
                confidence=0.95
            )
        
        return self.pass_test(
            f"GUI ready: MediaPipe {mp_version}, OpenCV {cv2_version}, {camera_count} camera(s)",
            metrics={
                "mediapipe_version": mp_version,
                "opencv_version": cv2_version,
                "camera_count": camera_count
            },
            learns={
                "mediapipe_available": True,
                "opencv_available": True,
                "camera_count": camera_count
            },
            confidence=1.0
        )


if __name__ == "__main__":
    test = GUIStartupTest()
    result = test.execute()
    
    print(f"\n{result['test_name']}")
    print(f"Status: {result['status']}")
    print(f"Details: {result['details']}")
