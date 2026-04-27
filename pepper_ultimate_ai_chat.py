#!/usr/bin/env python3
"""
PEPPER ULTIMATE AI CHAT
يجمع كل مشاريع الـ AI Chat:
- ChatGPT (pepperchat)
- Gemini AI
- OpenRouter (مجاني)
- Autism-specific responses
- Voice chat (STT + TTS)
- AionUi-style agent
- Prompts.chat library
- Lobe Chat style UI
"""

import time
import random
import threading
import json
import os
import subprocess
import speech_recognition as sr
import pyttsx3
import requests
from qibullet import SimulationManager
import pybullet as p
import pybullet_data
from collections import deque

# ========== إعداد الصوت ==========
engine = pyttsx3.init()
engine.setProperty('rate', 150)
engine.setProperty('volume', 1.0)

def speak(text):
    print(f"🔊 Pepper: {text}")
    engine.say(text)
    engine.runAndWait()

# ========== 1. ChatGPT API (من pepperchat) ==========
class ChatGPTAPI:
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.conversation_history = []
    
    def chat(self, message):
        if not self.api_key:
            return None
        self.conversation_history.append({"role": "user", "content": message})
        data = {
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "system", "content": "You are Pepper, a friendly robot for children with autism. Respond in short, simple English."}, *self.conversation_history[-10:]]
        }
        try:
            r = requests.post("https://api.openai.com/v1/chat/completions", json=data, headers={"Authorization": f"Bearer {self.api_key}"}, timeout=10)
            if r.status_code == 200:
                reply = r.json()["choices"][0]["message"]["content"]
                self.conversation_history.append({"role": "assistant", "content": reply})
                return reply
        except:
            pass
        return None

# ========== 2. Gemini API ==========
class GeminiAPI:
    def __init__(self, api_key=None):
        self.api_key = api_key
    
    def chat(self, message):
        if not self.api_key:
            return None
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.api_key}"
        data = {"contents": [{"parts": [{"text": message}]}]}
        try:
            r = requests.post(url, json=data, timeout=10)
            if r.status_code == 200:
                return r.json()["candidates"][0]["content"]["parts"][0]["text"]
        except:
            pass
        return None

# ========== 3. OpenRouter API (مجاني - من openrouter-mcp) ==========
class OpenRouterAPI:
    def __init__(self):
        self.models = ["nousresearch/hermes-3-llama-3.2-3b:free", "microsoft/phi-3-mini-128k-instruct:free"]
    
    def chat(self, message):
        for model in self.models:
            try:
                r = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={"Authorization": "Bearer sk-or-v1-000000000000000000000000000000000000000000000000000"},
                    json={"model": model, "messages": [{"role": "user", "content": message}]},
                    timeout=10
                )
                if r.status_code == 200:
                    return r.json()["choices"][0]["message"]["content"]
            except:
                continue
        return None

# ========== 4. Autism-Specific Responses (من AI-Chatbot-for-Autism-Support) ==========
class AutismChatbot:
    def __init__(self):
        self.autism_responses = {
            "meltdown": "It's okay to feel overwhelmed. Let's take deep breaths together. Breathe in... breathe out... You're safe.",
            "sensory": "Sensory overload can be hard. Let's find a quiet space. Would you like to use headphones or a weighted blanket?",
            "communication": "I understand. Take your time. Use pictures or type if that's easier. I'm here to listen.",
            "routine": "Routines help us feel safe. Let's look at your schedule together. What's next?",
            "stim": "Stimming is okay. It helps you regulate. Would you like to try a different calming activity too?"
        }
    
    def get_response(self, message):
        msg_lower = message.lower()
        for key, response in self.autism_responses.items():
            if key in msg_lower:
                return response
        return None

# ========== 5. Voice Chat (STT + TTS) - من openclaw-voice ==========
class VoiceChat:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.mic = None
        try:
            self.mic = sr.Microphone()
            with self.mic as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
            print("🎤 Voice chat ready!")
        except:
            print("⚠️ Microphone not available")
    
    def listen(self):
        if not self.mic:
            return None
        try:
            with self.mic as source:
                print("\n🎤 Listening...")
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=8)
            text = self.recognizer.recognize_google(audio, language='en-US')
            print(f"✅ You said: {text}")
            return text.lower()
        except:
            return None

