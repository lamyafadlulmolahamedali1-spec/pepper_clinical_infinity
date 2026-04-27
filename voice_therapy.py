#!/usr/bin/env python3
"""
Pepper Voice + Body Movement Therapy
- Pepper speaks with real voice
- Listens to your voice instead of typing
- Turns body toward each child
- Smooth hand movements while talking
- Eye contact (head tracks child face)
"""

import sys
import threading
import time
import math
import random
import pybullet as p
import pyttsx3
import queue

sys.path.insert(0, '/home/lamya/pepper_duo/src')
from pepper_balloon_chaser_backup_dance import PepperRobot
from therapy_integration import TherapyThread, KIDS_DATA

# ========== Voice Engine ==========
class VoiceEngine:
    def __init__(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 150)    # سرعة الكلام
        self.engine.setProperty('volume', 1.0)
        # صوت أنثى إن وجد
        voices = self.engine.getProperty('voices')
        for v in voices:
            if 'female' in v.name.lower() or 'zira' in v.name.lower():
                self.engine.setProperty('voice', v.id)
                break
        self.speaking = False
        self.queue = queue.Queue()
        threading.Thread(target=self._speak_loop, daemon=True).start()

    def speak(self, text):
        """إضافة نص لقائمة الكلام"""
        print(f"🔊 Pepper says: {text}")
        self.queue.put(text)

    def _speak_loop(self):
        while True:
            text = self.queue.get()
            self.speaking = True
            try:
                self.engine.say(text)
                self.engine.runAndWait()
            except:
                pass
            self.speaking = False

    def wait_done(self):
        while self.speaking or not self.queue.empty():
            time.sleep(0.1)


# ========== Speech Recognition ==========
class SpeechListener:
    def __init__(self):
        self.available = False
        try:
            import speech_recognition as sr
            self.r = sr.Recognizer()
            self.r.energy_threshold = 300
            self.r.dynamic_energy_threshold = True
            self.available = True
            print("✅ Microphone ready!")
        except:
            print("⚠️  No microphone - using text input")

    def listen(self, prompt=""):
        if prompt:
            print(f"\n🎤 {prompt}")
        if not self.available:
            return input("👶 You (type): ").strip()
        try:
            import speech_recognition as sr
            with sr.Microphone() as source:
                print("🎤 Listening... (speak now)")
                self.r.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.r.listen(source, timeout=8, phrase_time_limit=10)
            text = self.r.recognize_google(audio)
            print(f"👶 You said: {text}")
            return text
        except Exception as e:
            print(f"⚠️  Could not hear: {e}")
            return input("👶 You (type instead): ").strip()


