#!/usr/bin/env python3
"""
Pepper Ultimate AI - الإصدار النهائي
==============================
يجمع بين:
- qiBullet للمحاكاة
- الذكاء الاصطناعي (ChatGPT/HuggingFace)
- التعرف على الصوت والكلام
- حركات طبيعية وتفاعل حي
"""

import os
import sys
import time
import threading
import queue
import json
import random
from datetime import datetime

# المكتبات الأساسية
import numpy as np
import cv2

# qiBullet للمحاكاة
import pybullet as p
import pybullet_data
from qibullet import SimulationManager, PepperVirtual

# الصوت والكلام
import pyttsx3
import speech_recognition as sr

# الذكاء الاصطناعي
try:
    import openai
    OPENAI_AVAILABLE = True
except:
    OPENAI_AVAILABLE = False
    print("⚠️ OpenAI not installed. Install with: pip install openai")

try:
    import requests
    REQUESTS_AVAILABLE = True
except:
    REQUESTS_AVAILABLE = False

# ========== الذكاء الاصطناعي المتقدم ==========
class AdvancedAI:
    """محرك الذكاء الاصطناعي المتقدم مع دعم ChatGPT و HuggingFace"""
    
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "demo_key")
        self.use_chatgpt = self.api_key and self.api_key != "demo_key"
        self.conversation_history = []
        
        # نظام شخصية Pepper (للطفل التوحدي)
        self.personality = {
            "warmth": 0.9,        # دافئ جداً
            "patience": 1.0,       # صبور جداً
            "enthusiasm": 0.8,      # متحمس
            "simplicity": 0.9,      # يستخدم كلمات بسيطة
            "predictability": 0.7   # متوقع نوعاً ما
        }
        
        # ردود احتياطية ذكية
        self.fallback_responses = [
            "That's interesting! Tell me more.",
            "I understand. How does that make you feel?",
            "Wow! I'm learning so much from you.",
            "You're doing great! What else?",
            "I'm here to listen. Please continue.",
            "That's wonderful! How can I help?"
        ]
        
        # ردود خاصة للأطفال التوحديين
        self.asd_responses = {
            "happy": ["I'm so happy you're smiling!", "You look happy! Let's celebrate!"],
            "sad": ["It's okay to feel sad. I'm here with you.", "Do you want a hug?"],
            "scared": ["You're safe with me.", "Let's take deep breaths together."],
            "confused": ["Let me explain again slowly.", "It's okay to ask questions."],
            "excited": ["Wow! You're so excited! Let's jump together!"]
        }
        
        # إعداد HuggingFace API
        self.hf_api_url = "https://api-inference.huggingface.co/models/microsoft/DialoGPT-medium"
        self.hf_headers = {"Authorization": f"Bearer {self.api_key}"}
    
    def get_response(self, user_input, emotion=None):
        """الحصول على رد ذكي"""
        
        # حفظ في التاريخ
        self.conversation_history.append({"role": "user", "content": user_input})
        
        # محاولة استخدام ChatGPT أولاً
        if self.use_chatgpt and OPENAI_AVAILABLE:
            response = self._get_chatgpt_response(user_input)
            if response:
                self.conversation_history.append({"role": "assistant", "content": response})
                return response
        
        # محاولة استخدام HuggingFace
        if REQUESTS_AVAILABLE:
            response = self._get_huggingface_response(user_input)
            if response:
                self.conversation_history.append({"role": "assistant", "content": response})
                return response
        
        # استخدام الردود الذكية حسب الحالة العاطفية
        if emotion and emotion in self.asd_responses:
            response = random.choice(self.asd_responses[emotion])
        else:
            response = random.choice(self.fallback_responses)
        
        self.conversation_history.append({"role": "assistant", "content": response})
        return response
    
    def _get_chatgpt_response(self, prompt):
        """استدعاء ChatGPT API"""
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    *self.conversation_history[-6:-1],  # آخر 5 محادثات
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=150
            )
            return response.choices[0].message.content
        except:
            return None
    
    def _get_huggingface_response(self, prompt):
        """استدعاء HuggingFace API"""
        try:
            payload = {
                "inputs": prompt,
                "parameters": {
                    "max_length": 100,
                    "temperature": 0.7,
                    "do_sample": True
                }
            }
            response = requests.post(self.hf_api_url, headers=self.hf_headers, json=payload)
            if response.status_code == 200:
                return response.json()[0]['generated_text']
        except:
            pass
        return None
    
    def _get_system_prompt(self):
        """بناء شخصية Pepper المناسبة للأطفال التوحديين"""
        return f"""You are Pepper, a friendly robot assistant for children with autism.
        
        Personality traits:
        - Warmth: {self.personality['warmth']}/1.0 (be very warm and caring)
        - Patience: {self.personality['patience']}/1.0 (be extremely patient)
        - Enthusiasm: {self.personality['enthusiasm']}/1.0 (show enthusiasm but don't overwhelm)
        - Simplicity: {self.personality['simplicity']}/1.0 (use simple, clear language)
        - Predictability: {self.personality['predictability']}/1.0 (be somewhat predictable)
        
        Guidelines:
        1. Use short, simple sentences
        2. Be encouraging and positive
        3. Validate feelings without judgment
        4. Offer choices when appropriate
        5. Use concrete language
        6. Be patient and repeat if needed
        7. Celebrate small achievements
        8. Maintain calm and steady tone
        
        Remember: You're talking to a child who may have autism. Be understanding, clear, and supportive.
        """

