#!/usr/bin/env python3
"""
Pepper Full Interactive - Final Version
- Pepper walks automatically around the room
- Balloons floating in the room
- Pepper follows balloons with his head
- Connected to ASD games with scoring
- Claps when child answers correctly
"""

import os
import sys
import time
import threading
import random
import math
import webbrowser
import subprocess
import json
import requests
import urllib.parse
from datetime import datetime
from qibullet import SimulationManager
import pybullet as p
import pybullet_data

# ========== Paths ==========
GAMES_PATH = os.path.expanduser("~/Desktop/ASD_Final_Working")
DASHBOARD_FILE = os.path.join(GAMES_PATH, "pepper_data.json")
CHAT_API = "https://text.pollinations.ai/v1/chat/completions"
YOUTUBE_BASE = "https://www.youtube.com/results?search_query="
CARTOON_SUFFIX = "cartoon for kids educational"

# ========== Data Storage ==========
class Dashboard:
    def __init__(self):
        self.data = {"score": 0, "interactions": [], "games_played": []}
        self.load()
    
    def load(self):
        if os.path.exists(DASHBOARD_FILE):
            try:
                with open(DASHBOARD_FILE, 'r') as f:
                    self.data = json.load(f)
            except:
                pass
    
    def save(self):
        with open(DASHBOARD_FILE, 'w') as f:
            json.dump(self.data, f, indent=2)
    
    def add_score(self, points=10):
        self.data["score"] += points
        self.save()
        return f"🎉 +{points} points! Total: {self.data['score']} 🎉"
    
    def log_interaction(self, user, pepper):
        self.data["interactions"].append({
            "time": datetime.now().isoformat(),
            "user": user,
            "pepper": pepper
        })
        self.save()

# ========== Balloon Class ==========
class Balloon:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.z = random.uniform(0.5, 2.5)
        self.speed = random.uniform(0.02, 0.06)
        self.color = color
        self.body_id = None
        self.create()
    
    def create(self):
        # Balloon body (sphere)
        visual = p.createVisualShape(p.GEOM_SPHERE, radius=0.12, rgbaColor=self.color)
        self.body_id = p.createMultiBody(baseMass=0, baseVisualShapeIndex=visual,
                                          basePosition=[self.x, self.y, self.z])
        # String (small cylinder)
        string = p.createVisualShape(p.GEOM_CYLINDER, radius=0.01, length=0.2, rgbaColor=[0.5, 0.5, 0.5, 1])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=string,
                          basePosition=[self.x, self.y, self.z - 0.15])
    
    def update(self):
        self.z += self.speed
        if self.z > 3.0:
            self.z = 0.3
            self.x = random.uniform(-3, 3)
            self.y = random.uniform(-2.5, 2.5)
        p.resetBasePositionAndOrientation(self.body_id, [self.x, self.y, self.z], [0, 0, 0, 1])

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

