#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║     🤖 PEPPER - AI THERAPIST FOR AUTISM (GEMINI POWERED)                    ║
║     ABA | DTT | TEACCH | TIE | PyBullet | Real-time Emotion Detection      ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import time
import random
import math
import threading
import queue
import webbrowser
import urllib.parse
import json
from datetime import datetime

# ========== Core Libraries ==========
import cv2
import numpy as np
import pyttsx3
import speech_recognition as sr
import requests
from qibullet import SimulationManager
import pybullet as p
import pybullet_data

# ========== Gemini AI ==========
import google.generativeai as genai

# ========== Configuration ==========
GEMINI_API_KEY = "AIzaSyDEdleVKiQ5E00wMcjMbji0G9JcYT2TvE8"
GEMINI_MODEL = "gemini-1.5-flash"

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(GEMINI_MODEL)

# ========== Voice Settings ==========
engine = pyttsx3.init()
engine.setProperty('rate', 150)
engine.setProperty('volume', 1.0)
voices = engine.getProperty('voices')
for voice in voices:
    if 'female' in voice.name.lower() or 'english' in voice.name.lower():
        engine.setProperty('voice', voice.id)
        break

def speak(text):
    print(f"🔊 Pepper: {text}")
    engine.say(text)
    engine.runAndWait()

# ========== High-Sensitivity Microphone ==========
recognizer = sr.Recognizer()
recognizer.energy_threshold = 20  # Very low for quiet voices
recognizer.dynamic_energy_threshold = True
mic = None

try:
    mic = sr.Microphone()
    with mic as source:
        print("🎤 Calibrating microphone...")
        recognizer.adjust_for_ambient_noise(source, duration=1)
    print(f"✅ Microphone ready (threshold: {recognizer.energy_threshold})")
except Exception as e:
    print(f"⚠️ Microphone error: {e}")

def listen():
    if mic is None:
        return None
    try:
        with mic as source:
            print("\n🎤 Listening...", end="", flush=True)
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=8)
        text = recognizer.recognize_google(audio, language='en-US')
        print(f"\r   ✅ You said: {text}")
        return text.lower()
    except sr.WaitTimeoutError:
        print("\r   ⏰ No speech detected", end="", flush=True)
        return None
    except sr.UnknownValueError:
        print("\r   ❌ Could not understand", end="", flush=True)
        return None
    except Exception as e:
        print(f"\r   ❌ Error: {e}", end="", flush=True)
        return None

