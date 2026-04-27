#!/usr/bin/env python3
"""
Pepper في غرفة مع أطفال كرتونيين
- أطفال على شكل كرتوني (رأس كبير، جسم صغير)
- Pepper يتحرك في كل أنحاء الغرفة
- يتفاعل مع كل طفل
"""

import time
import pybullet as p
import pybullet_data
import threading
import random
import math
from qibullet import SimulationManager
import pyttsx3

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

# ========== طفل كرتوني ==========
class CartoonKid:
    def __init__(self, name, age, position, color):
        self.name = name
        self.age = age
        self.position = position
        self.color = color
        self.body_parts = []
        self.walk_direction = random.choice([(0.1,0), (-0.1,0), (0,0.1), (0,-0.1)])
        self.walk_timer = 0
        
    def create(self):
        """إنشاء طفل بشكل كرتوني لطيف"""
        
        # رأس كبير (كرتوني)
        head_vis = p.createVisualShape(p.GEOM_SPHERE, radius=0.25, rgbaColor=[1, 0.9, 0.8, 1])
        head = p.createMultiBody(baseMass=0, baseVisualShapeIndex=head_vis,
                                  basePosition=[self.position[0], self.position[1], self.position[2] + 0.8])
        self.body_parts.append(head)
        
        # عيون
        eye_vis = p.createVisualShape(p.GEOM_SPHERE, radius=0.05, rgbaColor=[0,0,0,1])
        # عين يمنى
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=eye_vis,
                          basePosition=[self.position[0] + 0.1, self.position[1] + 0.1, self.position[2] + 0.85])
        # عين يسرى
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=eye_vis,
                          basePosition=[self.position[0] - 0.1, self.position[1] + 0.1, self.position[2] + 0.85])
        
        # فم (قوس)
        p.addUserDebugLine([self.position[0] - 0.1, self.position[1] + 0.15, self.position[2] + 0.75],
                           [self.position[0] + 0.1, self.position[1] + 0.15, self.position[2] + 0.75],
                           [1,0,0], lineWidth=3)
        
        # جسم
        body_vis = p.createVisualShape(p.GEOM_CYLINDER, radius=0.15, length=0.5,
                                        rgbaColor=self.color)
        body = p.createMultiBody(baseMass=1, baseVisualShapeIndex=body_vis,
                                  basePosition=[self.position[0], self.position[1], self.position[2] + 0.45])
        self.body_parts.append(body)
        
        # أذرع
        arm_vis = p.createVisualShape(p.GEOM_CYLINDER, radius=0.05, length=0.4,
                                       rgbaColor=self.color)
        # ذراع يمنى
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=arm_vis,
                          basePosition=[self.position[0] + 0.2, self.position[1], self.position[2] + 0.5])
        # ذراع يسرى
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=arm_vis,
                          basePosition=[self.position[0] - 0.2, self.position[1], self.position[2] + 0.5])
        
        # اسم الطفل
        p.addUserDebugText(f"{self.name} ({self.age})", 
                          [self.position[0], self.position[1], self.position[2] + 1.1],
                          [0, 0, 0], textSize=1.2)
        
        return self.body_parts
    
    def move_random(self):
        """حركة عشوائية لطيفة"""
        self.walk_timer += 1
        if self.walk_timer > 30:  # تغيير الاتجاه كل فترة
            self.walk_direction = random.choice([(0.1,0), (-0.1,0), (0,0.1), (0,-0.1)])
            self.walk_timer = 0
        
        # حركة بسيطة
        new_x = self.position[0] + self.walk_direction[0] * 0.05
        new_y = self.position[1] + self.walk_direction[1] * 0.05
        
        # حدود الغرفة
        if abs(new_x) < 4 and abs(new_y) < 4:
            self.position = [new_x, new_y, self.position[2]]
            
            # تحديث موقع كل الأجزاء
            for i, part in enumerate(self.body_parts):
                if i == 0:  # رأس
                    p.resetBasePositionAndOrientation(part, [new_x, new_y, self.position[2] + 0.8], [0,0,0,1])
                elif i == 1:  # جسم
                    p.resetBasePositionAndOrientation(part, [new_x, new_y, self.position[2] + 0.45], [0,0,0,1])

