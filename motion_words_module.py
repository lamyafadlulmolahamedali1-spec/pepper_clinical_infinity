#!/usr/bin/env python3
"""
Motion-from-Words Module
Pepper تتحرك بشكل مناسب حسب الكلام
- clap    → تصفق
- wave    → تلوح
- point   → تشير
- breathe → حركة تنفس هادئة
- dance   → ترقص
- reach   → تمد يدها
- hug     → حركة احتضان
- happy   → حركة فرح
- sad     → حركة حزن
- calm    → حركة هادئة
"""

import time
import math
import threading
import re


# ========== خريطة الكلمات → الحركات ==========
WORD_MOTION_MAP = {
    # أفعال مباشرة
    "clap":     "clap",
    "clapping": "clap",
    "صفق":      "clap",

    "wave":     "wave",
    "waving":   "wave",
    "hello":    "wave",
    "hi":       "wave",
    "goodbye":  "wave",
    "bye":      "wave",
    "مرحبا":    "wave",

    "point":    "point",
    "look":     "point",
    "see":      "point",
    "انظر":     "point",

    "breathe":  "breathe",
    "breathing": "breathe",
    "breath":   "breathe",
    "calm":     "breathe",
    "relax":    "breathe",
    "تنفس":     "breathe",
    "هدأ":      "breathe",

    "dance":    "dance",
    "dancing":  "dance",
    "ارقص":     "dance",

    "reach":    "reach",
    "grab":     "reach",
    "take":     "reach",
    "hold":     "reach",

    "hug":      "hug",
    "embrace":  "hug",

    "happy":    "happy",
    "great":    "happy",
    "amazing":  "happy",
    "wonderful": "happy",
    "awesome":  "happy",
    "superstar": "happy",
    "ممتاز":    "happy",
    "رائع":     "happy",

    "sad":      "sad",
    "sorry":    "sad",
    "okay":     "calm",
    "alright":  "calm",

    "nose":     "nose",    # touch your nose
    "stand":    "stand",
    "sit":      "sit",
    "up":       "reach",
}

# الأولوية: لو كلمتين موجودتين، خذ الأعلى أولوية
MOTION_PRIORITY = {
    "dance": 10, "clap": 9, "wave": 8, "hug": 7,
    "happy": 6, "point": 5, "reach": 4,
    "breathe": 3, "calm": 2, "sad": 1, "nose": 5,
    "stand": 4, "sit": 3
}


