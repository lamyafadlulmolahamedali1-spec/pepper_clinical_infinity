#!/usr/bin/env python3
"""
PEPPER ALL IN ONE - QIBULLET
يجمع كل المشاريع:
- shadow-hand-asl (لغة إشارة)
- robot-simulator-foundrylocal (صوت بدون نت)
- Bottle-Opener (أوامر صوتية)
- Integrated_Robot_Project (كشف أشياء)
- GenieAI (Gemini AI)
"""

import time
import random
import math
import threading
import json
import os
import subprocess
import speech_recognition as sr
import pyttsx3
import cv2
import numpy as np
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

# ========== 2. Voice Commands (من robot-simulator-foundrylocal) ==========
recognizer = sr.Recognizer()
microphone = sr.Microphone()

def listen_voice():
    try:
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            print("🎤 Listening...")
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
        text = recognizer.recognize_google(audio, language='en-US')
        print(f"✅ You said: {text}")
        return text.lower()
    except:
        return None

# ========== 3. كاميرا + كشف أشياء (من Integrated_Robot_Project) ==========
class CameraVision:
    def __init__(self):
        self.model = YOLO('yolov8n.pt')
        self.cap = cv2.VideoCapture(1)
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(0)
        self.current_object = "nothing"
        self.current_emotion = "neutral"
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
    
    def stop(self):
        self.running = False

# ========== 4. Gemini AI (من GenieAI) ==========
class GeminiBrain:
    def __init__(self, api_keys=None):
        self.api_keys = api_keys or []
        self.current_key_index = 0
        self.conversation_history = []
        self.api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    
    def _call_gemini(self, prompt):
        if not self.api_keys:
            return self._fallback(prompt)
        key = self.api_keys[self.current_key_index]
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        url = f"{self.api_url}?key={key}"
        
        data = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 150}
        }
        try:
            response = requests.post(url, json=data, timeout=15)
            if response.status_code == 200:
                return response.json()["candidates"][0]["content"]["parts"][0]["text"]
        except:
            pass
        return self._fallback(prompt)
    
    def _fallback(self, prompt):
        return f"That's interesting! Tell me more about '{prompt[:50]}' 😊"
    
    def chat(self, message):
        return self._call_gemini(message)

# ========== 5. لغة إشارة (ASL) من shadow-hand-asl ==========
class ASLGestures:
    def __init__(self, pepper):
        self.pepper = pepper
    
    def letter_a(self):
        for _ in range(2):
            self.pepper.setAngles("LShoulderPitch", 0.5, 0.1)
            time.sleep(0.2)
            self.pepper.setAngles("LShoulderPitch", 0, 0.1)
            time.sleep(0.2)
    
    def letter_b(self):
        for _ in range(2):
            self.pepper.setAngles("RShoulderPitch", 0.5, 0.1)
            time.sleep(0.2)
            self.pepper.setAngles("RShoulderPitch", 0, 0.1)
            time.sleep(0.2)
    
    def hello(self):
        for _ in range(2):
            self.pepper.setAngles("LShoulderPitch", 1.0, 0.1)
            self.pepper.setAngles("RShoulderPitch", 1.0, 0.1)
            time.sleep(0.2)
            self.pepper.setAngles("LShoulderPitch", 0, 0.1)
            self.pepper.setAngles("RShoulderPitch", 0, 0.1)
            time.sleep(0.2)

# ========== 6. بدء qiBullet ==========
print("🤖 Starting Pepper in qiBullet...")

sim_manager = SimulationManager()
client_id = sim_manager.launchSimulation(gui=True)

pepper = sim_manager.spawnPepper(client_id, translation=[0, 0, 0], quaternion=[0, 0, 0, 1])

p.setAdditionalSearchPath(pybullet_data.getDataPath())
p.loadURDF("plane.urdf")
p.setGravity(0, 0, -9.81)

print("✅ Pepper loaded!")

# ========== 7. بالونات ==========
colors = [[1,0,0,1], [0,1,0,1], [0,0,1,1], [1,1,0,1], [1,0.5,0,1]]
balloons = []
for i in range(10):
    x = random.uniform(-3, 3)
    y = random.uniform(-2.5, 2.5)
    vis = p.createVisualShape(p.GEOM_SPHERE, radius=0.12, rgbaColor=colors[i%5])
    ball = p.createMultiBody(baseMass=0, baseVisualShapeIndex=vis, basePosition=[x, y, random.uniform(0.5,1.5)])
    balloons.append(ball)

p.resetDebugVisualizerCamera(cameraDistance=6, cameraYaw=45, cameraPitch=-30, cameraTargetPosition=[0,0,0.8])

# ========== 8. تشغيل الكاميرا والحركات ==========
camera = CameraVision()
asl = ASLGestures(pepper)
gemini = GeminiBrain(api_keys=[])  # ضعي مفاتيح Gemini API هنا

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
print("🤖 PEPPER ALL IN ONE - QIBULLET")
print("="*60)
print("✅ Camera (YOLO + Emotion)")
print("✅ ASL Gestures (A, B, Hello)")
print("✅ Voice Commands")
print("✅ Gemini AI (with API key rotation)")
print("✅ Continuous walking")
print("="*60)
print("\n📝 COMMANDS:")
print("   Type: hello, a, b, what is...")
print("   Or say: hello, a, b, what is...")
print("   Type 'exit' to quit")
print("="*60 + "\n")

speak("Hello! I am Pepper! I can see, hear, and talk! Try saying hello, a, or b!")

# ========== 9. المحادثة الرئيسية ==========
mode = "type"  # type or voice

while True:
    try:
        if mode == "type":
            user_input = input("\n👶 You: ").strip()
        else:
            user_input = listen_voice()
            if user_input is None:
                continue
        
        if user_input.lower() == 'exit':
            speak("Goodbye!")
            break
        
        if user_input.lower() == 'voice':
            mode = "voice"
            print("🎤 Voice mode activated. Say your command...")
            continue
        
        if user_input.lower() == 'type':
            mode = "type"
            print("📝 Type mode activated.")
            continue
        
        # أوامر لغة الإشارة
        if user_input.lower() == 'a':
            asl.letter_a()
            speak("Letter A in sign language!")
            continue
        elif user_input.lower() == 'b':
            asl.letter_b()
            speak("Letter B in sign language!")
            continue
        elif user_input.lower() == 'hello':
            asl.hello()
            speak("Hello! Nice to see you!")
            continue
        
        # إضافة معلومات من الكاميرا
        vision = camera.get_vision()
        print(f"📷 {vision}")
        
        # رد من Gemini AI
        response = gemini.chat(user_input)
        speak(response)
        
    except KeyboardInterrupt:
        print("\n")
        speak("Goodbye!")
        break

camera.stop()
print("\n✅ Done")
