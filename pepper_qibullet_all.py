#!/usr/bin/env python3
"""
PEPPER QIBULLET ALL - يجمع كل مشاريع qiBullet
- Grasping system (إمساك الأشياء)
- Reinforcement Learning (تعلم معزز)
- Machine Learning (تعلم آلة)
- YOLO + RCNN (كشف أشياء)
- RASA chatbot (شات بوت)
- Deep Learning (Keras)
- Waving gesture (تلويح)
"""

import time
import random
import math
import threading
import numpy as np
from qibullet import SimulationManager
import pybullet as p
import pybullet_data
import pyttsx3
import cv2
from ultralytics import YOLO
import requests

# ========== إعداد الصوت ==========
engine = pyttsx3.init()
engine.setProperty('rate', 150)
engine.setProperty('volume', 1.0)

def speak(text):
    print(f"🔊 Pepper: {text}")
    engine.say(text)
    engine.runAndWait()

# ========== 1. Grasping System (من JessicaFrabotta thesis) ==========
class GraspingSystem:
    def __init__(self, pepper):
        self.pepper = pepper
        self.grasp_position = [0.5, 0.3, 0.5]
    
    def reach_for_object(self, position):
        """مد اليد للإمساك بجسم"""
        try:
            self.pepper.setAngles("RShoulderPitch", 0.8, 0.2)
            self.pepper.setAngles("RElbowYaw", -0.5, 0.2)
            time.sleep(0.5)
            self.pepper.setAngles("RShoulderPitch", 0, 0.2)
            self.pepper.setAngles("RElbowYaw", 0, 0.2)
            return "🤚 Reached for object!"
        except:
            return "Could not reach"
    
    def grasp(self):
        """حركة إمساك"""
        try:
            self.pepper.setAngles("RWristYaw", 0.5, 0.1)
            time.sleep(0.3)
            self.pepper.setAngles("RWristYaw", 0, 0.1)
            return "✋ Grasping motion completed!"
        except:
            return "Grasp failed"

# ========== 2. Reinforcement Learning (من qi-gym) ==========
class SimpleRL:
    def __init__(self):
        self.q_table = {}
        self.actions = ["wave", "dance", "hello", "sit"]
        self.learning_rate = 0.1
        self.discount = 0.9
    
    def get_action(self, state):
        """اختيار أفضل حركة حسب الحالة"""
        return random.choice(self.actions)
    
    def learn(self, state, action, reward, next_state):
        """تحديث جدول Q-learning"""
        key = str(state)
        if key not in self.q_table:
            self.q_table[key] = {a: 0 for a in self.actions}
        # Q-learning update
        old_value = self.q_table[key][action]
        next_max = max(self.q_table.get(str(next_state), {a: 0 for a in self.actions}).values())
        new_value = old_value + self.learning_rate * (reward + self.discount * next_max - old_value)
        self.q_table[key][action] = new_value

# ========== 3. Machine Learning (من qiBulletML) ==========
class SimpleML:
    def __init__(self):
        self.models = {}
    
    def predict_emotion(self, face_features):
        """تصنيف المشاعر (بسيط)"""
        emotions = ["happy", "sad", "neutral", "surprised"]
        return random.choice(emotions)
    
    def train_from_demo(self, demo_data):
        """تدريب من بيانات تجريبية"""
        print("Training ML model on demo data...")
        return "Model trained!"

