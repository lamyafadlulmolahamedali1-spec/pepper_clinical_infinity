#!/usr/bin/env python3
"""
Pepper with Small Camera Window + Games on localhost:5001
"""

import os
import sys
import time
import threading
import random
import math
import webbrowser
import urllib.parse
import cv2
import numpy as np
from qibullet import SimulationManager
import pybullet as p
import pybullet_data
import requests
from ultralytics import YOLO
from deepface import DeepFace

# ========== Settings ==========
GAME_URL = "http://localhost:5001"
CHAT_API = "https://text.pollinations.ai/v1/chat/completions"
IMAGE_API = "https://image.pollinations.ai/prompt/"
YOUTUBE_BASE = "https://www.youtube.com/results?search_query="
CARTOON_SUFFIX = "cartoon for kids educational"
PERSON_NAME = "Lamia"

# ========== YOLO + Emotion Detection with SMALL Camera Window ==========
class VisionDetector:
    def __init__(self):
        print("📷 Loading YOLO model...")
        self.yolo = YOLO('yolov8n.pt')
        print("😊 Loading emotion detection...")
        self.current_emotion = "neutral"
        self.person_detected = False
        self.running = True
        self.start_camera()
    
    def start_camera(self):
        try:
            self.camera = cv2.VideoCapture(1)
            if not self.camera.isOpened():
                self.camera = cv2.VideoCapture(0)
            if self.camera.isOpened():
                print("✅ Camera working! Small window opening...")
                threading.Thread(target=self.detect_loop, daemon=True).start()
            else:
                print("❌ No camera found!")
                self.camera = None
        except Exception as e:
            print(f"⚠️ Camera error: {e}")
            self.camera = None
    
    def detect_loop(self):
        while self.running and self.camera:
            ret, frame = self.camera.read()
            if not ret:
                continue
            
            # Make frame SMALLER (320x240 instead of 640x480)
            frame = cv2.resize(frame, (320, 240))
            
            # YOLO detection
            results = self.yolo(frame)
            
            self.person_detected = False
            
            for r in results:
                boxes = r.boxes
                if boxes is not None:
                    for box in boxes:
                        cls = int(box.cls[0])
                        if self.yolo.names[cls] == 'person':
                            x1, y1, x2, y2 = map(int, box.xyxy[0])
                            self.person_detected = True
                            
                            # Crop face for emotion detection
                            face = frame[y1:y2, x1:x2]
                            if face.size > 0 and face.shape[0] > 20 and face.shape[1] > 20:
                                try:
                                    result = DeepFace.analyze(face, actions=['emotion'], enforce_detection=False)
                                    self.current_emotion = result[0]['dominant_emotion']
                                except:
                                    pass
                            
                            # Draw GREEN bounding box (smaller)
                            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                            
                            # Write text smaller
                            cv2.putText(frame, f"Lamia", (x1, y1 - 25), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                            cv2.putText(frame, f"{self.current_emotion.upper()}", (x1, y1 - 8), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
            
            # Print to terminal
            if self.person_detected:
                print(f"\r👤 {PERSON_NAME} | Emotion: {self.current_emotion.upper()}", end="")
            else:
                print(f"\r👀 No person", end="")
            
            # Show SMALL camera window (320x240)
            cv2.imshow('Pepper Vision (small)', frame)
            cv2.resizeWindow('Pepper Vision (small)', 320, 240)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            
            time.sleep(0.05)
    
    def get_current_emotion(self):
        return self.current_emotion if self.person_detected else "none"
    
    def stop(self):
        self.running = False
        if self.camera:
            self.camera.release()
        cv2.destroyAllWindows()

# ========== AI Chat ==========
class PepperAI:
    def __init__(self):
        self.last_request_time = 0
    
    def chat(self, message):
        time_since_last = time.time() - self.last_request_time
        if time_since_last < 1.5:
            time.sleep(1.5 - time_since_last)
        data = {
            "model": "openai",
            "messages": [
                {"role": "system", "content": "You are Pepper, a friendly robot. Respond in 1 short, fun sentence in ENGLISH."},
                {"role": "user", "content": message}
            ]
        }
        try:
            response = requests.post(CHAT_API, json=data, timeout=10)
            self.last_request_time = time.time()
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
        except:
            pass
        return "That's awesome! Tell me more! 😊"

# ========== Balloon Class ==========
class Balloon:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.z = random.uniform(0.8, 2.2)
        self.speed = random.uniform(0.01, 0.04)
        self.color = color
        self.body_id = None
        self.create()
    
    def create(self):
        visual = p.createVisualShape(p.GEOM_SPHERE, radius=0.15, rgbaColor=self.color)
        self.body_id = p.createMultiBody(baseMass=0, baseVisualShapeIndex=visual,
                                          basePosition=[self.x, self.y, self.z])
    
    def update(self):
        self.z += self.speed
        if self.z > 2.8:
            self.z = 0.6
            self.x = random.uniform(-3.2, 3.2)
            self.y = random.uniform(-2.5, 2.5)
        p.resetBasePositionAndOrientation(self.body_id, [self.x, self.y, self.z], [0, 0, 0, 1])

# ========== Create Kids ==========
def create_kid(name, color, pos):
    body = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.2, 0.15, 0.4], rgbaColor=color)
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=body, basePosition=[pos[0], pos[1], pos[2] + 0.2])
    head = p.createVisualShape(p.GEOM_SPHERE, radius=0.15, rgbaColor=[1, 0.85, 0.7, 1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=head, basePosition=[pos[0], pos[1], pos[2] + 0.55])
    p.addUserDebugText(name, [pos[0], pos[1], pos[2] + 0.85], [0, 0, 0], textSize=0.8, lifeTime=0)

# ========== Build Room ==========
def build_room():
    print("🏠 Building room...")
    p.setAdditionalSearchPath(pybullet_data.getDataPath())
    p.loadURDF("plane.urdf")
    
    kids = [
        ("Ahmed", [1.5, -1.2, 0], [1, 0.6, 0.4, 1]),
        ("Sara", [-1.2, 1.3, 0], [1, 0.7, 0.8, 1]),
        ("Yusuf", [0.5, -2, 0], [0.4, 0.7, 1, 1]),
    ]
    for name, pos, color in kids:
        create_kid(name, color, pos)
    print("✅ Room ready!")

# ========== Pepper Robot ==========
class PepperRobot:
    def __init__(self):
        self.ai = PepperAI()
        self.vision = VisionDetector()
        self.sim_manager = SimulationManager()
        self.client = self.sim_manager.launchSimulation(gui=True)
        p.setRealTimeSimulation(1)
        p.setGravity(0, 0, -9.81)
        
        build_room()
        
        print("🤖 Spawning Pepper...")
        self.pepper = self.sim_manager.spawnPepper(self.client)
        self.pepper.goToPosture("Stand", 0.5)
        
        self.x, self.y, self.angle = 0, 0, 0
        self.auto_walk = True
        self.walk_timer = 0
        self.balloons = []
        
        colors = [[1, 0.2, 0.2, 1], [0.2, 1, 0.2, 1], [0.2, 0.2, 1, 1], [1, 1, 0.2, 1]]
        for i in range(8):
            self.balloons.append(Balloon(random.uniform(-3, 3), random.uniform(-2.2, 2.2), colors[i % len(colors)]))
        
        self.head_yaw = 0
        self.is_talking = False
        self.arm_angle = 0
        self.arm_dir = 1
        
        p.resetDebugVisualizerCamera(cameraDistance=6.5, cameraYaw=45, cameraPitch=-30, cameraTargetPosition=[0, 0, 1])
        
        threading.Thread(target=self.auto_walk_loop, daemon=True).start()
        threading.Thread(target=self.move_arms_loop, daemon=True).start()
        threading.Thread(target=self.run_simulation, daemon=True).start()
        
        self.show_text(f"Hello {PERSON_NAME}! Type 'game' for your games at localhost:5001! 🎮")
        
        print("\n" + "="*55)
        print("🤖 PEPPER - Small Camera | Games on localhost:5001")
        print("="*55)
        print("📝 Commands:")
        print("   game - Opens your games at localhost:5001")
        print("   how to [topic] - Opens cartoon video")
        print("   picture [topic] - Opens image")
        print("   dance / wave - Pepper dances/waves")
        print("   exit - Quit")
        print("="*55)
    
    def auto_walk_loop(self):
        while True:
            if self.auto_walk:
                self.walk_timer += 0.02
                self.x += 0.04 * math.cos(self.walk_timer * 0.5)
                self.y += 0.04 * math.sin(self.walk_timer * 0.7)
                self.x = max(-3.2, min(3.2, self.x))
                self.y = max(-2.5, min(2.5, self.y))
                try:
                    self.pepper.setPosition([self.x, self.y, 0.8])
                except:
                    pass
            time.sleep(0.08)
    
    def move_arms_loop(self):
        while True:
            if self.is_talking:
                self.arm_angle += 0.07 * self.arm_dir
                if self.arm_angle > 0.6:
                    self.arm_angle = 0.6
                    self.arm_dir = -1
                elif self.arm_angle < 0:
                    self.arm_angle = 0
                    self.arm_dir = 1
                try:
                    self.pepper.setAngles("LShoulderPitch", self.arm_angle, 0.1)
                    self.pepper.setAngles("RShoulderPitch", self.arm_angle, 0.1)
                except:
                    pass
            else:
                if self.arm_angle > 0:
                    self.arm_angle -= 0.04
                    try:
                        self.pepper.setAngles("LShoulderPitch", self.arm_angle, 0.1)
                        self.pepper.setAngles("RShoulderPitch", self.arm_angle, 0.1)
                    except:
                        pass
            time.sleep(0.05)
    
    def run_simulation(self):
        while True:
            p.stepSimulation()
            for b in self.balloons:
                b.update()
            time.sleep(1/240.)
    
    def show_text(self, text):
        try:
            pos = p.getBasePositionAndOrientation(self.pepper.body)[0]
            p.addUserDebugText(text[:55], [pos[0], pos[1], pos[2] + 1.2], [0, 0, 0], textSize=1, lifeTime=3)
        except:
            pass
        print(f"\n🤖 Pepper: {text}")
    
    def open_game(self):
        webbrowser.open(GAME_URL)
        return f"🎮 Opening your games at localhost:5001, {PERSON_NAME}! 🎲"
    
    def open_video(self, topic):
        search = f"{topic} {CARTOON_SUFFIX}"
        url = f"{YOUTUBE_BASE}{urllib.parse.quote(search)}"
        webbrowser.open(url)
        return f"📺 Opening cartoon video about {topic}! 🌟"
    
    def open_picture(self, topic):
        clean = topic.replace(" ", "%20")
        url = f"{IMAGE_API}{clean}"
        webbrowser.open(url)
        return f"🖼️ Opening picture of {topic}! 📸"
    
    def dance(self):
        self.is_talking = True
        for _ in range(3):
            self.pepper.setAngles("LShoulderPitch", 1.0, 0.15)
            self.pepper.setAngles("RShoulderPitch", 1.0, 0.15)
            time.sleep(0.15)
            self.pepper.setAngles("LShoulderPitch", 0.2, 0.15)
            self.pepper.setAngles("RShoulderPitch", 0.2, 0.15)
            time.sleep(0.15)
        self.is_talking = False
    
    def wave(self):
        self.is_talking = True
        for _ in range(2):
            self.pepper.setAngles("LShoulderPitch", 1.2, 0.2)
            self.pepper.setAngles("RShoulderPitch", 1.2, 0.2)
            time.sleep(0.2)
            self.pepper.setAngles("LShoulderPitch", 0, 0.2)
            self.pepper.setAngles("RShoulderPitch", 0, 0.2)
            time.sleep(0.2)
        self.is_talking = False
    
    def process_command(self, cmd):
        c = cmd.lower().strip()
        
        if c in ["game", "games", "play", "لعبة"]:
            return self.open_game()
        elif c.startswith("how to"):
            topic = c.replace("how to", "").strip()
            return self.open_video(topic)
        elif c.startswith("picture") or c.startswith("image") or c.startswith("صورة"):
            topic = c.replace("picture", "").replace("image", "").replace("صورة", "").strip()
            return self.open_picture(topic)
        elif c in ["dance", "رقص"]:
            self.dance()
            return "Let's dance! 💃"
        elif c in ["wave", "hello", "hi"]:
            self.wave()
            return f"Hello {PERSON_NAME}! 👋"
        elif c in ["stop"]:
            self.auto_walk = False
            return "Stopping here! 🧍"
        elif c in ["go", "walk"]:
            self.auto_walk = True
            return "Walking again! 🚶‍♂️"
        return None
    
    def run(self):
        while True:
            try:
                user = input("\n👶 You: ").strip()
                if user.lower() in ['exit', 'quit', 'bye', 'خروج']:
                    self.show_text(f"Goodbye {PERSON_NAME}! 👋")
                    self.vision.stop()
                    break
                if not user:
                    continue
                
                result = self.process_command(user)
                if result:
                    self.show_text(result)
                else:
                    response = self.ai.chat(user)
                    self.show_text(response)
                    
            except KeyboardInterrupt:
                print("\n")
                self.show_text("Goodbye! 👋")
                self.vision.stop()
                break

if __name__ == "__main__":
    pepper = PepperRobot()
    pepper.run()
