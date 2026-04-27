#!/usr/bin/env python3
"""
PEPPER BALLOON CHASER - ULTIMATE VERSION
- PyBullet Pepper in room with balloons (original working version)
- Voice input (microphone)
- Voice output (speaker)
- ASD support features
- Movement commands
- Emotion recognition
- Daily routine
- Breathing exercise
- Parent dashboard integration
- Games on localhost:5001
"""

import os
import sys
import time
import threading
import webbrowser
import urllib.parse
import random
import math
import json
import requests
import speech_recognition as sr
import pyttsx3
from datetime import datetime
from collections import deque
from qibullet import SimulationManager
import pybullet as p
import pybullet_data

# ========== Settings ==========
GAME_URL = "http://localhost:5001"
YOUTUBE_BASE = "https://www.youtube.com/results?search_query="
CARTOON_SUFFIX = "cartoon for kids educational"

# ========== Text-to-Speech (Pepper Talks) ==========
class PepperSpeaker:
    def __init__(self):
        try:
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', 155)
            self.engine.setProperty('volume', 1.0)
            voices = self.engine.getProperty('voices')
            for voice in voices:
                if 'english' in voice.name.lower():
                    self.engine.setProperty('voice', voice.id)
                    break
            self.available = True
            print("🔊 Pepper's voice ready!")
        except:
            self.available = False
            print("⚠️ Speaker not available")
    
    def speak(self, text):
        print(f"🔊 Pepper: {text}")
        if self.available:
            self.engine.say(text)
            self.engine.runAndWait()

# ========== Voice Input (Pepper Listens) ==========
class PepperMicrophone:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 300
        self.microphone = None
        try:
            self.microphone = sr.Microphone()
            with self.microphone as source:
                print("🎤 Adjusting microphone...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1.5)
            print("🎤 Microphone ready!")
        except Exception as e:
            print(f"⚠️ Microphone not available: {e}")
    
    def listen(self):
        if not self.microphone:
            return None
        try:
            with self.microphone as source:
                print("\n🎤 Listening...", end="", flush=True)
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=8)
            text = self.recognizer.recognize_google(audio, language='en-US')
            print(f"\r   ✅ You said: '{text}'")
            return text.lower()
        except sr.WaitTimeoutError:
            print("\r   ⏰ No speech detected", end="", flush=True)
            return None
        except:
            print("\r   ❌ Could not understand", end="", flush=True)
            return None

# ========== ASD Support Features ==========
class AutismSupport:
    def __init__(self):
        self.knowledge = {
            "what is autism": "Autism Spectrum Disorder (ASD) is a developmental condition affecting communication, behavior, and social interaction. Each person with autism is unique.",
            "signs of autism": "Common signs: delayed speech, avoiding eye contact, repetitive movements, sensory sensitivities, difficulty with social interactions.",
            "aba therapy": "ABA (Applied Behavior Analysis) uses positive reinforcement to teach new skills and reduce challenging behaviors. It's evidence-based.",
            "pecs": "PECS (Picture Exchange Communication System) helps non-verbal individuals communicate using pictures. It's very effective for autism.",
            "sensory overload": "Create a calm environment, use noise-canceling headphones, offer weighted blankets, provide a quiet space to decompress.",
            "early intervention": "Early diagnosis and intervention (before age 3) greatly improves outcomes. Focus on speech, occupational, and behavioral therapy.",
            "how to communicate": "Use simple language, visual supports, be patient, listen actively, and validate their feelings.",
            "routine importance": "Visual schedules and consistent routines reduce anxiety and help with transitions."
        }
        
        self.emotions = {
            "happy": ["happy", "glad", "excited", "wonderful", "great", "awesome", "joy"],
            "sad": ["sad", "upset", "unhappy", "depressed", "lonely", "crying"],
            "angry": ["angry", "mad", "frustrated", "annoyed", "irritated"],
            "scared": ["scared", "afraid", "frightened", "worried", "anxious"],
            "tired": ["tired", "exhausted", "sleepy", "drained"]
        }
        
        self.routines = {
            "morning": ["Wake up 🛌", "Brush teeth 🪥", "Wash face 🧼", "Get dressed 👕", "Eat breakfast 🍳", "Pack bag 🎒"],
            "afternoon": ["Learning time 📚", "Play time 🎮", "Eat lunch 🍎", "Rest time 😴", "Outdoor walk 🚶"],
            "evening": ["Eat dinner 🍽️", "Bath time 🛁", "Read story 📖", "Brush teeth 🪥", "Bedtime 😴"]
        }
    
    def get_answer(self, question):
        q = question.lower()
        for key, answer in self.knowledge.items():
            if key in q:
                return answer
        return None
    
    def detect_emotion(self, text):
        text_lower = text.lower()
        for emotion, keywords in self.emotions.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return emotion
        return "neutral"
    
    def get_emotion_response(self, emotion):
        responses = {
            "happy": "I'm so happy you're feeling happy! Your joy makes me smile! 😊",
            "sad": "I'm here for you. It's okay to feel sad. Would you like to talk? 🤗",
            "angry": "I understand you're frustrated. Let's take a deep breath together. 🧘",
            "scared": "You're safe with me. Let's do something calming. 🛡️",
            "tired": "It's okay to rest. Let's do a quiet activity. 💤",
            "neutral": "I'm here to help you. What would you like to do today? 🌟"
        }
        return responses.get(emotion, responses["neutral"])
    
    def get_routine(self, time_of_day):
        return self.routines.get(time_of_day, self.routines["morning"])

