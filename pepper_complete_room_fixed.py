#!/usr/bin/env python3
"""
Pepper Complete Room - غرفة متكاملة مع بيبر (نسخة محسنة)
- أثاث (طاولات، كراسي، شاشة)
- مجسمات أطفال بأسماء
- بيبر يتحرك في نقاط محددة
- AI Chat متطور
"""

import time
import random
import math
import threading
from qibullet import SimulationManager
import pybullet as p
import pybullet_data
import requests

# ========== إعداد AI Chat متطور ==========
CHAT_API = "https://text.pollinations.ai/v1/chat/completions"

# قاعدة ردود محلية كبديل
local_responses = {
    "hello": "Hello! Nice to see you! I'm Pepper, your robot friend! 🤖",
    "hi": "Hi there! How are you today? 😊",
    "how are you": "I'm doing great! I love walking around my room and watching the balloons! 🎈",
    "what is your name": "My name is Pepper! I'm a friendly robot!",
    "who are you": "I'm Pepper, a robot who lives in this room with balloons and kids!",
    "what can you do": "I can walk around, wave, dance, and talk to you! I also follow the balloons with my head!",
    "tell me a joke": "Why did the robot go to the doctor? Because it had a hardware problem! 🤖😂",
    "i love you": "Aww, I love you too! You're my friend! 💙",
    "thank you": "You're welcome! I'm happy to help! 😊",
    "goodbye": "Goodbye! Come back soon! 👋",
    "dance": "Let's dance! 💃",
    "wave": "Waving hello to you! 👋",
    "what color is the sky": "The sky is usually blue, but it can be orange or pink at sunset! 🌅",
    "what is the weather": "I don't have a window, but I hope it's nice outside! ☀️",
    "do you like me": "Of course I like you! You're my friend! 💙",
}

def get_ai_response(message):
    msg_lower = message.lower().strip()
    
    # التحقق من الردود المحلية أولاً
    for key, response in local_responses.items():
        if key in msg_lower:
            return response
    
    # استخدام API إذا كان السؤال غير موجود في القاعدة
    try:
        data = {
            "model": "openai",
            "messages": [
                {"role": "system", "content": "You are Pepper, a friendly robot in a room with balloons and kids. Respond in short, simple English sentences (1-2 sentences). Be kind, encouraging, and use emojis sometimes."},
                {"role": "user", "content": message}
            ],
            "temperature": 0.7,
            "max_tokens": 80
        }
        response = requests.post(CHAT_API, json=data, timeout=10)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
    except:
        pass
    
    # ردود عامة إذا فشل API
    fallbacks = [
        f"That's interesting! Tell me more about '{message}' 😊",
        f"I like talking with you! What else would you like to know? 🌟",
        f"Great question! I'm still learning, but I'm happy to chat with you! 🤖",
        f"You said: '{message}'. That's cool! 😎"
    ]
    return random.choice(fallbacks)

# ========== بدء qiBullet ==========
print("🤖 Starting Pepper in qiBullet...")

sim_manager = SimulationManager()
client_id = sim_manager.launchSimulation(gui=True)

# تحميل بيبر
pepper = sim_manager.spawnPepper(client_id, translation=[0, 0, 0], quaternion=[0, 0, 0, 1])

# إضافة أرضية كبيرة
p.setAdditionalSearchPath(pybullet_data.getDataPath())
p.loadURDF("plane.urdf")
p.setGravity(0, 0, -9.81)
p.setRealTimeSimulation(1)

print("✅ Pepper loaded!")

# ========== بناء الغرفة المتكاملة ==========
print("🏠 Building room with furniture, screen, and kids...")

# ========== 1. أثاث ==========
# طاولة رئيسية
table_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[1.5, 1, 0.4], rgbaColor=[0.6, 0.4, 0.2, 1])
p.createMultiBody(baseMass=0, baseVisualShapeIndex=table_vis, basePosition=[2, 2, 0.4])

# طاولة صغيرة
small_table = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.8, 0.6, 0.3], rgbaColor=[0.5, 0.3, 0.1, 1])
p.createMultiBody(baseMass=0, baseVisualShapeIndex=small_table, basePosition=[-2, 1.5, 0.3])

# كراسي
chair_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.4, 0.4, 0.3], rgbaColor=[0.4, 0.2, 0.1, 1])
p.createMultiBody(baseMass=0, baseVisualShapeIndex=chair_vis, basePosition=[1.5, 2.5, 0.15])
p.createMultiBody(baseMass=0, baseVisualShapeIndex=chair_vis, basePosition=[2.5, 2.5, 0.15])
p.createMultiBody(baseMass=0, baseVisualShapeIndex=chair_vis, basePosition=[-1.5, 2, 0.15])
p.createMultiBody(baseMass=0, baseVisualShapeIndex=chair_vis, basePosition=[-2.5, 1, 0.15])

# رف كتب
shelf_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[1.2, 0.3, 1], rgbaColor=[0.6, 0.4, 0.2, 1])
p.createMultiBody(baseMass=0, baseVisualShapeIndex=shelf_vis, basePosition=[-3, -2, 0.5])

# سجادة
rug_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[5, 4, 0.02], rgbaColor=[0.3, 0.5, 0.3, 0.7])
p.createMultiBody(baseMass=0, baseVisualShapeIndex=rug_vis, basePosition=[0, 0, 0.01])

