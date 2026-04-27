#!/usr/bin/env python3
"""
PEPPER CLINICAL - WITH WORKING CAMERA & FINGER DETECTION
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

# Import OpenCV and MediaPipe
import cv2
import numpy as np
import mediapipe as mp
import pyttsx3

print("✅ All libraries loaded")

# ============================================================
# CONFIGURATION
# ============================================================
print("\n" + "="*64)
print("  PEPPER CLINICAL - WITH CAMERA")
print("="*64)
CHILD_NAME = input("\n👦 Enter Child's Name: ").strip() or "Child"
CSV_FILE = f"{CHILD_NAME.replace(' ', '_')}_Results.csv"

with open(CSV_FILE, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(["Timestamp", "Child", "Task", "Result", "Score", "Stars", "Fingers"])

# ============================================================
# TASKS
# ============================================================
TASKS = [
    {"id": "red", "name": "🔴 RED", "instruction": "Click the RED button!", 
     "type": "color", "target": "red", "options": ["red", "blue", "green", "yellow"], "tokens": 2},
    {"id": "blue", "name": "🔵 BLUE", "instruction": "Click the BLUE button!",
     "type": "color", "target": "blue", "options": ["blue", "red", "green", "yellow"], "tokens": 2},
    {"id": "green", "name": "🟢 GREEN", "instruction": "Click the GREEN button!",
     "type": "color", "target": "green", "options": ["green", "red", "blue", "yellow"], "tokens": 2},
    {"id": "lion", "name": "🦁 LION", "instruction": "Click the LION!",
     "type": "animal", "target": "lion", "options": ["lion", "elephant", "monkey", "giraffe"], "tokens": 3},
    {"id": "elephant", "name": "🐘 ELEPHANT", "instruction": "Click the ELEPHANT!",
     "type": "animal", "target": "elephant", "options": ["elephant", "lion", "monkey", "giraffe"], "tokens": 3},
    {"id": "num1", "name": "1️⃣ ONE", "instruction": "Click the number 1!",
     "type": "number", "target": 1, "options": [1, 2, 3, 4], "tokens": 3},
    {"id": "num2", "name": "2️⃣ TWO", "instruction": "Click the number 2!",
     "type": "number", "target": 2, "options": [2, 1, 3, 4], "tokens": 3},
    {"id": "num3", "name": "3️⃣ THREE", "instruction": "Click the number 3!",
     "type": "number", "target": 3, "options": [3, 1, 2, 4], "tokens": 3},
    {"id": "num4", "name": "4️⃣ FOUR", "instruction": "Click the number 4!",
     "type": "number", "target": 4, "options": [4, 1, 2, 3], "tokens": 3},
    {"id": "num5", "name": "5️⃣ FIVE", "instruction": "Click the number 5!",
     "type": "number", "target": 5, "options": [5, 1, 2, 3], "tokens": 4},
]

# ============================================================
# VOICE
# ============================================================
class Voice:
    def __init__(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 130)
        print("✅ Voice ready")
    
    def say(self, text):
        print(f"\n🔊 Pepper: {text}")
        self.engine.say(text)
        self.engine.runAndWait()

voice = Voice()

# ============================================================
# CAMERA THREAD WITH FINGER DETECTION
# ============================================================
class CameraThread(QThread):
    finger_signal = pyqtSignal(int)
    frame_signal = pyqtSignal(np.ndarray)
    
    def __init__(self):
        super().__init__()
        self.running = True
        self.cap = None
        self.hands = None
        
        # Open camera
        for idx in [1, 0, 2]:  # Try index 1 first (often works better)
            cap = cv2.VideoCapture(idx)
            if cap.isOpened():
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                cap.set(cv2.CAP_PROP_FPS, 30)
                self.cap = cap
                print(f"✅ Camera opened at index {idx}")
                break
            cap.release()
        
        if not self.cap:
            print("⚠️ No camera found - using simulation")
            return
        
        # Initialize MediaPipe Hands
        try:
            self.hands = mp.solutions.hands.Hands(
                static_image_mode=False,
                max_num_hands=2,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
            print("✅ MediaPipe Hands initialized")
        except Exception as e:
            print(f"⚠️ MediaPipe error: {e}")
    
    def count_fingers(self, hand_landmarks, handedness):
        """Count fingers for one hand (returns 0-5)"""
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
                if lm[tip].y < lm[dip].y:
                    fingers.append(1)
                else:
                    fingers.append(0)
            
            return sum(fingers)
        except:
            return 0
    
    def run(self):
        if not self.cap:
            # Simulate finger count if no camera
            while self.running:
                self.finger_signal.emit(0)
                self.msleep(100)
            return
        
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                self.msleep(10)
                continue
            
            # Flip horizontally for mirror effect
            frame = cv2.flip(frame, 1)
            
            # Process for hand detection
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands.process(rgb)
            
            total_fingers = 0
            
            # Draw hand landmarks and count fingers
            if results.multi_hand_landmarks:
                for hand_landmarks, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
                    # Get hand label
                    label = handedness.classification[0].label
                    
                    # Count fingers
                    finger_count = self.count_fingers(hand_landmarks, label)
                    total_fingers += finger_count
                    
                    # Draw landmarks
                    mp.solutions.drawing_utils.draw_landmarks(
                        frame, 
                        hand_landmarks, 
                        mp.solutions.hands.HAND_CONNECTIONS,
                        mp.solutions.drawing_utils.DrawingSpec(color=(0, 255, 0), thickness=2),
                        mp.solutions.drawing_utils.DrawingSpec(color=(0, 0, 255), thickness=1)
                    )
                    
                    # Draw finger count on hand
                    h, w = frame.shape[:2]
                    cx = int(hand_landmarks.landmark[0].x * w)
                    cy = int(hand_landmarks.landmark[0].y * h) - 30
                    cv2.putText(frame, f"{finger_count}", (cx, cy), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
            
            # Draw total fingers on frame
            cv2.putText(frame, f"Total Fingers: {total_fingers}", (10, 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
            
            # Emit signals
            self.finger_signal.emit(total_fingers)
            self.frame_signal.emit(frame)
            
            self.msleep(33)  # ~30 FPS
    
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
                QPushButton:hover {{ border: 5px solid #fbbf24; }}
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
        QTimer.singleShot(800, lambda: self.setStyleSheet(self.styleSheet().replace("border: 5px solid #22c55e !important; background: #166534 !important;", "")))
    
    def flash_wrong(self):
        original = self.styleSheet()
        self.setStyleSheet(original + "QPushButton { border: 5px solid #ef4444 !important; }")
        QTimer.singleShot(800, lambda: self.setStyleSheet(original))

# ============================================================
# PEPPER AVATAR
# ============================================================
class PepperAvatar(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(160, 160)
        self.setStyleSheet("background: transparent;")
        self.is_speaking = False
        self.mouth_open = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.animate)
        self.timer.start(100)
        self.update_face()
    
    def animate(self):
        if self.is_speaking:
            self.mouth_open = 15 + int(random.random() * 10)
        else:
            self.mouth_open = max(0, self.mouth_open - 3)
        self.update_face()
    
    def set_speaking(self, speaking):
        self.is_speaking = speaking
    
    def update_face(self):
        # Create a simple drawn face
        pixmap = QPixmap(160, 160)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Head
        painter.setBrush(QBrush(QColor(220, 195, 173)))
        painter.setPen(QPen(QColor(200, 175, 155), 2))
        painter.drawEllipse(20, 20, 120, 115)
        
        # Eyes
        painter.setBrush(QBrush(QColor(100, 180, 255)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(45, 55, 18, 15)
        painter.drawEllipse(97, 55, 18, 15)
        
        # Pupils
        painter.setBrush(QBrush(Qt.GlobalColor.white))
        painter.drawEllipse(49, 58, 8, 8)
        painter.drawEllipse(101, 58, 8, 8)
        
        # Nose
        painter.setBrush(QBrush(QColor(180, 140, 120)))
        painter.drawEllipse(75, 75, 12, 10)
        
        # Mouth
        if self.mouth_open > 5:
            painter.setBrush(QBrush(QColor(160, 80, 80)))
            painter.drawChord(55, 90, 50, self.mouth_open, 0, 180*16)
        else:
            painter.setPen(QPen(QColor(150, 80, 80), 4))
            painter.drawLine(60, 100, 100, 100)
        
        painter.end()
        self.setPixmap(pixmap)

# ============================================================
# MAIN WINDOW
# ============================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Pepper Clinical - {CHILD_NAME}")
        self.setFixedSize(1300, 800)
        
        self.buttons = []
        self.current_task = None
        self.correct_value = None
        self.locked = False
        self.score = 0
        self.consecutive = 0
        self.mastered = 0
        self.finger_count = 0
        self.task_timer = None
        
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
        
        # LEFT PANEL - Camera
        left_panel = QFrame()
        left_panel.setFixedWidth(500)
        left_panel.setStyleSheet("background: #0c0f1e; border-radius: 20px; border: 2px solid #1a1f40;")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        
        # Camera feed
        self.camera_label = QLabel()
        self.camera_label.setFixedSize(480, 360)
        self.camera_label.setStyleSheet("background: #000; border-radius: 10px;")
        self.camera_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.camera_label.setText("Starting camera...")
        left_layout.addWidget(self.camera_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Finger display
        self.finger_label = QLabel("✋ Fingers Detected: 0")
        self.finger_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        self.finger_label.setStyleSheet("color: #fbbf24; background: #1e1b4b; border-radius: 15px; padding: 15px;")
        self.finger_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(self.finger_label)
        
        # Stats
        self.score_label = QLabel(f"🏆 Score: {self.score}")
        self.score_label.setFont(QFont("Arial", 14))
        self.score_label.setStyleSheet("color: #a78bfa; background: #1e1b4b; border-radius: 10px; padding: 10px;")
        self.score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(self.score_label)
        
        self.mastered_label = QLabel(f"⭐ Mastered: {self.mastered}")
        self.mastered_label.setFont(QFont("Arial", 12))
        self.mastered_label.setStyleSheet("color: #34d399; background: #1e1b4b; border-radius: 10px; padding: 8px;")
        self.mastered_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(self.mastered_label)
        
        left_layout.addStretch()
        main_layout.addWidget(left_panel)
        
        # RIGHT PANEL
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(15)
        
        # Header with Pepper
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
        feedback_frame.setStyleSheet("background: #0c0f1e; border-radius: 15px;")
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
            QProgressBar { background: #1e1b4b; border-radius: 4px; }
            QProgressBar::chunk { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #4f46e5,stop:1 #a78bfa); border-radius: 4px; }
        """)
        right_layout.addWidget(self.progress)
        
        main_layout.addWidget(right_panel, 1)
    
    def setup_camera(self):
        self.camera_thread = CameraThread()
        self.camera_thread.finger_signal.connect(self.update_fingers)
        self.camera_thread.frame_signal.connect(self.update_camera)
        self.camera_thread.start()
    
    def update_fingers(self, count):
        self.finger_count = count
        self.finger_label.setText(f"✋ Fingers Detected: {count}")
        if count > 0:
            self.finger_label.setStyleSheet("color: #fbbf24; background: #1e1b4b; border-radius: 15px; padding: 15px; border: 2px solid #fbbf24;")
        else:
            self.finger_label.setStyleSheet("color: #fbbf24; background: #1e1b4b; border-radius: 15px; padding: 15px;")
    
    def update_camera(self, frame):
        # Convert OpenCV frame to QPixmap
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_image)
        scaled_pixmap = pixmap.scaled(480, 360, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.camera_label.setPixmap(scaled_pixmap)
    
    def start_session(self):
        QTimer.singleShot(500, self.greet)
    
    def greet(self):
        voice.say(f"Hello {CHILD_NAME}! I am Pepper! Let's learn together!")
        QTimer.singleShot(2500, self.next_task)
    
    def next_task(self):
        task_index = random.randint(0, len(TASKS) - 1)
        self.current_task = TASKS[task_index]
        self.correct_value = self.current_task["target"]
        
        # Update UI
        self.instruction.setText(self.current_task["instruction"])
        self.feedback.setText("Click the correct answer!")
        self.feedback.setStyleSheet("color: #60a5fa;")
        self.feedback_icon.setText("🎯")
        
        # Animate avatar
        self.avatar.set_speaking(True)
        QTimer.singleShot(500, lambda: self.avatar.set_speaking(False))
        
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
        
        colors = {"red": "#ef4444", "blue": "#3b82f6", "green": "#22c55e", "yellow": "#eab308"}
        
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
        self.avatar.set_speaking(True)
        
        if self.task_timer:
            self.task_timer.stop()
        if hasattr(self, 'progress_anim'):
            self.progress_anim.stop()
        
        if selected == self.correct_value:
            # Success
            points = self.current_task.get("tokens", 2) * 5
            self.score += points
            self.consecutive += 1
            
            for btn in self.buttons:
                if btn.value == selected:
                    btn.flash_correct()
            
            self.feedback.setText(f"✅ CORRECT! +{points} points!")
            self.feedback.setStyleSheet("color: #34d399;")
            self.feedback_icon.setText("✅")
            self.score_label.setText(f"🏆 Score: {self.score}")
            
            stars = "⭐" * self.consecutive + "☆" * (3 - self.consecutive)
            self.stars_label.setText(stars)
            
            # Log to CSV
            with open(CSV_FILE, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    datetime.now().strftime("%H:%M:%S"),
                    CHILD_NAME,
                    self.current_task["name"],
                    "SUCCESS",
                    self.score,
                    self.consecutive,
                    self.finger_count
                ])
            
            if self.consecutive >= 3:
                self.consecutive = 0
                self.mastered += 1
                self.mastered_label.setText(f"⭐ Mastered: {self.mastered}")
                voice.say(f"AMAZING {CHILD_NAME}! You mastered {self.current_task['name']}! +{points} points!")
                self.feedback.setText(f"🏆 MASTERED! +{points} points! 🏆")
            else:
                voice.say(f"Great job {CHILD_NAME}! {self.current_task['name']} is correct!")
            
            QTimer.singleShot(2000, lambda: self.avatar.set_speaking(False))
            QTimer.singleShot(2000, self.next_task)
        else:
            # Failure
            self.consecutive = 0
            
            for btn in self.buttons:
                if btn.value == selected:
                    btn.flash_wrong()
                if btn.value == self.correct_value:
                    btn.flash_correct()
            
            correct_display = str(self.correct_value).upper()
            self.feedback.setText(f"❌ Try again! The answer was {correct_display}")
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
                    "FAIL",
                    self.score,
                    0,
                    self.finger_count
                ])
            
            voice.say(f"That's okay! The answer was {self.correct_value}. Let's try the next one!")
            QTimer.singleShot(2000, lambda: self.avatar.set_speaking(False))
            QTimer.singleShot(2500, self.next_task)
    
    def task_timeout(self):
        if self.locked:
            return
        
        self.locked = True
        self.consecutive = 0
        
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
                "TIMEOUT",
                self.score,
                0,
                self.finger_count
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
║  PEPPER CLINICAL — WITH WORKING CAMERA                       ║
╠══════════════════════════════════════════════════════════════╣
║  ✓ Real-time finger detection (0-10 fingers)               ║
║  ✓ Live camera feed with hand tracking                      ║
║  ✓ Click tasks (Colors, Animals, Numbers)                   ║
║  ✓ Animated Pepper avatar                                   ║
║  ✓ Voice feedback                                           ║
║  ✓ 15 second timeout with progress bar                      ║
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