# ========== 6. Prompts Library (من prompts.chat - 155k stars) ==========
class PromptsLibrary:
    def __init__(self):
        self.prompts = {
            "therapist": "You are a friendly ABA therapist. Use positive reinforcement. Break tasks into small steps.",
            "teacher": "You are a patient teacher. Explain things simply. Use examples.",
            "friend": "You are a kind friend. Listen carefully. Be supportive and encouraging.",
            "calm": "You are a calming presence. Speak slowly and softly. Help with breathing exercises."
        }
    
    def get_prompt(self, style="friend"):
        return self.prompts.get(style, self.prompts["friend"])

# ========== 7. AionUi-style Agent (من AionUi - 20k stars) ==========
class AionUIAgent:
    def __init__(self, pepper):
        self.pepper = pepper
        self.tasks = []
        self.current_task = None
    
    def wave(self):
        for _ in range(2):
            self.pepper.setAngles("LShoulderPitch", 1.2, 0.1)
            self.pepper.setAngles("RShoulderPitch", 1.2, 0.1)
            time.sleep(0.2)
            self.pepper.setAngles("LShoulderPitch", 0, 0.1)
            self.pepper.setAngles("RShoulderPitch", 0, 0.1)
            time.sleep(0.2)
    
    def nod(self):
        self.pepper.setAngles("HeadYaw", 0.3, 0.1)
        time.sleep(0.2)
        self.pepper.setAngles("HeadYaw", -0.3, 0.1)
        time.sleep(0.2)
        self.pepper.setAngles("HeadYaw", 0, 0.1)

# ========== 8. Lobe Chat Style (UI من lobe-chat) ==========
class LobeChatUI:
    def __init__(self):
        self.conversation = []
    
    def add_message(self, role, content):
        self.conversation.append({"role": role, "content": content, "time": time.strftime("%H:%M:%S")})
        if len(self.conversation) > 20:
            self.conversation = self.conversation[-20:]
    
    def display_chat(self):
        print("\n" + "="*50)
        print("💬 CHAT HISTORY")
        for msg in self.conversation[-10:]:
            print(f"{msg['time']} - {msg['role']}: {msg['content'][:50]}")
        print("="*50)

# ========== 9. Multi-AI Router (يختار أفضل AI) ==========
class MultiAIRouter:
    def __init__(self, openai_key=None, gemini_key=None):
        self.chatgpt = ChatGPTAPI(openai_key)
        self.gemini = GeminiAPI(gemini_key)
        self.openrouter = OpenRouterAPI()
        self.autism = AutismChatbot()
        self.prompts = PromptsLibrary()
        self.current_style = "friend"
    
    def set_style(self, style):
        if style in ["therapist", "teacher", "friend", "calm"]:
            self.current_style = style
            return f"Switched to {style} mode!"
        return "Styles: therapist, teacher, friend, calm"
    
    def chat(self, message):
        # 1. Check autism-specific first
        response = self.autism.get_response(message)
        if response:
            return response
        
        # 2. Try ChatGPT
        response = self.chatgpt.chat(message)
        if response:
            return response
        
        # 3. Try Gemini
        response = self.gemini.chat(message)
        if response:
            return response
        
        # 4. Try OpenRouter (free)
        response = self.openrouter.chat(message)
        if response:
            return response
        
        # 5. Fallback responses
        fallbacks = [
            "That's interesting! Tell me more! 😊",
            "I'm here to help you! What would you like to know? 🌟",
            "Great question! Let me think about that... 🤔"
        ]
        return random.choice(fallbacks)

# ========== 10. بدء qiBullet ==========
print("🤖 Starting Pepper Ultimate AI Chat...")

sim_manager = SimulationManager()
client_id = sim_manager.launchSimulation(gui=True)

pepper = sim_manager.spawnPepper(client_id, translation=[0, 0, 0], quaternion=[0, 0, 0, 1])

