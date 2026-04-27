#!/usr/bin/env python3
"""
Pepper في غرفة عصرية مع أطفال حقيقيين
- ذكاء اصطناعي (ChatGPT)
- محادثة صوتية حقيقية
- أطفال يتحركون ويتفاعلون
- كاميرا Pepper تظهر ما يراه
"""

import time
import pybullet as p
import pybullet_data
import threading
import random
import queue
import numpy as np
import cv2
import os
from qibullet import SimulationManager
import pyttsx3
import speech_recognition as sr

# الذكاء الاصطناعي
try:
    import openai
    OPENAI_AVAILABLE = True
except:
    OPENAI_AVAILABLE = False
    print("⚠️ OpenAI غير مثبت. للذكاء الاصطناعي الحقيقي: pip install openai")

# ========== الطفل الذكي (يتحرك ويتكلم) ==========
class SmartKid:
    def __init__(self, name, age, color, position):
        self.name = name
        self.age = age
        self.color = color
        self.position = position
        self.mood = "happy"
        self.energy = 100
        self.body_id = None
        self.head_id = None
        self.last_action = time.time()
        self.speech_bubble = None
        
    def create_in_sim(self, sim_client):
        """إنشاء الطفل في المحاكاة"""
        # جسم الطفل
        col_id = p.createCollisionShape(p.GEOM_CYLINDER, radius=0.2, height=0.8)
        vis_id = p.createVisualShape(p.GEOM_CYLINDER, radius=0.2, length=0.8, rgbaColor=self.color)
        self.body_id = p.createMultiBody(baseMass=3, baseCollisionShapeIndex=col_id,
                                         baseVisualShapeIndex=vis_id, 
                                         basePosition=self.position)
        
        # رأس الطفل
        head_pos = [self.position[0], self.position[1], self.position[2] + 0.4]
        head_vis = p.createVisualShape(p.GEOM_SPHERE, radius=0.15, rgbaColor=[1, 0.9, 0.8, 1])
        self.head_id = p.createMultiBody(baseMass=0, baseVisualShapeIndex=head_vis,
                                        basePosition=head_pos)
        
        # اسم الطفل
        p.addUserDebugText(f"{self.name} ({self.age}y)", 
                          [self.position[0], self.position[1], self.position[2] + 0.8],
                          [0, 0, 0], textSize=1.2)
    
    def move_randomly(self):
        """تحرك الطفل بشكل عشوائي"""
        if random.random() < 0.1:  # 10% فرصة للحركة
            dx = random.uniform(-0.3, 0.3)
            dy = random.uniform(-0.3, 0.3)
            new_pos = [self.position[0] + dx, self.position[1] + dy, self.position[2]]
            
            # حدود الغرفة
            if abs(new_pos[0]) < 4 and abs(new_pos[1]) < 4:
                self.position = new_pos
                p.resetBasePositionAndOrientation(self.body_id, self.position, [0,0,0,1])
                head_pos = [self.position[0], self.position[1], self.position[2] + 0.4]
                p.resetBasePositionAndOrientation(self.head_id, head_pos, [0,0,0,1])
    
    def say(self, text, pepper):
        """الطفل يتكلم"""
        pepper.show_text(text, position=self.position, color=[0,0,255])
        print(f"👧 {self.name}: {text}")