# ========== Body Movement Controller ==========
class BodyMovement:
    """تحكم في حركة جسم Pepper"""
    def __init__(self, pepper_obj, robot_ref):
        self.pepper = pepper_obj
        self.robot = robot_ref
        self.current_yaw = 0
        self.target_yaw = 0
        self.talking = False
        self.arm_phase = 0

        # Thread لحركة الجسم المستمرة
        threading.Thread(target=self._body_loop, daemon=True).start()

    def face_kid(self, kid_pos, robot_pos):
        """دوران Pepper ناحية الطفل"""
        dx = kid_pos[0] - robot_pos[0]
        dy = kid_pos[1] - robot_pos[1]
        self.target_yaw = math.atan2(dy, dx)

    def _body_loop(self):
        """حلقة مستمرة لتحريك الجسم والأيدي"""
        while True:
            # دوران الرأس ناحية الطفل (eye contact)
            diff = self.target_yaw - self.current_yaw
            # normalize
            while diff > math.pi: diff -= 2*math.pi
            while diff < -math.pi: diff += 2*math.pi
            self.current_yaw += diff * 0.08  # سلاسة

            try:
                # الرأس يتبع الطفل
                self.pepper.setAngles("HeadYaw", self.current_yaw * 0.6, 0.08)
                self.pepper.setAngles("HeadPitch", -0.15, 0.05)  # نظرة للأمام قليلاً للأسفل

                # حركة الأيدي أثناء الكلام
                if self.talking:
                    self.arm_phase += 0.08
                    # حركة سلسة بـ sine wave
                    left  = 0.5 + 0.3 * math.sin(self.arm_phase)
                    right = 0.5 + 0.3 * math.sin(self.arm_phase + math.pi * 0.6)
                    self.pepper.setAngles("LShoulderPitch", left,  0.06)
                    self.pepper.setAngles("RShoulderPitch", right, 0.06)
                    # حركة المرفق
                    elbow = 0.3 + 0.2 * math.sin(self.arm_phase * 0.7)
                    self.pepper.setAngles("LElbowRoll", -elbow, 0.06)
                    self.pepper.setAngles("RElbowRoll",  elbow, 0.06)
                else:
                    # يدين تنزل بشكل سلس
                    self.pepper.setAngles("LShoulderPitch", 1.0, 0.04)
                    self.pepper.setAngles("RShoulderPitch", 1.0, 0.04)
                    self.pepper.setAngles("LElbowRoll", -0.3, 0.04)
                    self.pepper.setAngles("RElbowRoll",  0.3, 0.04)
            except:
                pass
            time.sleep(0.04)

    def move_to_kid(self, robot, kid_pos):
        """تحريك Pepper للوقوف أمام الطفل مباشرة"""
        target_x = kid_pos[0]
        target_y = kid_pos[1]

        # الوقوف على مسافة 0.7 متر أمام الطفل
        dx = target_x - robot.x
        dy = target_y - robot.y
        dist = math.sqrt(dx**2 + dy**2)

        if dist < 0.01:
            return

        # الموقع المستهدف: أمام الطفل بـ 0.7م
        stop_dist = 0.7
        ratio = max(0, dist - stop_dist) / dist
        goal_x = robot.x + dx * ratio
        goal_y = robot.y + dy * ratio

        # التحرك بخطوات سلسة
        steps = max(1, int(dist / 0.05))
        for i in range(steps):
            if dist <= stop_dist + 0.05:
                break
            t = (i + 1) / steps
            new_x = robot.x + (goal_x - robot.x) * t
            new_y = robot.y + (goal_y - robot.y) * t
            new_x = max(-3.2, min(3.2, new_x))
            new_y = max(-2.5, min(2.5, new_y))
            robot.x = new_x
            robot.y = new_y
            try:
                self.pepper.setPosition([new_x, new_y, 0.8])
            except:
                pass
            # تدوير الرأس ناحية الطفل أثناء المشي
            self.face_kid([target_x, target_y], [new_x, new_y])
            time.sleep(0.04)

        # بعد الوصول - اتجه للطفل مباشرة
        self.face_kid([target_x, target_y], [robot.x, robot.y])
        time.sleep(0.5)


