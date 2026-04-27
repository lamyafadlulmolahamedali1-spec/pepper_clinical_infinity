#!/usr/bin/env python3
"""
Pepper AI Chat ULTIMATE - Complete Edition
- 50+ open source AI projects
- Autism support & mental health projects
- Voice + Text dual mode
- Educational & therapeutic tools
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
    AUTISM_SUPPORT_MODE = True  # Enable autism-friendly features

# ========== AUTISM SUPPORT PROJECTS ==========
AUTISM_PROJECTS = {
    # AI Chatbot for Autism Support
    "autism-chat": {
        "name": "AI Chatbot for Autism Support",
        "type": "web",
        "url": "https://github.com/Karem2422/AI-Chatbot-for-Autism-Support",
        "description": "Intelligent conversational agent with empathetic interaction patterns for autistic patients",
        "keywords": ["autism", "autism support", "empathetic", "therapy", "autism-chat"],
        "category": "autism",
        "features": ["Empathetic responses", "Patient interaction", "Therapy support"]
    },
    
    # Autism Support Framework
    "autism-framework": {
        "name": "AI Chatbot for Autism Support Framework",
        "type": "web",
        "url": "https://github.com/MirzaAzhar172/AI-CHATBOT-FOR-AUTISM-SUPPORT",
        "description": "Complete framework for AI chatbot supporting autism with website AI prompts",
        "keywords": ["autism", "framework", "ai prompts", "support"],
        "category": "autism",
        "features": ["Website integration", "AI prompts", "Support system"]
    },
    
    # Neurodivergent AI Companion
    "nd4i": {
        "name": "ND4I - AI Companion for Neurodivergent Individuals",
        "type": "web",
        "url": "https://github.com/AJAX6255/ND4I---AI-Companion-for-Neurodivergent-Individuals",
        "description": "Multimodal LLM that estimates and responds to interaction states for neurodivergent individuals",
        "keywords": ["neurodivergent", "adhd", "multimodal", "interaction states"],
        "category": "autism",
        "features": ["State estimation", "Multimodal AI", "Personalized responses"]
    },
    
    # NeuroAura - Neurodivergent App
    "neuroaura": {
        "name": "NeuroAura",
        "type": "web",
        "url": "https://github.com/f20250356-coder/neuroaura",
        "description": "React Native app for neurodivergent teens with ADHD, autism, sensory sensitivities",
        "keywords": ["neurodivergent", "teens", "adhd", "sensory", "mobile"],
        "category": "autism",
        "features": ["Mood check-ins", "Sensory tools", "Mobile app", "Teen focused"]
    },
    
    # AccessiTube AI - YouTube Accessibility
    "accessitube": {
        "name": "AccessiTube AI",
        "type": "web",
        "url": "https://github.com/AksharaaSharmaa/Neurodivergent_Support_Hub",
        "description": "AI assistant making YouTube videos accessible for neurodivergent individuals",
        "keywords": ["youtube", "accessibility", "adhd", "dyslexia", "video"],
        "category": "autism",
        "features": ["Video summaries", "Accessibility features", "ADHD support", "Dyslexia support"]
    },
    
    # Autism Support App
    "autism-app": {
        "name": "Autism Support App",
        "type": "web",
        "url": "https://github.com/nityajamdagni/autism-support-app",
        "description": "Full-stack web app for autism screening and parent guidance with voice features",
        "keywords": ["autism screening", "isaac", "parents", "guidance", "voice"],
        "category": "autism",
        "features": ["ISAA assessment", "Parent guidance", "Voice features", "Screening tools"]
    },
    
    # EmotiSense - Emotion Recognition
    "emotisense": {
        "name": "EmotiSense AI",
        "type": "web",
        "url": "https://github.com/VPPranav/EmotiSense-Face-Speech-Emotion-Recognition-Platform-for-Autism-Support-with-Conversational-Chatbot",
        "description": "Face and speech emotion recognition platform for autism support with conversational chatbot",
        "keywords": ["emotion recognition", "face detection", "speech emotion", "conversational"],
        "category": "autism",
        "features": ["Face emotion recognition", "Speech emotion analysis", "Conversational AI", "Therapy support"]
    },
    
    # Medical Assessment Chatbot
    "medical-assessment": {
        "name": "Medical Assessment Chatbot",
        "type": "web",
        "url": "https://github.com/khanndelwalharshit/Medical-Assessment-Chatbot",
        "description": "AI-powered chatbot for mental health self-assessment tests",
        "keywords": ["mental health", "assessment", "depression", "anxiety", "self-test"],
        "category": "autism",
        "features": ["Mental health tests", "Self-assessment", "Depression screening", "Anxiety screening"]
    },
    
    # ASD Detection Chatbot
    "asd-detection": {
        "name": "ASD Detection Chatbot",
        "type": "web",
        "url": "https://github.com/SeddikBbz/-Chatbot-for-ASD-Detection",
        "description": "Advanced chatbot for early detection of Autism Spectrum Disorder",
        "keywords": ["asd", "detection", "early detection", "screening"],
        "category": "autism",
        "features": ["Early detection", "ASD screening", "Interactive assessment"]
    },
    
    # AI Autism Screening Tool
    "autism-screening": {
        "name": "AI Autism Screening Tool",
        "type": "web",
        "url": "https://github.com/trashhh-me/AI-tool-for-Autism-Screening",
        "description": "AI tool combining Q-CHAT and computer vision for eye blink and gaze pattern analysis",
        "keywords": ["screening", "q-chat", "eye tracking", "gaze pattern", "computer vision"],
        "category": "autism",
        "features": ["Q-CHAT integration", "Eye tracking", "Gaze analysis", "Computer vision"]
    },
    
    # Chatbot for People with Autism
    "autism-assistant": {
        "name": "Chatbot for People with Autism",
        "type": "web",
        "url": "https://github.com/dagtades/Chatbot-for-People-with-Autism-",
        "description": "AI-powered chatbot to assist people with disabilities in accessing services and resources",
        "keywords": ["disability", "services", "resources", "assistance"],
        "category": "autism",
        "features": ["Service access", "Resource navigation", "Disability support"]
    },
    
    # Simple Autism Chatbot
    "simple-autism": {
        "name": "Simple Autism Chatbot",
        "type": "web",
        "url": "https://github.com/selva1826/ai-chatbot-for-autism",
        "description": "Simple AI chatbot designed for autism support",
        "keywords": ["simple", "basic", "easy"],
        "category": "autism",
        "features": ["Simple interface", "Easy to use", "Basic support"]
    },
    
    # Chatbot for Autism (TypeScript)
    "autism-ts": {
        "name": "Chatbot for Autism",
        "type": "web",
        "url": "https://github.com/HappySusan2016/Chatbot-for-autism",
        "description": "TypeScript-based AI chatbot for autism support",
        "keywords": ["typescript", "modern", "web"],
        "category": "autism",
        "features": ["TypeScript", "Modern web", "Accessible"]
    }
}

# ========== PREVIOUS PROJECTS (Voice, Chat, Games) ==========
VOICE_PROJECTS = {
    "openclaw": {
        "name": "OpenClaw Voice",
        "type": "web",
        "url": "https://github.com/Purple-Horizons/openclaw-voice",
        "description": "Browser-based voice chat with Whisper STT + ElevenLabs TTS",
        "keywords": ["voice chat", "browser voice", "whisper", "openclaw"],
        "category": "voice"
    },
    "chatterbox": {
        "name": "ChatterBox Voice-to-Text",
        "type": "web",
        "url": "https://github.com/Choc-Shake/ChatterBox-Voice-to-Text",
        "description": "Free AI speech to text dictation tool",
        "keywords": ["voice to text", "dictation", "speech to text"],
        "category": "voice"
    }
}

CHAT_PROJECTS = {
    "aionui": {
        "name": "AionUi - AI Cowork",
        "type": "web",
        "url": "https://github.com/iOfficeAI/AionUi",
        "description": "Free local 24/7 AI cowork app with multiple AI assistants",
        "keywords": ["cowork", "local", "assistant", "aion"],
        "category": "chat",
        "stars": "20.5k"
    },
    "prompts-chat": {
        "name": "Prompts.Chat",
        "type": "web",
        "url": "https://github.com/f/prompts.chat",
        "description": "Share, discover, and collect AI prompts from the community",
        "keywords": ["prompts", "community", "discover", "share"],
        "category": "chat",
        "stars": "155k"
    },
    "gemini-chat": {
        "name": "Gemini AI Chatbot",
        "type": "web",
        "url": "https://github.com/vadimgierko/gemini-ai-chatbot-next-js",
        "description": "Free Gemini AI chatbot with Firebase & Next.js",
        "keywords": ["gemini", "google", "firebase", "nextjs"],
        "category": "chat"
    },
    "openrouter-mcp": {
        "name": "OpenRouter MCP",
        "type": "web",
        "url": "https://github.com/stabgan/openrouter-mcp-multimodal",
        "description": "300+ LLM access with vision and image generation",
        "keywords": ["openrouter", "multimodal", "vision", "llm"],
        "category": "chat"
    },
    "lobe-chat": {
        "name": "Lobe Chat",
        "type": "web",
        "url": "https://github.com/jichenghan800/lobe-chat",
        "description": "Modern AI Agent Workspace with RAG support",
        "keywords": ["lobe", "agent", "rag", "workspace"],
        "category": "chat"
    },
    "duckduckgo-ai": {
        "name": "DuckDuckGo AI API",
        "type": "web",
        "url": "https://github.com/dhiaaeddine16/duckduckgo-ai-openai-api",
        "description": "Free AI chat with GPT-4, Claude, Llama models",
        "keywords": ["duckduckgo", "free", "gpt4", "claude"],
        "category": "chat"
    },
    "chaqgpt": {
        "name": "ChaqGPT",
        "type": "web",
        "url": "https://github.com/Amer-alsayed/chaqgpt",
        "description": "Free AI chat with DeepSeek R1, LLaMA, and more",
        "keywords": ["deepseek", "llama", "free", "chat"],
        "category": "chat"
    },
    "lanjam-chat": {
        "name": "Lanjam Chat",
        "type": "web",
        "url": "https://github.com/lanjam-ai/lanjam-chat",
        "description": "Private, self-hosted AI chat for families",
        "keywords": ["family", "private", "self-hosted", "safe"],
        "category": "chat"
    }
}

GAMES_PROJECTS = {
    "quizhp": {
        "name": "QuizHP MCP",
        "type": "web",
        "url": "https://github.com/bassimeledath/quizhp-mcp",
        "description": "80+ interactive quiz game templates for AI chat",
        "keywords": ["quiz", "games", "trivia", "interactive"],
        "category": "games"
    }
}

EDUCATION_PROJECTS = {
    "distilltube": {
        "name": "DistillTube",
        "type": "web",
        "url": "https://github.com/AliyaanZahid/DistillTube",
        "description": "Turn any YouTube video into a conversation",
        "keywords": ["youtube", "video", "summary", "chat"],
        "category": "education"
    },
    "rag-chatbot": {
        "name": "RAG Chatbot",
        "type": "web",
        "url": "https://github.com/BhushanSutar/RAG_CHATBOT_LANGGRAPH",
        "description": "Document Q&A with LangGraph and ChromaDB",
        "keywords": ["rag", "documents", "qa", "langgraph"],
        "category": "education"
    }
}

LOCAL_AI_PROJECTS = {
    "ollama-manager": {
        "name": "Ollama Manager",
        "type": "web",
        "url": "https://github.com/Aditharavind/Ollama-Manager",
        "description": "Desktop GUI for running AI models locally",
        "keywords": ["ollama", "gui", "local", "desktop"],
        "category": "local"
    },
    "offline-chatbot": {
        "name": "Offline Chatbot",
        "type": "web",
        "url": "https://github.com/mrmendoza-dev/offline-chatbot",
        "description": "ChatGPT style interface for offline LLMs",
        "keywords": ["offline", "private", "mistral", "local"],
        "category": "local"
    },
    "queai": {
        "name": "QueAI",
        "type": "web",
        "url": "https://github.com/queai-project/QueAI",
        "description": "Centralized access to local AI solutions",
        "keywords": ["local", "centralized", "solutions"],
        "category": "local"
    }
}

BROWSER_EXTENSIONS = {
    "a-eye": {
        "name": "A-Eye Web Assistant",
        "type": "extension",
        "url": "https://github.com/vincentwun/A-Eye-Web-Chat-Assistant",
        "description": "Chrome extension with full voice control and screen analysis",
        "keywords": ["chrome", "extension", "voice control", "screen analysis"],
        "category": "extension"
    },
    "raya": {
        "name": "RayaAI",
        "type": "extension",
        "url": "https://github.com/terminalskid/RayaAI",
        "description": "Right-click AI chat extension",
        "keywords": ["right click", "extension", "quick chat"],
        "category": "extension"
    },
    "open-pluck": {
        "name": "Open Pluck",
        "type": "extension",
        "url": "https://github.com/karan-ksrk/open-pluck",
        "description": "Highlight text and ask follow-up questions in ChatGPT/Claude",
        "keywords": ["highlight", "follow-up", "chatgpt", "claude"],
        "category": "extension"
    }
}

# ========== COMBINE ALL PROJECTS ==========
ALL_PROJECTS = {
    **AUTISM_PROJECTS,
    **VOICE_PROJECTS,
    **CHAT_PROJECTS,
    **GAMES_PROJECTS,
    **EDUCATION_PROJECTS,
    **LOCAL_AI_PROJECTS,
    **BROWSER_EXTENSIONS
}

# ========== AI RESPONDER WITH AUTISM AWARENESS ==========
class AIResponder:
    def __init__(self):
        self.conversation_history = []
        self.autism_mode = Config.AUTISM_SUPPORT_MODE
        
    def get_response(self, message, mode="voice"):
        # Special autism support response
        if self.autism_mode and any(word in message.lower() for word in ["autism", "asd", "support", "therapy", "screening"]):
            return self._get_autism_response(message)
        
        projects_count = len(ALL_PROJECTS)
        autism_count = len(AUTISM_PROJECTS)
        
        system_prompt = f"""You are Pepper, a friendly, empathetic AI robot assistant.
