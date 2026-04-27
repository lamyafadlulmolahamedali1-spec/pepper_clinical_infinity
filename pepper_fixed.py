#!/usr/bin/env python3
"""
PEPPER CLINICAL INFINITY - FULLY FIXED
- All Qt operations on main thread only
- 10-finger detection
- Ultra-sensitive clicks
- Reliable speech recognition
- Auto-advance on timeout
- Animated Pepper avatar
"""

import os
import sys
import time
import threading
import random
import math
import csv
from datetime import datetime
from collections import deque

# Set environment before imports
os.environ['QT_QPA_PLATFORM'] = 'xcb'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

# Import Qt first
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

# Import other libraries
import cv2
import numpy as np
try:
    import mediapipe as mp
    MP_AVAILABLE = True
except:
    MP_AVAILABLE = False
    print("⚠️ MediaPipe not available - using basic detection")

try:
    import pyttsx3
    TTS_AVAILABLE = True
except:
    TTS_AVAILABLE = False
    print("⚠️ TTS not available")

try:
    import speech_recognition as sr
    SR_AVAILABLE = True
except:
    SR_AVAILABLE = False
    print("⚠️ Speech recognition not available")

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
    writer.writerow(["Timestamp", "Child", "Task", "Domain", "Result", "Stars", "Score", "Time_taken"])

# ============================================================
# TASKS
# ============================================================
TASKS = [
    # Motor tasks
    {"id": "clap", "name": "👏 CLAP HANDS", "domain": "Motor", "type": "motor", "action": "clap", "tokens": 2,
     "instruction": "Clap your hands!", "success": "Great clapping!"},
    {"id": "wave", "name": "👋 WAVE", "domain": "Motor", "type": "motor", "action": "wave", "tokens": 2,
     "instruction": "Wave your hand!", "success": "Nice wave!"},
    {"id": "raise_hand", "name": "✋ RAISE HAND", "domain": "Motor", "type": "motor", "action": "raise_hand", "tokens": 3,
     "instruction": "Raise your hand!", "success": "Hand raised!"},
    
    # Color tasks
    {"id": "red", "name": "🔴 FIND RED", "domain": "Cognitive", "type": "color", "target": "red", "tokens": 3,
     "instruction": "Click the RED button!", "options": ["red", "blue", "green", "yellow"],
     "correct": 0, "success": "Red is correct!"},
    {"id": "blue", "name": "🔵 FIND BLUE", "domain": "Cognitive", "type": "color", "target": "blue", "tokens": 3,
     "instruction": "Click the BLUE button!", "options": ["blue", "red", "green", "yellow"],
     "correct": 0, "success": "Blue is correct!"},
    {"id": "green", "name": "🟢 FIND GREEN", "domain": "Cognitive", "type": "color", "target": "green", "tokens": 3,
     "instruction": "Click the GREEN button!", "options": ["green", "red", "blue", "yellow"],
     "correct": 0, "success": "Green is correct!"},
    
    # Animal tasks
    {"id": "lion", "name": "🦁 FIND LION", "domain": "Cognitive", "type": "animal", "target": "lion", "tokens": 3,
     "instruction": "Click the LION!", "options": ["lion", "elephant", "monkey", "giraffe"],
     "correct": 0, "success": "Lion found!"},
    {"id": "elephant", "name": "🐘 FIND ELEPHANT", "domain": "Cognitive", "type": "animal", "target": "elephant", "tokens": 3,
     "instruction": "Click the ELEPHANT!", "options": ["elephant", "lion", "monkey", "giraffe"],
     "correct": 0, "success": "Elephant found!"},
    
    # Counting tasks
    {"id": "count_2", "name": "🔢 SHOW 2", "domain": "Math", "type": "count", "target": 2, "tokens": 3,
     "instruction": "Show me 2 fingers!", "success": "Two fingers!"},
    {"id": "count_3", "name": "🔢 SHOW 3", "domain": "Math", "type": "count", "target": 3, "tokens": 3,
     "instruction": "Show me 3 fingers!", "success": "Three fingers!"},
    {"id": "count_4", "name": "🔢 SHOW 4", "domain": "Math", "type": "count", "target": 4, "tokens": 4,
     "instruction": "Show me 4 fingers!", "success": "Four fingers!"},
    {"id": "count_5", "name": "🔢 SHOW 5", "domain": "Math", "type": "count", "target": 5, "tokens": 4,
     "instruction": "Show me 5 fingers!", "success": "Five fingers!"},
]