# ========== Breathing Exercise ==========
class BreathingExercise:
    def __init__(self, speak_func):
        self.speak = speak_func
    
    def start(self):
        self.speak("Let's do a breathing exercise together. Breathe in...")
        time.sleep(4)
        self.speak("Hold...")
        time.sleep(4)
        self.speak("Breathe out...")
        time.sleep(4)
        self.speak("Great job! Let's do one more.")
        time.sleep(1)
        self.speak("Breathe in...")
        time.sleep(4)
        self.speak("Hold...")
        time.sleep(4)
        self.speak("Breathe out...")
        time.sleep(4)
        self.speak("Wonderful! You're doing great! 🧘")

# ========== Pepper Movements ==========
class PepperMovements:
    def __init__(self, pepper):
        self.pepper = pepper
        self.position = [0, 0, 0.8]
        self.angle = 0
    
    def move_forward(self, steps=1):
        step_distance = 0.3
        for _ in range(steps):
            self.position[0] += step_distance * math.cos(self.angle)
            self.position[1] += step_distance * math.sin(self.angle)
            try:
                self.pepper.setTranslation(self.position)
            except:
                pass
            time.sleep(0.3)
        return "🚶 Pepper walked forward!"
    
    def move_backward(self, steps=1):
        step_distance = 0.3
        for _ in range(steps):
            self.position[0] -= step_distance * math.cos(self.angle)
            self.position[1] -= step_distance * math.sin(self.angle)
            try:
                self.pepper.setTranslation(self.position)
            except:
                pass
            time.sleep(0.3)
        return "🚶 Pepper walked backward!"
    
    def turn_left(self, degrees=45):
        rad = math.radians(degrees)
        self.angle += rad
        try:
            self.pepper.setAngles("HeadYaw", self.angle, 0.2)
        except:
            pass
        time.sleep(0.5)
        return f"🔄 Pepper turned left {degrees} degrees!"
    
    def turn_right(self, degrees=45):
        rad = math.radians(degrees)
        self.angle -= rad
        try:
            self.pepper.setAngles("HeadYaw", self.angle, 0.2)
        except:
            pass
        time.sleep(0.5)
        return f"🔄 Pepper turned right {degrees} degrees!"
    
    def wave(self):
        for _ in range(3):
            try:
                self.pepper.setAngles("LShoulderPitch", 1.2, 0.2)
                self.pepper.setAngles("RShoulderPitch", 1.2, 0.2)
                time.sleep(0.2)
                self.pepper.setAngles("LShoulderPitch", 0, 0.2)
                self.pepper.setAngles("RShoulderPitch", 0, 0.2)
                time.sleep(0.2)
            except:
                pass
        return "👋 Pepper waved!"
    
    def raise_arms(self):
        try:
            self.pepper.setAngles("LShoulderPitch", 1.5, 0.2)
            self.pepper.setAngles("RShoulderPitch", 1.5, 0.2)
            time.sleep(0.5)
            self.pepper.setAngles("LShoulderPitch", 0, 0.2)
            self.pepper.setAngles("RShoulderPitch", 0, 0.2)
        except:
            pass
        return "🙌 Pepper raised arms! Great job!"
    
    def shake_hand(self):
        try:
            self.pepper.setAngles("RShoulderPitch", 0.5, 0.2)
            self.pepper.setAngles("RElbowYaw", -0.5, 0.2)
            time.sleep(0.5)
            for _ in range(2):
                self.pepper.setAngles("RElbowRoll", 0.3, 0.1)
                time.sleep(0.2)
                self.pepper.setAngles("RElbowRoll", -0.3, 0.1)
                time.sleep(0.2)
            self.pepper.setAngles("RShoulderPitch", 0, 0.2)
            self.pepper.setAngles("RElbowYaw", 0, 0.2)
        except:
            pass
        return "🤝 Pepper offered a handshake!"
    
    def hug(self):
        try:
            self.pepper.setAngles("LShoulderPitch", 0.3, 0.2)
            self.pepper.setAngles("RShoulderPitch", 0.3, 0.2)
            self.pepper.setAngles("LElbowYaw", 1.2, 0.2)
            self.pepper.setAngles("RElbowYaw", -1.2, 0.2)
            time.sleep(1.5)
            self.pepper.setAngles("LElbowYaw", 0.5, 0.2)
            self.pepper.setAngles("RElbowYaw", -0.5, 0.2)
            time.sleep(1)
            self.pepper.setAngles("LShoulderPitch", 0, 0.2)
            self.pepper.setAngles("RShoulderPitch", 0, 0.2)
            self.pepper.setAngles("LElbowYaw", 0, 0.2)
            self.pepper.setAngles("RElbowYaw", 0, 0.2)
        except:
            pass
        return "🤗 Pepper opened arms for a hug!"
    
    def dance(self):
        for _ in range(3):
            for angle in [0.5, 1.0, 0.5, 0]:
                try:
                    self.pepper.setAngles("LShoulderPitch", angle, 0.1)
                    self.pepper.setAngles("RShoulderPitch", angle, 0.1)
                    time.sleep(0.15)
                except:
                    pass
        return "💃 Pepper danced!"

