#!/usr/bin/env python3
"""
PEPPER WITH EVERYTHING - جميع المشاريع في ملف واحد
- غرفة كاملة (جدران، طاولة، كراسي، دولاب، مراية)
- بالونات طائرة
- مجسمات ملونة تمشي (دائرة + مستطيلات)
- محادثة ذكية
- تعليم
- مساعدة طبية
- رقص
- حركات سلسة
"""

import time
import math
import random
import threading
import pyttsx3
import json
import urllib.request
import urllib.parse
import pybullet as p
import pybullet_data
from qibullet import SimulationManager

# ========== الصوت ==========
engine = pyttsx3.init()
engine.setProperty('rate', 150)
engine.setProperty('volume', 0.9)

def speak(text):
    print(f"🔊 Pepper: {text}")
    engine.say(text)
    engine.runAndWait()

# ========== المحادثة الذكية ==========
def get_ai_response(message):
    try:
        url = f"https://api.popcat.xyz/chat?msg={urllib.parse.quote(message)}"
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.loads(response.read().decode())
            return data.get("response", "That's interesting! Tell me more! 😊")
    except:
        responses = {
            "hello": "Hello! I'm Pepper! Welcome to my room!",
            "how are you": "I'm so happy to see you!",
            "dance": "Let's dance together! 🕺",
            "teach": "I love teaching! What would you like to learn?",
            "medical": "I can help you relax and breathe.",
        }
        for key in responses:
            if key in message.lower():
                return responses[key]
        return f"That's interesting! Tell me more!"

# ========== مجسم شخص بأشكال هندسية ==========
class GeometricPerson:
    def __init__(self, x, y, color, name=""):
        self.x = x
        self.y = y
        self.color = color
        self.name = name
        self.body_parts = []
        self.direction = random.choice([-0.015, 0.015])
        self.create_person()
    
    def create_person(self):
        # الرأس (دائرة)
        head = p.createVisualShape(p.GEOM_SPHERE, radius=0.13, rgbaColor=self.color)
        head_body = p.createMultiBody(baseMass=0.3, baseVisualShapeIndex=head, basePosition=[self.x, self.y, 0.95])
        self.body_parts.append(head_body)
        
        # الجسم (مستطيل)
        body = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.2, 0.14, 0.4], rgbaColor=self.color)
        body_body = p.createMultiBody(baseMass=0.3, baseVisualShapeIndex=body, basePosition=[self.x, self.y, 0.6])
        self.body_parts.append(body_body)
        
        # الذراع الأيمن
        right_arm = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.07, 0.07, 0.32], rgbaColor=self.color)
        right_arm_body = p.createMultiBody(baseMass=0.2, baseVisualShapeIndex=right_arm, basePosition=[self.x + 0.26, self.y, 0.72])
        self.body_parts.append(right_arm_body)
        
        # الذراع الأيسر
        left_arm = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.07, 0.07, 0.32], rgbaColor=self.color)
        left_arm_body = p.createMultiBody(baseMass=0.2, baseVisualShapeIndex=left_arm, basePosition=[self.x - 0.26, self.y, 0.72])
        self.body_parts.append(left_arm_body)
        
        # الرجل اليمنى
        right_leg = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.09, 0.09, 0.32], rgbaColor=self.color)
        right_leg_body = p.createMultiBody(baseMass=0.2, baseVisualShapeIndex=right_leg, basePosition=[self.x + 0.12, self.y, 0.28])
        self.body_parts.append(right_leg_body)
        
        # الرجل اليسرى
        left_leg = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.09, 0.09, 0.32], rgbaColor=self.color)
        left_leg_body = p.createMultiBody(baseMass=0.2, baseVisualShapeIndex=left_leg, basePosition=[self.x - 0.12, self.y, 0.28])
        self.body_parts.append(left_leg_body)
    
    def walk(self):
        self.x += self.direction
        if self.x > 3.5 or self.x < -3.5:
            self.direction = -self.direction
            self.x += self.direction
        for part in self.body_parts:
            pos, ori = p.getBasePositionAndOrientation(part)
            p.resetBasePositionAndOrientation(part, [self.x, self.y, pos[2]], ori)

