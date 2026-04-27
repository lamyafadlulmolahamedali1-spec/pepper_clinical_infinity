#!/usr/bin/env python3
"""
PEPPER ULTIMATE - التمارين اللانهائية مع ديتكشن الجسم الكامل
- عد الحلويات (3، 4، 5)
- ديتكشن حركات الجسم بالكامل (هيكل عظمي)
- تمارين نطق مع تسجيل صوتي
- بالونات تطير عند الإجابة الصحيحة
- تمارين لا نهائية يتم توليدها تلقائياً
"""

import os
import sys
import time
import threading
import random
import csv
import math
import wave
import tempfile
from datetime import datetime

os.environ['QT_QPA_PLATFORM'] = 'xcb'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

# استيراد المكتبات المطلوبة
import cv2
import numpy as np
import mediapipe as mp
import pyttsx3
import speech_recognition as sr

print("✅ جميع المكتبات تم تحميلها")

# ============================================================
# الإعدادات
# ============================================================
print("\n" + "="*64)
print("  PEPPER ULTIMATE - التمارين اللانهائية")
print("="*64)
CHILD_NAME = input("\n👦 أدخل اسم الطفل: ").strip() or "طفل"
CSV_FILE = f"{CHILD_NAME.replace(' ', '_')}_Results.csv"

