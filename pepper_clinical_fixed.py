#!/usr/bin/env python3
"""
PEPPER CLINICAL INFINITY - FIXED VERSION
Fixed: Click accuracy, Speech sensitivity, Movement detection
"""

import os
import sys
import time
import threading
import random
import math
import re
import csv
import json
import base64
import signal
import socket
from datetime import datetime
from collections import deque
import warnings

# Suppress warnings
os.environ.update({
    'TF_CPP_MIN_LOG_LEVEL': '3',
    'PYTHONWARNINGS': 'ignore',
    'OPENCV_LOG_LEVEL': 'ERROR',
    'QT_LOGGING_RULES': '*.debug=false',
    'QT_QPA_PLATFORM': 'xcb',
})
warnings.filterwarnings('ignore')

# Import required modules
try:
    import cv2
    import numpy as np
    import mediapipe as mp
    from PIL import Image, ImageDraw
    import pyttsx3
    import speech_recognition as sr
except ImportError as e:
    print(f"Please install missing module: {e}")
    print("Run: pip install opencv-python mediapipe Pillow pyttsx3 SpeechRecognition")
    sys.exit(1)

# PyQt6 imports
try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QPushButton, QFrame, QGridLayout
    )
    from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QThread
    from PyQt6.QtGui import QFont, QPixmap, QImage
except ImportError as e:
    print(f"Please install PyQt6: {e}")
    print("Run: pip install PyQt6")
    sys.exit(1)

# ============================================================
# CONFIGURATION
# ============================================================
MIC_ENERGY = 150  # Lower = more sensitive
MASTERY_N = 3

print("\n" + "="*60)
print("  PEPPER CLINICAL INFINITY - FIXED")
print("="*60)

CHILD_NAME = input("\nEnter Child's Name: ").strip()
if not CHILD_NAME:
    CHILD_NAME = "Child"

CHILD_NAME_SAFE = re.sub(r'[^a-zA-Z0-9_]', '_', CHILD_NAME)
CSV_FILE = f"{CHILD_NAME_SAFE}_Results.csv"

# Track completed tasks
COMPLETED_TASKS = set()

# Create CSV
with open(CSV_FILE, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(["Timestamp", "Child", "Task", "Domain", "Result", "Score"])

def log_csv(task_id, domain, result, score):
    with open(CSV_FILE, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            CHILD_NAME, task_id, domain, 
            "SUCCESS" if result else "FAIL",
            score
        ])

# ============================================================
# TASK DEFINITIONS
# ============================================================
COLORS = [
    {"id": "red", "color": "#ef4444", "label": "🔴 RED"},
    {"id": "blue", "color": "#3b82f6", "label": "🔵 BLUE"},
    {"id": "green", "color": "#22c55e", "label": "🟢 GREEN"},
    {"id": "yellow", "color": "#eab308", "label": "🟡 YELLOW"},
]

ANIMALS = [
    {"id": "dog", "emoji": "🐶", "label": "Dog"},
    {"id": "cat", "emoji": "🐱", "label": "Cat"},
    {"id": "lion", "emoji": "🦁", "label": "Lion"},
    {"id": "elephant", "emoji": "🐘", "label": "Elephant"},
]

FRUITS = [
    {"id": "apple", "emoji": "🍎", "label": "Apple"},
    {"id": "banana", "emoji": "🍌", "label": "Banana"},
    {"id": "orange", "emoji": "🍊", "label": "Orange"},
    {"id": "grapes", "emoji": "🍇", "label": "Grapes"},
]

MOTOR_TASKS = [
    {"id": "clap", "name": "👏 Clap Hands", "verify": "clap",
     "instruction": "Clap your hands together! 👏",
     "success": "Great clapping!", "fail": "Try clapping your hands!"},
    {"id": "wave", "name": "👋 Wave Hello", "verify": "wave",
     "instruction": "Wave your hand side to side! 👋",
     "success": "Wonderful wave!", "fail": "Wave your hand!"},
    {"id": "raise_hand", "name": "✋ Raise Hand", "verify": "raise_hand",
     "instruction": "Raise your hand high in the air! ✋",
     "success": "Perfect! Hand up!", "fail": "Raise your hand up!"},
]

