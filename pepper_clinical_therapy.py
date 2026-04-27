#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║  PEPPER CLINICAL THERAPY SYSTEM                                 ║
║  pepper_clinical_therapy.py                                     ║
║  Commander: Lamya | Omdurman Islamic University                 ║
╠══════════════════════════════════════════════════════════════════╣
║  ABA/ESDM Certified Digital Therapist                          ║
║  PyQt6 Tablet UI | PyBullet | Gemini AI | MediaPipe            ║
╚══════════════════════════════════════════════════════════════════╝
"""

# ═══════════════════════════════════════════════════════════════
# 0. ENVIRONMENT SETUP
# ═══════════════════════════════════════════════════════════════
import os, sys, subprocess, ctypes, warnings, socket, signal, time

os.environ.update({
    'TF_CPP_MIN_LOG_LEVEL': '3',
    'PYGAME_HIDE_SUPPORT_PROMPT': '1',
    'PYTHONWARNINGS': 'ignore',
    'OPENCV_LOG_LEVEL': 'ERROR',
    'CUDA_VISIBLE_DEVICES': '0',
    'TF_FORCE_GPU_ALLOW_GROWTH': 'true',
    'QT_LOGGING_RULES': '*.debug=false',
    'QT_QPA_PLATFORM': 'xcb',
})
warnings.filterwarnings('ignore')

try:
    _a = ctypes.cdll.LoadLibrary('libasound.so.2')
    _a.snd_lib_error_set_handler(ctypes.c_void_p(None))
except: pass

def auto_install(pkg, imp=None):
    name = imp or pkg.replace('-','_')
    try: __import__(name); return True
    except ImportError:
        print(f"⚙️  Installing {pkg}...")
        try:
            subprocess.run([sys.executable,'-m','pip','install',pkg,
                '--break-system-packages','-q'],
                capture_output=True,timeout=90)
            return True
        except: return False

for pkg,imp in [
    ('PyQt6','PyQt6'),('mediapipe','mediapipe'),
    ('faster-whisper','faster_whisper'),('deepface','deepface'),
    ('pyttsx3','pyttsx3'),('speechrecognition','speech_recognition'),
    ('opencv-python','cv2'),('numpy','numpy'),('flask','flask'),
]:
    auto_install(pkg,imp)

def kill_ports(*ports):
    for port in ports:
        try: os.system(f"fuser -k {port}/tcp 2>/dev/null")
        except: pass
        try:
            r=subprocess.run(['lsof','-ti',f':{port}'],
                capture_output=True,text=True,timeout=2)
            for pid in r.stdout.strip().split():
                try: os.kill(int(pid),signal.SIGKILL)
                except: pass
        except: pass
        for _ in range(8):
            try:
                s=socket.socket()
                s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
                s.bind(('0.0.0.0',port)); s.close(); break
            except: time.sleep(0.3)

kill_ports(5001,5007,5009)

# ═══════════════════════════════════════════════════════════════
# 1. IMPORTS
# ═══════════════════════════════════════════════════════════════
import cv2, numpy as np, threading, random, math, re
import json, webbrowser, urllib.parse
import pyttsx3, speech_recognition as sr
from flask import Flask,request,jsonify,render_template_string,redirect
from datetime import datetime
import pybullet as p, pybullet_data
sys.path.insert(0,'/home/lamya/pepper_duo/src')
import google.generativeai as genai

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QPushButton, QGridLayout,
    QFrame, QProgressBar, QScrollArea, QSizePolicy,
    QGraphicsDropShadowEffect,
)
from PyQt6.QtCore import (
    Qt, QTimer, pyqtSignal, QObject, QThread,
    QPropertyAnimation, QEasingCurve, QSize,
)
from PyQt6.QtGui import (
    QPixmap, QFont, QColor, QPainter, QPainterPath,
    QLinearGradient, QRadialGradient, QIcon,
    QPalette, QBrush, QFontDatabase,
)

try:
    from faster_whisper import WhisperModel
    WHISPER_OK = True
except:
    WHISPER_OK = False

# ═══════════════════════════════════════════════════════════════
# 2. CONFIG
# ═══════════════════════════════════════════════════════════════
GEMINI_KEY = "AIzaSyDEdleVKiQ5E00wMcjMbji0G9JcYT2TvE8"
GAME_URL   = "https://LamyaFadlulmolaHamedAli.pythonanywhere.com"
GITHUB_URL = "https://github.com/lamyafadlulmolahamedali1-spec/Pepper-Therapy-Games"
PORT_BRAIN = 5007
PORT_GAME  = 5009
PORT_REP   = 5001
API_DELAY  = 2.1
API_RPM    = 14

genai.configure(api_key=GEMINI_KEY)

def get_local_ip():
    try:
        s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        s.connect(("8.8.8.8",80)); ip=s.getsockname()[0]; s.close(); return ip
    except: return "127.0.0.1"

LOCAL_IP = get_local_ip()

# ═══════════════════════════════════════════════════════════════
# 3. THERAPY TASK LIBRARY — Infinite Mastery-Based Progression
# ═══════════════════════════════════════════════════════════════
"""
Each task has:
  - instruction: what Pepper says
  - verify: how success is measured
  - tablet_mode: what the tablet shows
  - options: choices shown on tablet (for click tasks)
  - correct: correct answer index (for click tasks)
  - mastery_needed: 3 consecutive successes