with open(CSV_FILE, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(["الوقت", "الطفل", "التمرين", "النوع", "النتيجة", "النقاط", "النجوم"])

# ============================================================
# توليد تمارين لا نهائية
# ============================================================
FRUITS = ["🍎", "🍌", "🍊", "🍇", "🍓", "🥝", "🍒", "🥭", "🍑", "🍉"]
NUMBERS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

def generate_counting_task():
    """توليد تمرين عد عشوائي"""
    number = random.choice([3, 4, 5])  # أرقام بسيطة للبدء
    fruit = random.choice(FRUITS)
    options = [number, number+1, number-1]
    random.shuffle(options)
    correct_idx = options.index(number)
    
    return {
        "id": f"count_{number}_{fruit}",
        "name": f"عد {fruit}",
        "domain": "Counting",
        "type": "counting",
        "target": number,
        "fruit": fruit,
        "options": options,
        "correct": correct_idx,
        "tokens": 3,
        "instruction": f"كم عدد {fruit} في الصورة؟",
        "success": f"ممتاز! العدد {number} صحيح!"
    }

MOTOR_ACTIONS = [
    {"id": "clap", "name": "👏 صفق", "action": "clap", 
     "instruction": "صفق بيديك!", "success": "تصفيق رائع!"},
    {"id": "wave", "name": "👋 لوح", "action": "wave",
     "instruction": "لوح بيدك!", "success": "تحية جميلة!"},
    {"id": "raise_hand", "name": "✋ ارفع يدك", "action": "raise_hand",
     "instruction": "ارفع يدك للأعلى!", "success": "يدك مرفوعة!"},
    {"id": "touch_nose", "name": "👆 المس أنفك", "action": "touch_nose",
     "instruction": "المس أنفك!", "success": "لمست أنفك!"},
    {"id": "touch_ear", "name": "👂 المس أذنك", "action": "touch_ear",
     "instruction": "المس أذنك!", "success": "لمست أذنك!"},
    {"id": "arms_out", "name": "🤸 افرد ذراعيك", "action": "arms_out",
     "instruction": "افرد ذراعيك على الجانبين!", "success": "ذراعيك ممدودان!"},
]

def generate_motor_task():
    """توليد تمرين حركي عشوائي"""
    return random.choice(MOTOR_ACTIONS).copy()

SPEECH_WORDS = ["تفاحة", "قطة", "كلب", "بيت", "شمس", "قمر", "زهرة", "طائر", "سمكة", "حليب"]

def generate_speech_task():
    """توليد تمرين نطق عشوائي"""
    word = random.choice(SPEECH_WORDS)
    return {
        "id": f"speech_{word}",
        "name": f"🗣️ قل {word}",
        "domain": "Speech",
        "type": "speech",
        "target": word,
        "tokens": 4,
        "instruction": f"قل الكلمة: {word}!",
        "success": f"أحسنت! نطق {word} صحيح!"
    }

# قائمة بجميع أنواع التمارين
TASK_TYPES = ["counting", "motor", "speech", "counting", "motor", "counting"]

def generate_infinite_task():
    """توليد تمرين لا نهائي عشوائي"""
    task_type = random.choice(TASK_TYPES)
    if task_type == "counting":
        return generate_counting_task()
    elif task_type == "motor":
        return generate_motor_task()
    else:
        return generate_speech_task()

# ============================================================
# الصوت
# ============================================================
class Voice:
    def __init__(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 130)
        print("✅ الصوت جاهز")
    
    def say(self, text):
        print(f"\n🔊 بيبر: {text}")
        self.engine.say(text)
        self.engine.runAndWait()

voice = Voice()

# ============================================================
# التعرف على الصوت
# ============================================================
class SpeechRecognizer:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 300
        self.microphone = None
        try:
            self.microphone = sr.Microphone()
            with self.microphone as src:
                self.recognizer.adjust_for_ambient_noise(src, duration=0.5)
            print("✅ التعرف على الصوت جاهز")
        except:
            print("⚠️ الميكروفون غير متوفر")
    
    def listen(self):
        if not self.microphone:
            return ""
        try:
            with self.microphone as src:
                audio = self.recognizer.listen(src, timeout=3, phrase_time_limit=3)
                text = self.recognizer.recognize_google(audio, language="ar")
                return text
        except:
            return ""

# ============================================================
# كاميرا وديتكشن الجسم بالكامل
# ============================================================
class BodyDetectionThread(QThread):
    pose_signal = pyqtSignal(object)  # ارسال نقاط الهيكل العظمي
    action_signal = pyqtSignal(str)   # ارسال الحركة المكتشفة
    
    def __init__(self):
        super().__init__()
        self.running = True
        self.cap = None
        self.pose = None
        self.current_action = None
        self.action_detected = False
        self.last_wrist_y = 0
        self.last_hand_distance = 1
        
        # فتح الكاميرا
        for idx in [1, 0, 2]:
            cap = cv2.VideoCapture(idx)
            if cap.isOpened():
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                self.cap = cap
                print(f"✅ كاميرا {idx} تعمل")
                break
            cap.release()
        
        # تهيئة MediaPipe Pose
        try:
            self.pose = mp.solutions.pose.Pose(
                static_image_mode=False,
                model_complexity=1,
                smooth_landmarks=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
            print("✅ ديتكشن الجسم جاهز")
        except Exception as e:
            print(f"⚠️ خطأ في MediaPipe: {e}")
    
    def detect_action(self, landmarks):
        """كشف الحركة بناءً على نقاط الهيكل العظمي"""
        if not landmarks:
            return None
        
        # استخراج النقاط المهمة
        nose = landmarks[mp.solutions.pose.PoseLandmark.NOSE]
        left_shoulder = landmarks[mp.solutions.pose.PoseLandmark.LEFT_SHOULDER]
        right_shoulder = landmarks[mp.solutions.pose.PoseLandmark.RIGHT_SHOULDER]
        left_elbow = landmarks[mp.solutions.pose.PoseLandmark.LEFT_ELBOW]
        right_elbow = landmarks[mp.solutions.pose.PoseLandmark.RIGHT_ELBOW]
        left_wrist = landmarks[mp.solutions.pose.PoseLandmark.LEFT_WRIST]
        right_wrist = landmarks[mp.solutions.pose.PoseLandmark.RIGHT_WRIST]
        left_hip = landmarks[mp.solutions.pose.PoseLandmark.LEFT_HIP]
        right_hip = landmarks[mp.solutions.pose.PoseLandmark.RIGHT_HIP]
        
        # كشف التصفيق (اليدين قريبتين من بعض)
        hand_distance = abs(left_wrist.x - right_wrist.x) + abs(left_wrist.y - right_wrist.y)
        if hand_distance < 0.15:
            self.last_hand_distance = hand_distance
            return "clap"
        
        # كشف التحية (اليد مرفوعة وتهتز)
        left_raised = left_wrist.y < left_shoulder.y - 0.1
        right_raised = right_wrist.y < right_shoulder.y - 0.1
        if left_raised or right_raised:
            wrist_y = left_wrist.y if left_raised else right_wrist.y
            if abs(wrist_y - self.last_wrist_y) > 0.03:
                self.last_wrist_y = wrist_y
                return "wave"
        
        # كشف رفع اليد
        if left_raised or right_raised:
            return "raise_hand"
        
        # كشف لمس الأنف (اليد قريبة من الوجه)
        left_to_nose = abs(left_wrist.x - nose.x) + abs(left_wrist.y - nose.y)
        right_to_nose = abs(right_wrist.x - nose.x) + abs(right_wrist.y - nose.y)
        if left_to_nose < 0.15 or right_to_nose < 0.15:
            return "touch_nose"
        
        # كشف لمس الأذن
        left_ear = landmarks[mp.solutions.pose.PoseLandmark.LEFT_EAR]
        right_ear = landmarks[mp.solutions.pose.PoseLandmark.RIGHT_EAR]
        left_to_ear = abs(left_wrist.x - left_ear.x) + abs(left_wrist.y - left_ear.y)
        right_to_ear = abs(right_wrist.x - right_ear.x) + abs(right_wrist.y - right_ear.y)
        if left_to_ear < 0.12 or right_to_ear < 0.12:
            return "touch_ear"
        
        # كشف فرد الذراعين
        left_arm_out = abs(left_elbow.x - left_shoulder.x) > 0.2
        right_arm_out = abs(right_elbow.x - right_shoulder.x) > 0.2
        if left_arm_out and right_arm_out:
            return "arms_out"
        
        return None
    
    def draw_skeleton(self, frame, landmarks):
        """رسم الهيكل العظمي على الفيديو"""
        h, w = frame.shape[:2]
        
        # النقاط الرئيسية
        connections = [
            (mp.solutions.pose.PoseLandmark.NOSE, mp.solutions.pose.PoseLandmark.LEFT_EAR),
            (mp.solutions.pose.PoseLandmark.NOSE, mp.solutions.pose.PoseLandmark.RIGHT_EAR),
            (mp.solutions.pose.PoseLandmark.LEFT_SHOULDER, mp.solutions.pose.PoseLandmark.RIGHT_SHOULDER),
            (mp.solutions.pose.PoseLandmark.LEFT_SHOULDER, mp.solutions.pose.PoseLandmark.LEFT_ELBOW),
            (mp.solutions.pose.PoseLandmark.LEFT_ELBOW, mp.solutions.pose.PoseLandmark.LEFT_WRIST),
            (mp.solutions.pose.PoseLandmark.RIGHT_SHOULDER, mp.solutions.pose.PoseLandmark.RIGHT_ELBOW),
            (mp.solutions.pose.PoseLandmark.RIGHT_ELBOW, mp.solutions.pose.PoseLandmark.RIGHT_WRIST),
            (mp.solutions.pose.PoseLandmark.LEFT_SHOULDER, mp.solutions.pose.PoseLandmark.LEFT_HIP),
            (mp.solutions.pose.PoseLandmark.RIGHT_SHOULDER, mp.solutions.pose.PoseLandmark.RIGHT_HIP),
            (mp.solutions.pose.PoseLandmark.LEFT_HIP, mp.solutions.pose.PoseLandmark.RIGHT_HIP),
        ]
        
        # رسم الخطوط
        for connection in connections:
            start = landmarks[connection[0]]
            end = landmarks[connection[1]]
            start_point = (int(start.x * w), int(start.y * h))
            end_point = (int(end.x * w), int(end.y * h))
            cv2.line(frame, start_point, end_point, (0, 255, 0), 3)
        
        # رسم النقاط
        for landmark in landmarks:
            x = int(landmark.x * w)
            y = int(landmark.y * h)
            cv2.circle(frame, (x, y), 5, (0, 0, 255), -1)
        
        return frame
    
    def run(self):
        if not self.cap:
            print("⚠️ لا توجد كاميرا - سيتم محاكاة الديتكشن")
            while self.running:
                self.action_signal.emit(None)
                self.msleep(100)
            return
        
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                self.msleep(10)
                continue
            
            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.pose.process(rgb)
            
            detected_action = None
            
            if results.pose_landmarks:
                # رسم الهيكل العظمي
                frame = self.draw_skeleton(frame, results.pose_landmarks.landmark)
                # كشف الحركة
                detected_action = self.detect_action(results.pose_landmarks.landmark)
                
                # عرض الحركة المكتشفة على الشاشة
                if detected_action:
                    cv2.putText(frame, f"الحركة: {detected_action}", (10, 50),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            
            # عرض الإطار
            cv2.imshow("Body Detection - الهيكل العظمي", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            
            # ارسال الحركة المكتشفة
            if detected_action:
                self.action_signal.emit(detected_action)
            
            self.msleep(33)
        
        cv2.destroyAllWindows()
    
    def stop(self):
        self.running = False
        if self.cap:
            self.cap.release()
        self.quit()
        self.wait()

# ============================================================
# بالونات متطايرة
# ============================================================
class BalloonWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.balloons = []
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_animation)
        self.hide()
    
    def launch(self):
        """إطلاق البالونات"""
        parent = self.parent()
        if parent:
            self.setGeometry(parent.rect())
        
        self.balloons = []
        colors = ["#ef4444", "#3b82f6", "#22c55e", "#fbbf24", "#a855f7", "#ec4899", "#f97316"]
        
        for _ in range(15):
            self.balloons.append({
                "x": random.randint(50, self.width() - 50),
                "y": self.height() - random.randint(20, 100),
                "vx": random.uniform(-2, 2),
                "vy": random.uniform(-8, -5),
                "color": random.choice(colors),
                "r": random.randint(25, 45),
                "emoji": random.choice(["🎈", "🎉", "⭐", "🌟", "🎊", "✨"])
            })
        
        self.show()
        self.raise_()
        self.timer.start(30)
        QTimer.singleShot(4000, self.stop)
    
    def update_animation(self):
        for b in self.balloons:
            b["x"] += b["vx"]
            b["y"] += b["vy"]
            b["vy"] *= 0.98
            b["vx"] += random.uniform(-0.2, 0.2)
        
        self.balloons = [b for b in self.balloons if b["y"] > -80]
        self.update()
        
        if not self.balloons:
            self.stop()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        for b in self.balloons:
            # رسم البالون
            color = QColor(b["color"])
            color.setAlpha(200)
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(int(b["x"] - b["r"]), int(b["y"] - b["r"]), b["r"] * 2, b["r"] * 2)
            
            # رسم الخيط
            painter.setPen(QPen(QColor(b["color"]).darker(140), 2))
            painter.drawLine(int(b["x"]), int(b["y"] + b["r"]), 
                           int(b["x"] + random.randint(-8, 8)), int(b["y"] + b["r"] + 20))
            
            # رسم الإيموجي
            painter.setFont(QFont("Arial", b["r"] // 2))
            painter.drawText(int(b["x"] - b["r"] // 2), int(b["y"] + b["r"] // 3), b["emoji"])
        
        painter.end()
    
    def stop(self):
        self.timer.stop()
        self.hide()
        self.balloons = []

# ============================================================
# زر قابل للنقر
# ============================================================
class FruitCard(QPushButton):
    def __init__(self, fruit, count, idx):
        super().__init__()
        self.count = count
        self.idx = idx
        
        # إنشاء صورة عرض الحلويات
        text = fruit * count
        self.setText(f"{text}\n{count}")
        self.setFont(QFont("Arial", 24))
        self.setFixedSize(180, 180)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 #1e1b4b, stop:1 #0c0f2e);
                border-radius: 20px;
                border: 3px solid #fbbf24;
                color: #fbbf24;
                font-weight: bold;
            }
            QPushButton:hover {
                border: 5px solid #a78bfa;
                background: #2a2550;
            }
        """)
    
    def flash_correct(self):
        self.setStyleSheet(self.styleSheet() + "QPushButton { border: 5px solid #22c55e !important; background: #166534 !important; }")
        QTimer.singleShot(800, self.reset_style)
    
    def reset_style(self):
        self.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 #1e1b4b, stop:1 #0c0f2e);
                border-radius: 20px;
                border: 3px solid #fbbf24;
                color: #fbbf24;
                font-weight: bold;
            }
        """)

class MotorCard(QPushButton):
    def __init__(self, text, action):
        super().__init__()
        self.action = action
        self.setText(text)
        self.setFont(QFont("Arial", 24))
        self.setFixedSize(200, 150)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 #1e1b4b, stop:1 #0c0f2e);
                border-radius: 20px;
                border: 3px solid #4f46e5;
                color: #e0e6ff;
                font-size: 20px;
                font-weight: bold;
            }
            QPushButton:hover { border: 4px solid #a78bfa; background: #2a2550; }
        """)
    
    def flash_correct(self):
        self.setStyleSheet(self.styleSheet() + "QPushButton { border: 5px solid #22c55e !important; background: #166534 !important; }")
        QTimer.singleShot(800, self.reset_style)
    
    def reset_style(self):
        self.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 #1e1b4b, stop:1 #0c0f2e);
                border-radius: 20px;
                border: 3px solid #4f46e5;
                color: #e0e6ff;
                font-size: 20px;
                font-weight: bold;
            }
        """)

# ============================================================
# النافذة الرئيسية
# ============================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"بيبر التمارين اللانهائية - {CHILD_NAME}")
        self.setMinimumSize(1400, 850)
        
        self.current_task = None
        self.locked = False
        self.score = 0
        self.consecutive = 0
        self.mastered = 0
        self.buttons = []
        self.speech_recognizer = SpeechRecognizer()
        
        self.setup_ui()
        self.setup_body_detection()
        self.start_session()
    
    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        central.setStyleSheet("background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #0a0a1a,stop:1 #0f0f2a);")
        
        main_layout = QHBoxLayout(central)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 15, 20, 15)
        
        # ========== اللوحة اليمنى ==========
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(15)
        
        # الهيدر مع بيبر
        header = QFrame()
        header.setStyleSheet("background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #1a0a3d,stop:1 #0a0f28); border-radius: 20px; border: 2px solid #4f46e5;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 10, 20, 10)
        
        pepper_icon = QLabel("🤖")
        pepper_icon.setFont(QFont("Arial", 40))
        header_layout.addWidget(pepper_icon)
        
        title_box = QVBoxLayout()
        title = QLabel("بيبر التمارين اللانهائية")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setStyleSheet("color: #a78bfa;")
        title_box.addWidget(title)
        
        child = QLabel(f"الطفل: {CHILD_NAME}")
        child.setFont(QFont("Arial", 12))
        child.setStyleSheet("color: #60a5fa;")
        title_box.addWidget(child)
        header_layout.addLayout(title_box, 1)
        
        self.stars_label = QLabel("☆☆☆")
        self.stars_label.setFont(QFont("Arial", 24))
        self.stars_label.setStyleSheet("color: #fbbf24; background: #1e1b4b; padding: 5px 20px; border-radius: 15px;")
        header_layout.addWidget(self.stars_label)
        
        right_layout.addWidget(header)
        
        # التعليمات
        instr_frame = QFrame()
        instr_frame.setStyleSheet("background: #1e1b4b; border-radius: 15px; border: 2px solid #4f46e5;")
        instr_layout = QVBoxLayout(instr_frame)
        instr_layout.setContentsMargins(20, 20, 20, 20)
        
        self.instruction = QLabel("جاري التحضير...")
        self.instruction.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        self.instruction.setStyleSheet("color: #e0e6ff;")
        self.instruction.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.instruction.setWordWrap(True)
        instr_layout.addWidget(self.instruction)
        
        right_layout.addWidget(instr_frame)
        
        # منطقة المحتوى (الأزرار)
        self.content_frame = QFrame()
        self.content_frame.setStyleSheet("background: #0c0f1e; border-radius: 20px; border: 2px solid #1a1f40;")
        self.content_layout = QVBoxLayout(self.content_frame)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(self.content_frame, 1)
        
        # التغذية الراجعة
        feedback_frame = QFrame()
        feedback_frame.setStyleSheet("background: #0c0f1e; border-radius: 15px;")
        feedback_layout = QHBoxLayout(feedback_frame)
        feedback_layout.setContentsMargins(20, 10, 20, 10)
        
        self.feedback_icon = QLabel("💤")
        self.feedback_icon.setFont(QFont("Arial", 24))
        feedback_layout.addWidget(self.feedback_icon)
        
        self.feedback = QLabel("بيبر يستعد...")
        self.feedback.setFont(QFont("Arial", 14))
        self.feedback.setStyleSheet("color: #9ca3af;")
        feedback_layout.addWidget(self.feedback, 1)
        
        right_layout.addWidget(feedback_frame)
        
        # شريط التقدم
        self.progress = QProgressBar()
        self.progress.setFixedHeight(10)
        self.progress.setStyleSheet("""
            QProgressBar { background: #1e1b4b; border-radius: 5px; }
            QProgressBar::chunk { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #4f46e5,stop:1 #a78bfa); border-radius: 5px; }
        """)
        right_layout.addWidget(self.progress)
        
        # إحصائيات
        stats_bar = QFrame()
        stats_bar.setStyleSheet("background: #07090f; border-radius: 15px;")
        stats_layout = QHBoxLayout(stats_bar)
        stats_layout.setContentsMargins(20, 10, 20, 10)
        
        self.score_label = QLabel(f"🏆 النقاط: {self.score}")
        self.score_label.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        self.score_label.setStyleSheet("color: #fbbf24;")
        stats_layout.addWidget(self.score_label)
        
        self.mastered_label = QLabel(f"⭐ أتقن: {self.mastered}")
        self.mastered_label.setFont(QFont("Arial", 12))
        self.mastered_label.setStyleSheet("color: #34d399;")
        stats_layout.addWidget(self.mastered_label)
        
        right_layout.addWidget(stats_bar)
        
        # ========== اللوحة اليسرى ==========
        left_panel = QFrame()
        left_panel.setFixedWidth(450)
        left_panel.setStyleSheet("background: #0c0f1e; border-radius: 20px; border: 2px solid #1a1f40;")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        
        # معلومات الكاميرا
        cam_info = QLabel("📷 كشف حركات الجسم")
        cam_info.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        cam_info.setStyleSheet("color: #a78bfa;")
        cam_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(cam_info)
        
        # حالة الكاميرا
        self.cam_status = QLabel("✅ الكاميرا تعمل - قم بالحركة")
        self.cam_status.setFont(QFont("Arial", 11))
        self.cam_status.setStyleSheet("color: #34d399; background: #1e1b4b; border-radius: 10px; padding: 8px;")
        self.cam_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(self.cam_status)
        
        # قائمة الحركات
        actions_frame = QFrame()
        actions_frame.setStyleSheet("background: #1e1b4b; border-radius: 15px;")
        actions_layout = QVBoxLayout(actions_frame)
        
        actions_title = QLabel("الحركات المتاحة:")
        actions_title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        actions_title.setStyleSheet("color: #fbbf24;")
        actions_layout.addWidget(actions_title)
        
        for action in MOTOR_ACTIONS:
            lbl = QLabel(f"  {action['name']}")
            lbl.setFont(QFont("Arial", 11))
            lbl.setStyleSheet("color: #e0e6ff;")
            actions_layout.addWidget(lbl)
        
        left_layout.addWidget(actions_frame)
        left_layout.addStretch()
        
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel, 1)
        
        # بالونات
        self.balloons = BalloonWidget(central)
    
    def setup_body_detection(self):
        self.body_thread = BodyDetectionThread()
        self.body_thread.action_signal.connect(self.on_body_action)
        self.body_thread.start()
    
    def on_body_action(self, action):
        if action and self.current_task and self.current_task.get("type") == "motor" and not self.locked:
            target_action = self.current_task.get("action")
            if action == target_action:
                self.task_success()
                self.cam_status.setText(f"✅ تم كشف الحركة: {action}")
                self.cam_status.setStyleSheet("color: #34d399; background: #1e1b4b; border-radius: 10px; padding: 8px;")
                QTimer.singleShot(2000, lambda: self.cam_status.setText("✅ الكاميرا تعمل - قم بالحركة"))
                QTimer.singleShot(2000, lambda: self.cam_status.setStyleSheet("color: #34d399; background: #1e1b4b; border-radius: 10px; padding: 8px;"))
    
    def start_session(self):
        QTimer.singleShot(500, self.greet)
    
    def greet(self):
        voice.say(f"مرحباً {CHILD_NAME}! أنا بيبر. هيا نلعب ونتعلم معاً!")
        QTimer.singleShot(3000, self.next_task)
    
    def next_task(self):
        # توليد تمرين جديد لا نهائي
        self.current_task = generate_infinite_task()
        
        # تحديث الواجهة
        self.instruction.setText(self.current_task["instruction"])
        self.feedback.setText("حان دورك!")
        self.feedback.setStyleSheet("color: #60a5fa;")
        self.feedback_icon.setText("🎯")
        
        # مسح الأزرار السابقة
        self.clear_buttons()
        
        # عرض التمرين حسب نوعه
        if self.current_task["type"] == "counting":
            self.show_counting_task()
        elif self.current_task["type"] == "motor":
            self.show_motor_task()
        else:  # speech
            self.show_speech_task()
        
        # بدء المؤقت (20 ثانية)
        if hasattr(self, 'task_timer'):
            self.task_timer.stop()
        self.task_timer = QTimer()
        self.task_timer.setSingleShot(True)
        self.task_timer.timeout.connect(self.task_timeout)
        self.task_timer.start(20000)
        
        # شريط التقدم
        self.progress.setValue(0)
        self.progress_anim = QPropertyAnimation(self.progress, b"value")
        self.progress_anim.setDuration(20000)
        self.progress_anim.setStartValue(0)
        self.progress_anim.setEndValue(100)
        self.progress_anim.start()
        
        # فتح القفل
        self.locked = False
        
        # النطق
        voice.say(self.current_task["instruction"])
    
    def show_counting_task(self):
        """عرض تمرين العد مع الحلويات"""
        task = self.current_task
        fruit = task["fruit"]
        options = task["options"]
        
        grid = QWidget()
        grid_layout = QGridLayout(grid)
        grid_layout.setSpacing(20)
        grid_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        for i, count in enumerate(options):
            btn = FruitCard(fruit, count, i)
            btn.clicked.connect(lambda checked, idx=i: self.check_counting_answer(idx))
            self.buttons.append(btn)
            grid_layout.addWidget(btn, i//2, i%2)
        
        self.content_layout.addWidget(grid)
    
    def show_motor_task(self):
        """عرض تمرين حركي"""
        task = self.current_task
        motor_frame = QFrame()
        motor_frame.setStyleSheet("background: #1e1b4b; border-radius: 20px; border: 3px solid #a78bfa;")
        motor_layout = QVBoxLayout(motor_frame)
        motor_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # عرض الحركة المطلوبة
        action_label = QLabel(task["name"])
        action_label.setFont(QFont("Arial", 32, QFont.Weight.Bold))
        action_label.setStyleSheet("color: #a78bfa;")
        action_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        motor_layout.addWidget(action_label)
        
        # أيقونة الحركة
        icon_label = QLabel("👇 قلد هذه الحركة! 👇")
        icon_label.setFont(QFont("Arial", 20))
        icon_label.setStyleSheet("color: #34d399;")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        motor_layout.addWidget(icon_label)
        
        self.content_layout.addWidget(motor_frame)
        
        # تنبيه للطفل
        self.feedback.setText(f"قم بـ {task['name']} - الكاميرا تراقبك!")
    
    def show_speech_task(self):
        """عرض تمرين نطق"""
        task = self.current_task
        speech_frame = QFrame()
        speech_frame.setStyleSheet("background: #1e1b4b; border-radius: 20px; border: 3px solid #fbbf24;")
        speech_layout = QVBoxLayout(speech_frame)
        speech_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # الكلمة المطلوبة
        word_label = QLabel(f"🗣️ {task['target']} 🗣️")
        word_label.setFont(QFont("Arial", 40, QFont.Weight.Bold))
        word_label.setStyleSheet("color: #fbbf24;")
        word_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        speech_layout.addWidget(word_label)
        
        # زر التسجيل
        record_btn = QPushButton("🎤 اضغط وتكلم 🎤")
        record_btn.setFixedSize(250, 60)
        record_btn.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        record_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #dc2626,stop:1 #ef4444);
                color: white;
                border-radius: 30px;
                border: 2px solid #fca5a5;
            }
            QPushButton:pressed { background: #991b1b; }
        """)
        record_btn.pressed.connect(self.start_recording)
        record_btn.released.connect(self.stop_recording)
        speech_layout.addWidget(record_btn)
        
        self.content_layout.addWidget(speech_frame)
        self.record_btn = record_btn
    
    def start_recording(self):
        self.feedback.setText("🎤 جاري التسجيل... تكلم الآن!")
        self.feedback_icon.setText("🔴")
    
    def stop_recording(self):
        self.feedback.setText("⏳ جاري معالجة الصوت...")
        threading.Thread(target=self.process_speech, daemon=True).start()
    
    def process_speech(self):
        text = self.speech_recognizer.listen()
        if text and self.current_task and self.current_task.get("type") == "speech" and not self.locked:
            target_word = self.current_task["target"]
            if target_word in text:
                QTimer.invokeMethod(self, "task_success")
            else:
                QTimer.invokeMethod(self, "task_fail", Qt.ConnectionType.QueuedConnection)
    
    def check_counting_answer(self, idx):
        if self.locked:
            return
        
        if idx == self.current_task["correct"]:
            self.task_success()
        else:
            self.task_fail()
    
    def task_success(self):
        if self.locked:
            return
        
        self.locked = True
        
        # إيقاف المؤقت
        if hasattr(self, 'task_timer'):
            self.task_timer.stop()
        if hasattr(self, 'progress_anim'):
            self.progress_anim.stop()
        
        # حساب النقاط
        points = self.current_task.get("tokens", 2) * 5
        self.score += points
        self.consecutive += 1
        
        # تحديث الواجهة
        self.feedback.setText(f"✅ صحيح! +{points} نقطة!")
        self.feedback.setStyleSheet("color: #34d399;")
        self.feedback_icon.setText("✅")
        self.score_label.setText(f"🏆 النقاط: {self.score}")
        
        # تحديث النجوم
        stars = "⭐" * self.consecutive + "☆" * (3 - self.consecutive)
        self.stars_label.setText(stars)
        
        # إطلاق البالونات
        self.balloons.launch()
        
        # تسجيل في CSV
        with open(CSV_FILE, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().strftime("%H:%M:%S"),
                CHILD_NAME,
                self.current_task["name"],
                self.current_task["type"],
                "صحيح",
                points,
                self.consecutive
            ])
        
        # التحقق من الإتقان
        if self.consecutive >= 3:
            self.consecutive = 0
            self.mastered += 1
            self.mastered_label.setText(f"⭐ أتقن: {self.mastered}")
            voice.say(f"ممتاز {CHILD_NAME}! أتقنت {self.current_task['name']}! +{points} نقطة!")
            self.feedback.setText(f"🏆 أتقنت التمرين! +{points} نقطة! 🏆")
        else:
            voice.say(self.current_task.get("success", "أحسنت!"))
        
        # الانتقال للتمرين التالي
        QTimer.singleShot(2500, self.next_task)
    
    def task_fail(self):
        if self.locked:
            return
        
        self.locked = True
        self.consecutive = 0
        
        # تحديث الواجهة
        self.feedback.setText(f"❌ حاول مرة أخرى! الإجابة الصحيحة: {self.current_task.get('target', '?')}")
        self.feedback.setStyleSheet("color: #f87171;")
        self.feedback_icon.setText("❌")
        self.stars_label.setText("☆☆☆")
        
        # تسجيل في CSV
        with open(CSV_FILE, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().strftime("%H:%M:%S"),
                CHILD_NAME,
                self.current_task["name"],
                self.current_task["type"],
                "خطأ",
                0,
                0
            ])
        
        voice.say("لا بأس! جرب التمرين التالي!")
        QTimer.singleShot(2500, self.next_task)
    
    def task_timeout(self):
        if self.locked:
            return
        
        self.locked = True
        self.consecutive = 0
        
        self.feedback.setText(f"⏰ انتهى الوقت! الإجابة: {self.current_task.get('target', '?')}")
        self.feedback.setStyleSheet("color: #f59e0b;")
        self.feedback_icon.setText("⏰")
        self.stars_label.setText("☆☆☆")
        
        # تسجيل في CSV
        with open(CSV_FILE, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().strftime("%H:%M:%S"),
                CHILD_NAME,
                self.current_task["name"],
                self.current_task["type"],
                "انتهى الوقت",
                0,
                0
            ])
        
        voice.say("انتهى الوقت! هيا نجرب التمرين التالي!")
        QTimer.singleShot(2500, self.next_task)
    
    def clear_buttons(self):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.buttons.clear()
    
    def closeEvent(self, event):
        if hasattr(self, 'body_thread'):
            self.body_thread.stop()
        
        duration = int((time.time() - getattr(self, 'start_time', time.time())) / 60)
        print(f"\n{'='*64}")
        print(f"🎉 انتهت الجلسة — {CHILD_NAME}")
        print(f"{'='*64}")
        print(f"النقاط النهائية: {self.score}")
        print(f"التمارين المتقنة: {self.mastered}")
        print(f"الملف: {CSV_FILE}")
        print('='*64)
        event.accept()

# ============================================================
# التشغيل الرئيسي
# ============================================================
def main():
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║  بيبر التمارين اللانهائية                                     ║
╠══════════════════════════════════════════════════════════════╣
║  ✓ عد الحلويات (٣، ٤، ٥ حلويات)                             ║
║  ✓ ديتكشن الجسم الكامل (هيكل عظمي)                          ║
║  ✓ تمارين حركية (تصفيق، تحية، لمس الأنف، لمس الأذن)         ║
║  ✓ تمارين نطق (تسجيل صوتي)                                  ║
║  ✓ بالونات تطير عند الإجابة الصحيحة                          ║
║  ✓ تمارين لا نهائية يتم توليدها تلقائياً                     ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.start_time = time.time()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