# ========== الغرفة العصرية ==========
class ModernRoom:
    def __init__(self, sim_client):
        self.client = sim_client
        self.build_room()
        
    def build_room(self):
        """بناء غرفة عصرية"""
        # أرضية باركيه
        floor_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[5, 5, 0.1], 
                                        rgbaColor=[0.6, 0.4, 0.2, 1])
        p.createMultiBody(baseVisualShapeIndex=floor_vis, basePosition=[0, 0, 0])
        
        # جدران زجاجية
        glass_color = [0.8, 0.9, 1, 0.3]  # شفاف
        
        # جدار خلفي
        wall_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[5, 0.1, 3], rgbaColor=glass_color)
        p.createMultiBody(baseVisualShapeIndex=wall_vis, basePosition=[0, -5, 1.5])
        
        # جدار أمامي
        p.createMultiBody(baseVisualShapeIndex=wall_vis, basePosition=[0, 5, 1.5])
        
        # جدار أيمن
        wall_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.1, 5, 3], rgbaColor=glass_color)
        p.createMultiBody(baseVisualShapeIndex=wall_vis, basePosition=[5, 0, 1.5])
        
        # جدار أيسر
        p.createMultiBody(baseVisualShapeIndex=wall_vis, basePosition=[-5, 0, 1.5])
        
        # سقف مع إضاءة
        ceiling_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[5, 5, 0.1], 
                                         rgbaColor=[1, 1, 1, 0.1])
        p.createMultiBody(baseVisualShapeIndex=ceiling_vis, basePosition=[0, 0, 3])
        
        # أثاث عصري
        self.add_modern_table()
        self.add_modern_chairs()
        self.add_bookshelf()
        self.add_rug()
        self.add_plants()
        
    def add_modern_table(self):
        """طاولة عصرية"""
        # سطح زجاجي
        glass_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[1.2, 0.8, 0.05], 
                                        rgbaColor=[0.9, 0.9, 1, 0.7])
        table_top = p.createMultiBody(baseMass=0, baseVisualShapeIndex=glass_vis,
                                      basePosition=[1, 1, 0.8])
        
        # أرجل معدنية
        metal_color = [0.7, 0.7, 0.8, 1]
        for dx, dy in [(-0.8, -0.5), (0.8, -0.5), (-0.8, 0.5), (0.8, 0.5)]:
            leg_vis = p.createVisualShape(p.GEOM_CYLINDER, radius=0.05, length=0.8, rgbaColor=metal_color)
            p.createMultiBody(baseMass=0, baseVisualShapeIndex=leg_vis,
                            basePosition=[1+dx, 1+dy, 0.4])
    
    def add_modern_chairs(self):
        """كراسي عصرية"""
        chair_positions = [[2, 1.5, 0], [0.5, 2, 0], [-1, -1, 0], [2, -2, 0]]
        for pos in chair_positions:
            # قاعدة
            seat_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.4, 0.4, 0.1],
                                          rgbaColor=[0.3, 0.3, 0.4, 1])
            p.createMultiBody(baseMass=0, baseVisualShapeIndex=seat_vis,
                            basePosition=[pos[0], pos[1], pos[2] + 0.3])
            
            # ظهر
            back_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.4, 0.1, 0.5],
                                          rgbaColor=[0.4, 0.4, 0.5, 1])
            p.createMultiBody(baseMass=0, baseVisualShapeIndex=back_vis,
                            basePosition=[pos[0], pos[1] + 0.3, pos[2] + 0.7])
    
    def add_bookshelf(self):
        """رف كتب"""
        shelf_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[1.5, 0.3, 1.5],
                                        rgbaColor=[0.5, 0.3, 0.2, 1])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=shelf_vis,
                         basePosition=[-3, 3, 0.8])
        
        # كتب ملونة
        colors = [[1,0,0,1], [0,1,0,1], [0,0,1,1], [1,1,0,1]]
        for i, color in enumerate(colors):
            book_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.1, 0.3, 0.2],
                                          rgbaColor=color)
            p.createMultiBody(baseMass=0, baseVisualShapeIndex=book_vis,
                            basePosition=[-3 + 0.3*i, 3.3, 1.2 + 0.2*i])
    
    def add_rug(self):
        """سجادة"""
        rug_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[3, 2, 0.05],
                                      rgbaColor=[0.8, 0.7, 0.6, 1])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=rug_vis,
                         basePosition=[0, 0, 0.02])
    
    def add_plants(self):
        """نباتات خضراء"""
        green = [0.2, 0.8, 0.2, 1]
        for pos in [[-2, -2, 0], [3, -3, 0], [-3, 2, 0]]:
            plant_vis = p.createVisualShape(p.GEOM_SPHERE, radius=0.3, rgbaColor=green)
            p.createMultiBody(baseMass=0, baseVisualShapeIndex=plant_vis,
                            basePosition=pos)

