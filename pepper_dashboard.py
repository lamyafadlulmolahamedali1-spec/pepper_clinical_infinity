#!/usr/bin/env python3
"""
Pepper with Dashboard Integration
- All projects accessible via dashboard at localhost:5000
- Pepper opens the dashboard when asked
"""

import time
import threading
import random
import math
import requests
import webbrowser
import urllib.parse
import speech_recognition as sr
import pyttsx3
import queue
import subprocess
import os
from qibullet import SimulationManager
import pybullet as p
import pybullet_data

# Dashboard URL
DASHBOARD_URL = "http://localhost:5000"

# ========== VOICE HANDLER ==========
class VoiceHandler:
    def __init__(self):
        self.engine = None
        self.recognizer = None
        self.microphone = None
        self.has_mic = False
        
        try:
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', 145)
            self.engine.setProperty('volume', 0.95)
            print("✅ Pepper voice ready")
        except:
            print("⚠️ Voice output not available")
        
        try:
            self.recognizer = sr.Recognizer()
            self.recognizer.energy_threshold = 4000
            self.microphone = sr.Microphone()
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            self.has_mic = True
            print("✅ Microphone ready")
        except:
            print("⚠️ No microphone detected")
    
    def speak(self, text):
        print(f"\n🤖 Pepper: {text}")
        if self.engine:
            try:
                self.engine.say(text)
                self.engine.runAndWait()
            except:
                pass
    
    def listen(self):
        if not self.has_mic:
            return None
        try:
            with self.microphone as source:
                print("\n🎤 Listening...", end="", flush=True)
                audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=5)
            text = self.recognizer.recognize_google(audio, language="en-US")
            print(f"\r✅ You: {text}")
            return text.lower()
        except:
            print("\r❌ Could not understand", end="", flush=True)
            return None

# ========== TEXT HANDLER ==========
class TextHandler:
    def __init__(self):
        self.input_queue = queue.Queue()
        self.running = True
        threading.Thread(target=self._get_input, daemon=True).start()
    
    def _get_input(self):
        while self.running:
            try:
                text = input("")
                if text:
                    self.input_queue.put(text)
            except:
                pass
    
    def get_command(self):
        try:
            return self.input_queue.get_nowait().lower()
        except:
            return None
    
    def speak(self, text):
        print(f"\n🤖 Pepper: {text}")
    
    def stop(self):
        self.running = False