# ========== Create Kids ==========
def create_kid(name, color, pos):
    body = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.2, 0.15, 0.4], rgbaColor=color)
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=body, basePosition=[pos[0], pos[1], pos[2] + 0.2])
    head = p.createVisualShape(p.GEOM_SPHERE, radius=0.15, rgbaColor=[1, 0.85, 0.7, 1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=head, basePosition=[pos[0], pos[1], pos[2] + 0.55])
    eye = p.createVisualShape(p.GEOM_SPHERE, radius=0.04, rgbaColor=[0, 0, 0, 1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=eye, basePosition=[pos[0] - 0.07, pos[1] + 0.08, pos[2] + 0.62])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=eye, basePosition=[pos[0] + 0.07, pos[1] + 0.08, pos[2] + 0.62])
    p.addUserDebugText(name, [pos[0], pos[1], pos[2] + 0.85], [0, 0, 0], textSize=0.8, lifeTime=0)

# ========== Build Room ==========
def build_room():
    print("🏠 Building room...")
    p.setAdditionalSearchPath(pybullet_data.getDataPath())
    p.loadURDF("plane.urdf")
    rug = p.createVisualShape(p.GEOM_BOX, halfExtents=[4.5, 3.5, 0.02], rgbaColor=[0.5, 0.3, 0.2, 1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=rug, basePosition=[0, 0, 0.01])
    
    wall_color = [0.85, 0.85, 0.9, 1]
    wall = p.createVisualShape(p.GEOM_BOX, halfExtents=[5, 0.1, 2.2], rgbaColor=wall_color)
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=wall, basePosition=[0, -4, 1.1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=wall, basePosition=[0, 4, 1.1])
    wall_side = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.1, 4, 2.2], rgbaColor=wall_color)
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=wall_side, basePosition=[5, 0, 1.1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=wall_side, basePosition=[-5, 0, 1.1])
    
    table = p.createVisualShape(p.GEOM_BOX, halfExtents=[1, 0.8, 0.4], rgbaColor=[0.6, 0.4, 0.2, 1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=table, basePosition=[2, 1.5, 0.4])
    chair = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.4, 0.4, 0.3], rgbaColor=[0.5, 0.3, 0.1, 1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=chair, basePosition=[1.5, 1.8, 0.15])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=chair, basePosition=[2.5, 1.8, 0.15])
    
    kids = [
        ("Ahmed", [1.5, -1.2, 0], [1, 0.6, 0.4, 1]),
        ("Sara", [-1.2, 1.3, 0], [1, 0.7, 0.8, 1]),
        ("Yusuf", [0.5, -2, 0], [0.4, 0.7, 1, 1]),
        ("Layla", [2.8, -0.2, 0], [1, 0.5, 0.9, 1]),
        ("Omar", [-2.2, -1, 0], [0.4, 0.8, 0.4, 1]),
    ]
    for name, pos, color in kids:
        create_kid(name, color, pos)
    print("✅ Room ready!")

