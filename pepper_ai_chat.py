#!/usr/bin/env python3
"""
Pepper AI Chat - PyBullet Version with Open Source AI Projects
- Pepper walks with balloons
- Voice input & output
- Integrated open source AI chat projects
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
import subprocess
import os
import json
from pathlib import Path
from qibullet import SimulationManager
import pybullet as p
import pybullet_data

# ========== Open Source AI Projects ==========
# Each project can be a web app, local server, or external URL
AI_PROJECTS = {
    # Chat Interfaces
    "chat": {
        "name": "AI Chat Interface",
        "type": "local",
        "path": "/home/ubuntu/pepper_duo/projects/chat",
        "port": 3000,
        "url": "http://localhost:3000",
        "description": "Free AI chat interface with multiple models",
        "keywords": ["chat", "talk", "conversation", "ai chat"]
    },
    
    # Local LLM Runner
    "ollama": {
        "name": "Ollama AI",
        "type": "local",
        "command": "ollama serve",
        "url": "http://localhost:11434",
        "description": "Run AI models locally - free and private",
        "keywords": ["ollama", "local ai", "private ai"]
    },
    
    # Lobe Chat - Multi-Provider AI
    "lobe": {
        "name": "Lobe Chat",
        "type": "web",
        "url": "https://lobe.chat",
        "description": "Modern AI chat workspace with multiple providers",
        "keywords": ["lobe", "modern chat", "ai workspace"]
    },
    
    # OpenRouter MCP
    "openrouter": {
        "name": "OpenRouter MCP",
        "type": "local",
        "path": "/home/ubuntu/pepper_duo/projects/openrouter-mcp",
        "port": 5000,
        "url": "http://localhost:5000",
        "description": "Access 300+ AI models through one interface",
        "keywords": ["openrouter", "many models", "model hub"]
    },
    
    # Quiz Games
    "quiz": {
        "name": "Quiz Games",
        "type": "local",
        "path": "/home/ubuntu/pepper_duo/projects/quizhp-mcp",
        "port": 5001,
        "url": "http://localhost:5001",
        "description": "80+ interactive quiz game templates",
        "keywords": ["quiz", "game", "trivia", "questions"]
    },
    
    # Document Chat
    "rag": {
        "name": "Document Chat",
        "type": "local",
        "path": "/home/ubuntu/pepper_duo/projects/rag-chatbot",
        "port": 5002,
        "url": "http://localhost:5002",
        "description": "Chat with your documents using RAG",
        "keywords": ["document", "pdf chat", "rag", "ask document"]
    },
    
    # Voice Assistant
    "voice": {
        "name": "Voice Assistant",
        "type": "local",
        "path": "/home/ubuntu/pepper_duo/projects/openclaw-voice",
        "port": 5003,
        "url": "http://localhost:5003",
        "description": "Browser-based voice chat for AI assistants",
        "keywords": ["voice", "speech", "talk", "listen"]
    },
    
    # YouTube Chat
    "youtube": {
        "name": "YouTube Chat",
        "type": "local",
        "path": "/home/ubuntu/pepper_duo/projects/distilltube",
        "port": 5004,
        "url": "http://localhost:5004",
        "description": "Turn any YouTube video into a conversation",
        "keywords": ["youtube", "video", "summary", "chat video"]
    },
    
    # AI Coding Assistant
    "coding": {
        "name": "AI Coding Assistant",
        "type": "web",
        "url": "https://github.com/features/copilot",
        "description": "Multi-AI coding assistant",
        "keywords": ["code", "programming", "coding help"]
    },
    
    # Drawing AI
    "drawing": {
        "name": "AI Drawing",
        "type": "local",
        "path": "/home/ubuntu/pepper_duo/projects/sketchvibe",
        "port": 5005,
        "url": "http://localhost:5005",
        "description": "AI that renders responses as visual blocks",
        "keywords": ["draw", "sketch", "art", "visual"]
    },
    
    # NS Budget Chat
    "budget": {
        "name": "NS Budget Chat",
        "type": "web",
        "url": "https://github.com/Synexiom-Labs/ns-budget-chat",
        "description": "Chat about Nova Scotia Budget 2026-27",
        "keywords": ["budget", "finance", "government"]
    },
    
    # Kaggle Chatbot
    "kaggle": {
        "name": "Kaggle Chatbot",
        "type": "web",
        "url": "https://github.com/kavindamihiran/Kaggle-chatbot",
        "description": "AI chatbot powered by Qwen2.5-Coder on free GPU",
        "keywords": ["kaggle", "qwen", "coder"]
    },
    
    # Healthcare Assistant
    "health": {
        "name": "Health Assistant",
        "type": "web",
        "url": "https://github.com/prabhatKumar65/PMJAY-Chatbot-POC",
        "description": "Healthcare scheme assistance chatbot",
        "keywords": ["health", "medical", "assistant"]
    },
    
    # Family AI Chat
    "family": {
        "name": "Family AI Chat",
        "type": "web",
        "url": "https://github.com/lanjam-ai/lanjam-chat",
        "description": "Private AI chat for families",
        "keywords": ["family", "kids", "safe chat"]
    },
    
    # DuckDuckGo AI
    "duckai": {
        "name": "DuckDuckGo AI",
        "type": "web",
        "url": "https://duckduckgo.com/?q=DuckDuckGo+AI+Chat&ia=chat",
        "description": "Free AI chat with multiple models",
        "keywords": ["duckduckgo", "free ai", "private"]
    },
    
    # Local AI Desktop
    "localai": {
        "name": "Local AI Desktop",
        "type": "local",
        "path": "/home/ubuntu/pepper_duo/projects/queai",
        "port": 5006,
        "url": "http://localhost:5006",
        "description": "Centralized access to local AI solutions",
        "keywords": ["local", "offline", "private"]
    },
    
    # Offline Chatbot
    "offline": {
        "name": "Offline Chatbot",
        "type": "local",
        "path": "/home/ubuntu/pepper_duo/projects/offline-chatbot",
        "port": 5007,
        "url": "http://localhost:5007",
        "description": "ChatGPT style interface for offline LLMs",
        "keywords": ["offline", "private", "no internet"]
    },
    
    # Ollama Manager
    "ollama-gui": {
        "name": "Ollama Manager",
        "type": "local",
        "path": "/home/ubuntu/pepper_duo/projects/ollama-manager",
        "port": 5008,
        "url": "http://localhost:5008",
        "description": "Desktop GUI for running AI models locally",
        "keywords": ["ollama", "gui", "desktop"]
    },
    
    # Android AI Chat
    "android": {
        "name": "Android AI Chat",
        "type": "web",
        "url": "https://github.com/ygxanix/pholus",
        "description": "Privacy-first Android chat app for LLMs",
        "keywords": ["android", "mobile", "privacy"]
    },
    
    # Chrome Extension
    "extension": {
        "name": "AI Chrome Extension",
        "type": "web",
        "url": "https://github.com/terminalskid/RayaAI",
        "description": "Right-click AI chat extension",
        "keywords": ["chrome", "extension", "browser"]
    }
}

# ========== AI Chat API ==========
CHAT_API = "https://text.pollinations.ai/v1/chat/completions"

def get_ai_response(message, child_name="Child"):
    # Create dynamic system prompt with available projects
    projects_list = "\n".join([f"- {key}: {info['description']}" for key, info in list(AI_PROJECTS.items())[:10]])
    
    system_prompt = f"""You are Pepper, a friendly AI robot for a child named {child_name}.