You have access to {projects_count} open source AI projects including {autism_count} autism support projects!

Autism Support Projects Available:
{', '.join(list(AUTISM_PROJECTS.keys())[:10])}

When someone mentions autism or asks for support, say: "I have special autism support tools! Try saying 'open autism-chat' or 'open emotisense' for emotion recognition."
Always be kind, patient, and encouraging. Use emojis to express emotions. 😊"""
        
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
        
        return self._get_fallback_response(message)
    
    def _get_autism_response(self, message):
        """Specialized responses for autism-related queries"""
        responses = [
            "I have many autism support tools! You can try 'open autism-chat' for empathetic conversations, 'open emotisense' for emotion recognition, or 'open nd4i' for neurodivergent support. Would you like me to open one? 😊",
            "That's an important topic. I have special AI tools for autism support including screening tools, emotion recognition, and therapy chatbots. Say 'open autism-chat' to get started! 💙",
            "I'm here to help! I can open autism support tools like EmotiSense for emotion recognition, NeuroAura for neurodivergent teens, or the ASD detection chatbot. Just say the name! 🌟"
        ]
        return random.choice(responses)
    
    def _get_fallback_response(self, message):
        autism_tools = "autism-chat, emotisense, neuroaura, nd4i"
        return f"I have {len(ALL_PROJECTS)} AI projects! For autism support, try: {autism_tools}. For voice chat, try 'open openclaw'. What would you like to explore? 😊"

# ========== VOICE HANDLER ==========
class VoiceHandler:
    def __init__(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty("rate", 150)
        self.engine.setProperty("volume", 1.0)
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 300
        self.microphone = None
        
        try:
            self.microphone = sr.Microphone()
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
            print("🎤 Voice handler ready!")
        except:
            self.microphone = None
            print("⚠️ No microphone - text only mode")
    
    def speak(self, text):
        print(f"🔊 Pepper: {text}")
        try:
            self.engine.say(text)
            self.engine.runAndWait()
        except:
            pass
    
    def listen_once(self):
        if not self.microphone:
            return None
        try:
            with self.microphone as source:
                print("\n🎤 Listening...", end="", flush=True)
                audio = self.recognizer.listen(source, timeout=4, phrase_time_limit=5)
            text = self.recognizer.recognize_google(audio, language="en-US")
            print(f"\r   ✅ You said: {text}")
            return text.lower()
        except:
            print("\r   ❌ Could not understand", end="", flush=True)
            return None

# ========== TEXT INPUT HANDLER ==========
class TextInputHandler:
    def __init__(self):
        self.input_queue = queue.Queue()
        self.running = True
        
    def start_input_thread(self):
        def input_loop():
            while self.running:
                try:
                    text = input("\n💬 You (type): ").strip()
                    if text:
                        self.input_queue.put(text)
                except:
                    break
        threading.Thread(target=input_loop, daemon=True).start()
    
    def get_input(self, timeout=0.1):
        try:
            return self.input_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def stop(self):
        self.running = False

# ========== PROJECT MANAGER ==========
class ProjectManager:
    def __init__(self, voice):
        self.voice = voice
        self.running_projects = {}
        
    def find_project(self, query):
        query_lower = query.lower()
        if query_lower in ALL_PROJECTS:
            return query_lower, ALL_PROJECTS[query_lower]
        for key, project in ALL_PROJECTS.items():
            for keyword in project.get("keywords", []):
                if keyword in query_lower:
                    return key, project
        return None, None
    
    def open_project(self, project_name):
        key, project = self.find_project(project_name)
        if not project:
            return False
        
        if key in self.running_projects:
            self.voice.speak(f"{project['name']} is already running!")
            webbrowser.open(project["url"])
            return True
        
        try:
            webbrowser.open(project["url"])
            self.voice.speak(f"Opening {project['name']}! {project['description']}")
            return True
        except:
            return False
    
    def list_projects(self, category=None):
        if category:
            projects = {k: v for k, v in ALL_PROJECTS.items() if v.get("category") == category}
        else:
            projects = ALL_PROJECTS
        
        print("\n" + "="*70)
        print(f"📦 AVAILABLE PROJECTS ({len(projects)} total)")
        print("="*70)
        
        categories = {}
        for key, project in projects.items():
            cat = project.get("category", "other")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append((key, project))
        
        for cat, items in categories.items():
            print(f"\n🎯 {cat.upper()} ({len(items)}):")
            for key, project in items[:8]:  # Show first 8 per category
                stars = project.get("stars", "")
                stars_str = f" ⭐{stars}" if stars else ""
                print(f"   • {key}: {project['description']}{stars_str}")
            if len(items) > 8:
                print(f"   ... and {len(items)-8} more")
        
        print("="*70)
        
        # Speak summary
        autism_count = len([p for p in projects.values() if p.get("category") == "autism"])
        self.voice.speak(f"I have {len(projects)} projects. {autism_count} autism support tools available!")
    
    def stop_all(self):
        for name in self.running_projects:
            print(f"Stopped {name}")
        self.running_projects.clear()

# ========== PEPPER ROBOT ==========
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
        
        # Autism-friendly colors (calming colors)
        colors = [[0.4,0.6,1,1], [0.6,0.8,1,1], [0.8,0.9,1,1], [0.5,0.7,1,1]]
        self.balloons = []
        for i in range(12):
            x = random.uniform(-3.5, 3.5)
            y = random.uniform(-3, 3)
            vis = p.createVisualShape(p.GEOM_SPHERE, radius=0.12, rgbaColor=colors[i%4])
            ball = p.createMultiBody(baseMass=0, baseVisualShapeIndex=vis, basePosition=[x, y, random.uniform(0.5,1.6)])
            self.balloons.append(ball)
        
        p.resetDebugVisualizerCamera(cameraDistance=7, cameraYaw=45, cameraPitch=-25, cameraTargetPosition=[0,0,0.9])
        self.running = True
        self.t = 0
        threading.Thread(target=self._walk, daemon=True).start()
        threading.Thread(target=self._update_balloons, daemon=True).start()
    
    def _walk(self):
        while self.running:
            self.t += 0.02
            x = 2.8 * math.cos(self.t * 0.35)
            y = 2.2 * math.sin(self.t * 0.5)
            try:
                self.pepper.setTranslation([x, y, 0.85])
            except:
                pass
            time.sleep(0.05)
    
    def _update_balloons(self):
        while self.running:
            for b in self.balloons:
                pos, _ = p.getBasePositionAndOrientation(b)
                new_z = pos[2] + 0.008
                if new_z > 1.8:
                    new_z = 0.4
                p.resetBasePositionAndOrientation(b, [pos[0], pos[1], new_z], [0,0,0,1])
            p.stepSimulation()
            time.sleep(1/60.)
    
    def dance(self):
        for _ in range(3):
            for angle in [0.4, 1.0, 0.4, 0]:
                try:
                    self.pepper.setAngles("LShoulderPitch", angle, 0.12)
                    self.pepper.setAngles("RShoulderPitch", angle, 0.12)
                    time.sleep(0.12)
                except:
                    pass
    
    def wave(self):
        for _ in range(2):
            try:
                self.pepper.setAngles("LShoulderPitch", 1.2, 0.2)
                self.pepper.setAngles("RShoulderPitch", 1.2, 0.2)
                time.sleep(0.25)
                self.pepper.setAngles("LShoulderPitch", 0, 0.2)
                self.pepper.setAngles("RShoulderPitch", 0, 0.2)
                time.sleep(0.25)
            except:
                pass
    
    def stop(self):
        self.running = False

# ========== MAIN APPLICATION ==========
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
        print("🤖 PEPPER AI CHAT ULTIMATE - Complete Edition")
        print("="*70)
        print(f"📦 Total Projects: {len(ALL_PROJECTS)}")
        print(f"🎗️ Autism Support: {len(AUTISM_PROJECTS)} specialized tools")
        print(f"🎤 Voice Projects: {len(VOICE_PROJECTS)}")
        print(f"💬 Chat Projects: {len(CHAT_PROJECTS)}")
        print(f"🎮 Games: {len(GAMES_PROJECTS)}")
        print(f"📚 Education: {len(EDUCATION_PROJECTS)}")
        print(f"💻 Local AI: {len(LOCAL_AI_PROJECTS)}")
        print(f"🔧 Extensions: {len(BROWSER_EXTENSIONS)}")
        print("\n🎯 Voice Commands:")
        print("   • 'open [project]' - Open any project")
        print("   • 'autism projects' - Show autism support tools")
        print("   • 'voice projects' - Show voice tools")
        print("   • 'what can you do' - List all projects")
        print("   • 'dance', 'wave' - Fun movements")
        print("="*70 + "\n")
        
        self.robot = PepperRobot()
        self.voice = VoiceHandler()
        self.text_input = TextInputHandler()
        self.project_manager = ProjectManager(self.voice)
        self.ai_responder = AIResponder()
        
        self.text_input.start_input_thread()
        time.sleep(2)
        
        self.voice.speak(f"Hello! I'm Pepper! I have {len(ALL_PROJECTS)} AI projects ready!")
        self.voice.speak(f"This includes {len(AUTISM_PROJECTS)} special autism support tools!")
        self.voice.speak("Say 'autism projects' to see them, or 'what can you do' for everything!")
    
    def process_command(self, text):
        if not text:
            return
        
        # Exit
        if any(word in text for word in ["goodbye", "exit", "bye bye", "quit"]):
            self.voice.speak("Goodbye! Take care! Come back anytime!")
            self.running = False
            return
        
        # Help
        if any(word in text for word in ["what can you do", "help", "projects"]):
            self.project_manager.list_projects()
            return
        
        # Autism projects
        if "autism projects" in text or "autism tools" in text:
            self.project_manager.list_projects(category="autism")
            return
        
        # Voice projects
        if "voice projects" in text:
            self.project_manager.list_projects(category="voice")
            return
        
        # Dance/Wave
        if "dance" in text:
            self.voice.speak("Let's dance!")
            self.robot.dance()
            return
        if "wave" in text:
            self.voice.speak("Waving hello!")
            self.robot.wave()
            return
        
        # Open project
        if "open " in text:
            project_name = text.split("open ")[-1].strip()
            success = self.project_manager.open_project(project_name)
            if not success:
                self.voice.speak(f"I couldn't find {project_name}. Try saying 'what can you do' to see all projects!")
            return
        
        # AI response
        response = self.ai_responder.get_response(text)
        self.voice.speak(response)
    
    def run(self):
        self.initialize()
        print("\n🎯 READY! Speak or type your commands...\n")
        print("💡 Try: 'autism projects' to see special tools, or 'open autism-chat' for empathetic support!\n")
        
        last_voice_time = 0
        voice_cooldown = 1.5
        
        while self.running:
            text_input = self.text_input.get_input(timeout=0.1)
            if text_input:
                print(f"\n📝 You typed: {text_input}")
                self.process_command(text_input)
                continue
            
            current_time = time.time()
            if self.voice.microphone and current_time - last_voice_time > voice_cooldown:
                voice_input = self.voice.listen_once()
                if voice_input:
                    last_voice_time = current_time
                    self.process_command(voice_input)
            
            time.sleep(0.1)
        
        self.robot.stop()
        self.project_manager.stop_all()
        self.text_input.stop()
        print("\n✅ Done!")

def main():
    app = PepperApp()
    try:
        app.run()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