# ========== Main Therapy Robot with Voice ==========
class VoicePepperRobot(PepperRobot):

    def __init__(self):
        super().__init__()

        # مكونات الصوت والحركة
        self.voice = VoiceEngine()
        self.listener = SpeechListener()
        self.body = BodyMovement(self.pepper, self)

        # بيانات الأطفال
        self.kids_positions = {k["name"]: k["pos"] for k in KIDS_DATA}
        self.kids_states = {k["name"]: {
            "severity": k["severity"],
            "response_chance": k["response_chance"],
            "interactions": 0,
            "successes": 0,
            "score": 0
        } for k in KIDS_DATA}

        self.current_kid = None
        self.therapy_running = False
        self.session_scores = {}

        print("\n✅ Voice Therapy Robot Ready!")
        print("🎤 You can SPEAK or TYPE commands")
        print("Commands: 'therapy', 'visit [name]', 'report', 'stop'\n")

    def speak(self, text):
        """Pepper تتكلم بصوت + تحرك يدين"""
        self.body.talking = True
        self.show_text(text)
        self.voice.speak(text)
        self.voice.wait_done()
        self.body.talking = False

    def visit_kid(self, kid_name):
        """Pepper تزور طفل معين"""
        if kid_name not in self.kids_positions:
            self.speak(f"I don't know {kid_name}!")
            return

        kid_pos = self.kids_positions[kid_name]
        kid_data = self.kids_states[kid_name]
        self.current_kid = kid_name

        print(f"\n[THERAPY] 🚶 Moving to {kid_name}...")
        self.auto_walk = False

        # تحرك للطفل
        self.body.move_to_kid(self, kid_pos)

        # نظر للطفل
        self.body.face_kid(kid_pos, [self.x, self.y])

        # ابدأ التفاعل
        self.speak(f"Hello {kid_name}! How are you today?")
        time.sleep(0.5)

        # اختيار فعل علاجي
        actions = [
            (f"Look at me {kid_name}! Can you clap your hands?", "dtt"),
            (f"{kid_name}, touch your nose! Like this!", "dtt"),
            (f"Look {kid_name}! Look at the red ball!", "joint_attention"),
            (f"What feeling is this {kid_name}? Happy! Can you show happy?", "emotion"),
            (f"Breathe with me {kid_name}! In... and out...", "sensory"),
        ]
        text, atype = random.choice(actions)
        self.speak(text)

        # استجابة الطفل
        responded = random.random() < kid_data["response_chance"]
        kid_data["interactions"] += 1

        time.sleep(1.0)
        if responded:
            kid_data["successes"] += 1
            kid_data["score"] += 10
            self.speak(f"Amazing {kid_name}! You are a superstar!")
        else:
            self.speak(f"That is okay {kid_name}! Let us try again!")

        rate = round(kid_data["successes"] / kid_data["interactions"] * 100, 1)
        print(f"[{kid_name}] Success rate: {rate}% | Score: {kid_data['score']}")

        self.auto_walk = True

    def start_therapy_loop(self):
        """الثيرابي التلقائي - يزور كل الأطفال بالترتيب"""
        self.therapy_running = True
        kids = list(self.kids_positions.keys())
        idx = 0
        self.speak("Starting therapy session! Let us visit all children!")

        while self.therapy_running:
            kid = kids[idx % len(kids)]
            self.visit_kid(kid)
            idx += 1
            # انتظر قبل الطفل التالي
            for _ in range(80):  # 8 ثواني
                if not self.therapy_running:
                    break
                time.sleep(0.1)

        self.speak("Therapy session complete! Great work everyone!")
        self.print_report()

    def print_report(self):
        print("\n" + "="*55)
        print("📊 SESSION REPORT")
        print("="*55)
        for name, data in self.kids_states.items():
            rate = 0 if data["interactions"] == 0 else round(data["successes"]/data["interactions"]*100, 1)
            bar = "█" * int(rate/10) + "░" * (10 - int(rate/10))
            print(f"👦 {name:8} ({data['severity']:8}) [{bar}] {rate}% | Score: {data['score']}")
        print("="*55)

    def process_command(self, cmd):
        c = cmd.lower().strip()

        if c == "therapy":
            threading.Thread(target=self.start_therapy_loop, daemon=True).start()
            return None  # Pepper ستتكلم من الداخل

        elif c.startswith("visit "):
            name = cmd[6:].strip().title()
            threading.Thread(target=self.visit_kid, args=(name,), daemon=True).start()
            return None

        elif c == "report":
            self.print_report()
            return None

        elif c in ["stop therapy", "stop session"]:
            self.therapy_running = False
            self.speak("Stopping therapy. Goodbye!")
            return None

        elif c in ["dance", "رقص"]:
            self.speak("Let us dance together!")
            self.dance()
            return None

        elif c in ["wave", "hello", "hi"]:
            self.speak("Hello there! Nice to meet you!")
            self.wave()
            return None

        elif c in ["stop", "توقف"]:
            self.auto_walk = False
            self.speak("Stopping now!")
            return None

        elif c in ["go", "walk", "move"]:
            self.auto_walk = True
            self.speak("Walking again!")
            return None

        else:
            # AI chat بالصوت
            self.speak("Let me think...")
            response = self.ai.chat(cmd)
            self.speak(response)
            return None

    def run(self):
        """تشغيل مع الصوت - تلقائي من البداية"""
        self.voice.speak("Hello! I am Pepper! I am ready for therapy!")

        # تشغيل الثيرابي تلقائياً بعد 4 ثواني
        def auto_start():
            time.sleep(4)
            self.start_therapy_loop()
        threading.Thread(target=auto_start, daemon=True).start()

        print("\n" + "="*55)
        print("🎤 VOICE MODE ACTIVE")
        print("="*55)
        print("Speak or type: 'therapy', 'visit Ahmed', 'report'")
        print("="*55 + "\n")

        while True:
            try:
                # استمع للصوت أو الكتابة
                user = self.listener.listen("Waiting for your command...")
                if not user:
                    continue
                if user.lower() in ['exit', 'quit', 'bye']:
                    self.therapy_running = False
                    self.speak("Goodbye! See you next time!")
                    break
                self.process_command(user)
            except KeyboardInterrupt:
                self.therapy_running = False
                self.speak("Goodbye!")
                self.print_report()
                break

if __name__ == "__main__":
    robot = VoicePepperRobot()
    robot.run()
