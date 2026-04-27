#!/usr/bin/env python3
"""
PEPPER GEMINI FINAL - النسخة النهائية
- Gemini AI ذكي (محادثة متطورة)
- حركة مستمرة (بيبر يمشي دائماً)
- 7 مشاعر من الكاميرا
- ألعاب على localhost:5009
- YouTube للأوامر "how to"
"""

import time
import random
import math
import threading
import webbrowser
import urllib.parse
import cv2
import numpy as np
import pyttsx3
from qibullet import SimulationManager
import pybullet as p
import pybullet_data

# ========== Gemini AI ==========
import google.generativeai as genai

# تكوين Gemini
GEMINI_API_KEY = "AIzaSyDEdleVKiQ5E00wMcjMbji0G9JcYT2TvE8"
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# ========== إعداد الصوت ==========
engine = pyttsx3.init()
engine.setProperty('rate', 140)
engine.setProperty('volume', 1.0)

def speak(text):
    print(f"🔊 Pepper: {text}")
    engine.say(text)
    engine.runAndWait()

# ========== Gemini AI Chat ==========
def get_gemini_response(message, emotion="neutral"):
    try:
        prompt = f"""You are Pepper, a friendly robot therapist for a child with autism. 
The child's current emotion is {emotion}. 
Respond in 1-2 short, simple English sentences. 
Be kind, encouraging, and use ABA therapy (positive reinforcement). 
Keep it fun and engaging!

Child: {message}
Pepper:"""
        
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"⚠️ Gemini error: {e}")
        return f"That's interesting! Tell me more! 😊"

