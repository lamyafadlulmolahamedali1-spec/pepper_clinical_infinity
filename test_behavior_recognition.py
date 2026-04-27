#!/usr/bin/env python3
"""اختبار كشف السلوك - Behavioural Video Recognition"""
import cv2
import numpy as np

print("🔬 Testing Behavioural Video Recognition")
print("="*50)

cap = cv2.VideoCapture(0)
prev_frame = None
hand_flapping_count = 0

print("🎥 Camera opened. Show hand flapping movements...")

for _ in range(100):
    ret, frame = cap.read()
    if not ret:
        continue
    
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    if prev_frame is not None:
        flow = cv2.calcOpticalFlowFarneback(prev_frame, gray, None, 0.5, 3, 15, 3, 5, 1.2, 0)
        magnitude, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
        rapid_motion = np.sum(magnitude > 2) / magnitude.size
        if rapid_motion > 0.3:
            hand_flapping_count += 1
            cv2.putText(frame, "⚠️ Hand Flapping Detected!", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    
    prev_frame = gray
    cv2.putText(frame, f"Hand Flapping Count: {hand_flapping_count}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    cv2.imshow("Behavior Recognition Test", frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
print(f"✅ Test complete! Detected {hand_flapping_count} hand flapping events")
