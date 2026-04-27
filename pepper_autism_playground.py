#!/usr/bin/env python3
"""
Pepper في غرفة مع أطفال توحديين (Peppers) + ذكاء اصطناعي
- 5 Peppers كأطفال بمشاعر مختلفة
- محادثة حقيقية عبر ChatGPT
- حركات طبيعية وتفاعل
"""

import time
import pybullet as p
import pybullet_data
import threading
import random
import math
import queue
from qibullet import SimulationManager
import pyttsx3
import speech_recognition as sr
import openai
import os

# ========== إعداد الذكاء الاصطناعي ==========
# ضعي مفتاح API هنا (أو استخدمي متغير البيئة)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "YOUR_API_KEY_HERE")
openai.api_key = OPENAI_API_KEY

class AIAssistant:
    def __init__(self):
        self.conversation_history = []
        self.personality = """You are Pepper, a friendly robot assistant in a playroom with children who have autism.
        Your name is Pepper. You are patient, warm, and encouraging.
        Use simple, clear language. Be supportive and understanding.
        If the child seems upset, comfort them. If they're happy, celebrate with them.
        Keep responses short (1-2 sentences) and positive.
        The children's names are: Emma, Liam, Sophia, Noah, Mia (each is a Pepper robot).
        """
        
    def get_response(self, user_input, child_name=None):
        """الحصول على رد من الذكاء الاصطناعي"""
        try:
            context = f"Talking to {child_name if child_name else 'someone'}: {user_input}"
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": self.personality},
                    {"role": "user", "content": context}
                ],
                temperature=0.7,
                max_tokens=100
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"⚠️ AI Error: {e}")
            return random.choice([
                "That's nice!",
                "I understand.",
                "Tell me more!",
                "You're doing great!"
            ])

# ========== محرك الصوت ==========
class VoiceEngine:
    def __init__(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 170)
        voices = self.engine.getProperty('voices')
        for voice in voices:
            if 'english' in voice.name.lower():
                self.engine.setProperty('voice', voice.id)
                break
        self.lock = threading.Lock()
    
    def speak(self, text):
        def _speak():
            with self.lock:
                self.engine.say(text)
                self.engine.runAndWait()
        threading.Thread(target=_speak, daemon=True).start()

# ========== الميكروفون ==========
class MicrophoneListener:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.mic = None
        try:
            self.mic = sr.Microphone()
            with self.mic as source:
                print("🔄 معايرة الميكروفون...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
            print("✅ الميكروفون جاهز")
        except Exception as e:
            print(f"⚠️ مشكلة في الميكروفون: {e}")
    
    def listen(self, timeout=2):
        if not self.mic:
            return None
        try:
            with self.mic as source:
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=5)
            text = self.recognizer.recognize_google(audio)
            return text
        except:
            return None

# ========== طفل Pepper ==========
class PepperKid:
    def __init__(self, name, age, personality, color, position, sim_manager, client):
        self.name = name
        self.age = age
        self.personality = personality  # happy, shy, curious, etc.
        self.color = color
        self.position = position
        self.sim_manager = sim_manager
        self.client = client
        self.mood = "happy"
        self.energy = 100
        self.last_action = time.time()
        
        # إنشاء Pepper كطفل
        self.pepper = sim_manager.spawnPepper(
            client, translation=position, quaternion=[0, 0, 0, 1]
        )
        
        # تلوينه (من خلال إضافة أضواء ملونة)
        self.add_color_effect()
        
        print(f"✅ طفل Pepper: {name} ({age} yrs) - {personality}")
    
    def add_color_effect(self):
        """إضافة تأثير لوني للطفل (بديل عن التلوين)"""
        # نضيف كرات ملونة حوله للتمييز
        offset = 0.5
        vis_id = p.createVisualShape(p.GEOM_SPHERE, radius=0.1, rgbaColor=self.color)
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=vis_id,
                          basePosition=[self.position[0] + offset, self.position[1], self.position[2] + 1.0])
    
    def move_random(self):
        """حركة عشوائية حسب الشخصية"""
        if self.personality == "shy":
            move_prob = 0.01  # يتحرك قليلاً
        elif self.personality == "hyper":
            move_prob = 0.05  # يتحرك كثيراً
        else:
            move_prob = 0.02
        
        if random.random() < move_prob:
            dx = random.uniform(-0.2, 0.2)
            dy = random.uniform(-0.2, 0.2)
            new_pos = [self.position[0] + dx, self.position[1] + dy, self.position[2]]
            
            # حدود الغرفة
            if abs(new_pos[0]) < 4 and abs(new_pos[1]) < 4:
                self.position = new_pos
                # تحديث موقع Pepper
                p.resetBasePositionAndOrientation(self.pepper, self.position, [0,0,0,1])
    
    def get_mood_text(self):
        """نص حسب المزاج"""
        moods = {
            "happy": "😊",
            "sad": "😢",
            "curious": "🤔",
            "excited": "🎉",
            "shy": "☺️"
        }
        return moods.get(self.personality, "😐")

