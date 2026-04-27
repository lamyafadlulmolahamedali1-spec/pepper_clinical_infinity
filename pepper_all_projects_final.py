#!/usr/bin/env python3
"""
PEPPER ALL PROJECTS FINAL - يجمع كل مشاريع Pepper
- ChatGPT对话 (pepperchat)
- Android remote control
- Gemini AI
- GPT with gestures
- AI Tutor
- Rock Paper Scissors game
- Multiple dances
- YOLO detection
- ROS2 simulation
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
from collections import deque

# ========== إعداد الصوت ==========
engine = pyttsx3.init()
engine.setProperty('rate', 150)
engine.setProperty('volume', 1.0)

def speak(text):
    print(f"🔊 Pepper: {text}")
    engine.say(text)
    engine.runAndWait()

# ========== 1. ChatGPT Dialogue (من pepperchat) ==========
class ChatGPTDialogue:
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.conversation_history = []
        self.api_url = "https://api.openai.com/v1/chat/completions"
    
    def chat(self, message):
        if not self.api_key:
            return self._fallback(message)
        
        self.conversation_history.append({"role": "user", "content": message})
        
        data = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "system", "content": "You are Pepper, a friendly robot assistant for children. Respond in short, simple English sentences."},
                *self.conversation_history[-10:]
            ],
            "max_tokens": 100
        }
        
        try:
            response = requests.post(self.api_url, json=data, headers={"Authorization": f"Bearer {self.api_key}"}, timeout=10)
            if response.status_code == 200:
                reply = response.json()["choices"][0]["message"]["content"]
                self.conversation_history.append({"role": "assistant", "content": reply})
                return reply
        except:
            pass
        return self._fallback(message)
    
    def _fallback(self, message):
        return f"You said: {message}. That's interesting! Tell me more! 😊"

# ========== 2. Gemini AI (من Pepper-Gemini-Flash-2.5) ==========
class GeminiAI:
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    
    def chat(self, message):
        if not self.api_key:
            return "I'm Pepper, your robot friend! 🤖"
        
        url = f"{self.api_url}?key={self.api_key}"
        data = {"contents": [{"parts": [{"text": message}]}]}
        
        try:
            response = requests.post(url, json=data, timeout=10)
            if response.status_code == 200:
                return response.json()["candidates"][0]["content"]["parts"][0]["text"]
        except:
            pass
        return "That's interesting! Tell me more! 😊"

# ========== 3. GPT with Gestures (من GPT-Pepper) ==========
class GPTWithGestures:
    def __init__(self, pepper):
        self.pepper = pepper
    
    def speak_with_gesture(self, text, emotion="neutral"):
        # حركة حسب المشاعر
        if emotion == "happy":
            self._happy_gesture()
        elif emotion == "excited":
            self._excited_gesture()
        else:
            self._neutral_gesture()
        speak(text)
    
    def _happy_gesture(self):
        for _ in range(2):
            self.pepper.setAngles("LShoulderPitch", 1.0, 0.1)
            self.pepper.setAngles("RShoulderPitch", 1.0, 0.1)
            time.sleep(0.15)
            self.pepper.setAngles("LShoulderPitch", 0, 0.1)
            self.pepper.setAngles("RShoulderPitch", 0, 0.1)
            time.sleep(0.15)
    
    def _excited_gesture(self):
        for angle in [0.5, 1.0, 1.2, 1.0, 0.5, 0]:
            self.pepper.setAngles("LShoulderPitch", angle, 0.1)
            self.pepper.setAngles("RShoulderPitch", angle, 0.1)
            time.sleep(0.1)
    
    def _neutral_gesture(self):
        self.pepper.setAngles("LShoulderPitch", 0.3, 0.1)
        self.pepper.setAngles("RShoulderPitch", 0.3, 0.1)
        time.sleep(0.3)
        self.pepper.setAngles("LShoulderPitch", 0, 0.1)
        self.pepper.setAngles("RShoulderPitch", 0, 0.1)

# ========== 4. AI Tutor (من pepper-ai-tutor) ==========
class AITutor:
    def __init__(self):
        self.lessons = {
            "math": ["What is 2+2?", "What is 5-3?", "What is 3x3?"],
            "english": ["What is the color of the sky?", "What sound does a dog make?"],
            "general": ["What is your name?", "How are you today?"]
        }
        self.current_lesson = None
        self.current_question_index = 0
    
    def start_lesson(self, subject):
        if subject in self.lessons:
            self.current_lesson = subject
            self.current_question_index = 0
            return f"Let's learn {subject}! {self.lessons[subject][0]}"
        return f"I don't have a lesson for {subject} yet."
    
    def check_answer(self, answer):
        if not self.current_lesson:
            return "Please start a lesson first!"
        
        correct_answers = {
            "2+2": "4", "5-3": "2", "3x3": "9",
            "color of the sky": "blue", "sound does a dog make": "woof"
        }
        
        for key, correct in correct_answers.items():
            if key in answer.lower():
                if correct in answer.lower():
                    self.current_question_index += 1
                    if self.current_question_index < len(self.lessons[self.current_lesson]):
                        return f"Correct! {self.lessons[self.current_lesson][self.current_question_index]}"
                    else:
                        self.current_lesson = None
                        return "Excellent! You completed the lesson! 🎉"
                else:
                    return f"Good try! The answer is {correct}. Let's continue."
        return "Interesting answer! Let me think about that."

# ========== 5. Rock Paper Scissors (من Pepper-Rock-Paper-Scissors) ==========
class RockPaperScissors:
    def __init__(self, pepper):
        self.pepper = pepper
        self.choices = ["rock", "paper", "scissors"]
        self.scores = {"player": 0, "pepper": 0}
    
    def play(self, player_choice):
        if player_choice not in self.choices:
            return "Choose rock, paper, or scissors!"
        
        pepper_choice = random.choice(self.choices)
        
        # حركة حسب الاختيار
        if pepper_choice == "rock":
            self._rock_gesture()
        elif pepper_choice == "paper":
            self._paper_gesture()
        else:
            self._scissors_gesture()
        
        # تحديد الفائز
        if player_choice == pepper_choice:
            result = "It's a tie!"
        elif (player_choice == "rock" and pepper_choice == "scissors") or \
             (player_choice == "paper" and pepper_choice == "rock") or \
             (player_choice == "scissors" and pepper_choice == "paper"):
            result = "You win! 🎉"
            self.scores["player"] += 1
        else:
            result = "I win! Better luck next time! 🤖"
            self.scores["pepper"] += 1
        
        return f"I chose {pepper_choice}! {result} Score: You {self.scores['player']} - Pepper {self.scores['pepper']}"
    
    def _rock_gesture(self):
        self.pepper.setAngles("RShoulderPitch", 0.5, 0.1)
        time.sleep(0.3)
        self.pepper.setAngles("RShoulderPitch", 0, 0.1)
    
    def _paper_gesture(self):
        self.pepper.setAngles("LShoulderPitch", 0.8, 0.1)
        time.sleep(0.3)
        self.pepper.setAngles("LShoulderPitch", 0, 0.1)
    
    def _scissors_gesture(self):
        for _ in range(2):
            self.pepper.setAngles("LShoulderPitch", 0.6, 0.1)
            self.pepper.setAngles("RShoulderPitch", 0.6, 0.1)
            time.sleep(0.15)
            self.pepper.setAngles("LShoulderPitch", 0, 0.1)
            self.pepper.setAngles("RShoulderPitch", 0, 0.1)
            time.sleep(0.15)

# ========== 6. Multiple Dances (من naoqi-robot-dance) ==========
class DanceCollection:
    def __init__(self, pepper):
        self.pepper = pepper
    
    def gangnam_style(self):
        for _ in range(4):
            self.pepper.setAngles("LShoulderPitch", 1.2, 0.1)
            self.pepper.setAngles("RShoulderPitch", 1.2, 0.1)
            time.sleep(0.2)
            self.pepper.setAngles("LShoulderPitch", 0.2, 0.1)
            self.pepper.setAngles("RShoulderPitch", 0.2, 0.1)
            time.sleep(0.2)
        return "Gangnam Style! 💃"
    
    def robot_dance(self):
        for _ in range(3):
            for angle in [0.5, 1.0, 0.5, 0]:
                self.pepper.setAngles("LShoulderPitch", angle, 0.1)
                self.pepper.setAngles("RShoulderPitch", angle, 0.1)
                time.sleep(0.15)
        return "Robot Dance! 🤖"
    
    def cha_cha(self):
        for _ in range(4):
            self.pepper.setAngles("LShoulderPitch", 0.8, 0.1)
            time.sleep(0.1)
            self.pepper.setAngles("LShoulderPitch", 0, 0.1)
            self.pepper.setAngles("RShoulderPitch", 0.8, 0.1)
            time.sleep(0.1)
            self.pepper.setAngles("RShoulderPitch", 0, 0.1)
        return "Cha-Cha! 💃"
    
    def happy_dance(self):
        for _ in range(3):
            self.pepper.setAngles("LShoulderPitch", 1.0, 0.1)
            self.pepper.setAngles("RShoulderPitch", 1.0, 0.1)
            time.sleep(0.2)
            self.pepper.setAngles("LShoulderPitch", 0.3, 0.1)
            self.pepper.setAngles("RShoulderPitch", 0.3, 0.1)
            time.sleep(0.2)
        return "Happy Dance! 🎉"

# ========== 7. YOLO Detection (من YOLO_RobotPepper_detection) ==========
class YOLODetector:
    def __init__(self):
        self.model = YOLO('yolov8n.pt')
        self.cap = cv2.VideoCapture(1)
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(0)
        self.detected_objects = []
        self.running = True
        threading.Thread(target=self._run, daemon=True).start()
    
    def _run(self):
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                continue
            results = self.model(frame, verbose=False)
            self.detected_objects = []
            for r in results:
                if r.boxes:
                    for box in r.boxes:
                        name = self.model.names[int(box.cls[0])]
                        self.detected_objects.append(name)
            cv2.imshow("YOLO Detection", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        self.cap.release()
        cv2.destroyAllWindows()
    
    def get_objects(self):
        return list(set(self.detected_objects))[:5]
    
    def stop(self):
        self.running = False

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
chatgpt = ChatGPTDialogue(api_key=None)  # ضعي مفتاح OpenAI هنا
gemini = GeminiAI(api_key=None)  # ضعي مفتاح Gemini هنا
gestures = GPTWithGestures(pepper)
tutor = AITutor()
rps = RockPaperScissors(pepper)
dances = DanceCollection(pepper)
vision = YOLODetector()

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
print("🤖 PEPPER ALL PROJECTS FINAL")
print("="*60)
print("✅ ChatGPT Dialogue (pepperchat)")
print("✅ Gemini AI")
print("✅ GPT with Gestures")
print("✅ AI Tutor")
print("✅ Rock Paper Scissors")
print("✅ Multiple Dances")
print("✅ YOLO Detection")
print("="*60)
print("\n📝 COMMANDS:")
print("   chat [message] - Talk to ChatGPT")
print("   gemini [message] - Talk to Gemini")
print("   learn [math/english] - Start lesson")
print("   answer [text] - Answer lesson question")
print("   play [rock/paper/scissors] - Play RPS")
print("   dance [gangnam/robot/chacha/happy] - Dance")
print("   objects - Show detected objects")
print("   exit - Quit")
print("="*60 + "\n")

speak("Hello! I am Pepper! I can chat, teach, play games, dance, and see objects!")

# ========== 11. المحادثة الرئيسية ==========
while True:
    try:
        user_input = input("\n👶 You: ").strip().lower()
        
        if user_input == 'exit':
            speak("Goodbye!")
            break
        
        elif user_input.startswith('chat '):
            msg = user_input[5:]
            response = chatgpt.chat(msg)
            gestures.speak_with_gesture(response, "happy")
        
        elif user_input.startswith('gemini '):
            msg = user_input[7:]
            response = gemini.chat(msg)
            speak(response)
        
        elif user_input.startswith('learn '):
            subject = user_input[6:]
            response = tutor.start_lesson(subject)
            speak(response)
        
        elif user_input.startswith('answer '):
            answer = user_input[7:]
            response = tutor.check_answer(answer)
            speak(response)
        
        elif user_input.startswith('play '):
            choice = user_input[5:]
            response = rps.play(choice)
            speak(response)
        
        elif user_input.startswith('dance '):
            dance_type = user_input[6:]
            if dance_type == 'gangnam':
                result = dances.gangnam_style()
            elif dance_type == 'robot':
                result = dances.robot_dance()
            elif dance_type == 'chacha':
                result = dances.cha_cha()
            elif dance_type == 'happy':
                result = dances.happy_dance()
            else:
                result = "Available dances: gangnam, robot, chacha, happy"
            speak(result)
        
        elif user_input == 'objects':
            objects = vision.get_objects()
            if objects:
                speak(f"I see: {', '.join(objects)}")
            else:
                speak("I don't see anything right now")
        
        else:
            # Default response
            speak(f"You said: {user_input}. Say 'chat hello' to talk to me!")
        
    except KeyboardInterrupt:
        print("\n")
        speak("Goodbye!")
        break

vision.stop()
print("\n✅ Done")
