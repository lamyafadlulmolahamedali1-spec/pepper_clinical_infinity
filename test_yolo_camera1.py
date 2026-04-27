import cv2
import time
from ultralytics import YOLO

print("📷 Loading YOLO model...")
model = YOLO('yolov8n.pt')
print("✅ YOLO loaded!")

print("🎥 Opening camera 1...")
cap = cv2.VideoCapture(1)

if not cap.isOpened():
    print("❌ Camera 1 not found, trying camera 0...")
    cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("❌ No camera found!")
    exit()

print("✅ Camera working! Press 'q' to quit")
print("📷 Looking for people...")

while True:
    ret, frame = cap.read()
    if not ret:
        continue
    
    # Run YOLO detection
    results = model(frame)
    
    person_count = 0
    
    for r in results:
        boxes = r.boxes
        if boxes is not None:
            for box in boxes:
                cls = int(box.cls[0])
                conf = float(box.conf[0])
                name = model.names[cls]
                
                if name == 'person' and conf > 0.5:
                    person_count += 1
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    
                    # Draw GREEN bounding box
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 3)
                    cv2.putText(frame, f"Person ({conf:.2f})", (x1, y1-10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    
    # Show person count on frame
    cv2.putText(frame, f"People detected: {person_count}", (10, 30), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    # Show frame
    cv2.imshow('YOLO Test - Press q to quit', frame)
    
    print(f"\r👤 People detected: {person_count}", end="")
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
print("\n✅ Test complete!")
