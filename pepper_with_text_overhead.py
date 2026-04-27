#!/usr/bin/env python3
"""
Pepper with Text Overhead - بيبر مع ظهور الكلام فوق الرأس
يستخدم qiBullet ويضيف خاصية عرض النص فوق رأس Pepper
"""

import os
import sys
import time
import threading
import queue
import random
from datetime import datetime

# المكتبات الأساسية
import numpy as np

# qiBullet للمحاكاة
import pybullet as p
import pybullet_data
from qibullet import SimulationManager, PepperVirtual

# الصوت والكلام
import pyttsx3
import speech_recognition as sr

# الذكاء الاصطناعي
try:
    import requests
    REQUESTS_AVAILABLE = True
except:
    REQUESTS_AVAILABLE = False

# API للذكاء الاصطناعي
CHAT_API = "https://text.pollinations.ai/v1/chat/completions"

class TextOverhead:
    """إدارة عرض النص فوق رأس Pepper"""
    def __init__(self, pepper):
        self.pepper = pepper
        self.current_text_id = None
        self.message_queue = queue.Queue()
        self.is_running = True
        self.text_thread = threading.Thread(target=self._text_worker, daemon=True)
        self.text_thread.start()
    
    def _text_worker(self):
        """عرض النصوص في PyBullet"""
        while self.is_running:
            try:
                text, duration = self.message_queue.get(timeout=0.1)
                self._show_text(text, duration)
            except queue.Empty:
                continue
    
    def _show_text(self, text, duration=4):
        """عرض النص فوق رأس Pepper"""
        # الحصول على موقع Pepper
        if self.pepper:
            position = self.pepper.getPosition()
            # وضع النص فوق الرأس (ارتفاع 1.3 متر)
            text_position = [position[0], position[1], position[2] + 1.3]
        else:
            text_position = [0, 0, 1.3]
        
        # إزالة النص القديم
        if self.current_text_id:
            try:
                p.removeUserDebugItem(self.current_text_id)
            except:
                pass
        
        # عرض النص الجديد
        self.current_text_id = p.addUserDebugText(
            text[:60],  # حد طول النص
            text_position,
            [1, 0.8, 0],  # لون برتقالي-أصفر
            textSize=1.2,
            lifeTime=duration
        )
        
        # طباعة في التيرمنال
        print(f"💬 Pepper: {text}")
    
    def show_text(self, text, duration=4):
        """وضع نص في قائمة الانتظار للعرض"""
        self.message_queue.put((text, duration))
    
    def stop(self):
        self.is_running = False

class VoiceEngine:
    """محرك الصوت"""
    def __init__(self):
        try:
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', 150)
            self.engine.setProperty('volume', 0.9)
            voices = self.engine.getProperty('voices')
            for voice in voices:
                if 'english' in voice.name.lower():
                    self.engine.setProperty('voice', voice.id)
                    break
            self.lock = threading.Lock()
            self.available = True
        except:
            print("⚠️ Voice engine not available")
            self.available = False
    
    def speak(self, text):
        if not self.available:
            print(f"🔊 (would say): {text}")
            return
        def _speak():
            with self.lock:
                self.engine.say(text)
                self.engine.runAndWait()
        threading.Thread(target=_speak, daemon=True).start()

class AIEngine:
    """محرك الذكاء الاصطناعي"""
    def __init__(self):
        self.last_request_time = 0
    
    def get_response(self, message):
        """الحصول على رد من الذكاء الاصطناعي"""
        import time
        time_since_last = time.time() - self.last_request_time
        if time_since_last < 2:
            time.sleep(2 - time_since_last)
        
        data = {
            "model": "openai",
            "messages": [
                {"role": "system", "content": "You are Pepper, a friendly robot for children. Respond in short, simple ENGLISH sentences. Be kind and encouraging. Keep responses to 1-2 sentences."},
                {"role": "user", "content": message}
            ]
        }
        
        try:
            response = requests.post(CHAT_API, json=data, timeout=15)
            self.last_request_time = time.time()
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            else:
                return "Sorry, I'm having trouble. Please try again."
        except Exception as e:
            return "Sorry, I can't connect right now. Please check your internet."

