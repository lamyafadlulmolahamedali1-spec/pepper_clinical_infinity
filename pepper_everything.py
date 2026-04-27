#!/usr/bin/env python3
"""
Pepper Everything - One Code to Rule Them All
- PyBullet with Pepper chasing balloons
- Camera with YOLO + Emotion Detection (Lamia)
- Chat terminal for typing
- Games on localhost:5001
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

# ========== YOLO + Emotion Detection with Camera ==========
class VisionDetector:
    def __init__(self):
        print("📷 Loading YOLO...")
        self.yolo = YOLO('yolov8n.pt')
        print("😊 Loading Emotion...")
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
                print("✅ Camera ready! Window opening...")
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
            
            # Resize for performance
            frame = cv2.resize(frame, (640, 480))
            
            # YOLO detection
            results = self.yolo(frame, verbose=False)
            self.person_detected = False
            
            for r in results:
                if r.boxes:
                    for box in r.boxes:
                        cls = int(box.cls[0])
                        if self.yolo.names[cls] == 'person':
                            x1, y1, x2, y2 = map(int, box.xyxy[0])
                            self.person_detected = True
                            
                            # Crop face for emotion
                            face = frame[y1:y2, x1:x2]
                            if face.size > 0 and face.shape[0] > 30:
                                try:
                                    result = DeepFace.analyze(face, actions=['emotion'], enforce_detection=False)
                                    self.current_emotion = result[0]['dominant_emotion']
                                except:
                                    pass
                            
                            # Draw green box
                            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 3)
                            cv2.putText(frame, PERSON_NAME, (x1, y1-35), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                            emoji = {'happy':'😊','sad':'😢','angry':'😠','surprise':'😲','neutral':'😐'}.get(self.current_emotion, '😐')
                            cv2.putText(frame, f'{self.current_emotion.upper()} {emoji}', (x1, y1-10), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Terminal output
            if self.person_detected:
                print(f"\r👤 {PERSON_NAME} | Emotion: {self.current_emotion.upper()}", end="")
            else:
                print(f"\r👀 No person detected", end="")
            
            cv2.imshow('Lamia - Emotion Detection', frame)
            cv2.resizeWindow('Lamia - Emotion Detection', 640, 480)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            time.sleep(0.03)
    
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
                {"role": "system", "content": "You are Pepper, a friendly robot. Respond in 1 short, fun sentence in ENGLISH. Be encouraging!"},
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

# ========== Balloon ==========
class Balloon:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.z = random.uniform(0.8, 2.2)
        self.speed = random.uniform(0.01, 0.04)
        self.color = color
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

# ========== Build Room ==========
def build_room():
    print("🏠 Building room...")
    p.setAdditionalSearchPath(pybullet_data.getDataPath())
    p.loadURDF("plane.urdf")
    # Simple floor rug
    rug = p.createVisualShape(p.GEOM_BOX, halfExtents=[4.5, 3.5, 0.02], rgbaColor=[0.5, 0.3, 0.2, 1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=rug, basePosition=[0, 0, 0.01])
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
        
        self.x, self.y = 0, 0
        self.auto_walk = True
        self.walk_timer = 0
        self.balloons = []
        
        colors = [[1,0.2,0.2,1], [0.2,1,0.2,1], [0.2,0.2,1,1], [1,1,0.2,1], [1,0.5,0.2,1]]
        for i in range(8):
            self.balloons.append(Balloon(random.uniform(-3,3), random.uniform(-2.2,2.2), colors[i%5]))
        
        self.head_yaw = 0
        self.is_talking = False
        self.arm_angle = 0
        self.arm_dir = 1
        self.current_balloon_idx = 0
        
        p.resetDebugVisualizerCamera(cameraDistance=6.5, cameraYaw=45, cameraPitch=-30, cameraTargetPosition=[0,0,1])
        
        threading.Thread(target=self.auto_walk_loop, daemon=True).start()
        threading.Thread(target=self.chase_balloons, daemon=True).start()
        threading.Thread(target=self.move_arms_loop, daemon=True).start()
        threading.Thread(target=self.run_simulation, daemon=True).start()
        
        self.show_text(f"Hello {PERSON_NAME}! Type 'game' for your games! 🎮")
        
        print("\n" + "="*55)
        print(f"🤖 PEPPER - {PERSON_NAME}'s Robot")
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
    
    def chase_balloons(self):
        while True:
            if self.balloons:
                # Find closest balloon
                closest = None
                min_dist = 999
                for b in self.balloons:
                    dist = math.sqrt((b.x - self.x)**2 + (b.y - self.y)**2)
                    if dist < min_dist:
                        min_dist = dist
                        closest = b
                if closest:
                    dx = closest.x - self.x
                    dy = closest.y - self.y
                    target_yaw = math.atan2(dy, dx)
                    self.head_yaw = self.head_yaw * 0.92 + target_yaw * 0.08
                    try:
                        self.pepper.setAngles("HeadYaw", self.head_yaw, 0.1)
                    except:
                        pass
            time.sleep(0.04)
    
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
            p.addUserDebugText(text[:55], [pos[0], pos[1], pos[2] + 1.2], [0,0,0], textSize=1, lifeTime=3)
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
        return f"🖼️ Picture of {topic}! 📸"
    
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
        if c in ["game","games","play","لعبة"]:
            return self.open_game()
        elif c.startswith("how to"):
            return self.open_video(c.replace("how to","").strip())
        elif c.startswith("picture") or c.startswith("image") or c.startswith("صورة"):
            return self.open_picture(c.replace("picture","").replace("image","").replace("صورة","").strip())
        elif c in ["dance","رقص"]:
            self.dance()
            return "Let's dance! 💃"
        elif c in ["wave","hello","hi"]:
            self.wave()
            return f"Hello {PERSON_NAME}! 👋"
        elif c in ["stop"]:
            self.auto_walk = False
            return "Stopping! 🧍"
        elif c in ["go","walk"]:
            self.auto_walk = True
            return "Walking! 🚶"
        return None
    
    def run(self):
        while True:
            try:
                user = input("\n👶 You: ").strip()
                if user.lower() in ['exit','quit','bye','خروج']:
                    self.show_text(f"Goodbye {PERSON_NAME}! 👋")
                    self.vision.stop()
                    break
                if not user:
                    continue
                
                result = self.process_command(user)
                if result:
                    self.show_text(result)
                else:
                    self.show_text("🤔")
                    time.sleep(0.3)
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
