#!/usr/bin/env python3
"""
Stage 2: Camera Detection
Verifies webcam is connected and functional.
"""
from .base_stage import BaseStage, CheckResult, StageResult


class CameraStage(BaseStage):
    """Check that a webcam is available and working."""
    
    def __init__(self):
        super().__init__(
            name="Camera Detection",
            description="Checking webcam availability..."
        )
    
    def run(self, callback=None) -> StageResult:
        checks = []
        
        # 1. Import OpenCV
        try:
            import cv2
        except ImportError:
            checks.append(CheckResult(
                name="OpenCV Import",
                passed=False,
                message="OpenCV not available",
                fix_instructions=["Complete Stage 1 first"]
            ))
            return self._make_result(checks)
        
        # 2. Find available cameras
        available_cameras = []
        for i in range(5):  # Check indices 0-4
            try:
                cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        available_cameras.append(i)
                    cap.release()
            except:
                pass
        
        camera_count = len(available_cameras)
        checks.append(CheckResult(
            name="Camera Detection",
            passed=camera_count > 0,
            message=f"Found {camera_count} camera(s): {available_cameras}" if camera_count > 0 else "No cameras found",
            fix_instructions=[] if camera_count > 0 else [
                "Connect a USB webcam",
                "Check Device Manager for camera",
                "Install camera drivers if needed"
            ],
            details={"cameras": available_cameras, "count": camera_count}
        ))
        if callback:
            callback("Camera Detection", checks[-1].passed, checks[-1].message)
        
        # 3. Test frame capture (if camera found)
        if camera_count > 0:
            test_cam = available_cameras[0]
            try:
                cap = cv2.VideoCapture(test_cam, cv2.CAP_DSHOW)
                ret, frame = cap.read()
                cap.release()
                
                if ret and frame is not None:
                    h, w = frame.shape[:2]
                    checks.append(CheckResult(
                        name="Frame Capture",
                        passed=True,
                        message=f"Camera {test_cam}: {w}x{h} resolution",
                        details={"width": w, "height": h, "camera": test_cam}
                    ))
                else:
                    checks.append(CheckResult(
                        name="Frame Capture",
                        passed=False,
                        message="Failed to read frame",
                        fix_instructions=[
                            "Close other apps using the camera",
                            "Try a different camera"
                        ]
                    ))
            except Exception as e:
                checks.append(CheckResult(
                    name="Frame Capture",
                    passed=False,
                    message=f"Error: {str(e)}",
                    fix_instructions=["Try restarting the application"]
                ))
            
            if callback:
                callback("Frame Capture", checks[-1].passed, checks[-1].message)
        
        return self._make_result(checks)
