"""
Therapy Integration - يضاف لـ PepperRobot
Pepper تتحرك للأطفال وتتفاعل معهم فعلياً
"""

import time
import math
import random
import threading
import pybullet as p

# ========== بيانات الأطفال مع سلوك التوحد ==========
KIDS_DATA = [
    {
        "name": "Ahmed",
        "pos": [1.5, -1.2, 0],
        "severity": "mild",
        "response_chance": 0.75,
        "attention_span": 12,
        "repetitive_chance": 0.2,
        "color": [1, 0.6, 0.4, 1]
    },
    {
        "name": "Sara",
        "pos": [-1.2, 1.3, 0],
        "severity": "moderate",
        "response_chance": 0.45,
        "attention_span": 7,
        "repetitive_chance": 0.45,
        "color": [1, 0.7, 0.8, 1]
    },
    {
        "name": "Yusuf",
        "pos": [0.5, -2, 0],
        "severity": "severe",
        "response_chance": 0.15,
        "attention_span": 3,
        "repetitive_chance": 0.75,
        "color": [0.4, 0.7, 1, 1]
    },
    {
        "name": "Layla",
        "pos": [2.8, -0.2, 0],
        "severity": "moderate",
        "response_chance": 0.50,
        "attention_span": 8,
        "repetitive_chance": 0.40,
        "color": [1, 0.5, 0.9, 1]
    },
    {
        "name": "Omar",
        "pos": [-2.2, -1, 0],
        "severity": "mild",
        "response_chance": 0.70,
        "attention_span": 10,
        "repetitive_chance": 0.25,
        "color": [0.4, 0.8, 0.4, 1]
    },
]

THERAPY_ACTIONS = [
    {"type": "greet",              "text": "Hello {name}! 👋 How are you today?",          "score": 5},
    {"type": "dtt",                "text": "Look at me {name}! Can you clap? 👏",           "score": 10},
    {"type": "dtt",                "text": "{name}, touch your nose! 👃",                   "score": 10},
    {"type": "dtt",                "text": "{name}, stand up please! 🧍",                   "score": 10},
    {"type": "joint_attention",    "text": "Look {name}! Look at the red ball! 🔴",         "score": 15},
    {"type": "joint_attention",    "text": "{name}, look here! See the yellow block? 🟡",   "score": 15},
    {"type": "emotion_recognition","text": "{name}, what feeling is this? 😊 Happy!",       "score": 20},
    {"type": "emotion_recognition","text": "Show me sad {name}! 😢 Like this!",             "score": 20},
    {"type": "sensory_break",      "text": "Breathe with me {name}! 🌬️ In... out...",      "score": 5},
    {"type": "praise",             "text": "Amazing {name}! You are a star! ⭐",            "score": 0},
    {"type": "teacch_schedule",    "text": "{name}, time for play! 🎮 Come with me!",       "score": 8},
]

BEHAVIORS = {
    "mild":     ["wandering", "smiling", "pointing", "brief_eye_contact"],
    "moderate": ["hand_flapping", "rocking", "ignoring", "fixating"],
    "severe":   ["spinning", "covering_ears", "running_away", "self_stimming"],
}

MELTDOWN_SIGNS = {
    "mild":     0.05,
    "moderate": 0.15,
    "severe":   0.35,
}

