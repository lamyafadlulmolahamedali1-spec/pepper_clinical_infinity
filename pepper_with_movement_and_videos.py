#!/usr/bin/env python3
"""
Pepper in PyBullet with:
- Real YouTube video links for "how to" questions
- Movement commands (move forward, backward, left, right, turn)
- AI chat
- Kids in room
"""

import time
import pybullet as p
import pybullet_data
import threading
import random
import math
import requests
import webbrowser
import urllib.parse
from qibullet import SimulationManager

# ========== Settings ==========
CHAT_API = "https://text.pollinations.ai/v1/chat/completions"
YOUTUBE_BASE = "https://www.youtube.com/results?search_query="

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
4. If child asks "how to" do something, OPEN A VIDEO
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
    
    def open_youtube_video(self, topic):
        """Open YouTube video for kids"""
        search_query = f"{topic} for kids educational step by step"
        encoded = urllib.parse.quote(search_query)
        url = f"{YOUTUBE_BASE}{encoded}"
        webbrowser.open(url)
        return f"📹 Opening a video about {topic} for you, {self.child_name}! Watch and learn! 🌟"

# ========== Create Kids as Humans ==========
def create_human_kid(name, color, position):
    """Create a human-shaped kid with name above head"""
    
    # Body
    body_visual = p.createVisualShape(
        p.GEOM_BOX,
        halfExtents=[0.2, 0.15, 0.4],
        rgbaColor=color
    )
    p.createMultiBody(
        baseMass=0,
        baseVisualShapeIndex=body_visual,
        basePosition=[position[0], position[1], position[2] + 0.2]
    )
    
    # Head
    head_visual = p.createVisualShape(
        p.GEOM_SPHERE,
        radius=0.15,
        rgbaColor=[1, 0.85, 0.7, 1]
    )
    p.createMultiBody(
        baseMass=0,
        baseVisualShapeIndex=head_visual,
        basePosition=[position[0], position[1], position[2] + 0.55]
    )
    
    # Eyes
    eye_visual = p.createVisualShape(p.GEOM_SPHERE, radius=0.04, rgbaColor=[0, 0, 0, 1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=eye_visual,
                     basePosition=[position[0] - 0.07, position[1] + 0.08, position[2] + 0.62])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=eye_visual,
                     basePosition=[position[0] + 0.07, position[1] + 0.08, position[2] + 0.62])
    
    # Mouth
    mouth_visual = p.createVisualShape(p.GEOM_SPHERE, radius=0.03, rgbaColor=[0.8, 0.2, 0.2, 1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=mouth_visual,
                     basePosition=[position[0], position[1] + 0.05, position[2] + 0.52])
    
    # Name
    p.addUserDebugText(
        name,
        [position[0], position[1], position[2] + 0.85],
        [0, 0, 0],
        textSize=0.8,
        lifeTime=0
    )

# ========== Build Full Room ==========
def build_full_room():
    """Build room with walls, furniture, and kids"""
    
    print("🏠 Building room...")
    
    # Ground
    p.setAdditionalSearchPath(pybullet_data.getDataPath())
    p.loadURDF("plane.urdf")
    
    # Rug
    rug = p.createVisualShape(p.GEOM_BOX, halfExtents=[4.5, 3.5, 0.02], rgbaColor=[0.5, 0.3, 0.2, 1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=rug, basePosition=[0, 0, 0.01])
    
    # Walls
    wall_color = [0.85, 0.85, 0.9, 1]
    wall_back = p.createVisualShape(p.GEOM_BOX, halfExtents=[5, 0.1, 2.2], rgbaColor=wall_color)
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=wall_back, basePosition=[0, -4, 1.1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=wall_back, basePosition=[0, 4, 1.1])
    
    wall_side = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.1, 4, 2.2], rgbaColor=wall_color)
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=wall_side, basePosition=[5, 0, 1.1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=wall_side, basePosition=[-5, 0, 1.1])
    
    # Table
    table = p.createVisualShape(p.GEOM_BOX, halfExtents=[1, 0.8, 0.4], rgbaColor=[0.6, 0.4, 0.2, 1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=table, basePosition=[2, 1.5, 0.4])
    
    # Chairs
    chair = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.4, 0.4, 0.3], rgbaColor=[0.5, 0.3, 0.1, 1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=chair, basePosition=[1.5, 1.8, 0.15])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=chair, basePosition=[2.5, 1.8, 0.15])
    
    # Shelf
    shelf = p.createVisualShape(p.GEOM_BOX, halfExtents=[1.5, 0.3, 1], rgbaColor=[0.6, 0.4, 0.2, 1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=shelf, basePosition=[-2.5, 2, 0.5])
    
    # Toy basket
    basket = p.createVisualShape(p.GEOM_CYLINDER, radius=0.4, length=0.4, rgbaColor=[0.3, 0.6, 0.3, 1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=basket, basePosition=[-1.5, -2, 0.2])
    
    # Kids
    kids = [
        ("Ahmed", [1.5, -1.2, 0], [1, 0.6, 0.4, 1]),
        ("Sara", [-1.2, 1.3, 0], [1, 0.7, 0.8, 1]),
        ("Yusuf", [0.5, -2, 0], [0.4, 0.7, 1, 1]),
        ("Layla", [2.8, -0.2, 0], [1, 0.5, 0.9, 1]),
        ("Omar", [-2.2, -1, 0], [0.4, 0.8, 0.4, 1]),
        ("Fatima", [3, 2, 0], [1, 0.8, 0.5, 1]),
        ("Ali", [-2.8, 1.5, 0], [0.6, 0.6, 0.8, 1]),
        ("Noor", [0, 2.5, 0], [1, 0.9, 0.7, 1]),
        ("Hassan", [-1, -2.2, 0], [0.5, 0.6, 0.5, 1]),
    ]
    
    for name, pos, color in kids:
        create_human_kid(name, color, pos)
        print(f"   👧 Created: {name}")
    
    print("✅ Room ready!")

# ========== Pepper Robot with Movement ==========
class PepperRobot:
    def __init__(self):
        self.ai = PepperAI(child_name="Yusuf")
        self.simulation_manager = SimulationManager()
        
        print("\n🤖 Launching PyBullet...")
        self.client = self.simulation_manager.launchSimulation(gui=True)
        p.setRealTimeSimulation(1)
        p.setGravity(0, 0, -9.81)
        
        # Build room
        build_full_room()
        
        # Spawn Pepper
        print("🤖 Spawning Pepper...")
        self.pepper = self.simulation_manager.spawnPepper(self.client)
        
        # Initial position
        self.current_x = 0
        self.current_y = 0
        self.current_angle = 0
        
        # Set camera view
        p.resetDebugVisualizerCamera(
            cameraDistance=6,
            cameraYaw=45,
            cameraPitch=-30,
            cameraTargetPosition=[0, 0, 1]
        )
        
        self.is_talking = False
        self.arm_angle = 0
        self.arm_direction = 1
        
        print("\n" + "="*55)
        print("✅ PEPPER IS READY!")
        print("="*55)
        print("📝 MOVEMENT COMMANDS:")
        print("   - 'move forward' - Pepper walks forward")
        print("   - 'move backward' - Pepper walks backward")
        print("   - 'turn left' - Pepper turns left")
        print("   - 'turn right' - Pepper turns right")
        print("   - 'come here' - Pepper comes to you")
        print("   - 'wave' - Pepper waves")
        print("   - 'how to ...' - Opens educational video")
        print("   - 'exit' - Quit")
        print("="*55)
    
    def move_pepper(self, direction):
        """Move Pepper in the room"""
        step = 0.3
        
        if direction == "forward":
            self.current_x += step * math.cos(self.current_angle)
            self.current_y += step * math.sin(self.current_angle)
        elif direction == "backward":
            self.current_x -= step * math.cos(self.current_angle)
            self.current_y -= step * math.sin(self.current_angle)
        elif direction == "left":
            self.current_angle += 0.3
        elif direction == "right":
            self.current_angle -= 0.3
        
        # Keep within bounds
        self.current_x = max(-3.5, min(3.5, self.current_x))
        self.current_y = max(-3, min(3, self.current_y))
        
        # Move Pepper
        try:
            self.pepper.setPosition([self.current_x, self.current_y, 0.8])
        except:
            pass
    
    def wave_arms(self):
        """Make Pepper wave"""
        self.is_talking = True
        for i in range(3):
            try:
                self.pepper.setAngles("LShoulderPitch", 1.0, 0.2)
                self.pepper.setAngles("RShoulderPitch", 1.0, 0.2)
                time.sleep(0.2)
                self.pepper.setAngles("LShoulderPitch", 0, 0.2)
                self.pepper.setAngles("RShoulderPitch", 0, 0.2)
                time.sleep(0.2)
            except:
                pass
        self.is_talking = False
    
    def smooth_arm_movement(self):
        """Smooth arm movement while talking"""
        while True:
            if self.is_talking:
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
    
    def show_text_over_head(self, text):
        """Show text above Pepper's head"""
        try:
            pos = p.getBasePositionAndOrientation(self.pepper.body)[0]
            p.addUserDebugText(
                text[:45],
                [pos[0], pos[1], pos[2] + 1.2],
                [0, 0, 0],
                textSize=1,
                lifeTime=3
            )
        except:
            pass
    
    def speak_with_arms(self, text):
        """Speak with smooth arm movement"""
        self.is_talking = True
        print(f"🤖 Pepper: {text}")
        self.show_text_over_head(text)
        time.sleep(min(len(text) * 0.08, 2.5))
        self.is_talking = False
    
    def run_simulation(self):
        """Run PyBullet simulation"""
        while True:
            p.stepSimulation()
            time.sleep(1./240.)
    
    def process_command(self, user_input):
        """Process movement commands"""
        cmd = user_input.lower().strip()
        
        # Movement commands
        if cmd == "move forward" or cmd == "forward":
            self.move_pepper("forward")
            return "Moving forward! 🚶"
        elif cmd == "move backward" or cmd == "backward":
            self.move_pepper("backward")
            return "Moving backward! 🔙"
        elif cmd == "turn left" or cmd == "left":
            self.move_pepper("left")
            return "Turning left! 🔄"
        elif cmd == "turn right" or cmd == "right":
            self.move_pepper("right")
            return "Turning right! 🔄"
        elif cmd == "come here" or cmd == "come":
            self.move_pepper("forward")
            return "Coming to you! 🚶‍♂️"
        elif cmd == "wave":
            self.wave_arms()
            return "👋 Waving hello!"
        
        # How-to questions - open video
        if "how to" in cmd:
            topic = cmd.replace("how to", "").strip()
            video_response = self.ai.open_youtube_video(topic)
            return video_response
        
        return None
    
    def run(self):
        """Main loop with terminal chat"""
        
        # Start threads
        arm_thread = threading.Thread(target=self.smooth_arm_movement, daemon=True)
        arm_thread.start()
        
        head_thread = threading.Thread(target=self.move_head_naturally, daemon=True)
        head_thread.start()
        
        sim_thread = threading.Thread(target=self.run_simulation, daemon=True)
        sim_thread.start()
        
        # Welcome
        self.speak_with_arms("Hello everyone! I'm Pepper! I can move around! Tell me to move forward, turn left, or ask me how to do something!")
        
        # Chat loop
        while True:
            try:
                user_input = input("\n👶 You: ").strip()
                
                if user_input.lower() in ['exit', 'quit', 'bye', 'goodbye']:
                    self.speak_with_arms("Goodbye! It was nice talking with you!")
                    time.sleep(2)
                    break
                
                if not user_input:
                    continue
                
                # Check for movement or video commands
                command_result = self.process_command(user_input)
                
                if command_result:
                    self.speak_with_arms(command_result)
                else:
                    # Regular AI chat
                    self.speak_with_arms("Let me think...")
                    time.sleep(0.5)
                    response = self.ai.get_response(user_input)
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
