#!/usr/bin/env python3
"""
Pepper في غرفة كاملة مع أطفال حقيقيين
- غرفة بأثاث كامل (طاولات، كراسي، سجادة، رفوف، العاب)
- أطفال مجسمون بألوان حقيقية
- Pepper يتحرك في كل مكان
- صوت نقي (بدون أخطاء)
"""

import time
import pybullet as p
import pybullet_data
import threading
import random
import math
from qibullet import SimulationManager
import pyttsx3

# ========== إصلاح الصوت ==========
class VoiceEngine:
    """محرك الصوت - نسخة آمنة للـ threading"""
    def __init__(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 170)
        self.engine.setProperty('volume', 1.0)
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

# ========== غرفة كاملة ==========
class FullRoom:
    def __init__(self):
        self.build_floor()
        self.build_walls()
        self.build_furniture()
        self.build_decorations()
    
    def build_floor(self):
        """أرضية مع سجادة"""
        # أرضية رئيسية
        floor_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[6, 6, 0.1], 
                                        rgbaColor=[0.7, 0.7, 0.7, 1])
        p.createMultiBody(baseVisualShapeIndex=floor_vis, basePosition=[0, 0, 0])
        
        # سجادة
        carpet_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[4, 4, 0.05], 
                                         rgbaColor=[0.8, 0.2, 0.2, 1])
        p.createMultiBody(baseVisualShapeIndex=carpet_vis, basePosition=[0, 0, 0.05])
    
    def build_walls(self):
        """جدران الغرفة"""
        wall_color = [0.9, 0.9, 0.8, 1]
        
        # جدار خلفي
        wall_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[6, 0.2, 3], rgbaColor=wall_color)
        p.createMultiBody(baseVisualShapeIndex=wall_vis, basePosition=[0, -6, 1.5])
        
        # جدار أمامي
        p.createMultiBody(baseVisualShapeIndex=wall_vis, basePosition=[0, 6, 1.5])
        
        # جدار أيمن
        wall_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.2, 6, 3], rgbaColor=wall_color)
        p.createMultiBody(baseVisualShapeIndex=wall_vis, basePosition=[6, 0, 1.5])
        
        # جدار أيسر
        p.createMultiBody(baseVisualShapeIndex=wall_vis, basePosition=[-6, 0, 1.5])
        
        # نوافذ (مربعات زرقاء شفافة)
        window_color = [0.5, 0.8, 1, 0.3]
        window_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[1.5, 0.1, 1.5], rgbaColor=window_color)
        p.createMultiBody(baseVisualShapeIndex=window_vis, basePosition=[-3, -5.9, 1.5])
        p.createMultiBody(baseVisualShapeIndex=window_vis, basePosition=[3, -5.9, 1.5])
    
    def build_furniture(self):
        """أثاث الغرفة"""
        # طاولة كبيرة
        self.add_table([1, 1, 0], size=[1.2, 0.8, 0.8])
        
        # طاولة صغيرة
        self.add_table([-2, -2, 0], size=[0.8, 0.8, 0.6])
        
        # كراسي حول الطاولة الكبيرة
        self.add_chair([2, 1.5, 0])
        self.add_chair([0.5, 2, 0])
        self.add_chair([1.5, 0, 0])
        
        # رف كتب
        self.add_shelf([3, -2, 0])
        
        # أريكة
        self.add_sofa([-3, 3, 0])
    
    def add_table(self, pos, size=[1.0, 0.6, 0.8]):
        """إضافة طاولة"""
        # سطح
        table_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[size[0]/2, size[1]/2, 0.1],
                                         rgbaColor=[0.5, 0.3, 0.1, 1])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=table_vis,
                          basePosition=[pos[0], pos[1], pos[2] + size[2]/2 + 0.1])
        
        # أرجل
        leg_color = [0.4, 0.2, 0.1, 1]
        for dx, dy in [(-size[0]/3, -size[1]/3), (size[0]/3, -size[1]/3),
                       (-size[0]/3, size[1]/3), (size[0]/3, size[1]/3)]:
            leg_vis = p.createVisualShape(p.GEOM_CYLINDER, radius=0.05, length=size[2],
                                          rgbaColor=leg_color)
            p.createMultiBody(baseMass=0, baseVisualShapeIndex=leg_vis,
                              basePosition=[pos[0] + dx, pos[1] + dy, pos[2] + size[2]/2])
    
    def add_chair(self, pos):
        """إضافة كرسي"""
        # قاعدة
        seat_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.3, 0.3, 0.1],
                                        rgbaColor=[0.3, 0.2, 0.1, 1])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=seat_vis,
                          basePosition=[pos[0], pos[1], pos[2] + 0.3])
        
        # ظهر
        back_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.3, 0.1, 0.4],
                                        rgbaColor=[0.4, 0.3, 0.2, 1])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=back_vis,
                          basePosition=[pos[0], pos[1] + 0.2, pos[2] + 0.6])
    
    def add_shelf(self, pos):
        """إضافة رف كتب"""
        shelf_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[1.0, 0.3, 1.5],
                                         rgbaColor=[0.4, 0.2, 0.1, 1])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=shelf_vis,
                          basePosition=[pos[0], pos[1], pos[2] + 0.75])
        
        # كتب ملونة
        for i in range(4):
            book_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.1, 0.2, 0.15],
                                            rgbaColor=[random.random(), random.random(), random.random(), 1])
            p.createMultiBody(baseMass=0, baseVisualShapeIndex=book_vis,
                              basePosition=[pos[0] - 0.3 + i*0.2, pos[1] + 0.2, pos[2] + 0.5])
    
    def add_sofa(self, pos):
        """إضافة أريكة"""
        # قاعدة
        base_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[1.0, 0.4, 0.3],
                                        rgbaColor=[0.2, 0.2, 0.4, 1])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=base_vis,
                          basePosition=[pos[0], pos[1], pos[2] + 0.3])
        
        # ظهر
        back_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[1.0, 0.1, 0.6],
                                        rgbaColor=[0.3, 0.3, 0.5, 1])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=back_vis,
                          basePosition=[pos[0], pos[1] - 0.25, pos[2] + 0.7])
    
    def build_decorations(self):
        """ديكورات إضافية"""
        # نباتات
        green = [0.2, 0.8, 0.2, 1]
        plant_positions = [[-4, -4, 0], [4, 4, 0], [-4, 4, 0], [4, -4, 0]]
        for pos in plant_positions:
            plant_vis = p.createVisualShape(p.GEOM_SPHERE, radius=0.3, rgbaColor=green)
            p.createMultiBody(baseMass=0, baseVisualShapeIndex=plant_vis, basePosition=pos)
        
        # ألعاب
        toy_colors = [[1,0,0,1], [0,1,0,1], [0,0,1,1], [1,1,0,1]]
        toy_positions = [[-1, -1, 0.1], [2, -2, 0.1], [-2, 2, 0.1], [0, 2, 0.1]]
        for pos, color in zip(toy_positions, toy_colors):
            toy_vis = p.createVisualShape(p.GEOM_SPHERE, radius=0.15, rgbaColor=color)
            p.createMultiBody(baseMass=0.1, baseVisualShapeIndex=toy_vis, basePosition=pos)