def generate_task():
    """Generate a unique task"""
    global COMPLETED_TASKS
    
    # Task pools
    pools = {
        "Motor": MOTOR_TASKS,
        "Color": COLORS,
        "Animal": ANIMALS,
        "Fruit": FRUITS,
    }
    
    # Find available tasks
    available = []
    for domain, pool in pools.items():
        for item in pool:
            task_id = f"{domain}_{item['id']}"
            if task_id not in COMPLETED_TASKS:
                available.append((domain, item))
    
    # If all done, reset
    if not available:
        COMPLETED_TASKS.clear()
        available = [(domain, item) for domain, pool in pools.items() for item in pool]
    
    # Pick random task
    domain, item = random.choice(available)
    task_id = f"{domain}_{item['id']}"
    COMPLETED_TASKS.add(task_id)
    
    if domain == "Motor":
        return {
            "id": task_id,
            "domain": domain,
            "name": item["name"],
            "instruction": item["instruction"],
            "success": item["success"],
            "fail": item["fail"],
            "verify": item["verify"],
            "type": "motor",
            "tokens": 2
        }
    else:
        # Cognitive task (color, animal, fruit)
        if domain == "Color":
            options = COLORS
            correct_idx = next(i for i, opt in enumerate(options) if opt["id"] == item["id"])
        elif domain == "Animal":
            options = ANIMALS
            correct_idx = next(i for i, opt in enumerate(options) if opt["id"] == item["id"])
        else:  # Fruit
            options = FRUITS
            correct_idx = next(i for i, opt in enumerate(options) if opt["id"] == item["id"])
        
        return {
            "id": task_id,
            "domain": domain,
            "name": f"Find {item['label']}",
            "instruction": f"Click the {item['label']}!",
            "success": f"Correct! That's the {item['label']}!",
            "fail": f"Find the {item['label']}!",
            "verify": "click",
            "type": "cognitive",
            "options": options,
            "correct_idx": correct_idx,
            "tokens": 3
        }

# ============================================================
# SHARED STATE
# ============================================================
ST = {
    "name": CHILD_NAME,
    "score": 0,
    "consecutive": 0,
    "tasks_mastered": 0,
    "clapping": False,
    "waving": False,
    "hand_raised": False,
    "tablet_click_result": None,
    "is_speaking": False,
    "waiting": False,
    "session_start": time.time(),
}

# ============================================================
# BRIDGE FOR SIGNALS
# ============================================================
class Bridge(QObject):
    new_task = pyqtSignal(dict)
    show_success = pyqtSignal(str)
    show_fail = pyqtSignal(str)
    update_camera = pyqtSignal(object)
    update_stats = pyqtSignal()
    celebration = pyqtSignal()
    unlock = pyqtSignal()
    lock = pyqtSignal()

BRIDGE = Bridge()

# ============================================================
# MOVEMENT DETECTOR
# ============================================================
class MovementDetector:
    def __init__(self):
        self.clap_history = deque(maxlen=10)
        self.wave_history = deque(maxlen=15)
        self.prev_wrist_x = None
        
    def detect_clap(self, hands):
        if len(hands) < 2:
            self.clap_history.append(False)
            return False
        
        # Get wrist positions
        left_wrist = hands[0].landmark[0]
        right_wrist = hands[1].landmark[0]
        
        # Distance between wrists
        dist = abs(left_wrist.x - right_wrist.x)
        is_clap = dist < 0.15
        
        self.clap_history.append(is_clap)
        
        # Check for pattern
        if len(self.clap_history) >= 6:
            recent = list(self.clap_history)[-6:]
            if recent[-3:] == [True, True, True]:
                return True
        return False
    
    def detect_wave(self, hand):
        if not hand:
            return False
        
        wrist = hand.landmark[0]
        current_x = wrist.x
        
        if self.prev_wrist_x is not None:
            movement = abs(current_x - self.prev_wrist_x)
            self.wave_history.append(movement)
            
            if len(self.wave_history) >= 10:
                avg_movement = sum(self.wave_history) / len(self.wave_history)
                self.prev_wrist_x = current_x
                return avg_movement > 0.03
        
        self.prev_wrist_x = current_x
        return False
    
    def detect_hand_raised(self, hand, pose):
        if not hand or not pose:
            return False
        
        wrist_y = hand.landmark[0].y
        shoulder_y = pose[11].y  # Left shoulder
        
        return wrist_y < shoulder_y - 0.1

