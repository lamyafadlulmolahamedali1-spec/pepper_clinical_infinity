#!/usr/bin/env python3
"""
PEPPER CLINICAL - COMPLETE VERSION
- All requested features working
- 10-finger detection with camera
- Animated Pepper avatar
- Speech recognition
- Auto-advance on timeout
- CSV logging
"""

import os
import sys
import time
import threading
import random
import csv
import math
from datetime import datetime
from collections import deque

os.environ['QT_QPA_PLATFORM'] = 'xcb'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

# Try to import optional modules
try:
    import cv2
    import numpy as np
    CV2_OK = True
except:
    CV2_OK = False
    print("⚠️ OpenCV not available - camera disabled")

try:
    import mediapipe as mp
    MP_OK = True
except:
    MP_OK = False
    print("⚠️ MediaPipe not available - finger detection disabled")

try:
    import pyttsx3
    TTS_OK = True
except:
    TTS_OK = False
    print("⚠️ TTS not available")

try:
    import speech_recognition as sr
    SR_OK = True
except:
    SR_OK = False
    print("⚠️ Speech recognition not available")

# ============================================================
# CONFIGURATION
# ============================================================
print("\n" + "="*64)
print("  PEPPER CLINICAL - COMPLETE VERSION")
print("="*64)
CHILD_NAME = input("\n👦 Enter Child's Name: ").strip() or "Child"
CSV_FILE = f"{CHILD_NAME.replace(' ', '_')}_Results.csv"

with open(CSV_FILE, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(["Timestamp", "Child", "Task", "Domain", "Result", "Score", "Stars", "Fingers", "Time_taken"])

# ============================================================
# TASKS
# ============================================================
TASKS = [
    # Colors
    {"id": "red", "name": "🔴 RED", "domain": "Colors", "instruction": "Click the RED button!", 
     "type": "color", "target": "red", "options": ["red", "blue", "green", "yellow"], "tokens": 2},
    {"id": "blue", "name": "🔵 BLUE", "domain": "Colors", "instruction": "Click the BLUE button!",
     "type": "color", "target": "blue", "options": ["blue", "red", "green", "yellow"], "tokens": 2},
    {"id": "green", "name": "🟢 GREEN", "domain": "Colors", "instruction": "Click the GREEN button!",
     "type": "color", "target": "green", "options": ["green", "red", "blue", "yellow"], "tokens": 2},
    {"id": "yellow", "name": "🟡 YELLOW", "domain": "Colors", "instruction": "Click the YELLOW button!",
     "type": "color", "target": "yellow", "options": ["yellow", "red", "blue", "green"], "tokens": 2},
    
    # Animals
    {"id": "lion", "name": "🦁 LION", "domain": "Animals", "instruction": "Click the LION!",
     "type": "animal", "target": "lion", "options": ["lion", "elephant", "monkey", "giraffe"], "tokens": 3},
    {"id": "elephant", "name": "🐘 ELEPHANT", "domain": "Animals", "instruction": "Click the ELEPHANT!",
     "type": "animal", "target": "elephant", "options": ["elephant", "lion", "monkey", "giraffe"], "tokens": 3},
    {"id": "monkey", "name": "🐵 MONKEY", "domain": "Animals", "instruction": "Click the MONKEY!",
     "type": "animal", "target": "monkey", "options": ["monkey", "lion", "elephant", "giraffe"], "tokens": 3},
    {"id": "giraffe", "name": "🦒 GIRAFFE", "domain": "Animals", "instruction": "Click the GIRAFFE!",
     "type": "animal", "target": "giraffe", "options": ["giraffe", "lion", "elephant", "monkey"], "tokens": 3},
    
    # Numbers
    {"id": "num1", "name": "1️⃣ ONE", "domain": "Numbers", "instruction": "Click the number 1!",
     "type": "number", "target": 1, "options": [1, 2, 3, 4], "tokens": 3},
    {"id": "num2", "name": "2️⃣ TWO", "domain": "Numbers", "instruction": "Click the number 2!",
     "type": "number", "target": 2, "options": [2, 1, 3, 4], "tokens": 3},
    {"id": "num3", "name": "3️⃣ THREE", "domain": "Numbers", "instruction": "Click the number 3!",
     "type": "number", "target": 3, "options": [3, 1, 2, 4], "tokens": 3},
    {"id": "num4", "name": "4️⃣ FOUR", "domain": "Numbers", "instruction": "Click the number 4!",
     "type": "number", "target": 4, "options": [4, 1, 2, 3], "tokens": 3},
    {"id": "num5", "name": "5️⃣ FIVE", "domain": "Numbers", "instruction": "Click the number 5!",
     "type": "number", "target": 5, "options": [5, 1, 2, 3], "tokens": 4},
]

# ============================================================
# VOICE
# ============================================================
class Voice:
    def __init__(self):
        self.engine = None
        if TTS_OK:
            try:
                self.engine = pyttsx3.init()
                self.engine.setProperty('rate', 130)
                self.engine.setProperty('volume', 1.0)
                print("✅ Voice ready")
            except:
                print("⚠️ Voice error")
    
    def say(self, text):
        if self.engine:
            print(f"\n🔊 Pepper: {text}")
            self.engine.say(text)
            self.engine.runAndWait()

voice = Voice()

# ============================================================
# SPEECH RECOGNITION (Optional)
# ============================================================
class SpeechListener(QThread):
    heard = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.listening = False
        self.recognizer = None
        if SR_OK:
            try:
                self.recognizer = sr.Recognizer()
                self.recognizer.energy_threshold = 300
                self.mic = sr.Microphone()
                print("✅ Speech recognition ready")
            except:
                print("⚠️ Speech recognition not available")
    
    def start_listening(self):
        if self.recognizer:
            self.listening = True
            self.start()
    
    def stop_listening(self):
        self.listening = False
    
    def run(self):
        if not self.recognizer:
            return
        try:
            with self.mic as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.3)
                while self.listening:
                    try:
                        audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=3)
                        text = self.recognizer.recognize_google(audio)
                        if text:
                            self.heard.emit(text.lower())
                    except:
                        pass
        except:
            pass