# ========== أطفال حقيقيون ==========
class RealKid:
    def __init__(self, name, age, color, position):
        self.name = name
        self.age = age
        self.color = color
        self.position = position
        self.body = None
        self.head = None
        
    def create(self):
        """إنشاء طفل بمجسم واضح"""
        # جسم
        col_id = p.createCollisionShape(p.GEOM_CYLINDER, radius=0.2, height=0.8)
        vis_id = p.createVisualShape(p.GEOM_CYLINDER, radius=0.2, length=0.8, rgbaColor=self.color)
        self.body = p.createMultiBody(baseMass=3, baseCollisionShapeIndex=col_id,
                                       baseVisualShapeIndex=vis_id, 
                                       basePosition=self.position)
        
        # رأس
        head_pos = [self.position[0], self.position[1], self.position[2] + 0.4]
        head_vis = p.createVisualShape(p.GEOM_SPHERE, radius=0.15, rgbaColor=[1, 0.9, 0.8, 1])
        self.head = p.createMultiBody(baseMass=0, baseVisualShapeIndex=head_vis,
                                       basePosition=head_pos)
        
        # اسم
        p.addUserDebugText(f"{self.name} ({self.age}y)", 
                          [self.position[0], self.position[1], self.position[2] + 0.8],
                          [0, 0, 0], textSize=1.2)
        
        return self.body
    
    def move_random(self):
        """حركة عشوائية بسيطة"""
        if random.random() < 0.05:  # 5% فرصة للحركة
            dx = random.uniform(-0.2, 0.2)
            dy = random.uniform(-0.2, 0.2)
            new_pos = [self.position[0] + dx, self.position[1] + dy, self.position[2]]
            
            # حدود الغرفة
            if abs(new_pos[0]) < 4 and abs(new_pos[1]) < 4:
                self.position = new_pos
                p.resetBasePositionAndOrientation(self.body, self.position, [0,0,0,1])
                head_pos = [self.position[0], self.position[1], self.position[2] + 0.4]
                p.resetBasePositionAndOrientation(self.head, head_pos, [0,0,0,1])

