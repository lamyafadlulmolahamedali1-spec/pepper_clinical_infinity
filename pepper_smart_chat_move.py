#!/usr/bin/env python3
"""
Pepper Smart Chat + Movement - محادثة ذكية + حركة مستمرة
- يفهم الأوامر (hello, a, b, grip, reach)
- يرد على الأسئلة العادية بذكاء
- يتحرك في الغرفة
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
    print(f"🔊 Pepper: {text}")
    engine.say(text)
    engine.runAndWait()

# ========== بدء المحاكاة ==========
print("🤖 Starting Pepper Smart Chat...")

sim_manager = SimulationManager()
client = sim_manager.launchSimulation(gui=True)
p.setAdditionalSearchPath(pybullet_data.getDataPath())
p.setRealTimeSimulation(1)
p.setGravity(0, 0, -9.81)
p.loadURDF("plane.urdf")

pepper = sim_manager.spawnPepper(client)
pepper.goToPosture("Stand", 0.5)
print("✅ Pepper loaded!")

# ========== بالونات ==========
colors = [[1,0,0,1], [0,1,0,1], [0,0,1,1], [1,1,0,1], [1,0.5,0,1]]
balloons = []
for i in range(10):
    x = random.uniform(-3, 3)
    y = random.uniform(-2.5, 2.5)
    vis = p.createVisualShape(p.GEOM_SPHERE, radius=0.12, rgbaColor=colors[i%5])
    ball = p.createMultiBody(baseMass=0, baseVisualShapeIndex=vis, basePosition=[x, y, random.uniform(0.5,1.5)])
    balloons.append(ball)

p.resetDebugVisualizerCamera(cameraDistance=6, cameraYaw=45, cameraPitch=-30, cameraTargetPosition=[0,0,0.8])

# ========== لغة الإشارة (ASL) ==========
def asl_letter_a():
    pepper.setAngles("LShoulderPitch", 0.3, 0.15)
    pepper.setAngles("LElbowYaw", 0.5, 0.15)
    time.sleep(0.4)
    pepper.setAngles("LShoulderPitch", 0, 0.15)
    pepper.setAngles("LElbowYaw", 0, 0.15)

def asl_letter_b():
    pepper.setAngles("RShoulderPitch", 0.3, 0.15)
    pepper.setAngles("RElbowYaw", -0.5, 0.15)
    time.sleep(0.4)
    pepper.setAngles("RShoulderPitch", 0, 0.15)
    pepper.setAngles("RElbowYaw", 0, 0.15)

def asl_hello():
    for _ in range(2):
        pepper.setAngles("LShoulderPitch", 0.8, 0.1)
        pepper.setAngles("RShoulderPitch", 0.8, 0.1)
        time.sleep(0.2)
        pepper.setAngles("LShoulderPitch", 0, 0.1)
        pepper.setAngles("RShoulderPitch", 0, 0.1)
        time.sleep(0.2)

def advanced_grip():
    pepper.setAngles("LShoulderPitch", 0.5, 0.1)
    pepper.setAngles("LElbowYaw", 0.6, 0.1)
    time.sleep(0.4)
    pepper.setAngles("LShoulderPitch", 0, 0.1)
    pepper.setAngles("LElbowYaw", 0, 0.1)

def advanced_reach():
    pepper.setAngles("RShoulderPitch", 0.7, 0.15)
    pepper.setAngles("RElbowYaw", -0.7, 0.15)
    time.sleep(0.4)
    pepper.setAngles("RShoulderPitch", 0, 0.15)
    pepper.setAngles("RElbowYaw", 0, 0.15)

# ========== قاعدة معرفة للأسئلة ==========
knowledge_base = {
    "what is your name": "My name is Pepper! I am your robot friend!",
    "who are you": "I am Pepper, a friendly robot. I can walk, talk, and do sign language!",
    "how are you": "I am great! Thank you for asking! I love walking around!",
    "what can you do": "I can walk, wave, dance, do sign language, and talk to you!",
    "what color is the sky": "The sky is usually blue during the day!",
    "what color is grass": "Grass is green!",
    "what is the weather": "I don't know the weather outside, but it's nice in my simulation!",
    "tell me a joke": "Why did the robot go to the doctor? Because it had a hardware problem! 🤖",
    "do you like me": "Of course I like you! You are my friend!",
    "thank you": "You are welcome! I'm happy to help!",
}

# ========== حركة يدين طبيعية ==========
arm_angle = 0
arm_dir = 1

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

# ========== حركة مشي ==========
t = 0
def walk():
    global t
    while True:
        t += 0.035
        x = 2.8 * math.cos(t * 0.45)
        y = 2.5 * math.sin(t * 0.6)
        try:
            pepper.setTranslation([x, y, 0.8])
        except:
            pass
        time.sleep(0.04)

# ========== تحديث البالونات ==========
def update_balloons():
    while True:
        for b in balloons:
            pos, _ = p.getBasePositionAndOrientation(b)
            new_z = pos[2] + 0.008
            if new_z > 1.6:
                new_z = 0.3
            p.resetBasePositionAndOrientation(b, [pos[0], pos[1], new_z], [0,0,0,1])
        p.stepSimulation()
        time.sleep(1/60.)

# ========== معالجة الأوامر والأسئلة ==========
def process_input(user_input):
    user_lower = user_input.lower().strip()
    
    # أوامر محددة (يتم تنفيذها فقط إذا كانت الكلمة بالضبط)
    exact_commands = {
        "a": ("Letter A in sign language", asl_letter_a),
        "b": ("Letter B in sign language", asl_letter_b),
        "hello": ("Hello! Nice to see you!", asl_hello),
        "hi": ("Hello! Nice to see you!", asl_hello),
        "wave": ("Waving hello!", asl_hello),
        "grip": ("Making a grip motion", advanced_grip),
        "reach": ("Reaching forward", advanced_reach),
    }
    
    # التحقق من الأوامر الدقيقة (الكلمة كاملة)
    if user_lower in exact_commands:
        response, action = exact_commands[user_lower]
        action()
        return response
    
    # التحقق من الأسئلة في قاعدة المعرفة
    for question, answer in knowledge_base.items():
        if question in user_lower:
            return answer
    
    # إذا كان السؤال عن لون أو شيء عام
    if "color" in user_lower:
        return "That's an interesting question about colors! The sky is blue, grass is green!"
    
    if "what" in user_lower or "why" in user_lower or "how" in user_lower:
        return f"That's a good question! Tell me more about {user_input[:30]}..."
    
    # ردود عشوائية للمحادثة العامة
    responses = [
        f"That's interesting! Tell me more.",
        f"I like talking with you! What else would you like to know?",
        f"Great question! I'm learning new things every day!",
        f"You said: {user_input}. That's cool!",
    ]
    return random.choice(responses)

# ========== بدء التشغيل ==========
threading.Thread(target=natural_arms, daemon=True).start()
threading.Thread(target=walk, daemon=True).start()
threading.Thread(target=update_balloons, daemon=True).start()

time.sleep(2)
speak("Hello! I am Pepper! I can walk, talk, and do sign language! Type hello, a, b, grip, reach, or ask me questions!")

print("\n" + "="*60)
print("🤖 PEPPER SMART CHAT + MOVEMENT")
print("="*60)
print("✅ Pepper walks continuously")
print("✅ Sign Language: hello, a, b")
print("✅ Advanced moves: grip, reach")
print("✅ Smart answers to questions")
print("="*60)
print("\n📝 EXAMPLES:")
print("   hello, a, b, grip, reach - Commands")
print("   what is your name? - Question")
print("   what color is the sky? - Question")
print("   tell me a joke - Joke")
print("   exit - Quit")
print("="*60 + "\n")

# ========== المحادثة ==========
while True:
    try:
        user_input = input("👶 You: ").strip()
        
        if user_input.lower() == 'exit':
            speak("Goodbye! See you later!")
            break
        
        if not user_input:
            continue
        
        response = process_input(user_input)
        speak(response)
        
    except KeyboardInterrupt:
        print("\n")
        speak("Goodbye!")
        break

print("\n✅ Done")
