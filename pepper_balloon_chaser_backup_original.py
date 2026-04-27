#!/usr/bin/env python3
"""
Pepper Balloon Chaser
- Pepper walks around chasing balloons
- Follows balloons with head and arms
- Text appears above head in BLACK
- Opens games at localhost:5000
- Opens cartoon videos and images
"""

import os
import sys
import time
import threading
import random
import math
import webbrowser
import urllib.parse
from qibullet import SimulationManager
import pybullet as p
import pybullet_data
import requests

# ========== Settings ==========
GAME_URL = "http://localhost:5000"
CHAT_API = "https://text.pollinations.ai/v1/chat/completions"
IMAGE_API = "https://image.pollinations.ai/prompt/"
YOUTUBE_BASE = "https://www.youtube.com/results?search_query="
CARTOON_SUFFIX = "cartoon for kids educational"

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
        # Balloon body
        visual = p.createVisualShape(p.GEOM_SPHERE, radius=0.15, rgbaColor=self.color)
        self.body_id = p.createMultiBody(baseMass=0, baseVisualShapeIndex=visual,
                                          basePosition=[self.x, self.y, self.z])
        # String
        string = p.createVisualShape(p.GEOM_CYLINDER, radius=0.008, length=0.25, rgbaColor=[0.4, 0.4, 0.4, 1])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=string,
                          basePosition=[self.x, self.y, self.z - 0.18])
    
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
    eye = p.createVisualShape(p.GEOM_SPHERE, radius=0.04, rgbaColor=[0, 0, 0, 1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=eye, basePosition=[pos[0] - 0.07, pos[1] + 0.08, pos[2] + 0.62])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=eye, basePosition=[pos[0] + 0.07, pos[1] + 0.08, pos[2] + 0.62])
    p.addUserDebugText(name, [pos[0], pos[1], pos[2] + 0.85], [0, 0, 0], textSize=0.8, lifeTime=0)