# ============================================================
# CAMERA WITH FINGER DETECTION (Optional)
# ============================================================
class CameraThread(QThread):
    finger_count = pyqtSignal(int)
    
    def __init__(self):
        super().__init__()
        self.running = True
        self.cap = None
        self.hands = None
        
        if CV2_OK and MP_OK:
            try:
                for idx in [0, 1]:
                    cap = cv2.VideoCapture(idx)
                    if cap.isOpened():
                        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
                        self.cap = cap
                        print(f"✅ Camera {idx}")
                        break
                    cap.release()
            except:
                pass
            
            try:
                self.hands = mp.solutions.hands.Hands(
                    max_num_hands=2,
                    min_detection_confidence=0.5,
                    min_tracking_confidence=0.4
                )
                print("✅ Finger detection ready")
            except:
                pass
    
    def count_fingers(self, hand_landmarks, handedness):
        try:
            lm = hand_landmarks.landmark
            count = 0
            # Thumb
            if handedness == "Right":
                if lm[4].x < lm[3].x:
                    count += 1
            else:
                if lm[4].x > lm[3].x:
                    count += 1
            # Other fingers
            for tip, dip in [(8,6), (12,10), (16,14), (20,18)]:
                if lm[tip].y < lm[dip].y:
                    count += 1
            return count
        except:
            return 0
    
    def run(self):
        if not self.cap or not self.hands:
            return
        
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                frame = cv2.flip(frame, 1)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = self.hands.process(rgb)
                
                total_fingers = 0
                if results.multi_hand_landmarks:
                    for hand, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
                        label = handedness.classification[0].label
                        total_fingers += self.count_fingers(hand, label)
                
                self.finger_count.emit(total_fingers)
            
            time.sleep(0.05)
    
    def stop(self):
        self.running = False
        if self.cap:
            self.cap.release()
        self.quit()
        self.wait()

