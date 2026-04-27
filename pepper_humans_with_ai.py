#!/usr/bin/env python3
"""
Pepper في غرفة مع أطفال (بشر ثابتين) + AI + حركة يدين سلسة
"""

import time
import pybullet as p
import pybullet_data
import threading
import random
import math
import json
import requests
from qibullet import SimulationManager

# ========== إعدادات ==========
CHAT_API = "https://text.pollinations.ai/v1/chat/completions"

# ========== محرك الصوت ==========
class VoiceEngine:
    def __init__(self):
        self.last_message = ""
    
    def speak(self, text):
        print(f"🤖 Pepper: {text}")
        self.last_message = text

# ========== الذكاء الاصطناعي ==========
class PepperAI:
    def __init__(self, child_name="Yusuf"):
        self.child_name = child_name
        self.conversation_history = []
        self.last_request_time = 0
    
    def get_response(self, user_input):
        """الحصول على رد من الذكاء الاصطناعي"""
        
        # Rate limit
        time_since_last = time.time() - self.last_request_time
        if time_since_last < 2:
            time.sleep(2 - time_since_last)
        
        system_prompt = f"""You are Pepper, a friendly robot for a child named {self.child_name} (under 18).

RULES:
1. Respond in 1-2 short, simple English sentences
2. Be kind, patient, and encouraging
3. Use the child's name: {self.child_name}
4. If child asks "how to" do something, say "I'll show you a video!"
5. Keep responses positive and educational

Child's message: {user_input}"""
        
        data = {
            "model": "openai",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            "temperature": 0.7,
            "max_tokens": 80
        }
        
        try:
            response = requests.post(CHAT_API, json=data, timeout=15)
            self.last_request_time = time.time()
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            else:
                return f"That's a great question, {self.child_name}! Tell me more!"
        except:
            return f"I'm here to help you learn, {self.child_name}! What would you like to know?"

# ========== إنشاء أطفال بشكل إنسان (ثابتين) ==========
class HumanKid:
    """طفل بشكل إنسان - ثابت"""
    
    def __init__(self, name, color, position):
        self.name = name
        self.color = color
        self.position = position
        self.body_id = None
        self.head_id = None
    
    def create_in_sim(self):
        """إنشاء الطفل في المحاكاة"""
        
        # الجسم (شكل إنسان - مستطيل)
        body_vis = p.createVisualShape(
            p.GEOM_BOX, 
            halfExtents=[0.2, 0.15, 0.4], 
            rgbaColor=self.color
        )
        self.body_id = p.createMultiBody(
            baseMass=0, 
            baseVisualShapeIndex=body_vis, 
            basePosition=[self.position[0], self.position[1], self.position[2] + 0.2]
        )
        
        # الرأس (كرة)
        head_vis = p.createVisualShape(
            p.GEOM_SPHERE, 
            radius=0.15, 
            rgbaColor=[1, 0.85, 0.7, 1]  # لون بشرة
        )
        self.head_id = p.createMultiBody(
            baseMass=0, 
            baseVisualShapeIndex=head_vis, 
            basePosition=[self.position[0], self.position[1], self.position[2] + 0.55]
        )
        
        # عينان (نقط سوداء صغيرة)
        eye_left = p.createVisualShape(
            p.GEOM_SPHERE, 
            radius=0.04, 
            rgbaColor=[0, 0, 0, 1]
        )
        p.createMultiBody(
            baseMass=0, 
            baseVisualShapeIndex=eye_left, 
            basePosition=[self.position[0] - 0.07, self.position[1] + 0.08, self.position[2] + 0.62]
        )
        
        eye_right = p.createVisualShape(
            p.GEOM_SPHERE, 
            radius=0.04, 
            rgbaColor=[0, 0, 0, 1]
        )
        p.createMultiBody(
            baseMass=0, 
            baseVisualShapeIndex=eye_right, 
            basePosition=[self.position[0] + 0.07, self.position[1] + 0.08, self.position[2] + 0.62]
        )
        
        # فم (خط صغير - باستخدام كرة صغيرة)
        mouth = p.createVisualShape(
            p.GEOM_SPHERE, 
            radius=0.03, 
            rgbaColor=[0.8, 0.2, 0.2, 1]
        )
        p.createMultiBody(
            baseMass=0, 
            baseVisualShapeIndex=mouth, 
            basePosition=[self.position[0], self.position[1] + 0.05, self.position[2] + 0.52]
        )
        
        # اسم الطفل فوق رأسه
        p.addUserDebugText(
            self.name,
            [self.position[0], self.position[1], self.position[2] + 0.85],
            [0, 0, 0],
            textSize=0.8,
            lifeTime=0
        )