# ========== 2. شاشة (TV) ==========
screen_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[1.2, 0.05, 0.8], rgbaColor=[0.1, 0.1, 0.2, 1])
screen_frame = p.createVisualShape(p.GEOM_BOX, halfExtents=[1.3, 0.1, 0.9], rgbaColor=[0.3, 0.3, 0.3, 1])
p.createMultiBody(baseMass=0, baseVisualShapeIndex=screen_frame, basePosition=[-3, 3, 1])
p.createMultiBody(baseMass=0, baseVisualShapeIndex=screen_vis, basePosition=[-3, 3, 1])
screen_display = p.createVisualShape(p.GEOM_BOX, halfExtents=[1.1, 0.03, 0.7], rgbaColor=[0, 0.2, 0.4, 1])
p.createMultiBody(baseMass=0, baseVisualShapeIndex=screen_display, basePosition=[-3, 3.02, 1])

# ========== 3. مجسمات أطفال بأسماء ==========
def create_kid(name, color, pos):
    body = p.createVisualShape(p.GEOM_CYLINDER, radius=0.2, length=0.4, rgbaColor=color)
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=body, basePosition=[pos[0], pos[1], pos[2] + 0.2])
    head = p.createVisualShape(p.GEOM_SPHERE, radius=0.15, rgbaColor=[1, 0.85, 0.7, 1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=head, basePosition=[pos[0], pos[1], pos[2] + 0.55])
    eye = p.createVisualShape(p.GEOM_SPHERE, radius=0.04, rgbaColor=[0, 0, 0, 1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=eye, basePosition=[pos[0] - 0.07, pos[1] + 0.08, pos[2] + 0.62])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=eye, basePosition=[pos[0] + 0.07, pos[1] + 0.08, pos[2] + 0.62])
    p.addUserDebugText(name, [pos[0], pos[1], pos[2] + 0.85], [0, 0, 0], textSize=0.8, lifeTime=0)

kids = [
    ("Yusuf", [1.5, -1.5, 0], [0.4, 0.7, 1, 1]),
    ("Ahmed", [-1, 2, 0], [1, 0.6, 0.4, 1]),
    ("Sara", [3, -1, 0], [1, 0.7, 0.8, 1]),
    ("Layla", [-2.5, -1.5, 0], [1, 0.5, 0.9, 1]),
    ("Omar", [0.5, 2.5, 0], [0.4, 0.8, 0.4, 1]),
]

for name, pos, color in kids:
    create_kid(name, color, pos)
    print(f"   👧 Created: {name}")

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

# ========== نقاط تحرك بيبر ==========
waypoints = [
    [2, 2], [3, 1], [2.5, -1], [1, -2], [-1, -2], [-2.5, -1], [-3, 1], [-2, 2], [0, 2.5], [2, 2]
]

print("📍 Pepper will follow waypoints around the room!")

# ========== كاميرا ==========
p.resetDebugVisualizerCamera(cameraDistance=8, cameraYaw=45, cameraPitch=-35, cameraTargetPosition=[0, 0, 0.8])

# ========== متغيرات ==========
robot_x, robot_y = 0, 0
current_target = 0
head_yaw = 0
arm_angle = 0
arm_dir = 1
is_moving = True

# ========== حركة يدين طبيعية ==========
def natural_arms():
    global arm_angle, arm_dir
    while True:
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

# ========== حركة رأس ==========
def natural_head():
    tt = 0
    while True:
        tt += 0.02
        yaw = math.sin(tt) * 0.3
        pitch = math.sin(tt * 0.7) * 0.1
        try:
            pepper.setAngles("HeadYaw", yaw, 0.05)
            pepper.setAngles("HeadPitch", pitch, 0.05)
        except:
            pass
        time.sleep(0.04)

# ========== حركة بيبر بين النقاط ==========
def move_to_waypoints():
    global robot_x, robot_y, current_target
    while is_moving:
        target = waypoints[current_target]
        dx = target[0] - robot_x
        dy = target[1] - robot_y
        if abs(dx) < 0.1 and abs(dy) < 0.1:
            current_target = (current_target + 1) % len(waypoints)
        else:
            robot_x += dx * 0.05
            robot_y += dy * 0.05
        try:
            pepper.setTranslation([robot_x, robot_y, 0.8])
        except:
            pass
        time.sleep(0.04)

# ========== تتبع البالونات ==========
def track_balloons():
    global head_yaw
    while True:
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
threading.Thread(target=move_to_waypoints, daemon=True).start()
threading.Thread(target=track_balloons, daemon=True).start()
threading.Thread(target=update_balloons, daemon=True).start()

print("\n" + "="*60)
print("🤖 PEPPER COMPLETE ROOM (ENHANCED AI)")
print("="*60)
print("✅ Room with furniture, screen, kids")
print("✅ Pepper follows waypoints")
print("✅ Balloons float around")
print("✅ Smart AI Chat with local responses")
print("✅ Type 'exit' to quit")
print("="*60 + "\n")

print("🤖 Pepper: Hello! I am Pepper! I'm in a room with furniture, a screen, and kids!")
print("💬 Try saying: hello, how are you, tell me a joke, what can you do\n")

# ========== AI Chat ==========
while True:
    try:
        user_input = input("👶 You: ").strip()
        
        if user_input.lower() == 'exit':
            print("🤖 Pepper: Goodbye! Come back soon! 👋")
            break
        
        if not user_input:
            continue
        
        print("🤖 Pepper: ", end="", flush=True)
        response = get_ai_response(user_input)
        print(response)
        
    except KeyboardInterrupt:
        print("\n🤖 Pepper: Goodbye! 👋")
        break

print("\n✅ Done")
