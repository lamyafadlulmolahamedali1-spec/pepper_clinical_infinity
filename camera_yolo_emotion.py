#!/usr/bin/env python3
"""
Camera YOLO + Emotion Detection
- Object detection (YOLO)
- Emotion detection (DeepFace)
- Real-time camera feed
"""

import cv2
import numpy as np
from ultralytics import YOLO
from deepface import DeepFace
import time

class CameraDetection:
    def __init__(self):
        print("📷 Loading YOLO model...")
        self.model = YOLO('yolov8n.pt')
        print("😊 Loading Emotion detection...")
        
        # Open camera
        self.cap = cv2.VideoCapture(1)
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(0)
        
        if not self.cap.isOpened():
            print("❌ No camera found!")
            exit()
        
        print("✅ Camera ready! Press 'q' to quit")
        
        self.emotion = "neutral"
        self.person_name = "Lamia"
        
        # Window settings
        self.window_name = "YOLO + Emotion Detection"
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.window_name, 640, 480)
        
        self.run()
    
    def detect_emotion(self, face):
        """Detect emotion from face"""
        try:
            result = DeepFace.analyze(face, actions=['emotion'], enforce_detection=False)
            return result[0]['dominant_emotion']
        except:
            return "neutral"
    
    def run(self):
        """Main detection loop"""
        while True:
            ret, frame = self.cap.read()
            if not ret:
                continue
            
            # Resize for better performance
            frame = cv2.resize(frame, (640, 480))
            
            # YOLO detection
            results = self.model(frame, verbose=False)
            
            for r in results:
                if r.boxes:
                    for box in r.boxes:
                        cls = int(box.cls[0])
                        conf = float(box.conf[0])
                        name = self.model.names[cls]
                        
                        if name == 'person' and conf > 0.5:
                            x1, y1, x2, y2 = map(int, box.xyxy[0])
                            
                            # Crop face for emotion
                            face = frame[y1:y2, x1:x2]
                            if face.size > 0 and face.shape[0] > 30:
                                self.emotion = self.detect_emotion(face)
                            
                            # Draw bounding box
                            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 3)
                            
                            # Person name
                            cv2.putText(frame, self.person_name, (x1, y1-35),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                            
                            # Emotion with emoji
                            emoji = {'happy':'😊', 'sad':'😢', 'angry':'😠', 
                                    'surprise':'😲', 'fear':'😨', 'neutral':'😐'}.get(self.emotion, '😐')
                            cv2.putText(frame, f"{self.emotion.upper()} {emoji}", (x1, y1-10),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Show FPS
            cv2.putText(frame, f"Emotion: {self.emotion.upper()}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Show frame
            cv2.imshow(self.window_name, frame)
            
            # Press 'q' to quit
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        self.cap.release()
        cv2.destroyAllWindows()
        print("✅ Camera closed")

if __name__ == "__main__":
    camera = CameraDetection()