# ========== Pepper الذكي ==========
class SmartPepper:
    def __init__(self):
        print("🚀 تشغيل Pepper الذكي...")
        
        # الصوت
        self.init_voice()
        
        # الميكروفون
        self.init_microphone()
        
        # الذكاء الاصطناعي
        self.init_ai()
        
        # المحاكي
        self.sim_manager = SimulationManager()
        self.client = self.sim_manager.launchSimulation(gui=True)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        
        # بناء الغرفة
        self.room = ModernRoom(self.client)
        
        # إنشاء Pepper
        self.create_pepper()
        
        # إنشاء الأطفال
        self.kids = []
        self.create_kids()
        
        # متغيرات التشغيل
        self.running = True
        self.speech_queue = queue.Queue()
        self.text_id = None
        self.camera_view = np.zeros((400, 600, 3), dtype=np.uint8)
        
        # بدء الاستماع
        self.start_listening()
        
        print("✅ Pepper جاهز في الغرفة العصرية!")
        self.speak("Hello everyone! I'm Pepper. Let's play together!")
        
    def init_voice(self):
        """صوت Pepper"""
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 170)
        self.engine.setProperty('volume', 1.0)
        voices = self.engine.getProperty('voices')
        for voice in voices:
            if 'english' in voice.name.lower():
                self.engine.setProperty('voice', voice.id)
                break
    
    def init_microphone(self):
        """الميكروفون"""
        self.recognizer = sr.Recognizer()
        try:
            self.microphone = sr.Microphone()
            with self.microphone as source:
                print("🔄 معايرة الميكروفون...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
            print("✅ الميكروفون جاهز")
        except Exception as e:
            print(f"⚠️ مشكلة في الميكروفون: {e}")
            self.microphone = None
    
    def init_ai(self):
        """الذكاء الاصطناعي"""
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        if self.api_key and OPENAI_AVAILABLE:
            openai.api_key = self.api_key
            self.use_ai = True
            print("✅ الذكاء الاصطناعي جاهز (ChatGPT)")
        else:
            self.use_ai = False
            print("⚠️ ردود افتراضية (للذكاء الحقيقي: ضعي OPENAI_API_KEY)")
        
        # ردود احتياطية
        self.responses = [
            "That's wonderful! Tell me more.",
            "I'm listening. Please continue.",
            "How interesting! What else?",
            "The children are having so much fun!",
            "I love playing with everyone here!"
        ]
    
    def create_pepper(self):
        """إنشاء Pepper"""
        self.pepper = self.sim_manager.spawnPepper(
            self.client, translation=[-3, -2, 0.2], quaternion=[0, 0, 0, 1]
        )
        self.pepper_pos = [-3, -2, 0.6]
    
    def create_kids(self):
        """إنشاء أطفال حقيقيين"""
        kids_data = [
            ("Emma", 4, [1.5, 1.5, 0.2], [1, 0.8, 0.8, 1]),
            ("Liam", 5, [-1, 2, 0.2], [0.8, 1, 0.8, 1]),
            ("Sophia", 3, [2, -2, 0.2], [0.8, 0.8, 1, 1]),
            ("Noah", 6, [-2, -1, 0.2], [1, 1, 0.8, 1]),
            ("Mia", 4, [3, 1, 0.2], [1, 0.8, 1, 1])
        ]
        
        for name, age, pos, color in kids_data:
            kid = SmartKid(name, age, color, pos)
            kid.create_in_sim(self.client)
            self.kids.append(kid)
            print(f"✅ طفل: {name} ({age} سنوات)")
    
    def start_listening(self):
        """بدء الاستماع في الخلفية"""
        def listen_loop():
            if not self.microphone:
                return
            while self.running:
                try:
                    with self.microphone as source:
                        print("\n🎤 استماع... (تحدث الآن)")
                        audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=7)
                    text = self.recognizer.recognize_google(audio)
                    print(f"📝 أنت: {text}")
                    self.speech_queue.put(text)
                except sr.WaitTimeoutError:
                    pass
                except sr.UnknownValueError:
                    print("❓ لم أفهم")
                except Exception as e:
                    print(f"⚠️ خطأ: {e}")
                time.sleep(0.1)
        
        threading.Thread(target=listen_loop, daemon=True).start()
    
    def speak(self, text):
        """نطق النص"""
        def speak_thread():
            self.engine.say(text)
            self.engine.runAndWait()
        threading.Thread(target=speak_thread, daemon=True).start()
    
    def show_text(self, text, position=None, color=[0,0,0]):
        """عرض نص"""
        if position is None:
            pos = self.pepper.getPosition()
            pos = [pos[0], pos[1], pos[2] + 2.0]
        else:
            pos = [position[0], position[1], position[2] + 0.8]
        
        p.addUserDebugText(text, pos, color, textSize=1.2, lifeTime=3)
    
    def move_to(self, target_pos):
        """تحريك Pepper نحو هدف"""
        current = self.pepper.getPosition()
        dx = target_pos[0] - current[0]
        dy = target_pos[1] - current[1]
        
        if abs(dx) > 0.2 or abs(dy) > 0.2:
            self.pepper.move(0.1 * dx, 0, 0.05 * dy)
            return False
        return True
    
    def wave(self):
        """يلوح"""
        for i in range(3):
            try:
                self.pepper.setAngles(["RShoulderPitch"], [-0.7], 0.5)
                time.sleep(0.2)
                self.pepper.setAngles(["RShoulderPitch"], [0.3], 0.5)
                time.sleep(0.2)
            except:
                pass
    
    def get_pepper_view(self):
        """ما يراه Pepper"""
        view = np.ones((400, 600, 3), dtype=np.uint8) * 240
        
        # رسم الأطفال في مجال رؤية Pepper
        pepper_pos = self.pepper.getPosition()
        y_pos = 50
        
        cv2.putText(view, "🤖 PEPPER'S VIEW", (200, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,0), 2)
        
        for kid in self.kids:
            # حساب المسافة والاتجاه
            dx = kid.position[0] - pepper_pos[0]
            dy = kid.position[1] - pepper_pos[1]
            dist = np.sqrt(dx**2 + dy**2)
            
            if dist < 4:  # في مجال الرؤية
                # حجم الطفل حسب المسافة
                size = int(200 / max(dist, 1))
                color = (0, 255, 0) if dist < 2 else (0, 255, 255)
                
                cv2.putText(view, f"👤 {kid.name}", (50, y_pos), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                cv2.putText(view, f"   {dist:.1f}m", (300, y_pos), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                y_pos += 30
                
                # رسم اتجاه الطفل
                angle = np.arctan2(dy, dx)
                x_end = int(400 + 50 * np.cos(angle))
                y_end = int(300 - 50 * np.sin(angle))
                cv2.line(view, (400, 300), (x_end, y_end), (0,255,0), 2)
        
        cv2.imshow("Pepper's Camera - What I See", view)
        cv2.waitKey(1)
    
    def get_ai_response(self, user_input):
        """الحصول على رد من الذكاء الاصطناعي"""
        if self.use_ai:
            try:
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are Pepper, a friendly robot in a room with children. Be warm, encouraging, and use simple language. The children's names are Emma, Liam, Sophia, Noah, and Mia."},
                        {"role": "user", "content": user_input}
                    ],
                    temperature=0.7,
                    max_tokens=100
                )
                return response.choices[0].message.content
            except:
                pass
        
        # ردود احتياطية ذكية
        if "hello" in user_input.lower() or "hi" in user_input.lower():
            return "Hello! I'm so happy to see you!"
        elif "name" in user_input.lower():
            kids_names = ", ".join([k.name for k in self.kids])
            return f"I'm Pepper! I'm playing with {kids_names}. They're wonderful children!"
        elif "play" in user_input.lower():
            return "Let's play together! What game would you like to play?"
        elif "how are you" in user_input.lower():
            return "I'm great! The children are being so sweet today!"
        else:
            return random.choice(self.responses)
    
    def process_speech(self, text):
        """معالجة الكلام والرد"""
        print(f"🤔 معالجة: '{text}'")
        
        # الحصول على رد ذكي
        response = self.get_ai_response(text)
        print(f"🤖 Pepper: {response}")
        
        # نطق الرد
        self.speak(response)
        
        # عرض النص فوق Pepper
        self.show_text(response)
        
        # حركة يدين
        self.wave()
        
        # طفل عشوائي يرد أحياناً
        if random.random() < 0.3:
            kid = random.choice(self.kids)
            kid_reply = f"{kid.name} smiles at you!"
            kid.say(kid_reply, self)
    
    def run(self):
        """تشغيل المحاكاة"""
        print("\n" + "="*70)
        print("🌟 PEPPER في الغرفة العصرية مع الأطفال")
        print("="*70 + "\n")
        print("🎤 تحدث الآن - Pepper سيسمعك ويرد بذكاء")
        print("💡 قل 'hello'، 'what's your name'، أو أي شيء\n")
        
        self.speak("Welcome to our modern room! I can hear you and answer intelligently!")
        
        current_target = 0
        last_move = time.time()
        
        try:
            while self.running:
                # Pepper يتجول بين الأطفال
                if time.time() - last_move > 8:
                    target = self.kids[current_target % len(self.kids)].position
                    if self.move_to(target):
                        current_target += 1
                        last_move = time.time()
                
                # الأطفال يتحركون عشوائياً
                for kid in self.kids:
                    kid.move_randomly()
                
                # عرض رؤية Pepper
                self.get_pepper_view()
                
                # معالجة الصوت
                if not self.speech_queue.empty():
                    text = self.speech_queue.get()
                    self.process_speech(text)
                
                time.sleep(0.05)
                
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            self.speak("Goodbye! It was lovely playing with you!")
        finally:
            cv2.destroyAllWindows()
            self.sim_manager.stopSimulation(self.client)

# ========== التشغيل ==========
if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║     🌟 PEPPER في الغرفة العصرية مع الأطفال 🌟          ║
    ╠══════════════════════════════════════════════════════════╣
    ║  • غرفة عصرية بأثاث حديث                                ║
    ║  • 5 أطفال حقيقيين (يتحركون)                            ║
    ║  • ذكاء اصطناعي (ChatGPT) للردود                        ║
    ║  • محادثة صوتية حقيقية                                  ║
    ║  • كاميرا Pepper تعرض ما يراه                            ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    # نصيحة لمفتاح API
    if not os.getenv("OPENAI_API_KEY"):
        print("\n🔑 للحصول على ردود ذكية حقيقية من ChatGPT:")
        print("1. سجلي في https://platform.openai.com")
        print("2. اذهبي إلى API Keys وأنشئي مفتاحاً")
        print("3. نفذي: export OPENAI_API_KEY='sk-...'")
        print("أو ضعي المفتاح مباشرة في الكود (غير موصى به)\n")
    
    pepper = SmartPepper()
    pepper.run()