# ========== إنشاء غرفة كاملة ==========
def create_full_room():
    """إنشاء غرفة بجدران وأثاث كامل"""
    
    p.setAdditionalSearchPath(pybullet_data.getDataPath())
    p.loadURDF("plane.urdf")
    p.setGravity(0, 0, -9.81)
    
    # ===== الجدران الأربعة =====
    # جدار شمالي
    wall_north = p.createVisualShape(p.GEOM_BOX, halfExtents=[5, 0.1, 2], rgbaColor=[0.8, 0.75, 0.7, 1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=wall_north, basePosition=[0, -4.5, 1])
    
    # جدار جنوبي
    wall_south = p.createVisualShape(p.GEOM_BOX, halfExtents=[5, 0.1, 2], rgbaColor=[0.8, 0.75, 0.7, 1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=wall_south, basePosition=[0, 4.5, 1])
    
    # جدار شرقي
    wall_east = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.1, 5, 2], rgbaColor=[0.8, 0.75, 0.7, 1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=wall_east, basePosition=[4.5, 0, 1])
    
    # جدار غربي
    wall_west = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.1, 5, 2], rgbaColor=[0.8, 0.75, 0.7, 1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=wall_west, basePosition=[-4.5, 0, 1])
    
    # ===== طاولة في الجنب =====
    table_top = p.createVisualShape(p.GEOM_BOX, halfExtents=[1, 0.8, 0.1], rgbaColor=[0.5, 0.3, 0.1, 1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=table_top, basePosition=[3, 2.5, 0.55])
    
    for leg_x, leg_y in [(2.2, 2.2), (2.2, 2.8), (3.8, 2.2), (3.8, 2.8)]:
        leg = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.08, 0.08, 0.5], rgbaColor=[0.4, 0.2, 0.05, 1])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=leg, basePosition=[leg_x, leg_y, 0.25])
    
    # ===== كراسي =====
    chair_positions = [(2.5, 1.8), (3.5, 1.8), (2.5, 3.2), (3.5, 3.2)]
    for cx, cy in chair_positions:
        seat = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.35, 0.35, 0.08], rgbaColor=[0.6, 0.4, 0.2, 1])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=seat, basePosition=[cx, cy, 0.25])
        back = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.08, 0.35, 0.35], rgbaColor=[0.6, 0.4, 0.2, 1])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=back, basePosition=[cx, cy - 0.3, 0.55])
    
    # ===== دولاب =====
    cabinet = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.7, 0.4, 1.2], rgbaColor=[0.4, 0.3, 0.2, 1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=cabinet, basePosition=[-3.2, -3, 0.6])
    
    # ===== مراية =====
    mirror = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.6, 0.05, 0.9], rgbaColor=[0.9, 0.9, 1, 0.7])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=mirror, basePosition=[0, -4.4, 1.2])
    
    # ===== بالونات (15 بالون طائر) =====
    colors = [[1,0,0,1], [0,1,0,1], [0,0,1,1], [1,1,0,1], [1,0.5,0,1], [0.8,0.2,0.8,1], [0.2,0.8,0.8,1]]
    balloons = []
    for i in range(15):
        x = random.uniform(-3.5, 3.5)
        y = random.uniform(-3.5, 3.5)
        color = colors[i % len(colors)]
        balloon = p.createVisualShape(p.GEOM_SPHERE, radius=0.1, rgbaColor=color)
        balloon_body = p.createMultiBody(baseMass=0.05, baseVisualShapeIndex=balloon, basePosition=[x, y, random.uniform(0.5, 1.8)])
        balloons.append(balloon_body)
    
    print("✅ غرفة كاملة: جدران، طاولة، كراسي، دولاب، مراية، 15 بالون!")
    return balloons

# ========== تحريك البالونات ==========
def animate_balloons(balloons):
    while True:
        for b in balloons:
            pos, _ = p.getBasePositionAndOrientation(b)
            new_z = pos[2] + 0.005
            if new_z > 1.8:
                new_z = 0.3
            p.resetBasePositionAndOrientation(b, [pos[0], pos[1], new_z], [0,0,0,1])
        p.stepSimulation()
        time.sleep(1/50.)

# ========== تحريك المجسمات ==========
def move_people(people):
    while True:
        for person in people:
            person.walk()
        time.sleep(0.05)

# ========== كل حركات Pepper ==========
class PepperActions:
    def __init__(self, pepper):
        self.pepper = pepper
    
    def wave(self):
        for angle in [0.3, 0.6, 0.9, 0.6, 0.3, 0]:
            try:
                self.pepper.setAngles("RShoulderPitch", angle, 0.1)
                time.sleep(0.08)
            except:
                pass
    
    def dance_happy(self):
        moves = [(0.5, 0.3), (1.0, 0.5), (1.2, 0.8), (0.8, 0.5), (0.3, 0.2), (0, 0)]
        for l, r in moves:
            try:
                self.pepper.setAngles("LShoulderPitch", l, 0.1)
                self.pepper.setAngles("RShoulderPitch", r, 0.1)
                time.sleep(0.12)
            except:
                pass
    
    def dance_robot(self):
        for i in range(4):
            try:
                self.pepper.setAngles("LShoulderRoll", 0.5, 0.1)
                self.pepper.setAngles("RShoulderRoll", -0.5, 0.1)
                time.sleep(0.2)
                self.pepper.setAngles("LShoulderRoll", -0.5, 0.1)
                self.pepper.setAngles("RShoulderRoll", 0.5, 0.1)
                time.sleep(0.2)
            except:
                pass
    
    def move_head(self):
        try:
            self.pepper.setAngles("HeadYaw", 0.5, 0.1)
            time.sleep(0.3)
            self.pepper.setAngles("HeadYaw", -0.5, 0.1)
            time.sleep(0.3)
            self.pepper.setAngles("HeadYaw", 0, 0.1)
        except:
            pass
    
    def raise_arms(self):
        try:
            self.pepper.setAngles("RShoulderPitch", 1.2, 0.1)
            self.pepper.setAngles("LShoulderPitch", 1.2, 0.1)
            time.sleep(0.8)
            self.pepper.setAngles("RShoulderPitch", 0, 0.1)
            self.pepper.setAngles("LShoulderPitch", 0, 0.1)
        except:
            pass

