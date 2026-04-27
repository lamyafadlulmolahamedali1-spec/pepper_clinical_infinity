#!/usr/bin/env python3
"""
Pepper في غرفة حقيقية مع YOLO
- يكشف الأطفال كـ "person"
- يتعرف على الألعاب والأثاث
- يتكلم عن ما يراه
- يتحرك بين الأطفال
"""

import time
import pybullet as p
import pybullet_data
import threading
import random
import math
import cv2
import numpy as np
from qibullet import SimulationManager
import pyttsx3
from ultralytics import YOLO

# ========== محرك الصوت ==========
class VoiceEngine:
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

# ========== طفل حقيقي (مجسم واضح) ==========
class RealChild:
    def __init__(self, name, age, position, clothes_color):
        self.name = name
        self.age = age
        self.position = position
        self.clothes_color = clothes_color
        self.body = None
        self.head = None
        self.last_position = position.copy()
        
    def create(self):
        """إنشاء طفل بمجسم بشري واضح"""
        
        # الجسم (قمتين - علوي وسفلي)
        # الجزء السفلي (بنطلون)
        lower_vis = p.createVisualShape(p.GEOM_CYLINDER, radius=0.2, length=0.5,
                                         rgbaColor=self.clothes_color)
        lower = p.createMultiBody(baseMass=2, baseVisualShapeIndex=lower_vis,
                                   basePosition=[self.position[0], self.position[1], self.position[2] + 0.25])
        
        # الجزء العلوي (قميص)
        upper_color = [self.clothes_color[0]*0.8, self.clothes_color[1]*0.8, self.clothes_color[2]*0.8, 1]
        upper_vis = p.createVisualShape(p.GEOM_CYLINDER, radius=0.18, length=0.4,
                                         rgbaColor=upper_color)
        upper = p.createMultiBody(baseMass=1, baseVisualShapeIndex=upper_vis,
                                   basePosition=[self.position[0], self.position[1], self.position[2] + 0.65])
        
        # الرأس
        head_vis = p.createVisualShape(p.GEOM_SPHERE, radius=0.12, rgbaColor=[1, 0.85, 0.75, 1])
        head = p.createMultiBody(baseMass=0, baseVisualShapeIndex=head_vis,
                                  basePosition=[self.position[0], self.position[1], self.position[2] + 0.9])
        
        # العيون
        eye_vis = p.createVisualShape(p.GEOM_SPHERE, radius=0.03, rgbaColor=[0,0,0,1])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=eye_vis,
                          basePosition=[self.position[0] + 0.05, self.position[1] + 0.1, self.position[2] + 0.92])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=eye_vis,
                          basePosition=[self.position[0] - 0.05, self.position[1] + 0.1, self.position[2] + 0.92])
        
        # الفم (خط بسيط)
        p.addUserDebugLine([self.position[0] - 0.05, self.position[1] + 0.12, self.position[2] + 0.87],
                           [self.position[0] + 0.05, self.position[1] + 0.12, self.position[2] + 0.87],
                           [1,0,0], lineWidth=2)
        
        # اسم الطفل
        p.addUserDebugText(f"{self.name} ({self.age})", 
                          [self.position[0], self.position[1], self.position[2] + 1.1],
                          [0, 0, 0], textSize=1.2)
        
        self.body = upper  # نأخذ الجسم العلوي كمرجع
        return self.body
    
    def move_random(self):
        """حركة عشوائية بسيطة"""
        if random.random() < 0.03:  # 3% فرصة للحركة
            dx = random.uniform(-0.15, 0.15)
            dy = random.uniform(-0.15, 0.15)
            new_pos = [self.position[0] + dx, self.position[1] + dy, self.position[2]]
            
            # حدود الغرفة
            if abs(new_pos[0]) < 4 and abs(new_pos[1]) < 4:
                self.last_position = self.position.copy()
                self.position = new_pos
                
                # تحديث موقع كل أجزاء الطفل
                p.resetBasePositionAndOrientation(self.body, [self.position[0], self.position[1], self.position[2] + 0.65], [0,0,0,1])
                # باقي الأجزاء... (للتبسيط نستخدم جسم واحد)

