#!/usr/bin/env python3
"""
PEPPER CLINICAL INFINITY - COMPLETE ENGLISH VERSION
- Infinite tasks (counting, motor, speech)
- Full body detection with skeleton overlay on main window
- 10-finger detection
- Balloons celebration
- Auto-advance on timeout
"""

import os
import sys
import time
import threading
import random
import csv
import math
from datetime import datetime

os.environ['QT_QPA_PLATFORM'] = 'xcb'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

import cv2
import numpy as np
import mediapipe as mp
import pyttsx3
import speech_recognition as sr

print("✅ All libraries loaded")

# ============================================================
# CONFIGURATION
# ============================================================
print("\n" + "="*64)
print("  PEPPER CLINICAL INFINITY")
print("="*64)
CHILD_NAME = input("\n👦 Enter Child's Name: ").strip() or "Child"
CSV_FILE = f"{CHILD_NAME.replace(' ', '_')}_Results.csv"

with open(CSV_FILE, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(["Timestamp", "Child", "Task", "Type", "Result", "Score", "Stars"])

# ============================================================
# INFINITE TASK GENERATOR
# ============================================================
FRUITS = ["🍎", "🍌", "🍊", "🍇", "🍓", "🥝", "🍒", "🥭"]
NUMBERS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

def generate_counting_task():
    """Generate random counting task with fruits"""
    number = random.choice([2, 3, 4, 5])
    fruit = random.choice(FRUITS)
    options = [number, number+1, number-1]
    random.shuffle(options)
    correct_idx = options.index(number)
    
    return {
        "id": f"count_{number}_{fruit}",
        "name": f"Count {fruit}",
        "domain": "Counting",
        "type": "counting",
        "target": number,
        "fruit": fruit,
        "options": options,
        "correct": correct_idx,
        "tokens": 3,
        "instruction": f"How many {fruit} are there?",
        "success": f"Excellent! The answer is {number}!"
    }

MOTOR_ACTIONS = [
    {"id": "clap", "name": "👏 CLAP HANDS", "action": "clap", 
     "instruction": "Clap your hands!", "success": "Great clapping!"},
    {"id": "wave", "name": "👋 WAVE", "action": "wave",
     "instruction": "Wave your hand!", "success": "Nice wave!"},
    {"id": "raise_hand", "name": "✋ RAISE HAND", "action": "raise_hand",
     "instruction": "Raise your hand up!", "success": "Hand raised!"},
    {"id": "touch_nose", "name": "👆 TOUCH NOSE", "action": "touch_nose",
     "instruction": "Touch your nose!", "success": "You touched your nose!"},
    {"id": "arms_out", "name": "🤸 ARMS OUT", "action": "arms_out",
     "instruction": "Spread your arms wide!", "success": "Arms wide open!"},
]

def generate_motor_task():
    """Generate random motor task"""
    return random.choice(MOTOR_ACTIONS).copy()

SPEECH_WORDS = ["apple", "ball", "cat", "dog", "fish", "bird", "sun", "moon", "star", "flower"]

def generate_speech_task():
    """Generate random speech task"""
    word = random.choice(SPEECH_WORDS)
    return {
        "id": f"speech_{word}",
        "name": f"🗣️ Say '{word}'",
        "domain": "Speech",
        "type": "speech",
        "target": word,
        "tokens": 4,
        "instruction": f"Say the word: {word}!",
        "success": f"Great! You said {word} correctly!"
    }

# Infinite task pool
TASK_TYPES = ["counting", "counting", "motor", "speech", "counting", "motor"]

def generate_infinite_task():
    """Generate a random infinite task"""
    task_type = random.choice(TASK_TYPES)
    if task_type == "counting":
        return generate_counting_task()
    elif task_type == "motor":
        return generate_motor_task()
    else:
        return generate_speech_task()

# ============================================================
# VOICE ENGINE
# ============================================================
class VoiceEngine:
    def __init__(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 130)
        print("✅ Voice ready")
    
    def say(self, text):
        print(f"\n🔊 Pepper: {text}")
        self.engine.say(text)
        self.engine.runAndWait()

voice = VoiceEngine()

# ============================================================
# SPEECH RECOGNITION
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
            print("✅ Speech recognition ready")
        except:
            print("⚠️ Microphone not available")
    
    def listen(self):
        if not self.microphone:
            return ""
        try:
            with self.microphone as src:
                audio = self.recognizer.listen(src, timeout=3, phrase_time_limit=3)
                text = self.recognizer.recognize_google(audio)
                return text.lower()
        except:
            return ""

# ============================================================
# BODY DETECTION THREAD (Camera with skeleton)
# ============================================================
class BodyDetectionThread(QThread):
    frame_signal = pyqtSignal(np.ndarray)  # Send frame to main window
    action_signal = pyqtSignal(str)        # Send detected action
    finger_signal = pyqtSignal(int)        # Send finger count
    
    def __init__(self):
        super().__init__()
        self.running = True
        self.cap = None
        self.pose = None
        self.hands = None
        self.current_action = None
        self.last_wrist_y = 0
        
        # Open camera
        for idx in [1, 0, 2]:
            cap = cv2.VideoCapture(idx)
            if cap.isOpened():
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                self.cap = cap
                print(f"✅ Camera {idx} working")
                break
            cap.release()
        
        # Initialize MediaPipe
        try:
            self.pose = mp.solutions.pose.Pose(
                static_image_mode=False,
                model_complexity=1,
                smooth_landmarks=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
            self.hands = mp.solutions.hands.Hands(
                max_num_hands=2,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
            print("✅ Body & Hand detection ready")
        except Exception as e:
            print(f"⚠️ MediaPipe error: {e}")
    
    def count_fingers(self, hand_landmarks, handedness):
        """Count fingers for one hand (0-5)"""
        try:
            lm = hand_landmarks.landmark
            fingers = []
            
            # Thumb
            if handedness == "Right":
                fingers.append(1 if lm[4].x < lm[3].x else 0)
            else:
                fingers.append(1 if lm[4].x > lm[3].x else 0)
            
            # Other 4 fingers
            tips = [8, 12, 16, 20]
            dips = [6, 10, 14, 18]
            for tip, dip in zip(tips, dips):
                fingers.append(1 if lm[tip].y < lm[dip].y else 0)
            
            return sum(fingers)
        except:
            return 0
    
    def detect_action(self, landmarks):
        """Detect body action from pose landmarks"""
        if not landmarks:
            return None
        
        # Get important landmarks
        nose = landmarks[mp.solutions.pose.PoseLandmark.NOSE]
        left_shoulder = landmarks[mp.solutions.pose.PoseLandmark.LEFT_SHOULDER]
        right_shoulder = landmarks[mp.solutions.pose.PoseLandmark.RIGHT_SHOULDER]
        left_elbow = landmarks[mp.solutions.pose.PoseLandmark.LEFT_ELBOW]
        right_elbow = landmarks[mp.solutions.pose.PoseLandmark.RIGHT_ELBOW]
        left_wrist = landmarks[mp.solutions.pose.PoseLandmark.LEFT_WRIST]
        right_wrist = landmarks[mp.solutions.pose.PoseLandmark.RIGHT_WRIST]
        
        # Detect clapping (hands close together)
        hand_distance = abs(left_wrist.x - right_wrist.x) + abs(left_wrist.y - right_wrist.y)
        if hand_distance < 0.12:
            return "clap"
        
        # Detect waving (hand moving side to side)
        left_raised = left_wrist.y < left_shoulder.y - 0.1
        right_raised = right_wrist.y < right_shoulder.y - 0.1
        if left_raised or right_raised:
            wrist_y = left_wrist.y if left_raised else right_wrist.y
            if abs(wrist_y - self.last_wrist_y) > 0.03:
                self.last_wrist_y = wrist_y
                return "wave"
        
        # Detect raised hand
        if left_raised or right_raised:
            return "raise_hand"
        
        # Detect touching nose
        left_to_nose = abs(left_wrist.x - nose.x) + abs(left_wrist.y - nose.y)
        right_to_nose = abs(right_wrist.x - nose.x) + abs(right_wrist.y - nose.y)
        if left_to_nose < 0.12 or right_to_nose < 0.12:
            return "touch_nose"
        
        # Detect arms out
        left_arm_out = abs(left_elbow.x - left_shoulder.x) > 0.2
        right_arm_out = abs(right_elbow.x - right_shoulder.x) > 0.2
        if left_arm_out and right_arm_out:
            return "arms_out"
        
        return None
    
    def draw_skeleton(self, frame, landmarks):
        """Draw body skeleton on frame"""
        h, w = frame.shape[:2]
        
        # Connections for skeleton
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
        
        # Draw lines
        for connection in connections:
            start = landmarks[connection[0]]
            end = landmarks[connection[1]]
            start_point = (int(start.x * w), int(start.y * h))
            end_point = (int(end.x * w), int(end.y * h))
            cv2.line(frame, start_point, end_point, (0, 255, 0), 3)
        
        # Draw joints
        for landmark in landmarks:
            x = int(landmark.x * w)
            y = int(landmark.y * h)
            cv2.circle(frame, (x, y), 5, (0, 0, 255), -1)
        
        return frame
    
    def run(self):
        if not self.cap:
            print("⚠️ No camera - simulation mode")
            while self.running:
                # Create simulated frame
                frame = np.zeros((480, 640, 3), dtype=np.uint8)
                frame[:] = (20, 15, 35)
                cv2.putText(frame, "Camera Not Found", (200, 240), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (100, 150, 255), 2)
                cv2.putText(frame, "Using Simulation Mode", (180, 280), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (150, 150, 150), 1)
                self.frame_signal.emit(frame)
                self.msleep(33)
            return
        
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                self.msleep(10)
                continue
            
            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Process pose for body detection
            detected_action = None
            total_fingers = 0
            
            if self.pose:
                pose_results = self.pose.process(rgb)
                if pose_results.pose_landmarks:
                    frame = self.draw_skeleton(frame, pose_results.pose_landmarks.landmark)
                    detected_action = self.detect_action(pose_results.pose_landmarks.landmark)
                    
                    # Display detected action
                    if detected_action:
                        cv2.putText(frame, f"Action: {detected_action}", (10, 50),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Process hands for finger counting
            if self.hands:
                hands_results = self.hands.process(rgb)
                if hands_results.multi_hand_landmarks:
                    for hand, handedness in zip(hands_results.multi_hand_landmarks, hands_results.multi_handedness):
                        label = handedness.classification[0].label
                        fingers = self.count_fingers(hand, label)
                        total_fingers += fingers
                        
                        # Draw hand landmarks
                        mp.solutions.drawing_utils.draw_landmarks(
                            frame, hand, mp.solutions.hands.HAND_CONNECTIONS,
                            mp.solutions.drawing_utils.DrawingSpec(color=(255, 100, 0), thickness=2),
                            mp.solutions.drawing_utils.DrawingSpec(color=(0, 255, 255), thickness=1))
                    
                    cv2.putText(frame, f"Fingers: {total_fingers}", (10, 90),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            
            # Send data
            self.frame_signal.emit(frame)
            if detected_action:
                self.action_signal.emit(detected_action)
            self.finger_signal.emit(total_fingers)
            
            self.msleep(33)
        
        cv2.destroyAllWindows()
    
    def stop(self):
        self.running = False
        if self.cap:
            self.cap.release()
        self.quit()
        self.wait()

# ============================================================
# BALLOON WIDGET
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
        parent = self.parent()
        if parent:
            self.setGeometry(parent.rect())
        
        self.balloons = []
        colors = ["#ef4444", "#3b82f6", "#22c55e", "#fbbf24", "#a855f7", "#ec4899", "#f97316"]
        
        for _ in range(20):
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
            color = QColor(b["color"])
            color.setAlpha(200)
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(int(b["x"] - b["r"]), int(b["y"] - b["r"]), b["r"] * 2, b["r"] * 2)
            
            painter.setPen(QPen(QColor(b["color"]).darker(140), 2))
            painter.drawLine(int(b["x"]), int(b["y"] + b["r"]), 
                           int(b["x"] + random.randint(-8, 8)), int(b["y"] + b["r"] + 20))
            
            painter.setFont(QFont("Arial", b["r"] // 2))
            painter.drawText(int(b["x"] - b["r"] // 2), int(b["y"] + b["r"] // 3), b["emoji"])
        
        painter.end()
    
    def stop(self):
        self.timer.stop()
        self.hide()
        self.balloons = []

# ============================================================
# COUNTING CARD
# ============================================================
class CountingCard(QPushButton):
    def __init__(self, fruit, count, idx):
        super().__init__()
        self.count = count
        self.idx = idx
        
        text = fruit * count
        self.setText(f"{text}\n{count}")
        self.setFont(QFont("Arial", 22))
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

# ============================================================
# MOTOR CARD
# ============================================================
class MotorCard(QPushButton):
    def __init__(self, text, action):
        super().__init__()
        self.action = action
        self.setText(text)
        self.setFont(QFont("Arial", 22))
        self.setFixedSize(220, 160)
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
# SPEECH CARD
# ============================================================
class SpeechCard(QWidget):
    def __init__(self, word, parent=None):
        super().__init__(parent)
        self.word = word
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        word_label = QLabel(f"🗣️ {self.word.upper()} 🗣️")
        word_label.setFont(QFont("Arial", 32, QFont.Weight.Bold))
        word_label.setStyleSheet("color: #fbbf24;")
        word_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(word_label)
        
        self.record_btn = QPushButton("🎤 PRESS & SPEAK 🎤")
        self.record_btn.setFixedSize(280, 60)
        self.record_btn.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.record_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #dc2626,stop:1 #ef4444);
                color: white;
                border-radius: 30px;
                border: 2px solid #fca5a5;
            }
            QPushButton:pressed { background: #991b1b; }
        """)
        layout.addWidget(self.record_btn)

# ============================================================
# MAIN WINDOW
# ============================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Pepper Clinical Infinity - {CHILD_NAME}")
        self.setMinimumSize(1400, 850)
        
        self.current_task = None
        self.locked = False
        self.score = 0
        self.consecutive = 0
        self.mastered = 0
        self.buttons = []
        self.finger_count = 0
        self.speech_recognizer = SpeechRecognizer()
        self.speech_card = None
        
        self.setup_ui()
        self.setup_camera()
        self.start_session()
    
    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        central.setStyleSheet("background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #0a0a1a,stop:1 #0f0f2a);")
        
        main_layout = QHBoxLayout(central)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 15, 20, 15)
        
        # ========== LEFT PANEL - Camera with Skeleton ==========
        left_panel = QFrame()
        left_panel.setFixedWidth(550)
        left_panel.setStyleSheet("background: #0c0f1e; border-radius: 20px; border: 2px solid #1a1f40;")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        
        # Camera title
        cam_title = QLabel("📷 LIVE BODY DETECTION")
        cam_title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        cam_title.setStyleSheet("color: #a78bfa;")
        cam_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(cam_title)
        
        # Camera feed
        self.camera_label = QLabel()
        self.camera_label.setFixedSize(530, 400)
        self.camera_label.setStyleSheet("background: #000; border-radius: 10px;")
        self.camera_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.camera_label.setText("Starting camera...")
        left_layout.addWidget(self.camera_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Detection info
        info_frame = QFrame()
        info_frame.setStyleSheet("background: #1e1b4b; border-radius: 15px;")
        info_layout = QVBoxLayout(info_frame)
        
        self.finger_label = QLabel("✋ Fingers: 0")
        self.finger_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.finger_label.setStyleSheet("color: #fbbf24;")
        self.finger_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_layout.addWidget(self.finger_label)
        
        self.action_label = QLabel("🎯 Waiting for action...")
        self.action_label.setFont(QFont("Arial", 12))
        self.action_label.setStyleSheet("color: #60a5fa;")
        self.action_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_layout.addWidget(self.action_label)
        
        left_layout.addWidget(info_frame)
        left_layout.addStretch()
        main_layout.addWidget(left_panel)
        
        # ========== RIGHT PANEL - Game Interface ==========
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(15)
        
        # Header with Pepper
        header = QFrame()
        header.setStyleSheet("background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #1a0a3d,stop:1 #0a0f28); border-radius: 20px; border: 2px solid #4f46e5;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 10, 20, 10)
        
        pepper_icon = QLabel("🤖")
        pepper_icon.setFont(QFont("Arial", 40))
        header_layout.addWidget(pepper_icon)
        
        title_box = QVBoxLayout()
        title = QLabel("PEPPER CLINICAL INFINITY")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #a78bfa;")
        title_box.addWidget(title)
        
        child = QLabel(f"Child: {CHILD_NAME}")
        child.setFont(QFont("Arial", 11))
        child.setStyleSheet("color: #60a5fa;")
        title_box.addWidget(child)
        header_layout.addLayout(title_box, 1)
        
        self.stars_label = QLabel("☆☆☆")
        self.stars_label.setFont(QFont("Arial", 24))
        self.stars_label.setStyleSheet("color: #fbbf24; background: #1e1b4b; padding: 5px 20px; border-radius: 15px;")
        header_layout.addWidget(self.stars_label)
        
        right_layout.addWidget(header)
        
        # Instruction
        instr_frame = QFrame()
        instr_frame.setStyleSheet("background: #1e1b4b; border-radius: 15px; border: 2px solid #4f46e5;")
        instr_layout = QVBoxLayout(instr_frame)
        instr_layout.setContentsMargins(20, 20, 20, 20)
        
        self.instruction = QLabel("Getting ready...")
        self.instruction.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        self.instruction.setStyleSheet("color: #e0e6ff;")
        self.instruction.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.instruction.setWordWrap(True)
        instr_layout.addWidget(self.instruction)
        
        right_layout.addWidget(instr_frame)
        
        # Content area (task display)
        self.content_frame = QFrame()
        self.content_frame.setStyleSheet("background: #0c0f1e; border-radius: 20px; border: 2px solid #1a1f40;")
        self.content_layout = QVBoxLayout(self.content_frame)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(self.content_frame, 1)
        
        # Feedback
        feedback_frame = QFrame()
        feedback_frame.setStyleSheet("background: #0c0f1e; border-radius: 15px;")
        feedback_layout = QHBoxLayout(feedback_frame)
        feedback_layout.setContentsMargins(20, 10, 20, 10)
        
        self.feedback_icon = QLabel("💤")
        self.feedback_icon.setFont(QFont("Arial", 24))
        feedback_layout.addWidget(self.feedback_icon)
        
        self.feedback = QLabel("Pepper is getting ready...")
        self.feedback.setFont(QFont("Arial", 14))
        self.feedback.setStyleSheet("color: #9ca3af;")
        feedback_layout.addWidget(self.feedback, 1)
        
        right_layout.addWidget(feedback_frame)
        
        # Progress bar
        self.progress = QProgressBar()
        self.progress.setFixedHeight(10)
        self.progress.setStyleSheet("""
            QProgressBar { background: #1e1b4b; border-radius: 5px; }
            QProgressBar::chunk { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #4f46e5,stop:1 #a78bfa); border-radius: 5px; }
        """)
        right_layout.addWidget(self.progress)
        
        # Stats bar
        stats_bar = QFrame()
        stats_bar.setStyleSheet("background: #07090f; border-radius: 15px;")
        stats_layout = QHBoxLayout(stats_bar)
        stats_layout.setContentsMargins(20, 10, 20, 10)
        
        self.score_label = QLabel(f"🏆 Score: {self.score}")
        self.score_label.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        self.score_label.setStyleSheet("color: #fbbf24;")
        stats_layout.addWidget(self.score_label)
        
        self.mastered_label = QLabel(f"⭐ Mastered: {self.mastered}")
        self.mastered_label.setFont(QFont("Arial", 12))
        self.mastered_label.setStyleSheet("color: #34d399;")
        stats_layout.addWidget(self.mastered_label)
        
        right_layout.addWidget(stats_bar)
        
        main_layout.addWidget(right_panel, 1)
        
        # Balloons
        self.balloons = BalloonWidget(central)
    
    def setup_camera(self):
        self.camera_thread = BodyDetectionThread()
        self.camera_thread.frame_signal.connect(self.update_camera)
        self.camera_thread.action_signal.connect(self.on_body_action)
        self.camera_thread.finger_signal.connect(self.update_fingers)
        self.camera_thread.start()
    
    def update_camera(self, frame):
        # Convert OpenCV frame to QPixmap
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_image)
        scaled_pixmap = pixmap.scaled(530, 400, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.camera_label.setPixmap(scaled_pixmap)
    
    def update_fingers(self, count):
        self.finger_count = count
        self.finger_label.setText(f"✋ Fingers: {count}")
        if count > 0:
            self.finger_label.setStyleSheet("color: #fbbf24; background: #1e1b4b; border-radius: 15px; padding: 8px; border: 2px solid #fbbf24;")
        else:
            self.finger_label.setStyleSheet("color: #fbbf24; background: #1e1b4b; border-radius: 15px; padding: 8px;")
    
    def on_body_action(self, action):
        if action:
            self.action_label.setText(f"🎯 Detected: {action}")
            self.action_label.setStyleSheet("color: #34d399; background: #1e1b4b; border-radius: 15px; padding: 8px;")
            QTimer.singleShot(1500, lambda: self.action_label.setText("🎯 Waiting for action..."))
            QTimer.singleShot(1500, lambda: self.action_label.setStyleSheet("color: #60a5fa; background: #1e1b4b; border-radius: 15px; padding: 8px;"))
            
            # Check if action matches current motor task
            if self.current_task and self.current_task.get("type") == "motor" and not self.locked:
                target_action = self.current_task.get("action")
                if action == target_action:
                    self.task_success()
    
    def start_session(self):
        QTimer.singleShot(500, self.greet)
    
    def greet(self):
        voice.say(f"Hello {CHILD_NAME}! I am Pepper. Let's play and learn together!")
        QTimer.singleShot(3000, self.next_task)
    
    def next_task(self):
        # Generate infinite task
        self.current_task = generate_infinite_task()
        
        # Update UI
        self.instruction.setText(self.current_task["instruction"])
        self.feedback.setText("Your turn!")
        self.feedback.setStyleSheet("color: #60a5fa;")
        self.feedback_icon.setText("🎯")
        
        # Clear previous buttons
        self.clear_buttons()
        
        # Display task based on type
        if self.current_task["type"] == "counting":
            self.show_counting_task()
        elif self.current_task["type"] == "motor":
            self.show_motor_task()
        else:
            self.show_speech_task()
        
        # Start timeout timer (20 seconds)
        if hasattr(self, 'task_timer'):
            self.task_timer.stop()
        self.task_timer = QTimer()
        self.task_timer.setSingleShot(True)
        self.task_timer.timeout.connect(self.task_timeout)
        self.task_timer.start(20000)
        
        # Progress bar animation
        self.progress.setValue(0)
        self.progress_anim = QPropertyAnimation(self.progress, b"value")
        self.progress_anim.setDuration(20000)
        self.progress_anim.setStartValue(0)
        self.progress_anim.setEndValue(100)
        self.progress_anim.start()
        
        # Unlock
        self.locked = False
        
        # Announce
        voice.say(self.current_task["instruction"])
    
    def show_counting_task(self):
        """Show counting task with fruit cards"""
        task = self.current_task
        fruit = task["fruit"]
        options = task["options"]
        
        grid = QWidget()
        grid_layout = QGridLayout(grid)
        grid_layout.setSpacing(20)
        grid_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        for i, count in enumerate(options):
            btn = CountingCard(fruit, count, i)
            btn.clicked.connect(lambda checked, idx=i: self.check_counting_answer(idx))
            self.buttons.append(btn)
            grid_layout.addWidget(btn, i//2, i%2)
        
        self.content_layout.addWidget(grid)
    
    def show_motor_task(self):
        """Show motor task with action button"""
        task = self.current_task
        
        motor_frame = QFrame()
        motor_frame.setStyleSheet("background: #1e1b4b; border-radius: 20px; border: 3px solid #a78bfa;")
        motor_layout = QVBoxLayout(motor_frame)
        motor_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Action display
        action_label = QLabel(task["name"])
        action_label.setFont(QFont("Arial", 32, QFont.Weight.Bold))
        action_label.setStyleSheet("color: #a78bfa;")
        action_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        motor_layout.addWidget(action_label)
        
        # Instruction
        arrow_label = QLabel("👇 COPY THIS MOVEMENT! 👇")
        arrow_label.setFont(QFont("Arial", 20))
        arrow_label.setStyleSheet("color: #34d399;")
        arrow_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        motor_layout.addWidget(arrow_label)
        
        # Camera reminder
        cam_label = QLabel("📷 Camera is watching you! 📷")
        cam_label.setFont(QFont("Arial", 14))
        cam_label.setStyleSheet("color: #fbbf24;")
        cam_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        motor_layout.addWidget(cam_label)
        
        self.content_layout.addWidget(motor_frame)
        self.feedback.setText(f"Perform {task['name']} - camera is tracking you!")
    
    def show_speech_task(self):
        """Show speech task with record button"""
        task = self.current_task
        word = task["target"]
        
        self.speech_card = SpeechCard(word)
        self.speech_card.record_btn.pressed.connect(self.start_recording)
        self.speech_card.record_btn.released.connect(self.stop_recording)
        self.content_layout.addWidget(self.speech_card)
    
    def start_recording(self):
        self.feedback.setText("🎤 Recording... Speak now!")
        self.feedback_icon.setText("🔴")
        self.speech_card.record_btn.setText("🔴 RELEASE TO STOP")
    
    def stop_recording(self):
        self.feedback.setText("⏳ Processing speech...")
        threading.Thread(target=self.process_speech, daemon=True).start()
    
    def process_speech(self):
        text = self.speech_recognizer.listen()
        if self.speech_card:
            QTimer.invokeMethod(self.speech_card.record_btn, "setText", 
                              Qt.ConnectionType.QueuedConnection, 
                              Q_ARG(str, "🎤 PRESS & SPEAK 🎤"))
        if text and self.current_task and self.current_task.get("type") == "speech" and not self.locked:
            target_word = self.current_task["target"]
            if target_word in text:
                QTimer.invokeMethod(self, "task_success", Qt.ConnectionType.QueuedConnection)
            else:
                QTimer.invokeMethod(self, "task_fail", Qt.ConnectionType.QueuedConnection)
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
        
        # Stop timers
        if hasattr(self, 'task_timer'):
            self.task_timer.stop()
        if hasattr(self, 'progress_anim'):
            self.progress_anim.stop()
        
        # Calculate points
        points = self.current_task.get("tokens", 2) * 5
        self.score += points
        self.consecutive += 1
        
        # Update UI
        self.feedback.setText(f"✅ CORRECT! +{points} points!")
        self.feedback.setStyleSheet("color: #34d399;")
        self.feedback_icon.setText("✅")
        self.score_label.setText(f"🏆 Score: {self.score}")
        
        # Update stars
        stars = "⭐" * self.consecutive + "☆" * (3 - self.consecutive)
        self.stars_label.setText(stars)
        
        # Launch balloons
        self.balloons.launch()
        
        # Log to CSV
        with open(CSV_FILE, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().strftime("%H:%M:%S"),
                CHILD_NAME,
                self.current_task["name"],
                self.current_task["type"],
                "SUCCESS",
                points,
                self.consecutive
            ])
        
        # Check mastery
        if self.consecutive >= 3:
            self.consecutive = 0
            self.mastered += 1
            self.mastered_label.setText(f"⭐ Mastered: {self.mastered}")
            voice.say(f"AMAZING {CHILD_NAME}! You mastered {self.current_task['name']}! +{points} points!")
            self.feedback.setText(f"🏆 MASTERED! +{points} points! 🏆")
        else:
            voice.say(self.current_task.get("success", "Great job!"))
        
        # Next task
        QTimer.singleShot(2500, self.next_task)
    
    def task_fail(self):
        if self.locked:
            return
        
        self.locked = True
        self.consecutive = 0
        
        # Update UI
        self.feedback.setText(f"❌ Try again! Correct answer: {self.current_task.get('target', '?')}")
        self.feedback.setStyleSheet("color: #f87171;")
        self.feedback_icon.setText("❌")
        self.stars_label.setText("☆☆☆")
        
        # Log to CSV
        with open(CSV_FILE, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().strftime("%H:%M:%S"),
                CHILD_NAME,
                self.current_task["name"],
                self.current_task["type"],
                "FAIL",
                0,
                0
            ])
        
        voice.say("That's okay! Let's try the next task!")
        QTimer.singleShot(2500, self.next_task)
    
    def task_timeout(self):
        if self.locked:
            return
        
        self.locked = True
        self.consecutive = 0
        
        self.feedback.setText(f"⏰ Time's up! Answer: {self.current_task.get('target', '?')}")
        self.feedback.setStyleSheet("color: #f59e0b;")
        self.feedback_icon.setText("⏰")
        self.stars_label.setText("☆☆☆")
        
        # Log to CSV
        with open(CSV_FILE, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().strftime("%H:%M:%S"),
                CHILD_NAME,
                self.current_task["name"],
                self.current_task["type"],
                "TIMEOUT",
                0,
                0
            ])
        
        voice.say("Time's up! Let's try the next task!")
        QTimer.singleShot(2500, self.next_task)
    
    def clear_buttons(self):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.buttons.clear()
    
    def closeEvent(self, event):
        if hasattr(self, 'camera_thread'):
            self.camera_thread.stop()
        
        duration = int((time.time() - getattr(self, 'start_time', time.time())) / 60)
        print(f"\n{'='*64}")
        print(f"🎉 SESSION COMPLETE — {CHILD_NAME}")
        print(f"{'='*64}")
        print(f"Final Score: {self.score}")
        print(f"Tasks Mastered: {self.mastered}")
        print(f"CSV Log: {CSV_FILE}")
        print('='*64)
        event.accept()

# ============================================================
# MAIN
# ============================================================
def main():
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║  PEPPER CLINICAL INFINITY — COMPLETE                         ║
╠══════════════════════════════════════════════════════════════╣
║  ✓ Counting tasks (fruits: 2-5 items)                      ║
║  ✓ Full body detection with skeleton on main window        ║
║  ✓ 10-finger detection                                     ║
║  ✓ Motor actions (clap, wave, raise hand, touch nose)      ║
║  ✓ Speech tasks with voice recording                       ║
║  ✓ Balloons celebration on correct answers                 ║
║  ✓ Infinite task generation                                ║
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
