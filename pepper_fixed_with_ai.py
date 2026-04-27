#!/usr/bin/env python3
"""
Pepper in PyBullet with Real Kids (Human-shaped) + AI + Smooth Arm Movement
- Fixed plane.urdf issue
- 7 kids with names above heads
- Pepper moves arms smoothly while talking
- AI chat through terminal
"""

import time
import pybullet as p
import pybullet_data
import threading
import random
import math
import requests
import sys
from qibullet import SimulationManager

# ========== AI Settings ==========
CHAT_API = "https://text.pollinations.ai/v1/chat/completions"

# ========== Voice/Speech ==========
class VoiceEngine:
    def __init__(self):
        self.last_message = ""
    
    def speak(self, text):
        print(f"🤖 Pepper: {text}")
        self.last_message = text

# ========== AI Engine ==========
class PepperAI:
    def __init__(self, child_name="Yusuf"):
        self.child_name = child_name
        self.last_request_time = 0
    
    def get_response(self, user_input):
        """Get AI response"""
        time_since_last = time.time() - self.last_request_time
        if time_since_last < 2:
            time.sleep(2 - time_since_last)
        
        system_prompt = f"""You are Pepper, a friendly robot for a child named {self.child_name} (under 18).

RULES:
1. Respond in 1-2 short, simple English sentences
2. Be kind, patient, and encouraging
3. Use the child's name: {self.child_name}
4. If child asks "how to" do something, say "I'll show you a video!"
5. Keep responses positive and educational

Child's message: {user_input}"""
        
        data = {
            "model": "openai",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            "temperature": 0.7,
            "max_tokens": 80
        }
        
        try:
            response = requests.post(CHAT_API, json=data, timeout=15)
            self.last_request_time = time.time()
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            else:
                return f"That's a great question, {self.child_name}! Tell me more!"
        except:
            return f"I'm here to help you learn, {self.child_name}! What would you like to know?"

# ========== Create Kids as Humans ==========
class HumanKid:
    def __init__(self, name, color, position):
        self.name = name
        self.color = color
        self.position = position
    
    def create(self):
        """Create kid in simulation"""
        # Body (box shape)
        body_visual = p.createVisualShape(
            p.GEOM_BOX,
            halfExtents=[0.2, 0.15, 0.4],
            rgbaColor=self.color
        )
        p.createMultiBody(
            baseMass=0,
            baseVisualShapeIndex=body_visual,
            basePosition=[self.position[0], self.position[1], self.position[2] + 0.2]
        )
        
        # Head (sphere)
        head_visual = p.createVisualShape(
            p.GEOM_SPHERE,
            radius=0.15,
            rgbaColor=[1, 0.85, 0.7, 1]  # Skin color
        )
        p.createMultiBody(
            baseMass=0,
            baseVisualShapeIndex=head_visual,
            basePosition=[self.position[0], self.position[1], self.position[2] + 0.55]
        )
        
        # Eyes
        eye_visual = p.createVisualShape(p.GEOM_SPHERE, radius=0.04, rgbaColor=[0, 0, 0, 1])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=eye_visual,
                         basePosition=[self.position[0] - 0.07, self.position[1] + 0.08, self.position[2] + 0.62])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=eye_visual,
                         basePosition=[self.position[0] + 0.07, self.position[1] + 0.08, self.position[2] + 0.62])
        
        # Mouth (small red sphere)
        mouth_visual = p.createVisualShape(p.GEOM_SPHERE, radius=0.03, rgbaColor=[0.8, 0.2, 0.2, 1])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=mouth_visual,
                         basePosition=[self.position[0], self.position[1] + 0.05, self.position[2] + 0.52])
        
        # Name above head
        p.addUserDebugText(
            self.name,
            [self.position[0], self.position[1], self.position[2] + 0.85],
            [0, 0, 0],
            textSize=0.8,
            lifeTime=0
        )

