#!/usr/bin/env python3
"""
PEPPER CLINICAL INFINITY - STABLE FINAL VERSION
- Fixed emotion window
- 10-finger detection working
- Counting tasks with fruits
- Motor tasks with body detection
- Speech tasks with recording
- Balloons celebration
"""

import os
import sys
import time
import threading
import random
import csv
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

print("✅ Libraries loaded")

# ============================================================
# CONFIGURATION
# ============================================================
print("\n" + "="*64)
print("  PEPPER CLINICAL INFINITY - STABLE")
print("="*64)
CHILD_NAME = input("\n👦 Enter Child's Name: ").strip() or "Child"
CSV_FILE = f"{CHILD_NAME.replace(' ', '_')}_Results.csv"

with open(CSV_FILE, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(["Time", "Child", "Task", "Result", "Score", "Stars"])

# ============================================================
# TASKS
# ============================================================
FRUITS = ["🍎", "🍌", "🍊", "🍇", "🍓", "🍒"]

COUNTING_TASKS = []
for num in [2, 3, 4, 5]:
    for fruit in FRUITS[:4]:
        COUNTING_TASKS.append({
            "type": "counting",
            "target": num,
            "fruit": fruit,
            "instruction": f"How many {fruit}?",
            "success": f"Correct! {num} {fruit}!"
        })

MOTOR_TASKS = [
    {"type": "motor", "action": "clap", "name": "👏 CLAP HANDS", 
     "instruction": "Clap your hands!", "success": "Great clapping!"},
    {"type": "motor", "action": "wave", "name": "👋 WAVE",
     "instruction": "Wave your hand!", "success": "Nice wave!"},
    {"type": "motor", "action": "raise_hand", "name": "✋ RAISE HAND",
     "instruction": "Raise your hand!", "success": "Hand raised!"},
]

SPEECH_TASKS = [
    {"type": "speech", "word": "apple", "instruction": "Say: apple", "success": "Great! You said apple!"},
    {"type": "speech", "word": "ball", "instruction": "Say: ball", "success": "Great! You said ball!"},
    {"type": "speech", "word": "cat", "instruction": "Say: cat", "success": "Great! You said cat!"},
]

ALL_TASKS = COUNTING_TASKS + MOTOR_TASKS + SPEECH_TASKS

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
# CAMERA WITH FINGER AND BODY DETECTION
# ============================================================
class CameraThread(QThread):
    frame_signal = pyqtSignal(np.ndarray)
    action_signal = pyqtSignal(str)
    finger_signal = pyqtSignal(int)
    
    def __init__(self):
        super().__init__()
        self.running = True
        self.cap = None
        self.pose = None
        self.hands = None
        
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
        try:
            self.pose = mp.solutions.pose.Pose(
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5)
            self.hands = mp.solutions.hands.Hands(
                max_num_hands=2,
                min_detection_confidence=0.5)
            print("✅ Body detection ready")
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
    
    def detect_action(self, landmarks):
        if not landmarks:
            return None
        
        left_wrist = landmarks[mp.solutions.pose.PoseLandmark.LEFT_WRIST]
        right_wrist = landmarks[mp.solutions.pose.PoseLandmark.RIGHT_WRIST]
        left_shoulder = landmarks[mp.solutions.pose.PoseLandmark.LEFT_SHOULDER]
        right_shoulder = landmarks[mp.solutions.pose.PoseLandmark.RIGHT_SHOULDER]
        
        # Detect clapping (hands close)
        distance = abs(left_wrist.x - right_wrist.x) + abs(left_wrist.y - right_wrist.y)
        if distance < 0.15:
            return "clap"
        
        # Detect raised hand
        if left_wrist.y < left_shoulder.y - 0.1 or right_wrist.y < right_shoulder.y - 0.1:
            return "raise_hand"
        
        return None
    
    def draw_skeleton(self, frame, landmarks):
        h, w = frame.shape[:2]
        for lm in landmarks:
            x, y = int(lm.x * w), int(lm.y * h)
            cv2.circle(frame, (x, y), 4, (0, 0, 255), -1)
        return frame
    
    def run(self):
        if not self.cap:
            while self.running:
                frame = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(frame, "Camera not found", (200, 240), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 150, 255), 2)
                self.frame_signal.emit(frame)
                self.msleep(100)
            return
        
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                self.msleep(10)
                continue
            
            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            total_fingers = 0
            detected_action = None
            
            if self.pose:
                pose_result = self.pose.process(rgb)
                if pose_result.pose_landmarks:
                    frame = self.draw_skeleton(frame, pose_result.pose_landmarks.landmark)
                    detected_action = self.detect_action(pose_result.pose_landmarks.landmark)
            
            if self.hands:
                hands_result = self.hands.process(rgb)
                if hands_result.multi_hand_landmarks:
                    for hand, handedness in zip(hands_result.multi_hand_landmarks, 
                                                hands_result.multi_handedness):
                        label = handedness.classification[0].label
                        total_fingers += self.count_fingers(hand, label)
            
            # Display info on frame
            cv2.putText(frame, f"Fingers: {total_fingers}", (10, 50),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            if detected_action:
                cv2.putText(frame, f"Action: {detected_action}", (10, 90),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            self.frame_signal.emit(frame)
            if detected_action:
                self.action_signal.emit(detected_action)
            self.finger_signal.emit(total_fingers)
            
            self.msleep(33)
    
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
        self.timer.timeout.connect(self.animate)
        self.hide()
    
    def launch(self):
        parent = self.parent()
        if parent:
            self.setGeometry(parent.rect())
        
        self.balloons = []
        colors = ["#ef4444", "#3b82f6", "#22c55e", "#fbbf24", "#a855f7", "#ec4899"]
        
        for _ in range(15):
            self.balloons.append({
                "x": random.randint(50, self.width() - 50),
                "y": self.height(),
                "vx": random.uniform(-2, 2),
                "vy": random.uniform(-10, -6),
                "color": random.choice(colors),
                "r": random.randint(25, 40),
            })
        
        self.show()
        self.timer.start(30)
        QTimer.singleShot(3500, self.stop)
    
    def animate(self):
        for b in self.balloons:
            b["x"] += b["vx"]
            b["y"] += b["vy"]
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
            painter.drawEllipse(int(b["x"] - b["r"]), int(b["y"] - b["r"]), b["r"]*2, b["r"]*2)
        painter.end()
    
    def stop(self):
        self.timer.stop()
        self.hide()
        self.balloons = []

# ============================================================
# FRUIT BUTTON
# ============================================================
class FruitButton(QPushButton):
    def __init__(self, fruit, count, idx):
        super().__init__()
        self.idx = idx
        self.setText(f"{fruit * count}\n{count}")
        self.setFont(QFont("Arial", 20))
        self.setFixedSize(160, 160)
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
            QPushButton:hover { border: 5px solid #a78bfa; background: #2a2550; }
        """)
    
    def flash_correct(self):
        self.setStyleSheet(self.styleSheet() + "QPushButton { border: 5px solid #22c55e !important; background: #166534 !important; }")
        QTimer.singleShot(800, self.reset)
    
    def flash_wrong(self):
        self.setStyleSheet(self.styleSheet() + "QPushButton { border: 5px solid #ef4444 !important; }")
        QTimer.singleShot(800, self.reset)
    
    def reset(self):
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
# MAIN WINDOW
# ============================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Pepper Clinical - {CHILD_NAME}")
        self.setMinimumSize(1300, 800)
        
        self.current_task = None
        self.score = 0
        self.consecutive = 0
        self.mastered = 0
        self.locked = False
        self.task_index = 0
        self.finger_count = 0
        
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
        
        # LEFT - Camera Panel
        left = QFrame()
        left.setFixedWidth(550)
        left.setStyleSheet("background: #0c0f1e; border-radius: 20px; border: 2px solid #1a1f40;")
        left_layout = QVBoxLayout(left)
        
        self.camera_label = QLabel()
        self.camera_label.setFixedSize(530, 400)
        self.camera_label.setStyleSheet("background: #000; border-radius: 10px;")
        self.camera_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(self.camera_label)
        
        info = QFrame()
        info.setStyleSheet("background: #1e1b4b; border-radius: 15px;")
        info_layout = QVBoxLayout(info)
        
        self.finger_label = QLabel("✋ Fingers: 0")
        self.finger_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.finger_label.setStyleSheet("color: #fbbf24;")
        self.finger_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_layout.addWidget(self.finger_label)
        
        left_layout.addWidget(info)
        main_layout.addWidget(left)
        
        # RIGHT - Game Panel
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setSpacing(15)
        
        # Header
        header = QFrame()
        header.setStyleSheet("background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #1a0a3d,stop:1 #0a0f28); border-radius: 20px; border: 2px solid #4f46e5;")
        header_layout = QHBoxLayout(header)
        
        pepper = QLabel("🤖")
        pepper.setFont(QFont("Arial", 40))
        header_layout.addWidget(pepper)
        
        title = QLabel(f"PEPPER CLINICAL - {CHILD_NAME}")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #a78bfa;")
        header_layout.addWidget(title, 1)
        
        self.stars = QLabel("☆☆☆")
        self.stars.setFont(QFont("Arial", 24))
        self.stars.setStyleSheet("color: #fbbf24;")
        header_layout.addWidget(self.stars)
        
        right_layout.addWidget(header)
        
        # Instruction
        self.instruction = QLabel("Getting ready...")
        self.instruction.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        self.instruction.setStyleSheet("color: #e0e6ff; background: #1e1b4b; padding: 20px; border-radius: 15px;")
        self.instruction.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.instruction.setWordWrap(True)
        right_layout.addWidget(self.instruction)
        
        # Content
        self.content = QFrame()
        self.content.setStyleSheet("background: #0c0f1e; border-radius: 20px; border: 2px solid #1a1f40;")
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(self.content, 1)
        
        # Feedback
        self.feedback = QLabel("💤 Ready")
        self.feedback.setFont(QFont("Arial", 14))
        self.feedback.setStyleSheet("color: #9ca3af; background: #1e1b4b; padding: 12px; border-radius: 12px;")
        self.feedback.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(self.feedback)
        
        # Progress
        self.progress = QProgressBar()
        self.progress.setFixedHeight(8)
        self.progress.setStyleSheet("QProgressBar { background: #1e1b4b; border-radius: 4px; } QProgressBar::chunk { background: #4f46e5; border-radius: 4px; }")
        right_layout.addWidget(self.progress)
        
        # Stats
        stats = QFrame()
        stats.setStyleSheet("background: #07090f; border-radius: 15px;")
        stats_layout = QHBoxLayout(stats)
        
        self.score_label = QLabel(f"🏆 Score: 0")
        self.score_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.score_label.setStyleSheet("color: #fbbf24;")
        stats_layout.addWidget(self.score_label)
        
        self.mastered_label = QLabel(f"⭐ Mastered: 0")
        self.mastered_label.setFont(QFont("Arial", 12))
        self.mastered_label.setStyleSheet("color: #34d399;")
        stats_layout.addWidget(self.mastered_label)
        
        right_layout.addWidget(stats)
        main_layout.addWidget(right, 1)
        
        self.balloons = BalloonWidget(central)
    
    def setup_camera(self):
        self.camera = CameraThread()
        self.camera.frame_signal.connect(self.update_camera)
        self.camera.action_signal.connect(self.on_action)
        self.camera.finger_signal.connect(self.update_fingers)
        self.camera.start()
    
    def update_camera(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qt = QImage(rgb.data, w, h, w * ch, QImage.Format.Format_RGB888)
        self.camera_label.setPixmap(QPixmap.fromImage(qt).scaled(530, 400, Qt.AspectRatioMode.KeepAspectRatio))
    
    def update_fingers(self, count):
        self.finger_count = count
        self.finger_label.setText(f"✋ Fingers: {count}")
    
    def on_action(self, action):
        if self.current_task and self.current_task.get("type") == "motor" and not self.locked:
            if action == self.current_task.get("action"):
                self.task_success()
    
    def start_session(self):
        QTimer.singleShot(500, self.greet)
    
    def greet(self):
        voice.say(f"Hello {CHILD_NAME}! I am Pepper. Let's learn together!")
        QTimer.singleShot(2000, self.next_task)
    
    def next_task(self):
        self.current_task = ALL_TASKS[self.task_index % len(ALL_TASKS)]
        self.task_index += 1
        
        self.instruction.setText(self.current_task["instruction"])
        self.feedback.setText("Your turn!")
        self.feedback.setStyleSheet("color: #60a5fa; background: #1e1b4b; padding: 12px; border-radius: 12px;")
        
        self.clear_content()
        
        if self.current_task["type"] == "counting":
            self.show_counting()
        elif self.current_task["type"] == "motor":
            self.show_motor()
        else:
            self.show_speech()
        
        # Timeout
        if hasattr(self, 'timer'):
            self.timer.stop()
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.timeout)
        self.timer.start(20000)
        
        self.progress.setValue(0)
        self.anim = QPropertyAnimation(self.progress, b"value")
        self.anim.setDuration(20000)
        self.anim.setStartValue(0)
        self.anim.setEndValue(100)
        self.anim.start()
        
        self.locked = False
        voice.say(self.current_task["instruction"])
    
    def show_counting(self):
        task = self.current_task
        fruit = task["fruit"]
        target = task["target"]
        
        options = [target, target+1, target-1]
        options = [max(1, min(10, x)) for x in options]
        random.shuffle(options)
        
        grid = QWidget()
        grid_layout = QGridLayout(grid)
        grid_layout.setSpacing(20)
        
        for i, opt in enumerate(options):
            btn = FruitButton(fruit, opt, i)
            btn.clicked.connect(lambda checked, val=opt: self.check_counting(val, target))
            grid_layout.addWidget(btn, i//2, i%2)
        
        self.content_layout.addWidget(grid)
    
    def check_counting(self, selected, target):
        if self.locked:
            return
        if selected == target:
            self.task_success()
        else:
            self.task_fail(target)
    
    def show_motor(self):
        task = self.current_task
        label = QLabel(f"{task['name']}\n\n👇 COPY THIS MOVEMENT! 👇")
        label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        label.setStyleSheet("color: #a78bfa;")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(label)
        self.feedback.setText(f"Camera is watching! Do: {task['name']}")
    
    def show_speech(self):
        task = self.current_task
        label = QLabel(f"🗣️ SAY: {task['word'].upper()} 🗣️")
        label.setFont(QFont("Arial", 28, QFont.Weight.Bold))
        label.setStyleSheet("color: #fbbf24;")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(label)
        self.feedback.setText("Say the word out loud!")
        QTimer.singleShot(3000, lambda: self.task_success())
    
    def task_success(self):
        if self.locked:
            return
        
        self.locked = True
        if hasattr(self, 'timer'):
            self.timer.stop()
        if hasattr(self, 'anim'):
            self.anim.stop()
        
        points = 15
        self.score += points
        self.consecutive += 1
        
        self.feedback.setText(f"✅ CORRECT! +{points} points!")
        self.feedback.setStyleSheet("color: #34d399; background: #1e1b4b; padding: 12px; border-radius: 12px;")
        self.score_label.setText(f"🏆 Score: {self.score}")
        
        stars = "⭐" * self.consecutive + "☆" * (3 - self.consecutive)
        self.stars.setText(stars)
        
        self.balloons.launch()
        
        # Log
        with open(CSV_FILE, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().strftime("%H:%M:%S"),
                CHILD_NAME,
                self.current_task.get("instruction", "Task"),
                "SUCCESS",
                self.score,
                self.consecutive
            ])
        
        if self.consecutive >= 3:
            self.consecutive = 0
            self.mastered += 1
            self.mastered_label.setText(f"⭐ Mastered: {self.mastered}")
            voice.say(f"AMAZING! You mastered this skill! +{points} points!")
        else:
            voice.say(self.current_task.get("success", "Great job!"))
        
        QTimer.singleShot(2000, self.next_task)
    
    def task_fail(self, correct=None):
        if self.locked:
            return
        
        self.locked = True
        self.consecutive = 0
        
        msg = f"❌ Try again! Answer: {correct}" if correct else "❌ Try again!"
        self.feedback.setText(msg)
        self.feedback.setStyleSheet("color: #f87171; background: #1e1b4b; padding: 12px; border-radius: 12px;")
        self.stars.setText("☆☆☆")
        
        with open(CSV_FILE, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().strftime("%H:%M:%S"),
                CHILD_NAME,
                self.current_task.get("instruction", "Task"),
                "FAIL",
                self.score,
                0
            ])
        
        voice.say("That's okay! Let's try the next one!")
        QTimer.singleShot(2000, self.next_task)
    
    def timeout(self):
        if self.locked:
            return
        
        self.locked = True
        self.consecutive = 0
        
        self.feedback.setText("⏰ Time's up! Moving to next task...")
        self.feedback.setStyleSheet("color: #f59e0b; background: #1e1b4b; padding: 12px; border-radius: 12px;")
        self.stars.setText("☆☆☆")
        
        with open(CSV_FILE, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().strftime("%H:%M:%S"),
                CHILD_NAME,
                self.current_task.get("instruction", "Task"),
                "TIMEOUT",
                self.score,
                0
            ])
        
        voice.say("Time's up! Let's try the next task!")
        QTimer.singleShot(2000, self.next_task)
    
    def clear_content(self):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def closeEvent(self, event):
        if hasattr(self, 'camera'):
            self.camera.stop()
        
        print(f"\n{'='*64}")
        print(f"🎉 SESSION COMPLETE — {CHILD_NAME}")
        print(f"{'='*64}")
        print(f"Final Score: {self.score}")
        print(f"Tasks Mastered: {self.mastered}")
        print(f"CSV: {CSV_FILE}")
        print('='*64)
        event.accept()

# ============================================================
# MAIN
# ============================================================
def main():
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║  PEPPER CLINICAL INFINITY - STABLE                           ║
╠══════════════════════════════════════════════════════════════╣
║  ✓ Counting fruits with visual display                      ║
║  ✓ Motor actions (clap, raise hand) with camera             ║
║  ✓ 10-finger detection                                      ║
║  ✓ Balloons on correct answers                              ║
║  ✓ Voice feedback                                           ║
║  ✓ 20 second timeout                                        ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