# ========== PyBullet Pepper Robot (Original Balloon Chaser) ==========
class PepperBalloonRobot:
    def __init__(self):
        print("🤖 Starting Pepper in PyBullet...")
        self.sim_manager = SimulationManager()
        self.client = self.sim_manager.launchSimulation(gui=True)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.setRealTimeSimulation(1)
        p.setGravity(0, 0, -9.81)
        p.loadURDF("plane.urdf")
        
        # Spawn Pepper
        self.pepper = self.sim_manager.spawnPepper(self.client)
        self.pepper.goToPosture("Stand", 0.5)
        print("✅ Pepper loaded!")
        
        # Create colorful balloons
        colors = [[1,0,0,1], [0,1,0,1], [0,0,1,1], [1,1,0,1], [1,0.5,0,1], [1,0,1,1]]
        self.balloons = []
        for i in range(12):
            x = random.uniform(-3.5, 3.5)
            y = random.uniform(-2.8, 2.8)
            z = random.uniform(0.4, 1.5)
            vis = p.createVisualShape(p.GEOM_SPHERE, radius=0.12, rgbaColor=colors[i%6])
            ball = p.createMultiBody(baseMass=0, baseVisualShapeIndex=vis, basePosition=[x, y, z])
            self.balloons.append(ball)
        
        # Camera view
        p.resetDebugVisualizerCamera(cameraDistance=6.5, cameraYaw=45, cameraPitch=-30, cameraTargetPosition=[0, 0, 0.8])
        
        self.running = True
        self.t = 0
        self.movements = PepperMovements(self.pepper)
        
        # Start threads
        threading.Thread(target=self._walk, daemon=True).start()
        threading.Thread(target=self._update_balloons, daemon=True).start()
        threading.Thread(target=self._look_at_balloons, daemon=True).start()
    
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
    
    def _update_balloons(self):
        while self.running:
            for b in self.balloons:
                pos, _ = p.getBasePositionAndOrientation(b)
                new_z = pos[2] + 0.008
                if new_z > 1.7:
                    new_z = 0.3
                p.resetBasePositionAndOrientation(b, [pos[0], pos[1], new_z], [0,0,0,1])
            p.stepSimulation()
            time.sleep(1/60.)
    
    def _look_at_balloons(self):
        while self.running:
            try:
                # Find closest balloon
                pos = self.pepper.getPosition()
                closest = None
                min_dist = 999
                for b in self.balloons:
                    b_pos = p.getBasePositionAndOrientation(b)[0]
                    dist = math.sqrt((b_pos[0]-pos[0])**2 + (b_pos[1]-pos[1])**2)
                    if dist < min_dist:
                        min_dist = dist
                        closest = b_pos
                if closest:
                    dx = closest[0] - pos[0]
                    dy = closest[1] - pos[1]
                    target_yaw = math.atan2(dy, dx)
                    current_yaw = self.movements.angle
                    new_yaw = current_yaw * 0.95 + target_yaw * 0.05
                    self.movements.angle = new_yaw
                    self.pepper.setAngles("HeadYaw", new_yaw, 0.1)
            except:
                pass
            time.sleep(0.05)
    
    def execute_movement(self, command):
        movements = {
            "move_forward": self.movements.move_forward,
            "move_backward": self.movements.move_backward,
            "turn_left": self.movements.turn_left,
            "turn_right": self.movements.turn_right,
            "wave": self.movements.wave,
            "raise_arms": self.movements.raise_arms,
            "shake_hand": self.movements.shake_hand,
            "hug": self.movements.hug,
            "dance": self.movements.dance,
        }
        if command in movements:
            return movements[command]()
        return None
    
    def stop(self):
        self.running = False