# ========== Full Room with Kids ==========
class FullRoom:
    def __init__(self):
        print("🏠 Building room...")
        self.build_floor_and_walls()
        self.build_furniture()
        self.build_kids()
        print("✅ Room ready with kids!")
    
    def build_floor_and_walls(self):
        """Build floor using plane from pybullet_data"""
        # Use the correct plane from pybullet_data
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        plane = p.loadURDF("plane.urdf")
        p.changeVisualShape(plane, -1, rgbaColor=[0.7, 0.7, 0.8, 1])
        
        # Add a floor texture/rug
        rug_visual = p.createVisualShape(p.GEOM_BOX, halfExtents=[4.5, 3.5, 0.02], rgbaColor=[0.5, 0.3, 0.2, 1])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=rug_visual, basePosition=[0, 0, 0.01])
        
        # Simple walls as boxes around the room
        # Back wall
        wall_visual = p.createVisualShape(p.GEOM_BOX, halfExtents=[5, 0.1, 2], rgbaColor=[0.85, 0.85, 0.9, 1])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=wall_visual, basePosition=[0, -4, 1])
        
        # Front wall
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=wall_visual, basePosition=[0, 4, 1])
        
        # Right wall
        wall_right = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.1, 4, 2], rgbaColor=[0.85, 0.85, 0.9, 1])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=wall_right, basePosition=[5, 0, 1])
        
        # Left wall
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=wall_right, basePosition=[-5, 0, 1])
    
    def build_furniture(self):
        """Add furniture"""
        # Table
        table_visual = p.createVisualShape(p.GEOM_BOX, halfExtents=[1, 0.8, 0.4], rgbaColor=[0.6, 0.4, 0.2, 1])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=table_visual, basePosition=[2, 1.5, 0.4])
        
        # Chairs
        chair_visual = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.4, 0.4, 0.3], rgbaColor=[0.5, 0.3, 0.1, 1])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=chair_visual, basePosition=[1.5, 1.8, 0.15])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=chair_visual, basePosition=[2.5, 1.8, 0.15])
        
        # Shelf
        shelf_visual = p.createVisualShape(p.GEOM_BOX, halfExtents=[1.5, 0.3, 1], rgbaColor=[0.6, 0.4, 0.2, 1])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=shelf_visual, basePosition=[-2.5, 2, 0.5])
        
        # Toy basket
        basket_visual = p.createVisualShape(p.GEOM_CYLINDER, radius=0.4, length=0.4, rgbaColor=[0.3, 0.6, 0.3, 1])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=basket_visual, basePosition=[-1.5, -2, 0.2])
    
    def build_kids(self):
        """Create kids as humans with names"""
        kids_data = [
            ("Ahmed", [1.5, -1.2, 0], [1, 0.6, 0.4, 1]),     # Brown
            ("Sara", [-1.2, 1.3, 0], [1, 0.7, 0.8, 1]),      # Pink
            ("Yusuf", [0.5, -2, 0], [0.4, 0.7, 1, 1]),       # Blue
            ("Layla", [2.8, -0.2, 0], [1, 0.5, 0.9, 1]),     # Light pink
            ("Omar", [-2.2, -1, 0], [0.4, 0.8, 0.4, 1]),     # Green
            ("Fatima", [3, 2, 0], [1, 0.8, 0.5, 1]),         # Orange
            ("Ali", [-2.8, 1.5, 0], [0.6, 0.6, 0.8, 1]),     # Purple
            ("Noor", [0, 2.5, 0], [1, 0.9, 0.7, 1]),         # Peach
            ("Hassan", [-1, -2.2, 0], [0.5, 0.6, 0.5, 1]),   # Dark green
        ]
        
        for name, pos, color in kids_data:
            kid = HumanKid(name, color, pos)
            kid.create()
            print(f"   👧 Created: {name}")