# ========== التحكم ==========
def command_listener(pepper_actions):
    print("\n" + "="*60)
    print("🎮 الأوامر المتاحة:")
    print("   hello  = يقول Hello")
    print("   wave   = يلوح")
    print("   dance  = يرقص")
    print("   teach  = تعليم أرقام")
    print("   medical = مساعدة طبية")
    print("   vision = يوصف الغرفة")
    print("   exit   = خروج")
    print("="*60 + "\n")
    
    while True:
        try:
            cmd = input("👤 You: ").strip().lower()
            
            if cmd == 'exit':
                speak("Goodbye! See you later!")
                break
            elif cmd == 'hello':
                speak("Hello! I'm Pepper! Welcome to my room!")
                pepper_actions.move_head()
            elif cmd == 'wave':
                pepper_actions.wave()
                speak("Hello!")
            elif cmd == 'dance':
                speak("Let's dance!")
                pepper_actions.dance_happy()
                pepper_actions.dance_robot()
            elif cmd == 'teach':
                speak("Let's learn numbers! 1, 2, 3, 4, 5")
                for i in range(1, 6):
                    speak(str(i))
                    time.sleep(0.5)
            elif cmd == 'medical':
                speak("Take a deep breath... in... and out...")
                time.sleep(2)
                speak("You're doing great!")
            elif cmd == 'vision':
                speak("I see a beautiful room with walls, a table, chairs, a cabinet, a mirror, colorful balloons, and colorful geometric people walking!")
            else:
                response = get_ai_response(cmd)
                speak(response)
                
        except KeyboardInterrupt:
            speak("Goodbye!")
            break

# ========== الرئيسي ==========
print("="*60)
print("🤖 PEPPER WITH EVERYTHING - Starting...")
print("="*60)

# تشغيل PyBullet
p.connect(p.GUI)

# إنشاء الغرفة والبالونات
balloons = create_full_room()

# ضبط الكاميرا
p.resetDebugVisualizerCamera(cameraDistance=6, cameraYaw=45, cameraPitch=-30, cameraTargetPosition=[0, 0, 0.8])

# تشغيل qiBullet
sim_manager = SimulationManager()
client_id = sim_manager.launchSimulation(gui=False)

# إضافة Pepper في المنتصف
print("\n🤖 جاري تحميل Pepper...")
pepper = sim_manager.spawnPepper(client_id, translation=[0, 0, 0])
print("✅ Pepper في المنتصف!")

# تهيئة حركات Pepper
pepper_actions = PepperActions(pepper)

# إنشاء مجسمات ملونة تمشي
colors_list = [[1,0.2,0.2,1], [0.2,1,0.2,1], [0.2,0.2,1,1], [1,1,0.2,1], [1,0.5,0.2,1], [0.8,0.2,0.8,1]]
people = []

for i in range(6):
    x = random.uniform(-3, 3)
    y = random.uniform(-3, 3)
    person = GeometricPerson(x, y, colors_list[i], f"Person{i+1}")
    people.append(person)
    print(f"✅ شخص {i+1} ملون يمشي")

# تشغيل الخيوط
balloon_thread = threading.Thread(target=animate_balloons, args=(balloons,), daemon=True)
balloon_thread.start()

people_thread = threading.Thread(target=move_people, args=(people,), daemon=True)
people_thread.start()

print("\n" + "="*60)
print("📍 Pepper في المنتصف!")
print("📍 غرفة كاملة (جدران، طاولة، كراسي، دولاب، مراية)")
print("📍 15 بالون طائر")
print("📍 6 أشخاص ملونين يمشون")
print("📍 جميع المشاريع مضافة!")
print("="*60 + "\n")

speak("Hello! I am Pepper! Welcome to my complete room! Look at the colorful balloons and the people walking around me!")

# بدء التحكم
command_listener(pepper_actions)

print("\n✅ Finished!")
