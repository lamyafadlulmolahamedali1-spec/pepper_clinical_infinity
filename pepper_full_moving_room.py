#!/usr/bin/env python3
"""
Pepper في غرفة كاملة مع أطفال متحركين
- غرفة بأثاث حقيقي
- Pepper يتجول في كل المكان
- أطفال Peppers يتحركون كمان
- تفاعل عند الاقتراب
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

# ========== طفل Pepper متحرك ==========
class MovingPepperKid:
    def __init__(self, name, age, personality, color, position, sim_manager, client):
        self.name = name
        self.age = age
        self.personality = personality
        self.color = color
        self.position = position
        self.sim_manager = sim_manager
        self.client = client
        self.direction = random.choice([(0.1,0), (-0.1,0), (0,0.1), (0,-0.1)])
        self.walk_timer = 0
        
        # إنشاء Pepper كطفل
        self.pepper = sim_manager.spawnPepper(
            client, translation=position, quaternion=[0, 0, 0, 1]
        )
        
        # اسم الطفل
        p.addUserDebugText(f"{name} ({age})", 
                          [position[0], position[1], position[2] + 1.5],
                          [0, 0, 0], textSize=1.2)
        
        print(f"✅ طفل: {name}")
    
    def move_random(self):
        """حركة عشوائية للطفل"""
        self.walk_timer += 1
        if self.walk_timer > 30:
            self.direction = random.choice([(0.1,0), (-0.1,0), (0,0.1), (0,-0.1)])
            self.walk_timer = 0
        
        new_x = self.position[0] + self.direction[0] * 0.05
        new_y = self.position[1] + self.direction[1] * 0.05
        
        # حدود الغرفة
        if abs(new_x) < 4 and abs(new_y) < 4:
            self.position = [new_x, new_y, self.position[2]]
            p.resetBasePositionAndOrientation(self.pepper, self.position, [0,0,0,1])

# ========== غرفة كاملة بأثاث ==========
class FullRoom:
    def __init__(self):
        self.build_floor()
        self.build_walls()
        self.build_furniture()
        self.build_decor()
    
    def build_floor(self):
        # أرضية خشبية
        floor_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[5, 5, 0.1], 
                                        rgbaColor=[0.6, 0.4, 0.2, 1])
        p.createMultiBody(baseVisualShapeIndex=floor_vis, basePosition=[0, 0, 0])
        
        # سجادة
        carpet_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[4, 4, 0.05], 
                                         rgbaColor=[0.8, 0.2, 0.2, 1])
        p.createMultiBody(baseVisualShapeIndex=carpet_vis, basePosition=[0, 0, 0.05])
    
    def build_walls(self):
        # جدران بيج
        wall_color = [0.9, 0.8, 0.7, 1]
        
        # جدار خلفي
        wall_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[5, 0.2, 3], rgbaColor=wall_color)
        p.createMultiBody(baseVisualShapeIndex=wall_vis, basePosition=[0, -5, 1.5])
        
        # جدار أمامي
        p.createMultiBody(baseVisualShapeIndex=wall_vis, basePosition=[0, 5, 1.5])
        
        # جدار أيمن
        wall_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.2, 5, 3], rgbaColor=wall_color)
        p.createMultiBody(baseVisualShapeIndex=wall_vis, basePosition=[5, 0, 1.5])
        
        # جدار أيسر
        p.createMultiBody(baseVisualShapeIndex=wall_vis, basePosition=[-5, 0, 1.5])
        
        # نوافذ
        window_color = [0.5, 0.8, 1, 0.3]
        window_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[1.5, 0.1, 1.5], rgbaColor=window_color)
        p.createMultiBody(baseVisualShapeIndex=window_vis, basePosition=[-3, -4.9, 1.5])
        p.createMultiBody(baseVisualShapeIndex=window_vis, basePosition=[3, -4.9, 1.5])
    
    def build_furniture(self):
        # طاولة كبيرة
        self.add_table([0, 0, 0])
        
        # كراسي حول الطاولة
        self.add_chair([1, 0.5, 0])
        self.add_chair([-1, 0.5, 0])
        self.add_chair([0.5, -1, 0])
        self.add_chair([-0.5, -1, 0])
        
        # رف كتب
        self.add_shelf([3, 3, 0])
        
        # أريكة
        self.add_sofa([-3, -2, 0])
    
    def add_table(self, pos):
        # سطح الطاولة
        table_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[1.2, 0.8, 0.1],
                                         rgbaColor=[0.5, 0.3, 0.1, 1])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=table_vis,
                          basePosition=[pos[0], pos[1], pos[2] + 0.6])
        
        # أرجل
        leg_color = [0.4, 0.2, 0.1, 1]
        for dx, dy in [(-0.8, -0.5), (0.8, -0.5), (-0.8, 0.5), (0.8, 0.5)]:
            leg_vis = p.createVisualShape(p.GEOM_CYLINDER, radius=0.05, length=0.6, rgbaColor=leg_color)
            p.createMultiBody(baseMass=0, baseVisualShapeIndex=leg_vis,
                              basePosition=[pos[0] + dx, pos[1] + dy, pos[2] + 0.3])
    
    def add_chair(self, pos):
        # قاعدة الكرسي
        seat_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.3, 0.3, 0.1],
                                        rgbaColor=[0.3, 0.2, 0.1, 1])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=seat_vis,
                          basePosition=[pos[0], pos[1], pos[2] + 0.3])
        
        # ظهر الكرسي
        back_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.3, 0.1, 0.4],
                                        rgbaColor=[0.4, 0.3, 0.2, 1])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=back_vis,
                          basePosition=[pos[0], pos[1] + 0.2, pos[2] + 0.6])
    
    def add_shelf(self, pos):
        # الرف
        shelf_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[1, 0.3, 1.5],
                                         rgbaColor=[0.4, 0.2, 0.1, 1])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=shelf_vis,
                          basePosition=[pos[0], pos[1], pos[2] + 0.75])
        
        # كتب ملونة
        for i in range(3):
            book_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.1, 0.2, 0.15],
                                            rgbaColor=[random.random(), random.random(), random.random(), 1])
            p.createMultiBody(baseMass=0, baseVisualShapeIndex=book_vis,
                              basePosition=[pos[0] - 0.3 + i*0.3, pos[1] + 0.2, pos[2] + 0.5])
    
    def add_sofa(self, pos):
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
    
    def build_decor(self):
        # نباتات
        green = [0.2, 0.8, 0.2, 1]
        for pos in [[-4, -4, 0], [4, 4, 0], [-4, 4, 0], [4, -4, 0]]:
            plant_vis = p.createVisualShape(p.GEOM_SPHERE, radius=0.3, rgbaColor=green)
            p.createMultiBody(baseMass=0, baseVisualShapeIndex=plant_vis, basePosition=pos)
        
        # ألعاب على الأرض
        toy_colors = [[1,0,0,1], [0,1,0,1], [0,0,1,1]]
        for i, pos in enumerate([[1,1,0.1], [-1,2,0.1], [2,-2,0.1]]):
            toy_vis = p.createVisualShape(p.GEOM_SPHERE, radius=0.15, rgbaColor=toy_colors[i])
            p.createMultiBody(baseMass=0.1, baseVisualShapeIndex=toy_vis, basePosition=pos)

# ========== Pepper الرئيسي المتحرك ==========
class MainMovingPepper:
    def __init__(self):
        print("🚀 تشغيل Pepper في غرفة كاملة...")
        
        # الصوت
        self.voice = VoiceEngine()
        
        # المحاكي
        self.sim_manager = SimulationManager()
        self.client = self.sim_manager.launchSimulation(gui=True)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.loadURDF("plane.urdf")
        
        # الغرفة الكاملة
        self.room = FullRoom()
        
        # Pepper الرئيسي
        self.main_pepper = self.sim_manager.spawnPepper(
            self.client, translation=[-4, -3, 0.2], quaternion=[0, 0, 0, 1]
        )
        
        # أطفال Peppers متحركين
        self.kids = self.create_kids()
        
        # نقاط التجوال في كل الغرفة
        self.walk_points = [
            [-4, -3, 0.2],
            [4, -3, 0.2],
            [4, 4, 0.2],
            [-4, 4, 0.2],
            [-2, 2, 0.2],
            [2, -2, 0.2],
            [0, 0, 0.2],
            [-3, 3, 0.2],
            [3, -3, 0.2]
        ]
        self.current_point = 0
        
        print("✅ Pepper جاهز في غرفة كاملة!")
        self.voice.speak("Welcome to our beautiful playroom!")

    def create_kids(self):
        kids_data = [
            ("Emma", 4, "happy", [1, 0.5, 0.5, 1], [2, 2, 0.2]),
            ("Liam", 5, "curious", [0.5, 1, 0.5, 1], [-2, 3, 0.2]),
            ("Sophia", 3, "shy", [0.5, 0.5, 1, 1], [3, -2, 0.2]),
            ("Noah", 6, "excited", [1, 1, 0.5, 1], [-3, -2, 0.2]),
            ("Mia", 4, "happy", [1, 0.5, 1, 1], [1, -3, 0.2])
        ]
        
        kids = []
        for name, age, personality, color, pos in kids_data:
            kid = MovingPepperKid(name, age, personality, color, pos, self.sim_manager, self.client)
            kids.append(kid)
        
        return kids

    def move_to_point(self, target):
        """تحريك Pepper إلى نقطة"""
        current = self.main_pepper.getPosition()
        dx = target[0] - current[0]
        dy = target[1] - current[1]
        dist = math.sqrt(dx*dx + dy*dy)
        
        if dist > 0.3:
            self.main_pepper.move(0.2 * dx / dist, 0, 0.1 * math.atan2(dy, dx))
            return False
        return True

    def find_nearest_kid(self):
        """أقرب طفل لـ Pepper"""
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
        """التحدث مع طفل"""
        texts = [
            f"Hi {kid.name}! How are you?",
            f"{kid.name}, let's play!",
            f"Hello {kid.name}!",
            f"{kid.name}, you're so cute!",
            f"What do you want to play, {kid.name}?",
            f"{kid.name}, I love your smile!"
        ]
        text = random.choice(texts)
        print(f"🤖 Pepper: {text}")
        self.voice.speak(text)
        self.show_text(text)
        self.wave()

    def run(self):
        print("\n" + "="*70)
        print("🌟 PEPPER في غرفة كاملة - يتحرك والأطفال يتحركون")
        print("="*70 + "\n")
        
        self.voice.speak("I will walk around and play with everyone!")
        
        last_interaction = time.time()
        
        try:
            while True:
                # 1. Pepper يتحرك في الغرفة
                target = self.walk_points[self.current_point]
                if self.move_to_point(target):
                    self.current_point = (self.current_point + 1) % len(self.walk_points)
                    
                    # يتفاعل مع طفل قريب
                    nearest_kid, dist = self.find_nearest_kid()
                    if nearest_kid and dist < 2.0:
                        self.talk_to_kid(nearest_kid)
                        last_interaction = time.time()
                
                # 2. الأطفال يتحركون
                for kid in self.kids:
                    kid.move_random()
                
                # 3. تفاعل عشوائي كل 8 ثواني
                if time.time() - last_interaction > 8:
                    kid = random.choice(self.kids)
                    self.talk_to_kid(kid)
                    last_interaction = time.time()
                
                time.sleep(0.05)
                
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
        finally:
            self.sim_manager.stopSimulation(self.client)

if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════════╗
    ║   🌟 PEPPER في غرفة أطفال كاملة - كل شيء يتحرك 🌟  ║
    ╠══════════════════════════════════════════════════════╣
    ║  • غرفة بأثاث كامل                                   ║
    ║  • 5 أطفال Peppers يتحركون                           ║
    ║  • Pepper الرئيسي يتجول في كل مكان                   ║
    ║  • يتفاعل مع الأطفال عند الاقتراب                    ║
    ╚══════════════════════════════════════════════════════╝
    """)
    
    pepper = MainMovingPepper()
    pepper.run()
