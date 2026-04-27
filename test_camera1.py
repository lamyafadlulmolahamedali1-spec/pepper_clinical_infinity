import cv2
import numpy as np

print("📷 Testing camera index 1...")

cap = cv2.VideoCapture(1)

if cap.isOpened():
    print("✅ Camera 1 opened successfully!")
    
    # Read one frame
    ret, frame = cap.read()
    if ret:
        print(f"✅ Frame captured! Size: {frame.shape}")
        
        # Save test image
        cv2.imwrite("camera1_test.jpg", frame)
        print("📸 Saved camera1_test.jpg")
        
        # Show camera window for 5 seconds
        print("🎥 Showing camera feed for 5 seconds... Press 'q' to quit early")
        
        start_time = cv2.getTickCount()
        while True:
            ret, frame = cap.read()
            if ret:
                cv2.putText(frame, "Camera 1 - Press q to quit", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.imshow("Camera 1 Test", frame)
            
            # Quit after 5 seconds or on 'q'
            elapsed = (cv2.getTickCount() - start_time) / cv2.getTickFrequency()
            if elapsed > 5 or cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        cv2.destroyAllWindows()
        print("✅ Camera window closed")
    else:
        print("❌ Could not read frame from camera 1")
    
    cap.release()
else:
    print("❌ Camera 1 not available")
    print("Trying camera 0 as fallback...")
    
    cap2 = cv2.VideoCapture(0)
    if cap2.isOpened():
        print("✅ Camera 0 opened!")
        ret, frame = cap2.read()
        if ret:
            cv2.imwrite("camera0_test.jpg", frame)
            print("📸 Saved camera0_test.jpg")
        cap2.release()
    else:
        print("❌ No camera found")

print("\n📋 To see saved images:")
print("   ls -la *.jpg")
