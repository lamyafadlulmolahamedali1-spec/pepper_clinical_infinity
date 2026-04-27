import cv2
import numpy as np

print("📷 Testing camera...")

# Try different camera indices
for idx in [0, 1, 2]:
    print(f"\nTrying camera index {idx}...")
    cap = cv2.VideoCapture(idx)
    if cap.isOpened():
        print(f"✅ Camera {idx} opened!")
        ret, frame = cap.read()
        if ret:
            print(f"✅ Frame captured! Size: {frame.shape}")
            # Save a test image
            cv2.imwrite(f"test_camera_{idx}.jpg", frame)
            print(f"📸 Saved test_camera_{idx}.jpg")
        cap.release()
    else:
        print(f"❌ Camera {idx} not available")