# ========== غرفة بسيطة ==========
class SimpleRoom:
    def __init__(self):
        # أرضية
        floor_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[5, 5, 0.1], 
                                        rgbaColor=[0.7, 0.7, 0.7, 1])
        p.createMultiBody(baseVisualShapeIndex=floor_vis, basePosition=[0, 0, 0])
        
        # جدران (حدود)
        wall_color = [0.9, 0.9, 0.8, 1]
        wall_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[5, 0.2, 3], rgbaColor=wall_color)
        p.createMultiBody(baseVisualShapeIndex=wall_vis, basePosition=[0, -5, 1.5])
        p.createMultiBody(baseVisualShapeIndex=wall_vis, basePosition=[0, 5, 1.5])
        
        wall_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.2, 5, 3], rgbaColor=wall_color)
        p.createMultiBody(baseVisualShapeIndex=wall_vis, basePosition=[5, 0, 1.5])
        p.createMultiBody(baseVisualShapeIndex=wall_vis, basePosition=[-5, 0, 1.5])

# ========== Pepper الرئيسي ==========
class PepperCartoonRoom:
    def __init__(self):
        print("🚀 تشغيل Pepper مع أطفال كرتونيين...")
        
        # الصوت
        self.voice = VoiceEngine()
        
        # المحاكي
        self.sim_manager = SimulationManager()
        self.client = self.sim_manager.launchSimulation(gui=True)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.loadURDF("plane.urdf")
        
        # الغرفة
        self.room = SimpleRoom()
        
        # Pepper
        self.pepper = self.sim_manager.spawnPepper(
            self.client, translation=[-4, -3, 0.2], quaternion=[0, 0, 0, 1]
        )
        
        # أطفال كرتونيون
        self.kids = self.create_cartoon_kids()
        
        # مسار Pepper (نقاط عشوائية)
        self.setup_walk_path()
        
        print("✅ Pepper جاهز مع أطفال كرتونيين!")
        self.voice.speak("Hello cute kids! Let's play!")

    def create_cartoon_kids(self):
        """إنشاء أطفال بشكل كرتوني"""
        kids_data = [
            ("Emma", 4, [2, 2, 0.2], [1, 0.5, 0.5, 1]),    # فستان أحمر
            ("Liam", 5, [-2, 3, 0.2], [0.5, 1, 0.5, 1]),   # قميص أخضر
            ("Sophia", 3, [3, -2, 0.2], [0.5, 0.5, 1, 1]), # بلوزة زرقاء
            ("Noah", 6, [-3, -2, 0.2], [1, 1, 0.5, 1]),    # تيشيرت أصفر
            ("Mia", 4, [0, 4, 0.2], [1, 0.5, 1, 1]),       # قميص بنفسجي
            ("Oliver", 5, [-4, 1, 0.2], [0.5, 1, 1, 1]),   # قميص سماوي
            ("Amelia", 3, [4, -1, 0.2], [1, 0.8, 0.8, 1])  # فستان وردي
        ]
        
        kids = []
        for name, age, pos, color in kids_data:
            kid = CartoonKid(name, age, pos, color)
            kid.create()
            kids.append(kid)
            print(f"✅ طفل كرتوني: {name}")
        
        return kids

    def setup_walk_path(self):
        """نقاط تجوال Pepper في كل الغرفة"""
        self.walk_points = [
            [-4, -3, 0.2],  # ركن 1
            [4, -3, 0.2],   # ركن 2
            [4, 4, 0.2],    # ركن 3
            [-4, 4, 0.2],   # ركن 4
            [-2, -2, 0.2],  # وسط
            [2, 2, 0.2],    # وسط
            [-3, 3, 0.2],   # قريب من الأطفال
            [3, -3, 0.2]    # قريب من الأطفال
        ]
        self.current_point = 0

    def move_to_point(self, target):
        """تحريك Pepper إلى نقطة"""
        current = self.pepper.getPosition()
        dx = target[0] - current[0]
        dy = target[1] - current[1]
        dist = math.sqrt(dx*dx + dy*dy)
        
        if dist > 0.3:
            self.pepper.move(0.15 * dx / dist, 0, 0.1 * math.atan2(dy, dx))
            return False
        return True

    def find_nearest_kid(self):
        """العثور على أقرب طفل"""
        pepper_pos = self.pepper.getPosition()
        nearest = None
        min_dist = float('inf')
        
        for kid in self.kids:
            dx = kid.position[0] - pepper_pos[0]
            dy = kid.position[1] - pepper_pos[1]
            dist = math.sqrt(dx*dx + dy*dy)
            if dist < min_dist:
                min_dist = dist
                nearest = kid
        
        return nearest, min_dist

    def wave(self):
        for i in range(2):
            self.pepper.setAngles(["RShoulderPitch"], [-0.7], 0.5)
            time.sleep(0.2)
            self.pepper.setAngles(["RShoulderPitch"], [0.3], 0.5)
            time.sleep(0.2)

    def show_text(self, text):
        pos = self.pepper.getPosition()
        p.addUserDebugText(text, [pos[0], pos[1], pos[2] + 2.0], [0,0,0], textSize=1.2, lifeTime=3)

    def interact_with_kid(self, kid):
        """التفاعل مع طفل معين"""
        greetings = [
            f"Hi {kid.name}! How are you?",
            f"Hello {kid.name}, let's play!",
            f"{kid.name}, you're so cute!",
            f"Hi sweet {kid.name}!",
            f"{kid.name}, what do you want to play?"
        ]
        
        text = random.choice(greetings)
        print(f"🤖 Pepper: {text}")
        self.voice.speak(text)
        self.show_text(text)
        self.wave()

    def run(self):
        print("\n" + "="*70)
        print("🌟 PEPPER مع أطفال كرتونيين - يتحرك في كل الغرفة")
        print("="*70 + "\n")
        
        self.voice.speak("I will walk around and talk to all the cute kids!")
        
        last_interaction = time.time()
        
        try:
            while True:
                # 1. Pepper يتحرك في الغرفة
                target = self.walk_points[self.current_point]
                if self.move_to_point(target):
                    self.current_point = (self.current_point + 1) % len(self.walk_points)
                    
                    # عندما يصل لنقطة جديدة، يتفاعل مع طفل قريب
                    nearest_kid, dist = self.find_nearest_kid()
                    if nearest_kid and dist < 2.0:
                        self.interact_with_kid(nearest_kid)
                
                # 2. الأطفال يتحركون
                for kid in self.kids:
                    kid.move_random()
                
                # 3. تفاعل عشوائي كل 10 ثواني
                if time.time() - last_interaction > 10:
                    kid = random.choice(self.kids)
                    self.interact_with_kid(kid)
                    last_interaction = time.time()
                
                time.sleep(0.05)
                
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
        finally:
            self.sim_manager.stopSimulation(self.client)

if __name__ == "__main__":
    print("""
    ╔════════════════════════════════════════════════════╗
    ║   🌟 PEPPER مع أطفال كرتونيين في غرفة اللعب 🌟   ║
    ╠════════════════════════════════════════════════════╣
    ║  • 7 أطفال كرتونيين بألوان مختلفة                ║
    ║  • Pepper يتحرك في كل أنحاء الغرفة               ║
    ║  • يتفاعل مع كل طفل عند الاقتراب                  ║
    ║  • حركة مستمرة وتفاعل طبيعي                       ║
    ╚════════════════════════════════════════════════════╝
    """)
    
    pepper = PepperCartoonRoom()
    pepper.run()
