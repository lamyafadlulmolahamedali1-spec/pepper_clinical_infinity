#!/usr/bin/env python3
"""
Face Detection + Emotion Recognition - Working Version
"""

import cv2
import numpy as np
import time

# Load face detector
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Try to load DeepFace for emotion detection
try:
    from deepface import DeepFace
    deepface_available = True
    print("✅ DeepFace loaded - Emotion detection available")
except ImportError:
    print("⚠️ DeepFace not found. Installing...")
    import subprocess
    import sys
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'deepface'])
    from deepface import DeepFace
    deepface_available = True
    print("✅ DeepFace installed and loaded")

# Open camera
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    cap = cv2.VideoCapture(1)

if not cap.isOpened():
    print("❌ No camera found!")
    exit()

print("\n✅ Camera opened successfully!")
print("🎮 Controls: 'q' to quit, 'e' to toggle emotion detection\n")

# Settings
emotion_detection_enabled = True
emotion = "neutral"
last_detection_time = 0
detection_interval = 1.0  # Detect emotion every 1 second

while True:
    ret, frame = cap.read()
    if not ret:
        continue
    
    # Convert to grayscale for face detection
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Detect faces
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)
    
    current_time = time.time()
    
    for (x, y, w, h) in faces:
        # Draw rectangle around face
        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
        
        # Detect emotion (only if enabled and time interval passed)
        if emotion_detection_enabled and (current_time - last_detection_time) >= detection_interval:
            face_roi = frame[y:y+h, x:x+w]
            if face_roi.size > 0 and face_roi.shape[0] > 30 and face_roi.shape[1] > 30:
                try:
                    result = DeepFace.analyze(face_roi, 
                                              actions=['emotion'], 
                                              enforce_detection=False,
                                              silent=True)
                    emotion = result[0]['dominant_emotion']
                    last_detection_time = current_time
                except Exception as e:
                    pass  # Keep previous emotion
        
        # Choose color based on emotion
        if emotion == 'happy':
            color = (0, 255, 255)  # Yellow
            emoji = "😊"
        elif emotion == 'sad':
            color = (255, 0, 0)    # Blue
            emoji = "😢"
        elif emotion == 'angry':
            color = (0, 0, 255)    # Red
            emoji = "😠"
        elif emotion == 'surprise':
            color = (255, 255, 0)  # Cyan
            emoji = "😲"
        elif emotion == 'fear':
            color = (255, 0, 255)  # Purple
            emoji = "😨"
        elif emotion == 'disgust':
            color = (0, 255, 255)  # Yellow
            emoji = "🤢"
        else:  # neutral
            color = (0, 255, 0)    # Green
            emoji = "😐"
        
        # Update rectangle color with emotion
        cv2.rectangle(frame, (x, y), (x+w, y+h), color, 3)
        
        # Display emotion text
        if emotion_detection_enabled:
            emotion_text = f"{emoji} {emotion.upper()}"
            cv2.putText(frame, emotion_text, (x, y-15),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        else:
            cv2.putText(frame, "Face", (x, y-15),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    # Draw information panel
    info_y = 30
    cv2.rectangle(frame, (5, 5), (350, 130), (0, 0, 0), -1)
    cv2.putText(frame, f"Faces: {len(faces)}", (10, info_y),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    info_y += 25
    cv2.putText(frame, f"Emotion: {emotion.upper()}", (10, info_y),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    info_y += 25
    cv2.putText(frame, f"Emotion Detection: {'ON' if emotion_detection_enabled else 'OFF'}", (10, info_y),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0) if emotion_detection_enabled else (0, 0, 255), 2)
    info_y += 25
    cv2.putText(frame, "Press 'q' to quit | 'e' toggle emotion", (10, info_y),
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    
    # Show frame
    cv2.imshow("Face & Emotion Detection", frame)
    
    # Handle keyboard input
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('e'):
        emotion_detection_enabled = not emotion_detection_enabled
        status = "ON" if emotion_detection_enabled else "OFF"
        print(f"🔄 Emotion detection turned {status}")

# Cleanup
cap.release()
cv2.destroyAllWindows()
print("\n✅ Camera closed successfully!")