# ========== Pepper with Smooth Arm Movement ==========
class PepperRobot:
    def __init__(self):
        self.voice = VoiceEngine()
        self.ai = PepperAI(child_name="Yusuf")
        self.simulation_manager = SimulationManager()
        
        print("\n🤖 Launching PyBullet with Pepper...")
        self.client = self.simulation_manager.launchSimulation(gui=True)
        p.setRealTimeSimulation(1)
        
        # Set camera position for better view
        p.resetDebugVisualizerCamera(
            cameraDistance=6,
            cameraYaw=45,
            cameraPitch=-30,
            cameraTargetPosition=[0, 0, 1]
        )
        
        # Build room with kids
        self.room = FullRoom()
        
        # Spawn Pepper
        print("🤖 Spawning Pepper...")
        self.pepper = self.simulation_manager.spawnPepper(self.client, spawn_ground=True)
        self.pepper.setPosition([0, 0, 0.8])
        self.pepper.goToPosture("Stand", 0.5)
        
        self.is_talking = False
        self.arm_angle = 0
        self.arm_direction = 1
        
        print("\n" + "="*55)
        print("✅ PEPPER IS READY!")
        print("="*55)
        print("📝 Type in THIS TERMINAL to talk to Pepper")
        print("👋 Pepper moves his arms smoothly while talking")
        print("👧 There are 9 kids in the room (with names above heads)")
        print("💬 Type 'exit' to quit")
        print("="*55)
    
    def smooth_arm_movement(self):
        """Smooth arm movement while talking"""
        while True:
            if self.is_talking:
                # Smooth up and down movement
                self.arm_angle += 0.06 * self.arm_direction
                if self.arm_angle > 0.9:
                    self.arm_angle = 0.9
                    self.arm_direction = -1
                elif self.arm_angle < 0:
                    self.arm_angle = 0
                    self.arm_direction = 1
                
                try:
                    self.pepper.setAngles("LShoulderPitch", self.arm_angle, 0.1)
                    self.pepper.setAngles("RShoulderPitch", self.arm_angle, 0.1)
                except:
                    pass
            else:
                # Slowly lower arms
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
    
    def move_head_naturally(self):
        """Natural head movement"""
        t = 0
        while True:
            t += 0.02
            try:
                yaw = math.sin(t) * 0.4
                pitch = math.sin(t * 0.7) * 0.15
                self.pepper.setAngles("HeadYaw", yaw, 0.1)
                self.pepper.setAngles("HeadPitch", pitch, 0.1)
            except:
                pass
            time.sleep(0.05)
    
    def show_text_over_head(self, text, duration=3):
        """Show text above Pepper's head"""
        try:
            pos = self.pepper.getPosition()
            p.addUserDebugText(
                text[:45],
                [pos[0], pos[1], pos[2] + 1.2],
                [0, 0, 0],
                textSize=1,
                lifeTime=duration
            )
        except:
            pass
    
    def speak_with_arms(self, text):
        """Speak with smooth arm movement"""
        self.is_talking = True
        print(f"🤖 Pepper: {text}")
        self.show_text_over_head(text)
        
        # Simulate talking time
        time.sleep(min(len(text) * 0.08, 2.5))
        self.is_talking = False
    
    def run_simulation(self):
        """Run PyBullet simulation"""
        while True:
            p.stepSimulation()
            time.sleep(1./240.)
    
    def run(self):
        """Main loop with terminal chat"""
        
        # Start arm movement thread
        arm_thread = threading.Thread(target=self.smooth_arm_movement, daemon=True)
        arm_thread.start()
        
        # Start head movement thread
        head_thread = threading.Thread(target=self.move_head_naturally, daemon=True)
        head_thread.start()
        
        # Start simulation thread
        sim_thread = threading.Thread(target=self.run_simulation, daemon=True)
        sim_thread.start()
        
        # Welcome message
        self.speak_with_arms("Hello everyone! I'm Pepper! Let's learn and play together!")
        
        # Main chat loop
        while True:
            try:
                user_input = input("\n👶 You: ").strip()
                
                if user_input.lower() in ['exit', 'quit', 'bye', 'goodbye']:
                    self.speak_with_arms("Goodbye! It was nice talking with you!")
                    time.sleep(2)
                    break
                
                if not user_input:
                    continue
                
                # Thinking response
                self.speak_with_arms("Let me think about that...")
                time.sleep(0.8)
                
                # Get AI response
                response = self.ai.get_response(user_input)
                
                # Speak with arm movement
                self.speak_with_arms(response)
                
            except KeyboardInterrupt:
                print("\n")
                self.speak_with_arms("Goodbye! See you next time!")
                break
            except Exception as e:
                print(f"Error: {e}")
                continue

if __name__ == "__main__":
    pepper = PepperRobot()
    pepper.run()