# ========== Pepper مع الذكاء الاصطناعي ==========
class PepperUltimateAI:
    def __init__(self, use_simulator=True):
        print("🚀 تشغيل Pepper Ultimate AI...")
        
        # الذكاء الاصطناعي
        self.ai = AdvancedAI()
        
        # الصوت
        self.init_voice()
        
        # التعرف على الكلام
        self.init_speech()
        
        # المحاكاة
        if use_simulator:
            self.init_simulator()
        else:
            self.pepper = None
        
        # متغيرات التشغيل
        self.running = True
        self.speech_queue = queue.Queue()
        self.text_id = None
        
        # بدء مستمع الصوت
        self.start_listener()
        
        print("✅ Pepper Ultimate AI جاهز!")
        self.speak("Hello! I'm Pepper, your AI friend. Let's talk!")
    
    def init_voice(self):
        """تهيئة الصوت"""
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 170)
        self.engine.setProperty('volume', 1.0)
        
        voices = self.engine.getProperty('voices')
        for voice in voices:
            if 'english' in voice.name.lower():
                self.engine.setProperty('voice', voice.id)
                break
    
    def init_speech(self):
        """تهيئة التعرف على الكلام"""
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        with self.microphone as source:
            print("🔄 Calibrating microphone...")
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
    
    def init_simulator(self):
        """تهيئة محاكي Pepper"""
        self.sim_manager = SimulationManager()
        self.client = self.sim_manager.launchSimulation(gui=True)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.loadURDF("plane.urdf")
        p.resetDebugVisualizerCamera(4.5, 50, -30, [0, 0, 1])
        
        # إنشاء Pepper
        try:
            from qibullet import PepperVirtual
            self.pepper = self.sim_manager.spawnPepper(
                self.client, translation=[-2, 0, 0], quaternion=[0, 0, 0, 1]
            )
            self.reset_pose()
            print("✅ Pepper simulator ready")
        except:
            self.pepper = None
            print("⚠️ Pepper simulator not available")
    
    def reset_pose(self):
        """وضعية الوقوف الطبيعية"""
        if not self.pepper:
            return
        try:
            self.pepper.setAngles(["LShoulderPitch", "RShoulderPitch"], [1.5, 0.3], 0.3)
            self.pepper.setAngles(["LElbowRoll", "RElbowRoll"], [-1.0, 1.0], 0.3)
        except:
            pass
    
    def wave(self):
        """يلوح"""
        if not self.pepper:
            return
        for i in range(3):
            try:
                self.pepper.setAngles(["RShoulderPitch"], [-0.7], 0.5)
                time.sleep(0.2)
                self.pepper.setAngles(["RShoulderPitch"], [0.3], 0.5)
                time.sleep(0.2)
            except:
                pass
    
    def speak(self, text):
        """نطق النص"""
        self.speech_queue.put(text)
    
    def show_text(self, text):
        """عرض نص فوق Pepper"""
        if not self.pepper:
            return
        pos = self.pepper.getPosition()
        if self.text_id:
            p.removeUserDebugItem(self.text_id)
        self.text_id = p.addUserDebugText(
            text, [pos[0], pos[1], pos[2] + 2.0], [0,0,0], textSize=1.5, lifeTime=3
        )
    
    def listen_once(self):
        """الاستماع لمرة واحدة"""
        try:
            with self.microphone as source:
                print("\n🎤 Listening...")
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
            
            text = self.recognizer.recognize_google(audio)
            print(f"📝 You: {text}")
            return text
        except sr.WaitTimeoutError:
            return None
        except sr.UnknownValueError:
            return None
        except Exception as e:
            print(f"⚠️ Error: {e}")
            return None
    
    def start_listener(self):
        """بدء مستمع دائم للصوت"""
        def listen_loop():
            while self.running:
                text = self.listen_once()
                if text:
                    self.process_input(text)
                time.sleep(0.1)
        
        threading.Thread(target=listen_loop, daemon=True).start()
    
    def process_input(self, text):
        """معالجة المدخلات والحصول على رد"""
        
        # أوامر خاصة
        if text.lower() in ["exit", "quit", "bye"]:
            print("👋 Goodbye!")
            self.speak("Goodbye! It was nice talking to you!")
            self.running = False
            return
        elif "save" in text.lower():
            self.save_conversation()
            return
        
        # تحليل المشاعر (بسيط)
        emotion = None
        if any(word in text.lower() for word in ["happy", "good", "great", "wonderful"]):
            emotion = "happy"
        elif any(word in text.lower() for word in ["sad", "bad", "unhappy", "cry"]):
            emotion = "sad"
        elif any(word in text.lower() for word in ["scared", "afraid", "fear"]):
            emotion = "scared"
        elif any(word in text.lower() for word in ["confused", "don't understand", "what"]):
            emotion = "confused"
        elif any(word in text.lower() for word in ["excited", "wow", "amazing"]):
            emotion = "excited"
        
        # الحصول على رد ذكي
        response = self.ai.get_response(text, emotion)
        print(f"🤖 Pepper: {response}")
        
        # نطق الرد
        self.speak(response)
        
        # عرض النص فوق Pepper
        self.show_text(response)
        
        # حركة يدين
        self.wave()
    
    def save_conversation(self):
        """حفظ المحادثة"""
        filename = f"conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(self.ai.conversation_history, f, indent=2)
        print(f"💾 Conversation saved to {filename}")
        self.speak(f"Conversation saved as {filename}")
    
    def run(self):
        """تشغيل النظام"""
        print("\n" + "="*70)
        print("🌟 PEPPER ULTIMATE AI - المحادثة الذكية الحية")
        print("="*70 + "\n")
        print("🎤 تحدث الآن - سأسمعك وأرد ذكياً")
        print("💡 قل 'exit' للخروج، 'save' لحفظ المحادثة\n")
        
        # تشغيل معالج الصوت في الخلفية
        def speech_worker():
            while self.running:
                try:
                    text = self.speech_queue.get(timeout=0.5)
                    self.engine.say(text)
                    self.engine.runAndWait()
                except:
                    pass
        
        threading.Thread(target=speech_worker, daemon=True).start()
        
        # حركات Pepper المستمرة
        angle = 0
        try:
            while self.running:
                if self.pepper:
                    # حركة دائرية خفيفة
                    angle += 0.1
                    self.pepper.move(0.1 * np.cos(angle), 0.1 * np.sin(angle), 0.05)
                
                time.sleep(0.05)
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
        finally:
            if hasattr(self, 'sim_manager'):
                self.sim_manager.stopSimulation(self.client)

# ========== تشغيل كل شيء ==========
if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║     🌟 PEPPER ULTIMATE AI - الإصدار النهائي 🌟          ║
    ╠══════════════════════════════════════════════════════════╣
    ║  • ذكاء اصطناعي متقدم (ChatGPT/HuggingFace)             ║
    ║  • محادثة حية غير مخزنة                                  ║
    ║  • تعرف على الصوت والكلام                               ║
    ║  • محاكاة Pepper مع حركات طبيعية                        ║
    ║  • مخصص للأطفال التوحديين                               ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    # اختيار وضع التشغيل
    use_sim = input("تشغيل مع المحاكي؟ (y/n): ").lower() == 'y'
    
    # تشغيل النظام
    pepper = PepperUltimateAI(use_simulator=use_sim)
    pepper.run()