# ========== Pepper الرئيسي ==========
class PepperInFullRoom:
    def __init__(self):
        print("🚀 تشغيل Pepper في الغرفة الكاملة...")
        
        # الصوت
        self.voice = VoiceEngine()
        
        # المحاكي
        self.sim_manager = SimulationManager()
        self.client = self.sim_manager.launchSimulation(gui=True)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.loadURDF("plane.urdf")
        
        # بناء الغرفة
        self.room = FullRoom()
        
        # إنشاء Pepper
        self.pepper = self.sim_manager.spawnPepper(
            self.client, translation=[-3, -2, 0.2], quaternion=[0, 0, 0, 1]
        )
        
        # إنشاء الأطفال
        self.kids = self.create_kids()
        
        # نقاط التجوال لـ Pepper
        self.walk_points = [
            [-3, -2, 0.2],
            [0, 0, 0.2],
            [3, 2, 0.2],
            [-2, 3, 0.2],
            [2, -3, 0.2],
            [-3, 2, 0.2],
            [3, -2, 0.2]
        ]
        self.current_point = 0
        
        print("✅ Pepper جاهز في غرفة كاملة!")
        self.voice.speak("Welcome to our beautiful room!")

    def create_kids(self):
        """إنشاء أطفال حقيقيين"""
        kids_data = [
            ("Emma", 4, [1, 1, 0.2], [1, 0.8, 0.8, 1]),
            ("Liam", 5, [-1, 2, 0.2], [0.8, 1, 0.8, 1]),
            ("Sophia", 3, [2, -2, 0.2], [0.8, 0.8, 1, 1]),
            ("Noah", 6, [-2, -1, 0.2], [1, 1, 0.8, 1]),
            ("Mia", 4, [3, 1, 0.2], [1, 0.8, 1, 1]),
            ("Oliver", 5, [-3, 3, 0.2], [0.9, 0.9, 0.9, 1])
        ]
        
        kids = []
        for name, age, pos, color in kids_data:
            kid = RealKid(name, age, color, pos)
            kid.create()
            kids.append(kid)
            print(f"✅ طفل: {name}")
        
        return kids

    def move_to_point(self, target):
        """تحريك Pepper إلى نقطة محددة"""
        current = self.pepper.getPosition()
        dx = target[0] - current[0]
        dy = target[1] - current[1]
        dist = math.sqrt(dx*dx + dy*dy)
        
        if dist > 0.2:
            # تحرك نحو الهدف
            self.pepper.move(0.1 * dx / dist, 0, 0.05 * math.atan2(dy, dx))
            return False
        return True

    def wave(self):
        """يلوح"""
        for i in range(2):
            self.pepper.setAngles(["RShoulderPitch"], [-0.7], 0.5)
            time.sleep(0.2)
            self.pepper.setAngles(["RShoulderPitch"], [0.3], 0.5)
            time.sleep(0.2)

    def show_text(self, text):
        pos = self.pepper.getPosition()
        p.addUserDebugText(text, [pos[0], pos[1], pos[2] + 2.0], [0,0,0], textSize=1.2, lifeTime=3)

    def run(self):
        print("\n" + "="*70)
        print("🌟 PEPPER في غرفة كاملة مع أطفال حقيقيين")
        print("="*70 + "\n")
        
        self.voice.speak("I will walk around the room and talk to you!")
        
        last_speak = time.time()
        last_move_check = time.time()
        
        try:
            while True:
                # 1. Pepper يتجول في الغرفة
                target = self.walk_points[self.current_point]
                if self.move_to_point(target):
                    # وصل للنقطة، ننتقل للنقطة التالية
                    self.current_point = (self.current_point + 1) % len(self.walk_points)
                    
                    # يتكلم عند كل نقطة جديدة
                    texts = [
                        "This room is so nice!",
                        "Look at all the furniture!",
                        "I love playing here!",
                        "Where should I go next?",
                        "The children are so cute!"
                    ]
                    text = random.choice(texts)
                    self.voice.speak(text)
                    self.show_text(text)
                    self.wave()
                
                # 2. الأطفال يتحركون
                for kid in self.kids:
                    kid.move_random()
                
                # 3. يتكلم عشوائياً كل 10 ثواني
                if time.time() - last_speak > 10:
                    kid = random.choice(self.kids)
                    texts = [
                        f"Hi {kid.name}! How are you?",
                        f"{kid.name}, let's play!",
                        f"Where is {kid.name} going?",
                        f"I see you {kid.name}!",
                        f"Hello everyone!"
                    ]
                    text = random.choice(texts)
                    self.voice.speak(text)
                    self.show_text(text)
                    self.wave()
                    last_speak = time.time()
                
                time.sleep(0.05)
                
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
        finally:
            self.sim_manager.stopSimulation(self.client)

if __name__ == "__main__":
    pepper = PepperInFullRoom()
    pepper.run()