class PepperWithText:
    """Pepper مع ظهور النص فوق الرأس"""
    
    def __init__(self):
        self.simulation_manager = None
        self.pepper = None
        self.text_overhead = None
        self.voice = VoiceEngine()
        self.ai = AIEngine()
        self.running = True
        self.conversation_history = []
        
        # إعداد qiBullet
        self.setup_simulation()
        
        # إعداد عرض النص
        if self.pepper:
            self.text_overhead = TextOverhead(self.pepper)
        
        print("\n" + "="*60)
        print("🤖 Pepper with Text Overhead is READY!")
        print("   Pepper will display text above his head")
        print("   You can chat with him by typing in the terminal")
        print("="*60)
    
    def setup_simulation(self):
        """إعداد qiBullet وتحميل Pepper"""
        try:
            self.simulation_manager = SimulationManager()
            
            # إطلاق المحاكاة
            self.client = self.simulation_manager.launchSimulation(gui=True)
            p.setRealTimeSimulation(1)
            
            # تحميل Pepper
            self.pepper = self.simulation_manager.spawnPepper(self.client, spawn_ground=True)
            
            # تحريك Pepper إلى موقع مناسب
            self.pepper.setPosition([0, 0, 0.8])
            self.pepper.goToPosture("Stand", 0.5)
            
            print("✅ Pepper loaded successfully in qiBullet!")
            
        except Exception as e:
            print(f"❌ Error loading Pepper: {e}")
            self.pepper = None
    
    def move_arms(self, angle=0.8):
        """تحريك أذرع Pepper"""
        if not self.pepper:
            return
        try:
            # استخدام qiBullet لتحريك الذراعين
            self.pepper.setAngles("LShoulderPitch", angle, 0.5)
            self.pepper.setAngles("RShoulderPitch", angle, 0.5)
        except:
            pass
    
    def wave_arms(self):
        """جعل Pepper يلوح بذراعيه"""
        for _ in range(3):
            self.move_arms(1.2)
            time.sleep(0.2)
            self.move_arms(0.5)
            time.sleep(0.2)
        self.move_arms(0)
    
    def show_text(self, text, duration=5):
        """عرض نص فوق رأس Pepper"""
        if self.text_overhead:
            self.text_overhead.show_text(text, duration)
        else:
            print(f"💬 Pepper: {text}")
    
    def speak(self, text):
        """نطق النص"""
        self.voice.speak(text)
        self.show_text(text, 5)
    
    def get_user_input(self):
        """الحصول على إدخال من المستخدم"""
        try:
            user_input = input("\n👶 You: ").strip()
            return user_input
        except:
            return None
    
    def process_input(self, user_input):
        """معالجة إدخال المستخدم"""
        if user_input.lower() in ['exit', 'quit', 'bye', 'goodbye']:
            self.show_text("Goodbye! It was nice talking with you! 👋", 4)
            self.wave_arms()
            return False
        
        if user_input.lower() == 'wave':
            self.wave_arms()
            return True
        
        if not user_input:
            return True
        
        print(f"👶 You: {user_input}")
        
        # تفكير
        self.show_text("🤔 Thinking...", 1.5)
        self.move_arms(0.5)
        
        # الحصول على رد من الذكاء الاصطناعي
        response = self.ai.get_response(user_input)
        
        # عرض الرد
        self.speak(response)
        
        # تسجيل المحادثة
        self.conversation_history.append({
            "user": user_input,
            "pepper": response,
            "time": datetime.now().strftime("%H:%M:%S")
        })
        
        return True
    
    def run_chat(self):
        """تشغيل المحادثة"""
        self.speak("Hello! I am Pepper! How can I help you today?")
        self.wave_arms()
        
        # دورة المحادثة
        while self.running:
            user_input = self.get_user_input()
            if user_input is None:
                continue
            
            self.running = self.process_input(user_input)
        
        print("\n👋 Session ended")
    
    def cleanup(self):
        """تنظيف"""
        if self.text_overhead:
            self.text_overhead.stop()
        if self.simulation_manager:
            self.simulation_manager.stopSimulation()
        print("✅ Cleanup done")

if __name__ == "__main__":
    pepper = PepperWithText()
    try:
        pepper.run_chat()
    finally:
        pepper.cleanup()