class MotionWordsModule:
    def __init__(self, pepper_obj):
        self.pepper = pepper_obj
        self.is_moving = False
        self.motion_queue = []
        threading.Thread(target=self._motion_executor, daemon=True).start()
        print("✅ Motion-Words Module ready!")

    def analyze_text(self, text):
        """تحليل النص واستخراج أفضل حركة"""
        text_lower = text.lower()
        words = re.findall(r'\b\w+\b', text_lower)

        found_motions = {}
        for word in words:
            if word in WORD_MOTION_MAP:
                motion = WORD_MOTION_MAP[word]
                priority = MOTION_PRIORITY.get(motion, 0)
                if motion not in found_motions or priority > found_motions[motion]:
                    found_motions[motion] = priority

        if not found_motions:
            return "talk"  # حركة كلام عامة

        # أعلى أولوية
        best = max(found_motions, key=found_motions.get)
        return best

    def perform(self, text, async_mode=True):
        """تنفيذ الحركة المناسبة للنص"""
        motion = self.analyze_text(text)
        print(f"[MOTION] Text: '{text[:40]}' → Motion: {motion}")

        if async_mode:
            self.motion_queue.append(motion)
        else:
            self._execute_motion(motion)

        return motion

    def _motion_executor(self):
        """Thread لتنفيذ الحركات بالترتيب"""
        while True:
            if self.motion_queue and not self.is_moving:
                motion = self.motion_queue.pop(0)
                self._execute_motion(motion)
            time.sleep(0.1)

    def _execute_motion(self, motion):
        self.is_moving = True
        try:
            getattr(self, f"_motion_{motion}", self._motion_talk)()
        except Exception as e:
            print(f"[MOTION] Error: {e}")
        self.is_moving = False

    # ========== الحركات ==========

    def _motion_clap(self):
        """تصفيق"""
        for _ in range(4):
            try:
                self.pepper.setAngles("LShoulderPitch", 0.8, 0.25)
                self.pepper.setAngles("RShoulderPitch", 0.8, 0.25)
                self.pepper.setAngles("LElbowRoll",    -0.5, 0.25)
                self.pepper.setAngles("RElbowRoll",     0.5, 0.25)
                time.sleep(0.18)
                self.pepper.setAngles("LShoulderPitch", 1.0, 0.25)
                self.pepper.setAngles("RShoulderPitch", 1.0, 0.25)
                self.pepper.setAngles("LElbowRoll",    -0.1, 0.25)
                self.pepper.setAngles("RElbowRoll",     0.1, 0.25)
                time.sleep(0.18)
            except: pass

    def _motion_wave(self):
        """تلويح"""
        try:
            self.pepper.setAngles("RShoulderPitch", 0.2, 0.2)
            self.pepper.setAngles("RElbowRoll",     0.8, 0.2)
            time.sleep(0.3)
            for _ in range(3):
                self.pepper.setAngles("RWristYaw",  0.5, 0.2)
                time.sleep(0.2)
                self.pepper.setAngles("RWristYaw", -0.5, 0.2)
                time.sleep(0.2)
            self.pepper.setAngles("RShoulderPitch", 1.0, 0.15)
            self.pepper.setAngles("RElbowRoll",     0.3, 0.15)
        except: pass

    def _motion_point(self):
        """إشارة للأمام"""
        try:
            self.pepper.setAngles("LShoulderPitch", 0.1, 0.15)
            self.pepper.setAngles("LShoulderRoll",  0.1, 0.15)
            self.pepper.setAngles("LElbowYaw",     -1.5, 0.15)
            self.pepper.setAngles("LElbowRoll",    -0.03, 0.15)
            time.sleep(1.0)
            self.pepper.setAngles("LShoulderPitch", 1.0, 0.15)
            self.pepper.setAngles("LElbowYaw",     -1.2, 0.15)
        except: pass

    def _motion_breathe(self):
        """حركة تنفس هادئة وبطيئة"""
        try:
            for _ in range(3):
                # شهيق - يدين ترتفعان ببطء
                self.pepper.setAngles("LShoulderPitch", 0.4, 0.04)
                self.pepper.setAngles("RShoulderPitch", 0.4, 0.04)
                time.sleep(1.2)
                # زفير - يدين تنزلان ببطء
                self.pepper.setAngles("LShoulderPitch", 1.0, 0.04)
                self.pepper.setAngles("RShoulderPitch", 1.0, 0.04)
                time.sleep(1.2)
        except: pass

    def _motion_dance(self):
        """رقصة خفيفة"""
        try:
            for _ in range(4):
                self.pepper.setAngles("LShoulderPitch", 0.3, 0.15)
                self.pepper.setAngles("RShoulderPitch", 0.9, 0.15)
                self.pepper.setAngles("HeadYaw",  0.3, 0.15)
                time.sleep(0.25)
                self.pepper.setAngles("LShoulderPitch", 0.9, 0.15)
                self.pepper.setAngles("RShoulderPitch", 0.3, 0.15)
                self.pepper.setAngles("HeadYaw", -0.3, 0.15)
                time.sleep(0.25)
            self.pepper.setAngles("HeadYaw", 0, 0.1)
        except: pass

    def _motion_reach(self):
        """مد اليد"""
        try:
            self.pepper.setAngles("RShoulderPitch", 0.2, 0.12)
            self.pepper.setAngles("RShoulderRoll", -0.1, 0.12)
            self.pepper.setAngles("RElbowRoll",     0.1, 0.12)
            time.sleep(0.8)
            self.pepper.setAngles("RShoulderPitch", 1.0, 0.12)
        except: pass

    def _motion_hug(self):
        """حركة احتضان"""
        try:
            self.pepper.setAngles("LShoulderPitch", 0.5, 0.1)
            self.pepper.setAngles("RShoulderPitch", 0.5, 0.1)
            self.pepper.setAngles("LShoulderRoll",  0.3, 0.1)
            self.pepper.setAngles("RShoulderRoll", -0.3, 0.1)
            self.pepper.setAngles("LElbowRoll",    -0.8, 0.1)
            self.pepper.setAngles("RElbowRoll",     0.8, 0.1)
            time.sleep(1.0)
            self.pepper.setAngles("LShoulderPitch", 1.0, 0.1)
            self.pepper.setAngles("RShoulderPitch", 1.0, 0.1)
            self.pepper.setAngles("LShoulderRoll",  0.0, 0.1)
            self.pepper.setAngles("RShoulderRoll",  0.0, 0.1)
        except: pass

    def _motion_happy(self):
        """فرح واحتفال"""
        try:
            for _ in range(2):
                self.pepper.setAngles("LShoulderPitch", 0.1, 0.2)
                self.pepper.setAngles("RShoulderPitch", 0.1, 0.2)
                self.pepper.setAngles("HeadPitch",     -0.3, 0.2)
                time.sleep(0.3)
                self.pepper.setAngles("LShoulderPitch", 0.8, 0.2)
                self.pepper.setAngles("RShoulderPitch", 0.8, 0.2)
                self.pepper.setAngles("HeadPitch",      0.0, 0.2)
                time.sleep(0.3)
        except: pass

    def _motion_sad(self):
        """حزن - حركة بطيئة لأسفل"""
        try:
            self.pepper.setAngles("HeadPitch",      0.4, 0.05)
            self.pepper.setAngles("LShoulderPitch", 1.2, 0.05)
            self.pepper.setAngles("RShoulderPitch", 1.2, 0.05)
            time.sleep(1.5)
            self.pepper.setAngles("HeadPitch",      0.0, 0.05)
            self.pepper.setAngles("LShoulderPitch", 1.0, 0.05)
            self.pepper.setAngles("RShoulderPitch", 1.0, 0.05)
        except: pass

    def _motion_calm(self):
        """هادئ - حركة ناعمة"""
        try:
            for _ in range(2):
                self.pepper.setAngles("LShoulderPitch", 0.6, 0.05)
                self.pepper.setAngles("RShoulderPitch", 0.6, 0.05)
                time.sleep(0.8)
                self.pepper.setAngles("LShoulderPitch", 1.0, 0.05)
                self.pepper.setAngles("RShoulderPitch", 1.0, 0.05)
                time.sleep(0.8)
        except: pass

    def _motion_nose(self):
        """لمس الأنف - للـ DTT"""
        try:
            self.pepper.setAngles("RShoulderPitch", 0.3, 0.15)
            self.pepper.setAngles("RElbowRoll",     0.3, 0.15)
            self.pepper.setAngles("HeadPitch",      0.2, 0.1)
            time.sleep(0.8)
            self.pepper.setAngles("RShoulderPitch", 1.0, 0.15)
            self.pepper.setAngles("HeadPitch",      0.0, 0.1)
        except: pass

    def _motion_stand(self):
        """حركة الوقوف"""
        try:
            self.pepper.setAngles("LShoulderPitch", 0.5, 0.15)
            self.pepper.setAngles("RShoulderPitch", 0.5, 0.15)
            self.pepper.setAngles("HeadPitch",     -0.2, 0.1)
            time.sleep(0.6)
            self.pepper.setAngles("LShoulderPitch", 1.0, 0.15)
            self.pepper.setAngles("RShoulderPitch", 1.0, 0.15)
            self.pepper.setAngles("HeadPitch",      0.0, 0.1)
        except: pass

    def _motion_sit(self):
        """حركة الجلوس"""
        try:
            self.pepper.setAngles("HeadPitch",      0.3, 0.1)
            self.pepper.setAngles("LShoulderPitch", 0.8, 0.1)
            self.pepper.setAngles("RShoulderPitch", 0.8, 0.1)
            time.sleep(0.8)
            self.pepper.setAngles("HeadPitch",      0.0, 0.1)
        except: pass

    def _motion_talk(self):
        """حركة كلام عامة"""
        try:
            import random
            for _ in range(2):
                angle = random.uniform(0.3, 0.7)
                self.pepper.setAngles("LShoulderPitch", angle, 0.1)
                self.pepper.setAngles("RShoulderPitch", 1.0 - angle + 0.3, 0.1)
                time.sleep(0.3)
            self.pepper.setAngles("LShoulderPitch", 1.0, 0.1)
            self.pepper.setAngles("RShoulderPitch", 1.0, 0.1)
        except: pass


# ===== اختبار مستقل =====
if __name__ == "__main__":
    print("🤖 Motion-Words Test (no robot - showing analysis only)")
    mw = MotionWordsModule(None)

    tests = [
        "Hello Ahmed! How are you today?",
        "Can you clap your hands?",
        "Look at the red ball!",
        "Breathe with me. In and out.",
        "Amazing! You are a superstar!",
        "Touch your nose please!",
        "Let us dance together!",
        "It is okay. Calm down.",
        "مرحباً! كيف حالك؟",
        "ممتاز! أحسنت!"
    ]

    for text in tests:
        motion = mw.analyze_text(text)
        print(f"  '{text[:45]:45}' → {motion}")