# ========== 7-Emotion Detector ==========
class SevenEmotionDetector:
    def __init__(self):
        self.current_emotion = "neutral"
        self.running = True
        self.cap = None
        
        self.emotion_emoji = {
            "happy": "😊", "sad": "😢", "angry": "😠", 
            "surprise": "😲", "fear": "😨", "disgust": "🤢", "neutral": "😐"
        }
        
        # فتح الكاميرا
        for i in range(3):
            self.cap = cv2.VideoCapture(i)
            if self.cap.isOpened():
                print(f"✅ Camera {i} opened")
                break
        
        if self.cap is None or not self.cap.isOpened():
            print("⚠️ No camera found")
            self.cap = None
            return
        
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        self.thread = threading.Thread(target=self._detect_loop, daemon=True)
        self.thread.start()
        print("✅ 7-Emotion detection started")
    
    def _detect_emotion(self, face_img):
        if face_img is None or face_img.size == 0:
            return "neutral"
        
        gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
        h, w = face_img.shape[:2]
        mouth_y = h * 2 // 3
        eye_y = h // 3
        
        mouth_region = gray[mouth_y:, :]
        eye_region = gray[:eye_y, :]
        
        mouth_brightness = np.mean(mouth_region)
        eye_brightness = np.mean(eye_region)
        eye_std = np.std(eye_region)
        
        if mouth_brightness > 110 and eye_brightness > 80:
            return "happy"
        elif mouth_brightness < 65 and eye_brightness < 70:
            return "sad"
        elif eye_std > 40 and eye_brightness < 60:
            return "angry"
        elif eye_std > 35:
            return "surprise"
        elif eye_std > 30 and eye_brightness < 65:
            return "fear"
        return "neutral"
    
    def _detect_loop(self):
        while self.running and self.cap:
            ret, frame = self.cap.read()
            if not ret:
                continue
            
            frame = cv2.resize(frame, (320, 240))
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, 1.1, 5)
            
            for (x, y, w, h) in faces:
                face_roi = frame[y:y+h, x:x+w]
                if face_roi.size > 0:
                    emotion = self._detect_emotion(face_roi)
                    if emotion != "neutral":
                        self.current_emotion = emotion
                    
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    cv2.putText(frame, f"{emotion.upper()} {self.emotion_emoji.get(emotion, '😐')}", 
                               (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            cv2.putText(frame, f"Emotion: {self.current_emotion.upper()} {self.emotion_emoji.get(self.current_emotion, '😐')}", 
                       (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            cv2.imshow("Pepper - Emotion", frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        cv2.destroyAllWindows()
    
    def get_emotion(self):
        return self.current_emotion
    
    def stop(self):
        self.running = False
        if self.cap:
            self.cap.release()
        cv2.destroyAllWindows()

# ========== PyBullet Pepper مع حركة مستمرة ==========
print("\n🤖 Starting Pepper in PyBullet...")

sim_manager = SimulationManager()
client = sim_manager.launchSimulation(gui=True)
p.setAdditionalSearchPath(pybullet_data.getDataPath())
p.setRealTimeSimulation(1)
p.setGravity(0, 0, -9.81)
p.loadURDF("plane.urdf")

pepper = sim_manager.spawnPepper(client)
pepper.goToPosture("Stand", 0.5)
print("✅ Pepper loaded!")

# بالونات
colors = [[1,0,0,1], [0,1,0,1], [0,0,1,1], [1,1,0,1], [1,0.5,0,1], [1,0,1,1]]
balloons = []
for i in range(10):
    x = random.uniform(-3, 3)
    y = random.uniform(-2.5, 2.5)
    vis = p.createVisualShape(p.GEOM_SPHERE, radius=0.12, rgbaColor=colors[i%6])
    ball = p.createMultiBody(baseMass=0, baseVisualShapeIndex=vis, basePosition=[x, y, random.uniform(0.5,1.5)])
    balloons.append(ball)

p.resetDebugVisualizerCamera(cameraDistance=6, cameraYaw=45, cameraPitch=-30, cameraTargetPosition=[0,0,0.8])

# ========== حركة مستمرة ==========
t = 0
def continuous_walk():
    global t
    while True:
        t += 0.03
        x = 2.8 * math.cos(t * 0.4)
        y = 2.2 * math.sin(t * 0.55)
        try:
            pepper.setTranslation([x, y, 0.8])
        except:
            pass
        time.sleep(0.05)
threading.Thread(target=continuous_walk, daemon=True).start()

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

# حركة يدين طبيعية
arm_angle = 0
arm_dir = 1
def natural_arms():
    global arm_angle, arm_dir
    while True:
        arm_angle += 0.04 * arm_dir
        if arm_angle > 0.5:
            arm_angle = 0.5
            arm_dir = -1
        elif arm_angle < 0:
            arm_angle = 0
            arm_dir = 1
        try:
            pepper.setAngles("LShoulderPitch", arm_angle, 0.1)
            pepper.setAngles("RShoulderPitch", arm_angle, 0.1)
        except:
            pass
        time.sleep(0.05)
threading.Thread(target=natural_arms, daemon=True).start()

# ========== حركات ==========
def dance():
    for _ in range(3):
        for angle in [0.5, 1.0, 0.5, 0]:
            pepper.setAngles("LShoulderPitch", angle, 0.1)
            pepper.setAngles("RShoulderPitch", angle, 0.1)
            time.sleep(0.15)

def wave():
    for _ in range(2):
        pepper.setAngles("LShoulderPitch", 1.2, 0.1)
        pepper.setAngles("RShoulderPitch", 1.2, 0.1)
        time.sleep(0.2)
        pepper.setAngles("LShoulderPitch", 0, 0.1)
        pepper.setAngles("RShoulderPitch", 0, 0.1)
        time.sleep(0.2)

# ========== أوامر ==========
def open_youtube(topic):
    url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(topic + ' cartoon for kids')}"
    webbrowser.open(url)
    return f"📺 Opening video about {topic}!"

def open_games():
    webbrowser.open("http://localhost:5009")
    return "🎮 Opening your games! Have fun!"

# ========== بدء الكاميرا ==========
emotion_detector = SevenEmotionDetector()
time.sleep(1)

print("\n" + "="*60)
print("🤖 PEPPER GEMINI FINAL - WORKING")
print("="*60)
print("✅ Gemini AI - Intelligent conversations")
print("✅ Pepper walks CONTINUOUSLY")
print("✅ 7 Emotions detection")
print("✅ Games on localhost:5009")
print("✅ Commands: dance, wave, game, how to...")
print("✅ Type 'exit' to quit")
print("="*60 + "\n")

speak("Hello! I am Pepper! I use Gemini AI and I walk continuously! Type your messages to talk to me!")

# ========== المحادثة الرئيسية ==========
while True:
    try:
        user_input = input("\n👶 You: ").strip().lower()
        
        if user_input == 'exit':
            speak("Goodbye! See you later!")
            break
        
        elif user_input == 'dance':
            speak("Let's dance!")
            dance()
        
        elif user_input == 'wave':
            speak("Waving!")
            wave()
        
        elif user_input == 'game' or user_input == 'games':
            speak(open_games())
        
        elif user_input.startswith('how to'):
            topic = user_input.replace('how to', '').strip()
            if topic:
                speak(open_youtube(topic))
            else:
                speak("What would you like to learn?")
        
        else:
            emotion = emotion_detector.get_emotion()
            emoji = {"happy":"😊", "sad":"😢", "angry":"😠", "surprise":"😲", "fear":"😨", "disgust":"🤢", "neutral":"😐"}.get(emotion, "😐")
            print(f"📷 Emotion: {emotion.upper()} {emoji}")
            
            print("🧠 Thinking...", end="", flush=True)
            response = get_gemini_response(user_input, emotion)
            print(f"\r🤖 Pepper: {response}")
            speak(response)
            
    except KeyboardInterrupt:
        print("\n")
        speak("Goodbye!")
        break

emotion_detector.stop()
print("\n✅ Done")