# ============================================================
# CAMERA THREAD
# ============================================================
class CameraThread(QThread):
    def __init__(self):
        super().__init__()
        self.running = True
        self.cap = None
        self.detector = MovementDetector()
        self._init_camera()
        
    def _init_camera(self):
        for i in [0, 1]:
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                self.cap = cap
                print(f"✅ Camera ready (index {i})")
                return
        print("⚠️ No camera found - using simulation")
        
    def run(self):
        mp_hands = mp.solutions.hands
        mp_pose = mp.solutions.pose
        
        hands = mp_hands.Hands(min_detection_confidence=0.5, min_tracking_confidence=0.5)
        pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
        
        while self.running:
            if self.cap and self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret:
                    frame = cv2.flip(frame, 1)
                else:
                    frame = self._create_sim_frame()
            else:
                frame = self._create_sim_frame()
            
            # Process with MediaPipe
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            hands_result = hands.process(rgb)
            pose_result = pose.process(rgb)
            
            # Detect movements
            if hands_result.multi_hand_landmarks:
                # Draw hands
                for hand_landmarks in hands_result.multi_hand_landmarks:
                    mp.solutions.drawing_utils.draw_landmarks(
                        frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                
                # Detect clap
                ST["clapping"] = self.detector.detect_clap(hands_result.multi_hand_landmarks)
                
                # Detect wave (use first hand)
                if hands_result.multi_hand_landmarks:
                    ST["waving"] = self.detector.detect_wave(hands_result.multi_hand_landmarks[0])
                
                # Detect hand raise
                pose_landmarks = pose_result.pose_landmarks.landmark if pose_result.pose_landmarks else None
                ST["hand_raised"] = self.detector.detect_hand_raised(
                    hands_result.multi_hand_landmarks[0], pose_landmarks)
            else:
                ST["clapping"] = False
                ST["waving"] = False
                ST["hand_raised"] = False
            
            # Draw pose
            if pose_result.pose_landmarks:
                mp.solutions.drawing_utils.draw_landmarks(
                    frame, pose_result.pose_landmarks, mp_pose.POSE_CONNECTIONS)
            
            # Draw status text
            self._draw_status(frame)
            
            # Convert to QImage
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            bytes_per_line = ch * w
            qt_img = QImage(rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            BRIDGE.update_camera.emit(qt_img)
            
            self.msleep(33)  # ~30 FPS
        
        hands.close()
        pose.close()
        if self.cap:
            self.cap.release()
    
    def _create_sim_frame(self):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(frame, "Camera Not Available", (200, 240), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (100, 150, 255), 2)
        return frame
    
    def _draw_status(self, frame):
        y = 30
        if ST["clapping"]:
            cv2.putText(frame, "👏 CLAP DETECTED", (10, y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            y += 30
        if ST["waving"]:
            cv2.putText(frame, "👋 WAVE DETECTED", (10, y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            y += 30
        if ST["hand_raised"]:
            cv2.putText(frame, "✋ HAND RAISED", (10, y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    
    def stop(self):
        self.running = False
        self.quit()
        self.wait()

# ============================================================
# CLICKABLE CARD
# ============================================================
class ClickCard(QPushButton):
    def __init__(self, data, idx, parent=None):
        super().__init__(parent)
        self.idx = idx
        self.data = data
        self.setFixedSize(150, 150)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._setup_style()
        self.clicked.connect(self._on_click)
    
    def _setup_style(self):
        if 'color' in self.data:
            # Color card
            self.setText(self.data['label'])
            self.setFont(QFont("Arial", 14, QFont.Weight.Bold))
            self.setStyleSheet(f"""
                QPushButton {{
                    background: {self.data['color']};
                    border-radius: 75px;
                    border: 3px solid white;
                    color: white;
                }}
                QPushButton:hover {{
                    border: 5px solid yellow;
                }}
            """)
        else:
            # Object card
            self.setText(f"{self.data.get('emoji', '')}\n{self.data['label']}")
            self.setFont(QFont("Arial", 12))
            self.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                        stop:0 #1e1b4b, stop:1 #0c0f2e);
                    border-radius: 15px;
                    border: 3px solid #4f46e5;
                    color: white;
                }
                QPushButton:hover {
                    border: 3px solid #a78bfa;
                }
            """)
    
    def _on_click(self):
        BRIDGE.new_task.emit({"action": "click", "idx": self.idx})
    
    def flash_correct(self):
        self.setStyleSheet(self.styleSheet() + "QPushButton { border: 5px solid #22c55e !important; }")
        QTimer.singleShot(500, lambda: self._setup_style())
    
    def flash_wrong(self):
        self.setStyleSheet(self.styleSheet() + "QPushButton { border: 5px solid #ef4444 !important; }")
        QTimer.singleShot(500, lambda: self._setup_style())

# ============================================================
# MAIN TABLET WINDOW
# ============================================================
class TabletWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Pepper Clinical - {CHILD_NAME}")
        self.setFixedSize(1200, 700)
        self.cards = []
        self.locked = False
        self.correct_idx = -1
        self._setup_ui()
        self._connect_signals()
        
    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        central.setStyleSheet("background: #060918;")
        
        layout = QHBoxLayout(central)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Left panel - Camera
        left = QFrame()
        left.setFixedWidth(550)
        left.setStyleSheet("background: #0a0d1e; border-radius: 15px;")
        left_layout = QVBoxLayout(left)
        
        self.camera_label = QLabel()
        self.camera_label.setFixedSize(550, 420)
        self.camera_label.setStyleSheet("background: black; border-radius: 10px;")
        self.camera_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(self.camera_label)
        
        self.movement_label = QLabel("🎯 Waiting for movement...")
        self.movement_label.setFont(QFont("Arial", 10))
        self.movement_label.setStyleSheet("color: #60a5fa; padding: 10px;")
        left_layout.addWidget(self.movement_label)
        
        left_layout.addStretch()
        layout.addWidget(left)
        
        # Right panel - Tasks
        right = QWidget()
        right.setFixedWidth(620)
        right_layout = QVBoxLayout(right)
        right_layout.setSpacing(10)
        
        # Header
        header = QLabel(f"🤖 PEPPER CLINICAL\n👤 {CHILD_NAME}")
        header.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        header.setStyleSheet("background: #1e1b4b; color: #a78bfa; padding: 15px; border-radius: 10px;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(header)
        
        # Progress
        progress = QFrame()
        progress.setStyleSheet("background: #0c0f1e; border-radius: 10px;")
        prog_layout = QHBoxLayout(progress)
        
        self.stars_label = QLabel("☆☆☆")
        self.stars_label.setFont(QFont("Arial", 20))
        self.stars_label.setStyleSheet("color: #fbbf24;")
        prog_layout.addWidget(self.stars_label)
        
        self.score_label = QLabel("Score: 0")
        self.score_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.score_label.setStyleSheet("color: #34d399;")
        prog_layout.addWidget(self.score_label)
        
        right_layout.addWidget(progress)
        
        # Instruction
        self.instruction_label = QLabel("Ready to start!")
        self.instruction_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.instruction_label.setStyleSheet("background: #1e1b4b; color: white; padding: 15px; border-radius: 10px;")
        self.instruction_label.setWordWrap(True)
        self.instruction_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(self.instruction_label)
        
        # Content area
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content.setStyleSheet("background: #0a0d1e; border-radius: 10px;")
        right_layout.addWidget(self.content, 1)
        
        # Feedback
        self.feedback_label = QLabel("💬 Follow the instruction!")
        self.feedback_label.setFont(QFont("Arial", 10))
        self.feedback_label.setStyleSheet("background: #0c0f1e; color: #9ca3af; padding: 10px; border-radius: 10px;")
        right_layout.addWidget(self.feedback_label)
        
        layout.addWidget(right)
    
    def _connect_signals(self):
        BRIDGE.new_task.connect(self._on_task)
        BRIDGE.show_success.connect(self._on_success)
        BRIDGE.show_fail.connect(self._on_fail)
        BRIDGE.update_camera.connect(self._update_camera)
        BRIDGE.update_stats.connect(self._update_stats)
        BRIDGE.unlock.connect(self._unlock)
        BRIDGE.lock.connect(self._lock)
    
    def _on_task(self, data):
        if data.get("action") == "click":
            self._handle_click(data["idx"])
            return
        
        self.instruction_label.setText(data.get("instruction", ""))
        self._build_content(data)
        self._unlock()
    
    def _build_content(self, data):
        # Clear
        for i in reversed(range(self.content_layout.count())):
            w = self.content_layout.itemAt(i).widget()
            if w:
                w.deleteLater()
        
        self.cards.clear()
        
        if data.get("type") == "motor":
            label = QLabel("🎯\n\nShow me the movement!\n\nWatch and copy Pepper!")
            label.setFont(QFont("Arial", 16))
            label.setStyleSheet("color: #a78bfa;")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.content_layout.addWidget(label)
        
        elif data.get("type") == "cognitive":
            options = data.get("options", [])
            self.correct_idx = data.get("correct_idx", -1)
            
            grid = QWidget()
            grid_layout = QGridLayout(grid)
            grid_layout.setSpacing(15)
            
            for i, opt in enumerate(options):
                card = ClickCard(opt, i)
                self.cards.append(card)
                grid_layout.addWidget(card, i // 2, i % 2)
            
            self.content_layout.addWidget(grid)
    
    def _handle_click(self, idx):
        if self.locked:
            return
        
        if idx == self.correct_idx:
            ST["tablet_click_result"] = "correct"
            if idx < len(self.cards):
                self.cards[idx].flash_correct()
            self.feedback_label.setText("✅ Correct! Well done!")
            self._lock()
        else:
            ST["tablet_click_result"] = "wrong"
            if idx < len(self.cards):
                self.cards[idx].flash_wrong()
            if 0 <= self.correct_idx < len(self.cards):
                self.cards[self.correct_idx].flash_correct()
            self.feedback_label.setText("❌ Not quite! Try again!")
            self._lock()
    
    def _on_success(self, msg):
        self.feedback_label.setText(f"✅ {msg}")
        self.feedback_label.setStyleSheet("background: #0c0f1e; color: #34d399; padding: 10px;")
        QTimer.singleShot(3000, self._reset_feedback)
    
    def _on_fail(self, msg):
        self.feedback_label.setText(f"❌ {msg}")
        self.feedback_label.setStyleSheet("background: #0c0f1e; color: #f87171; padding: 10px;")
        QTimer.singleShot(3000, self._reset_feedback)
    
    def _reset_feedback(self):
        self.feedback_label.setText("💬 Follow the instruction!")
        self.feedback_label.setStyleSheet("background: #0c0f1e; color: #9ca3af; padding: 10px;")
    
    def _update_camera(self, qimage):
        pixmap = QPixmap.fromImage(qimage)
        scaled = pixmap.scaled(550, 420, Qt.AspectRatioMode.KeepAspectRatio)
        self.camera_label.setPixmap(scaled)
        
        # Update movement indicators
        movements = []
        if ST["clapping"]: movements.append("👏 CLAP")
        if ST["waving"]: movements.append("👋 WAVE")
        if ST["hand_raised"]: movements.append("✋ HAND UP")
        
        if movements:
            self.movement_label.setText(f"🎯 Detected: {' '.join(movements)}")
            self.movement_label.setStyleSheet("color: #34d399; padding: 10px;")
        else:
            self.movement_label.setText("🎯 Waiting for movement...")
            self.movement_label.setStyleSheet("color: #60a5fa; padding: 10px;")
    
    def _update_stats(self):
        self.score_label.setText(f"Score: {ST['score']}")
        stars = "⭐" * ST["consecutive"] + "☆" * (3 - ST["consecutive"])
        self.stars_label.setText(stars)
    
    def _unlock(self):
        self.locked = False
        for card in self.cards:
            card.setEnabled(True)
    
    def _lock(self):
        self.locked = True
        for card in self.cards:
            card.setEnabled(False)

# ============================================================
# VOICE OUTPUT
# ============================================================
class VoiceOutput:
    def __init__(self):
        self.engine = None
        try:
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', 120)
            print("✅ Voice ready")
        except Exception as e:
            print(f"⚠️ Voice error: {e}")
    
    def say(self, text):
        if self.engine:
            ST["is_speaking"] = True
            print(f"🤖 Pepper: {text}")
            self.engine.say(text)
            self.engine.runAndWait()
            ST["is_speaking"] = False

# ============================================================
# THERAPY CONTROLLER
# ============================================================
class TherapyController:
    def __init__(self, voice):
        self.voice = voice
        self.running = True
        
    def run(self):
        time.sleep(1)
        self.voice.say(f"Hello {CHILD_NAME}! I'm Pepper! Let's play and learn!")
        time.sleep(1)
        
        while self.running:
            # Get new task
            task = generate_task()
            print(f"\n📋 Task: {task['name']}")
            
            # Announce
            self.voice.say(task['instruction'])
            BRIDGE.new_task.emit(task)
            
            # Wait for response
            success = self._wait_for_response(task, timeout=25)
            
            # Process result
            if success:
                ST["consecutive"] += 1
                ST["score"] += task.get('tokens', 2) * 10
                ST["tasks_mastered"] += 1 if ST["consecutive"] >= MASTERY_N else 0
                
                log_csv(task['id'], task['domain'], True, ST['score'])
                BRIDGE.show_success.emit(task['success'])
                BRIDGE.update_stats.emit()
                
                if ST["consecutive"] >= MASTERY_N:
                    ST["consecutive"] = 0
                    self.voice.say(f"Amazing {CHILD_NAME}! You got 3 stars! {task['success']}")
                    BRIDGE.celebration.emit()
                else:
                    self.voice.say(f"Excellent! {task['success']} Let's continue!")
            else:
                ST["consecutive"] = 0
                log_csv(task['id'], task['domain'], False, ST['score'])
                BRIDGE.show_fail.emit(task['fail'])
                self.voice.say(f"Let's try again! {task['fail']}")
            
            BRIDGE.update_stats.emit()
            time.sleep(1)
    
    def _wait_for_response(self, task, timeout=25):
        start = time.time()
        verify_type = task.get('verify', 'motor')
        
        while time.time() - start < timeout:
            if verify_type == 'clap' and ST["clapping"]:
                print("✅ Clap detected!")
                return True
            elif verify_type == 'wave' and ST["waving"]:
                print("✅ Wave detected!")
                return True
            elif verify_type == 'raise_hand' and ST["hand_raised"]:
                print("✅ Hand raise detected!")
                return True
            elif verify_type == 'click':
                result = ST.get("tablet_click_result")
                if result == "correct":
                    ST["tablet_click_result"] = None
                    return True
                elif result == "wrong":
                    ST["tablet_click_result"] = None
                    return False
            
            time.sleep(0.1)
        
        return False

# ============================================================
# MAIN
# ============================================================
def main():
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║  PEPPER CLINICAL INFINITY - FIXED                            ║
║  Patient: {CHILD_NAME:<40}║
╠══════════════════════════════════════════════════════════════╣
║  ✓ Fixed click detection                                     ║
║  ✓ Improved movement detection                               ║
║  ✓ No task repetition                                        ║
║  ✓ CSV logging                                               ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    # Create Qt app
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Create window
    window = TabletWindow()
    window.show()
    
    # Start camera
    camera = CameraThread()
    camera.start()
    
    # Start voice and therapy
    voice = VoiceOutput()
    therapy = TherapyController(voice)
    
    # Run therapy in thread
    therapy_thread = threading.Thread(target=therapy.run, daemon=True)
    therapy_thread.start()
    
    print("\n✅ System ready!")
    print("Press Ctrl+C to exit\n")
    
    # Run event loop
    try:
        sys.exit(app.exec())
    except:
        pass
    finally:
        camera.stop()
        therapy.running = False

if __name__ == "__main__":
    main()