# ========== Build Room ==========
def build_room():
    print("🏠 Building room...")
    p.setAdditionalSearchPath(pybullet_data.getDataPath())
    p.loadURDF("plane.urdf")
    
    # Rug
    rug = p.createVisualShape(p.GEOM_BOX, halfExtents=[4.5, 3.5, 0.02], rgbaColor=[0.5, 0.3, 0.2, 1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=rug, basePosition=[0, 0, 0.01])
    
    # Walls
    wall_color = [0.85, 0.85, 0.9, 1]
    wall = p.createVisualShape(p.GEOM_BOX, halfExtents=[5, 0.1, 2.2], rgbaColor=wall_color)
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=wall, basePosition=[0, -4, 1.1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=wall, basePosition=[0, 4, 1.1])
    wall_side = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.1, 4, 2.2], rgbaColor=wall_color)
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=wall_side, basePosition=[5, 0, 1.1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=wall_side, basePosition=[-5, 0, 1.1])
    
    # Table & chairs
    table = p.createVisualShape(p.GEOM_BOX, halfExtents=[1, 0.8, 0.4], rgbaColor=[0.6, 0.4, 0.2, 1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=table, basePosition=[2, 1.5, 0.4])
    chair = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.4, 0.4, 0.3], rgbaColor=[0.5, 0.3, 0.1, 1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=chair, basePosition=[1.5, 1.8, 0.15])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=chair, basePosition=[2.5, 1.8, 0.15])
    
    # Kids
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
        self.sim_manager = SimulationManager()
        self.client = self.sim_manager.launchSimulation(gui=True)
        p.setRealTimeSimulation(1)
        p.setGravity(0, 0, -9.81)
        
        build_room()
        
        print("🤖 Spawning Pepper...")
        self.pepper = self.sim_manager.spawnPepper(self.client)
        self.pepper.goToPosture("Stand", 0.5)
        
        # Position
        self.x, self.y, self.angle = 0, 0, 0
        self.auto_walk = True
        self.walk_timer = 0
        
        # Balloons
        self.balloons = []
        self.create_balloons()
        
        # Tracking
        self.target_balloon = None
        self.head_yaw = 0
        self.head_pitch = 0
        self.reach_arm = False
        
        # Arms
        self.is_talking = False
        self.arm_angle = 0
        self.arm_dir = 1
        
        # Camera
        p.resetDebugVisualizerCamera(cameraDistance=6.5, cameraYaw=45, cameraPitch=-30, cameraTargetPosition=[0, 0, 1])
        
        # Start threads
        threading.Thread(target=self.auto_walk_loop, daemon=True).start()
        threading.Thread(target=self.chase_balloons, daemon=True).start()
        threading.Thread(target=self.move_arms_loop, daemon=True).start()
        threading.Thread(target=self.run_simulation, daemon=True).start()
        
        self.show_text("Hello! I'm Pepper! I love chasing balloons! 🎈")
        
        print("\n" + "="*55)
        print("🤖 PEPPER - Balloon Chaser")
        print("="*55)
        print("🎈 Pepper walks around chasing balloons!")
        print("📝 Commands in TERMINAL:")
        print("   game - Opens ASD games at localhost:5000")
        print("   how to [topic] - Opens cartoon video")
        print("   picture [topic] - Opens image")
        print("   dance / wave - Pepper dances/waves")
        print("   stop / go - Stop/start walking")
        print("="*55)
    
    def create_balloons(self):
        colors = [[1, 0.2, 0.2, 1], [0.2, 1, 0.2, 1], [0.2, 0.2, 1, 1], 
                  [1, 1, 0.2, 1], [1, 0.5, 0.2, 1], [0.8, 0.2, 0.8, 1]]
        for i in range(10):
            self.balloons.append(Balloon(random.uniform(-3, 3), random.uniform(-2.2, 2.2), colors[i % len(colors)]))
        print("🎈 Created 10 floating balloons!")
    
    def auto_walk_loop(self):
        while True:
            if self.auto_walk:
                self.walk_timer += 0.02
                # Walk in a gentle circle
                self.x += 0.04 * math.cos(self.walk_timer * 0.5)
                self.y += 0.04 * math.sin(self.walk_timer * 0.7)
                # Boundaries
                self.x = max(-3.2, min(3.2, self.x))
                self.y = max(-2.5, min(2.5, self.y))
                try:
                    self.pepper.setPosition([self.x, self.y, 0.8])
                except:
                    pass
            time.sleep(0.08)
    
    def chase_balloons(self):
        while True:
            # Find closest balloon
            closest = None
            min_dist = 999
            for b in self.balloons:
                dist = math.sqrt((b.x - self.x)**2 + (b.y - self.y)**2)
                if dist < min_dist:
                    min_dist = dist
                    closest = b
                    self.target_balloon = b
            
            if closest:
                # Calculate angle to balloon
                dx = closest.x - self.x
                dy = closest.y - self.y
                target_yaw = math.atan2(dy, dx)
                # Smooth head movement
                self.head_yaw = self.head_yaw * 0.92 + target_yaw * 0.08
                # Head pitch based on balloon height
                dz = closest.z - 0.8
                target_pitch = math.atan2(dz, math.sqrt(dx*dx + dy*dy)) * 0.8
                self.head_pitch = self.head_pitch * 0.92 + target_pitch * 0.08
                
                try:
                    self.pepper.setAngles("HeadYaw", self.head_yaw, 0.1)
                    self.pepper.setAngles("HeadPitch", self.head_pitch, 0.1)
                except:
                    pass
                
                # Reach arms toward balloon if close
                if min_dist < 0.8:
                    self.reach_arm = True
                else:
                    self.reach_arm = False
            
            time.sleep(0.04)
    
    def move_arms_loop(self):
        while True:
            if self.reach_arm:
                # Reaching toward balloon
                target = 0.9
                if self.arm_angle < target:
                    self.arm_angle += 0.03
                try:
                    self.pepper.setAngles("LShoulderPitch", self.arm_angle, 0.1)
                    self.pepper.setAngles("RShoulderPitch", self.arm_angle, 0.1)
                except:
                    pass
            elif self.is_talking:
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
                    if self.arm_angle < 0:
                        self.arm_angle = 0
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
        """Show BLACK text above Pepper's head"""
        try:
            pos = p.getBasePositionAndOrientation(self.pepper.body)[0]
            p.addUserDebugText(text[:55], [pos[0], pos[1], pos[2] + 1.2], 
                               [0, 0, 0], textSize=1, lifeTime=3.5)
        except:
            pass
        print(f"🤖 Pepper: {text}")
    
    def open_game(self):
        """Open ASD games at localhost:5000"""
        webbrowser.open(GAME_URL)
        return "🎮 Opening your ASD games dashboard! Have fun playing! 🎲"
    
    def open_video(self, topic):
        """Open cartoon video"""
        search = f"{topic} {CARTOON_SUFFIX}"
        url = f"{YOUTUBE_BASE}{urllib.parse.quote(search)}"
        webbrowser.open(url)
        return f"📺 Opening cartoon video about {topic}! 🌟"
    
    def open_picture(self, topic):
        """Open image"""
        clean = topic.replace(" ", "%20")
        url = f"{IMAGE_API}{clean}"
        webbrowser.open(url)
        return f"🖼️ Opening picture of {topic}! Look and learn! 📸"
    
    def dance(self):
        self.is_talking = True
        for _ in range(4):
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
            return "Hello! 👋"
        elif c in ["stop", "توقف"]:
            self.auto_walk = False
            return "Stopping here! 🧍"
        elif c in ["go", "walk", "move", "امشي"]:
            self.auto_walk = True
            return "Walking again! 🚶‍♂️"
        return None
    
    def run(self):
        while True:
            try:
                user = input("\n👶 You: ").strip()
                if user.lower() in ['exit', 'quit', 'bye', 'خروج']:
                    self.show_text("Goodbye! Come play again! 👋")
                    break
                if not user:
                    continue
                
                result = self.process_command(user)
                if result:
                    self.show_text(result)
                else:
                    self.show_text("Let me think... 🤔")
                    time.sleep(0.5)
                    response = self.ai.chat(user)
                    self.show_text(response)
                    
            except KeyboardInterrupt:
                print("\n")
                self.show_text("Goodbye! 👋")
                break

if __name__ == "__main__":
    pepper = PepperRobot()
    pepper.run()
