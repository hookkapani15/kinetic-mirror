import cv2
import numpy as np
import logging
import threading

logger = logging.getLogger("main")

class BodySegmenter:
    """
    Optimized body segmentation - balances speed and detection quality.
    - Moderate processing resolution for reliable detection
    - Light temporal smoothing to reduce flicker
    - Fast morphology for clean edges
    """
    def __init__(self):
        import mediapipe as mp
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision as mp_vision
        from pathlib import Path
        import urllib.request
        import ssl
        
        # Ensure data dir exists
        model_path = Path("data/selfie_segmenter.tflite")
        model_path.parent.mkdir(exist_ok=True)
        
        if not model_path.exists():
            logger.info("Downloading segmentation model...")
            url = "https://storage.googleapis.com/mediapipe-models/image_segmenter/selfie_segmenter/float16/latest/selfie_segmenter.tflite"
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            with urllib.request.urlopen(url, context=ctx) as u, open(model_path, 'wb') as f:
                f.write(u.read())
            logger.info("Model downloaded")
        
        base_options = mp_python.BaseOptions(model_asset_path=str(model_path))
        options = mp_vision.ImageSegmenterOptions(
            base_options=base_options,
            running_mode=mp_vision.RunningMode.VIDEO,
            output_category_mask=True
        )
        self.segmenter = mp_vision.ImageSegmenter.create_from_options(options)
        self.frame_count = 0
        
        # No temporal smoothing — benchmark shows instant response is best
        # (camera is the bottleneck at 25 FPS, not processing)
        self.mask_buffer = None
        self.smoothing = 0.0  # 0 = instant (no lag), set >0 for stability
        
        # Morphology kernels (5x5 close: 0.07ms vs 7x7: 0.12ms per benchmark)
        self.kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        self.kernel_dilate = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        
    def get_body_mask(self, frame):
        """
        Body mask extraction with good detection quality.
        Returns binary mask (0 or 255)
        """
        self.frame_count += 1
        h, w = frame.shape[:2]
        
        # Benchmark-optimized: 192x144 saves 0.7ms vs 256x192, same detection
        proc_w, proc_h = 192, 144
        
        small = cv2.resize(frame, (proc_w, proc_h), interpolation=cv2.INTER_LINEAR)
        small_rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
        
        import mediapipe as mp
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=small_rgb)
        
        # Run segmentation with strictly increasing timestamps
        import time
        if not hasattr(self, '_last_timestamp'):
            self._last_timestamp = 0
            self._timestamp_lock = threading.Lock()
            
        with self._timestamp_lock:
            timestamp_ms = int(time.time() * 1000)
            if timestamp_ms <= self._last_timestamp:
                timestamp_ms = self._last_timestamp + 1
            self._last_timestamp = timestamp_ms
            
        result = self.segmenter.segment_for_video(mp_image, timestamp_ms)
        
        if result.category_mask is None:
            return np.zeros((h, w), dtype=np.uint8)
        
        # Get mask as float for smoothing
        mask = result.category_mask.numpy_view()
        mask_float = (mask > 0).astype(np.float32)
        
        # Light temporal smoothing
        if self.mask_buffer is None:
            self.mask_buffer = mask_float.copy()
        else:
            self.mask_buffer = self.smoothing * self.mask_buffer + (1.0 - self.smoothing) * mask_float
        
        # Convert to binary
        binary = (self.mask_buffer > 0.4).astype(np.uint8) * 255
        
        # Morphology to clean up and fill holes
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, self.kernel_close)
        binary = cv2.dilate(binary, self.kernel_dilate, iterations=1)
        
        # Upscale to camera frame size
        return cv2.resize(binary, (w, h), interpolation=cv2.INTER_NEAREST)

    def close(self):
        if hasattr(self, 'segmenter'):
            self.segmenter.close()

    def get_led_mask(self, frame, led_width=32, led_height=64):
        """
        Get body mask directly resized for 32x64 LED matrix
        Optimized single-call for LED output
        """
        # Get full resolution mask
        body_mask = self.get_body_mask(frame)
        
        # Resize to LED dimensions with area interpolation (best for downscaling)
        led_mask = cv2.resize(body_mask, (led_width, led_height), interpolation=cv2.INTER_AREA)
        
        # Final threshold to ensure clean binary
        led_mask = (led_mask > 128).astype(np.uint8) * 255
        
        return led_mask