class KidState:
    """حالة كل طفل في الـ simulation"""
    def __init__(self, data):
        self.name = data["name"]
        self.pos = list(data["pos"])
        self.severity = data["severity"]
        self.response_chance = data["response_chance"]
        self.attention_span = data["attention_span"]
        self.repetitive_chance = data["repetitive_chance"]

        # حالة السلوك
        self.current_behavior = "wandering"
        self.is_melting_down = False
        self.meltdown_timer = 0
        self.last_behavior_change = time.time()
        self.current_emotion = "calm"

        # نتائج الجلسة
        self.total_interactions = 0
        self.successful_responses = 0
        self.session_score = 0

        # حركة عشوائية
        self.wander_target = list(data["pos"])
        self.wander_offset = [0, 0]

        # body parts IDs في PyBullet
        self.torso_id = None
        self.head_id = None
        self.label_id = None

    def update_behavior(self):
        """تحديث سلوك الطفل بشكل عشوائي"""
        now = time.time()
        if now - self.last_behavior_change > self.attention_span:
            self.last_behavior_change = now

            # احتمال meltdown
            if random.random() < MELTDOWN_SIGNS[self.severity] and not self.is_melting_down:
                self.is_melting_down = True
                self.meltdown_timer = time.time()
                self.current_behavior = random.choice(BEHAVIORS[self.severity])
                self.current_emotion = "overwhelmed"
                print(f"[{self.name}] ⚠️  MELTDOWN: {self.current_behavior}")
                return

            # انتهاء الـ meltdown بعد 10 ثواني
            if self.is_melting_down and now - self.meltdown_timer > 10:
                self.is_melting_down = False
                self.current_emotion = "calm"
                print(f"[{self.name}] ✅ Calmed down")

            # سلوك عادي
            if random.random() < self.repetitive_chance:
                self.current_behavior = random.choice(BEHAVIORS[self.severity])
            else:
                self.current_behavior = "wandering"

            emotions = ["calm", "happy", "anxious", "sad", "excited"]
            self.current_emotion = random.choice(emotions)

    def wander(self):
        """حركة عشوائية بسيطة حول الموقع الأصلي"""
        if random.random() < 0.02:
            self.wander_offset = [
                random.uniform(-0.3, 0.3),
                random.uniform(-0.3, 0.3)
            ]
        # تحريك الجسم في PyBullet
        new_pos = [
            self.pos[0] + self.wander_offset[0],
            self.pos[1] + self.wander_offset[1],
            self.pos[2]
        ]
        if self.torso_id is not None:
            try:
                p.resetBasePositionAndOrientation(
                    self.torso_id,
                    [new_pos[0], new_pos[1], new_pos[2] + 0.2],
                    [0, 0, 0, 1]
                )
                p.resetBasePositionAndOrientation(
                    self.head_id,
                    [new_pos[0], new_pos[1], new_pos[2] + 0.55],
                    [0, 0, 0, 1]
                )
            except:
                pass

    def respond(self, action_type):
        """الطفل يستجيب لفعل Pepper"""
        self.total_interactions += 1

        # meltdown = لا استجابة
        if self.is_melting_down:
            print(f"[{self.name}] ⚠️  In meltdown - no response")
            return False

        responded = random.random() < self.response_chance
        if responded:
            self.successful_responses += 1
            print(f"[{self.name}] ✅ Responded to {action_type}!")
        else:
            print(f"[{self.name}] ❌ No response to {action_type}")
        return responded

    def get_success_rate(self):
        if self.total_interactions == 0:
            return 0
        return round(self.successful_responses / self.total_interactions * 100, 1)


