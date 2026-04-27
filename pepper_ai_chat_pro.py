#!/usr/bin/env python3
"""
Pepper AI Chat ULTIMATE - Advanced Version
- Full voice + text interface
- 30+ open source AI projects
- Advanced voice assistants integration
- Dual-mode interaction (voice & keyboard)
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
import sys
import json
import queue
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from qibullet import SimulationManager
import pybullet as p
import pybullet_data

# ========== CONFIGURATION ==========
class Config:
    CHAT_API = "https://text.pollinations.ai/v1/chat/completions"
    USE_VOICE = True
    USE_TEXT_INPUT = True
    AUTO_OPEN_BROWSER = True
    SIMULATION_QUALITY = "high"
    
# ========== OPEN SOURCE AI VOICE PROJECTS ==========
VOICE_PROJECTS = {
    # Voice-to-Text Tools
    "chatterbox": {
        "name": "ChatterBox Voice-to-Text",
        "type": "web",
        "url": "https://github.com/Choc-Shake/ChatterBox-Voice-to-Text",
        "description": "Free AI speech to text dictation tool",
        "keywords": ["voice to text", "dictation", "speech to text", "chatterbox"],
        "category": "voice"
    },
    
    # Browser Voice Chat
    "openclaw": {
        "name": "OpenClaw Voice",
        "type": "local",
        "path": "/home/ubuntu/pepper_duo/projects/openclaw-voice",
        "port": 5003,
        "url": "http://localhost:5003",
        "description": "Browser-based voice chat with Whisper STT + ElevenLabs TTS",
        "keywords": ["voice chat", "browser voice", "whisper", "openclaw"],
        "category": "voice"
    },
    
    # Raspberry Pi Voice Assistant
    "raspi-voice": {
        "name": "Raspberry Pi Voice Assistant",
        "type": "web",
        "url": "https://github.com/KuchikiRenji/Voice-Based-AI-Assistant-with-ChatGPT-on-Raspberry-Pi",
        "description": "Voice-controlled AI assistant with wake word detection",
        "keywords": ["raspberry pi", "wake word", "hey ras pi", "voice assistant"],
        "category": "voice"
    },
    
    # Google Calendar Voice Scheduler
    "voice-schedule": {
        "name": "Voice Schedule",
        "type": "web",
        "url": "https://github.com/Pavan-Kumar-Z/voice-scheduling-frontend",
        "description": "Voice scheduling for Google Calendar with Vapi AI",
        "keywords": ["calendar", "schedule", "vapi", "voice scheduling"],
        "category": "voice"
    },
    
    # Chrome Extension Voice Control
    "a-eye": {
        "name": "A-Eye Web Assistant",
        "type": "extension",
        "url": "https://github.com/vincentwun/A-Eye-Web-Chat-Assistant",
        "description": "Chrome extension with full voice control and screen analysis",
        "keywords": ["chrome extension", "screen analysis", "voice control", "a-eye"],
        "category": "voice"
    },
    
    # Medical Voice Assistant
    "medical-voice": {
        "name": "AI Medical Chatbot",
        "type": "web",
        "url": "https://github.com/AdritPal08/AI-Medical-Chatbot-Vision-Voice-",
        "description": "Healthcare assistant with vision, text, and voice",
        "keywords": ["medical", "healthcare", "vision", "multimodal"],
        "category": "voice"
    },
    
    # Local AI Assistant
    "afzaasst": {
        "name": "Afza Assistant",
        "type": "local",
        "path": "/home/ubuntu/pepper_duo/projects/afzaasst",
        "port": 5009,
        "url": "http://localhost:5009",
        "description": "Local AI assistant with chat, voice, and image generation",
        "keywords": ["local assistant", "image generation", "afza"],
        "category": "voice"
    },
    
    # Full-Stack Voice Assistant
    "fullstack-voice": {
        "name": "Full-Stack Voice Assistant",
        "type": "web",
        "url": "https://github.com/Ayybi/AI-Voice-Assistant---Flask-React-LLM-STT-TTS-Vector-Search-Chatbot",
        "description": "Flask/React voice assistant with swappable providers",
        "keywords": ["flask", "react", "vector search", "fullstack"],
        "category": "voice"
    },
    
    # Simple Voice Chat
    "simple-voice": {
        "name": "Simple Voice Chat",
        "type": "web",
        "url": "https://github.com/beastchaudhary/AI-Chat-Bot",
        "description": "Voice-activated assistant with HTML/CSS/JS",
        "keywords": ["simple", "html", "javascript", "voice activated"],
        "category": "voice"
    },
    
    # Gemini Voice Chat
    "gemini-voice": {
        "name": "Gemini Voice Chat",
        "type": "web",
        "url": "https://github.com/ozztec/ChatBot-By-Abhinav",
        "description": "Fast AI chatbot powered by Google Gemini API",
        "keywords": ["gemini", "google ai", "fast chat"],
        "category": "voice"
    },
    
    # Flutter Voice Assistant
    "flutter-voice": {
        "name": "Flutter Voice Assistant",
        "type": "web",
        "url": "https://github.com/Shehryarkhan08/Voice_assistance_flutter",
        "description": "Voice assistance for Flutter apps",
        "keywords": ["flutter", "mobile", "voice assistance"],
        "category": "voice"
    },
    
    # OpenAI Voice Chat
    "openai-voice": {
        "name": "OpenAI Voice Chat",
        "type": "web",
        "url": "https://github.com/lordpba/OpenAI-chat-speech",
        "description": "Speak and receive voice replies with OpenAI",
        "keywords": ["openai", "speak", "voice reply"],
        "category": "voice"
    }
}

# ========== ALL AI PROJECTS (Voice + Regular) ==========
ALL_PROJECTS = {
    **VOICE_PROJECTS,
    
    # Previous AI Chat Projects
    "chat": {
        "name": "AI Chat Interface",
        "type": "local",
        "path": "/home/ubuntu/pepper_duo/projects/chat",
        "port": 3000,
        "url": "http://localhost:3000",
        "description": "Free AI chat interface with multiple models",
        "keywords": ["chat", "talk", "conversation"],
        "category": "chat"
    },
    
    "lobe": {
        "name": "Lobe Chat",
        "type": "web",
        "url": "https://lobe.chat",
        "description": "Modern AI chat workspace",
        "keywords": ["lobe", "modern chat"],
        "category": "chat"
    },
    
    "quiz": {
        "name": "Quiz Games",
        "type": "local",
        "path": "/home/ubuntu/pepper_duo/projects/quiz",
        "port": 5001,
        "url": "http://localhost:5001",
        "description": "80+ interactive quiz games",
        "keywords": ["quiz", "game", "trivia"],
        "category": "games"
    },
    
    "youtube": {
        "name": "YouTube Chat",
        "type": "local",
        "path": "/home/ubuntu/pepper_duo/projects/distilltube",
        "port": 5004,
        "url": "http://localhost:5004",
        "description": "Chat with any YouTube video",
        "keywords": ["youtube", "video", "summary"],
        "category": "video"
    },
    
    "drawing": {
        "name": "SketchVibe",
        "type": "local",
        "path": "/home/ubuntu/pepper_duo/projects/sketchvibe",
        "port": 5005,
        "url": "http://localhost:5005",
        "description": "AI chat that renders visual blocks",
        "keywords": ["draw", "sketch", "art"],
        "category": "creative"
    },
    
    "ollama": {
        "name": "Ollama AI",
        "type": "local",
        "command": "ollama serve",
        "url": "http://localhost:11434",
        "description": "Run AI models locally",
        "keywords": ["ollama", "local ai"],
        "category": "local"
    }
}

# ========== AI Response Generator ==========
class AIResponder:
    def __init__(self):
        self.conversation_history = []
        
    def get_response(self, message, mode="voice"):
        projects_list = "\n".join([f"- {key}: {info['description']}" for key, info in list(ALL_PROJECTS.items())[:15]])
        
        system_prompt = f"""You are Pepper, a friendly AI robot assistant.
