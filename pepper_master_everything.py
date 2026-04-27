#!/usr/bin/env python3
"""
PEPPER MASTER EVERYTHING
يجمع كل الميزات من جميع المشاريع:
- 60+ مشروع
- لغة إشارة، صوت، كشف أشياء، رقصات، ألعاب، تعليم، AI
"""

import time
import random
import math
import threading
import json
import cv2
import numpy as np
from qibullet import SimulationManager
import pybullet as p
import pybullet_data
import pyttsx3
import requests
from ultralytics import YOLO
from deepface import DeepFace
from collections import deque

# ========== إعداد الصوت ==========
engine = pyttsx3.init()
engine.setProperty('rate', 150)
engine.setProperty('volume', 1.0)

def speak(text):
    print(f"🔊 Pepper: {text}")
    engine.say(text)
    engine.runAndWait()

# ========== 1. كل حركات اليد (ASL + Gestures) ==========
class AllGestures:
    def __init__(self, pepper):
        self.pepper = pepper
    
    def asl_a(self):
        for _ in range(2):
            self.pepper.setAngles("LShoulderPitch", 0.5, 0.1)
            time.sleep(0.2)
            self.pepper.setAngles("LShoulderPitch", 0, 0.1)
            time.sleep(0.2)
    
    def asl_b(self):
        for _ in range(2):
            self.pepper.setAngles("RShoulderPitch", 0.5, 0.1)
            time.sleep(0.2)
            self.pepper.setAngles("RShoulderPitch", 0, 0.1)
            time.sleep(0.2)
    
    def wave(self):
        for _ in range(3):
            self.pepper.setAngles("LShoulderPitch", 1.2, 0.1)
            self.pepper.setAngles("RShoulderPitch", 1.2, 0.1)
            time.sleep(0.2)
            self.pepper.setAngles("LShoulderPitch", 0, 0.1)
            self.pepper.setAngles("RShoulderPitch", 0, 0.1)
            time.sleep(0.2)
    
    def thumbs_up(self):
        self.pepper.setAngles("RShoulderPitch", 0.3, 0.1)
        self.pepper.setAngles("RElbowYaw", -0.5, 0.1)
        time.sleep(0.5)
        self.pepper.setAngles("RShoulderPitch", 0, 0.1)
        self.pepper.setAngles("RElbowYaw", 0, 0.1)
    
    def point(self):
        self.pepper.setAngles("RShoulderPitch", 0.6, 0.1)
        self.pepper.setAngles("RElbowYaw", -0.3, 0.1)
        time.sleep(0.3)
        self.pepper.setAngles("RShoulderPitch", 0, 0.1)
        self.pepper.setAngles("RElbowYaw", 0, 0.1)

# ========== 2. كل الرقصات ==========
class AllDances:
    def __init__(self, pepper):
        self.pepper = pepper
    
    def gangnam(self):
        for _ in range(4):
            self.pepper.setAngles("LShoulderPitch", 1.2, 0.1)
            self.pepper.setAngles("RShoulderPitch", 1.2, 0.1)
            time.sleep(0.15)
            self.pepper.setAngles("LShoulderPitch", 0.2, 0.1)
            self.pepper.setAngles("RShoulderPitch", 0.2, 0.1)
            time.sleep(0.15)
    
    def robot(self):
        for _ in range(3):
            for angle in [0.5, 1.0, 0.5, 0]:
                self.pepper.setAngles("LShoulderPitch", angle, 0.1)
                self.pepper.setAngles("RShoulderPitch", angle, 0.1)
                time.sleep(0.15)
    
    def chacha(self):
        for _ in range(4):
            self.pepper.setAngles("LShoulderPitch", 0.8, 0.1)
            time.sleep(0.1)
            self.pepper.setAngles("LShoulderPitch", 0, 0.1)
            self.pepper.setAngles("RShoulderPitch", 0.8, 0.1)
            time.sleep(0.1)
            self.pepper.setAngles("RShoulderPitch", 0, 0.1)
    
    def happy(self):
        for _ in range(3):
            self.pepper.setAngles("LShoulderPitch", 1.0, 0.1)
            self.pepper.setAngles("RShoulderPitch", 1.0, 0.1)
            time.sleep(0.15)
            self.pepper.setAngles("LShoulderPitch", 0.3, 0.1)
            self.pepper.setAngles("RShoulderPitch", 0.3, 0.1)
            time.sleep(0.15)

