#!/usr/bin/env python3
"""اختبار تصنيف المشاعر - Facial Emotion Classification"""
import cv2
from deepface import DeepFace

print("🔬 Testing Facial Emotion Classification")
print("="*50)

cap = cv2.VideoCapture(0)
print("🎥 Camera opened. Show your face...")

emotions_count = {"happy":0, "sad":0, "angry":0, "surprise":0, "neutral":0}

for _ in range(100):
    ret, frame = cap.read()
    if not ret:
        continue
    
    try:
        result = DeepFace.analyze(frame, actions=['emotion'], enforce_detection=False)
        emotion = result[0]['dominant_emotion']
        emotions_count[emotion] = emotions_count.get(emotion, 0) + 1
        cv2.putText(frame, f"Emotion: {emotion.upper()}", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    except:
        cv2.putText(frame, "No face detected", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    
    cv2.imshow("Emotion Classification Test", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
print(f"✅ Test complete! Emotions detected: {emotions_count}")
