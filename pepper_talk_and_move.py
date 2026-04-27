#!/usr/bin/env python3
"""
Pepper Talk & Move - بيبر يتحرك ويتكلم بصوت
- يتحرك في الغرفة باستمرار
- يقرأ ما تكتبيه في التيرمينال ويرد بصوت
- يحرك يديه ورأسه حسب الكلام
"""

import time
import random
import math
import threading
import pyttsx3
from qibullet import SimulationManager
import pybullet as p
import pybullet_data

# ========== إعداد الصوت ==========
engine = pyttsx3.init()
engine.setProperty('rate', 150)
engine.setProperty('volume', 1.0)

def speak(text):
    """جعل بيبر يتكلم بصوت"""
    print(f"🔊 Pepper: {text}")
    engine.say(text)
    engine.runAndWait()

# ========== بدء qiBullet ==========
print("🤖 Starting Pepper in qiBullet...")

sim_manager = SimulationManager()
client_id = sim_manager.launchSimulation(gui=True)

# تحميل بيبر
pepper = sim_manager.spawnPepper(client_id, translation=[0, 0, 0], quaternion=[0, 0, 0, 1])

# إضافة أرضية
p.setAdditionalSearchPath(pybullet_data.getDataPath())
p.loadURDF("plane.urdf")
p.setGravity(0, 0, -9.81)
p.setRealTimeSimulation(1)

print("✅ Pepper loaded!")

# ========== غرفة بسيطة ==========
# أرضية
floor = p.createVisualShape(p.GEOM_BOX, halfExtents=[6, 6, 0.05], rgbaColor=[0.4, 0.4, 0.4, 1])
p.createMultiBody(baseMass=0, baseVisualShapeIndex=floor, basePosition=[0, 0, -0.05])

# سجادة
rug = p.createVisualShape(p.GEOM_BOX, halfExtents=[5, 4, 0.02], rgbaColor=[0.3, 0.5, 0.3, 0.7])
p.createMultiBody(baseMass=0, baseVisualShapeIndex=rug, basePosition=[0, 0, 0.01])

print("🏠 Room ready!")

# ========== بالونات ملونة ==========
colors = [[1,0,0,1], [0,1,0,1], [0,0,1,1], [1,1,0,1], [1,0.5,0,1], [1,0,1,1]]
balloons = []
balloon_positions = []

for i in range(12):
    x = random.uniform(-4, 4)
    y = random.uniform(-3, 3)
    z = random.uniform(0.5, 1.8)
    vis = p.createVisualShape(p.GEOM_SPHERE, radius=0.12, rgbaColor=colors[i%6])
    ball = p.createMultiBody(baseMass=0, baseVisualShapeIndex=vis, basePosition=[x, y, z])
    balloons.append(ball)
    balloon_positions.append([x, y, z, random.uniform(0.008, 0.02)])

print("🎈 12 balloons created!")

# ========== كاميرا ==========
p.resetDebugVisualizerCamera(cameraDistance=8, cameraYaw=45, cameraPitch=-35, cameraTargetPosition=[0, 0, 0.8])

# ========== متغيرات الحركة ==========
robot_x, robot_y = 0, 0
t = 0
head_yaw = 0
arm_angle = 0
arm_dir = 1
is_talking = False

# ========== حركات اليدين حسب الكلام ==========
def gesture_wave():
    """حركة تلويح"""
    pepper.setAngles("LShoulderPitch", 1.2, 0.15)
    pepper.setAngles("RShoulderPitch", 1.2, 0.15)
    time.sleep(0.3)
    pepper.setAngles("LShoulderPitch", 0, 0.15)
    pepper.setAngles("RShoulderPitch", 0, 0.15)

def gesture_excited():
    """حركة حماس"""
    for _ in range(2):
        pepper.setAngles("LShoulderPitch", 1.0, 0.1)
        pepper.setAngles("RShoulderPitch", 1.0, 0.1)
        time.sleep(0.15)
        pepper.setAngles("LShoulderPitch", 0.2, 0.1)
        pepper.setAngles("RShoulderPitch", 0.2, 0.1)
        time.sleep(0.15)

def gesture_question():
    """حركة سؤال"""
    pepper.setAngles("LShoulderPitch", 0.5, 0.15)
    time.sleep(0.3)
    pepper.setAngles("LShoulderPitch", 0, 0.15)

def gesture_agree():
    """حركة موافقة (نعم)"""
    pepper.setAngles("HeadYaw", 0.3, 0.1)
    time.sleep(0.2)
    pepper.setAngles("HeadYaw", -0.3, 0.1)
    time.sleep(0.2)
    pepper.setAngles("HeadYaw", 0, 0.1)

def gesture_point():
    """حركة إشارة"""
    pepper.setAngles("RShoulderPitch", 0.8, 0.15)
    pepper.setAngles("RElbowYaw", -0.5, 0.15)
    time.sleep(0.5)
    pepper.setAngles("RShoulderPitch", 0, 0.15)
    pepper.setAngles("RElbowYaw", 0, 0.15)

def gesture_think():
    """حركة تفكير"""
    pepper.setAngles("HeadYaw", 0.2, 0.1)
    pepper.setAngles("HeadPitch", 0.1, 0.1)
    time.sleep(0.5)
    pepper.setAngles("HeadYaw", 0, 0.1)
    pepper.setAngles("HeadPitch", 0, 0.1)

# ========== تحليل الكلام واختيار الحركة ==========
def choose_gesture(text):
    text_lower = text.lower()
    
    if any(word in text_lower for word in ["hello", "hi", "hey", "wave"]):
        gesture_wave()
    elif any(word in text_lower for word in ["good", "great", "awesome", "nice", "love", "happy"]):
        gesture_excited()
    elif "?" in text or any(word in text_lower for word in ["what", "why", "how", "when", "where", "who"]):
        gesture_question()
    elif any(word in text_lower for word in ["yes", "ok", "okay", "sure", "correct", "right"]):
        gesture_agree()
    elif any(word in text_lower for word in ["look", "see", "there", "here", "point"]):
        gesture_point()
    else:
        gesture_think()

