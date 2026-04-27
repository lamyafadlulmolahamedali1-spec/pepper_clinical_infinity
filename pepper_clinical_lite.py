#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║  PEPPER CLINICAL LITE — NO FREEZING                             ║
║  Removed: PyBullet (heavy 3D), reduced CPU/GPU load            ║
║  Kept: OpenCV, MediaPipe, PyQt6, Voice, Speech                 ║
╚══════════════════════════════════════════════════════════════════╝
"""

# ═══════════════════════════════════════════════════════════════
# 0. ENV & AUTO-INSTALL
# ═══════════════════════════════════════════════════════════════
import os, sys, subprocess, ctypes, warnings, socket, time
import threading, random, math, re, json, csv, base64, wave, tempfile
from datetime import datetime
from io import BytesIO

os.environ.update({
    'TF_CPP_MIN_LOG_LEVEL': '3', 
    'PYTHONWARNINGS': 'ignore',
    'OPENCV_LOG_LEVEL': 'ERROR',
    'QT_LOGGING_RULES': '*.debug=false',
    'QT_QPA_PLATFORM': 'xcb',
    'OMP_NUM_THREADS': '2',  # Limit threads to prevent freezing
    'MKL_NUM_THREADS': '2',
    'NUMEXPR_NUM_THREADS': '2',
})
warnings.filterwarnings('ignore')

def auto_install(pkg, imp=None):
    name = imp or pkg.replace('-','_')
    try: __import__(name); return True
    except ImportError:
        print(f"⚙️  Installing {pkg}...")
        try:
            subprocess.run([sys.executable,'-m','pip','install',pkg,
                '--break-system-packages','-q'],capture_output=True,timeout=90)
            return True
        except: return False

for pkg,imp in [('PyQt6','PyQt6'),('mediapipe','mediapipe'),
    ('opencv-python','cv2'),('numpy','numpy'),
    ('pyttsx3','pyttsx3'),('speechrecognition','speech_recognition'),
    ('Pillow','PIL')]:
    auto_install(pkg,imp)

# ═══════════════════════════════════════════════════════════════
# 1. IMPORTS
# ═══════════════════════════════════════════════════════════════
import cv2, numpy as np
import pyttsx3, speech_recognition as sr
from PIL import Image, ImageDraw
import mediapipe as mp

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QGridLayout,
)
from PyQt6.QtCore import (
    Qt, QTimer, pyqtSignal, QObject, QThread,
)
from PyQt6.QtGui import (
    QFont, QColor, QPalette, QPixmap, QImage,
)

# ═══════════════════════════════════════════════════════════════
# 2. CONFIG
# ═══════════════════════════════════════════════════════════════
MIC_ENERGY = 400
MASTERY_N = 3

print("\n" + "═"*64)
print("  PEPPER CLINICAL LITE — No Freezing")
print("═"*64)
CHILD_NAME = input("\n👦 Enter Child's Name: ").strip()
if not CHILD_NAME: CHILD_NAME = "Child"
CHILD_NAME_SAFE = re.sub(r'[^a-zA-Z0-9_]','_', CHILD_NAME)
CSV_FILE = f"{CHILD_NAME_SAFE}_Results.csv"

with open(CSV_FILE,'w',newline='') as f:
    w=csv.writer(f)
    w.writerow(["Timestamp","Child","Task","Domain","Result","Score","Emotion"])

def log_csv(task_id, domain, result, score, emotion):
    with open(CSV_FILE,'a',newline='') as f:
        csv.writer(f).writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            CHILD_NAME, task_id, domain,
            "SUCCESS" if result else "FAIL",
            score, emotion])

# ═══════════════════════════════════════════════════════════════
# 3. TASK POOLS (simplified)
# ═══════════════════════════════════════════════════════════════
_COLORS = [
    {"id":"red", "color":"#ef4444", "label":"🔴 RED"},
    {"id":"blue", "color":"#3b82f6", "label":"🔵 BLUE"},
    {"id":"green", "color":"#22c55e", "label":"🟢 GREEN"},
    {"id":"yellow", "color":"#eab308", "label":"🟡 YELLOW"},
]

_ANIMALS = [
    {"id":"dog","emoji":"🐶","label":"Dog"},
    {"id":"cat","emoji":"🐱","label":"Cat"},
    {"id":"lion","emoji":"🦁","label":"Lion"},
    {"id":"elephant","emoji":"🐘","label":"Elephant"},
]

_FRUITS = [
    {"id":"apple","emoji":"🍎","label":"Apple"},
    {"id":"banana","emoji":"🍌","label":"Banana"},
    {"id":"orange","emoji":"🍊","label":"Orange"},
]

_MOTORS = [
    {"id":"clap","name":"👏 Clap","verify":"clap",
     "instruction":"CLAP your hands!",
     "success":"Amazing! You clapped! ✅",
     "fail":"Try again — clap your hands!"},
    {"id":"wave","name":"👋 Wave","verify":"wave",
     "instruction":"WAVE hello!",
     "success":"Wonderful! You waved! ✅",
     "fail":"Wave side to side!"},
    {"id":"raise_hand","name":"✋ Raise Hand","verify":"raise_hand",
     "instruction":"RAISE your hand HIGH!",
     "success":"Perfect! ✅",
     "fail":"Lift arm above head!"},
]

_WORDS = ["apple", "ball", "cat", "dog", "happy", "red", "blue", "green"]

def generate_task_pool():
    pool = []
    # Motor tasks
    for m in _MOTORS:
        pool.append({**m, "domain":"Motor", "level":1, "tokens":2})
    # Color tasks
    for c in _COLORS:
        pool.append({
            "id":f"color_{c['id']}", "domain":"Cognitive", "level":2,
            "name":f"Find {c['label']}",
            "instruction":f"Click the {c['label']} color!",
            "success":f"Correct! That is {c['label']}! ✅",
            "fail":f"Find {c['label']}!",
            "options":_COLORS, "correct":_COLORS.index(c),
            "tokens":3, "tablet_mode":"color_grid"
        })
    # Animal tasks
    for a in _ANIMALS:
        pool.append({
            "id":f"animal_{a['id']}", "domain":"Cognitive", "level":3,
            "name":f"Find {a['label']}",
            "instruction":f"Click the {a['label']}!",
            "success":f"Yes! That is the {a['label']}! ✅",
            "fail":f"Find the {a['label']}!",
            "options":_ANIMALS, "correct":_ANIMALS.index(a),
            "tokens":3, "tablet_mode":"object_grid"
        })
    # Fruit tasks
    for f in _FRUITS:
        pool.append({
            "id":f"fruit_{f['id']}", "domain":"Cognitive", "level":4,
            "name":f"Find {f['label']}",
            "instruction":f"Click the {f['label']}!",
            "success":f"Delicious {f['label']}! ✅",
            "fail":f"Find the {f['label']}!",
            "options":_FRUITS, "correct":_FRUITS.index(f),
            "tokens":3, "tablet_mode":"object_grid"
        })
    # Verbal tasks
    for w in _WORDS[:6]:
        pool.append({
            "id":f"say_{w}", "domain":"Verbal", "level":5,
            "name":f"Say '{w}'",
            "instruction":f"Say the word: {w.upper()}!",
            "success":f"I heard {w}! Perfect! ✅",
            "fail":f"Say {w}!",
            "tablet_mode":"word_display", "word_text":w.upper(),
            "verify":"speech_keyword", "keyword":w, "tokens":4
        })
    random.shuffle(pool)
    return pool

print("🎲 Generating tasks...")
TASK_POOL = generate_task_pool()
print(f"✅ {len(TASK_POOL)} tasks ready")

# ═══════════════════════════════════════════════════════════════
# 4. SHARED STATE
# ═══════════════════════════════════════════════════════════════
ST = {
    "name": CHILD_NAME,
    "task_index": 0,
    "consecutive": 0,
    "tasks_mastered": 0,
    "score": 0,
    "tokens": 0,
    "streak": 0,
    "tasks_success": 0,
    "tasks_fail": 0,
    "emotion": "neutral",
    "face_detected": False,
    "attention": 70,
    "hand_raised": False,
    "waving": False,
    "clapping": False,
    "finger_count": 0,
    "tablet_click_result": None,
    "is_speaking": False,
    "recording": False,
    "last_speech_text": "",
    "last_sound": time.time(),
    "session_chat": [],
    "uptime": time.time(),
}

def LOG(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg[:70]}")

# ═══════════════════════════════════════════════════════════════
# 5. BRIDGE
# ═══════════════════════════════════════════════════════════════
class TabletBridge(QObject):
    sig_new_task = pyqtSignal(dict)
    sig_show_success = pyqtSignal(str)
    sig_show_fail = pyqtSignal(str)
    sig_update_frame = pyqtSignal(object)
    sig_update_stats = pyqtSignal()
    sig_rec_stop = pyqtSignal(str)

BRIDGE = TabletBridge()

# ═══════════════════════════════════════════════════════════════
# 6. CAMERA THREAD (optimized - lower FPS)
# ═══════════════════════════════════════════════════════════════
class CameraThread(QThread):
    def __init__(self):
        super().__init__()
        self.running = False
        self.cap = None
        self._hands = None
        self._frame_count = 0
        
    def init_camera(self):
        for idx in [0, 1]:
            try:
                c = cv2.VideoCapture(idx)
                if c.isOpened():
                    c.set(cv2.CAP_PROP_FRAME_WIDTH, 320)  # Smaller for performance
                    c.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
                    c.set(cv2.CAP_PROP_FPS, 15)
                    self.cap = c
                    print(f"✅ Camera {idx}")
                    return
                c.release()
            except:
                pass
        print("⚠️  No camera - using simulation")
        
    def init_mediapipe(self):
        try:
            self._hands = mp.solutions.hands.Hands(
                max_num_hands=2,
                min_detection_confidence=0.7,
                min_tracking_confidence=0.5,
                static_image_mode=False
            )
            print("✅ MediaPipe Hands")
        except Exception as e:
            print(f"⚠️  MediaPipe: {e}")
            
    def count_fingers(self, hand_landmarks):
        try:
            tips = [8, 12, 16, 20]
            count = 0
            lm = hand_landmarks.landmark
            if lm[4].x < lm[3].x:
                count += 1
            for tip in tips:
                if lm[tip].y < lm[tip-2].y:
                    count += 1
            return count
        except:
            return 0
            
    def run(self):
        self.running = True
        self.init_camera()
        self.init_mediapipe()
        
        last_mp_time = 0
        mp_interval = 0.1  # Process mediapipe every 100ms
        
        while self.running:
            if self.cap and self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    frame = cv2.flip(frame, 1)
                    h, w = frame.shape[:2]
                    
                    # Process mediapipe less frequently
                    now = time.time()
                    if now - last_mp_time > mp_interval and self._hands:
                        last_mp_time = now
                        try:
                            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                            results = self._hands.process(rgb)
                            if results.multi_hand_landmarks:
                                fc = max(self.count_fingers(h) for h in results.multi_hand_landmarks)
                                ST["finger_count"] = fc
                                
                                # Detect clapping (hands close together)
                                if len(results.multi_hand_landmarks) >= 2:
                                    h1 = results.multi_hand_landmarks[0].landmark[0]
                                    h2 = results.multi_hand_landmarks[1].landmark[0]
                                    if abs(h1.x - h2.x) < 0.15 and abs(h1.y - h2.y) < 0.15:
                                        ST["clapping"] = True
                                    else:
                                        ST["clapping"] = False
                                        
                                # Detect waving (hand moving side to side - simplified)
                                if results.multi_hand_landmarks:
                                    wrist = results.multi_hand_landmarks[0].landmark[0]
                                    if hasattr(self, '_last_wrist_x'):
                                        if abs(wrist.x - self._last_wrist_x) > 0.08:
                                            ST["waving"] = True
                                        else:
                                            ST["waving"] = False
                                    self._last_wrist_x = wrist.x
                            else:
                                ST["finger_count"] = 0
                                ST["clapping"] = False
                        except Exception as e:
                            pass
                    
                    # Draw HUD
                    cv2.putText(frame, f"Task: {ST['task_index']+1}/{len(TASK_POOL)}", 
                               (5, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                    cv2.putText(frame, f"Score: {ST['score']}", 
                               (5, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                    cv2.putText(frame, f"Fingers: {ST['finger_count']}", 
                               (5, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                    
                    if ST["recording"]:
                        cv2.circle(frame, (w-20, 20), 8, (0, 0, 255), -1)
                    
                    # Convert to QImage and emit
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    h, w, ch = rgb.shape
                    bytes_per_line = ch * w
                    qt_img = QImage(rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
                    BRIDGE.sig_update_frame.emit(qt_img)
                    
            else:
                # Simulated frame
                frame = np.zeros((240, 320, 3), dtype=np.uint8)
                frame[:] = (10, 12, 28)
                cv2.putText(frame, "NO CAMERA - SIM MODE", (50, 120), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 150, 255), 1)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb.shape
                bytes_per_line = ch * w
                qt_img = QImage(rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
                BRIDGE.sig_update_frame.emit(qt_img)
                
            self.msleep(33)  # ~30 fps max
            
    def stop(self):
        self.running = False
        if self.cap:
            self.cap.release()
        self.quit()
        self.wait(1000)

# ═══════════════════════════════════════════════════════════════
# 7. VOICE RECORDER (optimized)
# ═══════════════════════════════════════════════════════════════
class TouchRecorder:
    def __init__(self):
        self._recording = False
        self._audio = None
        self.r = sr.Recognizer()
        self.r.energy_threshold = MIC_ENERGY
        self.r.dynamic_energy_threshold = True
        self.r.pause_threshold = 0.5
        
        try:
            with sr.Microphone() as src:
                self.r.adjust_for_ambient_noise(src, duration=0.5)
            print(f"✅ Mic ready (energy={self.r.energy_threshold:.0f})")
        except Exception as e:
            print(f"⚠️  Mic: {e}")
            
    def start(self):
        if self._recording:
            return
        self._recording = True
        self._audio = None
        ST["recording"] = True
        threading.Thread(target=self._capture, daemon=True).start()
        
    def _capture(self):
        try:
            with sr.Microphone() as src:
                audio = self.r.listen(src, timeout=5, phrase_time_limit=4)
                self._audio = audio
        except:
            pass
        finally:
            self._recording = False
            ST["recording"] = False
            
    def stop_and_recognise(self):
        for _ in range(20):
            if not self._recording:
                break
            time.sleep(0.05)
            
        if not self._audio:
            return ""
            
        try:
            text = self.r.recognize_google(self._audio)
            LOG(f"Recognized: {text}")
            return text.lower()
        except:
            return ""

# ═══════════════════════════════════════════════════════════════
# 8. TTS VOICE
# ═══════════════════════════════════════════════════════════════
class Voice:
    def __init__(self):
        self.ok = False
        try:
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', 120)
            self.engine.setProperty('volume', 1.0)
            self.ok = True
            print("✅ TTS Ready")
        except Exception as e:
            print(f"⚠️  TTS: {e}")
            
    def say(self, text, wait=False):
        if not self.ok or not text:
            return
        ST["is_speaking"] = True
        print(f"\n🔊 Pepper: {text}")
        ST["session_chat"].append({"role": "pepper", "text": text})
        self.engine.say(text)
        if wait:
            self.engine.runAndWait()
        else:
            self.engine.startLoop(False)
            self.engine.iterate()
            self.engine.endLoop()
        ST["is_speaking"] = False
        
    def stop(self):
        if self.ok:
            self.engine.stop()

# ═══════════════════════════════════════════════════════════════
# 9. CLICK CARD
# ═══════════════════════════════════════════════════════════════
class ClickCard(QPushButton):
    def __init__(self, data, idx, mode, parent=None):
        super().__init__(parent)
        self.idx = idx
        self.mode = mode
        self.data = data
        self.setFixedSize(140, 140)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setup_style()
        self.clicked.connect(lambda: BRIDGE.sig_new_task.emit({"action": "click", "idx": self.idx}))
        
    def setup_style(self):
        if self.mode == "color_grid":
            self.setText(f"\n\n{self.data['label']}")
            self.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            self.setStyleSheet(f"""
                QPushButton {{ background: {self.data['color']}; 
                              border-radius: 70px; 
                              border: 3px solid white;
                              color: white; }}
                QPushButton:hover {{ border: 5px solid yellow; }}
            """)
        else:
            self.setText(f"{self.data['emoji']}\n{self.data['label']}")
            self.setFont(QFont("Arial", 14, QFont.Weight.Bold))
            self.setStyleSheet("""
                QPushButton { background: #1e1b4b;
                              border-radius: 20px;
                              border: 3px solid #4f46e5;
                              color: #e0e6ff;
                              padding: 10px; }
                QPushButton:hover { border: 3px solid #a78bfa; }
            """)
            
    def flash_correct(self):
        self.setStyleSheet(self.styleSheet() + "QPushButton { border: 5px solid #22c55e !important; }")
        
    def flash_wrong(self):
        self.setStyleSheet(self.styleSheet() + "QPushButton { border: 5px solid #ef4444 !important; }")
        
    def reset(self):
        self.setup_style()

# ═══════════════════════════════════════════════════════════════
# 10. TABLET WINDOW
# ═══════════════════════════════════════════════════════════════
class TabletWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Pepper Clinical — {CHILD_NAME}")
        self.setFixedSize(1100, 700)
        self._cards = []
        self._locked = False
        self._correct_idx = -1
        self._recorder = TouchRecorder()
        self.setup_ui()
        self.connect_bridge()
        
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self.update_stats)
        self.stats_timer.start(500)
        
    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        central.setStyleSheet("background: #060918;")
        
        layout = QHBoxLayout(central)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # LEFT PANEL - Camera
        left = QFrame()
        left.setFixedWidth(480)
        left.setStyleSheet("background: #0a0d1e; border-radius: 15px;")
        left_layout = QVBoxLayout(left)
        
        self.cam_label = QLabel()
        self.cam_label.setFixedSize(480, 360)
        self.cam_label.setStyleSheet("background: black; border-radius: 10px;")
        self.cam_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(self.cam_label)
        
        self.status_label = QLabel("🎤 Ready")
        self.status_label.setFont(QFont("Arial", 12))
        self.status_label.setStyleSheet("color: #60a5fa; padding: 10px;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(self.status_label)
        
        self.chat_label = QLabel("")
        self.chat_label.setFont(QFont("Arial", 9))
        self.chat_label.setStyleSheet("color: #9ca3af; padding: 5px;")
        self.chat_label.setWordWrap(True)
        left_layout.addWidget(self.chat_label)
        
        left_layout.addStretch()
        layout.addWidget(left)
        
        # RIGHT PANEL - Tasks
        right = QWidget()
        right.setFixedWidth(580)
        right_layout = QVBoxLayout(right)
        right_layout.setSpacing(10)
        
        # Header
        header = QLabel(f"🤖 PEPPER CLINICAL — {CHILD_NAME}")
        header.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        header.setStyleSheet("color: #a78bfa; background: #1e1b4b; padding: 10px; border-radius: 10px;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(header)
        
        # Stars
        self.stars_label = QLabel("⭐ ☆ ☆")
        self.stars_label.setFont(QFont("Arial", 24))
        self.stars_label.setStyleSheet("color: #fbbf24; background: #0c0f1e; padding: 5px; border-radius: 10px;")
        self.stars_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(self.stars_label)
        
        # Instruction
        self.instruction_label = QLabel("Ready to learn!")
        self.instruction_label.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        self.instruction_label.setStyleSheet("color: #e0e6ff; background: #1e1b4b; padding: 15px; border-radius: 10px;")
        self.instruction_label.setWordWrap(True)
        self.instruction_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(self.instruction_label)
        
        # Content area
        self.content_frame = QFrame()
        self.content_frame.setStyleSheet("background: #0c0f1e; border-radius: 15px; border: 2px solid #4f46e5;")
        self.content_layout = QVBoxLayout(self.content_frame)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(self.content_frame, 1)
        
        # Feedback
        self.feedback_label = QLabel("👆 Tap the mic button to speak")
        self.feedback_label.setFont(QFont("Arial", 11))
        self.feedback_label.setStyleSheet("color: #9ca3af; background: #0c0f1e; padding: 10px; border-radius: 10px;")
        self.feedback_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(self.feedback_label)
        
        # Mic button
        self.mic_button = QPushButton("🎤  TAP & HOLD TO SPEAK")
        self.mic_button.setFixedHeight(50)
        self.mic_button.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.mic_button.setStyleSheet("""
            QPushButton { background: #dc2626; color: white; border-radius: 25px; border: 2px solid #fca5a5; }
            QPushButton:pressed { background: #991b1b; border: 3px solid white; }
        """)
        self.mic_button.pressed.connect(self.on_mic_press)
        self.mic_button.released.connect(self.on_mic_release)
        right_layout.addWidget(self.mic_button)
        
        # Stats bar
        stats_bar = QFrame()
        stats_bar.setStyleSheet("background: #07090f; border-radius: 10px;")
        stats_layout = QHBoxLayout(stats_bar)
        for label, attr, color in [("Score", "score_label", "#a78bfa"), 
                                   ("Mastered", "mastered_label", "#34d399"),
                                   ("Streak", "streak_label", "#fbbf24")]:
            w = QWidget()
            wl = QVBoxLayout(w)
            val = QLabel("0")
            val.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            val.setStyleSheet(f"color: {color};")
            val.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl = QLabel(label)
            lbl.setFont(QFont("Arial", 8))
            lbl.setStyleSheet("color: #6b7280;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            wl.addWidget(val)
            wl.addWidget(lbl)
            stats_layout.addWidget(w)
            setattr(self, attr, val)
        right_layout.addWidget(stats_bar)
        
        layout.addWidget(right)
        
    def connect_bridge(self):
        BRIDGE.sig_new_task.connect(self.on_new_task)
        BRIDGE.sig_show_success.connect(self.on_success)
        BRIDGE.sig_show_fail.connect(self.on_fail)
        BRIDGE.sig_update_frame.connect(self.update_camera)
        BRIDGE.sig_update_stats.connect(self.update_stats)
        BRIDGE.sig_rec_stop.connect(self.on_recognition)
        
    def update_camera(self, qimg):
        if qimg:
            pix = QPixmap.fromImage(qimg).scaled(480, 360, Qt.AspectRatioMode.KeepAspectRatio)
            self.cam_label.setPixmap(pix)
            
    def update_stats(self):
        self.score_label.setText(str(ST["score"]))
        self.mastered_label.setText(str(ST["tasks_mastered"]))
        self.streak_label.setText(str(ST["streak"]))
        stars = "⭐" * ST["consecutive"] + "☆" * (3 - ST["consecutive"])
        self.stars_label.setText(stars)
        
        # Update chat preview
        recent = ST["session_chat"][-3:]
        chat_text = "\n".join([f"{'🤖' if m['role']=='pepper' else '👦'}: {m['text'][:40]}" for m in recent])
        self.chat_label.setText(chat_text)
        
    def on_new_task(self, data):
        if data.get("action") == "click":
            self.handle_click(data["idx"])
            return
            
        self.instruction_label.setText(data.get("instruction", "Your turn!"))
        self.feedback_label.setText("Tap the correct answer!")
        self.feedback_label.setStyleSheet("color: #60a5fa; background: #0c0f1e; padding: 10px; border-radius: 10px;")
        self.build_content(data)
        self.unlock()
        
    def build_content(self, data):
        # Clear existing
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._cards.clear()
        
        mode = data.get("tablet_mode", "idle")
        
        if mode == "word_display":
            widget = QWidget()
            layout = QVBoxLayout(widget)
            word_label = QLabel(data.get("word_text", "SAY IT!"))
            word_label.setFont(QFont("Arial", 48, QFont.Weight.Bold))
            word_label.setStyleSheet("color: #a78bfa;")
            word_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(word_label)
            hint = QLabel("🎤 Tap the mic button and say the word!")
            hint.setFont(QFont("Arial", 12))
            hint.setStyleSheet("color: #6b7280;")
            hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(hint)
            self.content_layout.addWidget(widget)
            
        elif mode in ["color_grid", "object_grid"]:
            options = data.get("options", [])
            self._correct_idx = data.get("correct", -1)
            grid_widget = QWidget()
            grid = QGridLayout(grid_widget)
            grid.setSpacing(10)
            for i, opt in enumerate(options):
                card = ClickCard(opt, i, mode)
                self._cards.append(card)
                grid.addWidget(card, i // 2, i % 2)
            self.content_layout.addWidget(grid_widget)
            
        else:
            label = QLabel("👆 Watch Pepper and copy the movement!")
            label.setFont(QFont("Arial", 14))
            label.setStyleSheet("color: #a78bfa;")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.content_layout.addWidget(label)
            
    def handle_click(self, idx):
        if self._locked:
            return
            
        if self._correct_idx == -1:
            ST["tablet_click_result"] = "correct"
            if idx < len(self._cards):
                self._cards[idx].flash_correct()
            self.feedback_label.setText("✅ Great choice!")
            self.lock()
            return
            
        if idx == self._correct_idx:
            ST["tablet_click_result"] = "correct"
            if idx < len(self._cards):
                self._cards[idx].flash_correct()
            self.feedback_label.setText("✅ CORRECT! Well done!")
            self.feedback_label.setStyleSheet("color: #34d399; background: #0c0f1e; padding: 10px; border-radius: 10px;")
            LOG(f"✅ Correct answer! (idx={idx})")
        else:
            ST["tablet_click_result"] = "wrong"
            if idx < len(self._cards):
                self._cards[idx].flash_wrong()
            if 0 <= self._correct_idx < len(self._cards):
                self._cards[self._correct_idx].flash_correct()
            self.feedback_label.setText(f"❌ Try the {self._cards[self._correct_idx].data['label'] if self._correct_idx < len(self._cards) else 'correct'} one!")
            self.feedback_label.setStyleSheet("color: #f87171; background: #0c0f1e; padding: 10px; border-radius: 10px;")
            LOG(f"❌ Wrong answer! (idx={idx}, correct={self._correct_idx})")
        self.lock()
        
    def on_success(self, msg):
        self.clear_content()
        success_widget = QWidget()
        layout = QVBoxLayout(success_widget)
        check = QLabel("✅")
        check.setFont(QFont("Arial", 80))
        check.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(check)
        msg_label = QLabel(msg)
        msg_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        msg_label.setStyleSheet("color: #34d399;")
        msg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg_label.setWordWrap(True)
        layout.addWidget(msg_label)
        self.content_layout.addWidget(success_widget)
        self.feedback_label.setText(msg)
        QTimer.singleShot(2000, self.show_idle)
        
    def on_fail(self, msg):
        self.feedback_label.setText(f"❌ {msg}")
        self.feedback_label.setStyleSheet("color: #f87171; background: #0c0f1e; padding: 10px; border-radius: 10px;")
        QTimer.singleShot(2000, lambda: self.feedback_label.setStyleSheet("color: #9ca3af; background: #0c0f1e; padding: 10px; border-radius: 10px;"))
        
    def show_idle(self):
        self.clear_content()
        label = QLabel("🤖 Preparing next task...")
        label.setFont(QFont("Arial", 14))
        label.setStyleSheet("color: #6b7280;")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(label)
        
    def clear_content(self):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._cards.clear()
        
    def unlock(self):
        self._locked = False
        for card in self._cards:
            card.setEnabled(True)
            
    def lock(self):
        self._locked = True
        for card in self._cards:
            card.setEnabled(False)
        QTimer.singleShot(1000, lambda: setattr(self, '_locked', False))
        
    def on_mic_press(self):
        self.status_label.setText("🔴 RECORDING... Release to stop")
        self.status_label.setStyleSheet("color: #ef4444; padding: 10px;")
        self.mic_button.setText("🔴 RELEASE TO STOP")
        self._recorder.start()
        
    def on_mic_release(self):
        self.mic_button.setText("🎤 TAP & HOLD TO SPEAK")
        self.status_label.setText("⏳ Processing...")
        self.status_label.setStyleSheet("color: #fbbf24; padding: 10px;")
        threading.Thread(target=self.process_audio, daemon=True).start()
        
    def process_audio(self):
        text = self._recorder.stop_and_recognise()
        BRIDGE.sig_rec_stop.emit(text)
        
    def on_recognition(self, text):
        if text:
            self.status_label.setText(f"✅ Heard: \"{text[:30]}\"")
            self.status_label.setStyleSheet("color: #34d399; padding: 10px;")
            ST["last_speech_text"] = text
            ST["last_sound"] = time.time()
            ST["session_chat"].append({"role": "child", "text": text})
        else:
            self.status_label.setText("❌ Could not hear - try again!")
            self.status_label.setStyleSheet("color: #f87171; padding: 10px;")
        QTimer.singleShot(2000, lambda: self.status_label.setText("🎤 Ready"))
        QTimer.singleShot(2000, lambda: self.status_label.setStyleSheet("color: #60a5fa; padding: 10px;"))

# ═══════════════════════════════════════════════════════════════
# 11. THERAPY CONTROLLER
# ═══════════════════════════════════════════════════════════════
class TherapyController:
    def __init__(self, voice):
        self.voice = voice
        self.running = False
        
    def say(self, text):
        self.voice.say(text, wait=False)
        
    def run(self):
        self.running = True
        self.say(f"Hello {CHILD_NAME}! I am Pepper. Let's learn together!")
        time.sleep(1)
        
        while self.running:
            task = TASK_POOL[ST["task_index"] % len(TASK_POOL)]
            ST["tablet_instruction"] = task["instruction"]
            
            # Show task on tablet
            task_data = {
                "instruction": task["instruction"],
                "tablet_mode": task.get("tablet_mode", "motor")
            }
            if "options" in task:
                task_data["options"] = task["options"]
                task_data["correct"] = task["correct"]
            if "word_text" in task:
                task_data["word_text"] = task["word_text"]
                
            BRIDGE.sig_new_task.emit(task_data)
            
            # Announce task
            self.say(task["instruction"])
            
            # Run task
            success = self.run_task(task)
            
            # Log result
            log_csv(task["id"], task["domain"], success, ST["score"], ST["emotion"])
            
            if success:
                ST["consecutive"] += 1
                ST["score"] += task.get("tokens", 2) * 5
                ST["tasks_success"] += 1
                ST["streak"] += 1
                BRIDGE.sig_show_success.emit(task["success"])
                BRIDGE.sig_update_stats.emit()
                LOG(f"✅ Success! {ST['consecutive']}/3 stars")
                
                if ST["consecutive"] >= MASTERY_N:
                    ST["consecutive"] = 0
                    ST["tasks_mastered"] += 1
                    self.say(f"Excellent {CHILD_NAME}! You mastered that! [CELEBRATE]")
                    ST["task_index"] += 1
                    
            else:
                ST["consecutive"] = 0
                ST["streak"] = 0
                ST["tasks_fail"] += 1
                BRIDGE.sig_show_fail.emit(task["fail"])
                LOG(f"❌ Failed: {task['id']}")
                
            time.sleep(1)
            ST["task_index"] = (ST["task_index"] + 1) % len(TASK_POOL)
            
    def run_task(self, task):
        verify_type = task.get("verify", "motor")
        
        if verify_type in ["clap", "wave", "raise_hand"]:
            # Motor task
            deadline = time.time() + 15
            while time.time() < deadline:
                if verify_type == "clap" and ST["clapping"]:
                    return True
                if verify_type == "wave" and ST["waving"]:
                    return True
                if verify_type == "raise_hand" and ST["hand_raised"]:
                    return True
                time.sleep(0.2)
            return False
            
        elif verify_type == "speech_keyword":
            # Verbal task
            keyword = task.get("keyword", "")
            deadline = time.time() + 15
            ST["last_speech_text"] = ""
            while time.time() < deadline:
                if keyword and keyword in ST["last_speech_text"].lower():
                    return True
                time.sleep(0.2)
            return False
            
        elif verify_type == "tablet_click" or "options" in task:
            # Tablet click task
            deadline = time.time() + 20
            ST["tablet_click_result"] = None
            while time.time() < deadline:
                if ST["tablet_click_result"] == "correct":
                    return True
                if ST["tablet_click_result"] == "wrong":
                    return False
                time.sleep(0.1)
            return False
            
        return False

# ═══════════════════════════════════════════════════════════════
# 12. MAIN
# ═══════════════════════════════════════════════════════════════
def main():
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║  PEPPER CLINICAL LITE — NO FREEZING                         ║
║  Child: {CHILD_NAME:<40}║
╠══════════════════════════════════════════════════════════════╣
║  ✓ Removed PyBullet (heavy 3D)                              ║
║  ✓ Reduced camera resolution (320x240)                      ║
║  ✓ Limited MediaPipe processing (10 fps)                    ║
║  ✓ Optimized for low-resource laptops                       ║
╚══════════════════════════════════════════════════════════════╝
""")
    
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(6, 9, 18))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(224, 230, 255))
    app.setPalette(palette)
    
    window = TabletWindow()
    window.show()
    
    voice = Voice()
    camera = CameraThread()
    camera.start()
    
    controller = TherapyController(voice)
    
    def start_controller():
        time.sleep(2)
        controller.run()
        
    threading.Thread(target=start_controller, daemon=True).start()
    
    print("\n" + "="*64)
    print("✅ SYSTEM READY — NO FREEZING")
    print("="*64)
    print("\nCommands: Ctrl+C to quit")
    print("="*64 + "\n")
    
    try:
        sys.exit(app.exec())
    except:
        camera.stop()
        print(f"\n📊 Final Score: {ST['score']} | Mastered: {ST['tasks_mastered']}")
        print(f"📁 CSV: {CSV_FILE}")

if __name__ == "__main__":
    main()