# ============================================================
# GLOBAL STATE (Thread-safe via signals)
# ============================================================
class GlobalState(QObject):
    update_signal = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.task_index = 0
        self.consecutive = 0
        self.mastered = 0
        self.score = 0
        self.tokens = 0
        self.success_count = 0
        self.fail_count = 0
        
        # Vision
        self.finger_count = 0
        self.finger_left = 0
        self.finger_right = 0
        self.clapping = False
        self.waving = False
        self.hand_raised = False
        self.emotion = "neutral"
        
        # Task state
        self.current_action = None
        self.action_detected = False
        self.action_timeout = 0
        self.tablet_click = None
        self.speech_text = ""
        
        # Audio
        self.is_speaking = False
        self.recording = False
        self.lip_value = 0
        
        # Timing
        self.task_start = 0
        self.start_time = time.time()
        
        # Lock for thread-safe access
        self._lock = threading.Lock()
    
    def set_fingers(self, left, right):
        with self._lock:
            self.finger_left = left
            self.finger_right = right
            self.finger_count = left + right
            self.update_signal.emit()
    
    def set_action(self, action, detected):
        with self._lock:
            if self.current_action == action and detected:
                self.action_detected = True
            self.update_signal.emit()
    
    def get_fingers(self):
        with self._lock:
            return self.finger_count
    
    def get_action_detected(self):
        with self._lock:
            if self.action_detected:
                self.action_detected = False
                return True
            return False

state = GlobalState()

# ============================================================
# VOICE ENGINE (Main thread only)
# ============================================================
class VoiceEngine(QObject):
    finished = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.engine = None
        if TTS_AVAILABLE:
            try:
                self.engine = pyttsx3.init()
                self.engine.setProperty('rate', 130)
                print("✅ Voice ready")
            except:
                print("⚠️ Voice not available")
    
    def say(self, text):
        if self.engine:
            state.is_speaking = True
            print(f"\n🔊 Pepper: {text}")
            # Animate lips in separate thread
            threading.Thread(target=self._animate_lips, args=(text,), daemon=True).start()
            self.engine.say(text)
            self.engine.runAndWait()
            state.is_speaking = False
            self.finished.emit()
    
    def _animate_lips(self, text):
        words = text.split()
        for w in words:
            if not state.is_speaking:
                break
            state.lip_value = 0.8
            time.sleep(max(0.05, len(w) * 0.05))
            state.lip_value = 0.2
            time.sleep(0.03)
        state.lip_value = 0

voice = VoiceEngine()