# ========== High-Accuracy Camera & Emotion Detection ==========
class EmotionCamera:
    def __init__(self):
        self.current_emotion = "neutral"
        self.current_face = None
        self.running = True
        self.emotion_history = []
        self.last_emotion_time = 0
        
        # Initialize camera with multiple attempts
        self.cap = None
        for i in range(3):
            self.cap = cv2.VideoCapture(i)
            if self.cap.isOpened():
                print(f"✅ Camera {i} opened")
                break
        
        if self.cap is None or not self.cap.isOpened():
            print("⚠️ No camera found - running without emotion detection")
            self.cap = None
            return
        
        # Set camera properties for better performance
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        
        # Load face cascade
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        
        # Start detection thread
        self.thread = threading.Thread(target=self._detect_loop, daemon=True)
        self.thread.start()
    
    def _detect_emotion_simple(self, face_img):
        """Simple emotion detection using color and shape analysis (fallback)"""
        if face_img is None or face_img.size == 0:
            return "neutral"
        
        # Simple mouth detection for smile
        gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
        mouth_region = gray[gray.shape[0]//2:, :]
        mouth_brightness = np.mean(mouth_region)
        
        if mouth_brightness > 100:
            return "happy"
        elif mouth_brightness < 60:
            return "sad"
        return "neutral"
    
    def _detect_loop(self):
        while self.running and self.cap:
            ret, frame = self.cap.read()
            if not ret:
                continue
            
            # Resize for faster processing
            frame = cv2.resize(frame, (320, 240))
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Detect faces
            faces = self.face_cascade.detectMultiScale(gray, 1.1, 5)
            
            emotion = "neutral"
            for (x, y, w, h) in faces:
                self.current_face = (x, y, w, h)
                face_roi = frame[y:y+h, x:x+w]
                if face_roi.size > 0:
                    # Try DeepFace if available, otherwise use simple method
                    try:
                        from deepface import DeepFace
                        result = DeepFace.analyze(face_roi, actions=['emotion'], enforce_detection=False)
                        emotion = result[0]['dominant_emotion']
                    except:
                        emotion = self._detect_emotion_simple(face_roi)
                    
                    # Draw rectangle and emotion text
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    
                    # Emoji for emotion
                    emoji = {"happy":"😊", "sad":"😢", "angry":"😠", "surprise":"😲", "fear":"😨", "neutral":"😐"}.get(emotion, "😐")
                    cv2.putText(frame, f"{emotion.upper()} {emoji}", (x, y-10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            # Update current emotion
            if emotion != "neutral":
                self.current_emotion = emotion
                self.emotion_history.append(emotion)
                if len(self.emotion_history) > 30:
                    self.emotion_history = self.emotion_history[-30:]
                self.last_emotion_time = time.time()
            
            # Show FPS and status
            cv2.putText(frame, f"Emotion: {self.current_emotion}", (10, 20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            cv2.imshow("Pepper Vision - Emotion Detection", frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        cv2.destroyAllWindows()
    
    def get_emotion(self):
        # Return emotion from last 2 seconds if available
        if time.time() - self.last_emotion_time < 2:
            return self.current_emotion
        return "neutral"
    
    def stop(self):
        self.running = False
        if self.cap:
            self.cap.release()
        cv2.destroyAllWindows()

# ========== Gemini AI Chat with Therapy Context ==========
class GeminiTherapist:
    def __init__(self):
        self.conversation_history = []
        self.child_name = "Yusuf"
        self.therapy_mode = "ABA"
    
    def get_response(self, user_input, emotion="neutral"):
        # Build system prompt with therapy context
        system_prompt = f"""You are Pepper, an AI therapist for a child named {self.child_name} with Autism Spectrum Disorder.

THERAPY PROTOCOLS:
- ABA (Applied Behavior Analysis): Use positive reinforcement, clear instructions, break tasks into steps
- DTT (Discrete Trial Training): Give one instruction at a time, wait for response, provide immediate feedback
- TEACCH: Use structured, predictable responses
- TIE: Be therapeutic and educational

CURRENT CONTEXT:
- Child's emotion: {emotion}
- Therapy mode: {self.therapy_mode}

RULES:
1. Respond in 1-2 short, simple English sentences
2. Be VERY enthusiastic and encouraging! Use exclamation marks!
3. Use positive reinforcement: "Great job!", "Excellent!", "You're doing amazing!"
4. If child seems frustrated, offer comfort and simplify
5. If child asks "how to" do something, say "I'll show you a video!"
6. If child wants to play, say "Let's play a game!"
7. Use emojis to be engaging 😊

Child's message: {user_input}

Respond as Pepper, the enthusiastic therapist:"""

        # Add to history
        self.conversation_history.append({"role": "user", "content": user_input})
        
        # Keep last 10 messages
        if len(self.conversation_history) > 10:
            self.conversation_history = self.conversation_history[-10:]
        
        try:
            # Use Gemini
            chat = model.start_chat(history=[])
            response = chat.send_message(system_prompt + "\n\nChild: " + user_input)
            reply = response.text
            
            self.conversation_history.append({"role": "assistant", "content": reply})
            return reply
        except Exception as e:
            print(f"⚠️ Gemini error: {e}")
            return self._fallback_response(user_input, emotion)
    
    def _fallback_response(self, user_input, emotion):
        responses = {
            "happy": "I'm so happy you're happy! 😊 That's wonderful! Let's keep having fun! 🎉",
            "sad": "It's okay to feel sad. 🤗 I'm here with you. Would you like to do a fun activity? 🌟",
            "angry": "Let's take a deep breath together. 🧘 Breathe in... breathe out... You're doing great! 💪",
            "fear": "You're safe with me! 🛡️ Let's do something calming together. What's your favorite thing?",
            "neutral": f"That's interesting, {self.child_name}! Tell me more! I love talking with you! 🌟"
        }
        return responses.get(emotion, responses["neutral"])
    
    def set_child_name(self, name):
        self.child_name = name

# ========== PyBullet Pepper Robot ==========
class PepperRobot:
    def __init__(self):
        print("🤖 Starting Pepper in PyBullet...")
        self.sim_manager = SimulationManager()
        self.client = self.sim_manager.launchSimulation(gui=True)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.setRealTimeSimulation(1)
        p.setGravity(0, 0, -9.81)
        p.loadURDF("plane.urdf")
        
        self.pepper = self.sim_manager.spawnPepper(self.client)
        self.pepper.goToPosture("Stand", 0.5)
        print("✅ Pepper loaded!")
        
        # Create balloons
        colors = [[1,0,0,1], [0,1,0,1], [0,0,1,1], [1,1,0,1], [1,0.5,0,1], [1,0,1,1]]
        self.balloons = []
        for i in range(10):
            x = random.uniform(-3, 3)
            y = random.uniform(-2.5, 2.5)
            vis = p.createVisualShape(p.GEOM_SPHERE, radius=0.12, rgbaColor=colors[i%6])
            ball = p.createMultiBody(baseMass=0, baseVisualShapeIndex=vis, basePosition=[x, y, random.uniform(0.5,1.5)])
            self.balloons.append(ball)
        
        p.resetDebugVisualizerCamera(cameraDistance=6, cameraYaw=45, cameraPitch=-30, cameraTargetPosition=[0,0,0.8])
        
        self.running = True
        self.t = 0
        self.arm_angle = 0
        self.arm_dir = 1
        
        # Start threads
        threading.Thread(target=self._walk, daemon=True).start()
        threading.Thread(target=self._move_arms, daemon=True).start()
        threading.Thread(target=self._update_balloons, daemon=True).start()
    
    def _walk(self):
        while self.running:
            self.t += 0.02
            x = 2.5 * math.cos(self.t * 0.35)
            y = 2.0 * math.sin(self.t * 0.5)
            try:
                self.pepper.setTranslation([x, y, 0.8])
            except:
                pass
            time.sleep(0.05)
    
    def _move_arms(self):
        while self.running:
            self.arm_angle += 0.05 * self.arm_dir
            if self.arm_angle > 0.4:
                self.arm_angle = 0.4
                self.arm_dir = -1
            elif self.arm_angle < 0:
                self.arm_angle = 0
                self.arm_dir = 1
            try:
                self.pepper.setAngles("LShoulderPitch", self.arm_angle, 0.1)
                self.pepper.setAngles("RShoulderPitch", self.arm_angle, 0.1)
            except:
                pass
            time.sleep(0.05)
    
    def _update_balloons(self):
        while self.running:
            for b in self.balloons:
                pos, _ = p.getBasePositionAndOrientation(b)
                new_z = pos[2] + 0.008
                if new_z > 1.6:
                    new_z = 0.3
                p.resetBasePositionAndOrientation(b, [pos[0], pos[1], new_z], [0,0,0,1])
            p.stepSimulation()
            time.sleep(1/60.)
    
    def wave(self):
        for _ in range(2):
            try:
                self.pepper.setAngles("LShoulderPitch", 1.2, 0.15)
                self.pepper.setAngles("RShoulderPitch", 1.2, 0.15)
                time.sleep(0.2)
                self.pepper.setAngles("LShoulderPitch", 0, 0.15)
                self.pepper.setAngles("RShoulderPitch", 0, 0.15)
                time.sleep(0.2)
            except:
                pass
    
    def dance(self):
        for _ in range(3):
            for angle in [0.5, 1.0, 0.5, 0]:
                try:
                    self.pepper.setAngles("LShoulderPitch", angle, 0.1)
                    self.pepper.setAngles("RShoulderPitch", angle, 0.1)
                    time.sleep(0.15)
                except:
                    pass
    
    def stop(self):
        self.running = False

# ========== Web Actions Handler ==========
def open_youtube_video(topic):
    url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(topic + ' cartoon for kids educational')}"
    webbrowser.open(url)
    return f"📺 Opening video about {topic}!"

def open_image(topic):
    url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(topic + ' for kids')}"
    webbrowser.open(url)
    return f"🖼️ Opening picture of {topic}!"

def open_games():
    webbrowser.open("http://localhost:5009")
    return "🎮 Opening your games! Have fun!"

# ========== Main System ==========
class PepperTherapySystem:
    def __init__(self):
        print("\n" + "="*70)
        print("╔════════════════════════════════════════════════════════════════════╗")
        print("║     🤖 PEPPER ULTIMATE AI THERAPIST - GEMINI POWERED             ║")
        print("║     ABA | DTT | TEACCH | TIE | PyBullet | Real-time Emotion     ║")
        print("╚════════════════════════════════════════════════════════════════════╝")
        print("="*70)
        
        # Start components
        self.camera = EmotionCamera()
        self.therapist = GeminiTherapist()
        self.pepper = PepperRobot()
        
        # Set child name
        self.therapist.set_child_name("Yusuf")
        
        print("\n✅ All systems ready!")
        print("📝 Commands: type anything or speak into microphone")
        print("🎮 Type 'game' to open games")
        print("👋 Type 'wave' to see Pepper wave")
        print("💃 Type 'dance' to see Pepper dance")
        print("❌ Type 'exit' to quit")
        print("="*70 + "\n")
        
        # Welcome message
        speak("Hello! I am Pepper! I'm your AI therapist! I use ABA and DTT therapy methods. Let's have fun learning together! How are you feeling today? 😊")
        self.pepper.wave()
    
    def process_command(self, user_input):
        cmd = user_input.lower().strip()
        
        if cmd == 'wave':
            self.pepper.wave()
            return "👋 Waving hello to you!"
        elif cmd == 'dance':
            self.pepper.dance()
            return "💃 Let's dance together!"
        elif cmd == 'game' or cmd == 'games' or cmd == 'play':
            return open_games()
        elif cmd.startswith('how to'):
            topic = cmd.replace('how to', '').strip()
            if topic:
                return open_youtube_video(topic)
        elif cmd.startswith('picture') or cmd.startswith('image'):
            topic = cmd.replace('picture', '').replace('image', '').strip()
            if topic:
                return open_image(topic)
        
        return None
    
    def run(self):
        while True:
            try:
                # Check for voice input
                user_input = listen()
                
                if user_input is None:
                    # Also check for typed input
                    print("\n💬 Type message (or press Enter to speak): ", end="")
                    typed = input().strip().lower()
                    if typed:
                        user_input = typed
                    else:
                        continue
                
                if user_input in ['exit', 'quit', 'bye', 'goodbye']:
                    speak("Goodbye! It was wonderful talking with you! Come back soon! 👋")
                    break
                
                # Get current emotion from camera
                emotion = self.camera.get_emotion()
                if emotion != "neutral":
                    print(f"📷 Detected emotion: {emotion.upper()}")
                
                # Check for commands first
                result = self.process_command(user_input)
                if result:
                    speak(result)
                    continue
                
                # Get AI response
                print("🤔 Thinking...")
                response = self.therapist.get_response(user_input, emotion)
                speak(response)
                
            except KeyboardInterrupt:
                print("\n")
                speak("Goodbye! See you next time! 👋")
                break
            except Exception as e:
                print(f"⚠️ Error: {e}")
                continue
        
        self.camera.stop()
        self.pepper.stop()
        print("\n✅ System shutdown")

if __name__ == "__main__":
    system = PepperTherapySystem()
    system.run()