# ========== ردود صوتية حسب الكلام ==========
def get_response(text):
    text_lower = text.lower()
    
    if any(word in text_lower for word in ["hello", "hi", "hey"]):
        return "Hello! I am Pepper! Nice to see you! 👋"
    elif "how are you" in text_lower:
        return "I am doing great! I love walking around my room! 😊"
    elif "what is your name" in text_lower or "who are you" in text_lower:
        return "My name is Pepper! I am your robot friend! 🤖"
    elif "what can you do" in text_lower:
        return "I can walk around, wave, dance, and talk to you! I also follow the balloons with my head! 🎈"
    elif "tell me a joke" in text_lower:
        return "Why did the robot go to the doctor? Because it had a hardware problem! 🤖😂"
    elif "thank you" in text_lower:
        return "You are welcome! I am happy to help! 😊"
    elif "goodbye" in text_lower or "bye" in text_lower:
        return "Goodbye! Come back soon! 👋"
    elif "dance" in text_lower:
        return "Let's dance! 💃"
    elif "i love you" in text_lower:
        return "Aww, I love you too! You are my friend! 💙"
    else:
        return f"You said: {text}. That's interesting! Tell me more! 😊"

# ========== حركة يدين طبيعية مستمرة ==========
def natural_arms():
    global arm_angle, arm_dir
    while True:
        if not is_talking:
            arm_angle += 0.03 * arm_dir
            if arm_angle > 0.4:
                arm_angle = 0.4
                arm_dir = -1
            elif arm_angle < 0:
                arm_angle = 0
                arm_dir = 1
            try:
                pepper.setAngles("LShoulderPitch", arm_angle, 0.05)
                pepper.setAngles("RShoulderPitch", arm_angle, 0.05)
            except:
                pass
        time.sleep(0.04)

# ========== حركة رأس طبيعية ==========
def natural_head():
    tt = 0
    while True:
        if not is_talking:
            tt += 0.02
            yaw = math.sin(tt) * 0.3
            pitch = math.sin(tt * 0.7) * 0.1
            try:
                pepper.setAngles("HeadYaw", yaw, 0.05)
                pepper.setAngles("HeadPitch", pitch, 0.05)
            except:
                pass
        time.sleep(0.04)

# ========== حركة مشي مستمرة ==========
def continuous_walking():
    global robot_x, robot_y, t
    while True:
        if not is_talking:
            t += 0.045
            robot_x = 4.5 * math.cos(t * 0.4)
            robot_y = 3.5 * math.sin(t * 0.55)
            try:
                pepper.setTranslation([robot_x, robot_y, 0.8])
            except:
                pass
        time.sleep(0.035)

# ========== تتبع البالونات ==========
def track_balloons():
    global head_yaw
    while True:
        if not is_talking:
            closest = None
            min_dist = 999
            for b in balloon_positions:
                dist = math.sqrt((b[0] - robot_x)**2 + (b[1] - robot_y)**2)
                if dist < min_dist:
                    min_dist = dist
                    closest = b
            if closest:
                dx = closest[0] - robot_x
                dy = closest[1] - robot_y
                target_yaw = math.atan2(dy, dx)
                head_yaw = head_yaw * 0.92 + target_yaw * 0.08
                try:
                    pepper.setAngles("HeadYaw", head_yaw, 0.1)
                except:
                    pass
        time.sleep(0.05)

# ========== تحديث البالونات ==========
def update_balloons():
    while True:
        for i, b in enumerate(balloons):
            new_z = balloon_positions[i][2] + balloon_positions[i][3]
            if new_z > 2:
                new_z = 0.3
                balloon_positions[i][0] = random.uniform(-4, 4)
                balloon_positions[i][1] = random.uniform(-3, 3)
            balloon_positions[i][2] = new_z
            p.resetBasePositionAndOrientation(b, [balloon_positions[i][0], balloon_positions[i][1], new_z], [0,0,0,1])
        p.stepSimulation()
        time.sleep(1/60.)

# ========== بدء التشغيل ==========
threading.Thread(target=natural_arms, daemon=True).start()
threading.Thread(target=natural_head, daemon=True).start()
threading.Thread(target=continuous_walking, daemon=True).start()
threading.Thread(target=track_balloons, daemon=True).start()
threading.Thread(target=update_balloons, daemon=True).start()

print("\n" + "="*60)
print("🎤🔊🤖 PEPPER TALK & MOVE")
print("="*60)
print("✅ Pepper walks CONTINUOUSLY")
print("✅ Pepper moves arms naturally")
print("✅ Pepper looks at balloons")
print("✅ Type ANYTHING - Pepper TALKS BACK with VOICE")
print("✅ Pepper moves hands based on your words")
print("✅ Type 'exit' to quit")
print("="*60 + "\n")

speak("Hello! I am Pepper! I am walking around! Type anything and I will talk to you!")

# ========== المحادثة ==========
while True:
    try:
        user_input = input("\n👶 You: ").strip()
        
        if user_input.lower() == 'exit':
            speak("Goodbye! Come back soon! 👋")
            break
        
        if not user_input:
            continue
        
        # اختيار حركة حسب الكلام
        choose_gesture(user_input)
        
        # الحصول على رد
        response = get_response(user_input)
        
        # النطق بالرد
        speak(response)
        
    except KeyboardInterrupt:
        print("\n")
        speak("Goodbye! 👋")
        break

print("\n✅ Done")
