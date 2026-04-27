#!/usr/bin/env python3
"""
Camera YOLO + Emotion Detection - Working Version
"""

import cv2
import numpy as np
import time
import sys

# استيراد المكتبات بشكل آمن
try:
    from ultralytics import YOLO
    print("✅ YOLO loaded successfully")
except Exception as e:
    print(f"❌ Error loading YOLO: {e}")
    sys.exit(1)

try:
    from deepface import DeepFace
    print("✅ DeepFace loaded successfully")
except Exception as e:
    print(f"❌ Error loading DeepFace: {e}")
    sys.exit(1)

class CameraDetection:
    def __init__(self):
        print("\n📷 Starting Camera Detection System...")
        
        # Load YOLO model
        print("Loading YOLO model...")
        self.model = YOLO('yolov8n.pt')
        
        # Open camera
        print("Opening camera...")
        self.cap = cv2.VideoCapture(0)  # Use 0 instead of 1 first
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(1)
        
        if not self.cap.isOpened():
            print("❌ No camera found! Please check your camera.")
            sys.exit(1)
        
        # Set camera properties
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        print(f"✅ Camera opened successfully!")
        print(f"📐 Resolution: {int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}")
        
        self.emotion = "neutral"
        
        # Create window
        self.window_name = "Camera - YOLO + Emotion Detection"
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.window_name, 800, 600)
        
        print("\n🎮 Controls:")
        print("   'q' - Quit")
        print("   'r' - Reset")
        print("\nStarting detection...\n")
        
        self.run()
    
    def detect_emotion(self, face_img):
        """Detect emotion from face image"""
        if face_img is None or face_img.size == 0:
            return "neutral"
        
        try:
            # Resize face for faster processing
            face_resized = cv2.resize(face_img, (100, 100))
            result = DeepFace.analyze(face_resized, 
                                      actions=['emotion'], 
                                      enforce_detection=False,
                                      silent=True)
            return result[0]['dominant_emotion']
        except Exception as e:
            return "neutral"
    
    def run(self):
        """Main loop"""
        frame_count = 0
        process_every_n_frames = 3  # Process every 3 frames for better performance
        
        while True:
            ret, frame = self.cap.read()
            if not ret:
                print("Warning: Failed to grab frame")
                continue
            
            frame_count += 1
            
            # Detect objects and emotions
            results = self.model(frame, verbose=False)
            persons_detected = 0
            
            for r in results:
                if r.boxes:
                    for box in r.boxes:
                        cls = int(box.cls[0])
                        conf = float(box.conf[0])
                        name = self.model.names[cls]
                        
                        if name == 'person' and conf > 0.5:
                            persons_detected += 1
                            x1, y1, x2, y2 = map(int, box.xyxy[0])
                            
                            # Process emotion every N frames
                            if frame_count % process_every_n_frames == 0:
                                face_roi = frame[y1:y2, x1:x2]
                                if face_roi.size > 0 and face_roi.shape[0] > 30 and face_roi.shape[1] > 30:
                                    self.emotion = self.detect_emotion(face_roi)
                            
                            # Color based on emotion
                            color = (0, 255, 0)  # Default green
                            if self.emotion == 'happy':
                                color = (0, 255, 255)  # Yellow
                            elif self.emotion == 'sad':
                                color = (255, 0, 0)    # Blue
                            elif self.emotion == 'angry':
                                color = (0, 0, 255)    # Red
                            elif self.emotion == 'surprise':
                                color = (255, 255, 0)  # Cyan
                            
                            # Draw bounding box
                            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                            
                            # Person label
                            cv2.putText(frame, "Person", (x1, y1-25),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                            
                            # Emotion with emoji
                            emoji_map = {
                                'happy': '😊 HAPPY',
                                'sad': '😢 SAD',
                                'angry': '😠 ANGRY',
                                'surprise': '😲 SURPRISE',
                                'fear': '😨 FEAR',
                                'neutral': '😐 NEUTRAL'
                            }
                            emotion_text = emoji_map.get(self.emotion, '😐 NEUTRAL')
                            cv2.putText(frame, emotion_text, (x1, y2+20),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            # Draw information panel
            info_y = 30
            cv2.rectangle(frame, (5, 5), (300, 120), (0, 0, 0), -1)
            cv2.putText(frame, f"Persons: {persons_detected}", (10, info_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            info_y += 25
            cv2.putText(frame, f"Emotion: {self.emotion.upper()}", (10, info_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            info_y += 25
            cv2.putText(frame, "Press 'q' to quit", (10, info_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            
            # Show frame
            cv2.imshow(self.window_name, frame)
            
            # Handle key press
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("\n👋 Quitting...")
                break
            elif key == ord('r'):
                print("🔄 Resetting...")
                self.emotion = "neutral"
        
        # Cleanup
        self.cap.release()
        cv2.destroyAllWindows()
        print("✅ Camera closed successfully!")

if __name__ == "__main__":
    try:
        camera = CameraDetection()
    except KeyboardInterrupt:
        print("\n👋 Interrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}")