# ========== غرفة كاملة ==========
class FullRoom:
    def __init__(self):
        self.kids = []
        self.build_floor()
        self.build_walls()
        self.build_furniture()
        self.build_kids()
    
    def build_floor(self):
        """أرضية"""
        p.loadURDF("plane.urdf", [0, 0, -0.05])
        
        # سجادة
        carpet = p.createVisualShape(p.GEOM_BOX, halfExtents=[4, 3.5, 0.02], rgbaColor=[0.5, 0.3, 0.2, 1])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=carpet, basePosition=[0, 0, 0])
    
    def build_walls(self):
        """جدران"""
        # جدار خلفي
        wall_back = p.createVisualShape(p.GEOM_BOX, halfExtents=[5, 0.1, 2.2], rgbaColor=[0.85, 0.85, 0.9, 1])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=wall_back, basePosition=[0, -3.8, 1.1])
        
        # جدار أمامي
        wall_front = p.createVisualShape(p.GEOM_BOX, halfExtents=[5, 0.1, 2.2], rgbaColor=[0.85, 0.85, 0.9, 1])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=wall_front, basePosition=[0, 3.8, 1.1])
        
        # جدار يمين
        wall_right = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.1, 3.8, 2.2], rgbaColor=[0.85, 0.85, 0.9, 1])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=wall_right, basePosition=[4.8, 0, 1.1])
        
        # جدار يسار
        wall_left = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.1, 3.8, 2.2], rgbaColor=[0.85, 0.85, 0.9, 1])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=wall_left, basePosition=[-4.8, 0, 1.1])
    
    def build_furniture(self):
        """أثاث"""
        # طاولة
        table = p.createVisualShape(p.GEOM_BOX, halfExtents=[1.2, 0.8, 0.4], rgbaColor=[0.6, 0.4, 0.2, 1])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=table, basePosition=[2, 1.5, 0.4])
        
        # كراسي
        chair = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.4, 0.4, 0.3], rgbaColor=[0.5, 0.3, 0.1, 1])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=chair, basePosition=[1.5, 1.8, 0.15])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=chair, basePosition=[2.5, 1.8, 0.15])
        
        # رف كتب
        shelf = p.createVisualShape(p.GEOM_BOX, halfExtents=[1.5, 0.3, 1], rgbaColor=[0.6, 0.4, 0.2, 1])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=shelf, basePosition=[-2.5, 2, 0.5])
        
        # سلة ألعاب
        basket = p.createVisualShape(p.GEOM_CYLINDER, radius=0.4, length=0.4, rgbaColor=[0.3, 0.6, 0.3, 1])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=basket, basePosition=[-1.5, -2, 0.2])
    
    def build_kids(self):
        """إضافة أطفال بشكل إنسان"""
        
        kids_data = [
            ("Ahmed", [1, -1.5, 0], [1, 0.6, 0.4, 1]),      # بني
            ("Sara", [-1, 1, 0], [1, 0.7, 0.8, 1]),         # وردي
            ("Yusuf", [0, -2, 0], [0.4, 0.7, 1, 1]),        # أزرق
            ("Layla", [2.5, -0.5, 0], [1, 0.5, 0.9, 1]),    # وردي غامق
            ("Omar", [-2.5, -1, 0], [0.4, 0.8, 0.4, 1]),    # أخضر
            ("Fatima", [3, 2, 0], [1, 0.8, 0.5, 1]),        # برتقالي
            ("Ali", [-3, 1.5, 0], [0.6, 0.6, 0.8, 1]),      # أرجواني
        ]
        
        for name, pos, color in kids_data:
            kid = HumanKid(name, color, pos)
            kid.create_in_sim()
            self.kids.append(kid)
            print(f"👧 Added child: {name}")

