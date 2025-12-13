import cv2
import time
import sys
import serial
import serial.tools.list_ports
import mediapipe as mp
import numpy as np

print("🚀 Starting Crash Debugger...")

# 1. SETUP SERIAL
print("\n[1] Finding ESP32...")
ports = serial.tools.list_ports.comports()
esp_port = None
for p in ports:
    if "CP210" in p.description or "CH340" in p.description or "USB" in p.description:
        esp_port = p.device
        break

if esp_port:
    print(f"✅ Found ESP32 at {esp_port}")
    try:
        ser = serial.Serial(esp_port, 460800, timeout=1)
        print("✅ Serial Opened")
    except Exception as e:
        print(f"❌ Serial Failed: {e}")
        ser = None
else:
    print("⚠️ No ESP32 found - Skipping Serial Test")
    ser = None

# 2. SETUP MEDIAPIPE
print("\n[2] Init MediaPipe...")
try:
    mp_pose = mp.solutions.pose
    pose = mp_pose.Pose(
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
        model_complexity=0,
        enable_segmentation=True,  # Suspect this might be the cause
        smooth_landmarks=False
    )
    print("✅ MediaPipe Initialized")
except Exception as e:
    print(f"❌ MediaPipe Failed: {e}")
    sys.exit(1)

# 3. MAIN LOOP
print("\n[3] Starting Capture Loop (Press Ctrl+C to stop)...")
cap = cv2.VideoCapture(0 if len(sys.argv) < 2 else int(sys.argv[1]))

if not cap.isOpened():
    print("❌ Camera 0 failed")
    sys.exit(1)

frame_count = 0
try:
    while True:
        ret, frame = cap.read()
        if not ret:
            print("⚠️ Frame drop")
            continue
            
        # A. Processing
        print(f"Frame {frame_count}: Processing...", end='\r')
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(frame_rgb)
        
        # B. Serial Write
        if ser:
            # Send dummy packet
            packet = bytes([0xAA, 90, 90, 90, 90, 90, 90, 180]) # Simple Neutral Packet
            ser.write(packet)
            
        frame_count += 1
        if frame_count % 30 == 0:
            print(f"\n✅ {frame_count} frames processed OK")
            
        cv2.imshow("Debug", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
            
except KeyboardInterrupt:
    print("\n✓ User Interrupted")
except Exception as e:
    print(f"\n❌ CRASHED WITH EXCEPTION: {e}")
    import traceback
    traceback.print_exc()

print("\n✓ Debug Session Finished Cleanly")
if ser: ser.close()
cap.release()
cv2.destroyAllWindows()