# ========== Pepper Robot ==========
class PepperRobot:
    def __init__(self):
        self.ai = PepperAI()
        self.dashboard = Dashboard()
        self.sim_manager = SimulationManager()
        self.client = self.sim_manager.launchSimulation(gui=True)
        p.setRealTimeSimulation(1)
        p.setGravity(0, 0, -9.81)
        
        build_room()
        
        print("🤖 Spawning Pepper...")
        self.pepper = self.sim_manager.spawnPepper(self.client)
        self.pepper.goToPosture("Stand", 0.5)
        
        # Movement
        self.x, self.y, self.angle = 0, 0, 0
        self.walk_angle = 0
        self.auto_walk = True
        
        # Arms
        self.is_talking = False
        self.arm_angle = 0
        self.arm_dir = 1
        
        # Balloons
        self.balloons = []
        self.create_balloons()
        
        # Head tracking
        self.current_balloon = None
        self.head_yaw = 0
        
        p.resetDebugVisualizerCamera(cameraDistance=7, cameraYaw=45, cameraPitch=-30, cameraTargetPosition=[0, 0, 1])
        
        self.show_text("Hello! I'm Pepper! I love walking around and watching balloons! 🎈")
        self.clap()
        
        # Start auto-walk thread
        threading.Thread(target=self.auto_walk_loop, daemon=True).start()
        threading.Thread(target=self.track_balloons, daemon=True).start()
        threading.Thread(target=self.move_arms_loop, daemon=True).start()
        threading.Thread(target=self.run_simulation, daemon=True).start()
    
    def create_balloons(self):
        colors = [[1, 0.2, 0.2, 1], [0.2, 1, 0.2, 1], [0.2, 0.2, 1, 1], [1, 1, 0.2, 1], [1, 0.5, 0.2, 1]]
        for i in range(8):
            self.balloons.append(Balloon(random.uniform(-2.5, 2.5), random.uniform(-2, 2), colors[i % len(colors)]))
        print("🎈 Created 8 floating balloons!")
    
    def auto_walk_loop(self):
        while True:
            if self.auto_walk:
                self.walk_angle += 0.02
                self.x += 0.03 * math.cos(self.walk_angle)
                self.y += 0.03 * math.sin(self.walk_angle)
                # Boundaries
                self.x = max(-3.2, min(3.2, self.x))
                self.y = max(-2.5, min(2.5, self.y))
                try:
                    self.pepper.setPosition([self.x, self.y, 0.8])
                except:
                    pass
            time.sleep(0.1)
    
    def track_balloons(self):
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
                    # Calculate angle to balloon
                    dx = closest.x - self.x
                    dy = closest.y - self.y
                    target_yaw = math.atan2(dy, dx)
                    # Smooth head movement
                    self.head_yaw = self.head_yaw * 0.9 + target_yaw * 0.1
                    try:
                        self.pepper.setAngles("HeadYaw", self.head_yaw, 0.1)
                    except:
                        pass
            time.sleep(0.05)
    
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
                    self.arm_angle -= 0.05
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
    
    def clap(self):
        """Clap hands for correct answer"""
        self.is_talking = True
        for _ in range(2):
            self.pepper.setAngles("LShoulderPitch", 1.0, 0.15)
            self.pepper.setAngles("RShoulderPitch", 1.0, 0.15)
            time.sleep(0.1)
            self.pepper.setAngles("LShoulderPitch", 0.2, 0.15)
            self.pepper.setAngles("RShoulderPitch", 0.2, 0.15)
            time.sleep(0.1)
        self.is_talking = False
    
    def show_text(self, text):
        try:
            pos = p.getBasePositionAndOrientation(self.pepper.body)[0]
            p.addUserDebugText(text[:50], [pos[0], pos[1], pos[2] + 1.2], [0, 0, 0], textSize=1, lifeTime=3)
        except:
            pass
        print(f"🤖 Pepper: {text}")
    
    def open_games(self):
        if os.path.exists(GAMES_PATH):
            subprocess.Popen(['nautilus', GAMES_PATH])
            return "🎮 Opening your ASD games! Play and have fun! 🎲"
        return "🎮 Games folder not found!"
    
    def correct_answer(self):
        """When child answers correctly"""
        points_msg = self.dashboard.add_score(10)
        self.clap()
        return f"{points_msg} You're so smart! 🌟"
    
    def process_command(self, cmd):
        cmd = cmd.lower().strip()
        
        if cmd in ["walk", "move", "go"]:
            self.auto_walk = True
            return "I'm walking around! 🚶‍♂️"
        elif cmd in ["stop", "stay"]:
            self.auto_walk = False
            return "Okay, I'll stop here! 🧍"
        elif cmd in ["dance"]:
            self.is_talking = True
            for _ in range(3):
                self.pepper.setAngles("LShoulderPitch", 1.0, 0.15)
                self.pepper.setAngles("RShoulderPitch", 1.0, 0.15)
                time.sleep(0.15)
                self.pepper.setAngles("LShoulderPitch", 0.3, 0.15)
                self.pepper.setAngles("RShoulderPitch", 0.3, 0.15)
                time.sleep(0.15)
            self.is_talking = False
            return "Let's dance! 💃"
        elif cmd in ["wave", "hello"]:
            for _ in range(2):
                self.pepper.setAngles("LShoulderPitch", 1.2, 0.2)
                self.pepper.setAngles("RShoulderPitch", 1.2, 0.2)
                time.sleep(0.2)
                self.pepper.setAngles("LShoulderPitch", 0, 0.2)
                self.pepper.setAngles("RShoulderPitch", 0, 0.2)
                time.sleep(0.2)
            return "Hello! 👋"
        elif cmd in ["game", "games", "play"]:
            return self.open_games()
        elif cmd in ["correct", "right", "good answer"]:
            return self.correct_answer()
        elif "how to" in cmd:
            topic = cmd.replace("how to", "").strip()
            search = f"{topic} {CARTOON_SUFFIX}"
            url = f"{YOUTUBE_BASE}{urllib.parse.quote(search)}"
            webbrowser.open(url)
            return f"📺 Opening cartoon video about {topic}! 🌟"
        return None
    
    def run(self):
        while True:
            try:
                user = input("\n👶 You: ").strip()
                if user.lower() in ['exit', 'quit', 'bye']:
                    self.show_text("Goodbye! See you soon! 👋")
                    break
                if not user:
                    continue
                
                result = self.process_command(user)
                if result:
                    self.show_text(result)
                    self.dashboard.log_interaction(user, result)
                else:
                    self.show_text("Let me think... 🤔")
                    time.sleep(0.5)
                    response = self.ai.chat(user)
                    self.show_text(response)
                    self.dashboard.log_interaction(user, response)
                    
            except KeyboardInterrupt:
                print("\n")
                self.show_text("Goodbye! 👋")
                break

if __name__ == "__main__":
    pepper = PepperRobot()
    pepper.run()