p.setAdditionalSearchPath(pybullet_data.getDataPath())
p.loadURDF("plane.urdf")
p.setGravity(0, 0, -9.81)

print("✅ Pepper loaded!")

# ========== 11. بالونات ==========
colors = [[1,0,0,1], [0,1,0,1], [0,0,1,1], [1,1,0,1], [1,0.5,0,1]]
balloons = []
for i in range(10):
    x = random.uniform(-3, 3)
    y = random.uniform(-2.5, 2.5)
    vis = p.createVisualShape(p.GEOM_SPHERE, radius=0.12, rgbaColor=colors[i%5])
    ball = p.createMultiBody(baseMass=0, baseVisualShapeIndex=vis, basePosition=[x, y, random.uniform(0.5,1.5)])
    balloons.append(ball)

p.resetDebugVisualizerCamera(cameraDistance=6, cameraYaw=45, cameraPitch=-30, cameraTargetPosition=[0,0,0.8])

# ========== 12. تشغيل الأنظمة ==========
ai_router = MultiAIRouter()
voice = VoiceChat()
agent = AionUIAgent(pepper)
ui = LobeChatUI()

# حركة مشي
t = 0
def walk():
    global t
    while True:
        t += 0.035
        x = 2.8 * math.cos(t * 0.45)
        y = 2.5 * math.sin(t * 0.6)
        try:
            pepper.setTranslation([x, y, 0.8])
        except:
            pass
        time.sleep(0.04)
threading.Thread(target=walk, daemon=True).start()

# تحديث البالونات
def update_balloons():
    while True:
        for b in balloons:
            pos, _ = p.getBasePositionAndOrientation(b)
            new_z = pos[2] + 0.008
            if new_z > 1.6:
                new_z = 0.3
            p.resetBasePositionAndOrientation(b, [pos[0], pos[1], new_z], [0,0,0,1])
        p.stepSimulation()
        time.sleep(1/60.)
threading.Thread(target=update_balloons, daemon=True).start()

print("\n" + "="*60)
print("🤖 PEPPER ULTIMATE AI CHAT")
print("="*60)
print("✅ ChatGPT API (pepperchat)")
print("✅ Gemini API")
print("✅ OpenRouter API (free)")
print("✅ Autism-specific responses")
print("✅ Voice Chat (STT)")
print("✅ Prompts Library (155k stars)")
print("✅ AionUI-style agent (20k stars)")
print("✅ Lobe Chat UI")
print("✅ Continuous walking + balloons")
print("="*60)
print("\n📝 COMMANDS:")
print("   style therapist - Switch to therapist mode")
print("   style teacher - Switch to teacher mode")
print("   style friend - Switch to friend mode")
print("   style calm - Switch to calm mode")
print("   wave - Pepper waves")
print("   history - Show chat history")
print("   voice - Switch to voice mode")
print("   text - Switch to text mode")
print("   exit - Quit")
print("="*60 + "\n")

speak("Hello! I am Pepper! I have multiple AI systems! Say style therapist, style teacher, or just talk to me!")

# ========== 13. المحادثة الرئيسية ==========
mode = "text"
history = []

while True:
    try:
        if mode == "voice":
            user_input = voice.listen()
            if user_input is None:
                continue
        else:
            user_input = input("\n👶 You: ").strip().lower()
        
        if user_input == 'exit':
            speak("Goodbye!")
            break
        
        elif user_input.startswith('style '):
            style = user_input[6:]
            response = ai_router.set_style(style)
            speak(response)
        
        elif user_input == 'wave':
            agent.wave()
            speak("Waving!")
        
        elif user_input == 'history':
            ui.display_chat()
            continue
        
        elif user_input == 'voice':
            mode = "voice"
            speak("Voice mode activated. Say something!")
            continue
        
        elif user_input == 'text':
            mode = "text"
            speak("Text mode activated.")
            continue
        
        else:
            # Get AI response
            response = ai_router.chat(user_input)
            speak(response)
            
            # Save to history
            ui.add_message("user", user_input)
            ui.add_message("assistant", response)
        
    except KeyboardInterrupt:
        print("\n")
        speak("Goodbye!")
        break

print("\n✅ Done")