You have access to many free open-source AI projects:

{projects_list}
...and {len(AI_PROJECTS)} total projects!

When someone asks about an AI tool, you can say "Say open [project name] to try it!"
Respond in short, simple English sentences (1-2 sentences). Be kind, encouraging, and playful. Use emojis! 😊"""
    
    data = {
        "model": "openai",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ]
    }
    
    try:
        r = requests.post(CHAT_API, json=data, timeout=10)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
    except:
        pass
    
    return f"I have many AI projects! Try saying 'open chat' for AI chat, 'open quiz' for games, or 'open localai' for local AI! 😊"

# ========== Voice Classes ==========
class Voice:
    def __init__(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty("rate", 150)
        self.engine.setProperty("volume", 1.0)
        
    def speak(self, text):
        print(f"🔊 Pepper: {text}")
        self.engine.say(text)
        self.engine.runAndWait()

class Listener:
    def __init__(self):
        self.r = sr.Recognizer()
        self.r.energy_threshold = 300
        try:
            self.mic = sr.Microphone()
            with self.mic as source:
                self.r.adjust_for_ambient_noise(source, duration=1)
            print("🎤 Microphone ready!")
        except:
            self.mic = None
            print("⚠️ No microphone")
            
    def listen(self):
        if not self.mic:
            return None
        try:
            with self.mic as source:
                print("\n🎤 Listening...", end="", flush=True)
                audio = self.r.listen(source, timeout=4, phrase_time_limit=5)
            text = self.r.recognize_google(audio, language="en-US")
            print(f"\r   ✅ You said: {text}")
            return text.lower()
        except:
            print("\r   ❌ Could not understand", end="", flush=True)
            return None

# ========== Project Manager ==========
class ProjectManager:
    def __init__(self, voice):
        self.voice = voice
        self.running_projects = {}
        
    def find_project_by_keyword(self, text):
        """Find project that matches spoken keywords"""
        text_lower = text.lower()
        for key, project in AI_PROJECTS.items():
            for keyword in project.get("keywords", []):
                if keyword in text_lower:
                    return key, project
        return None, None
        
    def open_project(self, project_name):
        """Open a project by name or keyword"""
        # Try exact match first
        if project_name in AI_PROJECTS:
            project = AI_PROJECTS[project_name]
        else:
            # Try keyword matching
            found_key, found_project = self.find_project_by_keyword(project_name)
            if found_project:
                project = found_project
                project_name = found_key
            else:
                return False
        
        # Check if already running
        if project_name in self.running_projects:
            self.voice.speak(f"{project['name']} is already running!")
            webbrowser.open(project["url"])
            return True
        
        # Open based on type
        try:
            if project["type"] == "web":
                webbrowser.open(project["url"])
                self.voice.speak(f"Opening {project['name']}! {project['description']}")
                return True
                
            elif project["type"] == "local":
                # Check if path exists
                if "path" in project and os.path.exists(project["path"]):
                    # Try to start local server
                    if "command" in project:
                        proc = subprocess.Popen(
                            project["command"].split(),
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            shell=True
                        )
                    else:
                        # Assume it's a web app
                        proc = subprocess.Popen(
                            ["python3", "-m", "http.server", str(project["port"])],
                            cwd=project["path"],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL
                        )
                    
                    self.running_projects[project_name] = proc
                    time.sleep(2)  # Wait for server to start
                    webbrowser.open(project["url"])
                    self.voice.speak(f"Starting {project['name']}! {project['description']}")
                    return True
                else:
                    # Path doesn't exist, open GitHub instead
                    webbrowser.open(f"https://github.com/search?q={urllib.parse.quote(project_name)}")
                    self.voice.speak(f"I couldn't find {project['name']} installed. Opening GitHub to find it!")
                    return True
                    
        except Exception as e:
            print(f"Error opening {project_name}: {e}")
            return False
    
    def list_projects(self):
        """List all available projects"""
        projects_list = []
        for key, project in list(AI_PROJECTS.items())[:10]:  # Show first 10
            projects_list.append(f"{key} - {project['description']}")
        
        projects_text = ". ".join(projects_list[:5])
        self.voice.speak(f"I have {len(AI_PROJECTS)} AI projects! Here are some: {projects_text}. Say open followed by the project name!")
        
    def stop_all(self):
        """Stop all running projects"""
        for name, proc in self.running_projects.items():
            try:
                proc.terminate()
                print(f"Stopped {name}")
            except:
                pass

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
        
        # Balloons with different colors
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
    print("🤖 PEPPER AI CHAT - Open Source AI Projects Edition")
    print("="*60)
    print(f"📦 Loaded {len(AI_PROJECTS)} open source AI projects!")
    print("\n🎯 Voice Commands:")
    print("   • 'open [project]' - Open any AI project")
    print("   • 'what can you do' - List available projects")
    print("   • 'dance', 'wave' - Fun movements")
    print("   • 'help' - Show this help")
    print("\n📝 Example projects:")
    print("   • 'open chat' - AI Chat Interface")
    print("   • 'open quiz' - Quiz Games")
    print("   • 'open youtube' - YouTube Video Chat")
    print("   • 'open localai' - Local AI Desktop")
    print("="*60 + "\n")
    
    pepper = PepperRobot()
    voice = Voice()
    listener = Listener()
    project_manager = ProjectManager(voice)
    time.sleep(2)
    
    voice.speak(f"Hello! I'm Pepper! I have {len(AI_PROJECTS)} open source AI projects ready for you!")
    voice.speak("Say open chat for AI chat, open quiz for games, or say what can you do to see all projects!")
    
    while True:
        try:
            text = listener.listen()
            if text is None:
                continue
            
            # Exit commands
            if any(word in text for word in ["goodbye", "exit", "bye bye", "stop"]):
                voice.speak("Goodbye! It was nice talking with you! Come back soon!")
                break
            
            # Help command
            if "help" in text or "what can you do" in text or "projects" in text:
                project_manager.list_projects()
                continue
            
            # Dance command
            if "dance" in text:
                voice.speak("Let's dance!")
                pepper.dance()
                continue
            
            # Wave command
            if "wave" in text:
                voice.speak("Waving hello!")
                pepper.wave()
                continue
            
            # Open project commands
            if "open " in text:
                # Extract project name after "open"
                project_name = text.split("open ")[-1].strip()
                if project_name:
                    success = project_manager.open_project(project_name)
                    if not success:
                        voice.speak(f"I couldn't find {project_name}. Try saying 'what can you do' to see all projects!")
                continue
            
            # AI Chat for everything else
            response = get_ai_response(text)
            voice.speak(response)
            
        except KeyboardInterrupt:
            voice.speak("Goodbye!")
            break
    
    # Cleanup
    pepper.stop()
    project_manager.stop_all()
    print("\n✅ Done")

if __name__ == "__main__":
    main()