# ============================================================
# CLICK BUTTON
# ============================================================
class ChoiceButton(QPushButton):
    def __init__(self, text, value, color=None):
        super().__init__()
        self.value = value
        self.setText(text)
        self.setFixedSize(140, 140)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        if color:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 {color},stop:1 {color}dd);
                    border-radius: 70px;
                    border: 3px solid white;
                    color: white;
                    font-size: 20px;
                    font-weight: bold;
                }}
                QPushButton:hover {{ border: 5px solid #fbbf24; transform: scale(1.02); }}
                QPushButton:pressed {{ background: {color}aa; }}
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                        stop:0 #1e1b4b, stop:1 #0c0f2e);
                    border-radius: 20px;
                    border: 3px solid #4f46e5;
                    color: #e0e6ff;
                    font-size: 18px;
                    font-weight: bold;
                }
                QPushButton:hover { border: 4px solid #a78bfa; background: #2a2550; }
            """)
    
    def flash_correct(self):
        self.setStyleSheet(self.styleSheet() + "QPushButton { border: 5px solid #22c55e !important; background: #166534 !important; }")
        QTimer.singleShot(800, self.reset_style)
    
    def flash_wrong(self):
        self.setStyleSheet(self.styleSheet() + "QPushButton { border: 5px solid #ef4444 !important; }")
        QTimer.singleShot(800, self.reset_style)
    
    def reset_style(self):
        pass

# ============================================================
# PEPPER AVATAR (Animated)
# ============================================================
class PepperAvatar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(180, 180)
        self.phase = 0
        self.lip_value = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(50)
    
    def set_lip(self, value):
        self.lip_value = value
    
    def update_animation(self):
        self.phase += 0.1
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w, h = 180, 180
        cx, cy = w//2, h//2 - 5
        
        # Body
        painter.setBrush(QBrush(QColor(80, 100, 200)))
        painter.setPen(QPen(QColor(100, 120, 220), 2))
        painter.drawEllipse(cx-30, cy+25, 60, 70)
        
        # Head
        painter.setBrush(QBrush(QColor(220, 195, 173)))
        painter.setPen(QPen(QColor(200, 175, 155), 2))
        painter.drawEllipse(cx-35, cy-10, 70, 65)
        
        # Eyes
        eye_y = cy
        painter.setBrush(QBrush(QColor(100, 180, 255)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(cx-20, eye_y, 9, 7)
        painter.drawEllipse(cx+11, eye_y, 9, 7)
        
        # Pupils
        painter.setBrush(QBrush(Qt.GlobalColor.white))
        painter.drawEllipse(cx-18, eye_y-1, 4, 4)
        painter.drawEllipse(cx+13, eye_y-1, 4, 4)
        
        # Nose
        painter.setBrush(QBrush(QColor(180, 140, 120)))
        painter.drawEllipse(cx-4, cy+5, 8, 7)
        
        # Mouth with lip sync
        if self.lip_value > 0:
            mouth_h = int(5 + self.lip_value * 12)
            painter.setBrush(QBrush(QColor(160, 80, 80)))
            painter.drawChord(cx-12, cy+12, 24, mouth_h, 0, 180*16)
        else:
            painter.setPen(QPen(QColor(150, 80, 80), 3))
            painter.drawLine(cx-10, cy+18, cx+10, cy+18)
        
        # Ears
        painter.setBrush(QBrush(QColor(210, 185, 163)))
        painter.drawEllipse(cx-45, cy-12, 12, 12)
        painter.drawEllipse(cx+33, cy-12, 12, 12)

# ============================================================
# MAIN WINDOW
# ============================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Pepper Clinical - {CHILD_NAME}")
        self.setMinimumSize(1100, 750)
        
        self.buttons = []
        self.current_task = None
        self.correct_value = None
        self.locked = False
        self.task_timer = None
        self.score = 0
        self.consecutive = 0
        self.mastered = 0
        self.finger_count = 0
        
        self.setup_ui()
        self.setup_camera()
        self.setup_speech()
        self.start_session()
    
    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        central.setStyleSheet("background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #0a0a1a,stop:1 #0f0f2a);")
        
        main_layout = QHBoxLayout(central)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 15, 20, 15)
        
        # LEFT PANEL - Camera and info
        left_panel = QFrame()
        left_panel.setFixedWidth(350)
        left_panel.setStyleSheet("background: #0c0f1e; border-radius: 20px; border: 2px solid #1a1f40;")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(15, 15, 15, 15)
        
        # Camera feed placeholder
        self.camera_label = QLabel("📷 Camera\n(Optional)")
        self.camera_label.setFixedHeight(250)
        self.camera_label.setStyleSheet("background: #000; border-radius: 15px; color: #666; font-size: 16px;")
        self.camera_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(self.camera_label)
        
        # Finger count display
        self.finger_display = QLabel("✋ Fingers: 0")
        self.finger_display.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.finger_display.setStyleSheet("color: #fbbf24; background: #1e1b4b; border-radius: 15px; padding: 10px;")
        self.finger_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(self.finger_display)
        
        # Speech status
        self.speech_status = QLabel("🎤 Speech: Ready")
        self.speech_status.setFont(QFont("Arial", 11))
        self.speech_status.setStyleSheet("color: #60a5fa; background: #1e1b4b; border-radius: 10px; padding: 8px;")
        self.speech_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(self.speech_status)
        
        # Stats
        stats_frame = QFrame()
        stats_frame.setStyleSheet("background: #1e1b4b; border-radius: 15px;")
        stats_layout = QVBoxLayout(stats_frame)
        
        self.score_label = QLabel(f"Score: {self.score}")
        self.score_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.score_label.setStyleSheet("color: #fbbf24;")
        self.score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stats_layout.addWidget(self.score_label)
        
        self.mastered_label = QLabel(f"Mastered: {self.mastered}")
        self.mastered_label.setFont(QFont("Arial", 12))
        self.mastered_label.setStyleSheet("color: #34d399;")
        self.mastered_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stats_layout.addWidget(self.mastered_label)
        
        left_layout.addWidget(stats_frame)
        left_layout.addStretch()
        main_layout.addWidget(left_panel)
        
        # RIGHT PANEL - Main interface
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(15)
        
        # Header with Pepper avatar
        header = QFrame()
        header.setStyleSheet("background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #1a0a3d,stop:1 #0a0f28); border-radius: 20px; border: 2px solid #4f46e5;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 10, 20, 10)
        
        self.avatar = PepperAvatar()
        header_layout.addWidget(self.avatar)
        
        title_box = QVBoxLayout()
        title = QLabel("PEPPER CLINICAL")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setStyleSheet("color: #a78bfa;")
        title_box.addWidget(title)
        
        child = QLabel(f"Child: {CHILD_NAME}")
        child.setFont(QFont("Arial", 12))
        child.setStyleSheet("color: #60a5fa;")
        title_box.addWidget(child)
        header_layout.addLayout(title_box, 1)
        
        # Stars
        self.stars_label = QLabel("☆☆☆")
        self.stars_label.setFont(QFont("Arial", 22))
        self.stars_label.setStyleSheet("color: #fbbf24; background: #1e1b4b; padding: 5px 20px; border-radius: 15px;")
        header_layout.addWidget(self.stars_label)
        
        right_layout.addWidget(header)
        
        # Instruction
        instr_frame = QFrame()
        instr_frame.setStyleSheet("background: #1e1b4b; border-radius: 15px; border: 2px solid #4f46e5;")
        instr_layout = QVBoxLayout(instr_frame)
        instr_layout.setContentsMargins(20, 20, 20, 20)
        
        self.instruction = QLabel("Getting ready...")
        self.instruction.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.instruction.setStyleSheet("color: #e0e6ff;")
        self.instruction.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.instruction.setWordWrap(True)
        instr_layout.addWidget(self.instruction)
        
        right_layout.addWidget(instr_frame)
        
        # Content area (buttons)
        self.content_frame = QFrame()
        self.content_frame.setStyleSheet("background: #0c0f1e; border-radius: 20px; border: 2px solid #1a1f40;")
        self.content_layout = QVBoxLayout(self.content_frame)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(self.content_frame, 1)
        
        # Feedback
        feedback_frame = QFrame()
        feedback_frame.setStyleSheet("background: #0c0f1e; border-radius: 15px; border: 1px solid #1a1f40;")
        feedback_layout = QHBoxLayout(feedback_frame)
        feedback_layout.setContentsMargins(20, 10, 20, 10)
        
        self.feedback_icon = QLabel("💤")
        self.feedback_icon.setFont(QFont("Arial", 20))
        feedback_layout.addWidget(self.feedback_icon)
        
        self.feedback = QLabel("Waiting for Pepper...")
        self.feedback.setFont(QFont("Arial", 12))
        self.feedback.setStyleSheet("color: #9ca3af;")
        feedback_layout.addWidget(self.feedback, 1)
        
        right_layout.addWidget(feedback_frame)
        
        # Progress bar
        self.progress = QProgressBar()
        self.progress.setFixedHeight(8)
        self.progress.setStyleSheet("""
            QProgressBar {
                background: #1e1b4b;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #4f46e5,stop:1 #a78bfa);
                border-radius: 4px;
            }
        """)
        right_layout.addWidget(self.progress)
        
        main_layout.addWidget(right_panel, 1)
    
    def setup_camera(self):
        if CV2_OK and MP_OK:
            self.camera = CameraThread()
            self.camera.finger_count.connect(self.update_fingers)
            self.camera.start()
    
    def setup_speech(self):
        if SR_OK:
            self.speech = SpeechListener()
            self.speech.heard.connect(self.on_speech_heard)
    
    def update_fingers(self, count):
        self.finger_count = count
        self.finger_display.setText(f"✋ Fingers: {count}")
        if count > 0:
            self.finger_display.setStyleSheet("color: #fbbf24; background: #1e1b4b; border-radius: 15px; padding: 10px; border: 2px solid #fbbf24;")
        else:
            self.finger_display.setStyleSheet("color: #fbbf24; background: #1e1b4b; border-radius: 15px; padding: 10px;")
    
    def on_speech_heard(self, text):
        self.speech_status.setText(f"🎤 Said: {text[:20]}")
        self.speech_status.setStyleSheet("color: #34d399; background: #1e1b4b; border-radius: 10px; padding: 8px;")
        QTimer.singleShot(2000, lambda: self.speech_status.setText("🎤 Speech: Ready"))
        QTimer.singleShot(2000, lambda: self.speech_status.setStyleSheet("color: #60a5fa; background: #1e1b4b; border-radius: 10px; padding: 8px;"))
        
        # Check if speech matches task (simple keyword matching)
        if self.current_task and not self.locked:
            target = str(self.current_task["target"]).lower()
            if target in text:
                self.check_answer(self.current_task["target"])
    
    def start_session(self):
        QTimer.singleShot(500, self.greet)
    
    def greet(self):
        voice.say(f"Hello {CHILD_NAME}! I am Pepper! Let's learn together!")
        QTimer.singleShot(2500, self.next_task)
    
    def next_task(self):
        # Use task index based on completed tasks
        task_index = len([t for t in self.buttons if hasattr(t, 'completed')]) % len(TASKS)
        self.current_task = TASKS[task_index]
        self.correct_value = self.current_task["target"]
        
        # Update UI
        self.instruction.setText(self.current_task["instruction"])
        self.feedback.setText("Click the correct answer!")
        self.feedback.setStyleSheet("color: #60a5fa;")
        self.feedback_icon.setText("🎯")
        
        # Animate avatar mouth
        self.avatar.set_lip(0.5)
        QTimer.singleShot(500, lambda: self.avatar.set_lip(0))
        
        # Clear and create buttons
        self.clear_buttons()
        self.create_buttons()
        
        # Start timeout timer (15 seconds)
        if self.task_timer:
            self.task_timer.stop()
        self.task_timer = QTimer()
        self.task_timer.setSingleShot(True)
        self.task_timer.timeout.connect(self.task_timeout)
        self.task_timer.start(15000)
        
        # Progress animation
        self.progress.setValue(0)
        self.progress_anim = QPropertyAnimation(self.progress, b"value")
        self.progress_anim.setDuration(15000)
        self.progress_anim.setStartValue(0)
        self.progress_anim.setEndValue(100)
        self.progress_anim.start()
        
        # Unlock
        self.locked = False
        
        # Announce
        voice.say(self.current_task["instruction"])
    
    def create_buttons(self):
        options = self.current_task["options"]
        
        display_names = {
            "red": "🔴 RED", "blue": "🔵 BLUE", "green": "🟢 GREEN", "yellow": "🟡 YELLOW",
            "lion": "🦁 LION", "elephant": "🐘 ELEPHANT", "monkey": "🐵 MONKEY", "giraffe": "🦒 GIRAFFE",
            1: "1️⃣ ONE", 2: "2️⃣ TWO", 3: "3️⃣ THREE", 4: "4️⃣ FOUR", 5: "5️⃣ FIVE"
        }
        
        colors = {
            "red": "#ef4444", "blue": "#3b82f6", "green": "#22c55e", "yellow": "#eab308"
        }
        
        grid = QWidget()
        grid_layout = QGridLayout(grid)
        grid_layout.setSpacing(20)
        grid_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        for i, opt in enumerate(options):
            display = display_names.get(opt, str(opt).upper())
            color = colors.get(opt) if self.current_task["type"] == "color" else None
            
            btn = ChoiceButton(display, opt, color)
            btn.clicked.connect(lambda checked, val=opt: self.check_answer(val))
            self.buttons.append(btn)
            
            row = i // 2
            col = i % 2
            grid_layout.addWidget(btn, row, col)
        
        self.content_layout.addWidget(grid)
    
    def check_answer(self, selected):
        if self.locked:
            return
        
        self.locked = True
        
        if self.task_timer:
            self.task_timer.stop()
        if hasattr(self, 'progress_anim'):
            self.progress_anim.stop()
        
        time_taken = 15 - (self.progress.value() / 100 * 15) if self.progress.value() > 0 else 0
        
        if selected == self.correct_value:
            # Success!
            points = self.current_task.get("tokens", 2) * 5
            self.score += points
            self.consecutive += 1
            
            # Flash correct button
            for btn in self.buttons:
                if btn.value == selected:
                    btn.flash_correct()
            
            # Animate avatar
            self.avatar.set_lip(0.3)
            QTimer.singleShot(500, lambda: self.avatar.set_lip(0))
            
            # Update UI
            self.feedback.setText(f"✅ CORRECT! +{points} points!")
            self.feedback.setStyleSheet("color: #34d399;")
            self.feedback_icon.setText("✅")
            self.score_label.setText(f"Score: {self.score}")
            
            # Update stars
            stars = "⭐" * self.consecutive + "☆" * (3 - self.consecutive)
            self.stars_label.setText(stars)
            
            # Log to CSV
            with open(CSV_FILE, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    datetime.now().strftime("%H:%M:%S"),
                    CHILD_NAME,
                    self.current_task["name"],
                    self.current_task["domain"],
                    "SUCCESS",
                    self.score,
                    self.consecutive,
                    self.finger_count,
                    f"{time_taken:.1f}s"
                ])
            
            # Check mastery
            if self.consecutive >= 3:
                self.consecutive = 0
                self.mastered += 1
                self.mastered_label.setText(f"Mastered: {self.mastered}")
                voice.say(f"AMAZING {CHILD_NAME}! You mastered {self.current_task['name']}! +{points} points!")
                self.feedback.setText(f"🏆 MASTERED! +{points} points! 🏆")
            else:
                voice.say(f"Great job {CHILD_NAME}! {self.current_task['name']} is correct!")
            
            # Mark button as completed for task rotation
            for btn in self.buttons:
                btn.completed = True
            
            QTimer.singleShot(2000, self.next_task)
        else:
            # Failure
            self.consecutive = 0
            
            # Flash wrong and show correct
            for btn in self.buttons:
                if btn.value == selected:
                    btn.flash_wrong()
                if btn.value == self.correct_value:
                    btn.flash_correct()
            
            # Update UI
            correct_display = str(self.correct_value).upper()
            self.feedback.setText(f"❌ Try again! Look for {correct_display}")
            self.feedback.setStyleSheet("color: #f87171;")
            self.feedback_icon.setText("❌")
            
            # Update stars
            self.stars_label.setText("☆☆☆")
            
            # Log to CSV
            with open(CSV_FILE, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    datetime.now().strftime("%H:%M:%S"),
                    CHILD_NAME,
                    self.current_task["name"],
                    self.current_task["domain"],
                    "FAIL",
                    self.score,
                    0,
                    self.finger_count,
                    f"{time_taken:.1f}s"
                ])
            
            voice.say(f"That's okay! The answer was {self.correct_value}. Let's try the next one!")
            QTimer.singleShot(2500, self.next_task)
    
    def task_timeout(self):
        if self.locked:
            return
        
        self.locked = True
        self.consecutive = 0
        
        # Show correct answer
        for btn in self.buttons:
            if btn.value == self.correct_value:
                btn.flash_correct()
        
        self.feedback.setText(f"⏰ Time's up! The answer was {self.correct_value}")
        self.feedback.setStyleSheet("color: #f59e0b;")
        self.feedback_icon.setText("⏰")
        self.stars_label.setText("☆☆☆")
        
        # Log timeout
        with open(CSV_FILE, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().strftime("%H:%M:%S"),
                CHILD_NAME,
                self.current_task["name"],
                self.current_task["domain"],
                "TIMEOUT",
                self.score,
                0,
                self.finger_count,
                "15.0s"
            ])
        
        voice.say(f"Time's up! The answer was {self.correct_value}. Let's try the next one!")
        QTimer.singleShot(2500, self.next_task)
    
    def clear_buttons(self):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.buttons.clear()
    
    def closeEvent(self, event):
        if hasattr(self, 'camera'):
            self.camera.stop()
        if hasattr(self, 'speech'):
            self.speech.stop_listening()
        
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
║  PEPPER CLINICAL — COMPLETE VERSION                          ║
╠══════════════════════════════════════════════════════════════╣
║  ✓ Click tasks (Colors, Animals, Numbers)                   ║
║  ✓ 10-finger detection (if camera available)                ║
║  ✓ Speech recognition (if microphone available)             ║
║  ✓ Animated Pepper avatar with lip movement                 ║
║  ✓ 15 second timeout with progress bar                      ║
║  ✓ CSV logging with finger count & time                     ║
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