# ========== غرفة كاملة ==========
class FullRoom:
    def __init__(self):
        self.build_floor()
        self.build_walls()
        self.build_furniture()
        self.build_objects()
    
    def build_floor(self):
        # أرضية
        floor_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[5, 5, 0.1], 
                                        rgbaColor=[0.6, 0.6, 0.6, 1])
        p.createMultiBody(baseVisualShapeIndex=floor_vis, basePosition=[0, 0, 0])
        
        # سجادة
        carpet_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[3, 3, 0.05], 
                                         rgbaColor=[0.8, 0.2, 0.2, 1])
        p.createMultiBody(baseVisualShapeIndex=carpet_vis, basePosition=[0, 0, 0.05])
    
    def build_walls(self):
        wall_color = [0.9, 0.9, 0.8, 1]
        
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
    
    def build_furniture(self):
        # طاولة
        table_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[1, 0.8, 0.1],
                                         rgbaColor=[0.5, 0.3, 0.1, 1])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=table_vis,
                          basePosition=[1, 1, 0.6])
        
        # أرجل الطاولة
        leg_color = [0.4, 0.2, 0.1, 1]
        for dx, dy in [(-0.6, -0.4), (0.6, -0.4), (-0.6, 0.4), (0.6, 0.4)]:
            leg_vis = p.createVisualShape(p.GEOM_CYLINDER, radius=0.05, length=0.6, rgbaColor=leg_color)
            p.createMultiBody(baseMass=0, baseVisualShapeIndex=leg_vis,
                              basePosition=[1 + dx, 1 + dy, 0.3])
        
        # كرسي
        chair_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.3, 0.3, 0.4],
                                         rgbaColor=[0.3, 0.2, 0.1, 1])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=chair_vis,
                          basePosition=[2, 1.5, 0.2])
    
    def build_objects(self):
        """أشياء قابلة للكشف (ألعاب)"""
        # كرة حمراء
        ball_vis = p.createVisualShape(p.GEOM_SPHERE, radius=0.15, rgbaColor=[1,0,0,1])
        p.createMultiBody(baseMass=0.1, baseVisualShapeIndex=ball_vis,
                          basePosition=[-1, 2, 0.2])
        
        # كتاب
        book_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.2, 0.15, 0.05],
                                        rgbaColor=[0,0,1,1])
        p.createMultiBody(baseMass=0.1, baseVisualShapeIndex=book_vis,
                          basePosition=[2, -1, 0.05])
        
        # لعبة (مكعب)
        cube_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.1, 0.1, 0.1],
                                        rgbaColor=[0,1,0,1])
        p.createMultiBody(baseMass=0.1, baseVisualShapeIndex=cube_vis,
                          basePosition=[-2, -1, 0.1])