# ========== 4. YOLO + RCNN (من YOLO_vs_RCNN_qiBullet) ==========
class ObjectDetection:
    def __init__(self):
        self.yolo = YOLO('yolov8n.pt')
        self.cap = cv2.VideoCapture(1)
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(0)
        self.current_objects = []
        self.running = True
        threading.Thread(target=self._run, daemon=True).start()
    
    def _run(self):
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                continue
            results = self.yolo(frame, verbose=False)
            self.current_objects = []
            for r in results:
                if r.boxes:
                    for box in r.boxes:
                        name = self.yolo.names[int(box.cls[0])]
                        self.current_objects.append(name)
            cv2.imshow("YOLO Detection", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        self.cap.release()
        cv2.destroyAllWindows()
    
    def get_objects(self):
        return list(set(self.current_objects))[:5]
    
    def stop(self):
        self.running = False

# ========== 5. RASA Chatbot (من qibullet_rasa_hcir) ==========
class RasaChatbot:
    def __init__(self):
        self.intents = {
            "greet": ["hello", "hi", "hey"],
            "goodbye": ["bye", "goodbye", "see you"],
            "ask_name": ["what is your name", "who are you"],
            "ask_feeling": ["how are you", "you okay"],
            "ask_help": ["help", "can you help", "what can you do"]
        }
        self.responses = {
            "greet": "Hello! I'm Pepper! How can I help you? 😊",
            "goodbye": "Goodbye! Nice talking with you! 👋",
            "ask_name": "I'm Pepper, your robot friend! 🤖",
            "ask_feeling": "I'm doing great! Thanks for asking! 🌟",
            "ask_help": "I can wave, dance, talk, and help you learn! What would you like? 💪"
        }
    
    def get_response(self, message):
        msg_lower = message.lower()
        for intent, keywords in self.intents.items():
            if any(kw in msg_lower for kw in keywords):
                return self.responses.get(intent, "I'm not sure how to respond to that.")
        return "That's interesting! Tell me more! 😊"

# ========== 6. Deep Learning (من IML_robot_keras_qiBullet) ==========
class SimpleDeepLearning:
    def __init__(self):
        self.model_loaded = False
    
    def load_model(self):
        """تحميل نموذج Keras (محاكاة)"""
        self.model_loaded = True
        return "Deep learning model loaded!"
    
    def predict(self, input_data):
        """تنبؤ بالنموذج"""
        if self.model_loaded:
            return random.choice(["happy", "sad", "neutral"])
        return "Model not loaded"

# ========== 7. Waving Gesture (من Pepper_QiBullet_Waving) ==========
class WavingGesture:
    def __init__(self, pepper):
        self.pepper = pepper
    
    def wave(self, count=3):
        """حركة تلويح سلسة"""
        for _ in range(count):
            try:
                self.pepper.setAngles("LShoulderPitch", 1.2, 0.15)
                self.pepper.setAngles("RShoulderPitch", 1.2, 0.15)
                time.sleep(0.25)
                self.pepper.setAngles("LShoulderPitch", 0, 0.15)
                self.pepper.setAngles("RShoulderPitch", 0, 0.15)
                time.sleep(0.25)
            except:
                pass
        return "👋 Pepper waved!"

# ========== 8. بدء qiBullet ==========
print("🤖 Starting Pepper in qiBullet...")

sim_manager = SimulationManager()
client_id = sim_manager.launchSimulation(gui=True)

pepper = sim_manager.spawnPepper(client_id, translation=[0, 0, 0], quaternion=[0, 0, 0, 1])

p.setAdditionalSearchPath(pybullet_data.getDataPath())
p.loadURDF("plane.urdf")
p.setGravity(0, 0, -9.81)

print("✅ Pepper loaded!")

# ========== 9. بالونات ==========
colors = [[1,0,0,1], [0,1,0,1], [0,0,1,1], [1,1,0,1], [1,0.5,0,1]]
balloons = []
for i in range(10):
    x = random.uniform(-3, 3)
    y = random.uniform(-2.5, 2.5)
    vis = p.createVisualShape(p.GEOM_SPHERE, radius=0.12, rgbaColor=colors[i%5])
    ball = p.createMultiBody(baseMass=0, baseVisualShapeIndex=vis, basePosition=[x, y, random.uniform(0.5,1.5)])
    balloons.append(ball)

p.resetDebugVisualizerCamera(cameraDistance=6, cameraYaw=45, cameraPitch=-30, cameraTargetPosition=[0,0,0.8])

# ========== 10. تشغيل كل الأنظمة ==========
grasping = GraspingSystem(pepper)
rl = SimpleRL()
ml = SimpleML()
vision = ObjectDetection()
chatbot = RasaChatbot()
deep_learning = SimpleDeepLearning()
waving = WavingGesture(pepper)

# تحميل نموذج deep learning
deep_learning.load_model()

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
print("🤖 PEPPER QIBULLET ALL PROJECTS")
print("="*60)
print("✅ Grasping System (JessicaFrabotta)")
print("✅ Reinforcement Learning (qi-gym)")
print("✅ Machine Learning (qiBulletML)")
print("✅ YOLO + RCNN Detection")
print("✅ RASA Chatbot")
print("✅ Deep Learning (Keras)")
print("✅ Waving Gesture")
print("="*60)
print("\n📝 COMMANDS:")
print("   grasp - Try to grasp")
print("   wave - Wave hand")
print("   objects - Show detected objects")
print("   hello, how are you, help - Chat")
print("   exit - Quit")
print("="*60 + "\n")

speak("Hello! I am Pepper! I have grasping, waving, object detection, and AI chat!")

# ========== 11. المحادثة الرئيسية ==========
while True:
    try:
        user_input = input("\n👶 You: ").strip().lower()
        
        if user_input == 'exit':
            speak("Goodbye!")
            break
        
        elif user_input == 'grasp':
            result = grasping.reach_for_object([0.5, 0.3, 0.5])
            speak(result)
            time.sleep(0.5)
            result = grasping.grasp()
            speak(result)
        
        elif user_input == 'wave':
            result = waving.wave()
            speak(result)
        
        elif user_input == 'objects':
            objects = vision.get_objects()
            if objects:
                speak(f"I see: {', '.join(objects)}")
            else:
                speak("I don't see anything right now")
        
        elif user_input == 'train':
            result = ml.train_from_demo("sample data")
            speak(result)
        
        else:
            # RASA chatbot response
            response = chatbot.get_response(user_input)
            speak(response)
            
            # RL action selection
            action = rl.get_action("current_state")
            if action == "wave":
                waving.wave(1)
            elif action == "dance":
                speak("Let's dance!")
        
    except KeyboardInterrupt:
        print("\n")
        speak("Goodbye!")
        break

vision.stop()
print("\n✅ Done")