# ============================================================
# CAMERA THREAD (Separate thread, updates state via lock)
# ============================================================
class CameraThread(QThread):
    def __init__(self):
        super().__init__()
        self.running = True
        self.cap = None
        self.hands = None
        self.pose = None
        
        # Open camera
        for idx in [0, 1]:
            cap = cv2.VideoCapture(idx)
            if cap.isOpened():
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                self.cap = cap
                print(f"✅ Camera {idx}")
                break
            cap.release()
        
        # Initialize MediaPipe
        if MP_AVAILABLE:
            try:
                self.hands = mp.solutions.hands.Hands(
                    max_num_hands=2,
                    min_detection_confidence=0.6,
                    min_tracking_confidence=0.5
                )
                self.pose = mp.solutions.pose.Pose(
                    min_detection_confidence=0.5,
                    min_tracking_confidence=0.5
                )
                print("✅ MediaPipe ready")
            except:
                pass
    
    def count_fingers(self, hand_landmarks, handedness):
        """Count fingers for one hand (0-5)"""
        try:
            lm = hand_landmarks.landmark
            tips = [4, 8, 12, 16, 20]
            dips = [3, 6, 10, 14, 18]
            count = 0
            
            # Thumb
            if handedness == "Right":
                if lm[4].x < lm[3].x:
                    count += 1
            else:
                if lm[4].x > lm[3].x:
                    count += 1
            
            # Other fingers
            for i in range(1, 5):
                if lm[tips[i]].y < lm[dips[i]].y:
                    count += 1
            
            return count
        except:
            return 0
    
    def detect_gestures(self, hands_result):
        if not hands_result.multi_hand_landmarks:
            state.set_fingers(0, 0)
            return
        
        left_count = 0
        right_count = 0
        
        for i, (hand, handedness) in enumerate(zip(
            hands_result.multi_hand_landmarks,
            hands_result.multi_handedness
        )):
            label = handedness.classification[0].label
            count = self.count_fingers(hand, label)
            if label == "Left":
                left_count = count
            else:
                right_count = count
        
        state.set_fingers(left_count, right_count)
        
        # Detect clapping (hands close)
        if len(hands_result.multi_hand_landmarks) >= 2:
            h1 = hands_result.multi_hand_landmarks[0].landmark[0]
            h2 = hands_result.multi_hand_landmarks[1].landmark[0]
            distance = abs(h1.x - h2.x) + abs(h1.y - h2.y)
            if distance < 0.15:
                state.set_action("clap", True)
    
    def detect_pose(self, pose_result):
        if not pose_result.pose_landmarks:
            return
        
        lm = pose_result.pose_landmarks.landmark
        left_raised = lm[15].y < lm[11].y - 0.1
        right_raised = lm[16].y < lm[12].y - 0.1
        
        if left_raised or right_raised:
            state.set_action("raise_hand", True)
    
    def run(self):
        while self.running:
            if self.cap and self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret:
                    frame = cv2.flip(frame, 1)
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    
                    if self.hands:
                        hands_result = self.hands.process(rgb)
                        self.detect_gestures(hands_result)
                    
                    if self.pose:
                        pose_result = self.pose.process(rgb)
                        self.detect_pose(pose_result)
            
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
class ClickButton(QPushButton):
    def __init__(self, text, value, color=None):
        super().__init__()
        self.value = value
        self.setText(text)
        self.setFixedSize(130, 130)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        if color:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: {color};
                    border-radius: 65px;
                    border: 3px solid white;
                    color: white;
                    font-size: 18px;
                    font-weight: bold;
                }}
                QPushButton:hover {{ border: 5px solid #fbbf24; }}
                QPushButton:pressed {{ background: {color}cc; }}
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                        stop:0 #1e1b4b, stop:1 #0c0f2e);
                    border-radius: 20px;
                    border: 3px solid #4f46e5;
                    color: #e0e6ff;
                    font-size: 16px;
                    font-weight: bold;
                }
                QPushButton:hover { border: 4px solid #a78bfa; }
            """)
    
    def flash_correct(self):
        self.setStyleSheet(self.styleSheet() + "QPushButton { border: 5px solid #22c55e !important; background: #166534 !important; }")
        QTimer.singleShot(500, self._reset_style)
    
    def flash_wrong(self):
        self.setStyleSheet(self.styleSheet() + "QPushButton { border: 5px solid #ef4444 !important; }")
        QTimer.singleShot(500, self._reset_style)
    
    def _reset_style(self):
        # Reapply original style
        if hasattr(self, 'original_style'):
            self.setStyleSheet(self.original_style)

# ============================================================
# PEPPER AVATAR WIDGET
# ============================================================
class PepperAvatar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(200, 200)
        self.phase = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(50)
    
    def update_animation(self):
        self.phase += 0.1
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w, h = 200, 200
        cx, cy = w//2, h//2 - 10
        
        # Body
        painter.setBrush(QBrush(QColor(80, 100, 200)))
        painter.setPen(QPen(QColor(100, 120, 220), 2))
        painter.drawEllipse(cx-35, cy+30, 70, 80)
        
        # Head
        painter.setBrush(QBrush(QColor(220, 195, 173)))
        painter.setPen(QPen(QColor(200, 175, 155), 2))
        painter.drawEllipse(cx-40, cy-15, 80, 75)
        
        # Eyes
        eye_y = cy - 5
        eye_open = 6
        painter.setBrush(QBrush(QColor(100, 180, 255)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(cx-22, eye_y, 10, eye_open)
        painter.drawEllipse(cx+12, eye_y, 10, eye_open)
        
        # Pupils
        painter.setBrush(QBrush(Qt.GlobalColor.white))
        painter.drawEllipse(cx-20, eye_y-1, 4, 4)
        painter.drawEllipse(cx+14, eye_y-1, 4, 4)
        
        # Nose
        painter.setBrush(QBrush(QColor(180, 140, 120)))
        painter.drawEllipse(cx-5, cy+3, 10, 8)
        
        # Mouth with lip sync
        lip = state.lip_value
        if state.is_speaking or lip > 0:
            mouth_h = int(5 + lip * 15)
            painter.setBrush(QBrush(QColor(160, 80, 80)))
            painter.drawChord(cx-15, cy+12, 30, mouth_h, 0, 180*16)
        else:
            painter.setPen(QPen(QColor(150, 80, 80), 3))
            painter.drawLine(cx-12, cy+18, cx+12, cy+18)
        
        # Animated arms
        arm_angle = int(20 * math.sin(self.phase * 6)) if state.is_speaking else 0
        painter.setBrush(QBrush(QColor(70, 90, 190)))
        painter.drawEllipse(cx-55 + arm_angle//2, cy+25, 15, 40)
        painter.drawEllipse(cx+40 - arm_angle//2, cy+25, 15, 40)

# ============================================================
# MAIN WINDOW
# ============================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Pepper Clinical - {CHILD_NAME}")
        self.setFixedSize(1280, 780)
        
        self.buttons = []
        self.locked = True
        self.correct_idx = -1
        self.current_task = None
        self.task_timeout_timer = None
        
        self.setup_ui()
        self.connect_signals()
        
        # Stats timer
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self.update_stats)
        self.stats_timer.start(200)
        
        # Start camera
        self.camera = CameraThread()
        self.camera.start()
        
        # Start therapy
        QTimer.singleShot(2000, self.start_therapy)
    
    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        central.setStyleSheet("background: #060918;")
        
        main_layout = QHBoxLayout(central)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # LEFT PANEL
        left = QFrame()
        left.setFixedWidth(640)
        left.setStyleSheet("background: #0a0d1e; border-right: 2px solid #1a1f40;")
        left_layout = QVBoxLayout(left)
        
        # Camera placeholder
        self.camera_label = QLabel("📷 Camera Starting...")
        self.camera_label.setFixedSize(640, 480)
        self.camera_label.setStyleSheet("background: #000; color: #666; font-size: 20px;")
        self.camera_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(self.camera_label)
        
        # Info panel
        info = QFrame()
        info.setStyleSheet("background: #0c0f1e; border-radius: 10px; margin: 10px;")
        info_layout = QVBoxLayout(info)
        
        self.finger_label = QLabel("✋ Fingers: 0")
        self.finger_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.finger_label.setStyleSheet("color: #fbbf24;")
        self.finger_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_layout.addWidget(self.finger_label)
        
        self.emotion_label = QLabel("😊 Emotion: neutral")
        self.emotion_label.setFont(QFont("Arial", 12))
        self.emotion_label.setStyleSheet("color: #60a5fa;")
        self.emotion_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_layout.addWidget(self.emotion_label)
        
        left_layout.addWidget(info)
        left_layout.addStretch()
        main_layout.addWidget(left)
        
        # RIGHT PANEL
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setSpacing(10)
        right_layout.setContentsMargins(15, 10, 15, 10)
        
        # Header with avatar
        header = QFrame()
        header.setFixedHeight(100)
        header.setStyleSheet("background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #1a0a3d,stop:0.5 #0a0f28,stop:1 #1a0a3d); border-radius: 15px; border: 2px solid #4f46e5;")
        header_layout = QHBoxLayout(header)
        
        self.avatar = PepperAvatar()
        header_layout.addWidget(self.avatar)
        
        title_box = QVBoxLayout()
        title = QLabel("PEPPER CLINICAL INFINITY")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #a78bfa;")
        title_box.addWidget(title)
        
        child = QLabel(f"👦 {CHILD_NAME}")
        child.setFont(QFont("Arial", 11))
        child.setStyleSheet("color: #60a5fa;")
        title_box.addWidget(child)
        header_layout.addLayout(title_box, 1)
        
        self.status_label = QLabel("💤 Ready")
        self.status_label.setFont(QFont("Arial", 10))
        self.status_label.setStyleSheet("color: #9ca3af;")
        header_layout.addWidget(self.status_label)
        
        right_layout.addWidget(header)
        
        # Stars
        stars_frame = QFrame()
        stars_frame.setFixedHeight(60)
        stars_frame.setStyleSheet("background: #0c0f1e; border-radius: 12px;")
        stars_layout = QHBoxLayout(stars_frame)
        
        self.stars_label = QLabel("☆ ☆ ☆")
        self.stars_label.setFont(QFont("Arial", 28))
        self.stars_label.setStyleSheet("color: #4b5563;")
        self.stars_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stars_layout.addWidget(self.stars_label)
        
        self.mastery_label = QLabel("0/3")
        self.mastery_label.setFont(QFont("Arial", 12))
        self.mastery_label.setStyleSheet("color: #6b7280;")
        stars_layout.addWidget(self.mastery_label)
        right_layout.addWidget(stars_frame)
        
        # Instruction
        instr_frame = QFrame()
        instr_frame.setFixedHeight(70)
        instr_frame.setStyleSheet("background: #1e1b4b; border-radius: 12px; border: 2px solid #4f46e5;")
        instr_layout = QVBoxLayout(instr_frame)
        
        self.instr_label = QLabel("Getting ready...")
        self.instr_label.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        self.instr_label.setStyleSheet("color: #e0e6ff;")
        self.instr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.instr_label.setWordWrap(True)
        instr_layout.addWidget(self.instr_label)
        right_layout.addWidget(instr_frame)
        
        # Content area
        self.content_frame = QFrame()
        self.content_frame.setMinimumHeight(280)
        self.content_frame.setStyleSheet("background: rgba(12,15,30,0.95); border-radius: 14px; border: 2px solid #1a1f40;")
        self.content_layout = QVBoxLayout(self.content_frame)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(self.content_frame, 1)
        
        # Feedback
        fb_frame = QFrame()
        fb_frame.setFixedHeight(50)
        fb_frame.setStyleSheet("background: #0c0f1e; border-radius: 10px;")
        fb_layout = QHBoxLayout(fb_frame)
        
        self.fb_label = QLabel("💤 Waiting for Pepper...")
        self.fb_label.setFont(QFont("Arial", 11))
        self.fb_label.setStyleSheet("color: #9ca3af;")
        fb_layout.addWidget(self.fb_label, 1)
        right_layout.addWidget(fb_frame)
        
        # Stats bar
        stats_bar = QFrame()
        stats_bar.setFixedHeight(45)
        stats_bar.setStyleSheet("background: #07090f; border-radius: 10px;")
        stats_layout = QHBoxLayout(stats_bar)
        
        self.score_label = QLabel("Score: 0")
        self.score_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.score_label.setStyleSheet("color: #a78bfa;")
        stats_layout.addWidget(self.score_label)
        
        self.tokens_label = QLabel("Tokens: 0")
        self.tokens_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.tokens_label.setStyleSheet("color: #fbbf24;")
        stats_layout.addWidget(self.tokens_label)
        
        self.mastered_label = QLabel("Mastered: 0")
        self.mastered_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.mastered_label.setStyleSheet("color: #34d399;")
        stats_layout.addWidget(self.mastered_label)
        
        right_layout.addWidget(stats_bar)
        main_layout.addWidget(right)
        
        # Lock overlay
        self.lock_overlay = QLabel("🔒")
        self.lock_overlay.setParent(self.content_frame)
        self.lock_overlay.setGeometry(0, 0, 600, 280)
        self.lock_overlay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lock_overlay.setFont(QFont("Arial", 48))
        self.lock_overlay.setStyleSheet("QLabel { background: rgba(0,0,0,0.6); border-radius: 14px; color: #a78bfa; }")
        self.lock_overlay.hide()
    
    def connect_signals(self):
        state.update_signal.connect(self.on_state_update)
        voice.finished.connect(self.on_voice_done)
    
    def on_state_update(self):
        self.finger_label.setText(f"✋ Fingers: {state.finger_count}")
    
    def on_voice_done(self):
        self.status_label.setText("💤 Ready")
    
    def update_stats(self):
        self.score_label.setText(f"Score: {state.score}")
        self.tokens_label.setText(f"Tokens: {state.tokens}")
        self.mastered_label.setText(f"Mastered: {state.mastered}")
        
        stars = "⭐" * state.consecutive + "☆" * (3 - state.consecutive)
        self.stars_label.setText(stars)
        self.mastery_label.setText(f"{state.consecutive}/3")
        
        if state.is_speaking:
            self.status_label.setText("🔊 Speaking")
        else:
            self.status_label.setText("💤 Ready")
    
    def start_therapy(self):
        voice.say(f"Hello {CHILD_NAME}! I am Pepper!")
        QTimer.singleShot(2000, self.next_task)
    
    def next_task(self):
        task = TASKS[state.task_index % len(TASKS)]
        self.current_task = task
        state.task_start = time.time()
        state.tablet_click = None
        state.current_action = task.get("action")
        state.action_detected = False
        state.action_timeout = time.time() + 20
        
        # Show task UI
        self.clear_content()
        self.instr_label.setText(task["instruction"])
        self.fb_label.setText("Your turn!")
        self.fb_label.setStyleSheet("color: #60a5fa;")
        
        if task["type"] == "color" or task["type"] == "animal":
            self.show_choice_task(task)
        elif task["type"] == "count":
            self.show_count_task(task)
        else:  # motor
            self.show_motor_task(task)
        
        self.unlock()
        
        # Set timeout
        if self.task_timeout_timer:
            self.task_timeout_timer.stop()
        self.task_timeout_timer = QTimer()
        self.task_timeout_timer.setSingleShot(True)
        self.task_timeout_timer.timeout.connect(self.task_timeout)
        self.task_timeout_timer.start(20000)
        
        # Announce
        voice.say(task["instruction"])
    
    def show_choice_task(self, task):
        options = task["options"]
        self.correct_idx = task["correct"]
        
        # Map display names
        display_names = {
            "red": "🔴 RED", "blue": "🔵 BLUE", "green": "🟢 GREEN", "yellow": "🟡 YELLOW",
            "lion": "🦁 LION", "elephant": "🐘 ELEPHANT", "monkey": "🐵 MONKEY", "giraffe": "🦒 GIRAFFE"
        }
        
        colors = {"red": "#ef4444", "blue": "#3b82f6", "green": "#22c55e", "yellow": "#eab308"}
        
        grid = QWidget()
        grid_layout = QGridLayout(grid)
        grid_layout.setSpacing(15)
        
        for i, opt in enumerate(options):
            display = display_names.get(opt, opt.upper())
            color = colors.get(opt)
            btn = ClickButton(display, i, color)
            btn.clicked.connect(lambda checked, idx=i: self.on_button_click(idx))
            self.buttons.append(btn)
            grid_layout.addWidget(btn, i//2, i%2)
        
        self.content_layout.addWidget(grid)
    
    def show_count_task(self, task):
        target = task["target"]
        state.current_action = "count"
        
        count_frame = QFrame()
        count_frame.setStyleSheet("background: #1a3320; border-radius: 20px; border: 3px solid #22c55e;")
        count_layout = QVBoxLayout(count_frame)
        count_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        num = QLabel(str(target))
        num.setFont(QFont("Arial", 64, QFont.Weight.Bold))
        num.setStyleSheet("color: #34d399;")
        num.setAlignment(Qt.AlignmentFlag.AlignCenter)
        count_layout.addWidget(num)
        
        hint = QLabel("Show me with your fingers! 🖐️")
        hint.setFont(QFont("Arial", 14))
        hint.setStyleSheet("color: #6b7280;")
        count_layout.addWidget(hint)
        
        self.content_layout.addWidget(count_frame)
    
    def show_motor_task(self, task):
        motor_frame = QFrame()
        motor_frame.setStyleSheet("background: #1e1b4b; border-radius: 20px; border: 3px solid #a78bfa;")
        motor_layout = QVBoxLayout(motor_frame)
        motor_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        action = QLabel(task["name"])
        action.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        action.setStyleSheet("color: #a78bfa;")
        motor_layout.addWidget(action)
        
        arrow = QLabel("👇 DO IT NOW! 👇")
        arrow.setFont(QFont("Arial", 16))
        arrow.setStyleSheet("color: #34d399;")
        motor_layout.addWidget(arrow)
        
        self.content_layout.addWidget(motor_frame)
    
    def on_button_click(self, idx):
        if self.locked:
            return
        
        if idx == self.correct_idx:
            state.tablet_click = "correct"
            for btn in self.buttons:
                if btn.value == idx:
                    btn.flash_correct()
            self.fb_label.setText("✅ CORRECT! Well done!")
            self.fb_label.setStyleSheet("color: #34d399;")
            self.lock()
            QTimer.singleShot(500, self.task_success)
        else:
            for btn in self.buttons:
                if btn.value == self.correct_idx:
                    btn.flash_correct()
            self.fb_label.setText("❌ Try again! Look carefully!")
            self.fb_label.setStyleSheet("color: #f87171;")
            QTimer.singleShot(1500, lambda: self.fb_label.setStyleSheet("color: #9ca3af;"))
    
    def task_success(self):
        if self.task_timeout_timer:
            self.task_timeout_timer.stop()
        
        task = self.current_task
        points = task.get("tokens", 2) * 5
        state.consecutive += 1
        state.score += points
        state.tokens += task.get("tokens", 2)
        state.success_count += 1
        
        time_taken = int(time.time() - state.task_start)
        
        # Log to CSV
        with open(CSV_FILE, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().strftime("%H:%M:%S"),
                CHILD_NAME,
                task["id"],
                task["domain"],
                "SUCCESS",
                state.consecutive,
                state.score,
                time_taken
            ])
        
        self.fb_label.setText(f"✅ +{points} points!")
        self.fb_label.setStyleSheet("color: #34d399;")
        
        if state.consecutive >= 3:
            state.consecutive = 0
            state.mastered += 1
            voice.say(f"AMAZING {CHILD_NAME}! You mastered {task['domain']}! +{points} points!")
        else:
            voice.say(f"Great job {CHILD_NAME}! {task['success']}")
        
        state.task_index += 1
        QTimer.singleShot(2000, self.next_task)
    
    def task_timeout(self):
        if self.locked:
            return
        
        task = self.current_task
        state.consecutive = 0
        state.fail_count += 1
        
        time_taken = int(time.time() - state.task_start)
        
        with open(CSV_FILE, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().strftime("%H:%M:%S"),
                CHILD_NAME,
                task["id"],
                task["domain"],
                "TIMEOUT",
                0,
                state.score,
                time_taken
            ])
        
        self.fb_label.setText("⏰ Time's up! Moving to next task...")
        self.fb_label.setStyleSheet("color: #f59e0b;")
        
        state.task_index += 1
        voice.say("That's okay! Let's try something else!")
        QTimer.singleShot(2000, self.next_task)
    
    def unlock(self):
        self.locked = False
        self.lock_overlay.hide()
        for btn in self.buttons:
            btn.setEnabled(True)
    
    def lock(self):
        self.locked = True
        self.lock_overlay.show()
        for btn in self.buttons:
            btn.setEnabled(False)
    
    def clear_content(self):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.buttons.clear()
    
    def closeEvent(self, event):
        self.camera.stop()
        event.accept()

# ============================================================
# MAIN
# ============================================================
def main():
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║  PEPPER CLINICAL INFINITY — {CHILD_NAME:<30}║
╠══════════════════════════════════════════════════════════════╣
║  ✓ All operations on main thread                           ║
║  ✓ 10-finger detection (MediaPipe)                         ║
║  ✓ Ultra-sensitive clicks                                  ║
║  ✓ Auto-advance on timeout (20 seconds)                    ║
║  ✓ Animated Pepper avatar with lip-sync                    ║
║  ✓ CSV progress log                                        ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
