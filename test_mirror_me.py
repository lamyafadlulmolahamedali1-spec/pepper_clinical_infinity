#!/usr/bin/env python3
"""اختبار MirrorMe - تعليم المشاعر بالمرآة"""
import cv2
from deepface import DeepFace

print("🔬 Testing MirrorMe - Emotion Mirroring")
print("="*50)

cap = cv2.VideoCapture(0)
print("🎥 Camera opened. Show your face and make expressions!")
print("😊 Happy  |  😢 Sad  |  😲 Surprise  |  😠 Angry")

emotion_emoji = {
    "happy": "😊", "sad": "😢", "angry": "😠", 
    "surprise": "😲", "fear": "😨", "neutral": "😐"
}

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    try:
        result = DeepFace.analyze(frame, actions=['emotion'], enforce_detection=False)
        emotion = result[0]['dominant_emotion']
        emoji = emotion_emoji.get(emotion, "😐")
        
        cv2.putText(frame, f"Mirror: {emotion.upper()} {emoji}", (10, 50), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
        cv2.putText(frame, "MirrorMe - Copy my expression!", (10, 90), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    except:
        cv2.putText(frame, "No face detected", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    
    cv2.imshow("MirrorMe - Emotion Mirroring", frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
print("✅ Test complete!")
