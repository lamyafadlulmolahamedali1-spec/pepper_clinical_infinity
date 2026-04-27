#!/usr/bin/env python3
"""
Simplified Autism Detection System
- Emotion Recognition (DeepFace)
- Person Detection (YOLO)
- Session Recording
"""

import cv2
import numpy as np
from ultralytics import YOLO
from deepface import DeepFace
import time
import json
import os
from datetime import datetime
import pandas as pd

class AutismDetectionSystem:
    def __init__(self):
        print("🤖 Initializing Autism Detection System...")
        
        # Initialize YOLO
        print("📷 Loading YOLO model...")
        self.model = YOLO('yolov8n.pt')
        
        # Open camera
        self.cap = cv2.VideoCapture(1)
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(0)
        
        if not self.cap.isOpened():
            print("❌ No camera found!")
            exit()
        
        print("✅ Camera ready! Press 'q' to quit, 's' to save session, 'r' to start/stop recording")
        
        # Detection variables
        self.emotion = "neutral"
        self.emotion_history = []
        
        # Session recording
        self.session_data = []
        self.session_active = False
        self.session_start_time = None
        self.session_folder = f"autism_sessions_{datetime.now().strftime('%Y%m%d')}"
        
        # Create session folder
        if not os.path.exists(self.session_folder):
            os.makedirs(self.session_folder)
        
        # Window settings
        self.window_name = "ASD Detection System"
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.window_name, 1024, 768)
        
        self.run()
    
    def detect_emotion_from_face(self, face_img):
        """Detect emotion from face"""
        try:
            result = DeepFace.analyze(face_img, actions=['emotion'], enforce_detection=False)
            return result[0]['dominant_emotion']
        except:
            return "neutral"
    
    def calculate_asd_risk_score(self):
        """Calculate ASD risk based on emotion patterns"""
        if len(self.emotion_history) == 0:
            return {
                'risk_percentage': 0,
                'risk_level': "Insufficient Data",
                'recommendation': "Continue monitoring for more data"
            }
        
        # Count emotions
        emotion_counts = {}
        for e in self.emotion_history[-100:]:  # Last 100 frames
            emotion_counts[e] = emotion_counts.get(e, 0) + 1
        
        total = sum(emotion_counts.values())
        
        # Atypical emotions (potential ASD indicators)
        atypical = emotion_counts.get('angry', 0) + emotion_counts.get('fear', 0) + emotion_counts.get('sad', 0)
        neutral = emotion_counts.get('neutral', 0)
        
        if total > 0:
            atypical_ratio = atypical / total
            neutral_ratio = neutral / total
            
            # Simple risk calculation
            risk_percentage = (atypical_ratio * 100) + (neutral_ratio * 30)
            risk_percentage = min(100, risk_percentage)
            
            if risk_percentage < 30:
                risk_level = "Low"
                recommendation = "Continue monitoring"
            elif risk_percentage < 60:
                risk_level = "Moderate"
                recommendation = "Consult with specialist"
            else:
                risk_level = "High"
                recommendation = "Immediate professional consultation recommended"
        else:
            risk_percentage = 0
            risk_level = "No Data"
            recommendation = "Collect more data"
        
        return {
            'risk_percentage': risk_percentage,
            'risk_level': risk_level,
            'recommendation': recommendation,
            'emotion_counts': emotion_counts
        }
    
    def save_session_data(self):
        """Save current session data"""
        if not self.session_data:
            print("No data to save")
            return
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{self.session_folder}/session_{timestamp}.csv"
        
        df = pd.DataFrame(self.session_data)
        df.to_csv(filename, index=False)
        
        # Save risk assessment
        risk = self.calculate_asd_risk_score()
        summary_file = f"{self.session_folder}/summary_{timestamp}.json"
        with open(summary_file, 'w') as f:
            json.dump({
                'timestamp': timestamp,
                'duration_seconds': time.time() - self.session_start_time if self.session_start_time else 0,
                'risk_assessment': risk,
                'total_data_points': len(self.session_data)
            }, f, indent=2)
        
        print(f"✅ Session saved to {filename}")
        print(f"✅ Summary saved to {summary_file}")
        
        print("\n📊 ASD Risk Assessment:")
        print(f"Risk Level: {risk['risk_level']}")
        print(f"Risk Score: {risk['risk_percentage']:.1f}%")
        print(f"Recommendation: {risk['recommendation']}")
    
    def run(self):
        """Main detection loop"""
        frame_count = 0
        
        while True:
            ret, frame = self.cap.read()
            if not ret:
                continue
            
            # Resize for better performance
            frame = cv2.resize(frame, (1024, 768))
            
            # YOLO detection
            results = self.model(frame, verbose=False)
            persons = []
            
            for r in results:
                if r.boxes:
                    for box in r.boxes:
                        cls = int(box.cls[0])
                        conf = float(box.conf[0])
                        name = self.model.names[cls]
                        
                        if name == 'person' and conf > 0.5:
                            x1, y1, x2, y2 = map(int, box.xyxy[0])
                            persons.append((x1, y1, x2, y2))
                            
                            # Crop face for emotion
                            face = frame[y1:y2, x1:x2]
                            if face.size > 0 and face.shape[0] > 50:
                                self.emotion = self.detect_emotion_from_face(face)
                                self.emotion_history.append(self.emotion)
                            
                            # Draw bounding box
                            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 3)
                            
                            # Emotion with emoji
                            emoji = {'happy':'😊', 'sad':'😢', 'angry':'😠', 
                                    'surprise':'😲', 'fear':'😨', 'neutral':'😐'}.get(self.emotion, '😐')
                            cv2.putText(frame, f"{self.emotion.upper()} {emoji}", (x1, y1-10),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Calculate ASD risk
            risk = self.calculate_asd_risk_score()
            
            # Draw information panel
            panel_y = 30
            cv2.rectangle(frame, (10, 10), (400, 150), (0, 0, 0), -1)
            cv2.putText(frame, f"Emotion: {self.emotion.upper()}", (20, panel_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            panel_y += 25
            cv2.putText(frame, f"Persons: {len(persons)}", (20, panel_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            panel_y += 25
            cv2.putText(frame, f"ASD Risk: {risk['risk_percentage']:.0f}% ({risk['risk_level']})", (20, panel_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255) if risk['risk_level'] == 'High' else (0, 255, 0), 2)
            panel_y += 25
            
            # Show session status
            if self.session_active:
                elapsed = time.time() - self.session_start_time
                cv2.putText(frame, f"RECORDING: {elapsed:.0f}s", (frame.shape[1]-200, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            
            # Show frame
            cv2.imshow(self.window_name, frame)
            
            # Handle keyboard input
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                self.save_session_data()
            elif key == ord('r'):
                if not self.session_active:
                    self.session_active = True
                    self.session_start_time = time.time()
                    self.session_data = []
                    print("🔴 Session recording started...")
                else:
                    self.session_active = False
                    print("⏹️ Session recording stopped")
            
            # Record session data
            if self.session_active:
                session_entry = {
                    'timestamp': time.time(),
                    'emotion': self.emotion,
                    'persons_detected': len(persons)
                }
                self.session_data.append(session_entry)
        
        # Save data before exit
        if self.session_active and self.session_data:
            self.save_session_data()
        
        self.cap.release()
        cv2.destroyAllWindows()
        print("✅ System closed")
        
        # Print final assessment
        final_risk = self.calculate_asd_risk_score()
        print("\n" + "="*50)
        print("FINAL ASD RISK ASSESSMENT")
        print("="*50)
        print(f"Risk Level: {final_risk['risk_level']}")
        print(f"Risk Score: {final_risk['risk_percentage']:.1f}%")
        print(f"Recommendation: {final_risk['recommendation']}")

if __name__ == "__main__":
    system = AutismDetectionSystem()
