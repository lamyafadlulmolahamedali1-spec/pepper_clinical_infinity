#!/usr/bin/env python3
"""
Pepper All-In-One - يجمع كل الميزات من:
- Gemini AI (Google)
- GPT with gestures
- Dashboard control
- Android control
- Advanced simulation
"""

import time
import threading
import random
import math
import json
import requests
import webbrowser
import urllib.parse
from qibullet import SimulationManager
import pybullet as p
import pybullet_data

# ========== Configuration ==========
GEMINI_API_KEY = ""  # ضعي مفتاح Gemini API هنا
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# ========== Google Gemini AI (من Pepper-Gemini-Flash-2.5) ==========
class GeminiAI:
    def __init__(self, api_key=""):
        self.api_key = api_key
        self.conversation_history = []
    
    def get_response(self, message):
        if not self.api_key:
            return self.get_fallback_response(message)
        
        url = f"{GEMINI_API_URL}?key={self.api_key}"
        data = {
            "contents": [{"parts": [{"text": message}]}],
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 100}
        }
        try:
            response = requests.post(url, json=data, timeout=10)
            if response.status_code == 200:
                return response.json()["candidates"][0]["content"]["parts"][0]["text"]
        except:
            pass
        return self.get_fallback_response(message)
    
    def get_fallback_response(self, message):
        return f"That's interesting! Tell me more about {message} 😊"

# ========== GPT with Gestures (من GPT-Pepper) ==========
class GPTWithGestures:
    def __init__(self, pepper):
        self.pepper = pepper
        self.gestures = {
            "hello": ["LShoulderPitch", 1.2, "RShoulderPitch", 1.2],
            "wave": ["LShoulderPitch", 1.5, "RShoulderPitch", 1.5],
            "dance": ["LShoulderPitch", 1.0, "RShoulderPitch", 1.0],
            "excited": ["LShoulderPitch", 1.3, "RShoulderPitch", 1.3]
        }
    
    def speak_with_gesture(self, text, gesture="hello"):
        if gesture in self.gestures:
            g = self.gestures[gesture]
            try:
                self.pepper.setAngles(g[0], g[1], 0.2)
                self.pepper.setAngles(g[2], g[3], 0.2)
                time.sleep(0.5)
                self.pepper.setAngles(g[0], 0, 0.2)
                self.pepper.setAngles(g[2], 0, 0.2)
            except:
                pass
        return f"🤖 Pepper: {text}"

# ========== Dashboard Control (من Pepper-Robot-Dashboard) ==========
class DashboardControl:
    def __init__(self):
        self.dashboard_port = 5004
        self.dashboard_running = False
    
    def start_dashboard(self):
        """تشغيل داشبورد التحكم"""
        import subprocess
        subprocess.Popen(["python3", "-m", "http.server", str(self.dashboard_port)], 
                        cwd="/home/lamya/Desktop/Pepper-Robot-Dashboard", 
                        stderr=subprocess.DEVNULL)
        self.dashboard_running = True
        print(f"📊 Dashboard running at http://localhost:{self.dashboard_port}")
    
    def open_dashboard(self):
        webbrowser.open(f"http://localhost:{self.dashboard_port}")

# ========== Android Control (من pepper-android-realtime-chat) ==========
class AndroidControl:
    def __init__(self):
        self.android_port = 8080
        self.commands = []
    
    def start_server(self):
        """تشغيل خادم للتحكم من الأندرويد"""
        import http.server
        import socketserver
        
        handler = http.server.SimpleHTTPRequestHandler
        self.httpd = socketserver.TCPServer(("", self.android_port), handler)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        print(f"📱 Android control at http://localhost:{self.android_port}")

