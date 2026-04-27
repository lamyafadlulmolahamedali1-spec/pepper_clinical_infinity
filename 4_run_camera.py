import cv2
from ultralytics import YOLO
from deepface import DeepFace

print("📷 Loading YOLO...")
model = YOLO("yolov8n.pt")
print("😊 Loading Emotion...")

cap = cv2.VideoCapture(1)
if not cap.isOpened():
    cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("❌ No camera found!")
    exit()

cv2.namedWindow("Lamia - Emotion", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Lamia - Emotion", 400, 300)

emotion = "neutral"
PERSON_NAME = "Lamia"

while True:
    ret, frame = cap.read()
    if not ret:
        continue
    frame = cv2.resize(frame, (400, 300))
    results = model(frame, verbose=False)
    for r in results:
        if r.boxes:
            for box in r.boxes:
                if model.names[int(box.cls[0])] == "person":
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    face = frame[y1:y2, x1:x2]
                    if face.size > 0 and face.shape[0] > 20:
                        try:
                            result = DeepFace.analyze(face, actions=["emotion"], enforce_detection=False)
                            emotion = result[0]["dominant_emotion"]
                        except:
                            pass
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(frame, PERSON_NAME, (x1, y1-22), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                    emoji = {"happy":"😊","sad":"😢","angry":"😠","surprise":"😲","neutral":"😐"}.get(emotion, "😐")
                    cv2.putText(frame, f"{emotion.upper()} {emoji}", (x1, y1-8), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
    cv2.imshow("Lamia - Emotion", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
print("✅ Camera closed")
