import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)

class VisualVerifier:
    """
    Closed-loop visual verification system.
    Compares expected LED output (what we sent) vs observed LED output (what camera sees).
    """
    def __init__(self, target_width=32, target_height=64):
        self.target_w = target_width
        self.target_h = target_height
        self.homography = None
        self.input_pts = None # Points from camera (tl, tr, br, bl)
        
        # Target points for 32x64 rectified image
        # Order: TL, TR, BR, BL
        self.dst_pts = np.array([
            [0, 0],
            [target_width, 0],
            [target_width, target_height],
            [0, target_height]
        ], dtype=np.float32)

    def set_calibration_points(self, points):
        """Set the 4 corners of the LED wall in the camera frame (TL, TR, BR, BL)"""
        if len(points) != 4:
            logger.error("Calibration requires exactly 4 points")
            return
            
        self.input_pts = np.array(points, dtype=np.float32)
        self.homography = cv2.getPerspectiveTransform(self.input_pts, self.dst_pts)
        logger.info(f"Homography matrix calculated: \n{self.homography}")

    def auto_calibrate(self, frame):
        """
        Attempt to automatically find the LED wall corners.
        Robust version: uses blurring to merge the LED mesh/dots into a solid shape.
        """
        # 1. PREPROCESS: Grayscale + Blur to merge grid dots
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # Large blur is key to merging the individual LEDs/mesh into one solid block
        blurred = cv2.GaussianBlur(gray, (11, 11), 0)
        
        h, w = gray.shape[:2]
        frame_area = w * h
        logger.info(f"[Calib] Attempting auto-detection on {w}x{h} frame")
        
        # 2. THRESHOLDING: Try Otsu first, then fixed ranges
        thresh_strategies = [
            lambda img: cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1],
            lambda img: cv2.threshold(img, 150, 255, cv2.THRESH_BINARY)[1],
            lambda img: cv2.threshold(img, 100, 255, cv2.THRESH_BINARY)[1],
            lambda img: cv2.threshold(img, 60, 255, cv2.THRESH_BINARY)[1],
            lambda img: cv2.threshold(img, 30, 255, cv2.THRESH_BINARY)[1],
        ]
        
        for i, strategy in enumerate(thresh_strategies):
            thresh = strategy(blurred)
            
            # Morphological Cleanup
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
            thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)
            
            # Find Contours
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not contours:
                continue
                
            # Filter by area (between 2% and 90% of frame)
            min_area = frame_area * 0.02
            max_area = frame_area * 0.90
            
            # Sort by area
            valid_contours = []
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if min_area < area < max_area:
                    valid_contours.append(cnt)
            
            if not valid_contours:
                continue
            
            # Process best candidates
            valid_contours = sorted(valid_contours, key=cv2.contourArea, reverse=True)
            for cnt in valid_contours:
                # Use Convex Hull to ignore concave gaps/mask text
                hull = cv2.convexHull(cnt)
                epsilon = 0.02 * cv2.arcLength(hull, True)
                approx = cv2.approxPolyDP(hull, epsilon, True)
                
                # If we have 4 points, we found a quad
                if len(approx) == 4:
                    pts = approx.reshape(4, 2).astype(np.float32)
                    rect = self._sort_points(pts)
                    logger.info(f"[Calib] Strategy {i} SUCCESS! Area={cv2.contourArea(cnt):.0f}")
                    self.set_calibration_points(rect)
                    return rect
                
                # If we saved something close, maybe it's high vertex but basically a quad
                # Try higher epsilon
                epsilon_aggressive = 0.06 * cv2.arcLength(hull, True)
                approx_agg = cv2.approxPolyDP(hull, epsilon_aggressive, True)
                if len(approx_agg) == 4:
                    pts = approx_agg.reshape(4, 2).astype(np.float32)
                    rect = self._sort_points(pts)
                    logger.info(f"[Calib] Strategy {i} (Aggressive) SUCCESS! Area={cv2.contourArea(cnt):.0f}")
                    self.set_calibration_points(rect)
                    return rect
                    
        logger.warning("[Calib] Auto-calibration FAILED to find LED wall. Use manual mode.")
        return None

    def _sort_points(self, pts):
        """Stable sorting for quad points: TL, TR, BR, BL"""
        rect = np.zeros((4, 2), dtype="float32")
        
        # Top-Left has smallest sum, Bottom-Right has largest sum
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        
        # Top-Right has smallest difference, Bottom-Left has largest difference
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]
        
        return rect
        
        logger.info("[Calib] FAILED: No quadrilateral found at any threshold")
        return None

    def verify_frame(self, camera_frame, expected_led_mask):
        """
        Compare camera frame against expected LED state.
        Returns metrics dict: {ber, accuracy, error_map}
        """
        if self.homography is None:
            return {'error': "Not calibrated"}
            
        # 1. Warp perspective
        warped = cv2.warpPerspective(camera_frame, self.homography, (self.target_w, self.target_h))
        
        # 2. Preprocess observed image
        # Convert to grayscale
        gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
        # Threshold to binary (observed state)
        _, observed_bin = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY)
        
        # 3. Preprocess expected image
        # Ensure it's binary 0-255
        expected_bin = (expected_led_mask > 128).astype(np.uint8) * 255
        
        # Resize expected if needed (though it should be 32x64 already)
        if expected_bin.shape[:2] != (self.target_h, self.target_w):
             expected_bin = cv2.resize(expected_bin, (self.target_w, self.target_h), interpolation=cv2.INTER_NEAREST)

        # 4. Compare
        error_map = cv2.absdiff(observed_bin, expected_bin)
        error_count = np.count_nonzero(error_map) # Count non-zero pixels (differences)
        total_pixels = self.target_w * self.target_h
        ber = error_count / total_pixels
        
        return {
            'ber': ber,
            'accuracy': 1.0 - ber,
            'warped': warped, # Return physical rectified image for "advanced" UI
            'observed': observed_bin,
            'error_map': error_map,
            'mismatch_count': error_count
        }