# ========== الغرفة ==========
class PlayRoom:
    def __init__(self):
        # أرضية
        floor_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[5, 5, 0.1], 
                                        rgbaColor=[0.8, 0.8, 0.8, 1])
        p.createMultiBody(baseVisualShapeIndex=floor_vis, basePosition=[0, 0, 0])
        
        # سجادة ملونة
        carpet_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[4, 4, 0.05], 
                                         rgbaColor=[0.3, 0.5, 0.8, 1])
        p.createMultiBody(baseVisualShapeIndex=carpet_vis, basePosition=[0, 0, 0.05])
        
        # جدران
        wall_color = [0.9, 0.9, 0.9, 1]
        wall_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[5, 0.2, 3], rgbaColor=wall_color)
        p.createMultiBody(baseVisualShapeIndex=wall_vis, basePosition=[0, -5, 1.5])
        p.createMultiBody(baseVisualShapeIndex=wall_vis, basePosition=[0, 5, 1.5])
        
        wall_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.2, 5, 3], rgbaColor=wall_color)
        p.createMultiBody(baseVisualShapeIndex=wall_vis, basePosition=[5, 0, 1.5])
        p.createMultiBody(baseVisualShapeIndex=wall_vis, basePosition=[-5, 0, 1.5])
        
        # ألعاب
        self.add_toys()
    
    def add_toys(self):
        """إضافة ألعاب ملونة"""
        toys = [
            ([1, 1, 0.2], [1,0,0,1]),   # كرة حمراء
            ([-1, 2, 0.2], [0,1,0,1]),  # كرة خضراء
            ([2, -1, 0.2], [0,0,1,1]),  # كرة زرقاء
            ([-2, -1, 0.2], [1,1,0,1])  # مكعب أصفر
        ]
        
        for pos, color in toys:
            vis_id = p.createVisualShape(p.GEOM_SPHERE, radius=0.15, rgbaColor=color)
            p.createMultiBody(baseMass=0.1, baseVisualShapeIndex=vis_id, basePosition=pos)

