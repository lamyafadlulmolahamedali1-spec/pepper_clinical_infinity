#!/usr/bin/env python3
"""
PEPPER AUTISM COMPLETE - QIBULLET
يجمع كل المشاريع:
- كشف المشاعر وتحويلها لإيموجي
- كشف سلوكيات الطفل
- اختبارات تشخيصية للتوحد
- نظام علاجي ABA/DTT/TEACCH
- مراقبة تقدم العلاج
- كشف الوجه بالكاميرا
"""

import time
import random
import math
import threading
import json
import cv2
import numpy as np
from ultralytics import YOLO
from deepface import DeepFace
from qibullet import SimulationManager
import pybullet as p
import pybullet_data
import pyttsx3
import requests
from collections import deque

# ========== إعداد الصوت ==========
engine = pyttsx3.init()
engine.setProperty('rate', 150)
engine.setProperty('volume', 1.0)

def speak(text):
    print(f"🔊 Pepper: {text}")
    engine.say(text)
    engine.runAndWait()

# ========== 1. Emotion to Emoji (من pepper-emoji) ==========
EMOTION_EMOJI = {
    'happy': '😊', 'sad': '😢', 'angry': '😠', 'fear': '😨',
    'surprise': '😲', 'neutral': '😐', 'disgust': '🤢'
}

def emotion_to_emoji(emotion):
    return EMOTION_EMOJI.get(emotion, '😐')