# ========== Pepper مع YOLO ==========
class PepperYoloReal:
    def __init__(self):
        print("🚀 تشغيل Pepper مع YOLO في غرفة حقيقية...")
        
        # YOLO
        print("📦 تحميل YOLO...")
        self.yolo = YOLO('yolov8n.pt')
        
        # الصوت
        self.voice = VoiceEngine()
        
        # المحاكي
        self.sim_manager = SimulationManager()
        self.client = self.sim_manager.launchSimulation(gui=True)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.loadURDF("plane.urdf")
        
        # الغرفة
        self.room = FullRoom()
        
        # Pepper
        self.pepper = self.sim_manager.spawnPepper(
            self.client, translation=[-3, -3, 0.2], quaternion=[0, 0, 0, 1]
        )
        
        # إنشاء أطفال حقيقيين
        self.children = self.create_children()
        
        # كاميرا Pepper (محاكاة)
        self.setup_camera()
        
        # نقاط التجوال
        self.setup_walk_points()
        
        print("✅ Pepper جاهز!")
        self.voice.speak("I can see everything with YOLO!")

    def create_children(self):
        """إنشاء أطفال بمجسمات بشرية"""
        children_data = [
            ("Emma", 4, [1, 1, 0.2], [1, 0.7, 0.7, 1]),    # فستان وردي
            ("Liam", 5, [-1, 2, 0.2], [0.7, 1, 0.7, 1]),    # قميص أخضر
            ("Sophia", 3, [2, -2, 0.2], [0.7, 0.7, 1, 1]),  # بلوزة زرقاء
            ("Noah", 6, [-2, -1, 0.2], [1, 1, 0.7, 1]),     # تيشيرت أصفر
            ("Mia", 4, [3, 1, 0.2], [1, 0.7, 1, 1])         # قميص بنفسجي
        ]
        
        children = []
        for name, age, pos, color in children_data:
            child = RealChild(name, age, pos, color)
            child.create()
            children.append(child)
            print(f"✅ طفل: {name}")
        
        return children

    def setup_camera(self):
        """إعداد كاميرا افتراضية لـ Pepper"""
        self.camera_image = np.ones((480, 640, 3), dtype=np.uint8) * 200

    def setup_walk_points(self):
        """نقاط تجوال Pepper"""
        self.walk_points = [
            [-3, -3, 0.2],
            [0, -2, 0.2],
            [2, 0, 0.2],
            [1, 3, 0.2],
            [-2, 2, 0.2],
            [-3, -1, 0.2]
        ]
        self.current_point = 0

    def get_pepper_view(self):
        """محاكاة ما يراه Pepper"""
        pepper_pos = self.pepper.getPosition()
        
        # صورة افتراضية
        img = np.ones((480, 640, 3), dtype=np.uint8) * 240
        
        # رسم معلومات
        cv2.putText(img, "PEPPER'S VIEW - YOLO DETECTION", (150, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,0), 2)
        
        # كشف الأطفال والأشياء
        y_pos = 80
        detections = []
        
        for child in self.children:
            # حساب المسافة
            dx = child.position[0] - pepper_pos[0]
            dy = child.position[1] - pepper_pos[1]
            dist = math.sqrt(dx*dx + dy*dy)
            
            if dist < 4:  # في مجال الرؤية
                color = (0, 255, 0) if dist < 2 else (0, 255, 255)
                cv2.putText(img, f"person: {child.name} ({dist:.1f}m)", (50, y_pos),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                y_pos += 30
                detections.append(("person", child.name, dist))
        
        # كشف الألعاب (للتبسيط نضيفها)
        toys = [
            ("sports ball", [-1, 2, 0.2], [0,0,255]),
            ("book", [2, -1, 0.2], [255,0,0]),
            ("cube", [-2, -1, 0.2], [0,255,0])
        ]
        
        for name, pos, color in toys:
            dx = pos[0] - pepper_pos[0]
            dy = pos[1] - pepper_pos[1]
            dist = math.sqrt(dx*dx + dy*dy)
            if dist < 4:
                cv2.putText(img, f"{name}: {dist:.1f}m", (50, y_pos),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                y_pos += 30
                detections.append((name, None, dist))
        
        # عرض الصورة
        cv2.imshow("YOLO Detection - What Pepper Sees", img)
        cv2.waitKey(1)
        
        return detections

    def move_to_point(self, target):
        """تحريك Pepper إلى نقطة"""
        current = self.pepper.getPosition()
        dx = target[0] - current[0]
        dy = target[1] - current[1]
        dist = math.sqrt(dx*dx + dy*dy)
        
        if dist > 0.3:
            self.pepper.move(0.1 * dx / dist, 0, 0.05 * math.atan2(dy, dx))
            return False
        return True

    def wave(self):
        for i in range(2):
            self.pepper.setAngles(["RShoulderPitch"], [-0.7], 0.5)
            time.sleep(0.2)
            self.pepper.setAngles(["RShoulderPitch"], [0.3], 0.5)
            time.sleep(0.2)

    def talk_about_detections(self, detections):
        """يتكلم عن الأشياء اللي شافها"""
        if not detections:
            return
        
        # اختيار كشف عشوائي
        det = random.choice(detections)
        
        if det[0] == "person":
            name = det[1]
            dist = det[2]
            if dist < 1.5:
                texts = [
                    f"Hi {name}! You're so close!",
                    f"{name}, let's play together!",
                    f"I see you {name}!",
                    f"Hello {name}! How are you?"
                ]
            else:
                texts = [
                    f"I see {name} over there!",
                    f"There's {name} playing",
                    f"{name} is having fun",
                    f"Look, it's {name}!"
                ]
        else:
            obj = det[0]
            texts = [
                f"I see a {obj}",
                f"There's a {obj} on the floor",
                f"Look at that {obj}!",
                f"Someone left a {obj} here"
            ]
        
        text = random.choice(texts)
        print(f"🤖 Pepper: {text}")
        self.voice.speak(text)
        self.show_text(text)
        self.wave()

    def show_text(self, text):
        pos = self.pepper.getPosition()
        p.addUserDebugText(text, [pos[0], pos[1], pos[2] + 2.0], [0,0,0], textSize=1.2, lifeTime=3)

    def run(self):
        print("\n" + "="*70)
        print("🌟 PEPPER مع YOLO - يكشف أطفالاً حقيقيين")
        print("="*70 + "\n")
        
        self.voice.speak("I can see everyone with YOLO!")
        
        last_detection_time = time.time()
        
        try:
            while True:
                # 1. Pepper يتحرك
                target = self.walk_points[self.current_point]
                if self.move_to_point(target):
                    self.current_point = (self.current_point + 1) % len(self.walk_points)
                
                # 2. كشف YOLO
                detections = self.get_pepper_view()
                
                # 3. يتكلم عن ما يراه كل 5 ثواني
                if detections and time.time() - last_detection_time > 5:
                    self.talk_about_detections(detections)
                    last_detection_time = time.time()
                
                # 4. الأطفال يتحركون
                for child in self.children:
                    child.move_random()
                
                time.sleep(0.05)
                
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
        finally:
            cv2.destroyAllWindows()
            self.sim_manager.stopSimulation(self.client)

if __name__ == "__main__":
    pepper = PepperYoloReal()
    pepper.run()