# ========== PyBullet Pepper ==========
class PepperRobot:
    def __init__(self):
        print("🤖 Starting Pepper in PyBullet...")
        self.sim = SimulationManager()
        self.client = self.sim.launchSimulation(gui=True)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.setRealTimeSimulation(1)
        p.setGravity(0, 0, -9.81)
        p.loadURDF("plane.urdf")
        self.pepper = self.sim.spawnPepper(self.client)
        self.pepper.goToPosture("Stand", 0.5)
        print("✅ Pepper loaded!")
        
        # Balloons
        colors = [[1,0,0,1], [0,1,0,1], [0,0,1,1], [1,1,0,1], [1,0.5,0,1]]
        self.balloons = []
        for i in range(10):
            x = random.uniform(-3, 3)
            y = random.uniform(-2.5, 2.5)
            vis = p.createVisualShape(p.GEOM_SPHERE, radius=0.12, rgbaColor=colors[i%5])
            ball = p.createMultiBody(baseMass=0, baseVisualShapeIndex=vis, basePosition=[x, y, random.uniform(0.5,1.5)])
            self.balloons.append(ball)
        
        p.resetDebugVisualizerCamera(cameraDistance=6, cameraYaw=45, cameraPitch=-30, cameraTargetPosition=[0,0,0.8])
        self.running = True
        self.t = 0
        threading.Thread(target=self._walk, daemon=True).start()
        threading.Thread(target=self._update_balloons, daemon=True).start()
        
        # Initialize features
        self.gemini = GeminiAI(api_key=GEMINI_API_KEY)
        self.gestures = GPTWithGestures(self.pepper)
        self.dashboard = DashboardControl()
        self.android = AndroidControl()
    
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
                if new_z > 1.6:
                    new_z = 0.3
                p.resetBasePositionAndOrientation(b, [pos[0], pos[1], new_z], [0,0,0,1])
            p.stepSimulation()
            time.sleep(1/60.)
    
    def dance(self):
        for _ in range(3):
            for angle in [0.5, 1.0, 0.5, 0]:
                try:
                    self.pepper.setAngles("LShoulderPitch", angle, 0.1)
                    self.pepper.setAngles("RShoulderPitch", angle, 0.1)
                    time.sleep(0.15)
                except:
                    pass
    
    def wave(self):
        for _ in range(2):
            try:
                self.pepper.setAngles("LShoulderPitch", 1.2, 0.2)
                self.pepper.setAngles("RShoulderPitch", 1.2, 0.2)
                time.sleep(0.3)
                self.pepper.setAngles("LShoulderPitch", 0, 0.2)
                self.pepper.setAngles("RShoulderPitch", 0, 0.2)
                time.sleep(0.3)
            except:
                pass
    
    def stop(self):
        self.running = False

# ========== Main ==========
def main():
    print("\n" + "="*60)
    print("🤖 PEPPER ALL-IN-ONE - كل الميزات في مكان واحد")
    print("="*60)
    print("✅ Pepper in PyBullet with balloons")
    print("✅ Google Gemini AI")
    print("✅ GPT with gestures")
    print("✅ Dashboard control")
    print("✅ Android control")
    print("="*60 + "\n")
    
    pepper = PepperRobot()
    time.sleep(2)
    
    # Start dashboard
    pepper.dashboard.start_dashboard()
    
    # Start android server
    pepper.android.start_server()
    
    print("\n🎮 Commands:")
    print("   Type 'dance' - Pepper dances")
    print("   Type 'wave' - Pepper waves")
    print("   Type 'dashboard' - Open control dashboard")
    print("   Type 'game' - Open games")
    print("   Type 'exit' - Quit")
    print("-"*50 + "\n")
    
    while True:
        try:
            user = input("👶 You: ").strip().lower()
            
            if user == 'exit':
                print("🤖 Pepper: Goodbye!")
                break
            elif user == 'dance':
                print("💃 Pepper dances!")
                pepper.dance()
            elif user == 'wave':
                print("👋 Pepper waves!")
                pepper.wave()
            elif user == 'dashboard':
                pepper.dashboard.open_dashboard()
                print("📊 Dashboard opened!")
            elif user == 'game':
                webbrowser.open("http://localhost:5001")
                print("🎮 Games opened!")
            else:
                # Use Gemini AI
                response = pepper.gemini.get_response(user)
                # Add gesture
                pepper.gestures.speak_with_gesture(response, "hello")
                
        except KeyboardInterrupt:
            print("\n🤖 Pepper: Goodbye!")
            break
    
    pepper.stop()

if __name__ == "__main__":
    main()