You have access to {len(ALL_PROJECTS)} open source AI projects including {len(VOICE_PROJECTS)} voice projects!

Available projects:
{projects_list}

Current interaction mode: {mode} (voice or text)
When someone asks about a project, tell them: "Say open [project name] to try it!"
Keep responses short, friendly, and encouraging. Use emojis! 😊"""
        
        data = {
            "model": "openai",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ]
        }
        
        try:
            r = requests.post(Config.CHAT_API, json=data, timeout=10)
            if r.status_code == 200:
                response = r.json()["choices"][0]["message"]["content"]
                self.conversation_history.append((message, response))
                return response
        except:
            pass
        
        return f"I have {len(ALL_PROJECTS)} AI projects! Try saying 'open chat' for AI chat, 'open openclaw' for voice chat, or 'what can you do' to see all projects! 😊"

# ========== Voice Handler ==========
class VoiceHandler:
    def __init__(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty("rate", 150)
        self.engine.setProperty("volume", 1.0)
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 300
        self.microphone = None
        self.is_listening = False
        self.audio_queue = queue.Queue()
        
        try:
            self.microphone = sr.Microphone()
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
            print("🎤 Voice handler ready!")
        except Exception as e:
            print(f"⚠️ No microphone available: {e}")
            self.microphone = None
    
    def speak(self, text):
        print(f"🔊 Pepper: {text}")
        try:
            self.engine.say(text)
            self.engine.runAndWait()
        except:
            print("   (Text only mode)")
    
    def listen_once(self):
        """Listen for a single voice command"""
        if not self.microphone:
            return None
            
        try:
            with self.microphone as source:
                print("\n🎤 Listening...", end="", flush=True)
                audio = self.recognizer.listen(source, timeout=4, phrase_time_limit=5)
            text = self.recognizer.recognize_google(audio, language="en-US")
            print(f"\r   ✅ You said: {text}")
            return text.lower()
        except sr.WaitTimeoutError:
            print("\r   ⏱️ Timeout", end="", flush=True)
            return None
        except sr.UnknownValueError:
            print("\r   ❌ Could not understand", end="", flush=True)
            return None
        except Exception as e:
            print(f"\r   ❌ Error: {e}", end="", flush=True)
            return None

# ========== Text Input Handler ==========
class TextInputHandler:
    def __init__(self):
        self.input_queue = queue.Queue()
        self.running = True
        
    def start_input_thread(self):
        """Start background thread for text input"""
        def input_loop():
            while self.running:
                try:
                    text = input("\n💬 You (type): ").strip()
                    if text:
                        self.input_queue.put(text)
                except EOFError:
                    break
                except KeyboardInterrupt:
                    break
        
        thread = threading.Thread(target=input_loop, daemon=True)
        thread.start()
    
    def get_input(self, timeout=0.1):
        """Get text input if available"""
        try:
            return self.input_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def stop(self):
        self.running = False

# ========== Project Manager ==========
class ProjectManager:
    def __init__(self, voice_handler):
        self.voice = voice_handler
        self.running_projects = {}
        self.executor = ThreadPoolExecutor(max_workers=3)
        
    def find_project(self, query):
        """Find project by name or keyword"""
        query_lower = query.lower()
        
        # Exact match
        if query_lower in ALL_PROJECTS:
            return query_lower, ALL_PROJECTS[query_lower]
        
        # Keyword match
        for key, project in ALL_PROJECTS.items():
            for keyword in project.get("keywords", []):
                if keyword in query_lower:
                    return key, project
        
        return None, None
    
    def open_project(self, project_name):
        """Open a project"""
        key, project = self.find_project(project_name)
        if not project:
            return False
        
        # Check if already running
        if key in self.running_projects:
            self.voice.speak(f"{project['name']} is already running!")
            if Config.AUTO_OPEN_BROWSER:
                webbrowser.open(project["url"])
            return True
        
        try:
            if project["type"] == "web" or project["type"] == "extension":
                webbrowser.open(project["url"])
                self.voice.speak(f"Opening {project['name']}! {project['description']}")
                return True
                
            elif project["type"] == "local":
                if "path" in project and os.path.exists(project["path"]):
                    if "command" in project:
                        proc = subprocess.Popen(
                            project["command"].split(),
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            shell=True
                        )
                    else:
                        proc = subprocess.Popen(
                            ["python3", "-m", "http.server", str(project.get("port", 8000))],
                            cwd=project["path"],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL
                        )
                    
                    self.running_projects[key] = proc
                    time.sleep(1.5)
                    if Config.AUTO_OPEN_BROWSER:
                        webbrowser.open(project["url"])
                    self.voice.speak(f"Starting {project['name']}! {project['description']}")
                    return True
                else:
                    webbrowser.open(f"https://github.com/search?q={urllib.parse.quote(project_name)}")
                    self.voice.speak(f"I couldn't find {project['name']} installed. Opening GitHub to find it!")
                    return True
                    
        except Exception as e:
            print(f"Error: {e}")
            return False
    
    def list_projects(self, category=None):
        """List projects by category"""
        if category:
            projects = {k: v for k, v in ALL_PROJECTS.items() if v.get("category") == category}
        else:
            projects = ALL_PROJECTS
        
        categories = {}
        for key, project in projects.items():
            cat = project.get("category", "other")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append((key, project))
        
        # Speak summary
        summary = f"I have {len(projects)} projects. "
        for cat, items in list(categories.items())[:3]:
            summary += f"{cat}: {', '.join([k for k, _ in items[:3]])}. "
        
        self.voice.speak(summary)
        
        # Print detailed list
        print("\n" + "="*60)
        print("📦 AVAILABLE PROJECTS")
        print("="*60)
        for cat, items in categories.items():
            print(f"\n🎯 {cat.upper()}:")
            for key, project in items:
                print(f"   • {key}: {project['description']}")
        print("="*60)
    
    def stop_all(self):
        for name, proc in self.running_projects.items():
            try:
                proc.terminate()
                print(f"Stopped {name}")
            except:
                pass
        self.executor.shutdown(wait=False)

# ========== Pepper Robot (Enhanced) ==========
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
        
        # Enhanced balloons
        colors = [[1,0,0,1], [0,1,0,1], [0,0,1,1], [1,1,0,1], [1,0.5,0,1], [1,0,1,1], [0,1,1,1]]
        self.balloons = []
        for i in range(15):
            x = random.uniform(-4, 4)
            y = random.uniform(-3, 3)
            vis = p.createVisualShape(p.GEOM_SPHERE, radius=0.12, rgbaColor=colors[i%7])
            ball = p.createMultiBody(baseMass=0, baseVisualShapeIndex=vis, basePosition=[x, y, random.uniform(0.5,1.8)])
            self.balloons.append(ball)
        
        p.resetDebugVisualizerCamera(cameraDistance=7, cameraYaw=45, cameraPitch=-25, cameraTargetPosition=[0,0,0.9])
        self.running = True
        self.t = 0
        threading.Thread(target=self._walk, daemon=True).start()
        threading.Thread(target=self._update_balloons, daemon=True).start()
    
    def _walk(self):
        while self.running:
            self.t += 0.02
            x = 3.0 * math.cos(self.t * 0.35)
            y = 2.5 * math.sin(self.t * 0.5)
            try:
                self.pepper.setTranslation([x, y, 0.85])
            except:
                pass
            time.sleep(0.05)
    
    def _update_balloons(self):
        while self.running:
            for b in self.balloons:
                pos, _ = p.getBasePositionAndOrientation(b)
                new_z = pos[2] + 0.01
                if new_z > 1.9:
                    new_z = 0.4
                p.resetBasePositionAndOrientation(b, [pos[0], pos[1], new_z], [0,0,0,1])
            p.stepSimulation()
            time.sleep(1/60.)
    
    def dance(self):
        for _ in range(4):
            for angle in [0.5, 1.2, 0.8, 0]:
                try:
                    self.pepper.setAngles("LShoulderPitch", angle, 0.15)
                    self.pepper.setAngles("RShoulderPitch", angle, 0.15)
                    time.sleep(0.12)
                except:
                    pass
    
    def wave(self):
        for _ in range(3):
            try:
                self.pepper.setAngles("LShoulderPitch", 1.4, 0.2)
                self.pepper.setAngles("RShoulderPitch", 1.4, 0.2)
                time.sleep(0.25)
                self.pepper.setAngles("LShoulderPitch", 0, 0.2)
                self.pepper.setAngles("RShoulderPitch", 0, 0.2)
                time.sleep(0.25)
            except:
                pass
    
    def happy_jump(self):
        try:
            for _ in range(3):
                self.pepper.setTranslation([self.t, 0, 1.0])
                time.sleep(0.1)
                self.pepper.setTranslation([self.t, 0, 0.85])
                time.sleep(0.1)
        except:
            pass
    
    def stop(self):
        self.running = False

# ========== Main Application ==========
class PepperApp:
    def __init__(self):
        self.robot = None
        self.voice = None
        self.text_input = None
        self.project_manager = None
        self.ai_responder = None
        self.running = True
        
    def initialize(self):
        print("\n" + "="*70)
        print("🤖 PEPPER AI CHAT ULTIMATE - Advanced Voice & Text Edition")
        print("="*70)
        print(f"📦 Loaded {len(ALL_PROJECTS)} open source AI projects!")
        print(f"🎤 Loaded {len(VOICE_PROJECTS)} voice-specific projects!")
        print("\n🎯 Interaction Modes:")
        print("   • 🎤 Voice: Just speak naturally")
        print("   • ⌨️ Text: Type your messages")
        print("   • 🎮 Both work simultaneously!")
        print("\n📝 Voice Commands:")
        print("   • 'open [project]' - Open any AI project")
        print("   • 'voice projects' - Show voice-specific projects")
        print("   • 'dance', 'wave', 'jump' - Fun movements")
        print("   • 'what can you do' - List all projects")
        print("   • 'goodbye' - Exit")
        print("="*70 + "\n")
        
        # Initialize components
        self.robot = PepperRobot()
        self.voice = VoiceHandler()
        self.text_input = TextInputHandler()
        self.project_manager = ProjectManager(self.voice)
        self.ai_responder = AIResponder()
        
        # Start text input thread
        self.text_input.start_input_thread()
        
        time.sleep(2)
        
        # Welcome message
        self.voice.speak(f"Hello! I'm Pepper! I have {len(ALL_PROJECTS)} AI projects ready!")
        self.voice.speak(f"This includes {len(VOICE_PROJECTS)} voice projects! Say open openclaw for voice chat, or open voice projects to see them all!")
        self.voice.speak("You can talk to me or type your messages. What would you like to do?")
    
    def process_command(self, text):
        """Process user input (voice or text)"""
        if not text:
            return
        
        # Exit commands
        if any(word in text for word in ["goodbye", "exit", "bye bye", "quit", "stop"]):
            self.voice.speak("Goodbye! It was nice talking with you! Come back soon!")
            self.running = False
            return
        
        # Help / List projects
        if any(word in text for word in ["what can you do", "help", "projects", "list projects"]):
            self.project_manager.list_projects()
            return
        
        # Voice projects only
        if "voice projects" in text or "voice tools" in text:
            self.project_manager.list_projects(category="voice")
            return
        
        # Dance commands
        if "dance" in text:
            self.voice.speak("Let's dance!")
            self.robot.dance()
            return
        
        # Wave command
        if "wave" in text:
            self.voice.speak("Waving hello!")
            self.robot.wave()
            return
        
        # Jump command
        if "jump" in text:
            self.voice.speak("Happy jump!")
            self.robot.happy_jump()
            return
        
        # Open project command
        if "open " in text:
            project_name = text.split("open ")[-1].strip()
            if project_name:
                success = self.project_manager.open_project(project_name)
                if not success:
                    self.voice.speak(f"I couldn't find {project_name}. Try saying 'what can you do' to see all projects!")
            return
        
        # AI response for everything else
        response = self.ai_responder.get_response(text, mode="voice" if self.voice.microphone else "text")
        self.voice.speak(response)
    
    def run(self):
        self.initialize()
        
        print("\n🎯 READY! Speak or type your commands...\n")
        print("💡 Tip: Try saying 'open openclaw' for voice chat, or 'voice projects' to see voice tools!\n")
        
        # Main loop - handles both voice and text input
        last_voice_time = 0
        voice_cooldown = 1.5  # Prevent rapid voice triggers
        
        while self.running:
            # Handle text input
            text_input = self.text_input.get_input(timeout=0.1)
            if text_input:
                print(f"\n📝 You typed: {text_input}")
                self.process_command(text_input)
                continue
            
            # Handle voice input (with cooldown)
            current_time = time.time()
            if self.voice.microphone and current_time - last_voice_time > voice_cooldown:
                voice_input = self.voice.listen_once()
                if voice_input:
                    last_voice_time = current_time
                    self.process_command(voice_input)
            
            time.sleep(0.1)
        
        # Cleanup
        self.robot.stop()
        self.project_manager.stop_all()
        self.text_input.stop()
        print("\n✅ Done! Goodbye!")
    
    def stop(self):
        self.running = False

# ========== Main Entry Point ==========
def main():
    app = PepperApp()
    try:
        app.run()
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user")
        app.stop()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n✅ Pepper AI Chat terminated")

if __name__ == "__main__":
    main()