# ========== PEPPER ROBOT ==========
class PepperRobot:
    def __init__(self):
        print("🤖 Starting Pepper robot...")
        self.running = True
        self.t = 0
        self.arm_angle = 0
        self.arm_direction = 1
        
        try:
            self.sim = SimulationManager()
            self.client = self.sim.launchSimulation(gui=True)
            p.setAdditionalSearchPath(pybullet_data.getDataPath())
            p.setRealTimeSimulation(1)
            p.setGravity(0, 0, -9.81)
            
            p.loadURDF("plane.urdf")
            
            # Furniture
            table_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.9, 0.6, 0.35], rgbaColor=[0.55, 0.35, 0.15, 1])
            p.createMultiBody(baseMass=0, baseVisualShapeIndex=table_vis, basePosition=[1.8, 1.5, 0.35])
            
            chair_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.4, 0.4, 0.45], rgbaColor=[0.5, 0.3, 0.1, 1])
            p.createMultiBody(baseMass=0, baseVisualShapeIndex=chair_vis, basePosition=[1.8, 2.1, 0.25])
            
            shelf_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[1.2, 0.25, 0.9], rgbaColor=[0.4, 0.25, 0.1, 1])
            p.createMultiBody(baseMass=0, baseVisualShapeIndex=shelf_vis, basePosition=[-2.0, -1.8, 0.5])
            
            # Characters
            yusuf_vis = p.createVisualShape(p.GEOM_SPHERE, radius=0.22, rgbaColor=[0.2, 0.5, 0.9, 1])
            self.yusuf = p.createMultiBody(baseMass=0, baseVisualShapeIndex=yusuf_vis, basePosition=[2.2, -1.2, 0.22])
            
            ahmed_vis = p.createVisualShape(p.GEOM_SPHERE, radius=0.22, rgbaColor=[0.2, 0.8, 0.3, 1])
            self.ahmed = p.createMultiBody(baseMass=0, baseVisualShapeIndex=ahmed_vis, basePosition=[2.5, -1.6, 0.22])
            
            leila_vis = p.createVisualShape(p.GEOM_SPHERE, radius=0.2, rgbaColor=[1, 0.6, 0.8, 1])
            self.leila = p.createMultiBody(baseMass=0, baseVisualShapeIndex=leila_vis, basePosition=[1.9, -1.4, 0.2])
            
            # Pepper
            self.pepper = self.sim.spawnPepper(self.client)
            self.pepper.goToPosture("Stand", 0.5)
            time.sleep(0.5)
            
            # Balloons
            colors = [[1, 0.2, 0.2, 1], [0.2, 1, 0.2, 1], [0.2, 0.2, 1, 1],
                      [1, 1, 0.2, 1], [1, 0.5, 0.2, 1], [0.8, 0.2, 0.8, 1],
                      [0.2, 0.8, 0.8, 1]]
            self.balloons = []
            for i in range(20):
                x = random.uniform(-3.2, 3.2)
                y = random.uniform(-2.8, 2.8)
                vis = p.createVisualShape(p.GEOM_SPHERE, radius=0.13, rgbaColor=colors[i%7])
                ball = p.createMultiBody(baseMass=0, baseVisualShapeIndex=vis, 
                                        basePosition=[x, y, random.uniform(0.5, 1.7)])
                self.balloons.append(ball)
            
            p.resetDebugVisualizerCamera(cameraDistance=6.2, cameraYaw=48, 
                                        cameraPitch=-26, cameraTargetPosition=[0, 0, 0.85])
            
            print("✅ Pepper is ready with 20 balloons!")
            threading.Thread(target=self._animate, daemon=True).start()
            
        except Exception as e:
            print(f"⚠️ Robot error: {e}")
    
    def _animate(self):
        while self.running:
            try:
                self.t += 0.018
                x = 2.4 * math.cos(self.t * 0.38)
                y = 2.0 * math.sin(self.t * 0.48)
                self.pepper.setTranslation([x, y, 0.85])
                
                self.arm_angle += 0.12 * self.arm_direction
                if self.arm_angle > 0.6:
                    self.arm_direction = -1
                elif self.arm_angle < -0.2:
                    self.arm_direction = 1
                
                try:
                    self.pepper.setAngles("LShoulderPitch", 0.4 + self.arm_angle, 0.1)
                    self.pepper.setAngles("RShoulderPitch", 0.4 - self.arm_angle, 0.1)
                except:
                    pass
                
                head_angle = 0.2 * math.sin(self.t * 1.2)
                try:
                    self.pepper.setAngles("HeadYaw", head_angle, 0.1)
                except:
                    pass
                
                p.resetBasePositionAndOrientation(self.yusuf, [2.2 + 0.1*math.sin(self.t*0.6), -1.2, 0.22], [0,0,0,1])
                p.resetBasePositionAndOrientation(self.ahmed, [2.5 + 0.1*math.cos(self.t*0.7), -1.6, 0.22], [0,0,0,1])
                p.resetBasePositionAndOrientation(self.leila, [1.9 + 0.08*math.sin(self.t*0.9), -1.4, 0.2], [0,0,0,1])
                
                for b in self.balloons:
                    pos, _ = p.getBasePositionAndOrientation(b)
                    new_z = pos[2] + 0.009
                    if new_z > 1.85:
                        new_z = 0.5
                    p.resetBasePositionAndOrientation(b, [pos[0], pos[1], new_z], [0,0,0,1])
                
                p.stepSimulation()
                time.sleep(0.045)
            except:
                pass
    
    def dance(self):
        try:
            for _ in range(5):
                for angle in [0.7, 1.3, 0.9, 0.2]:
                    self.pepper.setAngles("LShoulderPitch", angle, 0.12)
                    self.pepper.setAngles("RShoulderPitch", angle, 0.12)
                    time.sleep(0.1)
                time.sleep(0.15)
        except:
            pass
    
    def wave(self):
        try:
            for _ in range(4):
                self.pepper.setAngles("RShoulderPitch", 1.4, 0.18)
                time.sleep(0.2)
                self.pepper.setAngles("RShoulderPitch", 0.3, 0.18)
                time.sleep(0.2)
        except:
            pass
    
    def stop(self):
        self.running = False

