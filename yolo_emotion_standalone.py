#!/usr/bin/env python3
"""
YOLO + Emotion Detection - Standalone Version
- Camera detects people and emotions
- Shows Person: [Name] and Emotion
- No PyBullet/Pepper required
"""

import cv2
import time
import numpy as np
from ultralytics import YOLO
from deepface import DeepFace

# ========== Settings ==========
PERSON_NAME = "Lamia"
CAMERA_INDEX = 1  # Camera 1 (change to 0 if needed)

print("\n" + "="*55)
print("🎥 YOLO + EMOTION DETECTION")
print("="*55)
print(f"👤 Person Name: {PERSON_NAME}")
print("😊 Detecting: Happy, Sad, Neutral, Surprise, Angry, Fear")
print("📷 Press 'q' to quit")
print("="*55)

# Load YOLO
print("\n📷 Loading YOLO model...")
model = YOLO('yolov8n.pt')
print("✅ YOLO loaded!")

# Open camera
print("🎥 Opening camera...")
cap = cv2.VideoCapture(CAMERA_INDEX)

if not cap.isOpened():
    print("❌ Camera 1 not found, trying camera 0...")
    cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("❌ No camera found!")
    exit()

print("✅ Camera working!")

# Emotion emojis
emotion_emojis = {
    'happy': '😊', 'sad': '😢', 'angry': '😠', 
    'fear': '😨', 'surprise': '😲', 'neutral': '😐',
    'disgust': '🤢', 'happy': '😊'
}

# Colors for different emotions
emotion_colors = {
    'happy': (0, 255, 0),      # Green
    'sad': (255, 0, 0),        # Blue
    'angry': (0, 0, 255),      # Red
    'surprise': (0, 255, 255), # Yellow
    'neutral': (200, 200, 200),# Gray
    'fear': (255, 0, 255)      # Purple
}

frame_count = 0
current_emotion = "neutral"
person_detected = False

while True:
    ret, frame = cap.read()
    if not ret:
        continue
    
    frame_count += 1
    
    # Resize for better performance
    frame = cv2.resize(frame, (640, 480))
    
    # Run YOLO detection every 5 frames (for speed)
    if frame_count % 5 == 0:
        results = model(frame)
        person_detected = False
        
        for r in results:
            boxes = r.boxes
            if boxes is not None:
                for box in boxes:
                    cls = int(box.cls[0])
                    conf = float(box.conf[0])
                    if model.names[cls] == 'person' and conf > 0.5:
                        person_detected = True
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        
                        # Crop face for emotion detection
                        face = frame[y1:y2, x1:x2]
                        if face.size > 0 and face.shape[0] > 30 and face.shape[1] > 30:
                            try:
                                result = DeepFace.analyze(face, actions=['emotion'], enforce_detection=False)
                                current_emotion = result[0]['dominant_emotion']
                            except Exception as e:
                                pass
                        
                        # Get color for emotion
                        color = emotion_colors.get(current_emotion, (0, 255, 0))
                        
                        # Draw bounding box
                        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)
                        
                        # Write "Person: Lamia"
                        cv2.putText(frame, f"Person: {PERSON_NAME}", (x1, y1 - 45), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
                        
                        # Write emotion with emoji
                        emoji = emotion_emojis.get(current_emotion, '😐')
                        cv2.putText(frame, f"Emotion: {current_emotion.upper()} {emoji}", 
                                   (x1, y1 - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    
    # Display info on frame
    if person_detected:
        status_color = emotion_colors.get(current_emotion, (0, 255, 0))
        status_text = f"✅ Person Detected | Emotion: {current_emotion.upper()} {emotion_emojis.get(current_emotion, '😐')}"
    else:
        status_color = (100, 100, 100)
        status_text = "👀 No person detected"
    
    cv2.putText(frame, status_text, (10, 30), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)
    
    # Add instructions
    cv2.putText(frame, "Press 'q' to quit", (10, frame.shape[0] - 10), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    
    # Show frame
    cv2.imshow('YOLO + Emotion Detection - Lamia', frame)
    
    # Print to terminal
    if person_detected:
        print(f"\r👤 {PERSON_NAME} | Emotion: {current_emotion.upper()} {emotion_emojis.get(current_emotion, '😐')}", end="")
    else:
        print(f"\r👀 No person detected", end="")
    
    # Quit on 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
print("\n\n✅ Detection stopped!")
