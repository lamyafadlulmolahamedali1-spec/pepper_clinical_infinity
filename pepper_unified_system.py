#!/usr/bin/env python3
"""
PEPPER UNIFIED SYSTEM - يجمع كل مشاريعك في qiBullet
- حركة يدين سلسة مع الكلام
- AI Chat متطور
- كاميرا (YOLO + Emotion)
- بيبر يتحرك في الغرفة
"""

import time
import random
import math
import threading
import pyttsx3
import cv2
from ultralytics import YOLO
from deepface import DeepFace
from qibullet import SimulationManager
import pybullet as p
import pybullet_data
import requests

# ========== 1. إعداد الصوت ==========
engine = pyttsx3.init()
engine.setProperty('rate', 150)
engine.setProperty('volume', 1.0)

def speak(text):
    print(f"🔊 Pepper: {text}")
    engine.say(text)
    engine.runAndWait()

# ========== 2. AI Chat متطور ==========
CHAT_API = "https://text.pollinations.ai/v1/chat/completions"

def get_ai_response(message):
    try:
        data = {
            "model": "openai",
            "messages": [
                {"role": "system", "content": "You are Pepper, a friendly robot for a child with autism. Respond in short, simple English sentences. Be patient, kind, and encouraging. Use ABA principles (positive reinforcement). Keep responses to 1-2 sentences."},
                {"role": "user", "content": message}
            ]
        }
        response = requests.post(CHAT_API, json=data, timeout=10)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
    except:
        pass
    return "That's interesting! Tell me more! 😊"

# ========== 3. كاميرا (YOLO + Emotion) ==========
class CameraDetection:
    def __init__(self):
        self.model = YOLO('yolov8n.pt')
        self.cap = cv2.VideoCapture(1)
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(0)
        self.current_emotion = "neutral"
        self.current_object = "nothing"
        self.running = True
        threading.Thread(target=self._run, daemon=True).start()
    
    def _run(self):
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                continue
            frame = cv2.resize(frame, (640, 480))
            results = self.model(frame, verbose=False)
            for r in results:
                if r.boxes:
                    for box in r.boxes:
                        cls = int(box.cls[0])
                        name = self.model.names[cls]
                        if name == 'person':
                            x1, y1, x2, y2 = map(int, box.xyxy[0])
                            face = frame[y1:y2, x1:x2]
                            if face.size > 0:
                                try:
                                    result = DeepFace.analyze(face, actions=['emotion'], enforce_detection=False)
                                    self.current_emotion = result[0]['dominant_emotion']
                                except:
                                    pass
                            self.current_object = f"person ({self.current_emotion})"
                        else:
                            self.current_object = name
            cv2.imshow("Pepper Vision", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        self.cap.release()
        cv2.destroyAllWindows()
    
    def get_vision(self):
        return f"I see {self.current_object}"
    
    def get_emotion(self):
        return self.current_emotion
    
    def stop(self):
        self.running = False

# ========== 4. حركة يدين سلسة مع الكلام ==========
class SmoothGestures:
    def __init__(self, pepper):
        self.pepper = pepper
        self.target_arm_angle = 0
        self.current_arm_angle = 0
        self.is_moving = False
    
    def wave(self):
        self.is_moving = True
        for angle in [0.5, 1.0, 1.2, 1.0, 0.5, 0]:
            self._move_arms_smooth(angle, 0.1)
            time.sleep(0.1)
        self.is_moving = False
    
    def raise_arms(self):
        self.is_moving = True
        self._move_arms_smooth(1.2, 0.2)
        time.sleep(0.5)
        self._move_arms_smooth(0, 0.2)
        self.is_moving = False
    
    def _move_arms_smooth(self, target, duration):
        steps = 20
        step_time = duration / steps
        start = self.current_arm_angle
        for i in range(steps):
            self.current_arm_angle = start + (target - start) * (i / steps)
            try:
                self.pepper.setAngles("LShoulderPitch", self.current_arm_angle, 0.05)
                self.pepper.setAngles("RShoulderPitch", self.current_arm_angle, 0.05)
            except:
                pass
            time.sleep(step_time)
    
    def natural_movement(self):
        if not self.is_moving:
            # حركة طبيعية مستمرة
            self.current_arm_angle = 0.2 + math.sin(time.time() * 1.5) * 0.1
            try:
                self.pepper.setAngles("LShoulderPitch", self.current_arm_angle, 0.05)
                self.pepper.setAngles("RShoulderPitch", self.current_arm_angle, 0.05)
            except:
                pass

# ========== 5. بدء qiBullet ==========
print("🤖 Starting Pepper in qiBullet...")

sim_manager = SimulationManager()
client_id = sim_manager.launchSimulation(gui=True)

pepper = sim_manager.spawnPepper(client_id, translation=[0, 0, 0], quaternion=[0, 0, 0, 1])

p.setAdditionalSearchPath(pybullet_data.getDataPath())
p.loadURDF("plane.urdf")
p.setGravity(0, 0, -9.81)

print("✅ Pepper loaded!")

# ========== 6. بالونات ==========
colors = [[1,0,0,1], [0,1,0,1], [0,0,1,1], [1,1,0,1], [1,0.5,0,1]]
balloons = []
for i in range(10):
    x = random.uniform(-3, 3)
    y = random.uniform(-2.5, 2.5)
    vis = p.createVisualShape(p.GEOM_SPHERE, radius=0.12, rgbaColor=colors[i%5])
    ball = p.createMultiBody(baseMass=0, baseVisualShapeIndex=vis, basePosition=[x, y, random.uniform(0.5,1.5)])
    balloons.append(ball)

p.resetDebugVisualizerCamera(cameraDistance=6, cameraYaw=45, cameraPitch=-30, cameraTargetPosition=[0,0,0.8])

# ========== 7. تشغيل الكاميرا والحركات ==========
camera = CameraDetection()
gestures = SmoothGestures(pepper)

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

# حركة يدين طبيعية
def natural_arms():
    while True:
        gestures.natural_movement()
        time.sleep(0.05)

threading.Thread(target=natural_arms, daemon=True).start()

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
print("🤖 PEPPER UNIFIED SYSTEM")
print("="*60)
print("✅ Camera (YOLO + Emotion) - عيون بيبر")
print("✅ AI Chat - عقل بيبر")
print("✅ Smooth gestures - حركة يدين سلسة")
print("✅ Continuous walking - مشي مستمر")
print("="*60 + "\n")

speak("Hello! I am Pepper! I can see you, hear you, and talk to you!")

# ========== 8. المحادثة ==========
while True:
    try:
        user_input = input("\n👶 You: ").strip()
        
        if user_input.lower() == 'exit':
            speak("Goodbye! See you later!")
            break
        
        if not user_input:
            continue
        
        # إضافة معلومات من الكاميرا للسياق
        vision_info = camera.get_vision()
        print(f"📷 Pepper sees: {vision_info}")
        
        # حركة يدين حسب الكلام
        if any(word in user_input.lower() for word in ["hello", "hi"]):
            gestures.wave()
        elif any(word in user_input.lower() for word in ["good", "great", "awesome"]):
            gestures.raise_arms()
        
        # الحصول على رد من AI
        response = get_ai_response(user_input)
        speak(response)
        
    except KeyboardInterrupt:
        print("\n")
        speak("Goodbye!")
        break

camera.stop()
print("\n✅ Done")