class TherapyThread:
    """
    Thread منفصل يشغل الثيرابي داخل PepperRobot
    Pepper تتحرك للأطفال وتتفاعل معهم
    """
    def __init__(self, pepper_robot):
        self.robot = pepper_robot          # PepperRobot instance
        self.pepper = pepper_robot.pepper  # qibullet pepper
        self.kids = [KidState(d) for d in KIDS_DATA]
        self.running = False
        self.current_kid_idx = 0
        self.session_log = []
        self.therapy_active = False

        # ربط body IDs بالأطفال الموجودين في الـ scene
        self._link_kid_bodies()

    def _link_kid_bodies(self):
        """ابحث عن الأجسام الموجودة في PyBullet وربطها بالأطفال"""
        # ما عندنا IDs للأطفال الأصليين لأنهم static visual only
        # نضيف أجسام جديدة قابلة للتحريك فوق القديمة
        for kid in self.kids:
            # Torso متحرك
            torso_vis = p.createVisualShape(
                p.GEOM_BOX,
                halfExtents=[0.19, 0.14, 0.38],
                rgbaColor=[k["color"] for k in KIDS_DATA if k["name"] == kid.name][0]
            )
            kid.torso_id = p.createMultiBody(
                baseMass=0,
                baseVisualShapeIndex=torso_vis,
                basePosition=[kid.pos[0], kid.pos[1], kid.pos[2] + 0.2]
            )
            # Head متحرك
            head_vis = p.createVisualShape(
                p.GEOM_SPHERE, radius=0.14,
                rgbaColor=[1, 0.85, 0.7, 1]
            )
            kid.head_id = p.createMultiBody(
                baseMass=0,
                baseVisualShapeIndex=head_vis,
                basePosition=[kid.pos[0], kid.pos[1], kid.pos[2] + 0.55]
            )
            print(f"[THERAPY] Linked movable body for {kid.name} ({kid.severity})")

    def _move_pepper_to_kid(self, kid):
        """Pepper تتحرك نحو الطفل"""
        target_x = kid.pos[0] + kid.wander_offset[0]
        target_y = kid.pos[1] + kid.wander_offset[1]

        # حساب الاتجاه
        dx = target_x - self.robot.x
        dy = target_y - self.robot.y
        dist = math.sqrt(dx**2 + dy**2)

        steps = int(dist / 0.06) + 1
        for i in range(steps):
            if not self.running:
                break
            # توقف قبل الطفل بمسافة 0.8 متر
            if dist < 0.8:
                break

            progress = (i + 1) / steps
            new_x = self.robot.x + dx * (0.06 / max(dist, 0.01))
            new_y = self.robot.y + dy * (0.06 / max(dist, 0.01))

            # تحديث موقع Pepper
            self.robot.x = max(-3.2, min(3.2, new_x))
            self.robot.y = max(-2.5, min(2.5, new_y))

            # تحديث الرأس لينظر للطفل
            head_yaw = math.atan2(dy, dx)
            try:
                self.pepper.setAngles("HeadYaw", head_yaw * 0.5, 0.15)
                self.pepper.setAngles("HeadPitch", -0.1, 0.1)
                self.pepper.setPosition([self.robot.x, self.robot.y, 0.8])
            except:
                pass

            dist = math.sqrt(
                (target_x - self.robot.x)**2 + (target_y - self.robot.y)**2
            )
            time.sleep(0.05)

    def _do_therapy_action(self, kid):
        """تنفيذ فعل علاجي مع الطفل"""

        # اختيار الفعل حسب حالة الطفل
        if kid.is_melting_down:
            action = {"type": "sensory_break",
                      "text": "Breathe {name}! 🌬️ It's okay... calm down...",
                      "score": 0}
        else:
            action = random.choice(THERAPY_ACTIONS)

        text = action["text"].replace("{name}", kid.name)

        # Pepper تتكلم + تتحرك
        self.robot.show_text(text)
        self.robot.is_talking = True

        # حركة الأيدي حسب نوع الفعل
        self._action_gesture(action["type"])

        time.sleep(1.5)

        # الطفل يستجيب
        responded = kid.respond(action["type"])

        if responded:
            praise = f"Amazing {kid.name}! ⭐ Great job!"
            self.robot.show_text(praise)
            kid.session_score += action["score"]
            # Pepper ترقص بشكل خفيف
            self._celebrate()
        else:
            retry = f"Try again {kid.name}! You can do it! 💪"
            self.robot.show_text(retry)

        self.robot.is_talking = False

        # تسجيل في الـ log
        self.session_log.append({
            "kid": kid.name,
            "severity": kid.severity,
            "action": action["type"],
            "text": text,
            "responded": responded,
            "score": kid.session_score,
            "emotion": kid.current_emotion,
            "behavior": kid.current_behavior
        })

    def _action_gesture(self, action_type):
        """حركة أيدي Pepper حسب نوع الفعل"""
        try:
            if action_type == "greet":
                # موجة ترحيب
                self.pepper.setAngles("RShoulderPitch", 0.3, 0.2)
                time.sleep(0.3)
                self.pepper.setAngles("RShoulderPitch", 1.0, 0.2)
                time.sleep(0.3)
                self.pepper.setAngles("RShoulderPitch", 0.3, 0.2)

            elif action_type == "joint_attention":
                # إشارة بالذراع للشيء
                self.pepper.setAngles("LShoulderPitch", 0.2, 0.15)
                self.pepper.setAngles("LElbowYaw", -1.2, 0.15)
                time.sleep(0.8)
                self.pepper.setAngles("LShoulderPitch", 1.0, 0.15)

            elif action_type == "emotion_recognition":
                # حركة الرأس + يدين
                self.pepper.setAngles("HeadPitch", 0.2, 0.15)
                self.pepper.setAngles("LShoulderPitch", 0.5, 0.15)
                self.pepper.setAngles("RShoulderPitch", 0.5, 0.15)
                time.sleep(0.6)
                self.pepper.setAngles("HeadPitch", 0, 0.15)

            elif action_type == "dtt":
                # رفع يد واحدة للتوضيح
                self.pepper.setAngles("RShoulderPitch", 0.4, 0.2)
                time.sleep(0.4)
                self.pepper.setAngles("RShoulderPitch", 0.9, 0.2)
                time.sleep(0.4)
                self.pepper.setAngles("RShoulderPitch", 0.4, 0.2)

            elif action_type == "sensory_break":
                # حركة بطيئة هادئة
                self.pepper.setAngles("LShoulderPitch", 0.3, 0.05)
                self.pepper.setAngles("RShoulderPitch", 0.3, 0.05)
                time.sleep(1.0)
                self.pepper.setAngles("LShoulderPitch", 0.8, 0.05)
                self.pepper.setAngles("RShoulderPitch", 0.8, 0.05)
                time.sleep(1.0)
                self.pepper.setAngles("LShoulderPitch", 0.3, 0.05)
                self.pepper.setAngles("RShoulderPitch", 0.3, 0.05)
        except:
            pass

    def _celebrate(self):
        """Pepper تحتفل عند استجابة الطفل"""
        try:
            for _ in range(2):
                self.pepper.setAngles("LShoulderPitch", 0.2, 0.2)
                self.pepper.setAngles("RShoulderPitch", 0.2, 0.2)
                time.sleep(0.2)
                self.pepper.setAngles("LShoulderPitch", 0.8, 0.2)
                self.pepper.setAngles("RShoulderPitch", 0.8, 0.2)
                time.sleep(0.2)
        except:
            pass

    def _update_all_kids(self):
        """تحديث سلوك وحركة كل الأطفال"""
        for kid in self.kids:
            kid.update_behavior()
            kid.wander()

    def run_therapy_loop(self):
        """الحلقة الرئيسية للثيرابي"""
        self.running = True
        self.therapy_active = True
        print("\n" + "="*60)
        print("🏥 THERAPY SESSION STARTED")
        print("="*60)
        print("Pepper will now visit each child and run therapy!")
        print("="*60 + "\n")

        kid_visit_timer = 0
        kid_update_timer = 0

        while self.running:
            now = time.time()

            # تحديث سلوك الأطفال كل 0.5 ثانية
            if now - kid_update_timer > 0.5:
                self._update_all_kids()
                kid_update_timer = now

            # زيارة طفل جديد كل 12 ثانية
            if now - kid_visit_timer > 12:
                kid_visit_timer = now

                # اختيار الطفل التالي
                kid = self.kids[self.current_kid_idx % len(self.kids)]
                self.current_kid_idx += 1

                print(f"\n[THERAPY] 🚶 Pepper moving to {kid.name} ({kid.severity})")
                print(f"[{kid.name}] Behavior: {kid.current_behavior} | Emotion: {kid.current_emotion}")

                # إيقاف المشي التلقائي مؤقتاً
                self.robot.auto_walk = False

                # Pepper تتحرك للطفل
                self._move_pepper_to_kid(kid)

                # تنفيذ الفعل العلاجي
                self._do_therapy_action(kid)

                # طباعة التقرير الجزئي
                self._print_mini_report(kid)

                # إعادة تشغيل المشي التلقائي
                self.robot.auto_walk = True

            time.sleep(0.1)

    def _print_mini_report(self, kid):
        """طباعة تقرير سريع للطفل"""
        rate = kid.get_success_rate()
        print(f"\n[REPORT] {kid.name} | Severity: {kid.severity.upper()}")
        print(f"  Interactions: {kid.total_interactions} | Success: {rate}% | Score: {kid.session_score}")

    def print_final_report(self):
        """تقرير نهائي للجلسة"""
        print("\n" + "="*60)
        print("📊 FINAL SESSION REPORT")
        print("="*60)
        for kid in self.kids:
            rate = kid.get_success_rate()
            bar = "█" * int(rate / 10) + "░" * (10 - int(rate / 10))
            print(f"\n👦 {kid.name} ({kid.severity.upper()})")
            print(f"   Progress: [{bar}] {rate}%")
            print(f"   Interactions: {kid.total_interactions}")
            print(f"   Successes:    {kid.successful_responses}")
            print(f"   Score:        {kid.session_score}")
            print(f"   Last emotion: {kid.current_emotion}")
        print("\n" + "="*60)

    def stop(self):
        self.running = False
        self.print_final_report()

