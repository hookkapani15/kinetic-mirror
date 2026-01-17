"""
Camera Detection and Test Tool
Helps diagnose camera issues
"""

import cv2
import time

print("="*60)
print("CAMERA DETECTION TOOL")
print("="*60)
print()

print("Scanning for cameras (this may take a moment)...")
print()

available_cameras = []

for i in range(10):
    print(f"Testing camera index {i}...", end=" ")
    try:
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        time.sleep(0.2)  # Give camera time to initialize
        
        if cap.isOpened():
            # Try to read a frame
            ret, frame = cap.read()
            if ret and frame is not None:
                height, width, channels = frame.shape
                available_cameras.append(i)
                print(f"✓ WORKING ({width}x{height})")
            else:
                print("✗ Opened but can't read frames")
            cap.release()
        else:
            print("✗ Not available")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    time.sleep(0.1)

print()
print("="*60)
print(f"RESULTS: Found {len(available_cameras)} working camera(s)")
print("="*60)
print()

if available_cameras:
    print(f"Available camera indices: {available_cameras}")
    print()
    
    # Test first camera with live preview
    test_cam = available_cameras[0]
    print(f"Testing camera {test_cam} with live preview...")
    print("Press 'q' to quit the preview")
    print()
    
    cap = cv2.VideoCapture(test_cam, cv2.CAP_DSHOW)
    time.sleep(0.3)
    
    if cap.isOpened():
        frame_count = 0
        start_time = time.time()
        
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Failed to read frame!")
                break
            
            frame_count += 1
            elapsed = time.time() - start_time
            if elapsed > 0:
                fps = frame_count / elapsed
                cv2.putText(frame, f"Camera {test_cam} - FPS: {fps:.1f}", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.putText(frame, "Press 'q' to quit", 
                           (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            cv2.imshow(f"Camera {test_cam} Test", frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        cap.release()
        cv2.destroyAllWindows()
        print(f"✓ Camera test complete! Average FPS: {fps:.1f}")
    else:
        print("✗ Failed to open camera for preview")
else:
    print("No cameras found!")
    print()
    print("Troubleshooting steps:")
    print("1. Check if another application is using the camera")
    print("2. Check camera permissions in Windows Settings")
    print("3. Try disconnecting and reconnecting the camera")
    print("4. Check Device Manager for camera driver issues")
    print("5. Restart your computer")
    print()
    print("Common issues:")
    print("- Skype/Teams/Zoom may be using the camera in background")
    print("- Camera privacy settings may be blocking access")
    print("- Camera drivers may need updating")

print()
print("="*60)
