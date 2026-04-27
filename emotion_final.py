#!/usr/bin/env python3
"""
Face & Emotion Detection - Final Working Version
"""

import cv2
import time
import os

# Suppress TensorFlow warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

# Try to import DeepFace
try:
    from deepface import DeepFace
    print("✅ DeepFace loaded successfully")
    deepface_ready = True
except Exception as e:
    print(f"⚠️ DeepFace error: {e}")
    print("Installing required packages...")
    import subprocess
    import sys
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'tensorflow', 'deepface'])
    from deepface import DeepFace
    deepface_ready = True

# Load face cascade
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Open camera
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    cap = cv2.VideoCapture(1)
    if not cap.isOpened():
        cap = cv2.VideoCapture(2)

if not cap.isOpened():
    print("❌ No camera found! Please check:")
    print("  1. Camera is connected")
    print("  2. Camera is not in use by another app")
    exit()

print("\n" + "="*50)
print("✅ CAMERA WORKING!")
print("="*50)
print("🎮 Controls:")
print("   'q' - Quit")
print("   'e' - Toggle emotion detection")
print("="*50 + "\n")

emotion = "neutral"
emotion_enabled = True
last_detection = 0
detection_interval = 1.0  # Detect every 1 second

while True:
    ret, frame = cap.read()
    if not ret:
        print("⚠️ Failed to grab frame")
        continue
    
    # Flip frame horizontally for mirror effect
    frame = cv2.flip(frame, 1)
    
    # Detect faces
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)
    
    current_time = time.time()
    
    for (x, y, w, h) in faces:
        # Emotion detection
        if emotion_enabled and deepface_ready and (current_time - last_detection) >= detection_interval:
            face_roi = frame[y:y+h, x:x+w]
            if face_roi.size > 0 and face_roi.shape[0] > 30:
                try:
                    result = DeepFace.analyze(face_roi, 
                                              actions=['emotion'],
                                              enforce_detection=False,
                                              silent=True)
                    emotion = result[0]['dominant_emotion']
                    last_detection = current_time
                except:
                    pass
        
        # Color based on emotion
        emotion_colors = {
            'happy': (0, 255, 255),    # Yellow
            'sad': (255, 0, 0),        # Blue
            'angry': (0, 0, 255),      # Red
            'surprise': (255, 255, 0), # Cyan
            'fear': (255, 0, 255),     # Purple
            'disgust': (0, 255, 255),  # Yellow
            'neutral': (0, 255, 0)     # Green
        }
        emotion_emojis = {
            'happy': '😊', 'sad': '😢', 'angry': '😠',
            'surprise': '😲', 'fear': '😨', 'disgust': '🤢',
            'neutral': '😐'
        }
        
        color = emotion_colors.get(emotion, (0, 255, 0))
        emoji = emotion_emojis.get(emotion, '😐')
        
        # Draw rectangle and text
        cv2.rectangle(frame, (x, y), (x+w, y+h), color, 3)
        
        if emotion_enabled:
            text = f"{emoji} {emotion.upper()}"
            cv2.putText(frame, text, (x, y-15),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        else:
            cv2.putText(frame, "FACE", (x, y-15),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    # Info panel
    info_y = 25
    cv2.rectangle(frame, (5, 5), (350, 120), (0, 0, 0), -1)
    cv2.putText(frame, f"👤 Faces: {len(faces)}", (10, info_y),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    info_y += 25
    cv2.putText(frame, f"😊 Emotion: {emotion.upper()}", (10, info_y),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    info_y += 25
    status = "ON" if emotion_enabled else "OFF"
    color = (0, 255, 0) if emotion_enabled else (0, 0, 255)
    cv2.putText(frame, f"🎭 Emotion Detection: {status}", (10, info_y),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    info_y += 25
    cv2.putText(frame, "Press 'q' to quit | 'e' toggle emotion", (10, info_y),
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    
    # Show frame
    cv2.imshow("Face & Emotion Detection", frame)
    
    # Handle keys
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('e'):
        emotion_enabled = not emotion_enabled
        print(f"\n🔄 Emotion detection: {'ON' if emotion_enabled else 'OFF'}\n")

# Cleanup
cap.release()
cv2.destroyAllWindows()
print("\n✅ Camera closed. Goodbye!")
