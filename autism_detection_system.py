#!/usr/bin/env python3
"""
Autism Spectrum Disorder Detection System
Integrated Computer Vision System for ASD Detection
Features:
- Emotion Recognition
- Eye Tracking & Gaze Pattern Analysis
- Facial Landmark Distance Analysis
- Behavioural Recognition
- Child-Therapist Interaction Analysis
- Session Recording & Progress Tracking
"""

import cv2
import numpy as np
from ultralytics import YOLO
from deepface import DeepFace
import mediapipe as mp
import time
import json
import os
from datetime import datetime
import pandas as pd

class AutismDetectionSystem:
    def __init__(self):
        print("🤖 Initializing Autism Detection System...")
        
        # Initialize YOLO for object/person detection
        print("📷 Loading YOLO model...")
        self.model = YOLO('yolov8n.pt')
        
        # Initialize MediaPipe for face landmarks and eye tracking
        print("👁️ Loading MediaPipe Face Mesh...")
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=2,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # Initialize MediaPipe Pose for body movement
        print("💪 Loading MediaPipe Pose...")
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # Initialize MediaPipe Hands for gesture recognition
        print("🖐️ Loading MediaPipe Hands...")
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        
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
        self.person_name = "Child"
        self.therapist_name = "Therapist"
        
        # Eye tracking variables
        self.gaze_history = []
        self.blink_count = 0
        self.eye_aspect_ratio_history = []
        
        # Behavioural variables
        self.movement_history = []
        self.hand_gestures = []
        self.posture_history = []
        
        # Session recording
        self.session_data = []
        self.session_active = False
        self.session_start_time = None
        self.session_folder = f"autism_sessions_{datetime.now().strftime('%Y%m%d')}"
        
        # Create session folder
        if not os.path.exists(self.session_folder):
            os.makedirs(self.session_folder)
        
        # Autism risk indicators
        self.asd_indicators = {
            'reduced_eye_contact': 0,
            'repetitive_movements': 0,
            'atypical_facial_expressions': 0,
            'limited_gaze_sharing': 0,
            'hand_flapping': 0,
            'head_movements': 0
        }
        
        # Window settings
        self.window_name = "ASD Detection System"
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.window_name, 1024, 768)
        
        self.run()
    
    def calculate_eye_aspect_ratio(self, landmarks, eye_indices):
        """Calculate Eye Aspect Ratio for blink detection"""
        try:
            points = []
            for idx in eye_indices:
                point = landmarks[idx]
                points.append([point.x, point.y])
            points = np.array(points)
            
            # Calculate vertical distances
            v1 = np.linalg.norm(points[1] - points[5])
            v2 = np.linalg.norm(points[2] - points[4])
            # Calculate horizontal distance
            h = np.linalg.norm(points[0] - points[3])
            
            ear = (v1 + v2) / (2.0 * h)
            return ear
        except:
            return 0.0
    
    def analyze_gaze_pattern(self, face_landmarks, frame_shape):
        """Analyze gaze direction and eye contact"""
        h, w = frame_shape[:2]
        
        # Eye landmarks indices (MediaPipe Face Mesh)
        left_eye_indices = [33, 160, 158, 133, 153, 144]
        right_eye_indices = [362, 385, 387, 263, 373, 380]
        
        # Calculate eye aspect ratio for blink detection
        left_ear = self.calculate_eye_aspect_ratio(face_landmarks, left_eye_indices)
        right_ear = self.calculate_eye_aspect_ratio(face_landmarks, right_eye_indices)
        avg_ear = (left_ear + right_ear) / 2
        
        # Detect blinks (EAR < threshold)
        if avg_ear < 0.2:
            self.blink_count += 1
        
        # Store EAR for analysis
        self.eye_aspect_ratio_history.append(avg_ear)
        
        # Calculate gaze direction (simplified)
        left_eye_center = face_landmarks[33]
        right_eye_center = face_landmarks[263]
        nose_tip = face_landmarks[1]
        
        gaze_x = (left_eye_center.x + right_eye_center.x) / 2
        gaze_y = (left_eye_center.y + right_eye_center.y) / 2
        
        # Check if looking at camera (gaze directed forward)
        looking_at_camera = abs(gaze_x - 0.5) < 0.1 and abs(gaze_y - 0.5) < 0.1
        
        # Update ASD indicators
        if not looking_at_camera:
            self.asd_indicators['reduced_eye_contact'] += 1
        
        return {
            'ear': avg_ear,
            'blink_detected': avg_ear < 0.2,
            'looking_at_camera': looking_at_camera,
            'gaze_x': gaze_x,
            'gaze_y': gaze_y
        }
    
    def analyze_facial_landmarks_distance(self, face_landmarks):
        """Calculate distances between facial landmarks for ASD detection"""
        distances = {}
        
        # Key facial landmarks
        left_eye = face_landmarks[33]
        right_eye = face_landmarks[263]
        nose = face_landmarks[1]
        left_mouth = face_landmarks[61]
        right_mouth = face_landmarks[291]
        
        # Calculate distances
        eye_distance = np.sqrt((left_eye.x - right_eye.x)**2 + (left_eye.y - right_eye.y)**2)
        nose_eye_left = np.sqrt((nose.x - left_eye.x)**2 + (nose.y - left_eye.y)**2)
        nose_eye_right = np.sqrt((nose.x - right_eye.x)**2 + (nose.y - right_eye.y)**2)
        mouth_width = np.sqrt((left_mouth.x - right_mouth.x)**2 + (left_mouth.y - right_mouth.y)**2)
        
        distances.update({
            'eye_distance': eye_distance,
            'nose_left_eye': nose_eye_left,
            'nose_right_eye': nose_eye_right,
            'mouth_width': mouth_width
        })
        
        # Check for atypical facial features (simplified)
        if eye_distance < 0.05 or eye_distance > 0.15:
            self.asd_indicators['atypical_facial_expressions'] += 0.5
        
        return distances
    
    def analyze_body_movement(self, pose_landmarks):
        """Analyze body movement for repetitive behaviors"""
        if not pose_landmarks:
            return {}
        
        # Get key landmarks
        left_shoulder = pose_landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER]
        right_shoulder = pose_landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER]
        left_hip = pose_landmarks[self.mp_pose.PoseLandmark.LEFT_HIP]
        right_hip = pose_landmarks[self.mp_pose.PoseLandmark.RIGHT_HIP]
        
        # Calculate shoulder movement
        shoulder_center_x = (left_shoulder.x + right_shoulder.x) / 2
        shoulder_center_y = (left_shoulder.y + right_shoulder.y) / 2
        
        # Store movement
        current_movement = {
            'timestamp': time.time(),
            'shoulder_x': shoulder_center_x,
            'shoulder_y': shoulder_center_y
        }
        self.movement_history.append(current_movement)
        
        # Detect repetitive movements (rocking, swaying)
        if len(self.movement_history) > 30:
            recent_movements = self.movement_history[-30:]
            shoulder_x_values = [m['shoulder_x'] for m in recent_movements]
            
            # Calculate frequency of movement
            if len(shoulder_x_values) > 1:
                movement_variance = np.var(shoulder_x_values)
                if movement_variance < 0.001 and movement_variance > 0:
                    # Too little movement or repetitive
                    self.asd_indicators['repetitive_movements'] += 0.3
        
        # Keep only last 300 movements
        if len(self.movement_history) > 300:
            self.movement_history = self.movement_history[-300:]
        
        return {
            'shoulder_center_x': shoulder_center_x,
            'shoulder_center_y': shoulder_center_y
        }
    
    def analyze_hand_gestures(self, hand_landmarks):
        """Analyze hand gestures for repetitive behaviors (hand flapping)"""
        if not hand_landmarks:
            return {}
        
        gestures = []
        for hand_idx, hand in enumerate(hand_landmarks):
            # Get finger positions
            fingers_up = []
            
            # Thumb
            if hand.landmark[4].x < hand.landmark[3].x:
                fingers_up.append(1)
            else:
                fingers_up.append(0)
            
            # Other fingers
            for finger_tip, finger_pip in [(8, 6), (12, 10), (16, 14), (20, 18)]:
                if hand.landmark[finger_tip].y < hand.landmark[finger_pip].y:
                    fingers_up.append(1)
                else:
                    fingers_up.append(0)
            
            total_fingers = sum(fingers_up)
            gestures.append(total_fingers)
            
            # Detect hand flapping (rapid up-down movement)
            # Simplified: track hand position changes
            if len(self.hand_gestures) > 10:
                recent_gestures = self.hand_gestures[-10:]
                if all(g == total_fingers for g in recent_gestures):
                    # Repetitive hand position
                    self.asd_indicators['hand_flapping'] += 0.5
        
        self.hand_gestures.append(sum(gestures) if gestures else 0)
        
        return {
            'total_fingers': sum(gestures) if gestures else 0,
            'hand_count': len(hand_landmarks)
        }
    
    def detect_emotion_from_face(self, face_img):
        """Enhanced emotion detection"""
        try:
            result = DeepFace.analyze(face_img, actions=['emotion'], enforce_detection=False)
            emotion = result[0]['dominant_emotion']
            
            # Track atypical emotional responses for ASD
            if emotion in ['angry', 'fear', 'sad'] and len(self.eye_aspect_ratio_history) > 0:
                # Atypical emotional expression might be an indicator
                self.asd_indicators['atypical_facial_expressions'] += 0.2
            
            return emotion
        except:
            return "neutral"
    
    def analyze_child_therapist_interaction(self, frame, persons):
        """Analyze interaction between child and therapist"""
        if len(persons) >= 2:
            # We have at least two persons (child + therapist)
            person_positions = []
            for person in persons[:2]:  # First two persons
                x1, y1, x2, y2 = person
                center_x = (x1 + x2) / 2
                center_y = (y1 + y2) / 2
                person_positions.append((center_x, center_y))
            
            # Calculate distance between persons
            if len(person_positions) == 2:
                distance = np.sqrt((person_positions[0][0] - person_positions[1][0])**2 +
                                  (person_positions[0][1] - person_positions[1][1])**2)
                
                # Check if child is maintaining appropriate distance
                if distance > 0.3:  # Too far
                    self.asd_indicators['limited_gaze_sharing'] += 0.3
                
                return {
                    'distance': distance,
                    'interaction_active': distance < 0.4,
                    'persons_detected': 2
                }
        
        return {'persons_detected': len(persons)}
    
    def calculate_asd_risk_score(self):
        """Calculate overall ASD risk score based on all indicators"""
        total_score = sum(self.asd_indicators.values())
        max_possible = 300  # Approximate maximum
        
        risk_percentage = min(100, (total_score / max_possible) * 100)
        
        # Determine risk level
        if risk_percentage < 30:
            risk_level = "Low"
            recommendation = "Continue monitoring"
        elif risk_percentage < 60:
            risk_level = "Moderate"
            recommendation = "Consult with specialist"
        else:
            risk_level = "High"
            recommendation = "Immediate professional consultation recommended"
        
        return {
            'risk_percentage': risk_percentage,
            'risk_level': risk_level,
            'recommendation': recommendation,
            'indicators': self.asd_indicators.copy()
        }
    
    def save_session_data(self):
        """Save current session data to CSV"""
        if not self.session_data:
            print("No data to save")
            return
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{self.session_folder}/session_{timestamp}.csv"
        
        df = pd.DataFrame(self.session_data)
        df.to_csv(filename, index=False)
        
        # Save risk assessment summary
        risk = self.calculate_asd_risk_score()
        summary_file = f"{self.session_folder}/summary_{timestamp}.json"
        with open(summary_file, 'w') as f:
            json.dump({
                'timestamp': timestamp,
                'duration_seconds': time.time() - self.session_start_time if self.session_start_time else 0,
                'risk_assessment': risk,
                'total_blinks': self.blink_count,
                'total_data_points': len(self.session_data)
            }, f, indent=2)
        
        print(f"✅ Session saved to {filename}")
        print(f"✅ Summary saved to {summary_file}")
        
        # Print risk assessment
        print("\n📊 ASD Risk Assessment:")
        print(f"Risk Level: {risk['risk_level']}")
        print(f"Risk Score: {risk['risk_percentage']:.1f}%")
        print(f"Recommendation: {risk['recommendation']}")
    
    def run(self):
        """Main detection loop"""
        frame_count = 0
        rgb_frame = None
        
        while True:
            ret, frame = self.cap.read()
            if not ret:
                continue
            
            # Resize for better performance
            frame = cv2.resize(frame, (1024, 768))
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
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
                            
                            # Draw bounding box
                            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 3)
                            
                            # Person label
                            person_label = self.person_name if len(persons) == 1 else f"{self.person_name}_{len(persons)}"
                            cv2.putText(frame, person_label, (x1, y1-35),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                            
                            # Emotion with emoji
                            emoji = {'happy':'😊', 'sad':'😢', 'angry':'😠', 
                                    'surprise':'😲', 'fear':'😨', 'neutral':'😐'}.get(self.emotion, '😐')
                            cv2.putText(frame, f"{self.emotion.upper()} {emoji}", (x1, y1-10),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # MediaPipe Face Mesh processing
            face_mesh_results = self.face_mesh.process(rgb_frame)
            gaze_data = {}
            landmarks_data = {}
            
            if face_mesh_results.multi_face_landmarks:
                for face_landmarks in face_mesh_results.multi_face_landmarks:
                    # Draw face mesh
                    self.mp_drawing.draw_landmarks(
                        image=frame,
                        landmark_list=face_landmarks,
                        connections=self.mp_face_mesh.FACEMESH_TESSELATION,
                        landmark_drawing_spec=None,
                        connection_drawing_spec=self.mp_drawing_styles
                        .get_default_face_mesh_tesselation_style())
                    
                    # Analyze gaze
                    gaze_data = self.analyze_gaze_pattern(face_landmarks.landmark, frame.shape)
                    
                    # Analyze facial landmarks
                    landmarks_data = self.analyze_facial_landmarks_distance(face_landmarks.landmark)
            
            # MediaPipe Pose processing
            pose_results = self.pose.process(rgb_frame)
            movement_data = {}
            if pose_results.pose_landmarks:
                self.mp_drawing.draw_landmarks(
                    image=frame,
                    landmark_list=pose_results.pose_landmarks,
                    connections=self.mp_pose.POSE_CONNECTIONS,
                    landmark_drawing_spec=self.mp_drawing_styles
                    .get_default_pose_landmarks_style())
                movement_data = self.analyze_body_movement(pose_results.pose_landmarks)
            
            # MediaPipe Hands processing
            hands_results = self.hands.process(rgb_frame)
            gesture_data = {}
            if hands_results.multi_hand_landmarks:
                for hand_landmarks in hands_results.multi_hand_landmarks:
                    self.mp_drawing.draw_landmarks(
                        image=frame,
                        landmark_list=hand_landmarks,
                        connections=self.mp_hands.HAND_CONNECTIONS,
                        landmark_drawing_spec=self.mp_drawing_styles
                        .get_default_hand_landmarks_style(),
                        connection_drawing_spec=self.mp_drawing_styles
                        .get_default_hand_connections_style())
                gesture_data = self.analyze_hand_gestures(hands_results.multi_hand_landmarks)
            
            # Analyze child-therapist interaction
            interaction_data = self.analyze_child_therapist_interaction(frame, persons)
            
            # Record session data if active
            if self.session_active:
                session_entry = {
                    'timestamp': time.time(),
                    'emotion': self.emotion,
                    'blink_count': self.blink_count,
                    'eye_aspect_ratio': gaze_data.get('ear', 0),
                    'looking_at_camera': gaze_data.get('looking_at_camera', False),
                    'persons_detected': len(persons),
                    'interaction_distance': interaction_data.get('distance', 0),
                    'hand_gesture': gesture_data.get('total_fingers', 0),
                    'asd_indicators': self.asd_indicators.copy()
                }
                self.session_data.append(session_entry)
            
            # Calculate ASD risk score
            risk = self.calculate_asd_risk_score()
            
            # Draw information panel
            panel_y = 30
            cv2.rectangle(frame, (10, 10), (400, 200), (0, 0, 0), -1)
            cv2.putText(frame, f"Emotion: {self.emotion.upper()}", (20, panel_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            panel_y += 25
            cv2.putText(frame, f"Blinks: {self.blink_count}", (20, panel_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            panel_y += 25
            cv2.putText(frame, f"Looking at Camera: {gaze_data.get('looking_at_camera', False)}", (20, panel_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            panel_y += 25
            cv2.putText(frame, f"Persons: {len(persons)}", (20, panel_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            panel_y += 25
            cv2.putText(frame, f"ASD Risk: {risk['risk_percentage']:.0f}% ({risk['risk_level']})", (20, panel_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255) if risk['risk_level'] == 'High' else (0, 255, 0), 2)
            
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
        
        # Save data before exit if session was active
        if self.session_active and self.session_data:
            self.save_session_data()
        
        self.cap.release()
        cv2.destroyAllWindows()
        print("✅ System closed")
        
        # Print final risk assessment
        final_risk = self.calculate_asd_risk_score()
        print("\n" + "="*50)
        print("FINAL ASD RISK ASSESSMENT")
        print("="*50)
        print(f"Risk Level: {final_risk['risk_level']}")
        print(f"Risk Score: {final_risk['risk_percentage']:.1f}%")
        print(f"Recommendation: {final_risk['recommendation']}")
        print("\nIndicator Details:")
        for indicator, value in final_risk['indicators'].items():
            print(f"  - {indicator}: {value:.1f}")

if __name__ == "__main__":
    system = AutismDetectionSystem()