# ========== Pepper الرئيسي ==========
class MainPepper:
    def __init__(self):
        print("🚀 تشغيل Pepper في غرفة مع أطفال توحديين...")
        
        # الذكاء الاصطناعي
        self.ai = AIAssistant()
        
        # الصوت
        self.voice = VoiceEngine()
        
        # الميكروفون
        self.mic = MicrophoneListener()
        
        # المحاكي
        self.sim_manager = SimulationManager()
        self.client = self.sim_manager.launchSimulation(gui=True)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.loadURDF("plane.urdf")
        
        # الغرفة
        self.room = PlayRoom()
        
        # Pepper الرئيسي
        self.main_pepper = self.sim_manager.spawnPepper(
            self.client, translation=[-3, -3, 0.2], quaternion=[0, 0, 0, 1]
        )
        
        # أطفال Pepper
        self.kids = self.create_kids()
        
        # مسار الحركة
        self.setup_path()
        
        # قائمة المحادثات
        self.conversation_queue = queue.Queue()
        
        # بدء الاستماع
        self.start_listening()
        
        print("✅ Pepper جاهز!")
        self.voice.speak("Hello everyone! Let's play together!")

    def create_kids(self):
        """إنشاء أطفال Pepper بشخصيات مختلفة"""
        kids_data = [
            ("Emma", 4, "happy", [1, 1, 0.8, 1], [2, 2, 0.2]),
            ("Liam", 5, "curious", [0.8, 1, 1, 1], [-2, 3, 0.2]),
            ("Sophia", 3, "shy", [1, 0.8, 1, 1], [3, -2, 0.2]),
            ("Noah", 6, "excited", [1, 1, 0.5, 1], [-3, -2, 0.2]),
            ("Mia", 4, "happy", [0.8, 0.8, 1, 1], [0, 4, 0.2])
        ]
        
        kids = []
        for name, age, personality, color, pos in kids_data:
            kid = PepperKid(name, age, personality, color, pos, self.sim_manager, self.client)
            kids.append(kid)
        
        return kids

    def setup_path(self):
        """نقاط تجوال Pepper"""
        self.walk_points = [
            [-3, -3, 0.2],
            [3, -3, 0.2],
            [3, 3, 0.2],
            [-3, 3, 0.2],
            [0, 0, 0.2]
        ]
        self.current_point = 0

    def move_to_point(self, target):
        current = self.main_pepper.getPosition()
        dx = target[0] - current[0]
        dy = target[1] - current[1]
        dist = math.sqrt(dx*dx + dy*dy)
        
        if dist > 0.3:
            self.main_pepper.move(0.15 * dx / dist, 0, 0.1 * math.atan2(dy, dx))
            return False
        return True

    def find_nearest_kid(self):
        """العثور على أقرب طفل"""
        pos = self.main_pepper.getPosition()
        nearest = None
        min_dist = float('inf')
        
        for kid in self.kids:
            dx = kid.position[0] - pos[0]
            dy = kid.position[1] - pos[1]
            dist = math.sqrt(dx*dx + dy*dy)
            if dist < min_dist:
                min_dist = dist
                nearest = kid
        
        return nearest, min_dist

    def wave(self):
        for i in range(2):
            self.main_pepper.setAngles(["RShoulderPitch"], [-0.7], 0.5)
            time.sleep(0.2)
            self.main_pepper.setAngles(["RShoulderPitch"], [0.3], 0.5)
            time.sleep(0.2)

    def show_text(self, text):
        pos = self.main_pepper.getPosition()
        p.addUserDebugText(text, [pos[0], pos[1], pos[2] + 2.0], [0,0,0], textSize=1.2, lifeTime=3)

    def talk_to_kid(self, kid):
        """التحدث مع طفل باستخدام الذكاء الاصطناعي"""
        prompt = f"You are talking to {kid.name}, a {kid.age}-year-old child with {kid.personality} personality."
        response = self.ai.get_response(f"Say something friendly to {kid.name}", kid.name)
        
        print(f"🤖 Pepper: {response}")
        self.voice.speak(response)
        self.show_text(response)
        self.wave()

    def start_listening(self):
        """بدء الاستماع في الخلفية"""
        def listen_loop():
            while True:
                text = self.mic.listen(timeout=1)
                if text:
                    print(f"📝 You: {text}")
                    self.conversation_queue.put(text)
                time.sleep(0.1)
        
        threading.Thread(target=listen_loop, daemon=True).start()

    def process_user_input(self, text):
        """معالجة مدخلات المستخدم"""
        # تحديد أقرب طفل
        nearest_kid, dist = self.find_nearest_kid()
        kid_name = nearest_kid.name if nearest_kid and dist < 3 else None
        
        response = self.ai.get_response(text, kid_name)
        print(f"🤖 Pepper: {response}")
        self.voice.speak(response)
        self.show_text(response)
        self.wave()

    def run(self):
        print("\n" + "="*70)
        print("🌟 PEPPER مع أطفال توحديين (Peppers) + ذكاء اصطناعي")
        print("="*70 + "\n")
        print("🎤 تحدث الآن - Pepper سيرد بذكاء")
        print("💡 يمكنك التحدث عن أي شيء\n")
        
        last_interaction = time.time()
        
        try:
            while True:
                # 1. Pepper يتحرك
                target = self.walk_points[self.current_point]
                if self.move_to_point(target):
                    self.current_point = (self.current_point + 1) % len(self.walk_points)
                    
                    # يتفاعل مع طفل قريب
                    nearest_kid, dist = self.find_nearest_kid()
                    if nearest_kid and dist < 2.5:
                        self.talk_to_kid(nearest_kid)
                        last_interaction = time.time()
                
                # 2. الأطفال يتحركون حسب شخصياتهم
                for kid in self.kids:
                    kid.move_random()
                
                # 3. تفاعل عشوائي مع طفل كل 15 ثانية
                if time.time() - last_interaction > 15:
                    kid = random.choice(self.kids)
                    self.talk_to_kid(kid)
                    last_interaction = time.time()
                
                # 4. معالجة صوت المستخدم
                while not self.conversation_queue.empty():
                    user_text = self.conversation_queue.get()
                    self.process_user_input(user_text)
                    last_interaction = time.time()
                
                time.sleep(0.05)
                
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
        finally:
            self.sim_manager.stopSimulation(self.client)

if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║   🌟 PEPPER مع أطفال توحديين + ذكاء اصطناعي 🌟         ║
    ╠══════════════════════════════════════════════════════════╣
    ║  • 5 أطفال Peppers بشخصيات مختلفة                      ║
    ║  • محادثة حقيقية عبر ChatGPT                            ║
    ║  • تفاعل صوتي مع المستخدم                               ║
    ║  • حركات طبيعية وشخصيات فريدة                           ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    if OPENAI_API_KEY == "YOUR_API_KEY_HERE":
        print("\n⚠️ لم يتم تعيين مفتاح OpenAI API!")
        print("للاستفادة من الذكاء الاصطناعي الحقيقي:")
        print("1. سجلي في https://platform.openai.com")
        print("2. أنشئي مفتاح API")
        print("3. نفذي: export OPENAI_API_KEY='sk-...'\n")
    
    pepper = MainPepper()
    pepper.run()