"""

TASK_LIBRARY = [
    # LEVEL 1 — MOTOR
    {
        "level":1,"name":"Clap Hands","protocol":"ABA-Motor",
        "instruction":"Clap your hands together! Show me!",
        "verify":"clap","tablet_mode":"image","image_theme":"clap",
        "options":[],"correct":-1,"tokens":2,
    },
    {
        "level":1,"name":"Touch Nose","protocol":"ABA-Motor",
        "instruction":"Touch your nose with your finger!",
        "verify":"touch_nose","tablet_mode":"image","image_theme":"nose",
        "options":[],"correct":-1,"tokens":2,
    },
    {
        "level":1,"name":"Raise Hand","protocol":"ABA-Motor",
        "instruction":"Raise your hand up high like this!",
        "verify":"raise_hand","tablet_mode":"image","image_theme":"hand",
        "options":[],"correct":-1,"tokens":2,
    },
    {
        "level":1,"name":"Wave Hello","protocol":"ABA-Motor",
        "instruction":"Wave hello to me! Say hello with your hand!",
        "verify":"wave","tablet_mode":"image","image_theme":"wave",
        "options":[],"correct":-1,"tokens":2,
    },
    # LEVEL 2 — COLORS
    {
        "level":2,"name":"Red Color","protocol":"DTT-Verbal",
        "instruction":"Touch the RED color on the tablet!",
        "verify":"tablet_click","tablet_mode":"colors",
        "options":["#ef4444","#3b82f6","#22c55e","#eab308"],
        "option_labels":["Red","Blue","Green","Yellow"],
        "correct":0,"tokens":3,
    },
    {
        "level":2,"name":"Blue Color","protocol":"DTT-Verbal",
        "instruction":"Touch the BLUE color on the tablet!",
        "verify":"tablet_click","tablet_mode":"colors",
        "options":["#22c55e","#3b82f6","#ef4444","#a855f7"],
        "option_labels":["Green","Blue","Red","Purple"],
        "correct":1,"tokens":3,
    },
    {
        "level":2,"name":"Yellow Color","protocol":"DTT-Verbal",
        "instruction":"Touch the YELLOW color! Find it!",
        "verify":"tablet_click","tablet_mode":"colors",
        "options":["#eab308","#ef4444","#3b82f6","#22c55e"],
        "option_labels":["Yellow","Red","Blue","Green"],
        "correct":0,"tokens":3,
    },
    {
        "level":2,"name":"Green Color","protocol":"DTT-Verbal",
        "instruction":"Can you find and touch GREEN?",
        "verify":"tablet_click","tablet_mode":"colors",
        "options":["#3b82f6","#a855f7","#22c55e","#ef4444"],
        "option_labels":["Blue","Purple","Green","Red"],
        "correct":2,"tokens":3,
    },
    # LEVEL 3 — ANIMALS
    {
        "level":3,"name":"Dog","protocol":"DTT-Cognitive",
        "instruction":"Touch the DOG! Which one is the dog?",
        "verify":"tablet_click","tablet_mode":"animals",
        "options":["🐶","🐱","🐻","🐭"],
        "option_labels":["Dog","Cat","Bear","Mouse"],
        "correct":0,"tokens":4,
    },
    {
        "level":3,"name":"Cat","protocol":"DTT-Cognitive",
        "instruction":"Find the CAT on the tablet! Touch it!",
        "verify":"tablet_click","tablet_mode":"animals",
        "options":["🐶","🐱","🦁","🐯"],
        "option_labels":["Dog","Cat","Lion","Tiger"],
        "correct":1,"tokens":4,
    },
    {
        "level":3,"name":"Lion","protocol":"DTT-Cognitive",
        "instruction":"Can you find the LION? Touch it!",
        "verify":"tablet_click","tablet_mode":"animals",
        "options":["🐘","🦒","🦁","🐧"],
        "option_labels":["Elephant","Giraffe","Lion","Penguin"],
        "correct":2,"tokens":4,
    },
    {
        "level":3,"name":"Elephant","protocol":"DTT-Cognitive",
        "instruction":"Touch the ELEPHANT! Find the big one!",
        "verify":"tablet_click","tablet_mode":"animals",
        "options":["🐘","🦊","🐼","🐨"],
        "option_labels":["Elephant","Fox","Panda","Koala"],
        "correct":0,"tokens":4,
    },
    # LEVEL 4 — FRUITS
    {
        "level":4,"name":"Apple","protocol":"DTT-Cognitive",
        "instruction":"Touch the APPLE! Which one is an apple?",
        "verify":"tablet_click","tablet_mode":"fruits",
        "options":["🍎","🍌","🍊","🍇"],
        "option_labels":["Apple","Banana","Orange","Grapes"],
        "correct":0,"tokens":4,
    },
    {
        "level":4,"name":"Banana","protocol":"DTT-Cognitive",
        "instruction":"Find the BANANA! Touch it on the tablet!",
        "verify":"tablet_click","tablet_mode":"fruits",
        "options":["🍎","🍌","🍑","🍓"],
        "option_labels":["Apple","Banana","Peach","Strawberry"],
        "correct":1,"tokens":4,
    },
    {
        "level":4,"name":"Say Apple","protocol":"DTT-Verbal",
        "instruction":"Say the word: APPLE! Say it out loud!",
        "verify":"speech_keyword","keyword":"apple",
        "tablet_mode":"word","word_display":"🍎 APPLE",
        "options":[],"correct":-1,"tokens":4,
    },
    {
        "level":4,"name":"Say Banana","protocol":"DTT-Verbal",
        "instruction":"Say the word: BANANA! You can do it!",
        "verify":"speech_keyword","keyword":"banana",
        "tablet_mode":"word","word_display":"🍌 BANANA",
        "options":[],"correct":-1,"tokens":4,
    },
    # LEVEL 5 — NUMBERS
    {
        "level":5,"name":"Number One","protocol":"DTT-Cognitive",
        "instruction":"Touch the number ONE on the tablet!",
        "verify":"tablet_click","tablet_mode":"numbers",
        "options":["1","2","3","4"],
        "option_labels":["One","Two","Three","Four"],
        "correct":0,"tokens":5,
    },
    {
        "level":5,"name":"Number Two","protocol":"DTT-Cognitive",
        "instruction":"Find the number TWO! Touch it!",
        "verify":"tablet_click","tablet_mode":"numbers",
        "options":["3","2","5","1"],
        "option_labels":["Three","Two","Five","One"],
        "correct":1,"tokens":5,
    },
    {
        "level":5,"name":"Count Stars","protocol":"DTT-Verbal",
        "instruction":"Count the stars and say the number! ⭐⭐⭐",
        "verify":"speech_number",
        "tablet_mode":"word","word_display":"⭐ ⭐ ⭐ = ?",
        "options":[],"correct":-1,"tokens":5,
    },
    # LEVEL 6 — SHAPES
    {
        "level":6,"name":"Circle","protocol":"ESDM-Cognitive",
        "instruction":"Touch the CIRCLE shape!",
        "verify":"tablet_click","tablet_mode":"shapes",
        "options":["⭕","⬛","🔺","💎"],
        "option_labels":["Circle","Square","Triangle","Diamond"],
        "correct":0,"tokens":5,
    },
    {
        "level":6,"name":"Square","protocol":"ESDM-Cognitive",
        "instruction":"Find the SQUARE! Which one is it?",
        "verify":"tablet_click","tablet_mode":"shapes",
        "options":["🔺","⭕","⬛","⭐"],
        "option_labels":["Triangle","Circle","Square","Star"],
        "correct":2,"tokens":5,
    },
    # LEVEL 7 — SOCIAL/VERBAL
    {
        "level":7,"name":"Full Sentence","protocol":"ESDM-Social",
        "instruction":"Tell me something you love! Use a full sentence!",
        "verify":"speech_sentence",
        "tablet_mode":"word","word_display":"💬 I love...",
        "options":[],"correct":-1,"tokens":6,"reward":"youtube",
    },
    {
        "level":7,"name":"Emotion Name","protocol":"ESDM-Social",
        "instruction":"How do you feel today? Tell me!",
        "verify":"speech_any",
        "tablet_mode":"emotions",
        "options":["😊","😢","😠","😨"],
        "option_labels":["Happy","Sad","Angry","Scared"],
        "correct":-1,"tokens":6,"reward":"youtube",
    },
    {
        "level":7,"name":"Daily Life","protocol":"ESDM-Social",
        "instruction":"What do you do when you are hungry? Tell me!",
        "verify":"speech_any",
        "tablet_mode":"word","word_display":"🍽️ When hungry...",
        "options":[],"correct":-1,"tokens":6,"reward":"youtube",
    },
]

# Empathy responses
class EmpathyLib:
    _lib = {
        "happy":      ["You are so happy today! Let us celebrate! [CELEBRATE]",
                       "Your smile makes me dance! [DANCE]"],
        "sad":        ["I see you. It is okay to feel sad. I am here. [HUG]",
                       "You are safe with me. Let us breathe. [NOD]"],
        "angry":      ["Let us breathe together. In... and out... [NOD]",
                       "It is okay. I am very patient. [HUG]"],
        "fear":       ["You are safe! I am right here. [HUG]",
                       "No worries. We go at your pace. [NOD]"],
        "confused":   ["Let me show you again! [THINK]",
                       "Good try! Let us try differently! [POINT]"],
        "joyful":     ["Amazing energy today! [DANCE][CELEBRATE]",
                       "Your joy fills the room! [CELEBRATE]"],
        "silence":    ["I am here whenever you are ready! 🎯",
                       "Take your time! I am listening. 🎯",
                       "No rush! Waiting for you. 🎯"],
        "greeting":   ["Hello! I am Pepper! What is your name? 🎯",
                       "Hi! I am so happy to meet you! 🎯"],
        "task_ok":    ["PERFECT! You did it! [CLAP][CELEBRATE]",
                       "WOW! Incredible! [DANCE]",
                       "BRILLIANT! Superstar! [CELEBRATE]"],
        "task_retry": ["Good try! One more time! 🎯",
                       "Almost there! You can do it! 🎯",
                       "Keep trying! I believe in you! 🎯"],
        "level_up":   ["LEVEL UP! Amazing work! [DANCE][CELEBRATE]",
                       "NEXT LEVEL! You are a champion! [CELEBRATE]"],
        "youtube":    ["You earned a video reward! What do you want to watch? 🎬",
                       "REWARD TIME! Tell me your favorite video! 🎬"],
        "default":    ["You are doing great! [CLAP]",
                       "Great effort! Ready? Your turn! 🎯"],
    }
    _last = {}
    def get(self, cat="default"):
        pool = self._lib.get(cat, self._lib["default"])
        last = self._last.get(cat,-1)
        choices = [i for i in range(len(pool)) if i!=last]
        if not choices: choices = list(range(len(pool)))
        idx = random.choice(choices)
        self._last[cat] = idx
        return pool[idx]

EMPATHY = EmpathyLib()

# ═══════════════════════════════════════════════════════════════
# 4. SHARED STATE
# ═══════════════════════════════════════════════════════════════
ST = {
    "name":"Friend","known":False,"age":6,"diagnosis":"ASD Level 2",
    # Mastery system
    "task_index":0,
    "consecutive_successes":0,
    "mastery_needed":3,
    "tasks_mastered":0,
    "current_level":1,
    "level_tasks_done":0,
    "total_tasks_passed":0,
    # Tablet state
    "tablet_locked":True,
    "tablet_mode":"idle",
    "tablet_click_answer":-1,
    "tablet_correct":-1,
    "tablet_result":None,
    "tablet_message":"Welcome! Getting ready...",
    "tablet_options":[],
    "tablet_option_labels":[],
    "tablet_word_display":"",
    "tablet_image_theme":"",
    # Perception
    "emotion":"neutral","emotion_scores":{},
    "face_detected":False,"face_box":None,
    "attention":70,"engagement":"moderate",
    "hand_raised":False,"waving":False,
    "clapping":False,"face_touch":False,
    "head_tilted":False,"blinking":False,
    "eye_contact":False,
    "pose_landmarks":{},
    "face_mesh_landmarks":{},
    "verify_action":None,"verify_result":False,
    "verify_timeout":0.0,
    "last_speech_text":"","last_sound":time.time(),
    # Session
    "protocol":"ABA-Motor",
    "is_speaking":False,"interrupt_flag":False,
    "listening":False,"waiting_for_child":False,
    "task_success":False,"youtube_pending":False,
    "sim_cmd":None,
    "lip_sync_value":0.0,"lip_sync_active":False,
    # API
    "gemini_ok":False,"gemini_model":"N/A",
    "last_api_call":0.0,"api_calls_this_min":0,
    "api_minute_start":time.time(),"api_fallback_count":0,
    # Progress
    "score":0,"tokens":0,"stars_today":0,
    "streak":0,"tasks_success":0,"tasks_fail":0,
    "skills":{"motor":50,"verbal":50,"cognitive":50,"social":50,"attention":50},
    # History
    "att_history":[],"score_history":[],
    "emo_history":[],"time_labels":[],
    "logs":[],"session_chat":[],
    "parent_chat":[],"parent_notes":[],"reports":[],
    "iasq_score":None,"iasq_result":None,
    "session_start":datetime.now().strftime("%H:%M"),
    "session_date":datetime.now().strftime("%Y-%m-%d"),
    "uptime":time.time(),"last_youtube":None,
}

_log_lock = threading.Lock()

def LOG(msg, t="info", proto=None):
    with _log_lock:
        e = {
            "time":datetime.now().strftime("%H:%M:%S"),
            "msg":str(msg)[:120],"type":t,
            "proto":proto or ST["protocol"],
            "emo":ST["emotion"],"child":ST["name"],
        }
        ST["logs"].append(e)
        if len(ST["logs"])>200: ST["logs"]=ST["logs"][-200:]
        if len(ST["logs"])%3==0:
            ST["att_history"].append(ST["attention"])
            ST["score_history"].append(ST["score"])
            ST["emo_history"].append(ST["emotion"])
            ST["time_labels"].append(datetime.now().strftime("%H:%M:%S"))
            for k in ["att_history","score_history","emo_history","time_labels"]:
                if len(ST[k])>60: ST[k]=ST[k][-60:]
    print(f"[{e['time']}][{t.upper()}] {msg[:65]}")

# ═══════════════════════════════════════════════════════════════
# 5. PYQT6 TABLET UI — Persistent Interactive HD Interface
# ═══════════════════════════════════════════════════════════════
class TabletSignals(QObject):
    update_display  = pyqtSignal(dict)
    click_answer    = pyqtSignal(int)
    unlock_tablet   = pyqtSignal()
    lock_tablet     = pyqtSignal()
    show_result     = pyqtSignal(bool, str)

tablet_signals = TabletSignals()

class ColorCard(QPushButton):
    """Interactive color card for color-identification tasks"""
    def __init__(self, color_hex, label, idx, parent=None):
        super().__init__(parent)
        self.idx = idx
        self.color_hex = color_hex
        self.label_text = label
        self.setFixedSize(150, 150)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._selected = False
        self._correct  = False
        self._wrong    = False
        self.setStyleSheet(self._base_style())
        self.setText(f"\n\n\n\n{label}")
        self.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        self.clicked.connect(lambda: tablet_signals.click_answer.emit(self.idx))

    def _base_style(self):
        return f"""
        QPushButton {{
            background: {self.color_hex};
            border-radius: 18px;
            border: 4px solid rgba(255,255,255,0.3);
            color: white;
            text-align: center;
            font-size: 13px;
            font-weight: bold;
            text-shadow: 1px 1px 3px rgba(0,0,0,0.8);
        }}
        QPushButton:hover {{
            border: 4px solid white;
            transform: scale(1.05);
        }}
        """
    def set_correct(self):
        self._correct = True
        self.setStyleSheet(f"""
        QPushButton {{
            background: {self.color_hex};
            border-radius: 18px;
            border: 6px solid #22c55e;
            color: white;
            font-size: 13px;
            font-weight: bold;
            text-shadow: 1px 1px 3px rgba(0,0,0,0.8);
        }}""")
    def set_wrong(self):
        self._wrong = True
        self.setStyleSheet(f"""
        QPushButton {{
            background: {self.color_hex};
            border-radius: 18px;
            border: 6px solid #ef4444;
            color: white;
            font-size: 13px;
            font-weight: bold;
            opacity: 0.6;
            text-shadow: 1px 1px 3px rgba(0,0,0,0.8);
        }}""")
    def reset(self):
        self._correct=False; self._wrong=False
        self.setStyleSheet(self._base_style())

class EmojiCard(QPushButton):
    """Interactive emoji card for animals, fruits, shapes, emotions"""
    def __init__(self, emoji, label, idx, parent=None):
        super().__init__(parent)
        self.idx = idx
        self.emoji = emoji
        self.label_text = label
        self.setFixedSize(160, 160)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._set_normal()
        self.clicked.connect(lambda: tablet_signals.click_answer.emit(self.idx))

    def _set_normal(self):
        self.setText(f"{self.emoji}\n{self.label_text}")
        self.setFont(QFont("Arial",12,QFont.Weight.Bold))
        self.setStyleSheet("""
        QPushButton {
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 #1e1b4b, stop:1 #2d2a5e);
            border-radius: 20px;
            border: 3px solid #4f46e5;
            color: #e0e6ff;
            font-size: 12px;
            font-weight: bold;
            padding: 8px;
            text-align: center;
        }
        QPushButton:hover {
            border: 3px solid #a78bfa;
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 #2e2b6e, stop:1 #3d3a7e);
        }
        """)

    def set_correct(self):
        self.setStyleSheet("""
        QPushButton {
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 #052918, stop:1 #0a3d20);
            border-radius: 20px;
            border: 5px solid #22c55e;
            color: #34d399;
            font-size: 12px;
            font-weight: bold;
            padding: 8px;
        }""")

    def set_wrong(self):
        self.setStyleSheet("""
        QPushButton {
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 #2d0a0a, stop:1 #3d1010);
            border-radius: 20px;
            border: 5px solid #ef4444;
            color: #f87171;
            font-size: 12px;
            font-weight: bold;
            opacity: 0.5;
            padding: 8px;
        }""")

    def reset(self): self._set_normal()

class NumberCard(QPushButton):
    """Large number display card"""
    def __init__(self, number, label, idx, parent=None):
        super().__init__(parent)
        self.idx=idx; self.number=number; self.label_text=label
        self.setFixedSize(150,150)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setText(f"{number}\n{label}")
        self.setFont(QFont("Arial",28,QFont.Weight.Bold))
        colors=["#6366f1","#ec4899","#f59e0b","#10b981"]
        c=colors[idx%len(colors)]
        self.setStyleSheet(f"""
        QPushButton {{
            background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 {c}99,stop:1 {c}55);
            border-radius:18px;border:3px solid {c};
            color:white;font-size:28px;font-weight:bold;text-align:center;
        }}
        QPushButton:hover{{border:4px solid white;}}""")
        self.clicked.connect(lambda: tablet_signals.click_answer.emit(self.idx))

    def set_correct(self):
        self.setStyleSheet(self.styleSheet()+"""
        QPushButton{border:5px solid #22c55e !important;}""")
    def set_wrong(self):
        self.setStyleSheet(self.styleSheet()+"""
        QPushButton{border:5px solid #ef4444 !important;opacity:0.5;}""")
    def reset(self): pass

class TabletWindow(QMainWindow):
    """Pepper's chest tablet — persistent, interactive HD interface"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pepper Tablet — Clinical Therapy")
        self.setFixedSize(700, 900)
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowStaysOnTopHint)
        self._cards   = []
        self._locked  = True
        self._phase   = 0.0
        self._correct_idx = -1
        self._setup_ui()
        self._setup_signals()
        self._setup_timer()

    def _setup_ui(self):
        # Main widget
        self.central = QWidget()
        self.setCentralWidget(self.central)
        self.central.setStyleSheet("""
        QWidget {
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 #06091a, stop:0.5 #0c0f2e, stop:1 #06091a);
        }""")
        main_layout = QVBoxLayout(self.central)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(15,10,15,10)

        # ── HEADER ───────────────────────────────────────────
        header = QFrame()
        header.setFixedHeight(85)
        header.setStyleSheet("""
        QFrame {
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 #1a0a3d, stop:0.5 #0a0f28, stop:1 #1a0a3d);
            border-radius: 15px;
            border: 2px solid #4f46e5;
        }""")
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(15,5,15,5)
        # Pepper avatar mini
        self.avatar_label = QLabel("🤖")
        self.avatar_label.setFont(QFont("Arial",32))
        self.avatar_label.setStyleSheet("color:#a78bfa;")
        h_lay.addWidget(self.avatar_label)
        # Title block
        title_widget = QWidget()
        t_lay = QVBoxLayout(title_widget)
        t_lay.setSpacing(2)
        self.title_lbl = QLabel("PEPPER CLINICAL THERAPY")
        self.title_lbl.setFont(QFont("Arial",14,QFont.Weight.Bold))
        self.title_lbl.setStyleSheet("color:#a78bfa;")
        t_lay.addWidget(self.title_lbl)
        self.subtitle_lbl = QLabel("ABA/ESDM Digital Therapist")
        self.subtitle_lbl.setFont(QFont("Arial",9))
        self.subtitle_lbl.setStyleSheet("color:#6b7280;")
        t_lay.addWidget(self.subtitle_lbl)
        h_lay.addWidget(title_widget,1)
        # Status indicators
        status_w = QWidget()
        s_lay = QVBoxLayout(status_w)
        s_lay.setSpacing(3)
        self.ai_status = QLabel("● AI ONLINE")
        self.ai_status.setFont(QFont("Arial",8,QFont.Weight.Bold))
        self.ai_status.setStyleSheet("color:#34d399;")
        s_lay.addWidget(self.ai_status, alignment=Qt.AlignmentFlag.AlignRight)
        self.child_name_lbl = QLabel("Child: Friend")
        self.child_name_lbl.setFont(QFont("Arial",9))
        self.child_name_lbl.setStyleSheet("color:#60a5fa;")
        s_lay.addWidget(self.child_name_lbl, alignment=Qt.AlignmentFlag.AlignRight)
        self.live_dot = QLabel("🔴 LIVE")
        self.live_dot.setFont(QFont("Arial",8))
        self.live_dot.setStyleSheet("color:#ef4444;")
        s_lay.addWidget(self.live_dot, alignment=Qt.AlignmentFlag.AlignRight)
        h_lay.addWidget(status_w)
        main_layout.addWidget(header)

        # ── LEVEL PROGRESS ───────────────────────────────────
        prog_frame = QFrame()
        prog_frame.setFixedHeight(50)
        prog_frame.setStyleSheet("""
        QFrame{background:#0c0f1e;border-radius:10px;border:1px solid #1a1f40;}""")
        p_lay = QHBoxLayout(prog_frame)
        p_lay.setContentsMargins(12,5,12,5)
        self.level_lbl = QLabel("Level 1 — ABA Motor")
        self.level_lbl.setFont(QFont("Arial",10,QFont.Weight.Bold))
        self.level_lbl.setStyleSheet("color:#34d399;")
        p_lay.addWidget(self.level_lbl)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0,3)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(18)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
        QProgressBar{background:#1f2937;border-radius:9px;border:none;}
        QProgressBar::chunk{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,
            stop:0 #059669,stop:1 #34d399);border-radius:9px;}
        """)
        p_lay.addWidget(self.progress_bar,1)
        self.mastery_lbl = QLabel("0/3")
        self.mastery_lbl.setFont(QFont("Arial",10,QFont.Weight.Bold))
        self.mastery_lbl.setStyleSheet("color:#fbbf24;")
        self.mastery_lbl.setMinimumWidth(35)
        p_lay.addWidget(self.mastery_lbl)
        main_layout.addWidget(prog_frame)

        # ── INSTRUCTION AREA ─────────────────────────────────
        self.instruction_frame = QFrame()
        self.instruction_frame.setFixedHeight(100)
        self.instruction_frame.setStyleSheet("""
        QFrame {
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 #1e1b4b, stop:1 #0c0f2e);
            border-radius: 14px;
            border: 2px solid #4f46e5;
        }""")
        i_lay = QVBoxLayout(self.instruction_frame)
        i_lay.setContentsMargins(15,8,15,8)
        self.instruction_icon = QLabel("📋")
        self.instruction_icon.setFont(QFont("Arial",20))
        self.instruction_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        i_lay.addWidget(self.instruction_icon)
        self.instruction_lbl = QLabel("Getting ready for therapy...")
        self.instruction_lbl.setFont(QFont("Arial",14,QFont.Weight.Bold))
        self.instruction_lbl.setStyleSheet("color:#e0e6ff;")
        self.instruction_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.instruction_lbl.setWordWrap(True)
        i_lay.addWidget(self.instruction_lbl)
        main_layout.addWidget(self.instruction_frame)

        # ── CONTENT AREA (cards shown here) ──────────────────
        self.content_frame = QFrame()
        self.content_frame.setMinimumHeight(380)
        self.content_frame.setStyleSheet("""
        QFrame {
            background: rgba(12,15,30,0.8);
            border-radius: 16px;
            border: 2px solid #1a1f40;
        }""")
        self.content_layout = QVBoxLayout(self.content_frame)
        self.content_layout.setContentsMargins(15,15,15,15)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Default content
        self.default_label = QLabel("🤖\nPepper is preparing your task...")
        self.default_label.setFont(QFont("Arial",16))
        self.default_label.setStyleSheet("color:#6b7280;")
        self.default_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(self.default_label)
        main_layout.addWidget(self.content_frame,1)

        # ── FEEDBACK AREA ─────────────────────────────────────
        self.feedback_frame = QFrame()
        self.feedback_frame.setFixedHeight(65)
        self.feedback_frame.setStyleSheet("""
        QFrame{background:#0c0f1e;border-radius:12px;border:1px solid #1a1f40;}""")
        f_lay = QHBoxLayout(self.feedback_frame)
        f_lay.setContentsMargins(15,8,15,8)
        self.feedback_icon = QLabel("💤")
        self.feedback_icon.setFont(QFont("Arial",22))
        f_lay.addWidget(self.feedback_icon)
        self.feedback_lbl = QLabel("Waiting for Pepper...")
        self.feedback_lbl.setFont(QFont("Arial",12,QFont.Weight.Bold))
        self.feedback_lbl.setStyleSheet("color:#9ca3af;")
        self.feedback_lbl.setWordWrap(True)
        f_lay.addWidget(self.feedback_lbl,1)
        main_layout.addWidget(self.feedback_frame)

        # ── STATS BAR ─────────────────────────────────────────
        stats_frame = QFrame()
        stats_frame.setFixedHeight(50)
        stats_frame.setStyleSheet("""
        QFrame{background:#07090f;border-radius:10px;border:1px solid #1a1f40;}""")
        st_lay = QHBoxLayout(stats_frame)
        st_lay.setContentsMargins(12,5,12,5)
        for label,key,color in [
            ("Score","score","#a78bfa"),
            ("Tokens","tokens","#fbbf24"),
            ("Mastered","tasks_mastered","#34d399"),
            ("Streak","streak","#60a5fa"),
        ]:
            w = QWidget()
            wl = QVBoxLayout(w)
            wl.setSpacing(1)
            wl.setContentsMargins(0,0,0,0)
            val = QLabel("0")
            val.setFont(QFont("Arial",13,QFont.Weight.Bold))
            val.setStyleSheet(f"color:{color};")
            val.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl = QLabel(label)
            lbl.setFont(QFont("Arial",7))
            lbl.setStyleSheet("color:#6b7280;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            wl.addWidget(val)
            wl.addWidget(lbl)
            st_lay.addWidget(w)
            setattr(self, f"stat_{key}", val)
        main_layout.addWidget(stats_frame)

        # ── LOCK OVERLAY ──────────────────────────────────────
        self.lock_overlay = QLabel()
        self.lock_overlay.setParent(self.content_frame)
        self.lock_overlay.setGeometry(0,0,670,380)
        self.lock_overlay.setStyleSheet("""
        QLabel{
            background:rgba(0,0,0,0.45);
            border-radius:16px;
            color:#a78bfa;
            font-size:48px;
        }""")
        self.lock_overlay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lock_overlay.setText("🔒")
        self.lock_overlay.hide()

    def _setup_signals(self):
        tablet_signals.update_display.connect(self._on_update)
        tablet_signals.click_answer.connect(self._on_click)
        tablet_signals.unlock_tablet.connect(self._unlock)
        tablet_signals.lock_tablet.connect(self._lock)
        tablet_signals.show_result.connect(self._on_result)

    def _setup_timer(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self._tick)
        self.timer.start(500)  # 0.5s refresh

    def _tick(self):
        """Update stats from shared state"""
        self.stat_score.setText(str(ST["score"]))
        self.stat_tokens.setText(str(ST["tokens"]))
        self.stat_tasks_mastered.setText(str(ST["tasks_mastered"]))
        self.stat_streak.setText(str(ST["streak"]))
        self.child_name_lbl.setText(f"Child: {ST['name']}")
        self.mastery_lbl.setText(f"{ST['consecutive_successes']}/3")
        self.progress_bar.setValue(ST["consecutive_successes"])
        lv = ST["current_level"]
        task_idx = ST["task_index"]
        if task_idx < len(TASK_LIBRARY):
            t = TASK_LIBRARY[task_idx]
            self.level_lbl.setText(f"Level {lv} — {t['protocol']}")
        # AI status
        if ST["gemini_ok"]:
            self.ai_status.setText(f"● {ST['gemini_model'][:15]}")
            self.ai_status.setStyleSheet("color:#34d399;")
        else:
            self.ai_status.setText("⚠ FALLBACK")
            self.ai_status.setStyleSheet("color:#fbbf24;")
        # Listening/speaking state
        if ST["is_speaking"]:
            self.feedback_icon.setText("🔊")
            self.feedback_lbl.setStyleSheet("color:#60a5fa;")
        elif ST["listening"]:
            self.feedback_icon.setText("👂")
            self.feedback_lbl.setStyleSheet("color:#34d399;")
        elif ST["waiting_for_child"]:
            self.feedback_icon.setText("⏳")
            self.feedback_lbl.setStyleSheet("color:#fbbf24;")
        else:
            self.feedback_icon.setText("💤")
            self.feedback_lbl.setStyleSheet("color:#9ca3af;")

    def _on_update(self, data):
        """Update tablet display for a new task"""
        mode  = data.get("mode","idle")
        instr = data.get("instruction","")
        opts  = data.get("options",[])
        labels= data.get("option_labels",[])
        correct = data.get("correct",-1)
        self._correct_idx = correct
        word  = data.get("word_display","")
        msg   = data.get("message","")
        self.instruction_lbl.setText(instr)
        if msg: self.feedback_lbl.setText(msg)
        self._build_content(mode, opts, labels, word)
        self._unlock()

    def _build_content(self, mode, opts, labels, word):
        """Clear and rebuild content cards"""
        # Remove old widgets
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._cards.clear()
        self.default_label = None

        if mode == "idle":
            lbl = QLabel("🤖\nPepper is preparing your task...")
            lbl.setFont(QFont("Arial",16))
            lbl.setStyleSheet("color:#6b7280;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.content_layout.addWidget(lbl)
            return

        if mode == "image":
            # Large instruction image area
            img_area = QWidget()
            ia_lay = QVBoxLayout(img_area)
            ia_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon = QLabel(self._theme_to_emoji(ST["tablet_image_theme"]))
            icon.setFont(QFont("Arial",80))
            icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            ia_lay.addWidget(icon)
            caption = QLabel(f"Watch and copy Pepper!")
            caption.setFont(QFont("Arial",14,QFont.Weight.Bold))
            caption.setStyleSheet("color:#a78bfa;")
            caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
            ia_lay.addWidget(caption)
            self.content_layout.addWidget(img_area)
            return

        if mode == "word":
            # Large word/emoji display
            word_frame = QFrame()
            word_frame.setStyleSheet("""
            QFrame{background:qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 #1e1b4b,stop:1 #0c0f1e);
                border-radius:20px;border:3px solid #4f46e5;
                min-height:200px;}""")
            wf_lay = QVBoxLayout(word_frame)
            wf_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
            word_lbl = QLabel(word or "Say it!")
            word_lbl.setFont(QFont("Arial",36,QFont.Weight.Bold))
            word_lbl.setStyleSheet("color:#a78bfa;")
            word_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            wf_lay.addWidget(word_lbl)
            hint = QLabel("🎤 Say it out loud!")
            hint.setFont(QFont("Arial",14))
            hint.setStyleSheet("color:#6b7280;")
            hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
            wf_lay.addWidget(hint)
            self.content_layout.addWidget(word_frame)
            return

        # GRID of clickable cards
        grid_w = QWidget()
        grid = QGridLayout(grid_w)
        grid.setSpacing(12)
        grid.setAlignment(Qt.AlignmentFlag.AlignCenter)

        for i,(opt,lbl) in enumerate(zip(opts,labels)):
            if mode=="colors":
                card = ColorCard(opt,lbl,i)
            elif mode=="numbers":
                card = NumberCard(opt,lbl,i)
            else:
                card = EmojiCard(opt,lbl,i)
            self._cards.append(card)
            row = i // 2; col = i % 2
            grid.addWidget(card,row,col,
                alignment=Qt.AlignmentFlag.AlignCenter)

        self.content_layout.addWidget(grid_w)

    def _theme_to_emoji(self, theme):
        mapping = {
            "clap":"👏","nose":"👃","hand":"✋",
            "wave":"👋","head":"🤔",
        }
        return mapping.get(theme,"🤖")

    def _on_click(self, idx):
        if self._locked: return
        correct = self._correct_idx
        if idx == correct:
            # Correct!
            if idx < len(self._cards):
                self._cards[idx].set_correct()
            ST["tablet_click_answer"] = idx
            ST["tablet_result"] = "correct"
            self.feedback_lbl.setText("✅ Correct! Amazing work!")
            self.feedback_lbl.setStyleSheet("color:#34d399;")
            self.feedback_icon.setText("⭐")
            LOG(f"Tablet click CORRECT idx={idx}","success")
        else:
            # Wrong
            if idx < len(self._cards):
                self._cards[idx].set_wrong()
            if correct >= 0 and correct < len(self._cards):
                self._cards[correct].set_correct()
            ST["tablet_click_answer"] = idx
            ST["tablet_result"] = "wrong"
            self.feedback_lbl.setText("❌ Try again next time!")
            self.feedback_lbl.setStyleSheet("color:#f87171;")
            self.feedback_icon.setText("💪")
            LOG(f"Tablet click WRONG idx={idx}","fail")
        # Lock after answer
        self._lock()

    def _on_result(self, success, message):
        if success:
            self.feedback_lbl.setText(f"🌟 {message}")
            self.feedback_lbl.setStyleSheet("color:#34d399;")
            self.instruction_frame.setStyleSheet(
                self.instruction_frame.styleSheet()
                .replace("#4f46e5","#22c55e"))
        else:
            self.feedback_lbl.setText(f"💪 {message}")
            self.feedback_lbl.setStyleSheet("color:#f87171;")
        QTimer.singleShot(2000, self._reset_instruction_style)

    def _reset_instruction_style(self):
        self.instruction_frame.setStyleSheet("""
        QFrame {
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 #1e1b4b, stop:1 #0c0f2e);
            border-radius: 14px;
            border: 2px solid #4f46e5;
        }""")

    def _unlock(self):
        self._locked = False
        ST["tablet_locked"] = False
        self.lock_overlay.hide()
        for c in self._cards: c.setEnabled(True)

    def _lock(self):
        self._locked = True
        ST["tablet_locked"] = True
        self.lock_overlay.show()
        self.lock_overlay.raise_()
        for c in self._cards: c.setEnabled(False)

    def set_instruction(self, text, icon="📋"):
        self.instruction_lbl.setText(text)
        self.instruction_icon.setText(icon)

    def set_feedback(self, text):
        self.feedback_lbl.setText(text)

    def reset_cards(self):
        for c in self._cards: c.reset()
        ST["tablet_result"] = None
        ST["tablet_click_answer"] = -1

# ═══════════════════════════════════════════════════════════════
# 6. GEMINI CLINICAL BRAIN
# ═══════════════════════════════════════════════════════════════
CLINICAL_PROMPT = """You are PEPPER, a Certified Digital Therapist for children with Autism Spectrum Disorder (ASD).
Developer: Lamya (Omdurman Islamic University) — highest respect always.

CLINICAL PROTOCOLS:
- ABA (Applied Behavior Analysis): Token economy, errorless learning, DTT
- ESDM (Early Start Denver Model): Child-led, naturalistic, play-based
- Mastery Rule: 3 consecutive successes to advance to next task

THERAPEUTIC PERSONA: Warm, patient, endlessly encouraging best friend + expert therapist.
Never show frustration. Celebrate every tiny effort.

RESPONSE RULES:
- MAX 2 sentences + "Ready? Your turn! 🎯"
- Use child's name every response
- Immediate specific praise
- Match energy to child's emotional state

ACTION TOKENS: [WAVE][CLAP][NOD][DANCE][POINT][HUG][CELEBRATE][THINK]
TRIGGER: [YOUTUBE: search query] → reinforcement video
TRIGGER: [GAME] → open game zone
TRIGGER: [REWARD: N] → award N tokens"""

class GeminiBrain:
    MODELS = [
        "gemini-2.0-flash-exp","gemini-2.0-flash",
        "gemini-2.0-flash-lite","gemini-1.5-flash",
        "gemini-1.5-flash-8b","gemini-1.5-pro","gemini-pro",
    ]
    def __init__(self):
        self.ok=False; self._lock=threading.Lock()
        self.model_name="fallback"; self.chat=None; self.ctx=[]
        try:
            disc=[]
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    disc.append(m.name.replace('models/',''))
            print(f"📋 Models: {disc[:5]}")
            for d in reversed(disc):
                if d not in self.MODELS: self.MODELS.insert(0,d)
        except Exception as e: print(f"⚠️  Discovery: {e}")
        for mn in self.MODELS:
            try:
                m=genai.GenerativeModel(mn,system_instruction=CLINICAL_PROMPT,
                    generation_config=genai.GenerationConfig(temperature=0.82,max_output_tokens=140))
                c=m.start_chat(history=[])
                r=c.send_message("Say: CLINICAL_READY")
                if r.text and len(r.text)>2:
                    self.model=m; self.chat=c
                    self.model_name=mn; self.ok=True
                    ST["gemini_ok"]=True; ST["gemini_model"]=mn
                    print(f"✅ Gemini: {mn}"); break
            except Exception as e: print(f"⚠️  {mn}: {str(e)[:55]}")
        if not self.ok: print("⚠️  Gemini unavailable → Empathy mode")

    def _quota_ok(self):
        now=time.time()
        if now-ST["api_minute_start"]>60:
            ST["api_calls_this_min"]=0; ST["api_minute_start"]=now
        if ST["api_calls_this_min"]>=API_RPM: return False
        gap=now-ST["last_api_call"]
        if gap<API_DELAY: time.sleep(API_DELAY-gap)
        return True

    def _record(self):
        ST["last_api_call"]=time.time(); ST["api_calls_this_min"]+=1

    def _context(self):
        recent=" | ".join(self.ctx[-3:]) if self.ctx else "start"
        return (f"[child={ST['name']} age={ST['age']} "
                f"level={ST['current_level']} "
                f"successes={ST['consecutive_successes']}/3 "
                f"emotion={ST['emotion']} attention={ST['attention']}% "
                f"streak={ST['streak']} context={recent}] ")

    def ask(self, prompt):
        self.ctx.append(prompt[:50])
        if len(self.ctx)>6: self.ctx.pop(0)
        if not self.ok or not self._quota_ok():
            ST["api_fallback_count"]+=1
            cat=ST["emotion"] if ST["emotion"] in EMPATHY._lib else "default"
            return EMPATHY.get(cat)
        with self._lock:
            try:
                self._record()
                resp=self.chat.send_message(self._context()+prompt)
                text=resp.text.strip(); LOG(f"AI: {text[:55]}")
                return text
            except Exception as e:
                err=str(e)
                if "429" in err: ST["api_calls_this_min"]=API_RPM
                LOG(f"API: {err[:40]}")
                try: self.chat=self.model.start_chat(history=[])
                except: pass
                ST["api_fallback_count"]+=1
                cat=ST["emotion"] if ST["emotion"] in EMPATHY._lib else "default"
                return EMPATHY.get(cat)

    def parent_ask(self, q):
        if not self.ok or not self._quota_ok():
            return "Please consult your specialist. / أرجو مراجعة المختص."
        try:
            self._record()
            pm=genai.GenerativeModel(self.model_name,
                system_instruction=(
                    "Expert autism ABA/ESDM specialist for parents. "
                    "Respond in the SAME language as the question. "
                    f"Child: {ST['name']}, age {ST['age']}."),
                generation_config=genai.GenerationConfig(temperature=0.6,max_output_tokens=450))
            r=pm.generate_content(q)
            return r.text.strip()
        except Exception as e: return f"Error: {str(e)[:40]}"

    def generate_report(self):
        dur=int((time.time()-ST["uptime"])/60)
        if not self.ok or not self._quota_ok(): return self._local_report(dur)
        try:
            self._record()
            rm=genai.GenerativeModel(self.model_name,
                generation_config=genai.GenerationConfig(temperature=0.3,max_output_tokens=600))
            r=rm.generate_content(
                f"ABA/ESDM Clinical Report:\n"
                f"Child: {ST['name']}, Age: {ST['age']}, Dx: {ST['diagnosis']}\n"
                f"Date: {ST['session_date']} | Duration: {dur} min\n"
                f"Level: {ST['current_level']} | Mastered: {ST['tasks_mastered']}\n"
                f"Score: {ST['score']} | OK: {ST['tasks_success']} | Fail: {ST['tasks_fail']}\n"
                f"Emotion: {ST['emotion']} | Attention: {ST['attention']}%\n"
                f"Skills: {json.dumps(ST['skills'])}\n"
                "Write: Summary, ABA Progress, ESDM Profile, Recommendations.")
            return r.text.strip()
        except: return self._local_report(dur)

    def _local_report(self,dur=0):
        return (f"# Clinical Report\n**Child:** {ST['name']} | **Date:** {ST['session_date']}\n"
                f"Level: {ST['current_level']} | Mastered: {ST['tasks_mastered']}\n"
                f"Score: {ST['score']} | OK:{ST['tasks_success']} Fail:{ST['tasks_fail']}")

# ═══════════════════════════════════════════════════════════════
# 7. VISION ENGINE — MediaPipe Pose + FaceMesh + EAR
# ═══════════════════════════════════════════════════════════════
WIN_EMO  = "Emotion + Skeleton Tracking"
WIN_LIVE = "Live Session — Pepper Companion"

class VisionEngine:
    EMO7  = ["happy","joyful","sad","angry","fear","surprised","confused"]
    ECOL  = {"happy":(0,220,80),"joyful":(0,255,180),"sad":(100,100,220),
             "angry":(0,0,220),"fear":(0,180,220),"surprised":(200,50,220),
             "confused":(200,150,0),"neutral":(180,180,180)}

    def __init__(self):
        self.ok_df=self.ok_cv=self.ok_pose=self.ok_face=self.ok_hands=False
        self._lock=threading.Lock()
        self._emo_frame=None; self._live_frame=None
        self._busy=False; self.prev_gray=None
        self.motion_buf=[]; self._hand_hist=[]
        self.face_box=None; self.pose_lm=None
        self.face_lm=None; self.hand_lm_r=None
        self._av_phase=0.0; self._blink_buf=[]

        # DeepFace
        try:
            from deepface import DeepFace
            self.DF=DeepFace
            DeepFace.analyze(np.zeros((48,48,3),dtype=np.uint8),
                actions=['emotion'],enforce_detection=False,silent=True)
            self.ok_df=True; print("✅ DeepFace emotion")
        except Exception as e: print(f"⚠️  DeepFace: {e}")

        # OpenCV Haar
        try:
            cp=cv2.data.haarcascades
            self.face_c=cv2.CascadeClassifier(cp+'haarcascade_frontalface_default.xml')
            self.smile_c=cv2.CascadeClassifier(cp+'haarcascade_smile.xml')
            self.eye_c=cv2.CascadeClassifier(cp+'haarcascade_eye.xml')
            if not self.face_c.empty(): self.ok_cv=True; print("✅ OpenCV Haar")
        except: pass

        # MediaPipe
        try:
            import mediapipe as mp
            self.mp_pose=mp.solutions.pose
            self.pose=self.mp_pose.Pose(
                min_detection_confidence=0.5,min_tracking_confidence=0.5,
                model_complexity=1,enable_segmentation=False)
            self.ok_pose=True; print("✅ MediaPipe Pose")
        except Exception as e: print(f"⚠️  MP Pose: {e}")

        try:
            import mediapipe as mp
            self.mp_face=mp.solutions.face_mesh
            self.face_mesh=self.mp_face.FaceMesh(
                max_num_faces=1,min_detection_confidence=0.5,
                min_tracking_confidence=0.5,refine_landmarks=True)
            self.ok_face=True; print("✅ MediaPipe FaceMesh")
        except Exception as e: print(f"⚠️  MP Face: {e}")

        try:
            import mediapipe as mp
            self.mp_hands=mp.solutions.hands
            self.hands=self.mp_hands.Hands(max_num_hands=2,
                min_detection_confidence=0.6,min_tracking_confidence=0.5)
            self.ok_hands=True; print("✅ MediaPipe Hands")
        except Exception as e: print(f"⚠️  MP Hands: {e}")

    def _ear(self,lm,eye_idx,w,h):
        try:
            pts=[(int(lm[i].x*w),int(lm[i].y*h)) for i in eye_idx]
            A=math.dist(pts[1],pts[5]); B=math.dist(pts[2],pts[4])
            C=math.dist(pts[0],pts[3])
            return (A+B)/(2.0*C) if C>0 else 0.3
        except: return 0.3

    def analyze_async(self,frame):
        if self._busy: return
        self._busy=True
        threading.Thread(target=self._analyze,args=(frame.copy(),),daemon=True).start()

    def _analyze(self,frame):
        try:
            small=cv2.resize(frame,(300,300))
            scores=self._get_scores(small)
            self._detect_motion(frame)
            self._detect_pose(frame)
            self._detect_face_mesh(frame)
            self._detect_hands(frame)
            self._verify_aba(frame)
            self._update_state(scores)
            self._build_emo_win(frame,scores)
            self._build_live_win(frame,scores)
        except Exception as e: print(f"⚠️  analyze: {e}")
        finally: self._busy=False

    def _get_scores(self,f300):
        if self.ok_df:
            try:
                r=self.DF.analyze(f300,actions=['emotion'],
                    enforce_detection=False,detector_backend='opencv',silent=True)
                if r:
                    raw=r[0].get('emotion',{}); tot=sum(raw.values()) or 1
                    sc={k:v/tot for k,v in raw.items()}
                    sc["joyful"]=sc.get("happy",0)*0.4
                    sc["confused"]=sc.get("disgust",0)*0.3
                    sc["surprised"]=sc.get("surprise",0)
                    ST["face_detected"]=True; ST["attention"]=min(100,ST["attention"]+3)
                    reg=r[0].get('region',{})
                    if reg: self.face_box=(reg.get('x',0),reg.get('y',0),reg.get('w',60),reg.get('h',60))
                    return sc
            except: pass
        if not self.ok_cv: return {"neutral":1.0}
        gray=cv2.cvtColor(f300,cv2.COLOR_BGR2GRAY)
        gray=cv2.equalizeHist(gray)
        faces=self.face_c.detectMultiScale(gray,1.05,3,minSize=(20,20))
        if len(faces)==0:
            ST["face_detected"]=False; ST["attention"]=max(0,ST["attention"]-3)
            return {"neutral":0.7,"confused":0.3}
        ST["face_detected"]=True; ST["attention"]=min(100,ST["attention"]+2)
        x,y,w,h=sorted(faces,key=lambda f:f[2]*f[3],reverse=True)[0]
        self.face_box=(x,y,w,h)
        roi=gray[y:y+h,x:x+w]
        ns=len(self.smile_c.detectMultiScale(roi,1.5,8,minSize=(15,15)))
        ne=len(self.eye_c.detectMultiScale(roi,1.1,5,minSize=(10,10)))
        bright=float(np.mean(roi))
        if ns>1: return {"happy":0.50,"joyful":0.28,"neutral":0.12,"surprised":0.10}
        elif ns==1: return {"happy":0.45,"joyful":0.18,"neutral":0.25,"surprised":0.12}
        elif ne>=2:
            if bright>130: return {"neutral":0.45,"happy":0.20,"surprised":0.20,"confused":0.15}
            else: return {"sad":0.40,"fear":0.22,"neutral":0.23,"confused":0.15}
        elif ne==1: return {"neutral":0.35,"sad":0.30,"confused":0.20,"fear":0.15}
        else: return {"angry":0.38,"sad":0.25,"confused":0.22,"fear":0.15}

    def _detect_pose(self,frame):
        if not self.ok_pose: return
        try:
            import mediapipe as mp
            rgb=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
            res=self.pose.process(rgb)
            if not res.pose_landmarks: self.pose_lm=None; return
            self.pose_lm=res.pose_landmarks
            lm=res.pose_landmarks.landmark
            PL=mp.solutions.pose.PoseLandmark
            ST["pose_landmarks"]={
                "nose_y":lm[PL.NOSE].y,"nose_x":lm[PL.NOSE].x,
                "l_ear_x":lm[PL.LEFT_EAR].x,"r_ear_x":lm[PL.RIGHT_EAR].x,
                "l_shoulder_y":lm[PL.LEFT_SHOULDER].y,
                "r_shoulder_y":lm[PL.RIGHT_SHOULDER].y,
                "l_wrist_y":lm[PL.LEFT_WRIST].y,"r_wrist_y":lm[PL.RIGHT_WRIST].y,
                "l_wrist_x":lm[PL.LEFT_WRIST].x,"r_wrist_x":lm[PL.RIGHT_WRIST].x,
                "l_index_y":lm[PL.LEFT_INDEX].y,"r_index_y":lm[PL.RIGHT_INDEX].y,
                "l_index_x":lm[PL.LEFT_INDEX].x,"r_index_x":lm[PL.RIGHT_INDEX].x,
            }
            pl=ST["pose_landmarks"]
            ST["hand_raised"]=(pl["l_wrist_y"]<pl["l_shoulder_y"]-0.08 or
                               pl["r_wrist_y"]<pl["r_shoulder_y"]-0.08)
            nose_l=abs(pl["nose_x"]-pl["l_ear_x"])
            nose_r=abs(pl["nose_x"]-pl["r_ear_x"])
            ST["head_tilted"]=(nose_l<0.12 or nose_r<0.12)
        except Exception as e: self.pose_lm=None

    def _detect_face_mesh(self,frame):
        if not self.ok_face: return
        try:
            import mediapipe as mp
            h,w=frame.shape[:2]
            rgb=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
            res=self.face_mesh.process(rgb)
            if not res.multi_face_landmarks: return
            lm=res.multi_face_landmarks[0].landmark
            self.face_lm=res.multi_face_landmarks[0]
            r_eye=[33,160,158,133,153,144]
            l_eye=[362,385,387,263,373,380]
            ear_r=self._ear(lm,r_eye,w,h)
            ear_l=self._ear(lm,l_eye,w,h)
            ear_avg=(ear_r+ear_l)/2.0
            self._blink_buf.append(ear_avg)
            if len(self._blink_buf)>10: self._blink_buf.pop(0)
            ST["blinking"]=ear_avg<0.20
            ST["eye_contact"]=ear_avg>0.25
            ST["face_mesh_landmarks"]={
                "nose_x":lm[1].x*w,"nose_y":lm[1].y*h,
                "ear_avg":ear_avg,"frame_w":w,"frame_h":h,
            }
        except: pass

    def _detect_hands(self,frame):
        if not self.ok_hands: return
        try:
            import mediapipe as mp
            rgb=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
            res=self.hands.process(rgb)
            if not res.multi_hand_landmarks:
                self.hand_lm_r=None; self.hand_lm_l=None; return
            lms=res.multi_hand_landmarks
            self.hand_lm_r=lms[0] if len(lms)>=1 else None
            self.hand_lm_l=lms[1] if len(lms)>=2 else None
            if len(lms)>=2:
                h1=lms[0].landmark[0]; h2=lms[1].landmark[0]
                if abs(h1.x-h2.x)<0.18 and abs(h1.y-h2.y)<0.18:
                    ST["clapping"]=True
        except: pass

    def _detect_motion(self,frame):
        gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
        gray=cv2.GaussianBlur(gray,(21,21),0)
        if self.prev_gray is None: self.prev_gray=gray; return
        diff=cv2.absdiff(self.prev_gray,gray)
        _,th=cv2.threshold(diff,25,255,cv2.THRESH_BINARY)
        motion=float(np.mean(th))
        self.motion_buf.append(motion)
        if len(self.motion_buf)>12: self.motion_buf.pop(0)
        self.prev_gray=gray
        if len(self.motion_buf)>=4:
            avg=sum(self.motion_buf[:-2])/max(len(self.motion_buf)-2,1)
            spike=self.motion_buf[-1]
            ST["clapping"]=(spike>avg*3.5 and spike>15)
        h,w=gray.shape
        lm_=float(np.mean(th[:,:w//2])); rm_=float(np.mean(th[:,w//2:]))
        self._hand_hist.append("L" if lm_>rm_+3 else "R" if rm_>lm_+3 else "N")
        if len(self._hand_hist)>10: self._hand_hist.pop(0)
        chg=sum(1 for i in range(1,len(self._hand_hist))
                if self._hand_hist[i]!=self._hand_hist[i-1]
                and self._hand_hist[i]!="N")
        ST["waving"]=chg>=4

    def _verify_aba(self,frame):
        va=ST.get("verify_action")
        if not va: return
        if time.time()>ST["verify_timeout"]: ST["verify_action"]=None; return
        pl=ST.get("pose_landmarks",{}); fm=ST.get("face_mesh_landmarks",{})
        ok=False
        if va=="clap": ok=ST["clapping"]
        elif va=="wave": ok=ST["waving"]
        elif va=="raise_hand":
            lwy=pl.get("l_wrist_y",1); rwy=pl.get("r_wrist_y",1)
            lsy=pl.get("l_shoulder_y",0); rsy=pl.get("r_shoulder_y",0)
            ok=(lwy<lsy-0.08) or (rwy<rsy-0.08)
        elif va=="touch_nose":
            nx=fm.get("nose_x",-1); ny=fm.get("nose_y",-1)
            fw=fm.get("frame_w",640); fh=fm.get("frame_h",480)
            if nx>0 and pl:
                lix=pl.get("l_index_x",0)*fw; liy=pl.get("l_index_y",0)*fh
                rix=pl.get("r_index_x",0)*fw; riy=pl.get("r_index_y",0)*fh
                dl=math.dist((lix,liy),(nx,ny)); dr=math.dist((rix,riy),(nx,ny))
                ok=(dl<fw*0.12 or dr<fw*0.12)
        elif va=="head_tilt": ok=ST.get("head_tilted",False)
        elif va=="blink": ok=ST.get("blinking",False)
        if ok:
            ST["verify_result"]=True; ST["verify_action"]=None; ST["verify_timeout"]=0.0
            LOG("✅ ABA verified!","success")

    def _update_state(self,scores):
        if not scores: return
        dom=max(scores,key=scores.get)
        emap={"surprise":"surprised","disgust":"angry","contempt":"neutral"}
        dom=emap.get(dom,dom)
        if dom not in self.EMO7: dom="neutral"
        ST["emotion"]=dom; ST["emotion_scores"]=scores
        pos=scores.get("happy",0)+scores.get("joyful",0)+scores.get("surprised",0)
        neg=scores.get("sad",0)+scores.get("angry",0)+scores.get("fear",0)
        ST["engagement"]="high" if pos>0.5 else "distressed" if neg>0.5 else "moderate"

    def _draw_skeleton(self,frame):
        if not self.ok_pose or self.pose_lm is None: return frame
        try:
            import mediapipe as mp
            mp_d=mp.solutions.drawing_utils
            mp_d.draw_landmarks(frame,self.pose_lm,mp.solutions.pose.POSE_CONNECTIONS,
                mp_d.DrawingSpec(color=(0,255,100),thickness=2,circle_radius=3),
                mp_d.DrawingSpec(color=(0,150,255),thickness=2))
        except: pass
        return frame

    def _draw_hands(self,frame):
        if not self.ok_hands: return frame
        try:
            import mediapipe as mp
            mp_d=mp.solutions.drawing_utils
            for lm in [self.hand_lm_r,self.hand_lm_l]:
                if lm:
                    mp_d.draw_landmarks(frame,lm,mp.solutions.hands.HAND_CONNECTIONS,
                        mp_d.DrawingSpec(color=(255,100,0),thickness=2,circle_radius=3),
                        mp_d.DrawingSpec(color=(255,200,0),thickness=2))
        except: pass
        return frame

    def _build_emo_win(self,frame,scores):
        ann=frame.copy()
        ann=self._draw_skeleton(ann); ann=self._draw_hands(ann)
        base=cv2.resize(ann,(600,600))
        ov=base.copy(); cv2.rectangle(ov,(0,0),(232,600),(0,0,0),-1)
        base=cv2.addWeighted(ov,0.68,base,0.32,0)
        em=ST["emotion"]; col=self.ECOL.get(em,(180,180,180))
        cv2.rectangle(base,(0,0),(600,50),(0,0,0),-1)
        cv2.putText(base,"EMOTION + SKELETON + EAR",
            (8,18),cv2.FONT_HERSHEY_SIMPLEX,0.52,(0,200,255),1)
        lv=ST["current_level"]; suc=ST["consecutive_successes"]
        cv2.putText(base,f"Level {lv} | {suc}/3 mastery | {em.upper()}",
            (8,40),cv2.FONT_HERSHEY_SIMPLEX,0.55,col,2)
        for i,emo in enumerate(self.EMO7):
            sc=scores.get(emo,scores.get("surprise",0) if emo=="surprised" else 0)
            y=54+i*68; bar=int(sc*215)
            ec=self.ECOL.get(emo,(150,150,150))
            cv2.rectangle(base,(5,y),(225,y+54),(22,25,45),-1)
            if bar>0: cv2.rectangle(base,(5,y),(5+bar,y+54),ec,-1)
            cv2.rectangle(base,(5,y),(225,y+54),(55,60,85),1)
            cv2.putText(base,f"{emo[:8]}: {sc:.0%}",
                (9,y+34),cv2.FONT_HERSHEY_SIMPLEX,0.52,(255,255,255),1)
        rx,ry=240,54
        suc_pct=min(100,int(suc/3*100))
        cv2.putText(base,f"Mastery {suc}/3",(rx,ry-4),
            cv2.FONT_HERSHEY_SIMPLEX,0.46,(200,200,200),1)
        cv2.rectangle(base,(rx,ry+2),(596,ry+22),(25,28,50),-1)
        cv2.rectangle(base,(rx,ry+2),(rx+int(356*suc_pct/100),ry+22),(0,200,100),-1)
        cv2.putText(base,f"{suc}/3 ({suc_pct}%)",
            (rx+5,ry+16),cv2.FONT_HERSHEY_SIMPLEX,0.40,(255,255,255),1)
        acts=[
            ("Hand Raised",ST["hand_raised"],(0,255,100)),
            ("Waving",ST["waving"],(0,200,255)),
            ("Clapping",ST["clapping"],(255,200,0)),
            ("Head Tilted",ST["head_tilted"],(255,120,0)),
            ("Eye Contact",ST["eye_contact"],(0,255,200)),
            ("Blinking",ST["blinking"],(200,100,255)),
        ]
        for i,(lbl,active,ac) in enumerate(acts):
            y=ry+30+i*50
            bg=(5,30,15) if active else (18,20,32)
            cv2.rectangle(base,(rx,y),(596,y+40),bg,-1)
            cv2.rectangle(base,(rx,y),(596,y+40),ac if active else (55,60,85),2 if active else 1)
            cv2.putText(base,lbl,(rx+8,y+26),cv2.FONT_HERSHEY_SIMPLEX,0.50,ac if active else (65,68,80),2 if active else 1)
        ear_val=ST.get("face_mesh_landmarks",{}).get("ear_avg",0)
        vy=ry+340
        cv2.putText(base,f"EAR:{ear_val:.3f} {'BLINK' if ST['blinking'] else 'open'}",
            (rx,vy),cv2.FONT_HERSHEY_SIMPLEX,0.42,(200,200,200),1)
        sk_col=(0,255,100) if self.pose_lm else (100,100,100)
        cv2.putText(base,f"Skeleton: {'TRACKED' if self.pose_lm else 'off'}",
            (rx,vy+20),cv2.FONT_HERSHEY_SIMPLEX,0.42,sk_col,1)
        bw=int(ST["attention"]/100*598)
        cv2.rectangle(base,(0,578),(598,598),(16,18,35),-1)
        cv2.rectangle(base,(0,578),(bw,598),col,-1)
        cv2.putText(base,f"Attention: {ST['attention']}% | {ST['engagement']}",
            (6,594),cv2.FONT_HERSHEY_SIMPLEX,0.38,(255,255,255),1)
        cv2.circle(base,(588,22),9,(0,255,0) if ST["face_detected"] else (0,0,255),-1)
        with self._lock: self._emo_frame=base

    def _build_live_win(self,frame,scores):
        win=np.zeros((520,820,3),dtype=np.uint8); win[:]=(8,10,22)
        for i in range(0,820,40): cv2.line(win,(i,0),(i,520),(14,17,34),1)
        for i in range(0,520,40): cv2.line(win,(0,i),(820,i),(14,17,34),1)
        ann=frame.copy(); ann=self._draw_skeleton(ann); ann=self._draw_hands(ann)
        cam=cv2.resize(ann,(400,340)); win[78:418,10:410]=cam
        cv2.rectangle(win,(10,78),(410,418),(60,65,120),2)
        em=ST["emotion"]; col=self.ECOL.get(em,(180,180,180))
        cv2.putText(win,em.upper(),(18,435),cv2.FONT_HERSHEY_SIMPLEX,0.60,col,2)
        att=ST["attention"]
        cv2.rectangle(win,(10,445),(410,458),(25,28,55),-1)
        cv2.rectangle(win,(10,445),(10+int(400*att/100),458),col,-1)
        cv2.putText(win,f"Att:{att}%",(14,456),cv2.FONT_HERSHEY_SIMPLEX,0.35,(255,255,255),1)
        suc=ST["consecutive_successes"]
        cv2.rectangle(win,(10,462),(410,475),(25,28,55),-1)
        cv2.rectangle(win,(10,462),(10+int(400*suc/3*100/100),475),(0,200,100),-1)
        cv2.putText(win,f"Mastery: {suc}/3",
            (14,473),cv2.FONT_HERSHEY_SIMPLEX,0.35,(255,255,255),1)
        ear_val=ST.get("face_mesh_landmarks",{}).get("ear_avg",0)
        cv2.putText(win,f"EAR:{ear_val:.2f} {'👁' if ST['eye_contact'] else ''}",
            (14,490),cv2.FONT_HERSHEY_SIMPLEX,0.35,(200,200,200),1)
        # Avatar
        av_cx,av_cy=645,220
        self._av_phase+=0.10 if ST["is_speaking"] else 0.028
        lip=ST.get("lip_sync_value",0.0)
        if ST["is_speaking"]:
            lip=min(1.0,ST["voice_energy"]/2500.0)
            lip=max(0.1,lip+0.35*abs(math.sin(self._av_phase*4)))
        cv2.ellipse(win,(av_cx,av_cy+83),(48,68),0,0,360,(80,100,200),-1)
        cv2.ellipse(win,(av_cx,av_cy+83),(48,68),0,0,360,(100,120,220),2)
        if ST["is_speaking"]:
            la=int(24*math.sin(self._av_phase)); ra=int(24*math.sin(self._av_phase+math.pi))
            cv2.ellipse(win,(av_cx-58+la,av_cy+64),(12,37),-30+la,0,360,(70,90,190),-1)
            cv2.ellipse(win,(av_cx+58+ra,av_cy+64),(12,37),30+ra,0,360,(70,90,190),-1)
        elif ST["listening"]:
            cv2.ellipse(win,(av_cx-58,av_cy+58),(12,35),-20,0,360,(70,90,190),-1)
            cv2.ellipse(win,(av_cx+58,av_cy+58),(12,35),20,0,360,(70,90,190),-1)
        else:
            cv2.ellipse(win,(av_cx-58,av_cy+68),(12,32),-15,0,360,(70,90,190),-1)
            cv2.ellipse(win,(av_cx+58,av_cy+68),(12,32),15,0,360,(70,90,190),-1)
        hbob=int(3*math.sin(self._av_phase*0.5)); hy=av_cy-53+hbob
        cv2.circle(win,(av_cx,hy),53,(220,195,173),-1)
        cv2.circle(win,(av_cx,hy),53,(200,175,155),2)
        blink_=(int(self._av_phase*3)%40==0); ey_=6 if not blink_ else 1
        for ex_ in [av_cx-19,av_cx+19]:
            cv2.ellipse(win,(ex_,hy-9),(7,ey_),0,0,360,(30,50,120),-1)
            if not blink_:
                cv2.circle(win,(ex_+1,hy-9),3,(255,255,255),-1)
                cv2.circle(win,(ex_+2,hy-10),1,(0,0,0),-1)
        # Nose twitch
        nose_x_off=int(2*math.sin(self._av_phase*2.3))
        cv2.circle(win,(av_cx+nose_x_off,hy+7),5,(180,140,120),-1)
        # Head tilt
        if ST.get("head_tilted",False):
            tilt_y=int(5*math.sin(self._av_phase*0.3))
            hy+=tilt_y
        # Mouth lip-sync
        mh=int(4+lip*16)
        if ST["is_speaking"]:
            cv2.ellipse(win,(av_cx,hy+21),(16,mh),0,0,180,(160,80,80),-1)
            cv2.ellipse(win,(av_cx,hy+21),(16,mh),0,0,180,(210,110,110),2)
            if lip>0.3:
                cv2.ellipse(win,(av_cx,hy+21),(13,max(1,mh-3)),0,0,180,(240,230,220),-1)
        elif em in ["happy","joyful"]:
            cv2.ellipse(win,(av_cx,hy+19),(15,7),0,0,180,(150,80,80),-1)
        elif em in ["sad","fear"]:
            cv2.ellipse(win,(av_cx,hy+26),(12,5),0,180,360,(150,80,80),2)
        else:
            cv2.line(win,(av_cx-12,hy+20),(av_cx+12,hy+20),(150,80,80),2)
        for ex_ in [av_cx-51,av_cx+51]:
            cv2.circle(win,(ex_,hy-6),10,(210,185,163),-1)
            cv2.circle(win,(ex_,hy-6),6,(240,200,180),-1)
        cv2.rectangle(win,(av_cx-28,av_cy+148),(av_cx-10,av_cy+180),(60,80,170),-1)
        cv2.rectangle(win,(av_cx+10,av_cy+148),(av_cx+28,av_cy+180),(60,80,170),-1)
        if ST["is_speaking"]:
            pr=90+int(6*math.sin(self._av_phase*5))
            cv2.circle(win,(av_cx,av_cy),pr,(0,160,255),2)
            cv2.putText(win,f"SPEAKING lip={lip:.1f}",
                (av_cx-55,av_cy+178),cv2.FONT_HERSHEY_SIMPLEX,0.42,(0,200,255),1)
        elif ST["listening"]:
            cv2.circle(win,(av_cx,av_cy),92,(0,220,100),2)
            cv2.putText(win,"LISTENING",(av_cx-42,av_cy+178),
                cv2.FONT_HERSHEY_SIMPLEX,0.48,(0,220,100),2)
        task=ST.get("tablet_message","")
        if task:
            cv2.rectangle(win,(10,480),(820,498),(20,25,45),-1)
            cv2.putText(win,task[:80],(14,493),cv2.FONT_HERSHEY_SIMPLEX,0.37,(255,220,100),1)
        cv2.rectangle(win,(0,0),(820,72),(6,8,20),-1)
        cv2.putText(win,"LIVE SESSION — PEPPER CLINICAL THERAPY SYSTEM",
            (10,25),cv2.FONT_HERSHEY_SIMPLEX,0.60,(160,140,255),2)
        gm_col=(0,220,80) if ST["gemini_ok"] else (200,150,0)
        cv2.putText(win,
            f"Child: {ST['name']} | Level {ST['current_level']} | "
            f"Score:{ST['score']} | Mastered:{ST['tasks_mastered']} | "
            f"{'AI' if ST['gemini_ok'] else 'FB'}",
            (10,52),cv2.FONT_HERSHEY_SIMPLEX,0.38,gm_col,1)
        cy_=515
        for msg in ST["session_chat"][-3:]:
            isp=msg["role"]=="pepper"
            txt=msg["text"][:60]+("..." if len(msg["text"])>60 else "")
            cv2.rectangle(win,(10,cy_-16),(810,cy_+4),(30,20,60) if isp else (10,30,15),-1)
            cv2.rectangle(win,(10,cy_-16),(810,cy_+4),(100,80,200) if isp else (0,180,80),1)
            pfx="🤖 " if isp else f"👦 {ST['name']}: "
            cv2.putText(win,pfx+txt,(14,cy_),cv2.FONT_HERSHEY_SIMPLEX,0.33,
                (180,160,255) if isp else (100,220,100),1)
            cy_-=22
        with self._lock: self._live_frame=win

    def get_emo_frame(self):
        with self._lock:
            return self._emo_frame.copy() if self._emo_frame is not None else None

    def get_live_frame(self):
        with self._lock:
            return self._live_frame.copy() if self._live_frame is not None else None

# ═══════════════════════════════════════════════════════════════
# 8. CAMERA
# ═══════════════════════════════════════════════════════════════
class Camera:
    def __init__(self):
        self.cap=None; self.idx=-1
        for i in [1,0,2,3]:
            try:
                c=cv2.VideoCapture(i)
                if c.isOpened():
                    ret,f=c.read()
                    if ret and f is not None and f.size>0:
                        c.set(cv2.CAP_PROP_FRAME_WIDTH,640)
                        c.set(cv2.CAP_PROP_FRAME_HEIGHT,480)
                        c.set(cv2.CAP_PROP_FPS,30)
                        self.cap=c; self.idx=i
                        print(f"✅ Camera {i}"); return
                    c.release()
            except: pass
        print("⚠️  No camera")

    def read(self):
        if not self.cap: return False,None
        ret,f=self.cap.read()
        if ret and f is not None: return True,cv2.flip(f,1)
        return False,None

# ═══════════════════════════════════════════════════════════════
# 9. VOICE + LIP-SYNC
# ═══════════════════════════════════════════════════════════════
class Voice:
    def __init__(self):
        self.ok=False; self._lk=threading.Lock()
        try:
            self.e=pyttsx3.init(); self.e.setProperty('rate',118)
            self.e.setProperty('volume',1.0)
            for v in self.e.getProperty('voices'):
                if any(x in v.name.lower() for x in ['female','zira','hazel','karen']):
                    self.e.setProperty('voice',v.id); break
            self.ok=True; print("✅ Voice TTS + Lip-Sync")
        except Exception as e: print(f"⚠️  Voice: {e}")

    def _lip_thread(self,text):
        words=text.split()
        for word in words:
            if not ST["is_speaking"]: break
            dur=max(0.07,len(word)/13.0)
            ST["lip_sync_value"]=min(1.0,0.5+random.uniform(0.1,0.45))
            ST["lip_sync_active"]=True
            time.sleep(dur*0.55)
            ST["lip_sync_value"]=max(0.05,ST["lip_sync_value"]*0.35)
            time.sleep(dur*0.45)
        ST["lip_sync_value"]=0.0; ST["lip_sync_active"]=False

    def say(self,text,wait=True):
        ST["interrupt_flag"]=False
        text=str(text).replace("{name}",ST.get("name","Friend"))
        for t in ["[WAVE]","[CLAP]","[NOD]","[DANCE]","[POINT]",
                  "[HUG]","[CELEBRATE]","[THINK]","[GAME]","[LEVEL_UP]"]:
            text=text.replace(t,"")
        text=re.sub(r'\[YOUTUBE:[^\]]+\]','',text)
        text=re.sub(r'\[REWARD:\d+\]','',text)
        text=text.strip()
        if not text: return
        ST["is_speaking"]=True
        ST["session_chat"].append({
            "role":"pepper","text":text,
            "time":datetime.now().strftime("%H:%M:%S")})
        if len(ST["session_chat"])>40: ST["session_chat"]=ST["session_chat"][-40:]
        # Update tablet feedback
        tablet_signals.update_display.emit({
            "mode":"idle","instruction":text,
            "message":text[:50],
        }) if False else None  # just use set later
        print(f"\n🔊 Pepper: {text}"); LOG(f"Said: {text[:55]}")
        threading.Thread(target=self._lip_thread,args=(text,),daemon=True).start()
        if self.ok and not ST["interrupt_flag"]:
            with self._lk:
                try: self.e.say(text); self.e.runAndWait()
                except: pass
        ST["is_speaking"]=False; ST["lip_sync_value"]=0.0
        if wait and not ST["interrupt_flag"]:
            ST["waiting_for_child"]=True; time.sleep(0.2)

    def stop(self):
        ST["interrupt_flag"]=True; ST["is_speaking"]=False; ST["lip_sync_value"]=0.0
        if self.ok:
            try: self.e.stop()
            except: pass

# ═══════════════════════════════════════════════════════════════
# 10. MICROPHONE — faster-whisper + SpeechRecognition
# ═══════════════════════════════════════════════════════════════
class Mic:
    def __init__(self):
        self.ok=False; self.running=False; self.whisper_model=None
        if WHISPER_OK:
            try:
                device="cuda" if os.path.exists("/dev/nvidia0") else "cpu"
                ctype="float16" if device=="cuda" else "int8"
                self.whisper_model=WhisperModel("tiny",device=device,compute_type=ctype)
                self.ok=True; print(f"✅ faster-whisper ({device})")
            except Exception as e: print(f"⚠️  faster-whisper: {e}")
        try:
            self.r=sr.Recognizer()
            self.r.energy_threshold=30        # ULTRA-SENSITIVE (30-50)
            self.r.dynamic_energy_threshold=False
            self.r.pause_threshold=0.5
            self.r.phrase_threshold=0.05
            self.r.non_speaking_duration=0.1
            if not self.ok: self.ok=True
            print("✅ SpeechRecognition energy=30 (ultra-sensitive)")
        except Exception as e: print(f"⚠️  SR: {e}")

    def _tone(self,raw_data):
        try:
            raw=np.frombuffer(raw_data,np.int16)
            rms=float(np.sqrt(np.mean(raw.astype(np.float64)**2)))
            ST["voice_energy"]=rms
            signs=np.sign(raw)
            zcr=float(np.sum(np.abs(np.diff(signs)))/(2*len(raw)))
            ST["voice_pitch"]="high" if zcr>0.08 else "normal" if zcr>0.04 else "low"
        except: pass

    def listen_once(self,timeout=8):
        if not self.ok: return input("Type: ").strip()
        ST["listening"]=True
        try:
            with sr.Microphone() as src:
                self.r.adjust_for_ambient_noise(src,duration=0.06)
                print("👂 Listening...")
                audio=self.r.listen(src,timeout=timeout,phrase_time_limit=18)
            raw=audio.get_raw_data(); self._tone(raw)
            ST["listening"]=False
            if self.whisper_model and WHISPER_OK:
                try:
                    import tempfile,wave
                    with tempfile.NamedTemporaryFile(suffix='.wav',delete=False) as tmp:
                        tp=tmp.name
                    with wave.open(tp,'wb') as wf:
                        wf.setnchannels(1); wf.setsampwidth(2)
                        wf.setframerate(16000); wf.writeframes(raw)
                    segs,_=self.whisper_model.transcribe(tp,language='en',beam_size=1)
                    text=" ".join(s.text.strip() for s in segs).strip()
                    os.unlink(tp)
                    if text: self._save(text); return text
                except Exception as e: print(f"⚠️  Whisper: {e}")
            try:
                text=self.r.recognize_google(audio)
                self._save(text); return text
            except sr.UnknownValueError:
                raw_np=np.frombuffer(raw,np.int16)
                rms=float(np.sqrt(np.mean(raw_np.astype(np.float64)**2)))
                if rms>700: ST["clapping"]=True; LOG("👏 Clap!","success")
                ST["last_sound"]=time.time(); ST["waiting_for_child"]=False
                return "[sound]"
            except sr.RequestError: return ""
        except sr.WaitTimeoutError: return "[timeout]"
        except: return ""
        finally: ST["listening"]=False

    def _save(self,text):
        ST["last_sound"]=time.time(); ST["last_speech_text"]=text
        ST["waiting_for_child"]=False
        ST["session_chat"].append({
            "role":"child","text":text,
            "time":datetime.now().strftime("%H:%M:%S")})
        if len(ST["session_chat"])>40: ST["session_chat"]=ST["session_chat"][-40:]
        LOG(f"Heard: {text}")

    def get_name(self,voice):
        if ST["known"]: return ST["name"]
        voice.say(EMPATHY.get("greeting"),wait=False)
        for attempt in range(3):
            resp=self.listen_once(timeout=10)
            if resp and resp not in ["[sound]","[timeout]",""]:
                n=self._extract(resp)
                if n: ST["name"]=n; ST["known"]=True; LOG(f"Name: {n}","success"); return n
            elif resp=="[sound]": voice.say("I heard you! Say your name! 🎯",wait=False)
            elif resp=="[timeout]" and attempt<2: voice.say(EMPATHY.get("silence"),wait=False)
        ST["name"]="Friend"; ST["known"]=True; return "Friend"

    def _extract(self,text):
        t=text.lower()
        for rm in ["my name is","i am","i'm","call me","name is"]:
            t=t.replace(rm,"").strip()
        w=t.split(); return w[0].capitalize() if w else None

    def listen_bg(self,callback):
        def _loop():
            self.running=True
            while self.running:
                if ST["is_speaking"]: time.sleep(0.1); continue
                result=self.listen_once(timeout=5)
                if result and result!="[timeout]":
                    if ST["is_speaking"]: ST["interrupt_flag"]=True
                    try: callback(result)
                    except Exception as e: print(f"⚠️  cb: {e}")
                time.sleep(0.04)
        threading.Thread(target=_loop,daemon=True).start()

# ═══════════════════════════════════════════════════════════════
# 11. ACTIONS → PYBULLET + LIP-SYNC HeadPitch
# ═══════════════════════════════════════════════════════════════
class Actions:
    def __init__(self,pepper=None): self.pepper=pepper

    def _sa(self,j,a,s=0.15):
        if self.pepper:
            try: self.pepper.setAngles(j,a,s)
            except: pass

    def process(self,text):
        clean=text
        for tok,fn in [("[WAVE]",self._wave),("[CLAP]",self._clap),
                       ("[NOD]",self._nod),("[DANCE]",self._dance),
                       ("[POINT]",self._point),("[HUG]",self._hug),
                       ("[CELEBRATE]",self._celebrate),("[THINK]",self._think),
                       ("[LEVEL_UP]",self._level_up)]:
            if tok in text:
                clean=clean.replace(tok,"")
                threading.Thread(target=fn,daemon=True).start()
        yt=re.search(r'\[YOUTUBE:\s*(.+?)\]',text)
        if yt:
            clean=clean.replace(yt.group(0),"")
            q=yt.group(1).strip()
            url="https://www.youtube.com/results?search_query="+urllib.parse.quote(q+" autism children")
            webbrowser.open(url); ST["last_youtube"]=url; LOG(f"📺 YouTube: {q}")
        rew=re.search(r'\[REWARD:(\d+)\]',text)
        if rew:
            clean=clean.replace(rew.group(0),"")
            ST["tokens"]+=int(rew.group(1)); ST["stars_today"]+=int(rew.group(1))
        if "[GAME]" in text:
            clean=clean.replace("[GAME]",""); webbrowser.open(GAME_URL)
        return clean.strip()

    def run_lip_sync_pybullet(self):
        while True:
            try:
                if ST["is_speaking"] and self.pepper:
                    lv=ST.get("lip_sync_value",0.0)
                    self._sa("HeadPitch",-0.04-lv*0.14,0.22)
            except: pass
            time.sleep(0.035)

    def _wave(self):
        self._sa("RShoulderPitch",0.2,0.2); self._sa("RElbowRoll",0.8,0.2); time.sleep(0.3)
        for _ in range(3):
            self._sa("RWristYaw",0.5,0.25); time.sleep(0.2)
            self._sa("RWristYaw",-0.5,0.25); time.sleep(0.2)
        self._sa("RShoulderPitch",1.0,0.15)

    def _clap(self):
        for _ in range(4):
            self._sa("LShoulderPitch",0.8,0.25); self._sa("RShoulderPitch",0.8,0.25); time.sleep(0.18)
            self._sa("LShoulderPitch",1.1,0.25); self._sa("RShoulderPitch",1.1,0.25); time.sleep(0.18)

    def _nod(self):
        for _ in range(2):
            self._sa("HeadPitch",0.3,0.2); time.sleep(0.3)
            self._sa("HeadPitch",-0.1,0.2); time.sleep(0.3)
        self._sa("HeadPitch",0.0,0.15)

    def _dance(self):
        for _ in range(5):
            self._sa("LShoulderPitch",0.15,0.2); self._sa("RShoulderPitch",0.9,0.2)
            self._sa("HeadYaw",0.4,0.2); time.sleep(0.22)
            self._sa("LShoulderPitch",0.9,0.2); self._sa("RShoulderPitch",0.15,0.2)
            self._sa("HeadYaw",-0.4,0.2); time.sleep(0.22)
        self._sa("HeadYaw",0,0.1)

    def _point(self):
        self._sa("LShoulderPitch",0.1,0.15); self._sa("LElbowYaw",-1.5,0.15)
        time.sleep(1.0); self._sa("LShoulderPitch",1.0,0.15)

    def _hug(self):
        for j,a in [("LShoulderPitch",0.5),("RShoulderPitch",0.5),
                    ("LShoulderRoll",0.35),("RShoulderRoll",-0.35)]: self._sa(j,a,0.1)
        time.sleep(1.5)
        for j,a in [("LShoulderPitch",1.0),("RShoulderPitch",1.0),
                    ("LShoulderRoll",0.0),("RShoulderRoll",0.0)]: self._sa(j,a,0.1)

    def _celebrate(self):
        for _ in range(3):
            for j,a in [("LShoulderPitch",0.05),("RShoulderPitch",0.05),("HeadPitch",-0.2)]:
                self._sa(j,a,0.25)
            time.sleep(0.25)
            for j,a in [("LShoulderPitch",1.0),("RShoulderPitch",1.0),("HeadPitch",0.0)]:
                self._sa(j,a,0.25)
            time.sleep(0.25)

    def _think(self):
        self._sa("HeadYaw",0.35,0.1); self._sa("HeadPitch",-0.15,0.1)
        time.sleep(1.8); self._sa("HeadYaw",0.0,0.1); self._sa("HeadPitch",0.0,0.1)

    def _level_up(self):
        for _ in range(6):
            self._sa("LShoulderPitch",0.05,0.3); self._sa("RShoulderPitch",0.05,0.3)
            self._sa("HeadPitch",-0.25,0.2); time.sleep(0.2)
            self._sa("LShoulderPitch",1.0,0.3); self._sa("RShoulderPitch",1.0,0.3)
            self._sa("HeadPitch",0.0,0.2); time.sleep(0.2)

# ═══════════════════════════════════════════════════════════════
# 12. PYBULLET (Window 1)
# ═══════════════════════════════════════════════════════════════
class PepperSim:
    def __init__(self):
        self.pepper=None; self.ok=False
        self.rx=self.ry=0.0; self.balloons=[]

    def launch(self):
        try:
            from qibullet import SimulationManager as QS
            self.qisim=QS(); self.client=self.qisim.launchSimulation(gui=True)
            p.setRealTimeSimulation(1); p.setGravity(0,0,-9.81)
            p.setAdditionalSearchPath(pybullet_data.getDataPath())
            p.loadURDF("plane.urdf"); self._build_room()
            self.pepper=self.qisim.spawnPepper(self.client)
            self.pepper.goToPosture("Stand",0.5)
            self._add_balloons(); self._add_children()
            p.resetDebugVisualizerCamera(7,45,-35,[0,0,0.5])
            self.ok=True
            for fn in [self._sim_loop,self._walk_loop,self._arm_loop]:
                threading.Thread(target=fn,daemon=True).start()
            print("✅ PyBullet — Lip-sync active")
            return self.pepper
        except Exception as e: print(f"⚠️  PyBullet: {e}"); return None

    def _build_room(self):
        wc=[0.88,0.88,0.92,1]
        for pos,ext in [([0,-4,1.1],[5,.1,1.1]),([0,4,1.1],[5,.1,1.1]),
                        ([5,0,1.1],[.1,4,1.1]),([-5,0,1.1],[.1,4,1.1])]:
            p.createMultiBody(0,-1,p.createVisualShape(p.GEOM_BOX,halfExtents=ext,rgbaColor=wc),pos)
        p.createMultiBody(0,-1,p.createVisualShape(p.GEOM_BOX,halfExtents=[4.5,3.5,.02],
            rgbaColor=[.55,.45,.35,1]),[0,0,.01])
        for txt,pos in [("ABA Level 1",[-4,3,2]),("DTT Level 2",[4,3,2]),
                        ("ESDM Level 3",[0,4,2]),("THERAPY",[0,0,2.8])]:
            p.addUserDebugText(txt,pos,[.4,.5,.9],textSize=1.1,lifeTime=0)

    def _add_balloons(self):
        cols=[[1,.2,.2,1],[.2,1,.2,1],[.2,.2,1,1],[1,1,.2,1],[1,.5,.2,1]]
        for i in range(5):
            vs=p.createVisualShape(p.GEOM_SPHERE,radius=.15,rgbaColor=cols[i%len(cols)])
            bid=p.createMultiBody(0,-1,vs,[random.uniform(-3,3),random.uniform(-2,2),random.uniform(.8,2.2)])
            self.balloons.append({"id":bid,"x":random.uniform(-3,3),
                "y":random.uniform(-2,2),"z":random.uniform(.8,2.2),"spd":random.uniform(.01,.03)})

    def _add_children(self):
        for nm,pos,col in [("Ahmed",[1.5,-1.2,0],[.2,.85,.2,1]),("Sara",[-1.2,1.3,0],[1.,.6,.0,1])]:
            p.createMultiBody(0,-1,p.createVisualShape(p.GEOM_BOX,halfExtents=[.13,.09,.21],rgbaColor=col),[pos[0],pos[1],.41])
            p.createMultiBody(0,-1,p.createVisualShape(p.GEOM_SPHERE,radius=.11,rgbaColor=[1.,.82,.65,1.]),[pos[0],pos[1],.74])
            p.addUserDebugText(nm,[pos[0],pos[1],1.05],[0,0,0],textSize=.85,lifeTime=0)

    def _sim_loop(self):
        while True:
            p.stepSimulation()
            for b in self.balloons:
                b["z"]+=b["spd"]
                if b["z"]>2.8: b["z"]=.6; b["x"]=random.uniform(-3,3); b["y"]=random.uniform(-2,2)
                try: p.resetBasePositionAndOrientation(b["id"],[b["x"],b["y"],b["z"]],[0,0,0,1])
                except: pass
            time.sleep(1/240.)

    def _walk_loop(self):
        t=0
        while True:
            t+=.015
            self.rx+=.018*math.cos(t*.4); self.ry+=.018*math.sin(t*.5)
            self.rx=max(-3.5,min(3.5,self.rx)); self.ry=max(-2.8,min(2.8,self.ry))
            try: self.pepper.setPosition([self.rx,self.ry,.8])
            except: pass
            time.sleep(.06)

    def _arm_loop(self):
        ph=0
        while True:
            try:
                if ST["is_speaking"]:
                    ph+=.07
                    L=.5+.3*math.sin(ph); R=.5+.3*math.sin(ph+math.pi*.6)
                    self.pepper.setAngles("LShoulderPitch",L,.07)
                    self.pepper.setAngles("RShoulderPitch",R,.07)
                    lip=ST.get("lip_sync_value",0.0)
                    self.pepper.setAngles("HeadPitch",-0.04-lip*0.13,.18)
                elif ST["listening"]:
                    self.pepper.setAngles("HeadYaw",0.25,.05)
                    self.pepper.setAngles("HeadPitch",0.12,.05)
                else:
                    self.pepper.setAngles("LShoulderPitch",1.,.04)
                    self.pepper.setAngles("RShoulderPitch",1.,.04)
                    self.pepper.setAngles("HeadYaw",0.,.03)
                    self.pepper.setAngles("HeadPitch",0.,.03)
            except: pass
            time.sleep(.04)

    def show_text(self,text):
        if not self.ok: return
        try:
            pos=p.getBasePositionAndOrientation(self.pepper.body)[0]
            p.addUserDebugText(text[:55],[pos[0],pos[1],pos[2]+1.35],[0,0,0],textSize=.85,lifeTime=5)
        except: pass

# ═══════════════════════════════════════════════════════════════
# 13. DISPLAY (OpenCV Windows 2 & 3)
# ═══════════════════════════════════════════════════════════════
class Display:
    def __init__(self,vision,cam):
        self.v=vision; self.c=cam; self.running=True
        threading.Thread(target=self._run,daemon=True).start()
        print("✅ Display: 2 OpenCV windows")

    def _sim_frame(self):
        h,w=480,640; f=np.zeros((h,w,3),dtype=np.uint8); f[:]=(7,10,25)
        t=time.time()
        for i in range(0,w,60): cv2.line(f,(i,0),(i,h),(15,22,50),1)
        for i in range(0,h,60): cv2.line(f,(0,i),(w,i),(15,22,50),1)
        r=int(28+10*math.sin(t*1.5))
        cv2.circle(f,(w//2,h//2-40),r,(int(50+50*math.sin(t)),int(100+100*math.cos(t*0.7)),220),3)
        cv2.putText(f,"SIMULATION MODE",(w//2-110,h//2+20),cv2.FONT_HERSHEY_SIMPLEX,0.8,(100,150,255),2)
        return f

    def _run(self):
        no_cam=self.c.idx<0; em_last=0
        # RESIZABLE windows (cv2.WINDOW_NORMAL)
        cv2.namedWindow(WIN_EMO,cv2.WINDOW_NORMAL)
        cv2.resizeWindow(WIN_EMO,600,600)
        try: cv2.setWindowProperty(WIN_EMO,cv2.WND_PROP_TOPMOST,1)
        except: pass
        cv2.moveWindow(WIN_EMO,670,30)
        cv2.namedWindow(WIN_LIVE,cv2.WINDOW_NORMAL)
        cv2.resizeWindow(WIN_LIVE,820,520)
        try: cv2.setWindowProperty(WIN_LIVE,cv2.WND_PROP_TOPMOST,1)
        except: pass
        cv2.moveWindow(WIN_LIVE,30,30)
        while self.running:
            try:
                if no_cam: frame=self._sim_frame()
                else:
                    ret,f=self.c.read(); frame=f if ret else self._sim_frame()
                now=time.time()
                if now-em_last>0.65 and not no_cam:
                    em_last=now; self.v.analyze_async(frame.copy())
                elif no_cam and now-em_last>3:
                    em_last=now; ST["emotion"]=random.choice(["happy","neutral","joyful","happy"])
                ew=self.v.get_emo_frame()
                if ew is not None: cv2.imshow(WIN_EMO,ew)
                lw=self.v.get_live_frame()
                if lw is not None: cv2.imshow(WIN_LIVE,lw)
                key=cv2.waitKey(1)&0xFF
                if key in [ord('q'),ord('Q'),27]: self.running=False; break
            except Exception as e: print(f"⚠️  display: {e}"); time.sleep(0.1)
            time.sleep(0.016)
        try: cv2.destroyAllWindows()
        except: pass

    def stop(self):
        self.running=False; time.sleep(0.3)
        try: cv2.destroyAllWindows()
        except: pass

# ═══════════════════════════════════════════════════════════════
# 14. FLASK SERVERS
# ═══════════════════════════════════════════════════════════════
game_app=Flask("game"); rep_app=Flask("reports"); brain_app=Flask("brain")
_gemini=None

GAME_HTML=r"""<!DOCTYPE html><html><head>
<meta charset="UTF-8"><title>Therapy Games</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>*{margin:0;padding:0;box-sizing:border-box}
body{background:#060912;color:#e0e6ff;font-family:'Segoe UI',sans-serif;padding:12px}
h1{color:#a78bfa;text-align:center;margin-bottom:10px}
.nav{display:flex;gap:6px;justify-content:center;margin-bottom:10px;flex-wrap:wrap}
.nav a{padding:8px 14px;border-radius:9px;text-decoration:none;font-size:.8em;font-weight:700;min-height:40px;display:flex;align-items:center}
.b1{background:#4f46e5;color:#fff}.b2{background:#059669;color:#fff}.b3{background:#1d4ed8;color:#fff}.b4{background:#7c3aed;color:#fff}
.sc{background:#1a0a3d;border-radius:8px;padding:7px 14px;text-align:center;margin-bottom:10px;color:#a78bfa}
.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;max-width:700px;margin:0 auto}
@media(min-width:500px){.grid{grid-template-columns:repeat(3,1fr)}}
.gc{background:#0c0f1e;border:2px solid #1a1f40;border-radius:11px;padding:14px;text-align:center;cursor:pointer;transition:.3s}
.gc:hover,.gc:active{border-color:#a78bfa;transform:translateY(-2px)}
.gi{font-size:2.4em;margin-bottom:5px}.gn{font-weight:700;color:#e0e6ff;font-size:.85em}.gd{font-size:.68em;color:#6b7280;margin-top:3px}
#ag{max-width:700px;margin:10px auto}
.btn{background:#4f46e5;color:#fff;border:none;padding:9px 16px;border-radius:7px;cursor:pointer;font-size:.8em;margin:4px;min-height:42px;touch-action:manipulation}
.btn-g{background:#059669}
canvas{border:2px solid #4f46e5;border-radius:8px;background:#0a0f1e;display:block;margin:8px auto;max-width:100%;touch-action:none}
.pbox{background:#0c0f1e;border:2px solid #a78bfa;border-radius:11px;padding:14px;max-width:700px;margin:10px auto;text-align:center}
</style></head><body>
<h1>🎮 ABA Therapy Games</h1>
<div class="nav">
  <a href="http://127.0.0.1:5007/" class="b1">🧠 Brain</a>
  <a href="http://127.0.0.1:5001/" class="b3">📋 Reports</a>
  <a href="http://127.0.0.1:5009/" class="b2">🎮 Games</a>
  <a href="https://LamyaFadlulmolaHamedAli.pythonanywhere.com" class="b4" target="_blank">🌐 Platform</a>
</div>
<div class="sc">Score: <span id="pts">0</span> ⭐ | Level: <span id="lvl">1</span></div>
<div class="grid">
  <div class="gc" onclick="start('balloons')"><div class="gi">🎈</div><div class="gn">Balloons</div><div class="gd">Pop them!</div></div>
  <div class="gc" onclick="start('emotions')"><div class="gi">😊</div><div class="gn">Emotions</div><div class="gd">Mirror face</div></div>
  <div class="gc" onclick="start('colors')"><div class="gi">🎨</div><div class="gn">Colors</div><div class="gd">Match it!</div></div>
  <div class="gc" onclick="start('numbers')"><div class="gi">🔢</div><div class="gn">Count!</div><div class="gd">How many?</div></div>
  <div class="gc" onclick="start('memory')"><div class="gi">🧠</div><div class="gn">Memory</div><div class="gd">Find pairs!</div></div>
  <div class="gc" onclick="start('shapes')"><div class="gi">⭐</div><div class="gn">Shapes</div><div class="gd">Name it!</div></div>
</div>
<div id="ag"></div>
<div class="pbox">
  <h3 style="color:#a78bfa;margin-bottom:6px">🌐 Platform</h3>
  <a href="https://LamyaFadlulmolaHamedAli.pythonanywhere.com" target="_blank" class="btn btn-g" style="display:inline-block;text-decoration:none">Open 🚀</a>
</div>
<script>
var sc=0,lv=1;
function add(n){sc+=n;lv=Math.floor(sc/50)+1;document.getElementById('pts').textContent=sc;document.getElementById('lvl').textContent=lv;}
function start(g){var d=document.getElementById('ag');
  if(g==='balloons')runBalloons(d);else if(g==='emotions')emoGame(d);
  else if(g==='colors')colorGame(d);else if(g==='numbers')numGame(d);
  else if(g==='memory')memGame(d);else shapeGame(d);}
function runBalloons(d){
  var W=Math.min(680,window.innerWidth-24);
  d.innerHTML='<canvas id="gc" width="'+W+'" height="280" style="width:100%"></canvas>';
  var c=document.getElementById('gc'),ctx=c.getContext('2d'),bs=[];
  for(var i=0;i<8;i++)bs.push({x:Math.random()*(W-40)+20,y:Math.random()*240+20,r:18+Math.random()*12,vx:(Math.random()-0.5)*2.5,vy:(Math.random()-0.5)*2.5,color:['#f87171','#34d399','#60a5fa','#fbbf24','#c084fc'][Math.floor(Math.random()*5)],alive:true});
  function hit(mx,my){bs.forEach(function(b){if(!b.alive)return;if(Math.sqrt((mx-b.x)**2+(my-b.y)**2)<b.r){b.alive=false;add(10);}});if(bs.every(function(b){return !b.alive;}))bs.forEach(function(b){b.alive=true;b.x=Math.random()*(W-40)+20;b.y=Math.random()*240+20;});}
  c.addEventListener('click',function(e){var r=c.getBoundingClientRect(),s=c.width/r.width;hit((e.clientX-r.left)*s,(e.clientY-r.top)*s);});
  c.addEventListener('touchstart',function(e){e.preventDefault();var r=c.getBoundingClientRect(),s=c.width/r.width,t=e.touches[0];hit((t.clientX-r.left)*s,(t.clientY-r.top)*s);},{passive:false});
  (function loop(){ctx.fillStyle='#0a0f1e';ctx.fillRect(0,0,W,280);bs.forEach(function(b){if(!b.alive)return;b.x+=b.vx;b.y+=b.vy;if(b.x<b.r||b.x>W-b.r)b.vx*=-1;if(b.y<b.r||b.y>280-b.r)b.vy*=-1;ctx.beginPath();ctx.arc(b.x,b.y,b.r,0,Math.PI*2);ctx.fillStyle=b.color;ctx.fill();ctx.fillStyle='white';ctx.font='16px sans-serif';ctx.textAlign='center';ctx.fillText('🎈',b.x,b.y+5);});requestAnimationFrame(loop);})();}
function emoGame(d){var em=[['😊','Happy'],['😢','Sad'],['😠','Angry'],['😨','Scared'],['😲','Surprised']];var pick=em[Math.floor(Math.random()*em.length)];d.innerHTML='<div style="text-align:center;padding:14px"><p style="color:#a78bfa;margin-bottom:7px">Show this face!</p><div style="font-size:4em;margin:10px">'+pick[0]+'</div><p style="font-weight:700;color:#e0e6ff">'+pick[1]+'</p><button class="btn btn-g" onclick="add(20);this.textContent=\'✅ Amazing!\'" style="display:block;width:100%;max-width:200px;margin:10px auto">I did it! 🌟</button><button class="btn" onclick="emoGame(document.getElementById(\'ag\'))" style="display:block;width:100%;max-width:200px;margin:6px auto">Next ➡️</button></div>';}
function colorGame(d){var cs=[['Red','#ef4444'],['Blue','#3b82f6'],['Green','#22c55e'],['Yellow','#eab308'],['Purple','#a855f7'],['Orange','#f97316']];var idx=Math.floor(Math.random()*cs.length);d.innerHTML='<div style="text-align:center;padding:14px"><p style="color:#a78bfa;margin-bottom:7px">What color?</p><div style="width:90px;height:90px;background:'+cs[idx][1]+';border-radius:50%;margin:8px auto;border:3px solid #374151"></div><div id="cbtns" style="display:flex;flex-wrap:wrap;justify-content:center;gap:6px;margin-top:8px">'+cs.map(function(c,i){return '<button class="btn" onclick="chkC('+i+','+idx+')" style="background:'+c[1]+';min-width:80px">'+c[0]+'</button>';}).join('')+'</div></div>';}
window.chkC=function(ch,co){if(ch===co){add(15);document.getElementById('cbtns').innerHTML='<p style="color:#34d399;margin:8px">✅ Correct! 🌟</p><button class="btn" onclick="colorGame(document.getElementById(\'ag\'))" style="display:block;margin:6px auto">Next ➡️</button>';}else document.getElementById('cbtns').innerHTML='<p style="color:#f87171;margin:8px">Try again! 💪</p><button class="btn" onclick="colorGame(document.getElementById(\'ag\'))" style="display:block;margin:6px auto">Retry ↩️</button>';};
function numGame(d){var n=Math.floor(Math.random()*9)+1,stars='';for(var i=0;i<n;i++)stars+='⭐';var opts=Array.from(new Set([n,Math.max(1,n-1),Math.min(10,n+1),n>2?n-2:n+3])).sort(function(){return Math.random()-0.5;}).slice(0,4);d.innerHTML='<div style="text-align:center;padding:14px"><p style="color:#a78bfa">Count!</p><div style="font-size:1.4em;margin:9px;word-break:break-all">'+stars+'</div><div style="display:flex;flex-wrap:wrap;justify-content:center;gap:8px">'+opts.map(function(x){return '<button class="btn" onclick="chkN('+x+','+n+')" style="font-size:1.1em;min-width:60px">'+x+'</button>';}).join('')+'</div></div>';}
window.chkN=function(ch,co){if(ch===co){add(20);alert('✅ YES! '+co+'! 🌟');numGame(document.getElementById('ag'));}else alert('Try again! 💪');};
function memGame(d){var pairs=['🐶','🐱','🐻','🦊','🐼','🐨'],cards=pairs.concat(pairs).sort(function(){return Math.random()-0.5;});window._mc=cards;window._mf=[];window._mm=[];d.innerHTML='<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:6px;max-width:300px;margin:10px auto">'+cards.map(function(c,i){return '<div id="mc'+i+'" onclick="flipM('+i+')" style="height:60px;background:#1f2937;border-radius:7px;display:flex;align-items:center;justify-content:center;font-size:1.7em;cursor:pointer;border:2px solid #374151;touch-action:manipulation">❓</div>';}).join('')+'</div>';}
window.flipM=function(idx){var c=window._mc;if(window._mf.length>=2||window._mm.includes(idx)||window._mf.includes(idx))return;document.getElementById('mc'+idx).textContent=c[idx];window._mf.push(idx);if(window._mf.length===2){var a=window._mf[0],b=window._mf[1];if(c[a]===c[b]){window._mm.push(a,b);add(25);window._mf=[];if(window._mm.length===c.length)setTimeout(function(){alert('🎉 All matched!');memGame(document.getElementById('ag'));},400);}else setTimeout(function(){document.getElementById('mc'+a).textContent='❓';document.getElementById('mc'+b).textContent='❓';window._mf=[];},1000);}};
function shapeGame(d){var shapes=[['⬛','Square'],['⭕','Circle'],['🔺','Triangle'],['💎','Diamond'],['⭐','Star']];var pick=shapes[Math.floor(Math.random()*shapes.length)];d.innerHTML='<div style="text-align:center;padding:14px"><p style="color:#a78bfa;margin-bottom:7px">What shape?</p><div style="font-size:4em;margin:10px">'+pick[0]+'</div><div style="display:flex;flex-wrap:wrap;justify-content:center;gap:6px">'+shapes.map(function(s){return '<button class="btn" onclick="chkS(\''+s[1]+'\',\''+pick[1]+'\')">'+s[1]+'</button>';}).join('')+'</div></div>';}
window.chkS=function(ch,co){if(ch===co){add(15);alert('✅ Correct! 🌟');shapeGame(document.getElementById('ag'));}else alert('Try again! 💪');};
</script></body></html>"""

@game_app.route("/")
@game_app.route("/<path:path>")
def game_catch(path=""): return GAME_HTML

@game_app.errorhandler(404)
def g404(e): return redirect("/"),302

@game_app.errorhandler(405)
def g405(e): return redirect("/"),302

REP_HTML="""<!DOCTYPE html><html><head>
<meta charset="UTF-8"><title>Clinical Reports</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="5">
<style>*{margin:0;padding:0;box-sizing:border-box}
body{background:#060912;color:#e0e6ff;font-family:'Segoe UI',sans-serif;padding:14px}
h1{color:#a78bfa;margin-bottom:10px}
.nav{display:flex;gap:6px;margin-bottom:10px;flex-wrap:wrap}
.nav a{padding:7px 12px;border-radius:8px;text-decoration:none;font-size:.78em;font-weight:700;min-height:38px;display:flex;align-items:center}
.b1{background:#4f46e5;color:#fff}.b2{background:#059669;color:#fff}.b3{background:#1d4ed8;color:#fff}.b4{background:#7c3aed;color:#fff}
.card{background:#0c0f1e;border-radius:10px;padding:12px;border:1px solid #1a1f40;margin-bottom:10px}
.card h2{color:#818cf8;margin-bottom:7px;font-size:.82em}
.stat{display:inline-block;background:#1a0a3d;border-radius:7px;padding:5px 10px;margin:3px;text-align:center}
.n{font-size:1.3em;font-weight:700;color:#a78bfa}.l{font-size:.63em;color:#6b7280}
.rep{background:#07090f;border-radius:7px;padding:9px;margin:6px 0;border-left:3px solid #a78bfa;white-space:pre-wrap;font-size:.75em;line-height:1.7;color:#c0c8e0;max-height:250px;overflow-y:auto}
.btn{background:#4f46e5;color:#fff;border:none;padding:9px 16px;border-radius:7px;cursor:pointer;font-size:.78em;margin:3px;min-height:40px}
.btn-g{background:#059669}
input,textarea,select{width:100%;padding:6px 8px;border-radius:5px;border:1px solid #1a1f40;background:#07090f;color:#e0e6ff;font-size:.77em;font-family:inherit;outline:none;min-height:38px}
textarea{resize:vertical;min-height:65px;margin:4px 0}
.note{background:#0a1020;border-left:3px solid #a78bfa;padding:6px;margin:3px 0;font-size:.72em}
</style></head><body>
<h1>📋 Clinical Reports</h1>
<div class="nav">
  <a href="http://127.0.0.1:5007/" class="b1">🧠 Brain</a>
  <a href="http://127.0.0.1:5009/" class="b2">🎮 Games</a>
  <a href="http://127.0.0.1:5001/" class="b3">📋 Reports</a>
  <a href="https://LamyaFadlulmolaHamedAli.pythonanywhere.com" class="b4" target="_blank">🌐 Platform</a>
</div>
<div class="card"><h2>📊 Session Progress</h2>
  <div class="stat"><div class="n">{{s.current_level}}</div><div class="l">Level</div></div>
  <div class="stat"><div class="n">{{s.consecutive_successes}}/3</div><div class="l">Mastery</div></div>
  <div class="stat"><div class="n">{{s.tasks_mastered}}</div><div class="l">Mastered</div></div>
  <div class="stat"><div class="n">{{s.score}}</div><div class="l">Score</div></div>
  <div class="stat"><div class="n">{{s.tokens}}</div><div class="l">Tokens</div></div>
  <div class="stat"><div class="n">{{s.tasks_success}}</div><div class="l">OK</div></div>
  <div class="stat"><div class="n">{{s.tasks_fail}}</div><div class="l">Fail</div></div>
  <div class="stat"><div class="n">{{s.attention}}%</div><div class="l">Attention</div></div>
</div>
<div class="card"><h2>📄 Reports</h2>
  <form method="POST" action="/generate">
    <button class="btn btn-g" style="width:100%">⚡ Generate Report</button>
  </form>
  {% for rep in s.reports[-5:]|reverse %}
  <div class="rep">{{rep.content}}</div>
  <div style="font-size:.63em;color:#6b7280;margin:2px">{{rep.time}}</div>
  {% endfor %}
  {% if not s.reports %}<p style="color:#6b7280;font-size:.77em;margin-top:6px">Click Generate.</p>{% endif %}
</div>
<div class="card"><h2>📝 Notes</h2>
  <form method="POST" action="/note">
    <select name="cat" style="width:140px;margin-bottom:5px">
      <option>behavior</option><option>progress</option>
      <option>concern</option><option>milestone</option>
    </select>
    <textarea name="note" placeholder="Observation..."></textarea>
    <button class="btn btn-g" style="width:100%;margin-top:5px">Save</button>
  </form>
  {% for n in s.parent_notes[-10:]|reverse %}
  <div class="note"><span style="color:#a78bfa;font-size:.67em;font-weight:700">{{n.category.upper()}}</span>
    <span style="color:#6b7280;font-size:.67em"> {{n.time}}</span><br>{{n.text}}</div>
  {% endfor %}
</div>
</body></html>"""

@rep_app.route("/")
@rep_app.route("/<path:path>")
def rep_catch(path=""): return render_template_string(REP_HTML,s=ST)

@rep_app.route("/generate",methods=["POST"])
def rep_gen():
    if _gemini:
        r=_gemini.generate_report()
        ST["reports"].append({"time":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"content":r})
        if len(ST["reports"])>10: ST["reports"]=ST["reports"][-10:]
    return redirect("/")

@rep_app.route("/note",methods=["POST"])
def rep_note():
    note=request.form.get("note","").strip(); cat=request.form.get("cat","other")
    if note: ST["parent_notes"].append({"time":datetime.now().strftime("%H:%M:%S"),"text":note,"category":cat})
    return redirect("/")

@rep_app.errorhandler(404)
def r404(e): return redirect("/"),302

@rep_app.errorhandler(405)
def r405(e): return redirect("/"),302

# Brain Dashboard
BRAIN_HTML="""<!DOCTYPE html><html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pepper Clinical Brain</title><meta http-equiv="refresh" content="3">
<script src="https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js"></script>
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{--bg:#060912;--card:#0c0f1e;--bo:#1a1f40;--pu:#a78bfa;--bl:#60a5fa;--gr:#34d399;--rd:#f87171;--yl:#fbbf24;--tx:#e0e6ff;--mu:#6b7280}
body{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--tx);font-size:13px}
.layout{display:flex;min-height:100vh}
.sidebar{width:142px;background:#07090f;border-right:2px solid var(--bo);display:flex;flex-direction:column;padding:7px 5px;gap:5px;position:sticky;top:0;height:100vh;overflow-y:auto;flex-shrink:0}
.sidebar h3{color:var(--pu);font-size:.70em;margin-bottom:2px;text-align:center}
.slink{display:flex;flex-direction:column;align-items:center;padding:8px 4px;border-radius:9px;text-decoration:none;font-weight:700;transition:.25s;border:2px solid;width:100%;font-size:.67em}
.slink:hover{transform:translateY(-2px);opacity:.9}
.sl-brain{background:#1e1b4b;color:var(--pu);border-color:var(--pu)}
.sl-game{background:#052918;color:var(--gr);border-color:var(--gr)}
.sl-rep{background:#1e3a5f;color:var(--bl);border-color:var(--bl)}
.sl-gh{background:#2a1060;color:#c084fc;border-color:#c084fc}
.sl-plat{background:#1a2040;color:var(--yl);border-color:var(--yl)}
.sl-icon{font-size:1.45em;margin-bottom:2px}.sl-port{font-size:.56em;opacity:.7}
.content{flex:1;padding:8px;min-width:0;overflow-y:auto}
.android-info{background:#051a0f;border:1px solid var(--gr);border-radius:8px;padding:6px 10px;margin-bottom:7px;text-align:center}
.android-url{font-size:.80em;color:var(--gr);font-weight:700;word-break:break-all}
.mastery-box{background:#051a0f;border:2px solid var(--gr);border-radius:9px;padding:8px;margin-bottom:7px;text-align:center}
.hdr{background:linear-gradient(135deg,#0a0f28,#1a0a3d);border-radius:9px;padding:8px 12px;display:flex;align-items:center;gap:7px;border:1px solid #4f46e5;margin-bottom:7px}
.hdr h1{font-size:.85em;color:var(--pu)}
.bd{padding:2px 5px;border-radius:8px;font-size:.60em;font-weight:700}
.live{background:#ef4444;color:#fff;animation:blink 1s infinite}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.3}}
.row{display:grid;gap:7px}
.r3{grid-template-columns:1fr 1fr 1fr}.r2{grid-template-columns:1fr 1fr}.r5{grid-template-columns:repeat(5,1fr)}
.card{background:var(--card);border-radius:9px;padding:10px;border:1px solid var(--bo)}
.card h2{font-size:.73em;color:#818cf8;border-bottom:1px solid var(--bo);padding-bottom:3px;margin-bottom:6px}
.stat{background:linear-gradient(135deg,#0d1030,#1a0a3d);border:1px solid #312e81;border-radius:7px;padding:8px;text-align:center}
.n{font-size:1.45em;font-weight:700;color:var(--pu)}.l{font-size:.62em;color:var(--mu);margin-top:2px}
.n-g{color:var(--gr)}.n-y{color:var(--yl)}.n-b{color:var(--bl)}
.emo{display:inline-block;padding:4px 10px;border-radius:12px;font-weight:700;font-size:.87em}
.happy,.joyful{background:#05291555;color:#34d399;border:1px solid #34d399}
.sad{background:#1e3a5f55;color:#60a5fa;border:1px solid #60a5fa}
.angry{background:#45090a55;color:#f87171;border:1px solid #f87171}
.fear{background:#1c190055;color:#fbbf24;border:1px solid #fbbf24}
.surprised{background:#2e106555;color:#c084fc;border:1px solid #c084fc}
.confused{background:#2a1a0055;color:#fb923c;border:1px solid #fb923c}
.neutral{background:#1f293755;color:#9ca3af;border:1px solid #9ca3af}
.bar-bg{background:#1f2937;border-radius:5px;height:6px;margin:3px 0}
.bar{height:6px;border-radius:5px;background:linear-gradient(90deg,#6366f1,#a78bfa)}
.btn{background:linear-gradient(135deg,#4f46e5,#7c3aed);color:#fff;border:none;padding:4px 8px;border-radius:5px;cursor:pointer;font-size:.67em;margin:2px;transition:.2s;font-family:inherit;min-height:30px}
.btn:hover{opacity:.85}
.btn-g{background:linear-gradient(135deg,#059669,#10b981)}
.btn-y{background:linear-gradient(135deg,#d97706,#f59e0b)}
.btn-r{background:linear-gradient(135deg,#dc2626,#ef4444)}
.btn-b{background:linear-gradient(135deg,#1d4ed8,#3b82f6)}
input,textarea,select{width:100%;padding:5px 7px;border-radius:5px;border:1px solid var(--bo);background:#07090f;color:var(--tx);font-size:.71em;font-family:inherit;outline:none;min-height:30px}
input:focus,textarea:focus{border-color:var(--pu)}
textarea{resize:vertical;min-height:44px}
.log-box{max-height:155px;overflow-y:auto;scrollbar-width:thin}
.li{padding:2px 5px;margin:1px 0;border-radius:3px;font-size:.66em;border-left:3px solid #4f46e5;background:#07090f;line-height:1.4}
.li.success{border-color:var(--gr)}.li.fail{border-color:var(--rd)}
.cw{height:130px;background:#07090f;border-radius:6px;padding:4px}
.chat-box{height:135px;overflow-y:auto;background:#07090f;border-radius:6px;padding:6px;margin-bottom:4px;scrollbar-width:thin}
.cm{padding:3px 6px;margin:2px 0;border-radius:5px;font-size:.69em;line-height:1.5}
.cmp{background:#1e1b4b;border-left:3px solid var(--pu)}.cmc{background:#052918;border-left:3px solid var(--gr)}
.tabs{display:flex;gap:3px;flex-wrap:wrap;margin-bottom:6px}
.tab{padding:3px 8px;border-radius:5px;cursor:pointer;font-size:.67em;background:#1f2937;color:#9ca3af;border:1px solid var(--bo);transition:.2s;min-height:26px}
.tab.active,.tab:hover{background:#4f46e5;color:#fff}
.tc{display:none}.tc.active{display:block}
.hc{background:#0a1020;border-radius:7px;padding:7px;border-left:4px solid var(--pu)}
.hct{color:var(--pu);font-weight:700;font-size:.71em;margin-bottom:2px}
.hcb{color:#9ca3af;font-size:.68em;line-height:1.6}
.tip{background:#051a0f;border:1px solid var(--gr);border-radius:3px;padding:3px;margin-top:3px;font-size:.66em;color:#6ee7b7}
.ab{display:inline-block;padding:2px 5px;border-radius:6px;font-size:.64em;font-weight:700;margin:1px}
.aon{background:#052918;color:var(--gr);border:1px solid var(--gr)}
.aoff{background:#1f2937;color:#374151;border:1px solid #374151}
::-webkit-scrollbar{width:3px}::-webkit-scrollbar-track{background:var(--card)}::-webkit-scrollbar-thumb{background:#4f46e5;border-radius:3px}
@media(max-width:700px){.sidebar{width:108px}.r3{grid-template-columns:1fr 1fr}.r5{grid-template-columns:repeat(3,1fr)}.r2{grid-template-columns:1fr}}
</style></head><body>
<div class="layout">
<div class="sidebar">
  <h3>🤖 Clinical</h3>
  <div style="text-align:center;padding:5px">
    <div style="font-size:2em">🤖</div>
    <div style="font-size:.60em;color:{{'#34d399' if s.gemini_ok else '#fbbf24'}};margin-top:3px">
      {{'AI ON' if s.gemini_ok else 'FALLBACK'}}</div>
    <div style="font-size:.58em;color:#6b7280;margin-top:2px">
      {{'🔊' if s.is_speaking else '👂' if s.listening else '💤'}}</div>
  </div>
  <a href="http://127.0.0.1:5007/" class="slink sl-brain"><div class="sl-icon">🧠</div><div>Brain</div><div class="sl-port">:5007</div></a>
  <a href="http://127.0.0.1:5009/" target="_blank" class="slink sl-game"><div class="sl-icon">🎮</div><div>Games</div><div class="sl-port">:5009</div></a>
  <a href="http://127.0.0.1:5001/" target="_blank" class="slink sl-rep"><div class="sl-icon">📋</div><div>Reports</div><div class="sl-port">:5001</div></a>
  <a href="https://LamyaFadlulmolaHamedAli.pythonanywhere.com" target="_blank" class="slink sl-plat"><div class="sl-icon">🌐</div><div>Platform</div><div class="sl-port">Live</div></a>
  <a href="{{ github_url }}" target="_blank" class="slink sl-gh"><div class="sl-icon">📦</div><div>GitHub</div><div class="sl-port">Games</div></a>
  <a href="/auto_report" class="slink" style="background:#1a2040;color:var(--yl);border-color:var(--yl)"><div class="sl-icon">⚡</div><div>Report</div><div class="sl-port">→:5001</div></a>
</div>
<div class="content">
<div class="android-info">📱 <b>Android:</b>
  <div class="android-url">http://{{ local_ip }}:5007</div>
  <div style="font-size:.66em;color:#6ee7b7;margin-top:2px">Same WiFi → browser → URL</div>
</div>
<div class="mastery-box">
  <div style="color:var(--gr);font-size:.80em;font-weight:700">
    🎯 Task: {{ task_name }} | Mastery {{ s.consecutive_successes }}/3</div>
  <div style="background:#1f2937;border-radius:5px;height:10px;margin:5px 0">
    <div style="width:{{ mastery_pct }}%;height:10px;border-radius:5px;background:linear-gradient(90deg,#059669,#34d399)"></div>
  </div>
  <div style="font-size:.68em;color:var(--mu)">
    Mastered: {{ s.tasks_mastered }} | Level {{ s.current_level }} | {{ s.protocol }}</div>
</div>
<div class="hdr">
  <div style="font-size:1.2em">🤖</div>
  <div>
    <h1>Pepper Clinical Therapy — Tablet UI Active</h1>
    <p style="font-size:.66em;opacity:.8">Commander: <b>Lamya</b> | Child: <b>{{s.name}}</b> ({{s.age}}) | {{s.session_start}}</p>
  </div>
  <span class="bd live">LIVE</span>
  <span class="bd" style="background:#1a2555;color:var(--bl);border:1px solid var(--bl)">
    {% if s.gemini_ok %}AI:{{s.gemini_model[:12]}}{% else %}FALLBACK{% endif %}
  </span>
</div>
<div class="row r5" style="margin-bottom:7px">
  <div class="stat"><div class="n n-g">{{s.score}}</div><div class="l">Score</div></div>
  <div class="stat"><div class="n n-y">{{s.tokens}}</div><div class="l">Tokens</div></div>
  <div class="stat"><div class="n n-b">{{s.attention}}%</div><div class="l">Attention</div></div>
  <div class="stat"><div class="n">{{s.current_level}}</div><div class="l">Level</div></div>
  <div class="stat"><div class="n n-g">{{s.streak}}</div><div class="l">Streak</div></div>
</div>
<div class="tabs">
  <div class="tab active" onclick="T('ov')">📊 Overview</div>
  <div class="tab" onclick="T('ch')">📈 Charts</div>
  <div class="tab" onclick="T('cb')">💬 Chatbot</div>
  <div class="tab" onclick="T('nt')">📝 Notes</div>
  <div class="tab" onclick="T('hl')">💡 Help</div>
  <div class="tab" onclick="T('st')">⚙️ Settings</div>
</div>
<div id="tc-ov" class="tc active">
<div class="row r3">
  <div class="card"><h2>😊 Emotion</h2>
    <div style="text-align:center;padding:4px">
      <div class="emo {{s.emotion}}">{{s.emotion.upper()}}</div>
      <div style="margin:5px 0"><div class="bar-bg"><div class="bar" style="width:{{s.attention}}%"></div></div>
        <span style="font-size:.66em;color:var(--pu)">{{s.attention}}%</span></div>
      <div style="font-size:.64em;margin:2px;color:{{'#34d399' if s.face_detected else '#f87171'}}">{{'Face OK' if s.face_detected else 'No Face'}}</div>
      <div>
        <span class="ab {{'aon' if s.hand_raised else 'aoff'}}">Hand</span>
        <span class="ab {{'aon' if s.waving else 'aoff'}}">Wave</span>
        <span class="ab {{'aon' if s.clapping else 'aoff'}}">Clap</span>
        <span class="ab {{'aon' if s.blinking else 'aoff'}}">Blink</span>
        <span class="ab {{'aon' if s.eye_contact else 'aoff'}}">Eyes</span>
      </div>
      {% if s.is_speaking %}<div style="font-size:.63em;color:var(--bl);margin-top:3px">🔊 Lip:{{(s.lip_sync_value*10)|int}}/10</div>
      {% elif s.listening %}<div style="font-size:.63em;color:var(--gr);margin-top:3px">👂 Listening</div>
      {% endif %}
    </div>
  </div>
  <div class="card"><h2>🎮 Controls</h2>
    <form method="POST" action="/cmd">
      <button class="btn btn-g" name="c" value="dance" style="width:100%;margin:2px 0">Dance [DANCE]</button>
      <button class="btn btn-y" name="c" value="celebrate" style="width:100%;margin:2px 0">Celebrate [CELEBRATE]</button>
      <button class="btn btn-b" name="c" value="game" style="width:100%;margin:2px 0">Open Games</button>
      <button class="btn btn-r" name="c" value="break" style="width:100%;margin:2px 0">Break Time</button>
      <button class="btn" name="c" value="report" style="width:100%;margin:2px 0">Report</button>
      <button class="btn" name="c" value="next_task" style="width:100%;margin:2px 0">Next Task ⏭️</button>
    </form>
    <form method="POST" action="/search" style="display:flex;gap:3px;margin-top:4px">
      <input name="q" placeholder="YouTube search..."><button class="btn">Go</button>
    </form>
    <form method="POST" action="/name" style="display:flex;gap:3px;margin-top:3px">
      <input name="n" placeholder="Child name..."><button class="btn">Set</button>
    </form>
  </div>
  <div class="card"><h2>💬 Session</h2>
    <div class="chat-box" id="cs">
      {% for m in s.session_chat[-20:]|reverse %}
      <div class="cm {{'cmp' if m.role=='pepper' else 'cmc'}}">
        <span style="color:{{'var(--pu)' if m.role=='pepper' else 'var(--gr)'}};font-size:.59em">
          {{'🤖' if m.role=='pepper' else '👦 '+s.name}} [{{m.time}}]</span><br>{{m.text}}
      </div>{% endfor %}
    </div>
    <div style="font-size:.63em;color:var(--mu)">OK:{{s.tasks_success}} Fail:{{s.tasks_fail}}</div>
  </div>
</div>
</div>
<div id="tc-ch" class="tc">
  <div class="row r2">
    <div class="card"><h2>Attention</h2><div class="cw"><canvas id="aC"></canvas></div></div>
    <div class="card"><h2>Score</h2><div class="cw"><canvas id="sC"></canvas></div></div>
  </div>
  <div class="row r2">
    <div class="card"><h2>Emotions</h2><div class="cw"><canvas id="eC"></canvas></div></div>
    <div class="card"><h2>Skills</h2>
      <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:3px;margin-top:4px">
        {% for sk,v in s.skills.items() %}
        <div style="text-align:center">
          <div style="height:48px;background:#1f2937;border-radius:5px;position:relative;overflow:hidden">
            <div style="position:absolute;bottom:0;width:100%;height:{{v}}%;background:linear-gradient(0deg,#6366f1,#a78bfa);border-radius:5px"></div></div>
          <div style="font-size:.56em;color:var(--mu);margin-top:1px">{{sk}}</div>
          <div style="font-size:.63em;color:var(--pu);font-weight:700">{{v}}%</div>
        </div>{% endfor %}
      </div>
    </div>
  </div>
  <div class="card"><h2>Log</h2>
    <div class="log-box">
      {% for lg in s.logs[-40:]|reverse %}
      <div class="li {{lg.type}}">
        <span style="color:#6366f1">{{lg.time}}</span>
        <b style="color:var(--pu)">{{lg.child}}</b>: {{lg.msg}}
      </div>{% endfor %}
    </div>
    <a href="/export" class="btn btn-g" style="display:inline-block;margin-top:4px;text-decoration:none">Export</a>
  </div>
</div>
<div id="tc-cb" class="tc">
  <div class="row r2">
    <div class="card"><h2>Parent Chatbot (Arabic + English)</h2>
      <div class="chat-box" id="cp">
        {% for m in s.parent_chat[-20:]|reverse %}
        <div class="cm {{'cmp' if m.role=='pepper' else 'cmr'}}">
          <span style="color:var(--{'pu' if m.role=='pepper' else 'bl'});font-size:.59em">
            {{'Pepper' if m.role=='pepper' else 'Parent'}} [{{m.time}}]</span><br>{{m.text}}
        </div>{% endfor %}
        {% if not s.parent_chat %}<div style="color:var(--mu);text-align:center;padding:14px;font-size:.72em">Ask / اسأل</div>{% endif %}
      </div>
      <form method="POST" action="/parent_ask" style="display:flex;gap:4px">
        <input name="question" placeholder="اسأل... / Ask..."><button class="btn btn-g">Ask</button>
      </form>
    </div>
    <div class="card"><h2>Quick Questions</h2>
      {% for q in qqs %}
      <form method="POST" action="/parent_ask">
        <button class="btn" name="question" value="{{q}}" style="width:100%;text-align:left;margin:1px 0;font-size:.64em;padding:3px 5px;min-height:26px">{{q}}</button>
      </form>{% endfor %}
    </div>
  </div>
</div>
<div id="tc-nt" class="tc">
  <div class="row r2">
    <div class="card"><h2>Add Note</h2>
      <form method="POST" action="/note">
        <select name="cat" style="margin-bottom:4px"><option>behavior</option><option>progress</option><option>concern</option><option>milestone</option></select>
        <textarea name="note" placeholder="Observation..."></textarea>
        <button class="btn btn-g" style="width:100%;margin-top:4px;padding:6px">Save</button>
      </form>
    </div>
    <div class="card"><h2>History</h2>
      <div style="max-height:230px;overflow-y:auto">
        {% for n in s.parent_notes[-15:]|reverse %}
        <div style="background:#0a1020;border-left:3px solid var(--pu);padding:5px;margin:2px 0;font-size:.69em">
          <span style="color:var(--pu);font-size:.64em;font-weight:700">{{n.category.upper()}}</span>
          <span style="color:var(--mu);font-size:.64em"> {{n.time}}</span><br>{{n.text}}
        </div>{% endfor %}
      </div>
    </div>
  </div>
</div>
<div id="tc-hl" class="tc">
  <div class="row r3">
    <div class="hc"><div class="hct">Tablet UI</div>
      <div class="hcb">PyQt6 HD tablet shows real animals, colors, fruits, shapes. Child clicks to answer. Locked until task active.</div>
      <div class="tip">3 consecutive successes = mastery!</div></div>
    <div class="hc"><div class="hct">Mastery Rule</div>
      <div class="hcb">Each task requires 3 consecutive successes before unlocking next task. Dynamic difficulty scaling.</div>
      <div class="tip">Progress bar shows current mastery level.</div></div>
    <div class="hc"><div class="hct">Lip-Sync</div>
      <div class="hcb">HeadPitch in PyBullet syncs with voice energy. Avatar mouth opens proportionally in Window 3.</div>
      <div class="tip">Watch PyBullet window when Pepper speaks!</div></div>
    <div class="hc"><div class="hct">EAR Detection</div>
      <div class="hcb">Eye Aspect Ratio via FaceMesh 468 landmarks. Blink = EAR &lt; 0.20. Eye contact = EAR &gt; 0.25.</div>
      <div class="tip">Green in Window 2 = skeleton tracked.</div></div>
    <div class="hc"><div class="hct">YouTube Reward</div>
      <div class="hcb">After completing Level 7 (Social) tasks, Pepper asks what video to watch and opens it.</div>
      <div class="tip">Video reinforcement = ESDM best practice.</div></div>
    <div class="hc"><div class="hct">Android Access</div>
      <div class="hcb">Same WiFi → browser → <b style="color:var(--gr)">http://{{local_ip}}:5007</b></div>
      <div class="tip">4 windows: PyBullet + Emotion + Live + Tablet</div></div>
  </div>
  <div class="card" style="margin-top:7px"><h2>Session Info</h2>
    <div style="font-size:.69em;color:#9ca3af;line-height:1.8">
      Child: <b style="color:var(--tx)">{{s.name}}</b> | Level {{s.current_level}} | {{s.session_date}}<br>
      Score: <b style="color:var(--pu)">{{s.score}}</b> | Tokens: <b style="color:var(--yl)">{{s.tokens}}</b> | Mastered: {{s.tasks_mastered}}<br>
      OK: {{s.tasks_success}} | Fail: {{s.tasks_fail}} | Fallbacks: {{s.api_fallback_count}}
    </div>
    <div style="margin-top:5px;display:flex;gap:4px">
      <a href="/export" class="btn btn-g" style="text-decoration:none">Export</a>
      <a href="/auto_report" class="btn btn-b" style="text-decoration:none">Report→:5001</a>
    </div>
  </div>
</div>
<div id="tc-st" class="tc">
  <div class="row r2">
    <div class="card"><h2>Child Profile</h2>
      <form method="POST" action="/update_child">
        <label style="font-size:.66em;color:var(--mu)">Name</label>
        <input name="name" value="{{s.name}}" style="margin-bottom:4px">
        <label style="font-size:.66em;color:var(--mu)">Age</label>
        <input name="age" type="number" value="{{s.age}}" min="1" max="18" style="margin-bottom:4px">
        <label style="font-size:.66em;color:var(--mu)">Diagnosis</label>
        <select name="diagnosis" style="margin-bottom:4px">
          <option {{'selected' if s.diagnosis=='ASD Level 1'}}>ASD Level 1</option>
          <option {{'selected' if s.diagnosis=='ASD Level 2'}}>ASD Level 2</option>
          <option {{'selected' if s.diagnosis=='ASD Level 3'}}>ASD Level 3</option>
          <option>Suspected ASD</option>
        </select>
        <button class="btn btn-g" style="width:100%;padding:6px">Save</button>
      </form>
    </div>
    <div class="card"><h2>System Info</h2>
      <div style="font-size:.69em;color:var(--mu);line-height:1.9">
        Model: {{s.gemini_model}}<br>API/min: {{s.api_calls_this_min}}/14<br>
        Whisper: {{whisper_ok}}<br>Mic energy: 30 (ultra-sensitive)<br>
        Lip-sync: HeadPitch + Avatar<br>Tablet: PyQt6 HD<br>
        EAR: FaceMesh 468pts<br>Android: http://{{local_ip}}:5007
      </div>
    </div>
  </div>
</div>
</div></div>
<script>
function T(n){document.querySelectorAll('.tc').forEach(t=>t.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  document.getElementById('tc-'+n).classList.add('active');event.target.classList.add('active');}
const AD={{att_h|tojson}},SD={{sc_h|tojson}},ED={{ed|tojson}};
const LB=Array.from({length:AD.length},(_,i)=>i+1);
const CO={responsive:true,maintainAspectRatio:false,
  plugins:{legend:{labels:{color:'#9ca3af',font:{size:8}}}},
  scales:{x:{ticks:{color:'#6b7280',font:{size:7}},grid:{color:'#1f2937'}},
          y:{ticks:{color:'#6b7280',font:{size:7}},grid:{color:'#1f2937'}}}};
if(document.getElementById('aC'))new Chart(document.getElementById('aC'),{type:'line',
  data:{labels:LB,datasets:[{label:'Att%',data:AD,borderColor:'#6366f1',
    backgroundColor:'rgba(99,102,241,0.1)',tension:0.4,fill:true,pointRadius:1}]},
  options:{...CO,scales:{...CO.scales,y:{...CO.scales.y,min:0,max:100}}}});
if(document.getElementById('sC'))new Chart(document.getElementById('sC'),{type:'bar',
  data:{labels:LB,datasets:[{label:'Score',data:SD,backgroundColor:'rgba(167,139,250,0.5)',borderColor:'#a78bfa',borderWidth:1}]},options:CO});
if(document.getElementById('eC')&&Object.keys(ED).length>0){
  const EC={happy:'#34d399',sad:'#60a5fa',angry:'#f87171',neutral:'#9ca3af',fear:'#fbbf24',surprised:'#c084fc',joyful:'#34d399',confused:'#fb923c'};
  new Chart(document.getElementById('eC'),{type:'doughnut',
    data:{labels:Object.keys(ED),datasets:[{data:Object.values(ED),backgroundColor:Object.keys(ED).map(e=>EC[e]||'#6366f1')}]},
    options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{position:'right',labels:{color:'#9ca3af',font:{size:8}}}}}});}
['cs','cp'].forEach(id=>{const el=document.getElementById(id);if(el)el.scrollTop=el.scrollHeight;});
</script></body></html>"""

QUICK_QS=["My child has a meltdown, what do I do?",
          "How do I improve eye contact?","Best way to teach toilet training?",
          "How to handle repetitive behaviors?",
          "كيف أتعامل مع نوبات الغضب؟","كيف أساعد طفلي على التواصل البصري؟",
          "What is ABA therapy?","كيف أحسن مهارات التواصل لطفلي؟",
          "How to help with sleep problems?","What is ESDM?"]

@brain_app.route("/")
@brain_app.route("/<path:path>")
def brain_catch(path=""):
    ed={}
    for e in ST["emo_history"]: ed[e]=ed.get(e,0)+1
    task_idx=min(ST["task_index"],len(TASK_LIBRARY)-1)
    task_name=TASK_LIBRARY[task_idx]["name"]
    mastery_pct=min(100,int(ST["consecutive_successes"]/3*100))
    return render_template_string(BRAIN_HTML,s=ST,qqs=QUICK_QS,
        att_h=ST["att_history"][-40:],sc_h=ST["score_history"][-40:],
        ed=ed,local_ip=LOCAL_IP,github_url=GITHUB_URL,
        task_name=task_name,mastery_pct=mastery_pct,
        whisper_ok=str(WHISPER_OK))

@brain_app.route("/cmd",methods=["GET","POST"])
def brain_cmd():
    c=(request.form.get("c","") or request.args.get("c",""))
    if c:
        if c=="next_task": ST["sim_cmd"]="next_task"
        else: ST["sim_cmd"]=c
        if c=="report" and _gemini:
            r=_gemini.generate_report()
            ST["reports"].append({"time":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"content":r})
    return redirect("http://127.0.0.1:5007/")

@brain_app.route("/auto_report")
def brain_auto():
    if _gemini:
        r=_gemini.generate_report()
        ST["reports"].append({"time":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"content":r})
    return redirect("http://127.0.0.1:5001/")

@brain_app.route("/search",methods=["GET","POST"])
def brain_search():
    q=(request.form.get("q","") or request.args.get("q",""))
    webbrowser.open("https://www.youtube.com/results?search_query="+urllib.parse.quote(q+" autism"))
    return redirect("http://127.0.0.1:5007/")

@brain_app.route("/name",methods=["GET","POST"])
def brain_name():
    n=(request.form.get("n","") or request.args.get("n","")).strip().title()
    if n: ST["name"]=n; ST["known"]=True
    return redirect("http://127.0.0.1:5007/")

@brain_app.route("/parent_ask",methods=["GET","POST"])
def brain_pask():
    q=(request.form.get("question","") or request.args.get("question","")).strip()
    if q and _gemini:
        ST["parent_chat"].append({"role":"parent","text":q,"time":datetime.now().strftime("%H:%M:%S")})
        ans=_gemini.parent_ask(q)
        ST["parent_chat"].append({"role":"pepper","text":ans,"time":datetime.now().strftime("%H:%M:%S")})
        if len(ST["parent_chat"])>40: ST["parent_chat"]=ST["parent_chat"][-40:]
    return redirect("http://127.0.0.1:5007/")

@brain_app.route("/note",methods=["GET","POST"])
def brain_note():
    note=(request.form.get("note","") or request.args.get("note","")).strip()
    cat=(request.form.get("cat","other") or "other")
    if note: ST["parent_notes"].append({"time":datetime.now().strftime("%H:%M:%S"),"text":note,"category":cat})
    return redirect("http://127.0.0.1:5007/")

@brain_app.route("/update_child",methods=["GET","POST"])
def brain_uc():
    ST["name"]=(request.form.get("name","Friend") or "Friend").strip().title()
    ST["age"]=int(request.form.get("age",6) or 6)
    ST["diagnosis"]=request.form.get("diagnosis","ASD Level 2") or "ASD Level 2"
    return redirect("http://127.0.0.1:5007/")

@brain_app.route("/export")
def brain_export():
    fn=f"session_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(fn,"w") as f: json.dump(ST,f,indent=2,default=str)
    return jsonify({"saved":fn})

@brain_app.route("/api/state")
def brain_api():
    return jsonify({
        "name":ST["name"],"emotion":ST["emotion"],
        "attention":ST["attention"],"score":ST["score"],
        "current_level":ST["current_level"],
        "consecutive_successes":ST["consecutive_successes"],
        "tasks_mastered":ST["tasks_mastered"],
        "gemini_ok":ST["gemini_ok"],
        "is_speaking":ST["is_speaking"],"listening":ST["listening"],
        "lip_sync_value":round(ST["lip_sync_value"],2),
        "local_ip":LOCAL_IP,
    })

@brain_app.errorhandler(404)
def b404(e): return redirect("http://127.0.0.1:5007/"),302

@brain_app.errorhandler(405)
def b405(e): return redirect("http://127.0.0.1:5007/"),302

def run_server(app,port,name):
    from werkzeug.serving import make_server
    try:
        srv=make_server('0.0.0.0',port,app,threaded=True)
        srv.socket.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        print(f"✅ {name}: http://{LOCAL_IP}:{port}/")
        srv.serve_forever()
    except Exception as e: print(f"⚠️  {name}: {e}")

# ═══════════════════════════════════════════════════════════════
# 15. THERAPY CONTROLLER — Mastery-Based Infinite Progression
# ═══════════════════════════════════════════════════════════════
class TherapyCtrl:
    def __init__(self,g,v,m,d,s,a,tw):
        self.g=g; self.v=v; self.m=m; self.d=d
        self.s=s; self.a=a; self.tw=tw
        self.running=False

    def _speak(self,text):
        clean=self.a.process(str(text))
        if self.s.ok: self.s.show_text(clean[:55])
        # Update tablet instruction
        if self.tw:
            QTimer.singleShot(0,lambda: self.tw.set_instruction(clean[:70]))
            QTimer.singleShot(0,lambda: self.tw.set_feedback(clean[:50]))
        self.v.say(clean)

    def _ask(self,prompt):
        resp=self.g.ask(prompt); self._speak(resp); return resp

    def run(self):
        self.running=True
        name=self.m.get_name(self.v)
        self._ask(
            f"Child name is {name}. Warm ABA/ESDM greeting! [WAVE] "
            "Explain the tablet UI and mastery system. "
            "Exciting start! 'Ready? Your turn! 🎯'")
        time.sleep(0.5)
        self.m.listen_bg(self._on_speech)
        last_em=ST["emotion"]; em_t=time.time()
        while self.running:
            if time.time()-ST["last_sound"]>12:
                ST["last_sound"]=time.time()
                self.v.say(EMPATHY.get("silence"),wait=False)
            curr=ST["emotion"]
            if curr!=last_em and time.time()-em_t>8:
                last_em=curr; em_t=time.time()
                if curr in ["sad","angry","fear"]:
                    self._ask(f"Child became {curr}. [HUG] Comfort immediately!")
            self._handle_cmd()
            task_idx=ST["task_index"]%len(TASK_LIBRARY)
            task=TASK_LIBRARY[task_idx]
            ST["protocol"]=task["protocol"]
            ST["current_level"]=task["level"]
            ST["tablet_message"]=task["instruction"][:60]
            # Show task on tablet
            self._show_tablet(task)
            success=self._run_task(task)
            if success: self._on_success(task)
            else: self._on_fail(task)
            time.sleep(0.3)

    def _show_tablet(self,task):
        """Send task data to PyQt6 tablet"""
        if not self.tw: return
        mode=task.get("tablet_mode","idle")
        opts=task.get("options",[])
        labels=task.get("option_labels",[]) or opts
        correct=task.get("correct",-1)
        word=task.get("word_display","")
        ST["tablet_image_theme"]=task.get("image_theme","")
        ST["tablet_correct"]=correct
        ST["tablet_result"]=None
        ST["tablet_click_answer"]=-1
        data={
            "mode":mode,
            "instruction":task["instruction"],
            "options":opts,
            "option_labels":list(labels),
            "correct":correct,
            "word_display":word,
            "message":f"Task: {task['name']}",
        }
        tablet_signals.update_display.emit(data)
        tablet_signals.unlock_tablet.emit()

    def _run_task(self,task):
        name=ST["name"]; vtype=task["verify"]
        prompts=task["prompts"]
        ST["task_success"]=False; ST["last_speech_text"]=""
        # Set camera verify for motor tasks
        if vtype in ["clap","wave","raise_hand","touch_nose","head_tilt","blink"]:
            ST["verify_action"]=vtype; ST["verify_result"]=False
            ST["verify_timeout"]=time.time()+18
        # DTT instruction
        resp=self.g.ask(
            f"Task: '{task['instruction']}' for {name}. "
            f"Em:{ST['emotion']}. Prompt hierarchy attempt 1. "
            "'Ready? Your turn! 🎯'")
        self._speak(resp)
        for attempt in range(3):
            ST["prompt_attempt"]=attempt
            ok=self._wait_task(task,timeout=15)
            if ok: ST["verify_action"]=None; return True
            if attempt<len(prompts):
                hint=prompts[attempt]
                self.v.say(f"{name}... {hint} 🎯",wait=False)
                if self.tw:
                    QTimer.singleShot(0,lambda h=hint:self.tw.set_feedback(h))
                time.sleep(0.5)
        ST["verify_action"]=None
        return False

    def _wait_task(self,task,timeout=15):
        vtype=task["verify"]; keyword=task.get("keyword","")
        deadline=time.time()+timeout
        while time.time()<deadline:
            # Camera-based motor tasks
            if vtype in ["clap","wave","raise_hand","touch_nose","head_tilt","blink"]:
                if ST["verify_result"]: ST["verify_result"]=False; return True
                if vtype=="clap" and ST["clapping"]: return True
                if vtype=="wave" and ST["waving"]: return True
                if vtype=="raise_hand" and ST["hand_raised"]: return True
                if vtype=="blink" and ST["blinking"]: return True
                if vtype=="head_tilt" and ST["head_tilted"]: return True
            # Tablet click
            elif vtype=="tablet_click":
                result=ST.get("tablet_result")
                if result=="correct": ST["tablet_result"]=None; return True
                elif result=="wrong": ST["tablet_result"]=None; return False
            # Speech tasks
            elif vtype=="speech_keyword" and keyword:
                if keyword.lower() in ST.get("last_speech_text","").lower(): return True
            elif vtype in ["speech_any","speech"]:
                if ST["last_sound"]>time.time()-3 and len(ST.get("last_speech_text",""))>0: return True
            elif vtype=="speech_number":
                if any(c.isdigit() for c in ST.get("last_speech_text","")): return True
            elif vtype=="speech_sentence":
                if len(ST.get("last_speech_text","").split())>=3: return True
            # Positive engagement
            if ST["emotion"] in ["happy","joyful"] and ST["attention"]>70: return True
            time.sleep(0.2)
        return False

    def _on_success(self,task):
        name=ST["name"]
        ST["consecutive_successes"]+=1
        ST["score"]+=task.get("tokens",2)*5
        ST["tokens"]+=task.get("tokens",2)
        ST["tasks_success"]+=1; ST["streak"]+=1
        # Skill update
        sk_map={1:"motor",2:"cognitive",3:"cognitive",4:"cognitive",
                5:"cognitive",6:"cognitive",7:"social"}
        sk=sk_map.get(task["level"],"motor")
        ST["skills"][sk]=min(100,ST["skills"][sk]+random.randint(1,3))
        ST["skills"]["attention"]=min(100,ST["skills"]["attention"]+random.randint(0,2))
        # Show result on tablet
        if self.tw:
            QTimer.singleShot(0,lambda: tablet_signals.show_result.emit(True,"Amazing work!"))
        LOG(f"✅ Success {ST['consecutive_successes']}/3 '{task['name']}'","success")
        # MASTERY CHECK — 3 consecutive successes
        if ST["consecutive_successes"]>=3:
            ST["consecutive_successes"]=0
            ST["tasks_mastered"]+=1
            ST["task_index"]+=1
            # Wrap around (infinite progression)
            if ST["task_index"]>=len(TASK_LIBRARY):
                ST["task_index"]=0
                ST["current_level"]+=1  # Keep incrementing level
            next_task=TASK_LIBRARY[ST["task_index"]%len(TASK_LIBRARY)]
            LOG(f"🏆 MASTERED! Next: {next_task['name']}","success")
            self._ask(
                f"{name} MASTERED that task with 3 successes! [LEVEL_UP][CELEBRATE][DANCE] "
                f"Now we try: '{next_task['instruction'][:30]}' [WAVE]")
            # YouTube reward if applicable
            if task.get("reward")=="youtube":
                ST["youtube_pending"]=True
                self._ask(f"{name} earned a video reward! [CELEBRATE] "
                          "Ask what video they want! 🎬")
        else:
            self.v.say(EMPATHY.get("task_ok"),wait=False)
            if self.tw:
                QTimer.singleShot(500,lambda:self.tw.reset_cards())

    def _on_fail(self,task):
        ST["consecutive_successes"]=0  # Reset mastery streak
        ST["streak"]=0; ST["tasks_fail"]+=1
        self.v.say(EMPATHY.get("task_retry"),wait=False)
        if self.tw:
            QTimer.singleShot(0,lambda:tablet_signals.show_result.emit(False,"Try again!"))
            QTimer.singleShot(2000,lambda:self.tw.reset_cards())

    def _handle_cmd(self):
        cmd=ST.get("sim_cmd")
        if not cmd: return
        ST["sim_cmd"]=None
        if cmd=="dance": self._ask("Dance joyfully! [DANCE][CELEBRATE]")
        elif cmd=="game":
            webbrowser.open(GAME_URL)
            self.v.say(f"Opening games {ST['name']}! [GAME] 🎮",wait=False)
        elif cmd=="celebrate": self._ask("Big celebration! [CELEBRATE][CLAP][DANCE]")
        elif cmd=="break": self.v.say("Break time! Rest and relax.",wait=False)
        elif cmd=="next_task":
            ST["consecutive_successes"]=0
            ST["task_index"]=(ST["task_index"]+1)%len(TASK_LIBRARY)
            self.v.say(f"Next task coming up {ST['name']}! 🎯",wait=False)
        elif cmd=="report" and _gemini:
            r=_gemini.generate_report()
            ST["reports"].append({"time":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"content":r})

    def _on_speech(self,text):
        ST["last_sound"]=time.time(); ST["waiting_for_child"]=False
        ST["last_speech_text"]=text
        if not text: return
        t=text.lower(); name=ST["name"]
        if text=="[sound]":
            self.v.say(f"I heard you {name}! Great!",wait=False); return
        if ST["is_speaking"]: self.v.stop(); time.sleep(0.1)
        if not ST["known"]:
            n=self.m._extract(text)
            if n: ST["name"]=n; ST["known"]=True; self._ask(f"Welcome {n}! [WAVE] 🎯")
            return
        # YouTube pending
        if ST.get("youtube_pending"):
            ST["youtube_pending"]=False
            self.a.process(f"[YOUTUBE: {text} autism children educational]"); return
        # Game
        if any(w in t for w in ["game","play","العب","لعبة"]):
            webbrowser.open(GAME_URL)
            self.v.say(f"Opening games {name}! [GAME] 🎮",wait=False); return
        # Educational question
        edu_kw=["how","what","why","where","when","who","show","teach","كيف","ما هو","لماذا","أين","متى"]
        if any(w in t for w in edu_kw):
            resp=self.g.ask(f"Child asked: '{text}'. Answer clearly! [YOUTUBE: {text}] 🎯")
            self._speak(resp); return
        # Emotional
        emo_kw=["happy","sad","angry","scared","love","tired","hurt","حزين","خايف","زعلان","مبسوط"]
        if any(w in t for w in emo_kw):
            resp=self.g.ask(f"Child expressed: '{text}'. [HUG] Empathy! 🎯")
            self._speak(resp); return
        # Default smart response
        resp=self.g.ask(f"Child said: '{text}'. Respond therapeutically! 'Ready? Your turn! 🎯'")
        self._speak(resp)

# ═══════════════════════════════════════════════════════════════
# 16. MAIN — Launch everything
# ═══════════════════════════════════════════════════════════════
def main():
    global _gemini

    print(f"""
╔══════════════════════════════════════════════════════════════╗
║  PEPPER CLINICAL THERAPY SYSTEM                             ║
║  Commander: Lamya | Omdurman Islamic University             ║
╠══════════════════════════════════════════════════════════════╣
║  PyQt6 HD Tablet | ABA/ESDM | Mastery Rule (3 successes)   ║
║  MediaPipe Pose+FaceMesh | Lip-Sync | faster-whisper        ║
╠══════════════════════════════════════════════════════════════╣
║  Window 1: PyBullet (auto-opens)                           ║
║  Window 2: Emotion + Skeleton (600x600 resizable)          ║
║  Window 3: Live Session + Avatar (820x520 resizable)       ║
║  Window 4: PyQt6 Tablet UI (700x900 HD)                    ║
╠══════════════════════════════════════════════════════════════╣
║  Laptop:  http://127.0.0.1:5007                             ║
║  Android: http://{LOCAL_IP}:5007                            ║
╚══════════════════════════════════════════════════════════════╝
""")

    # Start Flask servers
    for app,port,name in [(game_app,PORT_GAME,"Game"),
                          (rep_app,PORT_REP,"Reports"),
                          (brain_app,PORT_BRAIN,"Brain")]:
        threading.Thread(target=run_server,args=(app,port,name),daemon=True).start()
        time.sleep(0.4)
    time.sleep(0.8)

    # Init systems
    gemini=GeminiBrain(); _gemini=gemini
    voice=Voice(); camera=Camera()
    vision=VisionEngine(); display=Display(vision,camera)
    mic=Mic()
    sim=PepperSim(); pepper=sim.launch()
    acts=Actions(pepper)
    threading.Thread(target=acts.run_lip_sync_pybullet,daemon=True).start()

    time.sleep(1.5)

    # PyQt6 App — must run on main thread
    qt_app=QApplication(sys.argv)
    qt_app.setApplicationName("Pepper Clinical Therapy")
    qt_app.setStyle("Fusion")
    palette=QPalette()
    palette.setColor(QPalette.ColorRole.Window,QColor(6,9,18))
    palette.setColor(QPalette.ColorRole.WindowText,QColor(224,230,255))
    palette.setColor(QPalette.ColorRole.Base,QColor(12,15,30))
    palette.setColor(QPalette.ColorRole.Text,QColor(224,230,255))
    qt_app.setPalette(palette)

    tablet_win=TabletWindow()
    tablet_win.show()
    tablet_win.move(10,600)  # Bottom-left

    # Start therapy in background thread
    ctrl=TherapyCtrl(gemini,voice,mic,display,sim,acts,tablet_win)
    therapy_thread=threading.Thread(target=ctrl.run,daemon=True)

    # Welcome
    def _start():
        time.sleep(0.5)
        voice.say("Welcome to Pepper Clinical Therapy! "
                  "Commander Lamya, all four windows are active! "
                  "The tablet is ready! Starting now!",wait=False)
        if pepper:
            threading.Thread(target=acts._wave,daemon=True).start()
        therapy_thread.start()

    threading.Thread(target=_start,daemon=True).start()

    print(f"""
{'='*62}
✅ ALL SYSTEMS ACTIVE — 4 WINDOWS
{'='*62}
Window 1: PyBullet  (auto-opened)
Window 2: Emotion + Skeleton (600x600)
Window 3: Live Session (820x520)
Window 4: PyQt6 Tablet (700x900) HD ← Child clicks here!

Laptop  → http://127.0.0.1:{PORT_BRAIN}/
Android → http://{LOCAL_IP}:{PORT_BRAIN}/
Tablet  → PyQt6 window (bottom-left)
{'='*62}
Close the tablet window or press Ctrl+C to exit.
{'='*62}
""")

    # Input loop in background
    def _input_loop():
        while ctrl.running:
            try:
                cmd=input("> ").strip()
                if not cmd: continue
                cl=cmd.lower()
                if cl in ["q","exit","quit"]:
                    ctrl.running=False; display.stop()
                    qt_app.quit(); break
                elif cl=="stats":
                    print(f"\n Child:{ST['name']} Level:{ST['current_level']} "
                          f"Mastery:{ST['consecutive_successes']}/3 "
                          f"Mastered:{ST['tasks_mastered']} Score:{ST['score']}")
                elif cl.startswith("name "):
                    n=cl[5:].strip().title(); ST["name"]=n; ST["known"]=True
                    voice.say(f"Hello {n}!",wait=False)
                elif cl in ["stop","interrupt"]:
                    voice.stop()
                else:
                    ctrl._on_speech(cmd)
            except (KeyboardInterrupt,EOFError): break
        qt_app.quit()

    threading.Thread(target=_input_loop,daemon=True).start()

    # Qt event loop (blocks until closed)
    ret=qt_app.exec()

    # Shutdown
    ctrl.running=False; display.stop()
    if _gemini:
        r=_gemini.generate_report()
        ST["reports"].append({"time":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"content":r})
    voice.say("Goodbye! Amazing session!",wait=False)
    fn=f"session_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(fn,"w") as f: json.dump(ST,f,indent=2,default=str)
    print(f"\n📄 Saved: {fn} | Goodbye Commander Lamya!")
    sys.exit(ret)

if __name__=="__main__":
    main()
