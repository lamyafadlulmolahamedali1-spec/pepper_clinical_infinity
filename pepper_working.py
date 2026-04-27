#!/usr/bin/env python3
"""
PEPPER CLINICAL - WORKING VERSION
- Reliable click tasks (colors, animals, numbers)
- Simple UI with no threading issues
- Auto-advance on timeout
- CSV logging
- Pepper voice feedback
"""

import os
import sys
import time
import threading
import random
import csv
from datetime import datetime

os.environ['QT_QPA_PLATFORM'] = 'xcb'

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

try:
    import pyttsx3
    TTS_OK = True
except:
    TTS_OK = False
    print("⚠️ TTS not available")

# ============================================================
# CONFIG
# ============================================================
print("\n" + "="*64)
print("  PEPPER CLINICAL - WORKING VERSION")
print("="*64)
CHILD_NAME = input("\n👦 Enter Child's Name: ").strip() or "Child"
CSV_FILE = f"{CHILD_NAME.replace(' ', '_')}_Results.csv"

with open(CSV_FILE, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(["Timestamp", "Child", "Task", "Result", "Score", "Stars"])

# ============================================================
# TASKS - All click-based for reliability
# ============================================================
TASKS = [
    # Colors
    {"id": "red", "name": "🔴 RED", "instruction": "Click the RED button!", "type": "color", 
     "target": "red", "options": ["red", "blue", "green", "yellow"], "tokens": 2},
    {"id": "blue", "name": "🔵 BLUE", "instruction": "Click the BLUE button!", "type": "color",
     "target": "blue", "options": ["blue", "red", "green", "yellow"], "tokens": 2},
    {"id": "green", "name": "🟢 GREEN", "instruction": "Click the GREEN button!", "type": "color",
     "target": "green", "options": ["green", "red", "blue", "yellow"], "tokens": 2},
    {"id": "yellow", "name": "🟡 YELLOW", "instruction": "Click the YELLOW button!", "type": "color",
     "target": "yellow", "options": ["yellow", "red", "blue", "green"], "tokens": 2},
    
    # Animals
    {"id": "lion", "name": "🦁 LION", "instruction": "Click the LION!", "type": "animal",
     "target": "lion", "options": ["lion", "elephant", "monkey", "giraffe"], "tokens": 3},
    {"id": "elephant", "name": "🐘 ELEPHANT", "instruction": "Click the ELEPHANT!", "type": "animal",
     "target": "elephant", "options": ["elephant", "lion", "monkey", "giraffe"], "tokens": 3},
    {"id": "monkey", "name": "🐵 MONKEY", "instruction": "Click the MONKEY!", "type": "animal",
     "target": "monkey", "options": ["monkey", "lion", "elephant", "giraffe"], "tokens": 3},
    {"id": "giraffe", "name": "🦒 GIRAFFE", "instruction": "Click the GIRAFFE!", "type": "animal",
     "target": "giraffe", "options": ["giraffe", "lion", "elephant", "monkey"], "tokens": 3},
    
    # Numbers
    {"id": "num1", "name": "1️⃣ ONE", "instruction": "Click the number 1!", "type": "number",
     "target": 1, "options": [1, 2, 3, 4], "tokens": 3},
    {"id": "num2", "name": "2️⃣ TWO", "instruction": "Click the number 2!", "type": "number",
     "target": 2, "options": [2, 1, 3, 4], "tokens": 3},
    {"id": "num3", "name": "3️⃣ THREE", "instruction": "Click the number 3!", "type": "number",
     "target": 3, "options": [3, 1, 2, 4], "tokens": 3},
    {"id": "num4", "name": "4️⃣ FOUR", "instruction": "Click the number 4!", "type": "number",
     "target": 4, "options": [4, 1, 2, 3], "tokens": 3},
    {"id": "num5", "name": "5️⃣ FIVE", "instruction": "Click the number 5!", "type": "number",
     "target": 5, "options": [5, 1, 2, 3], "tokens": 4},
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
                    background: {color};
                    border-radius: 70px;
                    border: 3px solid white;
                    color: white;
                    font-size: 20px;
                    font-weight: bold;
                }}
                QPushButton:hover {{ border: 5px solid #fbbf24; transform: scale(1.05); }}
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
                    font-size: 18px;
                    font-weight: bold;
                }
                QPushButton:hover { border: 4px solid #a78bfa; background: #2a2550; }
            """)
    
    def flash_correct(self):
        self.setStyleSheet(self.styleSheet() + "QPushButton { border: 5px solid #22c55e !important; background: #166534 !important; }")
        QTimer.singleShot(800, self.reset_style)
    
    def flash_wrong(self):
        original = self.styleSheet()
        self.setStyleSheet(original + "QPushButton { border: 5px solid #ef4444 !important; }")
        QTimer.singleShot(800, lambda: self.setStyleSheet(original))
    
    def reset_style(self):
        if hasattr(self, '_original_style'):
            self.setStyleSheet(self._original_style)

# ============================================================
# MAIN WINDOW
# ============================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Pepper Clinical - {CHILD_NAME}")
        self.setFixedSize(1100, 750)
        
        self.buttons = []
        self.current_task = None
        self.correct_value = None
        self.locked = False
        self.task_timer = None
        self.score = 0
        self.consecutive = 0
        self.mastered = 0
        
        self.setup_ui()
        self.start_session()
    
    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        central.setStyleSheet("background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #0a0a1a,stop:1 #0f0f2a);")
        
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(25, 20, 25, 20)
        
        # Header
        header = QFrame()
        header.setStyleSheet("background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #1a0a3d,stop:1 #0a0f28); border-radius: 20px; border: 2px solid #4f46e5;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 10, 20, 10)
        
        # Pepper icon
        pepper = QLabel("🤖")
        pepper.setFont(QFont("Arial", 36))
        header_layout.addWidget(pepper)
        
        # Title
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
        
        # Stats
        stats_box = QHBoxLayout()
        self.score_label = QLabel("Score: 0")
        self.score_label.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        self.score_label.setStyleSheet("color: #fbbf24; background: #1e1b4b; padding: 5px 15px; border-radius: 15px;")
        stats_box.addWidget(self.score_label)
        
        self.stars_label = QLabel("☆☆☆")
        self.stars_label.setFont(QFont("Arial", 20))
        self.stars_label.setStyleSheet("color: #fbbf24; background: #1e1b4b; padding: 5px 15px; border-radius: 15px;")
        stats_box.addWidget(self.stars_label)
        
        header_layout.addLayout(stats_box)
        main_layout.addWidget(header)
        
        # Instruction area
        instr_frame = QFrame()
        instr_frame.setStyleSheet("background: #1e1b4b; border-radius: 15px; border: 2px solid #4f46e5;")
        instr_layout = QVBoxLayout(instr_frame)
        instr_layout.setContentsMargins(20, 15, 20, 15)
        
        self.instruction = QLabel("Getting ready...")
        self.instruction.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.instruction.setStyleSheet("color: #e0e6ff;")
        self.instruction.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.instruction.setWordWrap(True)
        instr_layout.addWidget(self.instruction)
        
        main_layout.addWidget(instr_frame)
        
        # Content area (buttons)
        self.content_frame = QFrame()
        self.content_frame.setStyleSheet("background: #0c0f1e; border-radius: 20px; border: 2px solid #1a1f40;")
        self.content_layout = QVBoxLayout(self.content_frame)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.content_frame, 1)
        
        # Feedback area
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
        
        main_layout.addWidget(feedback_frame)
        
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
        main_layout.addWidget(self.progress)
    
    def start_session(self):
        QTimer.singleShot(500, self.greet)
    
    def greet(self):
        voice.say(f"Hello {CHILD_NAME}! I am Pepper!")
        QTimer.singleShot(2000, self.next_task)
    
    def next_task(self):
        task = TASKS[len(self.buttons) % len(TASKS)] if self.buttons else TASKS[0]
        self.current_task = task
        self.correct_value = task["target"]
        
        # Update UI
        self.instruction.setText(task["instruction"])
        self.feedback.setText("Click the correct answer!")
        self.feedback.setStyleSheet("color: #60a5fa;")
        self.feedback_icon.setText("🎯")
        
        # Clear and create buttons
        self.clear_buttons()
        self.create_buttons(task)
        
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
        voice.say(task["instruction"])
    
    def create_buttons(self, task):
        options = task["options"]
        
        # Display names
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
            color = colors.get(opt) if task["type"] == "color" else None
            
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
        
        if selected == self.correct_value:
            # Success!
            points = self.current_task.get("tokens", 2) * 5
            self.score += points
            self.consecutive += 1
            
            # Flash correct button
            for btn in self.buttons:
                if btn.value == selected:
                    btn.flash_correct()
            
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
                    "SUCCESS",
                    self.score,
                    self.consecutive
                ])
            
            # Check mastery
            if self.consecutive >= 3:
                self.consecutive = 0
                self.mastered += 1
                voice.say(f"AMAZING {CHILD_NAME}! You mastered {self.current_task['name']}! +{points} points!")
                self.feedback.setText(f"🏆 MASTERED! +{points} points! 🏆")
            else:
                voice.say(f"Great job {CHILD_NAME}! {self.current_task['name']} is correct!")
            
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
            self.feedback.setText(f"❌ Try again! Look for {self.correct_value}")
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
                    "FAIL",
                    self.score,
                    0
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
                "TIMEOUT",
                self.score,
                0
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
        # Final report
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
║  PEPPER CLINICAL — WORKING VERSION                           ║
╠══════════════════════════════════════════════════════════════╣
║  ✓ Reliable click tasks (Colors, Animals, Numbers)         ║
║  ✓ 15 second timeout with visual progress bar              ║
║  ✓ Voice feedback from Pepper                              ║
║  ✓ Star rewards for 3 correct answers                      ║
║  ✓ CSV progress logging                                    ║
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