# ========== Main System ==========
class PepperBalloonUltimate:
    def __init__(self):
        self.speaker = PepperSpeaker()
        self.microphone = PepperMicrophone()
        self.support = AutismSupport()
        self.breathing = BreathingExercise(self.speaker.speak)
        
        # Start PyBullet Pepper
        self.pepper_robot = PepperBalloonRobot()
        time.sleep(2)
        
        print("\n" + "="*55)
        print("🎈 PEPPER BALLOON CHASER - ULTIMATE")
        print("="*55)
        print("✅ Pepper in room with balloons (original working version)")
        print("✅ Voice input & output")
        print("✅ Movement commands (walk, turn, wave, hug, dance)")
        print("✅ Emotion recognition")
        print("✅ Autism support knowledge")
        print("✅ Breathing exercise")
        print("✅ Daily routine")
        print("✅ Games dashboard on localhost:5001")
        print("="*55 + "\n")
    
    def process_command(self, text):
        # Movement commands
        if text in ["walk", "move", "go", "move forward", "forward"]:
            result = self.pepper_robot.execute_movement("move_forward")
            self.speaker.speak(result)
            return True
        elif text in ["back", "move back", "backward"]:
            result = self.pepper_robot.execute_movement("move_backward")
            self.speaker.speak(result)
            return True
        elif text in ["left", "turn left"]:
            result = self.pepper_robot.execute_movement("turn_left")
            self.speaker.speak(result)
            return True
        elif text in ["right", "turn right"]:
            result = self.pepper_robot.execute_movement("turn_right")
            self.speaker.speak(result)
            return True
        elif text in ["wave", "hello", "hi"]:
            result = self.pepper_robot.execute_movement("wave")
            self.speaker.speak(result)
            return True
        elif text in ["celebrate", "good job", "raise arms"]:
            result = self.pepper_robot.execute_movement("raise_arms")
            self.speaker.speak(result)
            return True
        elif text in ["shake hand", "handshake"]:
            result = self.pepper_robot.execute_movement("shake_hand")
            self.speaker.speak(result)
            return True
        elif text in ["hug", "open arms"]:
            result = self.pepper_robot.execute_movement("hug")
            self.speaker.speak(result)
            return True
        elif text in ["dance"]:
            result = self.pepper_robot.execute_movement("dance")
            self.speaker.speak(result)
            return True
        
        # Breathing
        if "breathe" in text or "breathing" in text or "calm" in text:
            self.breathing.start()
            return True
        
        # Routine
        if "routine" in text or "schedule" in text:
            if "morning" in text:
                tasks = self.support.get_routine("morning")
                self.speaker.speak(f"Morning routine: {', '.join(tasks)}")
            elif "afternoon" in text:
                tasks = self.support.get_routine("afternoon")
                self.speaker.speak(f"Afternoon routine: {', '.join(tasks)}")
            elif "evening" in text:
                tasks = self.support.get_routine("evening")
                self.speaker.speak(f"Evening routine: {', '.join(tasks)}")
            else:
                self.speaker.speak("Say morning routine, afternoon routine, or evening routine")
            return True
        
        # Game
        if "game" in text or "games" in text or "play" in text:
            webbrowser.open(GAME_URL)
            self.speaker.speak("Opening your games dashboard on localhost 5001! Have fun!")
            return True
        
        # How-to video
        if "how to" in text:
            topic = text.replace("how to", "").strip()
            if topic:
                url = YOUTUBE_BASE + urllib.parse.quote(topic + " " + CARTOON_SUFFIX)
                webbrowser.open(url)
                self.speaker.speak(f"Opening a cartoon video about {topic} for you! Watch and learn!")
            return True
        
        return False
    
    def run(self):
        self.speaker.speak("Hello! I'm Pepper! I'm in my room with colorful balloons! I can walk, wave, hug, dance, and help you! Say walk, wave, hug, dance, or ask me questions!")
        
        while True:
            try:
                text = self.microphone.listen()
                if text is None:
                    continue
                
                if text in ["exit", "quit", "bye", "goodbye"]:
                    self.speaker.speak("Goodbye! It was wonderful talking with you! Come back soon!")
                    break
                
                if self.process_command(text):
                    continue
                
                # Emotion detection
                emotion = self.support.detect_emotion(text)
                if emotion != "neutral":
                    self.speaker.speak(self.support.get_emotion_response(emotion))
                    continue
                
                # Knowledge base
                answer = self.support.get_answer(text)
                if answer:
                    self.speaker.speak(answer)
                    continue
                
                # Default
                self.speaker.speak("I can walk, wave, hug, dance, or answer questions. What would you like?")
                
            except KeyboardInterrupt:
                self.speaker.speak("Goodbye!")
                break
        
        self.pepper_robot.stop()
        print("\n✅ System shutdown")

if __name__ == "__main__":
    system = PepperBalloonUltimate()
    system.run()