# ========== Pepper مع حركة يدين سلسة ==========
class PepperWithArms:
    def __init__(self):
        self.voice = VoiceEngine()
        self.ai = PepperAI(child_name="Yusuf")
        self.simulation_manager = SimulationManager()
        self.client = self.simulation_manager.launchSimulation(gui=True)
        p.setRealTimeSimulation(1)
        p.resetDebugVisualizerCamera(cameraDistance=6, cameraYaw=45, cameraPitch=-30, cameraTargetPosition=[0, 0, 1])
        
        print("\n" + "="*50)
        print("🏠 Building room with real kids...")
        self.room = FullRoom()
        
        print("🤖 Loading Pepper...")
        self.pepper = self.simulation_manager.spawnPepper(self.client, spawn_ground=True)
        self.pepper.setPosition([0, 0, 0.8])
        self.pepper.goToPosture("Stand", 0.5)
        
        self.is_talking = False
        self.arm_angle = 0
        self.arm_direction = 1
        
        print("\n✅ Pepper is ready in the room!")
        print("📝 Type in the terminal to talk to Pepper!")
        print("👋 Pepper moves his arms smoothly while talking")
        print("👧 There are real kids in the room (with names)")
        print("💬 Type 'exit' to quit")
        print("="*50)
    
    def smooth_arm_movement(self):
        """حركة يدين سلسة أثناء الكلام"""
        while True:
            if self.is_talking:
                # حركة سلسة فوق وتحت
                self.arm_angle += 0.05 * self.arm_direction
                if self.arm_angle > 0.8:
                    self.arm_angle = 0.8
                    self.arm_direction = -1
                elif self.arm_angle < 0:
                    self.arm_angle = 0
                    self.arm_direction = 1
                
                # تحريك الذراعين
                try:
                    self.pepper.setAngles("LShoulderPitch", self.arm_angle, 0.1)
                    self.pepper.setAngles("RShoulderPitch", self.arm_angle, 0.1)
                except:
                    pass
            else:
                # إعادة الذراعين للأسفل ببطء
                if self.arm_angle > 0:
                    self.arm_angle -= 0.03
                    if self.arm_angle < 0:
                        self.arm_angle = 0
                    try:
                        self.pepper.setAngles("LShoulderPitch", self.arm_angle, 0.1)
                        self.pepper.setAngles("RShoulderPitch", self.arm_angle, 0.1)
                    except:
                        pass
            
            time.sleep(0.05)
    
    def move_head_naturally(self):
        """حركة رأس طبيعية"""
        t = 0
        while True:
            t += 0.02
            try:
                # حركة الرأس يمين/يسار
                yaw = math.sin(t) * 0.5
                pitch = math.sin(t * 0.7) * 0.2
                self.pepper.setAngles("HeadYaw", yaw, 0.1)
                self.pepper.setAngles("HeadPitch", pitch, 0.1)
            except:
                pass
            time.sleep(0.05)
    
    def speak_with_arms(self, text):
        """نطق النص مع تحريك اليدين"""
        self.is_talking = True
        print(f"🤖 Pepper: {text}")
        
        # عرض النص فوق رأس Pepper
        pos = self.pepper.getPosition()
        p.addUserDebugText(
            text[:50],
            [pos[0], pos[1], pos[2] + 1.2],
            [0, 0, 0],
            textSize=1,
            lifeTime=3
        )
        
        # محاكاة وقت الكلام
        time.sleep(min(len(text) * 0.1, 3))
        self.is_talking = False
    
    def run(self):
        """تشغيل Pepper مع المحادثة"""
        
        # تشغيل حركة الذراعين في Thread منفصل
        arm_thread = threading.Thread(target=self.smooth_arm_movement, daemon=True)
        arm_thread.start()
        
        # تشغيل حركة الرأس في Thread منفصل
        head_thread = threading.Thread(target=self.move_head_naturally, daemon=True)
        head_thread.start()
        
        # رسالة ترحيب
        self.speak_with_arms("Hello everyone! I'm Pepper! Let's learn and play together!")
        
        # محاكاة الحركة
        def run_simulation():
            while True:
                p.stepSimulation()
                time.sleep(1./240.)
        
        sim_thread = threading.Thread(target=run_simulation, daemon=True)
        sim_thread.start()
        
        # محادثة مع المستخدم
        while True:
            try:
                user_input = input("\n👶 You: ").strip()
                
                if user_input.lower() in ['exit', 'quit', 'bye']:
                    self.speak_with_arms("Goodbye! It was nice talking with you!")
                    time.sleep(2)
                    break
                
                if not user_input:
                    continue
                
                # التفكير
                self.speak_with_arms("Let me think about that...")
                time.sleep(1)
                
                # الحصول على رد من AI
                response = self.ai.get_response(user_input)
                
                # الرد مع حركة اليدين
                self.speak_with_arms(response)
                
            except KeyboardInterrupt:
                print("\n")
                self.speak_with_arms("Goodbye! See you next time!")
                break

if __name__ == "__main__":
    pepper = PepperWithArms()
    pepper.run()