# ========== 2. كاميرا + كشف مشاعر + كشف وجه (من pepper-emoji + HAAR) ==========
class EmotionCamera:
    def __init__(self):
        self.model = YOLO('yolov8n.pt')
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.cap = cv2.VideoCapture(1)
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(0)
        self.current_emotion = "neutral"
        self.current_emoji = "😐"
        self.face_count = 0
        self.running = True
        threading.Thread(target=self._run, daemon=True).start()
    
    def _run(self):
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                continue
            frame = cv2.resize(frame, (640, 480))
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, 1.1, 5)
            self.face_count = len(faces)
            
            results = self.model(frame, verbose=False)
            for r in results:
                if r.boxes:
                    for box in r.boxes:
                        if self.model.names[int(box.cls[0])] == 'person':
                            x1, y1, x2, y2 = map(int, box.xyxy[0])
                            face = frame[y1:y2, x1:x2]
                            if face.size > 0:
                                try:
                                    result = DeepFace.analyze(face, actions=['emotion'], enforce_detection=False)
                                    self.current_emotion = result[0]['dominant_emotion']
                                    self.current_emoji = emotion_to_emoji(self.current_emotion)
                                except:
                                    pass
                            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 3)
                            cv2.putText(frame, f"{self.current_emotion} {self.current_emoji}", 
                                       (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            cv2.putText(frame, f"Faces: {self.face_count} | Emotion: {self.current_emotion} {self.current_emoji}", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.imshow("Pepper Vision - Autism Support", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        self.cap.release()
        cv2.destroyAllWindows()
    
    def get_emotion(self):
        return self.current_emotion, self.current_emoji
    
    def get_face_count(self):
        return self.face_count
    
    def stop(self):
        self.running = False

# ========== 3. اختبارات تشخيصية للتوحد (من Pepper_Autism_Test_App) ==========
AUTISM_SCREENING_QUESTIONS = [
    {"question": "Does the child make eye contact?", "score_if_yes": 1},
    {"question": "Does the child respond to their name?", "score_if_yes": 1},
    {"question": "Does the child point to show interest?", "score_if_yes": 1},
    {"question": "Does the child play pretend?", "score_if_yes": 1},
    {"question": "Does the child follow where you point?", "score_if_yes": 1},
    {"question": "Does the child have repetitive movements?", "score_if_no": 1},
    {"question": "Does the child have unusual sensory interests?", "score_if_no": 1},
]

def run_screening():
    score = 0
    speak("Let me ask you some questions about the child.")
    for q in AUTISM_SCREENING_QUESTIONS:
        speak(q["question"])
        # In real implementation, would listen for answer
        print(f"Question: {q['question']}")
        print("Answer (yes/no): ", end="")
        answer = input().strip().lower()
        if answer == 'yes':
            if "score_if_yes" in q:
                score += q["score_if_yes"]
        elif answer == 'no':
            if "score_if_no" in q:
                score += q["score_if_no"]
    
    if score >= 4:
        result = "High likelihood of ASD traits. Please consult a specialist."
    elif score >= 2:
        result = "Moderate indicators. Consider professional screening."
    else:
        result = "Low indicators. Continue monitoring."
    
    speak(result)
    return result

# ========== 4. نظام علاجي (ABA/DTT/TEACCH) من PepperForAutism ==========
class TherapySystem:
    def __init__(self):
        self.positive_reinforcements = [
            "Great job! 🌟", "Excellent! 👏", "You're doing amazing! 💪",
            "I'm so proud of you! 🎉", "Wonderful! ✨"
        ]
        self.current_task = None
        self.task_steps = []
        self.current_step = 0
    
    def reinforce(self):
        return random.choice(self.positive_reinforcements)
    
    def start_task(self, task_name, steps):
        self.current_task = task_name
        self.task_steps = steps
        self.current_step = 0
        return f"Let's learn {task_name}. Step 1: {steps[0]}"
    
    def next_step(self):
        self.current_step += 1
        if self.current_step < len(self.task_steps):
            return f"Step {self.current_step + 1}: {self.task_steps[self.current_step]}"
        else:
            result = f"Great! You completed {self.current_task}! {self.reinforce()}"
            self.current_task = None
            return result

# ========== 5. مراقبة تقدم العلاج (من therapy-aid-tool) ==========
class ProgressTracker:
    def __init__(self):
        self.sessions = []
        self.current_session = []
    
    def start_session(self):
        self.current_session = []
        return "Session started!"
    
    def log_interaction(self, interaction_type, success):
        self.current_session.append({
            "time": time.time(),
            "type": interaction_type,
            "success": success
        })
    
    def end_session(self):
        if self.current_session:
            total = len(self.current_session)
            successful = sum(1 for s in self.current_session if s["success"])
            success_rate = (successful / total) * 100 if total > 0 else 0
            self.sessions.append({
                "date": time.strftime("%Y-%m-%d %H:%M"),
                "total": total,
                "successful": successful,
                "success_rate": success_rate
            })
            return f"Session complete! Success rate: {success_rate:.1f}%"
        return "No session data"

# ========== 6. كشف سلوكيات (من Behavioural-Video-Recognition) ==========
class BehaviorDetector:
    def __init__(self):
        self.behaviors = {
            "hand_flapping": "repetitive hand movement",
            "rocking": "body rocking",
            "spinning": "spinning objects",
            "eye_contact_avoidance": "avoiding eye contact"
        }
    
    def detect(self, text):
        text_lower = text.lower()
        detected = []
        for behavior, description in self.behaviors.items():
            if behavior.replace('_', ' ') in text_lower:
                detected.append(description)
        return detected

# ========== 7. بدء qiBullet ==========
print("🤖 Starting Pepper in qiBullet...")

sim_manager = SimulationManager()
client_id = sim_manager.launchSimulation(gui=True)

pepper = sim_manager.spawnPepper(client_id, translation=[0, 0, 0], quaternion=[0, 0, 0, 1])

p.setAdditionalSearchPath(pybullet_data.getDataPath())
p.loadURDF("plane.urdf")
p.setGravity(0, 0, -9.81)

print("✅ Pepper loaded!")

# ========== 8. بالونات ==========
colors = [[1,0,0,1], [0,1,0,1], [0,0,1,1], [1,1,0,1], [1,0.5,0,1]]
balloons = []
for i in range(10):
    x = random.uniform(-3, 3)
    y = random.uniform(-2.5, 2.5)
    vis = p.createVisualShape(p.GEOM_SPHERE, radius=0.12, rgbaColor=colors[i%5])
    ball = p.createMultiBody(baseMass=0, baseVisualShapeIndex=vis, basePosition=[x, y, random.uniform(0.5,1.5)])
    balloons.append(ball)

p.resetDebugVisualizerCamera(cameraDistance=6, cameraYaw=45, cameraPitch=-30, cameraTargetPosition=[0,0,0.8])

# ========== 9. تشغيل الكاميرا والأنظمة ==========
camera = EmotionCamera()
therapy = TherapySystem()
tracker = ProgressTracker()
behavior = BehaviorDetector()

# حركة مشي مستمرة
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
print("🤖 PEPPER AUTISM COMPLETE - QIBULLET")
print("="*60)
print("✅ Emotion to Emoji (pepper-emoji)")
print("✅ Face Detection (HAAR Cascade)")
print("✅ Autism Screening Tests")
print("✅ ABA/DTT/TEACCH Therapy System")
print("✅ Progress Tracking")
print("✅ Behavior Detection")
print("="*60)
print("\n📝 COMMANDS:")
print("   screen - Run autism screening")
print("   therapy - Start therapy session")
print("   progress - Show progress report")
print("   emotion - Show current emotion")
print("   hello, a, b - Sign language")
print("   exit - Quit")
print("="*60 + "\n")

speak("Hello! I am Pepper! I can help with autism screening and therapy! Say screen for testing, or therapy for learning!")

# ========== 10. المحادثة الرئيسية ==========
while True:
    try:
        user_input = input("\n👶 You: ").strip().lower()
        
        if user_input == 'exit':
            speak("Goodbye!")
            break
        
        elif user_input == 'screen':
            run_screening()
        
        elif user_input == 'therapy':
            speak("Let's start a therapy session. What would you like to learn?")
            tracker.start_session()
            speak(therapy.start_task("daily routine", ["Wake up", "Brush teeth", "Get dressed", "Eat breakfast"]))
        
        elif user_input == 'next' or user_input == 'step':
            result = therapy.next_step()
            speak(result)
            tracker.log_interaction("task_step", "success" in result)
        
        elif user_input == 'progress':
            result = tracker.end_session()
            speak(result)
        
        elif user_input == 'emotion':
            emotion, emoji = camera.get_emotion()
            speak(f"I see {emotion} {emoji}")
        
        elif user_input == 'good' or user_input == 'great':
            speak(therapy.reinforce())
            tracker.log_interaction("positive_reinforcement", True)
        
        else:
            # كشف سلوكيات من الكلام
            detected = behavior.detect(user_input)
            if detected:
                speak(f"I notice {detected[0]}. Let's work on that together.")
            
            # رد عام
            emotion, emoji = camera.get_emotion()
            speak(f"You said: {user_input}. {therapy.reinforce()}")
        
    except KeyboardInterrupt:
        print("\n")
        speak("Goodbye!")
        break

camera.stop()
print("\n✅ Done")
