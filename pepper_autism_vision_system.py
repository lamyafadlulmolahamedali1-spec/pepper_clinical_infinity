#!/usr/bin/env python3
"""
PEPPER AUTISM VISION SYSTEM
يجمع كل مشاريع Computer Vision للتوحد:
- Behavioural Video Recognition
- Facial Emotion Classification
- SPARK (Early detection)
- HAAR Cascade (Face detection)
- Therapy aid tool
- MirrorMe (Emotion mirror)
- MediaPipe Autism detection
- Attention monitoring
"""

import time
import threading
import cv2
import numpy as np
from ultralytics import YOLO
from deepface import DeepFace
import mediapipe as mp
from qibullet import SimulationManager
import pybullet as p
import pybullet_data
import pyttsx3
from collections import deque
import math

# ========== إعداد الصوت ==========
engine = pyttsx3.init()
engine.setProperty('rate', 150)
engine.setProperty('volume', 1.0)

def speak(text):
    print(f"🔊 Pepper: {text}")
    engine.say(text)
    engine.runAndWait()

# ========== 1. Behavioural Video Recognition (كشف السلوك) ==========
class BehaviorRecognizer:
    def __init__(self):
        self.behaviors = {
            "hand_flapping": {"detected": False, "count": 0},
            "rocking": {"detected": False, "count": 0},
            "eye_contact_avoidance": {"detected": False, "count": 0},
            "repetitive_movements": {"detected": False, "count": 0}
        }
        self.optical_flow = None
        self.prev_frame = None
    
    def detect_hand_flapping(self, frame):
        """كشف حركة اليدين المتكررة"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if self.prev_frame is not None:
            flow = cv2.calcOpticalFlowFarneback(self.prev_frame, gray, None, 0.5, 3, 15, 3, 5, 1.2, 0)
            magnitude, angle = cv2.cartToPolar(flow[..., 0], flow[..., 1])
            rapid_motion = np.sum(magnitude > 2) / magnitude.size
            if rapid_motion > 0.3:
                self.behaviors["hand_flapping"]["detected"] = True
                self.behaviors["hand_flapping"]["count"] += 1
            else:
                self.behaviors["hand_flapping"]["detected"] = False
        self.prev_frame = gray
        return self.behaviors["hand_flapping"]["detected"]
    
    def get_report(self):
        report = []
        for behavior, data in self.behaviors.items():
            if data["count"] > 0:
                report.append(f"{behavior.replace('_', ' ')}: {data['count']} times")
        return report if report else ["No unusual behaviors detected"]

# ========== 2. Facial Emotion Classification (من Autism-Facial-Emotion-Classification) ==========
class EmotionClassifier:
    def __init__(self):
        self.emotion_history = deque(maxlen=30)
        self.emotions = ["happy", "sad", "angry", "surprise", "fear", "disgust", "neutral"]
    
    def classify_emotion(self, face_img):
        """تصنيف المشاعر باستخدام DeepFace"""
        try:
            result = DeepFace.analyze(face_img, actions=['emotion'], enforce_detection=False)
            emotion = result[0]['dominant_emotion']
            self.emotion_history.append(emotion)
            return emotion
        except:
            return "neutral"
    
    def get_emotion_stats(self):
        if not self.emotion_history:
            return {}
        stats = {}
        for e in self.emotions:
            stats[e] = self.emotion_history.count(e)
        return stats

# ========== 3. SPARK - Early Detection (من SPARK) ==========
class SPARKDetector:
    def __init__(self):
        self.risk_score = 0
        self.indicators = {
            "eye_contact": 0,
            "social_smile": 0,
            "response_to_name": 0,
            "pointing": 0
        }
    
    def check_eye_contact(self, face_landmarks):
        """تحقق من التواصل البصري"""
        if face_landmarks:
            # تحليل اتجاه العينين
            left_eye = face_landmarks.landmark[159]
            right_eye = face_landmarks.landmark[386]
            # حساب درجة التواصل البصري
            gaze = abs(left_eye.x - right_eye.x)
            if gaze < 0.05:
                self.indicators["eye_contact"] += 1
                return True
        return False
    
    def get_risk_assessment(self):
        total = sum(self.indicators.values())
        if total >= 3:
            return "⚠️ High risk indicators. Consider professional screening."
        elif total >= 2:
            return "📋 Moderate risk. Monitor development closely."
        else:
            return "✅ Low risk. Continue normal development tracking."

# ========== 4. HAAR Cascade (Face Detection) - من Autism-Detection-HAAR-Cascade ==========
class HAARFaceDetector:
    def __init__(self):
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
        self.smile_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_smile.xml')
    
    def detect_faces(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 5)
        results = []
        for (x, y, w, h) in faces:
            face_roi = gray[y:y+h, x:x+w]
            eyes = self.eye_cascade.detectMultiScale(face_roi)
            smiles = self.smile_cascade.detectMultiScale(face_roi)
            results.append({
                "box": (x, y, w, h),
                "eyes_count": len(eyes),
                "smile_detected": len(smiles) > 0
            })
        return results

# ========== 5. Therapy Aid Tool (مراقبة التقدم) ==========
class TherapyAid:
    def __init__(self):
        self.session_data = []
        self.attention_scores = []
        self.emotion_timeline = []
    
    def record_session(self, attention, emotion):
        self.attention_scores.append(attention)
        self.emotion_timeline.append(emotion)
        if len(self.attention_scores) > 100:
            self.attention_scores = self.attention_scores[-100:]
            self.emotion_timeline = self.emotion_timeline[-100:]
    
    def get_progress_report(self):
        if not self.attention_scores:
            return "No session data yet"
        avg_attention = sum(self.attention_scores) / len(self.attention_scores)
        return f"Average attention: {avg_attention:.1f}% over {len(self.attention_scores)} frames"

# ========== 6. MirrorMe (تعليم المشاعر) ==========
class MirrorMe:
    def __init__(self, pepper):
        self.pepper = pepper
        self.current_emotion = "neutral"
        self.emotion_gestures = {
            "happy": self._happy_gesture,
            "sad": self._sad_gesture,
            "surprise": self._surprise_gesture,
            "angry": self._angry_gesture
        }
    
    def _happy_gesture(self):
        for _ in range(2):
            self.pepper.setAngles("LShoulderPitch", 1.0, 0.1)
            self.pepper.setAngles("RShoulderPitch", 1.0, 0.1)
            time.sleep(0.15)
            self.pepper.setAngles("LShoulderPitch", 0, 0.1)
            self.pepper.setAngles("RShoulderPitch", 0, 0.1)
            time.sleep(0.15)
    
    def _sad_gesture(self):
        self.pepper.setAngles("HeadPitch", 0.2, 0.1)
        time.sleep(0.5)
        self.pepper.setAngles("HeadPitch", 0, 0.1)
    
    def _surprise_gesture(self):
        self.pepper.setAngles("HeadYaw", 0.5, 0.1)
        time.sleep(0.3)
        self.pepper.setAngles("HeadYaw", 0, 0.1)
    
    def _angry_gesture(self):
        for _ in range(2):
            self.pepper.setAngles("LShoulderPitch", 0.8, 0.1)
            time.sleep(0.15)
            self.pepper.setAngles("LShoulderPitch", 0, 0.1)
            time.sleep(0.15)
    
    def mirror_emotion(self, emotion):
        if emotion in self.emotion_gestures:
            self.emotion_gestures[emotion]()
            return f"Mirroring {emotion} emotion!"
        return None

# ========== 7. MediaPipe Autism Detection ==========
class MediaPipeDetector:
    def __init__(self):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(static_image_mode=False, max_num_faces=1, refine_landmarks=True)
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose()
    
    def detect_face_landmarks(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb)
        if results.multi_face_landmarks:
            return results.multi_face_landmarks[0]
        return None
    
    def detect_pose(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(rgb)
        return results.pose_landmarks

# ========== 8. Attention Monitoring (مراقبة الانتباه) ==========
class AttentionMonitor:
    def __init__(self):
        self.attention_history = deque(maxlen=100)
        self.gaze_direction = "center"
    
    def calculate_attention(self, face_landmarks):
        """حساب درجة الانتباه من حركة العينين"""
        if face_landmarks:
            # استخدام نقاط العينين
            left_eye = face_landmarks.landmark[159]
            right_eye = face_landmarks.landmark[386]
            gaze_x = (left_eye.x + right_eye.x) / 2
            if gaze_x < 0.4:
                self.gaze_direction = "left"
                attention = 40
            elif gaze_x > 0.6:
                self.gaze_direction = "right"
                attention = 40
            else:
                self.gaze_direction = "center"
                attention = 80
            self.attention_history.append(attention)
            return attention
        return 0
    
    def get_avg_attention(self):
        if self.attention_history:
            return sum(self.attention_history) / len(self.attention_history)
        return 0

# ========== 9. نظام الرؤية المتكامل ==========
class AutismVisionSystem:
    def __init__(self, pepper):
        self.pepper = pepper
        self.behavior = BehaviorRecognizer()
        self.emotion = EmotionClassifier()
        self.spark = SPARKDetector()
        self.haar = HAARFaceDetector()
        self.therapy = TherapyAid()
        self.mirror = MirrorMe(pepper)
        self.mediapipe = MediaPipeDetector()
        self.attention = AttentionMonitor()
        
        # كاميرا
        self.cap = cv2.VideoCapture(1)
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(0)
        
        self.running = True
        self.current_emotion = "neutral"
        
        # شاشة عرض
        cv2.namedWindow("Autism Vision System", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Autism Vision System", 800, 600)
        
        threading.Thread(target=self._run, daemon=True).start()
    
    def _run(self):
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                continue
            
            frame = cv2.resize(frame, (800, 600))
            
            # 1. HAAR Face Detection
            faces = self.haar.detect_faces(frame)
            
            # 2. MediaPipe landmarks
            face_landmarks = self.mediapipe.detect_face_landmarks(frame)
            
            # 3. Attention monitoring
            attention = self.attention.calculate_attention(face_landmarks)
            self.therapy.record_session(attention, self.current_emotion)
            
            # 4. Emotion classification
            if faces:
                x, y, w, h = faces[0]["box"]
                face_roi = frame[y:y+h, x:x+w]
                if face_roi.size > 0:
                    self.current_emotion = self.emotion.classify_emotion(face_roi)
                    self.spark.check_eye_contact(face_landmarks)
            
            # 5. Behavior detection
            self.behavior.detect_hand_flapping(frame)
            
            # رسم المعلومات على الشاشة
            for face in faces:
                x, y, w, h = face["box"]
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 3)
                cv2.putText(frame, f"Emotion: {self.current_emotion}", (x, y-30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(frame, f"Eyes: {face['eyes_count']}", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                if face["smile_detected"]:
                    cv2.putText(frame, "Smile!", (x, y+h+25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            # معلومات إضافية
            cv2.putText(frame, f"Attention: {attention:.0f}%", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, f"Gaze: {self.attention.gaze_direction}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            behaviors = self.behavior.get_report()
            if behaviors and behaviors[0] != "No unusual behaviors detected":
                cv2.putText(frame, f"Behavior: {behaviors[0][:30]}", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            
            cv2.imshow("Autism Vision System", frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        self.cap.release()
        cv2.destroyAllWindows()
    
    def get_status(self):
        return {
            "emotion": self.current_emotion,
            "attention": self.attention.get_avg_attention(),
            "risk": self.spark.get_risk_assessment(),
            "progress": self.therapy.get_progress_report()
        }
    
    def stop(self):
        self.running = False

# ========== بدء qiBullet ==========
print("🤖 Starting Pepper Autism Vision System...")

sim_manager = SimulationManager()
client_id = sim_manager.launchSimulation(gui=True)

pepper = sim_manager.spawnPepper(client_id, translation=[0, 0, 0], quaternion=[0, 0, 0, 1])

p.setAdditionalSearchPath(pybullet_data.getDataPath())
p.loadURDF("plane.urdf")
p.setGravity(0, 0, -9.81)

print("✅ Pepper loaded!")

# ========== بالونات ==========
colors = [[1,0,0,1], [0,1,0,1], [0,0,1,1], [1,1,0,1], [1,0.5,0,1]]
balloons = []
for i in range(10):
    x = random.uniform(-3, 3)
    y = random.uniform(-2.5, 2.5)
    vis = p.createVisualShape(p.GEOM_SPHERE, radius=0.12, rgbaColor=colors[i%5])
    ball = p.createMultiBody(baseMass=0, baseVisualShapeIndex=vis, basePosition=[x, y, random.uniform(0.5,1.5)])
    balloons.append(ball)

p.resetDebugVisualizerCamera(cameraDistance=6, cameraYaw=45, cameraPitch=-30, cameraTargetPosition=[0,0,0.8])

# ========== تشغيل الرؤية ==========
vision = AutismVisionSystem(pepper)

# حركة مشي
t = 0
def walk():
    global t
    while True:
        t += 0.035
        x = 2.8 * math.cos(t * 0.45)
        y = 2.5 * math.sin(t * 0.6)
        try:
            pepper.setTranslation([x, y, 0.8])
        except:
            pass
        time.sleep(0.04)
threading.Thread(target=walk, daemon=True).start()

# تحديث البالونات
def update_balloons():
    while True:
        for b in balloons:
            pos, _ = p.getBasePositionAndOrientation(b)
            new_z = pos[2] + 0.008
            if new_z > 1.6:
                new_z = 0.3
            p.resetBasePositionAndOrientation(b, [pos[0], pos[1], new_z], [0,0,0,1])
        p.stepSimulation()
        time.sleep(1/60.)
threading.Thread(target=update_balloons, daemon=True).start()

print("\n" + "="*60)
print("🤖 PEPPER AUTISM VISION SYSTEM")
print("="*60)
print("✅ Behavioural Video Recognition")
print("✅ Facial Emotion Classification")
print("✅ SPARK Early Detection")
print("✅ HAAR Cascade (Face + Eyes + Smile)")
print("✅ Therapy Aid Tool")
print("✅ MirrorMe (Emotion Mirroring)")
print("✅ MediaPipe Detection")
print("✅ Attention Monitoring")
print("="*60)
print("\n📝 COMMANDS:")
print("   status - Show vision status")
print("   mirror - Mirror current emotion")
print("   report - Show progress report")
print("   risk - Show risk assessment")
print("   exit - Quit")
print("="*60 + "\n")

speak("Autism vision system activated! I can detect emotions, behaviors, and attention!")

# ========== محادثة ==========
while True:
    try:
        user_input = input("\n👶 You: ").strip().lower()
        
        if user_input == 'exit':
            speak("Goodbye!")
            break
        
        elif user_input == 'status':
            status = vision.get_status()
            speak(f"Emotion: {status['emotion']}, Attention: {status['attention']:.0f} percent")
        
        elif user_input == 'mirror':
            result = vision.mirror.mirror_emotion(vision.current_emotion)
            if result:
                speak(result)
            else:
                speak("No emotion to mirror")
        
        elif user_input == 'report':
            report = vision.therapy.get_progress_report()
            speak(report)
        
        elif user_input == 'risk':
            risk = vision.spark.get_risk_assessment()
            speak(risk)
        
        else:
            speak(f"Vision status: {vision.current_emotion} emotion detected")
        
    except KeyboardInterrupt:
        print("\n")
        speak("Goodbye!")
        break

vision.stop()
print("\n✅ Done")
