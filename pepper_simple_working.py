#!/usr/bin/env python3
"""
PEPPER CLINICAL - SIMPLE WORKING VERSION
- Counting tasks with fruits (visual)
- Click buttons to answer
- Voice feedback
- Balloons on correct answers
- Auto-advance
"""

import os
import sys
import time
import random
import csv
from datetime import datetime

os.environ['QT_QPA_PLATFORM'] = 'xcb'

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

import pyttsx3

print("✅ Libraries loaded")

# ============================================================
# CONFIGURATION
# ============================================================
print("\n" + "="*64)
print("  PEPPER CLINICAL")
print("="*64)
CHILD_NAME = input("\n👦 Enter Child's Name: ").strip() or "Child"
CSV_FILE = f"{CHILD_NAME.replace(' ', '_')}_Results.csv"

with open(CSV_FILE, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(["Time", "Child", "Task", "Result", "Score", "Stars"])

# ============================================================
# TASKS
# ============================================================
FRUITS = ["🍎", "🍌", "🍊", "🍇", "🍓", "🍒", "🥝", "🥭"]

def generate_task():
    """Generate a counting task"""
    number = random.choice([2, 3, 4, 5])
    fruit = random.choice(FRUITS)
    options = [number, number+1, number-1]
    options = [max(1, min(10, x)) for x in options]
    random.shuffle(options)
    correct_idx = options.index(number)
    
    return {
        "id": f"count_{number}",
        "fruit": fruit,
        "target": number,
        "options": options,
        "correct": correct_idx,
        "instruction": f"How many {fruit}?",
        "success": f"Correct! {number} {fruit}!"
    }

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
        colors = ["#ef4444", "#3b82f6", "#22c55e", "#fbbf24", "#a855f7", "#ec4899"]
        
        for _ in range(15):
            self.balloons.append({
                "x": random.randint(50, self.width() - 50),
                "y": self.height() - random.randint(20, 100),
                "vx": random.uniform(-2, 2),
                "vy": random.uniform(-8, -5),
                "color": random.choice(colors),
                "r": random.randint(25, 45),
                "emoji": random.choice(["🎈", "🎉", "⭐", "🌟", "🎊"])
            })
        
        self.show()
        self.timer.start(30)
        QTimer.singleShot(3500, self.stop)
    
    def update_animation(self):
        for b in self.balloons:
            b["x"] += b["vx"]
            b["y"] += b["vy"]
            b["vy"] *= 0.98
        
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
                           int(b["x"]), int(b["y"] + b["r"] + 15))
            
            painter.setFont(QFont("Arial", b["r"] // 2))
            painter.drawText(int(b["x"] - b["r"] // 2), int(b["y"] + b["r"] // 3), b["emoji"])
        
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
        self.count = count
        self.idx = idx
        
        # Create display with fruits
        fruits_display = fruit * count
        self.setText(f"{fruits_display}\n{count}")
        self.setFont(QFont("Arial", 20))
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
        self.setFixedSize(1100, 750)
        
        self.current_task = None
        self.score = 0
        self.consecutive = 0
        self.mastered = 0
        self.locked = False
        self.buttons = []
        
        self.setup_ui()
        self.start_session()
    
    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        central.setStyleSheet("background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #0a0a1a,stop:1 #0f0f2a);")
        
        layout = QVBoxLayout(central)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 20, 30, 20)
        
        # Header
        header = QFrame()
        header.setStyleSheet("background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #1a0a3d,stop:1 #0a0f28); border-radius: 20px; border: 2px solid #4f46e5;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 10, 20, 10)
        
        pepper = QLabel("🤖")
        pepper.setFont(QFont("Arial", 40))
        header_layout.addWidget(pepper)
        
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
        
        self.stars = QLabel("☆☆☆")
        self.stars.setFont(QFont("Arial", 24))
        self.stars.setStyleSheet("color: #fbbf24; background: #1e1b4b; padding: 5px 20px; border-radius: 15px;")
        header_layout.addWidget(self.stars)
        
        layout.addWidget(header)
        
        # Instruction
        instr_frame = QFrame()
        instr_frame.setStyleSheet("background: #1e1b4b; border-radius: 15px; border: 2px solid #4f46e5;")
        instr_layout = QVBoxLayout(instr_frame)
        instr_layout.setContentsMargins(20, 20, 20, 20)
        
        self.instruction = QLabel("Getting ready...")
        self.instruction.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        self.instruction.setStyleSheet("color: #e0e6ff;")
        self.instruction.setAlignment(Qt.AlignmentFlag.AlignCenter)
        instr_layout.addWidget(self.instruction)
        
        layout.addWidget(instr_frame)
        
        # Content (buttons)
        self.content_frame = QFrame()
        self.content_frame.setStyleSheet("background: #0c0f1e; border-radius: 20px; border: 2px solid #1a1f40;")
        self.content_layout = QVBoxLayout(self.content_frame)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.content_frame, 1)
        
        # Feedback
        feedback_frame = QFrame()
        feedback_frame.setStyleSheet("background: #0c0f1e; border-radius: 15px;")
        feedback_layout = QHBoxLayout(feedback_frame)
        feedback_layout.setContentsMargins(20, 10, 20, 10)
        
        self.feedback_icon = QLabel("💤")
        self.feedback_icon.setFont(QFont("Arial", 24))
        feedback_layout.addWidget(self.feedback_icon)
        
        self.feedback = QLabel("Ready...")
        self.feedback.setFont(QFont("Arial", 14))
        self.feedback.setStyleSheet("color: #9ca3af;")
        feedback_layout.addWidget(self.feedback, 1)
        
        layout.addWidget(feedback_frame)
        
        # Progress
        self.progress = QProgressBar()
        self.progress.setFixedHeight(8)
        self.progress.setStyleSheet("""
            QProgressBar { background: #1e1b4b; border-radius: 4px; }
            QProgressBar::chunk { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #4f46e5,stop:1 #a78bfa); border-radius: 4px; }
        """)
        layout.addWidget(self.progress)
        
        # Stats
        stats_bar = QFrame()
        stats_bar.setStyleSheet("background: #07090f; border-radius: 15px;")
        stats_layout = QHBoxLayout(stats_bar)
        stats_layout.setContentsMargins(20, 10, 20, 10)
        
        self.score_label = QLabel(f"🏆 Score: 0")
        self.score_label.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        self.score_label.setStyleSheet("color: #fbbf24;")
        stats_layout.addWidget(self.score_label)
        
        self.mastered_label = QLabel(f"⭐ Mastered: 0")
        self.mastered_label.setFont(QFont("Arial", 12))
        self.mastered_label.setStyleSheet("color: #34d399;")
        stats_layout.addWidget(self.mastered_label)
        
        layout.addWidget(stats_bar)
        
        # Balloons
        self.balloons = BalloonWidget(central)
    
    def start_session(self):
        QTimer.singleShot(500, self.greet)
    
    def greet(self):
        voice.say(f"Hello {CHILD_NAME}! I am Pepper. Let's count fruits!")
        QTimer.singleShot(2500, self.next_task)
    
    def next_task(self):
        self.current_task = generate_task()
        
        self.instruction.setText(self.current_task["instruction"])
        self.feedback.setText("Click the correct answer!")
        self.feedback.setStyleSheet("color: #60a5fa;")
        self.feedback_icon.setText("🎯")
        
        self.clear_buttons()
        self.create_buttons()
        
        # Timeout
        if hasattr(self, 'task_timer'):
            self.task_timer.stop()
        self.task_timer = QTimer()
        self.task_timer.setSingleShot(True)
        self.task_timer.timeout.connect(self.timeout)
        self.task_timer.start(15000)
        
        # Progress animation
        self.progress.setValue(0)
        self.progress_anim = QPropertyAnimation(self.progress, b"value")
        self.progress_anim.setDuration(15000)
        self.progress_anim.setStartValue(0)
        self.progress_anim.setEndValue(100)
        self.progress_anim.start()
        
        self.locked = False
        voice.say(self.current_task["instruction"])
    
    def create_buttons(self):
        task = self.current_task
        fruit = task["fruit"]
        options = task["options"]
        
        grid = QWidget()
        grid_layout = QGridLayout(grid)
        grid_layout.setSpacing(20)
        grid_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        for i, count in enumerate(options):
            btn = FruitButton(fruit, count, i)
            btn.clicked.connect(lambda checked, idx=i: self.check_answer(idx))
            self.buttons.append(btn)
            grid_layout.addWidget(btn, i//2, i%2)
        
        self.content_layout.addWidget(grid)
    
    def check_answer(self, idx):
        if self.locked:
            return
        
        self.locked = True
        
        if hasattr(self, 'task_timer'):
            self.task_timer.stop()
        if hasattr(self, 'progress_anim'):
            self.progress_anim.stop()
        
        if idx == self.current_task["correct"]:
            # Success
            points = 15
            self.score += points
            self.consecutive += 1
            
            # Flash correct button
            for btn in self.buttons:
                if btn.idx == idx:
                    btn.flash_correct()
            
            self.feedback.setText(f"✅ CORRECT! +{points} points!")
            self.feedback.setStyleSheet("color: #34d399;")
            self.feedback_icon.setText("✅")
            self.score_label.setText(f"🏆 Score: {self.score}")
            
            # Update stars
            stars = "⭐" * self.consecutive + "☆" * (3 - self.consecutive)
            self.stars.setText(stars)
            
            # Launch balloons
            self.balloons.launch()
            
            # Log
            with open(CSV_FILE, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    datetime.now().strftime("%H:%M:%S"),
                    CHILD_NAME,
                    f"Count {self.current_task['target']}",
                    "SUCCESS",
                    self.score,
                    self.consecutive
                ])
            
            # Mastery
            if self.consecutive >= 3:
                self.consecutive = 0
                self.mastered += 1
                self.mastered_label.setText(f"⭐ Mastered: {self.mastered}")
                voice.say(f"AMAZING! You mastered counting! +{points} points!")
            else:
                voice.say(self.current_task["success"])
            
            QTimer.singleShot(2000, self.next_task)
        else:
            # Fail
            self.consecutive = 0
            
            # Show correct answer
            for btn in self.buttons:
                if btn.idx == self.current_task["correct"]:
                    btn.flash_correct()
                if btn.idx == idx:
                    btn.flash_wrong()
            
            self.feedback.setText(f"❌ Oops! The answer was {self.current_task['target']}")
            self.feedback.setStyleSheet("color: #f87171;")
            self.feedback_icon.setText("❌")
            self.stars.setText("☆☆☆")
            
            # Log
            with open(CSV_FILE, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    datetime.now().strftime("%H:%M:%S"),
                    CHILD_NAME,
                    f"Count {self.current_task['target']}",
                    "FAIL",
                    self.score,
                    0
                ])
            
            voice.say(f"That's okay! The answer was {self.current_task['target']}")
            QTimer.singleShot(2000, self.next_task)
    
    def timeout(self):
        if self.locked:
            return
        
        self.locked = True
        self.consecutive = 0
        
        # Show correct answer
        for btn in self.buttons:
            if btn.idx == self.current_task["correct"]:
                btn.flash_correct()
        
        self.feedback.setText(f"⏰ Time's up! Answer: {self.current_task['target']}")
        self.feedback.setStyleSheet("color: #f59e0b;")
        self.feedback_icon.setText("⏰")
        self.stars.setText("☆☆☆")
        
        # Log
        with open(CSV_FILE, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().strftime("%H:%M:%S"),
                CHILD_NAME,
                f"Count {self.current_task['target']}",
                "TIMEOUT",
                self.score,
                0
            ])
        
        voice.say(f"Time's up! The answer was {self.current_task['target']}")
        QTimer.singleShot(2000, self.next_task)
    
    def clear_buttons(self):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.buttons.clear()
    
    def closeEvent(self, event):
        duration = int((time.time() - getattr(self, 'start_time', time.time())) / 60)
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
║  PEPPER CLINICAL - WORKING VERSION                           ║
╠══════════════════════════════════════════════════════════════╣
║  ✓ Counting fruits (2-5 items)                             ║
║  ✓ Visual fruit display                                    ║
║  ✓ Click to answer                                         ║
║  ✓ Balloons on correct answer                              ║
║  ✓ Voice feedback                                          ║
║  ✓ 15 second timeout                                       ║
║  ✓ 3 correct = Mastery                                     ║
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
