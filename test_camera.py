import cv2
import time
from ultralytics import YOLO

print("📷 Loading YOLO...")
model = YOLO('yolov8n.pt')

print("🎥 Opening camera...")
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("❌ Camera not found!")
    exit()

print("✅ Camera working! Window opening in 2 seconds...")
time.sleep(2)

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    # Detect people
    results = model(frame)
    for r in results:
        boxes = r.boxes
        if boxes is not None:
            for box in boxes:
                cls = int(box.cls[0])
                if model.names[cls] == 'person':
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 3)
                    cv2.putText(frame, "Person: Lamia", (x1, y1-10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    cv2.imshow('YOLO Detection - Lamia', frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
print("✅ Camera closed")