# ========== MAIN ==========
def main():
    print("\n" + "="*70)
    print("🤖 PEPPER WITH DASHBOARD - All Projects in One Place")
    print("="*70)
    
    # Choose input mode
    print("\n🔊 Choose input mode:")
    print("   [1] ✍️  TEXT - Type your messages")
    print("   [2] 🎤 VOICE - Speak to Pepper")
    print("   [3] 🎯 BOTH - Speak and type together")
    
    choice = input("\n📝 Enter number (1, 2, or 3): ").strip()
    
    if choice == "1":
        interface = TextHandler()
        print("\n✅ TEXT MODE - Type your messages below")
    elif choice == "2":
        interface = VoiceHandler()
        print("\n✅ VOICE MODE - Speak to Pepper")
    else:
        interface = VoiceHandler()
        print("\n✅ BOTH MODE - Speak and type together")
        text_queue = queue.Queue()
        def text_input():
            while True:
                try:
                    text = input("")
                    if text:
                        text_queue.put(text)
                except:
                    pass
        threading.Thread(target=text_input, daemon=True).start()
    
    print("\n" + "="*70)
    print("🎈 Pepper is walking in the room with:")
    print("   • 20 colorful floating balloons")
    print("   • Furniture (Table, Chair, Bookshelf)")
    print("   • Friends: Yusuf (blue), Ahmed (green), Leila (pink)")
    print(f"   • Dashboard: {DASHBOARD_URL} - All projects in one place!")
    print("\n🎯 Commands:")
    print("   • 'dance' - Pepper dances")
    print("   • 'wave' - Pepper waves")
    print("   • 'dashboard' - Open the projects dashboard")
    print("   • 'video [topic]' - Search YouTube tutorials")
    print("   • 'image [topic]' - Search Google Images")
    print("   • 'play [song]' - Play music on YouTube")
    print("   • 'goodbye' - Exit")
    print("="*70 + "\n")
    
    # Start dashboard server in background
    dashboard_process = None
    dashboard_path = "/home/lamya/pepper_duo/dashboard"
    if os.path.exists(dashboard_path):
        try:
            dashboard_process = subprocess.Popen(
                ["python3", "start_dashboard.py"],
                cwd=dashboard_path,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            print("✅ Dashboard server starting...")
            time.sleep(2)
        except:
            print("⚠️ Could not start dashboard server")
    
    robot = PepperRobot()
    
    time.sleep(2)
    interface.speak("Hello! I'm Pepper!")
    interface.speak("I have 20 colorful balloons and my friends Yusuf, Ahmed, and Leila are here!")
    interface.speak("Say dashboard to see all my projects in one place!")
    
    running = True
    while running:
        cmd = None
        
        if choice == "1":
            cmd = interface.get_command()
        elif choice == "2":
            cmd = interface.listen()
        else:
            try:
                cmd = text_queue.get_nowait().lower()
                print()
            except:
                cmd = interface.listen()
        
        if cmd:
            # Exit
            if cmd in ["goodbye", "exit", "quit", "bye", "stop"]:
                interface.speak("Goodbye! Come back soon!")
                running = False
            
            # Dance
            elif "dance" in cmd:
                interface.speak("Let's dance!")
                robot.dance()
            
            # Wave
            elif "wave" in cmd:
                interface.speak("Hello there!")
                robot.wave()
            
            # Open Dashboard
            elif cmd in ["dashboard", "projects", "all projects", "menu"]:
                webbrowser.open(DASHBOARD_URL)
                interface.speak("Opening my projects dashboard! You'll see all my AI tools there!")
            
            # YouTube video
            elif cmd.startswith("video "):
                topic = cmd[6:].strip()
                search = urllib.parse.quote(topic)
                url = f"https://www.youtube.com/results?search_query={search}"
                webbrowser.open(url)
                interface.speak(f"Opening videos about {topic}")
            
            # Images
            elif cmd.startswith("image "):
                topic = cmd[6:].strip()
                search = urllib.parse.quote(topic)
                url = f"https://www.google.com/search?q={search}&tbm=isch"
                webbrowser.open(url)
                interface.speak(f"Opening images of {topic}")
            
            # Music
            elif cmd.startswith("play "):
                song = cmd[5:].strip()
                search = urllib.parse.quote(f"{song} song")
                url = f"https://www.youtube.com/results?search_query={search}"
                webbrowser.open(url)
                interface.speak(f"Playing {song}")
            
            # Default AI response
            else:
                responses = [
                    "That's interesting! Tell me more! 😊",
                    "I love talking with you! Say dashboard to see my projects! 🌟",
                    "I have 20 balloons floating around me! 🎈",
                    "You can ask me to open the dashboard to see all my AI tools! 🚀"
                ]
                interface.speak(random.choice(responses))
        
        time.sleep(0.1)
    
    # Cleanup
    robot.stop()
    if dashboard_process:
        dashboard_process.terminate()
    if hasattr(interface, 'stop'):
        interface.stop()
    print("\n✅ Goodbye!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