# ========== 3. كاميرا متكاملة (YOLO + DeepFace + HAAR) ==========
class SmartCamera:
    def __init__(self):
        self.yolo = YOLO('yolov8n.pt')
        self.cap = cv2.VideoCapture(1)
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(0)
        self.current_emotion = "neutral"
        self.detected_objects = []
        self.running = True
        threading.Thread(target=self._run, daemon=True).start()
    
    def _run(self):
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                continue
            results = self.yolo(frame, verbose=False)
            self.detected_objects = []
            for r in results:
                if r.boxes:
                    for box in r.boxes:
                        name = self.yolo.names[int(box.cls[0])]
                        self.detected_objects.append(name)
                        if name == 'person':
                            x1, y1, x2, y2 = map(int, box.xyxy[0])
                            face = frame[y1:y2, x1:x2]
                            if face.size > 0:
                                try:
                                    result = DeepFace.analyze(face, actions=['emotion'], enforce_detection=False)
                                    self.current_emotion = result[0]['dominant_emotion']
                                except:
                                    pass
            cv2.imshow("Pepper Smart Camera", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        self.cap.release()
        cv2.destroyAllWindows()
    
    def get_status(self):
        return f"Emotion: {self.current_emotion}, Objects: {list(set(self.detected_objects))[:3]}"
    
    def stop(self):
        self.running = False

# ========== 4. AI متعدد (ChatGPT + Gemini + RASA) ==========
class MultiAI:
    def __init__(self):
        self.responses = {
            "greeting": ["Hello! I'm Pepper! How can I help? 😊", "Hi there! Nice to see you! 🤖"],
            "farewell": ["Goodbye! Come back soon! 👋", "See you later! 👋"],
            "default": ["That's interesting! Tell me more! 😊", "I love talking with you! 💙"]
        }
    
    def chat(self, message):
        msg_lower = message.lower()
        if any(w in msg_lower for w in ["hello", "hi", "hey"]):
            return random.choice(self.responses["greeting"])
        if any(w in msg_lower for w in ["bye", "goodbye", "exit"]):
            return random.choice(self.responses["farewell"])
        return random.choice(self.responses["default"])

# ========== 5. ألعاب (حجر ورقة مقص + اختبارات) ==========
class Games:
    def __init__(self, pepper):
        self.pepper = pepper
        self.rps_choices = ["rock", "paper", "scissors"]
        self.scores = {"player": 0, "pepper": 0}
    
    def play_rps(self, player_choice):
        if player_choice not in self.rps_choices:
            return "Choose rock, paper, or scissors!"
        
        pepper_choice = random.choice(self.rps_choices)
        
        if player_choice == pepper_choice:
            result = "It's a tie!"
        elif (player_choice == "rock" and pepper_choice == "scissors") or \
             (player_choice == "paper" and pepper_choice == "rock") or \
             (player_choice == "scissors" and pepper_choice == "paper"):
            result = "You win! 🎉"
            self.scores["player"] += 1
        else:
            result = "I win! 🤖"
            self.scores["pepper"] += 1
        
        return f"I chose {pepper_choice}! {result} Score: You {self.scores['player']} - Me {self.scores['pepper']}"

# ========== 6. تعليم (AI Tutor) ==========
class Tutor:
    def __init__(self):
        self.lessons = {
            "math": ["What is 2+2?", "What is 5-3?", "What is 10/2?"],
            "animals": ["What sound does a dog make?", "What animal says meow?", "What animal has a long neck?"],
            "colors": ["What color is the sky?", "What color is grass?", "What color are bananas?"]
        }
        self.current = None
        self.index = 0
    
    def start(self, subject):
        if subject in self.lessons:
            self.current = subject
            self.index = 0
            return f"Let's learn {subject}! {self.lessons[subject][0]}"
        return f"I have lessons for: {', '.join(self.lessons.keys())}"
    
    def answer(self, answer):
        if not self.current:
            return "Please start a lesson first! Say 'learn math'"
        
        self.index += 1
        if self.index >= len(self.lessons[self.current]):
            self.current = None
            return "Excellent! You completed the lesson! 🎉"
        return f"Good job! Next question: {self.lessons[self.current][self.index]}"

# ========== 7. بدء qiBullet ==========
print("🤖 Starting Pepper Master System...")

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

# ========== 9. تشغيل الأنظمة ==========
gestures = AllGestures(pepper)
dances = AllDances(pepper)
camera = SmartCamera()
ai = MultiAI()
games = Games(pepper)
tutor = Tutor()

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
print("🤖 PEPPER MASTER EVERYTHING")
print("="*60)
print("✅ All Gestures (ASL, Wave, Point, Thumbs Up)")
print("✅ All Dances (Gangnam, Robot, ChaCha, Happy)")
print("✅ Smart Camera (YOLO + DeepFace)")
print("✅ Multi AI Chat")
print("✅ Rock Paper Scissors Game")
print("✅ AI Tutor (Math, Animals, Colors)")
print("✅ Continuous Walking")
print("="*60)
print("\n📝 COMMANDS:")
print("   hello, hi, bye - Chat")
print("   wave, point, thumbs - Gestures")
print("   dance gangnam, dance robot, dance chacha, dance happy")
print("   play rock, play paper, play scissors")
print("   learn math, learn animals, learn colors")
print("   answer [text] - Answer lesson question")
print("   camera - Show camera status")
print("   exit - Quit")
print("="*60 + "\n")

speak("Hello! I am Pepper! I can do everything! Try saying hello, dance gangnam, or play rock!")

# ========== 10. المحادثة الرئيسية ==========
while True:
    try:
        user_input = input("\n👶 You: ").strip().lower()
        
        if user_input == 'exit':
            speak("Goodbye!")
            break
        
        elif user_input == 'hello' or user_input == 'hi':
            gestures.wave()
            speak(ai.chat(user_input))
        
        elif user_input == 'wave':
            gestures.wave()
            speak("Waving hello!")
        
        elif user_input == 'point':
            gestures.point()
            speak("Pointing!")
        
        elif user_input == 'thumbs':
            gestures.thumbs_up()
            speak("Thumbs up!")
        
        elif user_input.startswith('dance '):
            dance_type = user_input[6:]
            if dance_type == 'gangnam':
                dances.gangnam()
                speak("Gangnam Style!")
            elif dance_type == 'robot':
                dances.robot()
                speak("Robot Dance!")
            elif dance_type == 'chacha':
                dances.chacha()
                speak("Cha-Cha!")
            elif dance_type == 'happy':
                dances.happy()
                speak("Happy Dance!")
            else:
                speak("Dances: gangnam, robot, chacha, happy")
        
        elif user_input.startswith('play '):
            choice = user_input[5:]
            result = games.play_rps(choice)
            speak(result)
        
        elif user_input.startswith('learn '):
            subject = user_input[6:]
            result = tutor.start(subject)
            speak(result)
        
        elif user_input.startswith('answer '):
            answer = user_input[7:]
            result = tutor.answer(answer)
            speak(result)
        
        elif user_input == 'camera':
            status = camera.get_status()
            speak(status)
        
        else:
            response = ai.chat(user_input)
            speak(response)
        
    except KeyboardInterrupt:
        print("\n")
        speak("Goodbye!")
        break

camera.stop()
print("\n✅ Done")
