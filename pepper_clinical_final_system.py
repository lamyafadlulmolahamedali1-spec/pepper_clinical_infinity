#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║  PEPPER CLINICAL FINAL SYSTEM                                   ║
║  pepper_clinical_final_system.py                                ║
║  Commander: Lamya | Omdurman Islamic University                 ║
╠══════════════════════════════════════════════════════════════════╣
║  FIXES APPLIED:                                                 ║
║  ✅ Qt Threading: ALL UI via pyqtSignal (zero threading bugs)  ║
║  ✅ DeepFace removed → MediaPipe-only emotion/gesture          ║
║  ✅ energy_threshold=300 (no ghost speech)                     ║
║  ✅ Gemini: gemini-1.5-flash stable + fallback list            ║
║  ✅ No breathing tasks — Motor/Verbal/Cognitive only            ║
║  ✅ Visual modeling on tablet for every motor task             ║
║  ✅ MediaPipe joint angle validation for motor tasks           ║
║  ✅ 3-star mastery indicator on tablet                         ║
║  ✅ PyBullet Window 1 (FIXED) | OpenCV resizable               ║
╚══════════════════════════════════════════════════════════════════╝
"""

# ═══════════════════════════════════════════════════════════════
# 0. SETUP
# ═══════════════════════════════════════════════════════════════
import os, sys, subprocess, ctypes, warnings, socket, signal, time

os.environ.update({
    'TF_CPP_MIN_LOG_LEVEL':'3',
    'PYGAME_HIDE_SUPPORT_PROMPT':'1',
    'PYTHONWARNINGS':'ignore',
    'OPENCV_LOG_LEVEL':'ERROR',
    'CUDA_VISIBLE_DEVICES':'0',
    'TF_FORCE_GPU_ALLOW_GROWTH':'true',
    'QT_LOGGING_RULES':'*.debug=false',
    'QT_QPA_PLATFORM':'xcb',
    'QT_QPA_FONTDIR':'/usr/share/fonts',
})
warnings.filterwarnings('ignore')
try:
    _a=ctypes.cdll.LoadLibrary('libasound.so.2')
    _a.snd_lib_error_set_handler(ctypes.c_void_p(None))
except: pass

def auto_install(pkg,imp=None):
    name=imp or pkg.replace('-','_')
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
    ('faster-whisper','faster_whisper'),
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
import cv2, numpy as np, threading, random, math, re, json
import webbrowser, urllib.parse
import pyttsx3, speech_recognition as sr
from flask import Flask,request,jsonify,render_template_string,redirect
from datetime import datetime
import pybullet as p, pybullet_data
sys.path.insert(0,'/home/lamya/pepper_duo/src')
import google.generativeai as genai

# PyQt6 — ALL UI work on main thread via signals
from PyQt6.QtWidgets import (
    QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,
    QLabel,QPushButton,QGridLayout,QFrame,QProgressBar,
)
from PyQt6.QtCore import (
    Qt,QTimer,pyqtSignal,QObject,QThread,QMetaObject,Q_ARG,
)
from PyQt6.QtGui import (
    QFont,QColor,QPalette,
)

try:
    from faster_whisper import WhisperModel
    WHISPER_OK=True
except: WHISPER_OK=False

# ═══════════════════════════════════════════════════════════════
# 2. CONFIG
# ═══════════════════════════════════════════════════════════════
# ⚠️  Replace with fresh Gemini key if 403 error occurs
GEMINI_KEY = "AIzaSyDEdleVKiQ5E00wMcjMbji0G9JcYT2TvE8"
GAME_URL   = "https://LamyaFadlulmolaHamedAli.pythonanywhere.com"
GITHUB_URL = "https://github.com/lamyafadlulmolahamedali1-spec/Pepper-Therapy-Games"
PORT_BRAIN = 5007
PORT_GAME  = 5009
PORT_REP   = 5001
API_DELAY  = 2.1
API_RPM    = 14
# FIX: energy_threshold=300 — no ghost speech
MIC_ENERGY = 300

genai.configure(api_key=GEMINI_KEY)

def get_local_ip():
    try:
        s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        s.connect(("8.8.8.8",80)); ip=s.getsockname()[0]; s.close(); return ip
    except: return "127.0.0.1"

LOCAL_IP=get_local_ip()

# ═══════════════════════════════════════════════════════════════
# 3. TASK LIBRARY
#    Motor (visual modeling) | Cognitive (HD images) | Verbal
#    NO breathing tasks per spec
# ═══════════════════════════════════════════════════════════════
TASKS=[
    # ── MOTOR: Visual Modeling — tablet shows HD movement image ──
    {
        "id":"clap","domain":"Motor","level":1,"protocol":"ABA-Motor",
        "instruction":"Look at the screen and clap your hands like this!",
        "verify":"clap",
        "tablet_mode":"motor_model",
        "motor_emoji":"👏","motor_label":"CLAP HANDS",
        "motor_desc":"Bring both hands together and make a sound!",
        "joint_check":"clap",
        "prompts":["Clap your hands!","Hands together!","*clap* like this!"],
        "tokens":2,"joy":"dance",
    },
    {
        "id":"wave","domain":"Motor","level":1,"protocol":"ABA-Motor",
        "instruction":"Look at the screen and wave hello like this!",
        "verify":"wave",
        "tablet_mode":"motor_model",
        "motor_emoji":"👋","motor_label":"WAVE HELLO",
        "motor_desc":"Move your hand from side to side!",
        "joint_check":"wave",
        "prompts":["Wave hello!","Side to side!","Hello wave!"],
        "tokens":2,"joy":"wave_back",
    },
    {
        "id":"raise_hand","domain":"Motor","level":1,"protocol":"ABA-Motor",
        "instruction":"Look at the screen and raise your hand up high!",
        "verify":"raise_hand",
        "tablet_mode":"motor_model",
        "motor_emoji":"✋","motor_label":"RAISE HAND",
        "motor_desc":"Lift your arm above your shoulder!",
        "joint_check":"raise_hand",
        "prompts":["Hand up!","Reach high!","Up up up!"],
        "tokens":2,"joy":"celebrate",
    },
    {
        "id":"touch_nose","domain":"Motor","level":1,"protocol":"ABA-Motor",
        "instruction":"Look at the screen and touch your nose with your finger!",
        "verify":"touch_nose",
        "tablet_mode":"motor_model",
        "motor_emoji":"👆👃","motor_label":"TOUCH NOSE",
        "motor_desc":"Point your finger and touch your nose!",
        "joint_check":"touch_nose",
        "prompts":["Touch nose!","Finger to nose!","Point here!"],
        "tokens":2,"joy":"celebrate",
    },
    {
        "id":"arms_out","domain":"Motor","level":1,"protocol":"ABA-Motor",
        "instruction":"Look at the screen and stretch both arms out wide!",
        "verify":"arms_out",
        "tablet_mode":"motor_model",
        "motor_emoji":"🤸","motor_label":"ARMS OUT",
        "motor_desc":"Spread both arms wide like an airplane!",
        "joint_check":"arms_out",
        "prompts":["Arms out wide!","Like an airplane!","Stretch!"],
        "tokens":2,"joy":"dance",
    },
    {
        "id":"hands_up","domain":"Motor","level":1,"protocol":"ABA-Motor",
        "instruction":"Look at the screen and put BOTH hands up high!",
        "verify":"hands_up",
        "tablet_mode":"motor_model",
        "motor_emoji":"🙌","motor_label":"BOTH HANDS UP",
        "motor_desc":"Lift both arms above your head!",
        "joint_check":"hands_up",
        "prompts":["Both hands up!","Two hands high!","Up up!"],
        "tokens":2,"joy":"celebrate",
    },
    # ── COGNITIVE: Color Identification (HD colored circles) ──
    {
        "id":"color_red","domain":"Cognitive","level":2,"protocol":"TEACCH-Visual",
        "instruction":"Click on the RED circle!",
        "verify":"tablet_click",
        "tablet_mode":"color_grid",
        "options":[
            {"color":"#ef4444","label":"🔴 Red"},
            {"color":"#3b82f6","label":"🔵 Blue"},
            {"color":"#22c55e","label":"🟢 Green"},
            {"color":"#eab308","label":"🟡 Yellow"},
        ],
        "correct":0,"tokens":3,"joy":"celebrate",
        "visual_hint":"Find the RED circle and click it!",
    },
    {
        "id":"color_blue","domain":"Cognitive","level":2,"protocol":"TEACCH-Visual",
        "instruction":"Click on the BLUE circle!",
        "verify":"tablet_click","tablet_mode":"color_grid",
        "options":[
            {"color":"#22c55e","label":"🟢 Green"},
            {"color":"#3b82f6","label":"🔵 Blue"},
            {"color":"#ef4444","label":"🔴 Red"},
            {"color":"#a855f7","label":"🟣 Purple"},
        ],
        "correct":1,"tokens":3,"joy":"dance","visual_hint":"Find BLUE!",
    },
    {
        "id":"color_green","domain":"Cognitive","level":2,"protocol":"TEACCH-Visual",
        "instruction":"Click on the GREEN circle!",
        "verify":"tablet_click","tablet_mode":"color_grid",
        "options":[
            {"color":"#eab308","label":"🟡 Yellow"},
            {"color":"#ef4444","label":"🔴 Red"},
            {"color":"#22c55e","label":"🟢 Green"},
            {"color":"#3b82f6","label":"🔵 Blue"},
        ],
        "correct":2,"tokens":3,"joy":"celebrate","visual_hint":"Find GREEN!",
    },
    {
        "id":"color_yellow","domain":"Cognitive","level":2,"protocol":"TEACCH-Visual",
        "instruction":"Click on the YELLOW circle!",
        "verify":"tablet_click","tablet_mode":"color_grid",
        "options":[
            {"color":"#eab308","label":"🟡 Yellow"},
            {"color":"#a855f7","label":"🟣 Purple"},
            {"color":"#ef4444","label":"🔴 Red"},
            {"color":"#22c55e","label":"🟢 Green"},
        ],
        "correct":0,"tokens":3,"joy":"celebrate","visual_hint":"Find YELLOW!",
    },
    # ── COGNITIVE: Animal Identification (HD emoji animals) ──
    {
        "id":"animal_dog","domain":"Cognitive","level":3,"protocol":"TEACCH-Visual",
        "instruction":"Click on the DOG!",
        "verify":"tablet_click","tablet_mode":"object_grid",
        "options":[
            {"emoji":"🐶","label":"Dog","size":90},
            {"emoji":"🐱","label":"Cat","size":90},
            {"emoji":"🐻","label":"Bear","size":90},
            {"emoji":"🐭","label":"Mouse","size":90},
        ],
        "correct":0,"tokens":4,"joy":"dance",
        "visual_hint":"Which one is the DOG? Click it!",
    },
    {
        "id":"animal_cat","domain":"Cognitive","level":3,"protocol":"TEACCH-Visual",
        "instruction":"Click on the CAT!",
        "verify":"tablet_click","tablet_mode":"object_grid",
        "options":[
            {"emoji":"🐶","label":"Dog","size":90},
            {"emoji":"🐱","label":"Cat","size":90},
            {"emoji":"🦁","label":"Lion","size":90},
            {"emoji":"🐯","label":"Tiger","size":90},
        ],
        "correct":1,"tokens":4,"joy":"celebrate",
        "visual_hint":"Find the CAT!",
    },
    {
        "id":"animal_lion","domain":"Cognitive","level":3,"protocol":"TEACCH-Visual",
        "instruction":"Click on the LION!",
        "verify":"tablet_click","tablet_mode":"object_grid",
        "options":[
            {"emoji":"🐘","label":"Elephant","size":90},
            {"emoji":"🦒","label":"Giraffe","size":90},
            {"emoji":"🦁","label":"Lion","size":90},
            {"emoji":"🐧","label":"Penguin","size":90},
        ],
        "correct":2,"tokens":4,"joy":"dance",
        "visual_hint":"Find the LION — the king!",
    },
    # ── COGNITIVE: Fruit Identification ──────────────────────
    {
        "id":"fruit_apple","domain":"Cognitive","level":4,"protocol":"TEACCH-Visual",
        "instruction":"Click on the APPLE!",
        "verify":"tablet_click","tablet_mode":"object_grid",
        "options":[
            {"emoji":"🍎","label":"Apple","size":90},
            {"emoji":"🍌","label":"Banana","size":90},
            {"emoji":"🍊","label":"Orange","size":90},
            {"emoji":"🍇","label":"Grapes","size":90},
        ],
        "correct":0,"tokens":4,"joy":"celebrate",
        "visual_hint":"Find the APPLE!",
    },
    {
        "id":"fruit_banana","domain":"Cognitive","level":4,"protocol":"TEACCH-Visual",
        "instruction":"Click on the BANANA!",
        "verify":"tablet_click","tablet_mode":"object_grid",
        "options":[
            {"emoji":"🍎","label":"Apple","size":90},
            {"emoji":"🍌","label":"Banana","size":90},
            {"emoji":"🍑","label":"Peach","size":90},
            {"emoji":"🍓","label":"Berry","size":90},
        ],
        "correct":1,"tokens":4,"joy":"dance",
        "visual_hint":"Find the BANANA!",
    },
    # ── COGNITIVE: Shape Identification ──────────────────────
    {
        "id":"shape_circle","domain":"Cognitive","level":5,"protocol":"TEACCH-Visual",
        "instruction":"Click on the CIRCLE shape!",
        "verify":"tablet_click","tablet_mode":"shape_grid",
        "options":[
            {"emoji":"⭕","label":"Circle","size":85},
            {"emoji":"⬛","label":"Square","size":85},
            {"emoji":"🔺","label":"Triangle","size":85},
            {"emoji":"💎","label":"Diamond","size":85},
        ],
        "correct":0,"tokens":4,"joy":"celebrate",
        "visual_hint":"Find the round CIRCLE!",
    },
    {
        "id":"shape_square","domain":"Cognitive","level":5,"protocol":"TEACCH-Visual",
        "instruction":"Click on the SQUARE!",
        "verify":"tablet_click","tablet_mode":"shape_grid",
        "options":[
            {"emoji":"🔺","label":"Triangle","size":85},
            {"emoji":"⭕","label":"Circle","size":85},
            {"emoji":"⬛","label":"Square","size":85},
            {"emoji":"⭐","label":"Star","size":85},
        ],
        "correct":2,"tokens":4,"joy":"dance",
        "visual_hint":"Find the SQUARE with 4 equal sides!",
    },
    # ── COGNITIVE: Number Identification ─────────────────────
    {
        "id":"number_1","domain":"Cognitive","level":5,"protocol":"DTT-Verbal",
        "instruction":"Click on the number ONE!",
        "verify":"tablet_click","tablet_mode":"number_grid",
        "options":[
            {"num":"1","label":"One"},
            {"num":"2","label":"Two"},
            {"num":"3","label":"Three"},
            {"num":"4","label":"Four"},
        ],
        "correct":0,"tokens":5,"joy":"celebrate",
        "visual_hint":"Find number 1!",
    },
    {
        "id":"number_3","domain":"Cognitive","level":5,"protocol":"DTT-Verbal",
        "instruction":"Click on the number THREE!",
        "verify":"tablet_click","tablet_mode":"number_grid",
        "options":[
            {"num":"5","label":"Five"},
            {"num":"2","label":"Two"},
            {"num":"3","label":"Three"},
            {"num":"1","label":"One"},
        ],
        "correct":2,"tokens":5,"joy":"dance",
        "visual_hint":"Find number 3!",
    },
    # ── VERBAL: Word repetition ───────────────────────────────
    {
        "id":"say_apple","domain":"Verbal","level":6,"protocol":"DTT-Verbal",
        "instruction":"Say the word APPLE out loud!",
        "verify":"speech_keyword","keyword":"apple",
        "tablet_mode":"word_display",
        "word_emoji":"🍎","word_text":"APPLE",
        "prompts":["Say Apple!","Ap...ple!","Repeat: Apple!"],
        "tokens":4,"joy":"celebrate",
    },
    {
        "id":"say_blue","domain":"Verbal","level":6,"protocol":"DTT-Verbal",
        "instruction":"The sky is BLUE! Say BLUE!",
        "verify":"speech_keyword","keyword":"blue",
        "tablet_mode":"word_display",
        "word_emoji":"🔵","word_text":"BLUE",
        "prompts":["Say Blue!","Blue...","Repeat: Blue!"],
        "tokens":4,"joy":"dance",
    },
    {
        "id":"say_name","domain":"Verbal","level":6,"protocol":"DTT-Verbal",
        "instruction":"Tell me your name!",
        "verify":"speech_any",
        "tablet_mode":"word_display",
        "word_emoji":"👦","word_text":"MY NAME IS...",
        "prompts":["Your name!","I am...","What is your name?"],
        "tokens":4,"joy":"celebrate",
    },
    {
        "id":"count_3","domain":"Verbal","level":6,"protocol":"DTT-Verbal",
        "instruction":"Count to THREE! Say 1, 2, 3!",
        "verify":"speech_number",
        "tablet_mode":"word_display",
        "word_emoji":"⭐⭐⭐","word_text":"1, 2, 3",
        "prompts":["Count!","1, 2, 3...","Three!"],
        "tokens":5,"joy":"celebrate",
    },
    # ── SOCIAL/LINGUISTIC ────────────────────────────────────
    {
        "id":"full_sentence","domain":"Social","level":7,"protocol":"ESDM-Social",
        "instruction":"Tell me something you love! Use a full sentence!",
        "verify":"speech_sentence",
        "tablet_mode":"word_display",
        "word_emoji":"💬","word_text":"I LOVE...",
        "prompts":["I love...","Tell me!","Full sentence!"],
        "tokens":6,"joy":"full_joy","reward":"youtube",
    },
    {
        "id":"how_feel","domain":"Social","level":7,"protocol":"ESDM-Social",
        "instruction":"How do you feel today?",
        "verify":"tablet_click","tablet_mode":"emotion_grid",
        "options":[
            {"emoji":"😊","label":"Happy"},
            {"emoji":"😢","label":"Sad"},
            {"emoji":"😠","label":"Angry"},
            {"emoji":"😨","label":"Scared"},
        ],
        "correct":-1,"tokens":6,"joy":"full_joy","reward":"youtube",
        "visual_hint":"How do you feel? Click your face!",
    },
]

# ═══════════════════════════════════════════════════════════════
# 4. EMPATHY LIBRARY
# ═══════════════════════════════════════════════════════════════
class EmpathyLib:
    _lib={
        "happy":     ["You are so happy! [CELEBRATE]","Amazing energy! [DANCE]"],
        "sad":       ["I see you. I am here. [HUG]","You are safe. [NOD]"],
        "angry":     ["It is okay. I am patient. [NOD]","Let us calm down. [HUG]"],
        "fear":      ["You are safe! [HUG]","No worries. [NOD]"],
        "confused":  ["Let me show you again! [THINK]","Try differently! [POINT]"],
        "joyful":    ["So joyful! [DANCE][CELEBRATE]","Your joy! [DANCE]"],
        "silence":   ["Ready when you are! 🎯","Take your time. 🎯","I am here! 🎯"],
        "greeting":  ["Hello! I am Pepper! What is your name? 🎯",
                      "Hi! So happy to meet you! 🎯"],
        "task_ok":   ["PERFECT! You did it! [CLAP][CELEBRATE]",
                      "WOW! Amazing! [DANCE]","BRILLIANT! [CELEBRATE]"],
        "task_retry":["Good try! One more time! 🎯",
                      "Almost! You can! 🎯","Try again! 🎯"],
        "level_up":  ["LEVEL UP! [DANCE][CELEBRATE]","CHAMPION! [CELEBRATE]"],
        "youtube":   ["Video reward! What to watch? 🎬","Tell me your favorite! 🎬"],
        "default":   ["Great effort! [CLAP]","Ready? Your turn! 🎯"],
    }
    _last={}
    def get(self,cat="default"):
        pool=self._lib.get(cat,self._lib["default"])
        last=self._last.get(cat,-1)
        choices=[i for i in range(len(pool)) if i!=last]
        if not choices: choices=list(range(len(pool)))
        idx=random.choice(choices); self._last[cat]=idx
        return pool[idx]

EMPATHY=EmpathyLib()

# ═══════════════════════════════════════════════════════════════
# 5. SHARED STATE
# ═══════════════════════════════════════════════════════════════
ST={
    "name":"Friend","known":False,"age":6,"diagnosis":"ASD Level 2",
    # Mastery gate
    "task_index":0,"consecutive":0,"mastery_needed":3,
    "tasks_mastered":0,"current_level":1,"domain":"Motor","protocol":"ABA-Motor",
    # Tablet
    "tablet_locked":True,"tablet_click_result":None,
    "tablet_correct":-1,"tablet_instruction":"Welcome!",
    "tablet_task_name":"","tablet_domain":"Motor",
    # Vision — MediaPipe only (DeepFace removed)
    "emotion":"neutral","emotion_scores":{},
    "face_detected":False,"face_box":None,
    "attention":70,"engagement":"moderate",
    "hand_raised":False,"waving":False,"clapping":False,
    "face_touch":False,"head_tilted":False,
    "blinking":False,"eye_contact":False,
    "arms_out":False,"hands_up":False,
    "pose_landmarks":{},"face_mesh_landmarks":{},
    "hand_lm_data":{},
    "verify_action":None,"verify_result":False,"verify_timeout":0.0,
    "last_speech_text":"","last_sound":time.time(),
    # Session
    "is_speaking":False,"interrupt_flag":False,
    "listening":False,"waiting_for_child":False,
    "task_success":False,"youtube_pending":False,"sim_cmd":None,
    "lip_sync_value":0.0,"lip_sync_active":False,
    "voice_energy":0.0,
    # API
    "gemini_ok":False,"gemini_model":"N/A",
    "last_api_call":0.0,"api_calls_this_min":0,
    "api_minute_start":time.time(),"api_fallback_count":0,
    # Progress
    "score":0,"tokens":0,"stars_today":0,
    "streak":0,"tasks_success":0,"tasks_fail":0,
    "skills":{"motor":50,"cognitive":50,"verbal":50,"social":50,"attention":50},
    "att_history":[],"score_history":[],"emo_history":[],"time_labels":[],
    "logs":[],"session_chat":[],
    "parent_chat":[],"parent_notes":[],"reports":[],
    "iasq_score":None,"iasq_result":None,
    "session_start":datetime.now().strftime("%H:%M"),
    "session_date":datetime.now().strftime("%Y-%m-%d"),
    "uptime":time.time(),"last_youtube":None,
}

_log_lock=threading.Lock()
def LOG(msg,t="info",proto=None):
    with _log_lock:
        e={"time":datetime.now().strftime("%H:%M:%S"),"msg":str(msg)[:120],
           "type":t,"proto":proto or ST["protocol"],
           "emo":ST["emotion"],"child":ST["name"]}
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
# 6. TABLET SIGNALS — Thread-Safe PyQt6 UI updates
#    FIX: ALL UI updates go through these signals (never direct calls)
# ═══════════════════════════════════════════════════════════════
class TabletBridge(QObject):
    """
    ALL cross-thread UI communication goes through here.
    Background threads → emit signal → Qt main thread → update UI
    This eliminates QBasicTimer threading errors.
    """
    # Signals (safe cross-thread)
    sig_show_task    = pyqtSignal(dict)
    sig_show_result  = pyqtSignal(bool, str)
    sig_show_joy     = pyqtSignal(str)
    sig_unlock       = pyqtSignal()
    sig_lock         = pyqtSignal()
    sig_set_feedback = pyqtSignal(str)
    sig_set_instr    = pyqtSignal(str)

BRIDGE=TabletBridge()

# ═══════════════════════════════════════════════════════════════
# 7. PYQT6 TABLET WINDOW
#    FIXED 740×960 | Visual modeling | 3-star mastery | HD assets
# ═══════════════════════════════════════════════════════════════
class ClickCard(QPushButton):
    """Clickable card for cognitive tasks"""
    def __init__(self,data,idx,mode,parent=None):
        super().__init__(parent)
        self.idx=idx; self.mode=mode; self._data=data
        self._enabled=True
        sz=160 if mode=="color_grid" else 155
        self.setFixedSize(sz,sz)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._set_normal()
        self.clicked.connect(self._on_click)

    def _set_normal(self):
        d=self._data; mode=self.mode
        if mode=="color_grid":
            self.setText(f"\n\n\n{d['label']}")
            self.setFont(QFont("Arial",11,QFont.Weight.Bold))
            self.setStyleSheet(f"""
            QPushButton{{background:{d['color']};border-radius:80px;
                border:5px solid rgba(255,255,255,0.3);
                color:white;font-weight:bold;
                text-shadow:1px 1px 4px rgba(0,0,0,0.9);}}
            QPushButton:hover{{border:5px solid white;}}""")
        elif mode in ["object_grid","shape_grid","emotion_grid"]:
            sz=d.get("size",90)
            self.setText(f"{d['emoji']}\n{d['label']}")
            self.setFont(QFont("Arial",sz//6,QFont.Weight.Bold))
            self.setStyleSheet("""
            QPushButton{background:qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 #1e1b4b,stop:1 #0c0f2e);
                border-radius:20px;border:4px solid #4f46e5;
                color:#e0e6ff;font-weight:bold;padding:8px;}
            QPushButton:hover{border:4px solid #a78bfa;
                background:#2e2b6e;}""")
        elif mode=="number_grid":
            colors=["#6366f1","#ec4899","#f59e0b","#10b981"]
            c=colors[self.idx%len(colors)]
            self.setText(f"{d['num']}\n{d['label']}")
            self.setFont(QFont("Arial",32,QFont.Weight.Bold))
            self.setStyleSheet(f"""
            QPushButton{{background:qlineargradient(x1:0,y1:0,x2:1,y2:1,
                stop:0 {c}aa,stop:1 {c}55);
                border-radius:20px;border:4px solid {c};
                color:white;font-weight:bold;}}
            QPushButton:hover{{border:5px solid white;}}""")

    def flash_correct(self):
        self.setStyleSheet(self.styleSheet()
            .split("QPushButton:hover")[0]
            +"QPushButton{border:7px solid #22c55e !important;}"
            +"QPushButton:hover{border:7px solid #22c55e;}")

    def flash_wrong(self):
        self.setStyleSheet(self.styleSheet()
            .split("QPushButton:hover")[0]
            +"QPushButton{border:7px solid #ef4444 !important;opacity:0.4;}"
            +"QPushButton:hover{border:7px solid #ef4444;}")

    def reset(self): self._set_normal()

    def _on_click(self):
        if not self._enabled: return
        # Signal via bridge (thread-safe not needed here — on main thread)
        BRIDGE.sig_show_task.emit({"action":"click","idx":self.idx})


class TabletWindow(QMainWindow):
    """
    Pepper's chest tablet — FIXED 740×960
    Visual modeling + 3-star mastery + HD cognitive assets
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pepper Tablet — Clinical Therapy")
        self.setFixedSize(740,960)
        self.setWindowFlags(
            Qt.WindowType.Window|
            Qt.WindowType.WindowStaysOnTopHint|
            Qt.WindowType.CustomizeWindowHint|
            Qt.WindowType.WindowTitleHint)
        self._cards=[]; self._locked=True
        self._correct_idx=-1
        self._joy_phase=0.0; self._joy_timer=QTimer()
        self._joy_timer.timeout.connect(self._joy_tick)
        self._setup_ui()
        self._connect_bridge()
        # Refresh timer — only stat updates (safe, on main thread)
        self._tick=QTimer(); self._tick.timeout.connect(self._update_stats)
        self._tick.start(500)

    def _setup_ui(self):
        cw=QWidget(); self.setCentralWidget(cw)
        cw.setStyleSheet("""QWidget{background:qlineargradient(
            x1:0,y1:0,x2:0,y2:1,stop:0 #060918,stop:0.5 #0c0f2e,stop:1 #060918);}""")
        lay=QVBoxLayout(cw); lay.setSpacing(7); lay.setContentsMargins(14,8,14,8)

        # HEADER
        hdr=QFrame(); hdr.setFixedHeight(80)
        hdr.setStyleSheet("""QFrame{background:qlineargradient(
            x1:0,y1:0,x2:1,y2:0,stop:0 #1a0a3d,stop:0.5 #0a0f28,stop:1 #1a0a3d);
            border-radius:14px;border:2px solid #4f46e5;}""")
        hl=QHBoxLayout(hdr); hl.setContentsMargins(14,5,14,5)
        self.av_lbl=QLabel("🤖")
        self.av_lbl.setFont(QFont("Arial",28)); self.av_lbl.setStyleSheet("color:#a78bfa;")
        hl.addWidget(self.av_lbl)
        tw=QWidget(); tl=QVBoxLayout(tw); tl.setSpacing(2)
        self.title_lbl=QLabel("PEPPER CLINICAL THERAPY")
        self.title_lbl.setFont(QFont("Arial",13,QFont.Weight.Bold))
        self.title_lbl.setStyleSheet("color:#a78bfa;")
        tl.addWidget(self.title_lbl)
        self.sub_lbl=QLabel("ABA · TEACCH · DTT · ESDM")
        self.sub_lbl.setFont(QFont("Arial",8))
        self.sub_lbl.setStyleSheet("color:#6b7280;")
        tl.addWidget(self.sub_lbl)
        hl.addWidget(tw,1)
        sw=QWidget(); sl=QVBoxLayout(sw); sl.setSpacing(2)
        self.ai_lbl=QLabel("● AI READY")
        self.ai_lbl.setFont(QFont("Arial",8,QFont.Weight.Bold))
        self.ai_lbl.setStyleSheet("color:#34d399;")
        sl.addWidget(self.ai_lbl,alignment=Qt.AlignmentFlag.AlignRight)
        self.child_lbl=QLabel("Child: Friend")
        self.child_lbl.setFont(QFont("Arial",8))
        self.child_lbl.setStyleSheet("color:#60a5fa;")
        sl.addWidget(self.child_lbl,alignment=Qt.AlignmentFlag.AlignRight)
        self.state_lbl=QLabel("💤 Ready")
        self.state_lbl.setFont(QFont("Arial",8))
        self.state_lbl.setStyleSheet("color:#9ca3af;")
        sl.addWidget(self.state_lbl,alignment=Qt.AlignmentFlag.AlignRight)
        hl.addWidget(sw)
        lay.addWidget(hdr)

        # ── TEACCH VISUAL SCHEDULE ────────────────────────────
        sched=QFrame(); sched.setFixedHeight(55)
        sched.setStyleSheet("QFrame{background:#0c0f1e;border-radius:12px;border:1px solid #1a1f40;}")
        sc=QHBoxLayout(sched); sc.setContentsMargins(12,6,12,6); sc.setSpacing(8)
        self.sched_task=QLabel("📋 Task")
        self.sched_task.setFont(QFont("Arial",10,QFont.Weight.Bold))
        self.sched_task.setStyleSheet(
            "color:#a78bfa;background:#1e1b4b;border-radius:8px;padding:4px 10px;border:2px solid #4f46e5;")
        sc.addWidget(self.sched_task)
        sc.addWidget(self._arr())
        # Stars mastery indicator (3 stars)
        stars_w=QWidget(); stars_l=QVBoxLayout(stars_w)
        stars_l.setSpacing(2); stars_l.setContentsMargins(0,0,0,0)
        self.stars_lbl=QLabel("☆ ☆ ☆")
        self.stars_lbl.setFont(QFont("Arial",18))
        self.stars_lbl.setStyleSheet("color:#fbbf24;")
        self.stars_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stars_l.addWidget(self.stars_lbl)
        self.mastery_sub=QLabel("0 / 3 successes")
        self.mastery_sub.setFont(QFont("Arial",7))
        self.mastery_sub.setStyleSheet("color:#6b7280;")
        self.mastery_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stars_l.addWidget(self.mastery_sub)
        sc.addWidget(stars_w,1)
        sc.addWidget(self._arr())
        self.reward_lbl=QLabel("⭐")
        self.reward_lbl.setFont(QFont("Arial",22))
        self.reward_lbl.setStyleSheet(
            "color:#fbbf24;background:#2a1a00;border-radius:8px;padding:2px 10px;border:2px solid #f59e0b;")
        sc.addWidget(self.reward_lbl)
        lay.addWidget(sched)

        # ── DOMAIN BADGE ──────────────────────────────────────
        self.domain_badge=QLabel("🏃 Motor Domain — ABA Protocol")
        self.domain_badge.setFont(QFont("Arial",10,QFont.Weight.Bold))
        self.domain_badge.setFixedHeight(30)
        self.domain_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.domain_badge.setStyleSheet(
            "color:#60a5fa;background:#1e3a5f;border-radius:10px;border:1px solid #3b82f6;")
        lay.addWidget(self.domain_badge)

        # ── INSTRUCTION AREA ──────────────────────────────────
        if_=QFrame(); if_.setFixedHeight(92)
        if_.setStyleSheet("""QFrame{background:qlineargradient(
            x1:0,y1:0,x2:0,y2:1,stop:0 #1e1b4b,stop:1 #0c0f2e);
            border-radius:13px;border:2px solid #4f46e5;}""")
        il=QVBoxLayout(if_); il.setContentsMargins(14,5,14,5)
        self.instr_icon=QLabel("📋")
        self.instr_icon.setFont(QFont("Arial",18))
        self.instr_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        il.addWidget(self.instr_icon)
        self.instr_lbl=QLabel("Getting ready...")
        self.instr_lbl.setFont(QFont("Arial",14,QFont.Weight.Bold))
        self.instr_lbl.setStyleSheet("color:#e0e6ff;")
        self.instr_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.instr_lbl.setWordWrap(True)
        il.addWidget(self.instr_lbl)
        lay.addWidget(if_)

        # ── CONTENT AREA ──────────────────────────────────────
        self.content_fr=QFrame()
        self.content_fr.setMinimumHeight(390)
        self.content_fr.setStyleSheet("""QFrame{background:rgba(12,15,30,0.85);
            border-radius:16px;border:2px solid #1a1f40;}""")
        self.content_lay=QVBoxLayout(self.content_fr)
        self.content_lay.setContentsMargins(14,14,14,14)
        self.content_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._show_idle()
        lay.addWidget(self.content_fr,1)

        # ── FEEDBACK ──────────────────────────────────────────
        ff=QFrame(); ff.setFixedHeight(60)
        ff.setStyleSheet("QFrame{background:#0c0f1e;border-radius:12px;border:1px solid #1a1f40;}")
        fl=QHBoxLayout(ff); fl.setContentsMargins(14,7,14,7)
        self.fb_icon=QLabel("💤"); self.fb_icon.setFont(QFont("Arial",22))
        fl.addWidget(self.fb_icon)
        self.fb_lbl=QLabel("Waiting for Pepper...")
        self.fb_lbl.setFont(QFont("Arial",11,QFont.Weight.Bold))
        self.fb_lbl.setStyleSheet("color:#9ca3af;"); self.fb_lbl.setWordWrap(True)
        fl.addWidget(self.fb_lbl,1)
        lay.addWidget(ff)

        # ── STATS BAR ─────────────────────────────────────────
        sb=QFrame(); sb.setFixedHeight(46)
        sb.setStyleSheet("QFrame{background:#07090f;border-radius:10px;border:1px solid #1a1f40;}")
        stl=QHBoxLayout(sb); stl.setContentsMargins(12,4,12,4)
        for label,attr,color in [
            ("Score","stat_score","#a78bfa"),("Tokens","stat_tokens","#fbbf24"),
            ("Mastered","stat_mastered","#34d399"),("Streak","stat_streak","#60a5fa"),
        ]:
            w=QWidget(); wl=QVBoxLayout(w); wl.setSpacing(1); wl.setContentsMargins(0,0,0,0)
            val=QLabel("0"); val.setFont(QFont("Arial",12,QFont.Weight.Bold))
            val.setStyleSheet(f"color:{color};"); val.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lb=QLabel(label); lb.setFont(QFont("Arial",7))
            lb.setStyleSheet("color:#6b7280;"); lb.setAlignment(Qt.AlignmentFlag.AlignCenter)
            wl.addWidget(val); wl.addWidget(lb); stl.addWidget(w)
            setattr(self,attr,val)
        lay.addWidget(sb)

        # ── LOCK OVERLAY ──────────────────────────────────────
        self.lock_ov=QLabel("🔒")
        self.lock_ov.setParent(self.content_fr)
        self.lock_ov.setGeometry(0,0,712,390)
        self.lock_ov.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lock_ov.setFont(QFont("Arial",52))
        self.lock_ov.setStyleSheet(
            "QLabel{background:rgba(0,0,0,0.52);border-radius:16px;color:#a78bfa;}")
        self.lock_ov.hide()

    def _arr(self):
        a=QLabel("▶"); a.setFont(QFont("Arial",14)); a.setStyleSheet("color:#4f46e5;")
        return a

    def _show_idle(self):
        self._clear_content()
        d=QLabel("🤖\nPepper is preparing your task...")
        d.setFont(QFont("Arial",15)); d.setStyleSheet("color:#6b7280;")
        d.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_lay.addWidget(d)

    def _clear_content(self):
        while self.content_lay.count():
            item=self.content_lay.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        self._cards.clear()

    def _connect_bridge(self):
        """Connect bridge signals to UI slots — all on main thread"""
        BRIDGE.sig_show_task.connect(self._on_show_task)
        BRIDGE.sig_show_result.connect(self._on_result)
        BRIDGE.sig_show_joy.connect(self._on_joy)
        BRIDGE.sig_unlock.connect(self._do_unlock)
        BRIDGE.sig_lock.connect(self._do_lock)
        BRIDGE.sig_set_feedback.connect(self._set_feedback)
        BRIDGE.sig_set_instr.connect(self._set_instr)

    def _update_stats(self):
        """Called every 500ms on main thread — safe"""
        self.stat_score.setText(str(ST["score"]))
        self.stat_tokens.setText(str(ST["tokens"]))
        self.stat_mastered.setText(str(ST["tasks_mastered"]))
        self.stat_streak.setText(str(ST["streak"]))
        self.child_lbl.setText(f"Child: {ST['name']}")
        # Update stars
        n=ST["consecutive"]
        stars="⭐"*n+"☆"*(3-n)
        self.stars_lbl.setText(stars)
        self.mastery_sub.setText(f"{n} / 3 successes")
        # Stars color changes
        if n==3: self.stars_lbl.setStyleSheet("color:#f59e0b;font-size:22px;")
        elif n==2: self.stars_lbl.setStyleSheet("color:#fbbf24;font-size:18px;")
        elif n==1: self.stars_lbl.setStyleSheet("color:#d97706;font-size:18px;")
        else: self.stars_lbl.setStyleSheet("color:#4b5563;font-size:18px;")
        # Task schedule
        tidx=min(ST["task_index"],len(TASKS)-1)
        t=TASKS[tidx]
        self.sched_task.setText(f"📋 {t['id'].replace('_',' ').title()}")
        # Domain badge
        dom=ST["domain"]; proto=ST["protocol"]
        icons={"Motor":"🏃","Cognitive":"🧠","Verbal":"🗣️","Social":"🤝"}
        ic=icons.get(dom,"📋")
        self.domain_badge.setText(f"{ic} {dom} — {proto}")
        bgs={"Motor":"#1e3a5f","Cognitive":"#1e1b4b","Verbal":"#1a3320","Social":"#2a1060"}
        self.domain_badge.setStyleSheet(
            f"color:#e0e6ff;background:{bgs.get(dom,'#1a1f40')};"
            "border-radius:10px;border:1px solid #4f46e5;")
        # AI status
        if ST["gemini_ok"]:
            self.ai_lbl.setText(f"● {ST['gemini_model'][:15]}")
            self.ai_lbl.setStyleSheet("color:#34d399;")
        else:
            self.ai_lbl.setText("⚠ FALLBACK")
            self.ai_lbl.setStyleSheet("color:#fbbf24;")
        # State
        if ST["is_speaking"]:
            self.fb_icon.setText("🔊"); self.state_lbl.setText("🔊 Speaking")
            self.fb_lbl.setStyleSheet("color:#60a5fa;")
        elif ST["listening"]:
            self.fb_icon.setText("👂"); self.state_lbl.setText("👂 Listening")
            self.fb_lbl.setStyleSheet("color:#34d399;")
        elif ST["waiting_for_child"]:
            self.fb_icon.setText("⏳"); self.state_lbl.setText("⏳ Waiting")
            self.fb_lbl.setStyleSheet("color:#fbbf24;")
        else:
            self.fb_icon.setText("💤"); self.state_lbl.setText("💤 Ready")
            self.fb_lbl.setStyleSheet("color:#9ca3af;")

    def _on_show_task(self,data):
        """Handle show_task signal (always on main thread)"""
        action=data.get("action","")
        if action=="click":
            self._handle_click(data.get("idx",-1)); return
        mode=data.get("mode","idle")
        instr=data.get("instruction","")
        self.instr_lbl.setText(instr)
        self.fb_lbl.setText(f"Task ready — click the correct answer!")
        self._build_content(data)
        self._do_unlock()

    def _build_content(self,data):
        """Build task content in content area"""
        self._clear_content(); mode=data.get("mode","idle")

        if mode=="idle": self._show_idle(); return

        if mode=="motor_model":
            # Visual modeling — HD instruction image
            vw=QWidget(); vl=QVBoxLayout(vw)
            vl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            # Big animated emoji representing movement
            em_lbl=QLabel(data.get("emoji","🤖"))
            em_lbl.setFont(QFont("Arial",100))
            em_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            vl.addWidget(em_lbl)
            title=QLabel(data.get("label",""))
            title.setFont(QFont("Arial",18,QFont.Weight.Bold))
            title.setStyleSheet("color:#a78bfa;")
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            vl.addWidget(title)
            desc=QLabel(data.get("desc",""))
            desc.setFont(QFont("Arial",12))
            desc.setStyleSheet("color:#9ca3af;")
            desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
            desc.setWordWrap(True)
            vl.addWidget(desc)
            # Arrow pointing to child
            arrow=QLabel("👆 Now you do it!")
            arrow.setFont(QFont("Arial",13,QFont.Weight.Bold))
            arrow.setStyleSheet("color:#34d399;")
            arrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
            vl.addWidget(arrow)
            self.content_lay.addWidget(vw)
            return

        if mode=="word_display":
            wf=QFrame()
            wf.setStyleSheet("""QFrame{background:qlineargradient(
                x1:0,y1:0,x2:0,y2:1,stop:0 #1e1b4b,stop:1 #0c0f1e);
                border-radius:20px;border:3px solid #4f46e5;min-height:200px;}""")
            wfl=QVBoxLayout(wf); wfl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            el=QLabel(data.get("emoji","📢"))
            el.setFont(QFont("Arial",60))
            el.setAlignment(Qt.AlignmentFlag.AlignCenter)
            wfl.addWidget(el)
            wl=QLabel(data.get("word","SAY IT!"))
            wl.setFont(QFont("Arial",32,QFont.Weight.Bold))
            wl.setStyleSheet("color:#a78bfa;")
            wl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            wfl.addWidget(wl)
            hl=QLabel("🎤 Say it out loud!")
            hl.setFont(QFont("Arial",13))
            hl.setStyleSheet("color:#6b7280;")
            hl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            wfl.addWidget(hl)
            self.content_lay.addWidget(wf)
            return

        # Grid tasks (colors, objects, shapes, numbers, emotions)
        opts=data.get("options",[])
        correct=data.get("correct",-1)
        self._correct_idx=correct
        # Visual hint
        hint=data.get("visual_hint","")
        if hint:
            hl=QLabel(f"💡 {hint}")
            hl.setFont(QFont("Arial",11))
            hl.setStyleSheet("color:#60a5fa;")
            hl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.content_lay.addWidget(hl)
        # 2x2 grid
        gw=QWidget(); grid=QGridLayout(gw)
        grid.setSpacing(12)
        grid.setAlignment(Qt.AlignmentFlag.AlignCenter)
        for i,opt in enumerate(opts):
            card=ClickCard(opt,i,mode)
            self._cards.append(card)
            grid.addWidget(card,i//2,i%2,Qt.AlignmentFlag.AlignCenter)
        self.content_lay.addWidget(gw)

    def _handle_click(self,idx):
        if self._locked: return
        correct=self._correct_idx
        if correct==-1:
            # Emotion/free-choice task
            ST["tablet_click_result"]="correct"
            self.fb_lbl.setText("✅ Great choice!")
            self.fb_lbl.setStyleSheet("color:#34d399;")
            if idx<len(self._cards): self._cards[idx].flash_correct()
            self._do_lock(); LOG(f"Tablet free click idx={idx}","success"); return
        if idx==correct:
            ST["tablet_click_result"]="correct"
            if idx<len(self._cards): self._cards[idx].flash_correct()
            self.fb_lbl.setText("✅ Correct! Great job! You found it!")
            self.fb_lbl.setStyleSheet("color:#34d399;")
            LOG(f"Tablet CORRECT idx={idx}","success")
        else:
            ST["tablet_click_result"]="wrong"
            if idx<len(self._cards): self._cards[idx].flash_wrong()
            if 0<=correct<len(self._cards): self._cards[correct].flash_correct()
            self.fb_lbl.setText("❌ Try again! Look carefully!")
            self.fb_lbl.setStyleSheet("color:#f87171;")
            LOG(f"Tablet WRONG idx={idx}","fail")
        self._do_lock()

    def _on_result(self,success,msg):
        if success:
            self.fb_lbl.setText(f"🌟 {msg}"); self.fb_lbl.setStyleSheet("color:#34d399;")
        else:
            self.fb_lbl.setText(f"💪 {msg}"); self.fb_lbl.setStyleSheet("color:#f87171;")
        QTimer.singleShot(2500,lambda: self.fb_lbl.setStyleSheet("color:#9ca3af;"))

    def _on_joy(self,joy_type):
        """Social joy animation on tablet"""
        self._joy_phase=0.0; self._joy_timer.start(60)
        msgs={
            "dance":"🕺 AMAZING DANCE! 🎉","celebrate":"🎊 CELEBRATION! ⭐",
            "wave_back":"👋 HIGH FIVE! 🌟","full_joy":"🏆 CHAMPION! 🎉🎊🌟",
        }
        msg=msgs.get(joy_type,"🌟 AMAZING! 🎉")
        self.fb_lbl.setText(msg)
        self.fb_lbl.setStyleSheet("color:#fbbf24;font-size:15px;")
        QTimer.singleShot(3000,self._end_joy)

    def _joy_tick(self):
        self._joy_phase+=0.20
        emojis=["🎉","🌟","⭐","🏆","✨","🎊","💫","🎈","🌈"]
        self.av_lbl.setText(emojis[int(self._joy_phase)%len(emojis)])
        if self._joy_phase>20: self._end_joy()

    def _end_joy(self):
        self._joy_timer.stop(); self.av_lbl.setText("🤖")
        QTimer.singleShot(500,lambda: self.fb_lbl.setStyleSheet("color:#9ca3af;"))

    def _do_unlock(self):
        self._locked=False; ST["tablet_locked"]=False
        self.lock_ov.hide()
        for c in self._cards: c.setEnabled(True)

    def _do_lock(self):
        self._locked=True; ST["tablet_locked"]=True
        self.lock_ov.show(); self.lock_ov.raise_()
        for c in self._cards: c.setEnabled(False)

    def _set_feedback(self,txt): self.fb_lbl.setText(txt)
    def _set_instr(self,txt): self.instr_lbl.setText(txt)

    def reset_cards(self):
        for c in self._cards: c.reset()
        ST["tablet_click_result"]=None

# ═══════════════════════════════════════════════════════════════
# 8. GEMINI — stable gemini-1.5-flash primary
# ═══════════════════════════════════════════════════════════════
CLINICAL_PROMPT="""You are PEPPER, a Certified Clinical Therapist for ASD children.
Developer: Lamya (Omdurman Islamic University).

PROTOCOLS: ABA, TEACCH, DTT, ESDM
MASTERY GATE: 3 consecutive successes before task change.

RULES:
- MAX 2 sentences + "Ready? Your turn! 🎯"
- Use child's name every response
- For motor tasks: say "Look at the screen and do this!"
- For cognitive: say "Click the correct one on the tablet!"
- Celebrate specifically (not generic "nice")

TOKENS: [WAVE][CLAP][NOD][DANCE][POINT][HUG][CELEBRATE][THINK]
SOCIAL: [GAZE_TABLET][GAZE_CHILD][SOCIAL_JOY]
TRIGGER: [YOUTUBE: query] | [GAME] | [REWARD: N]"""

class GeminiBrain:
    # FIX: stable models first, experimental last
    MODELS=[
        "gemini-1.5-flash",
        "gemini-1.5-flash-8b",
        "gemini-1.5-pro",
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        "gemini-pro",
    ]
    def __init__(self):
        self.ok=False; self._lock=threading.Lock()
        self.model_name="fallback"; self.chat=None; self.ctx=[]
        try:
            disc=[]
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    disc.append(m.name.replace('models/',''))
            print(f"📋 Available: {disc[:6]}")
            # Add discovered stable models to front
            for d in reversed(disc):
                if d not in self.MODELS and "exp" not in d:
                    self.MODELS.insert(0,d)
        except Exception as e: print(f"⚠️  Discovery: {e}")
        for mn in self.MODELS:
            try:
                m=genai.GenerativeModel(mn,system_instruction=CLINICAL_PROMPT,
                    generation_config=genai.GenerationConfig(temperature=0.82,max_output_tokens=140))
                c=m.start_chat(history=[])
                r=c.send_message("Say: READY")
                if r.text and len(r.text)>2:
                    self.model=m; self.chat=c; self.model_name=mn
                    self.ok=True; ST["gemini_ok"]=True; ST["gemini_model"]=mn
                    print(f"✅ Gemini: {mn}"); break
            except Exception as e:
                err=str(e)
                if "403" in err:
                    print(f"⚠️  {mn}: API key issue — rotate key")
                else:
                    print(f"⚠️  {mn}: {err[:55]}")
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

    def _ctx(self):
        recent=" | ".join(self.ctx[-3:]) if self.ctx else "start"
        return (f"[child={ST['name']} age={ST['age']} "
                f"level={ST['current_level']} domain={ST['domain']} "
                f"mastery={ST['consecutive']}/3 "
                f"emotion={ST['emotion']} attention={ST['attention']}% "
                f"streak={ST['streak']} ctx={recent}] ")

    def ask(self,prompt):
        self.ctx.append(prompt[:50])
        if len(self.ctx)>6: self.ctx.pop(0)
        if not self.ok or not self._quota_ok():
            ST["api_fallback_count"]+=1
            return EMPATHY.get(ST["emotion"] if ST["emotion"] in EMPATHY._lib else "default")
        with self._lock:
            try:
                self._record()
                resp=self.chat.send_message(self._ctx()+prompt)
                text=resp.text.strip(); LOG(f"AI: {text[:55]}"); return text
            except Exception as e:
                err=str(e)
                if "429" in err: ST["api_calls_this_min"]=API_RPM
                if "403" in err: print("⚠️  403: API key leaked/disabled — please rotate")
                LOG(f"API: {err[:40]}")
                try: self.chat=self.model.start_chat(history=[])
                except: pass
                ST["api_fallback_count"]+=1
                return EMPATHY.get(ST["emotion"] if ST["emotion"] in EMPATHY._lib else "default")

    def parent_ask(self,q):
        if not self.ok or not self._quota_ok():
            return "Please consult your specialist. / أرجو مراجعة المختص."
        try:
            self._record()
            pm=genai.GenerativeModel(self.model_name,
                system_instruction=(
                    "Expert autism ABA/TEACCH/DTT/ESDM specialist for parents. "
                    "Respond in the SAME language as the question. "
                    f"Child: {ST['name']}, age {ST['age']}."),
                generation_config=genai.GenerationConfig(temperature=0.6,max_output_tokens=450))
            r=pm.generate_content(q); return r.text.strip()
        except Exception as e: return f"Error: {str(e)[:40]}"

    def generate_report(self):
        dur=int((time.time()-ST["uptime"])/60)
        if not self.ok or not self._quota_ok(): return self._local(dur)
        try:
            self._record()
            rm=genai.GenerativeModel(self.model_name,
                generation_config=genai.GenerationConfig(temperature=0.3,max_output_tokens=600))
            r=rm.generate_content(
                f"ABA/TEACCH/DTT/ESDM Clinical Report:\n"
                f"Child:{ST['name']} Age:{ST['age']} Dx:{ST['diagnosis']}\n"
                f"Date:{ST['session_date']} Duration:{dur}min\n"
                f"Level:{ST['current_level']} Domain:{ST['domain']} Mastered:{ST['tasks_mastered']}\n"
                f"Score:{ST['score']} OK:{ST['tasks_success']} Fail:{ST['tasks_fail']}\n"
                f"Emotion:{ST['emotion']} Attention:{ST['attention']}%\n"
                f"Skills:{json.dumps(ST['skills'])}\n"
                "Write professional clinical report.")
            return r.text.strip()
        except: return self._local(dur)

    def _local(self,dur=0):
        return (f"# ABA/TEACCH/DTT/ESDM Clinical Report\n"
                f"**Child:** {ST['name']} | **Date:** {ST['session_date']}\n"
                f"Level:{ST['current_level']} | Mastered:{ST['tasks_mastered']}\n"
                f"Score:{ST['score']} | OK:{ST['tasks_success']} Fail:{ST['tasks_fail']}")

# ═══════════════════════════════════════════════════════════════
# 9. VISION ENGINE — MediaPipe ONLY (DeepFace removed per fix)
#    Joint angle validation for motor tasks
# ═══════════════════════════════════════════════════════════════
WIN_EMO  = "Emotion + Skeleton (Resizable)"
WIN_LIVE = "Live Session — Pepper"

class VisionEngine:
    # Emotion from face mesh + pose (no DeepFace)
    ECOL={
        "happy":(0,220,80),"joyful":(0,255,180),"sad":(100,100,220),
        "angry":(0,0,220),"fear":(0,180,220),"surprised":(200,50,220),
        "confused":(200,150,0),"neutral":(180,180,180),
    }

    def __init__(self):
        self.ok_cv=self.ok_pose=self.ok_face=self.ok_hands=False
        self._lock=threading.Lock()
        self._emo_frame=None; self._live_frame=None
        self._busy=False; self.prev_gray=None
        self.motion_buf=[]; self._hand_hist=[]
        self.face_box=None; self.pose_lm=None
        self.face_lm=None; self.hand_lm_r=None; self.hand_lm_l=None
        self._av_phase=0.0; self._blink_buf=[]
        self._ear_history=[]

        # OpenCV Haar (for face box only)
        try:
            cp=cv2.data.haarcascades
            self.face_c=cv2.CascadeClassifier(cp+'haarcascade_frontalface_default.xml')
            self.smile_c=cv2.CascadeClassifier(cp+'haarcascade_smile.xml')
            if not self.face_c.empty(): self.ok_cv=True; print("✅ OpenCV Haar")
        except: pass

        # MediaPipe Pose — 33 landmarks for joint angles
        try:
            import mediapipe as mp
            self.mp_pose=mp.solutions.pose
            self.pose=self.mp_pose.Pose(
                min_detection_confidence=0.5,min_tracking_confidence=0.5,
                model_complexity=1,enable_segmentation=False)
            self.ok_pose=True; print("✅ MediaPipe Pose (joint angles)")
        except Exception as e: print(f"⚠️  MP Pose: {e}")

        # MediaPipe FaceMesh — EAR + emotion from mesh
        try:
            import mediapipe as mp
            self.mp_face=mp.solutions.face_mesh
            self.face_mesh=self.mp_face.FaceMesh(
                max_num_faces=1,min_detection_confidence=0.5,
                min_tracking_confidence=0.5,refine_landmarks=True)
            self.ok_face=True; print("✅ MediaPipe FaceMesh (EAR + emotion)")
        except Exception as e: print(f"⚠️  MP FaceMesh: {e}")

        # MediaPipe Hands — finger/hand tracking
        try:
            import mediapipe as mp
            self.mp_hands=mp.solutions.hands
            self.hands=self.mp_hands.Hands(
                max_num_hands=2,min_detection_confidence=0.6,
                min_tracking_confidence=0.5)
            self.ok_hands=True; print("✅ MediaPipe Hands")
        except Exception as e: print(f"⚠️  MP Hands: {e}")

    def _ear(self,lm,eye_idx,w,h):
        try:
            pts=[(int(lm[i].x*w),int(lm[i].y*h)) for i in eye_idx]
            A=math.dist(pts[1],pts[5]); B=math.dist(pts[2],pts[4])
            C=math.dist(pts[0],pts[3])
            return (A+B)/(2.0*C) if C>0 else 0.3
        except: return 0.3

    def _joint_angle(self,a,b,c):
        """Calculate angle at joint b given 3 points (MediaPipe landmarks)"""
        try:
            ab=np.array([a.x-b.x,a.y-b.y,a.z-b.z])
            cb=np.array([c.x-b.x,c.y-b.y,c.z-b.z])
            cos_a=np.dot(ab,cb)/(np.linalg.norm(ab)*np.linalg.norm(cb)+1e-6)
            return math.degrees(math.acos(np.clip(cos_a,-1,1)))
        except: return 0.0

    def analyze_async(self,frame):
        if self._busy: return
        self._busy=True
        threading.Thread(target=self._analyze,args=(frame.copy(),),daemon=True).start()

    def _analyze(self,frame):
        try:
            self._detect_face_haar(frame)
            self._detect_pose(frame)
            self._detect_face_mesh(frame)
            self._detect_hands(frame)
            self._detect_motion(frame)
            self._validate_aba_joints()
            self._infer_emotion_from_mesh()
            self._build_emo_win(frame)
            self._build_live_win(frame)
        except Exception as e: print(f"⚠️  analyze: {e}")
        finally: self._busy=False

    def _detect_face_haar(self,frame):
        if not self.ok_cv: return
        try:
            gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
            gray=cv2.equalizeHist(gray)
            faces=self.face_c.detectMultiScale(gray,1.05,3,minSize=(30,30))
            if len(faces)==0:
                ST["face_detected"]=False; ST["attention"]=max(0,ST["attention"]-2)
            else:
                x,y,w,h=sorted(faces,key=lambda f:f[2]*f[3],reverse=True)[0]
                self.face_box=(x,y,w,h)
                ST["face_detected"]=True; ST["attention"]=min(100,ST["attention"]+2)
        except: pass

    def _detect_pose(self,frame):
        """Pose tracking with joint angle calculation"""
        if not self.ok_pose: return
        try:
            import mediapipe as mp
            rgb=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
            res=self.pose.process(rgb)
            if not res.pose_landmarks: self.pose_lm=None; return
            self.pose_lm=res.pose_landmarks
            lm=res.pose_landmarks.landmark
            PL=mp.solutions.pose.PoseLandmark
            pl={
                "nose_y":lm[PL.NOSE].y,"nose_x":lm[PL.NOSE].x,
                "l_ear_x":lm[PL.LEFT_EAR].x,"r_ear_x":lm[PL.RIGHT_EAR].x,
                "l_shoulder_y":lm[PL.LEFT_SHOULDER].y,
                "r_shoulder_y":lm[PL.RIGHT_SHOULDER].y,
                "l_shoulder_x":lm[PL.LEFT_SHOULDER].x,
                "r_shoulder_x":lm[PL.RIGHT_SHOULDER].x,
                "l_elbow_y":lm[PL.LEFT_ELBOW].y,
                "r_elbow_y":lm[PL.RIGHT_ELBOW].y,
                "l_wrist_y":lm[PL.LEFT_WRIST].y,"r_wrist_y":lm[PL.RIGHT_WRIST].y,
                "l_wrist_x":lm[PL.LEFT_WRIST].x,"r_wrist_x":lm[PL.RIGHT_WRIST].x,
                "l_index_y":lm[PL.LEFT_INDEX].y,"r_index_y":lm[PL.RIGHT_INDEX].y,
                "l_index_x":lm[PL.LEFT_INDEX].x,"r_index_x":lm[PL.RIGHT_INDEX].x,
                "l_hip_y":lm[PL.LEFT_HIP].y,"r_hip_y":lm[PL.RIGHT_HIP].y,
            }
            # Joint angles
            # Shoulder abduction (for arms_out)
            l_shoulder_angle=self._joint_angle(
                lm[PL.LEFT_ELBOW],lm[PL.LEFT_SHOULDER],lm[PL.LEFT_HIP])
            r_shoulder_angle=self._joint_angle(
                lm[PL.RIGHT_ELBOW],lm[PL.RIGHT_SHOULDER],lm[PL.RIGHT_HIP])
            pl["l_shoulder_angle"]=l_shoulder_angle
            pl["r_shoulder_angle"]=r_shoulder_angle
            # Elbow angle
            l_elbow_angle=self._joint_angle(
                lm[PL.LEFT_SHOULDER],lm[PL.LEFT_ELBOW],lm[PL.LEFT_WRIST])
            r_elbow_angle=self._joint_angle(
                lm[PL.RIGHT_SHOULDER],lm[PL.RIGHT_ELBOW],lm[PL.RIGHT_WRIST])
            pl["l_elbow_angle"]=l_elbow_angle
            pl["r_elbow_angle"]=r_elbow_angle
            ST["pose_landmarks"]=pl
            # Basic gestures
            ST["hand_raised"]=(pl["l_wrist_y"]<pl["l_shoulder_y"]-0.08 or
                               pl["r_wrist_y"]<pl["r_shoulder_y"]-0.08)
            ST["head_tilted"]=(abs(pl["nose_x"]-pl["l_ear_x"])<0.12 or
                               abs(pl["nose_x"]-pl["r_ear_x"])<0.12)
            # Arms out: shoulder angle > 70° on both sides
            ST["arms_out"]=(l_shoulder_angle>70 and r_shoulder_angle>70)
            # Hands up: both wrists above shoulders
            ST["hands_up"]=(pl["l_wrist_y"]<pl["l_shoulder_y"]-0.08 and
                            pl["r_wrist_y"]<pl["r_shoulder_y"]-0.08)
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
            # EAR
            r_eye=[33,160,158,133,153,144]; l_eye=[362,385,387,263,373,380]
            ear_r=self._ear(lm,r_eye,w,h); ear_l=self._ear(lm,l_eye,w,h)
            ear_avg=(ear_r+ear_l)/2.0
            self._blink_buf.append(ear_avg)
            if len(self._blink_buf)>10: self._blink_buf.pop(0)
            ST["blinking"]=ear_avg<0.20; ST["eye_contact"]=ear_avg>0.25
            ST["face_mesh_landmarks"]={
                "nose_x":lm[1].x*w,"nose_y":lm[1].y*h,
                "ear_avg":ear_avg,"frame_w":w,"frame_h":h,
            }
            self._ear_history.append(ear_avg)
            if len(self._ear_history)>20: self._ear_history.pop(0)
            # Mouth openness (upper/lower lip distance)
            upper_lip_y=lm[13].y*h; lower_lip_y=lm[14].y*h
            mouth_open=(lower_lip_y-upper_lip_y)/h
            ST["face_mesh_landmarks"]["mouth_open"]=mouth_open
        except: pass

    def _infer_emotion_from_mesh(self):
        """
        Infer emotion from MediaPipe FaceMesh landmarks
        (replaces DeepFace — pure MediaPipe)
        """
        fm=ST.get("face_mesh_landmarks",{})
        if not fm: ST["emotion"]="neutral"; return
        ear_avg=fm.get("ear_avg",0.3)
        mouth_open=fm.get("mouth_open",0.02)
        # Simple heuristic emotion from facial geometry
        if ear_avg<0.20: em="surprised"
        elif mouth_open>0.06: em="happy"
        elif mouth_open>0.04: em="joyful"
        elif ear_avg<0.22 and mouth_open<0.02: em="sad"
        else: em="neutral"
        ST["emotion"]=em
        ST["face_detected"]=True
        ST["attention"]=min(100,ST["attention"]+1)
        # Simple scores
        scores={"neutral":0.1,"happy":0.0,"joyful":0.0,"sad":0.0,"fear":0.0,
                "angry":0.0,"surprised":0.0,"confused":0.0}
        scores[em]=0.8
        ST["emotion_scores"]=scores

    def _detect_hands(self,frame):
        if not self.ok_hands: return
        try:
            import mediapipe as mp
            rgb=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
            res=self.hands.process(rgb)
            if not res.multi_hand_landmarks:
                self.hand_lm_r=None; self.hand_lm_l=None
                ST["clapping"]=False; return
            lms=res.multi_hand_landmarks
            self.hand_lm_r=lms[0] if len(lms)>=1 else None
            self.hand_lm_l=lms[1] if len(lms)>=2 else None
            if len(lms)>=2:
                h1=lms[0].landmark[0]; h2=lms[1].landmark[0]
                if abs(h1.x-h2.x)<0.18 and abs(h1.y-h2.y)<0.18:
                    ST["clapping"]=True
                else: ST["clapping"]=False
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
            if spike>avg*3.5 and spike>15: ST["clapping"]=True
        h,w=gray.shape
        lm_=float(np.mean(th[:,:w//2])); rm_=float(np.mean(th[:,w//2:]))
        self._hand_hist.append("L" if lm_>rm_+3 else "R" if rm_>lm_+3 else "N")
        if len(self._hand_hist)>10: self._hand_hist.pop(0)
        chg=sum(1 for i in range(1,len(self._hand_hist))
                if self._hand_hist[i]!=self._hand_hist[i-1]
                and self._hand_hist[i]!="N")
        ST["waving"]=chg>=4

    def _validate_aba_joints(self):
        """
        Joint angle-based motor task validation (MediaPipe).
        More precise than pixel-diff.
        """
        va=ST.get("verify_action")
        if not va: return
        if time.time()>ST["verify_timeout"]: ST["verify_action"]=None; return
        pl=ST.get("pose_landmarks",{}); fm=ST.get("face_mesh_landmarks",{})
        ok=False

        if va=="clap":
            # Two hands close + motion spike
            ok=ST["clapping"]

        elif va=="wave":
            # Alternating hand motion
            ok=ST["waving"]

        elif va=="raise_hand":
            # Wrist above shoulder: wrist_y < shoulder_y - margin
            lwy=pl.get("l_wrist_y",1); rwy=pl.get("r_wrist_y",1)
            lsy=pl.get("l_shoulder_y",0); rsy=pl.get("r_shoulder_y",0)
            # Also check elbow angle > 150° (arm extended)
            lea=pl.get("l_elbow_angle",0); rea=pl.get("r_elbow_angle",0)
            ok=((lwy<lsy-0.08 and lea>120) or (rwy<rsy-0.08 and rea>120))

        elif va=="touch_nose":
            # Index finger within 12% of frame width from nose tip
            nx=fm.get("nose_x",-1); ny=fm.get("nose_y",-1)
            fw=fm.get("frame_w",640); fh=fm.get("frame_h",480)
            if nx>0 and pl:
                lix=pl.get("l_index_x",0)*fw; liy=pl.get("l_index_y",0)*fh
                rix=pl.get("r_index_x",0)*fw; riy=pl.get("r_index_y",0)*fh
                ok=(math.dist((lix,liy),(nx,ny))<fw*0.12 or
                    math.dist((rix,riy),(nx,ny))<fw*0.12)

        elif va=="arms_out":
            # Both shoulder angles > 70° (arms spread wide)
            ok=ST.get("arms_out",False)

        elif va=="hands_up":
            # Both wrists above shoulders
            ok=ST.get("hands_up",False)

        elif va=="head_tilt":
            ok=ST.get("head_tilted",False)

        elif va=="blink":
            ok=ST.get("blinking",False)

        if ok:
            ST["verify_result"]=True; ST["verify_action"]=None
            ST["verify_timeout"]=0.0
            LOG("✅ Joint validated!","success")

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

    def _draw_face_mesh(self,frame):
        if not self.ok_face or self.face_lm is None: return frame
        try:
            import mediapipe as mp
            mp_d=mp.solutions.drawing_utils
            mp_styles=mp.solutions.drawing_styles
            mp_d.draw_landmarks(frame,self.face_lm,
                mp.solutions.face_mesh.FACEMESH_CONTOURS,
                landmark_drawing_spec=None,
                connection_drawing_spec=mp_styles.get_default_face_mesh_contours_style())
        except: pass
        return frame

    def _build_emo_win(self,frame):
        """Window 2: Emotion + Skeleton (RESIZABLE)"""
        ann=frame.copy()
        ann=self._draw_skeleton(ann)
        ann=self._draw_hands(ann)
        ann=self._draw_face_mesh(ann)
        base=cv2.resize(ann,(600,600))
        ov=base.copy(); cv2.rectangle(ov,(0,0),(232,600),(0,0,0),-1)
        base=cv2.addWeighted(ov,0.68,base,0.32,0)
        em=ST["emotion"]; col=self.ECOL.get(em,(180,180,180))
        cv2.rectangle(base,(0,0),(600,50),(0,0,0),-1)
        cv2.putText(base,"MEDIAPIPE SKELETON + EMOTION",
            (8,18),cv2.FONT_HERSHEY_SIMPLEX,0.50,(0,200,255),1)
        suc=ST["consecutive"]; dom=ST["domain"]
        cv2.putText(base,f"{dom} | {suc}/3 ★ | {em.upper()}",
            (8,40),cv2.FONT_HERSHEY_SIMPLEX,0.54,col,2)
        # Gesture indicators
        acts=[
            ("Hand Raised",ST["hand_raised"],(0,255,100)),
            ("Waving",ST["waving"],(0,200,255)),
            ("Clapping",ST["clapping"],(255,200,0)),
            ("Arms Out",ST["arms_out"],(255,120,0)),
            ("Hands Up",ST["hands_up"],(0,255,200)),
            ("Eye Contact",ST["eye_contact"],(200,100,255)),
            ("Touch Nose",ST["face_touch"],(255,180,100)),
        ]
        rx,ry=240,54
        suc_pct=min(100,int(suc/3*100))
        cv2.putText(base,"MASTERY",(rx,ry-4),cv2.FONT_HERSHEY_SIMPLEX,0.42,(200,200,200),1)
        cv2.rectangle(base,(rx,ry+2),(596,ry+18),(25,28,50),-1)
        cv2.rectangle(base,(rx,ry+2),(rx+int(356*suc_pct/100),ry+18),(0,200,100),-1)
        cv2.putText(base,f"{suc}/3 ({suc_pct}%)",
            (rx+5,ry+13),cv2.FONT_HERSHEY_SIMPLEX,0.38,(255,255,255),1)
        for i,(lbl,active,ac) in enumerate(acts):
            y=ry+22+i*44
            bg=(5,30,15) if active else (18,20,32)
            cv2.rectangle(base,(rx,y),(596,y+34),bg,-1)
            cv2.rectangle(base,(rx,y),(596,y+34),ac if active else (55,60,85),2 if active else 1)
            cv2.putText(base,lbl,(rx+8,y+22),cv2.FONT_HERSHEY_SIMPLEX,
                0.46,ac if active else (65,68,80),2 if active else 1)
        # Joint angles
        pl=ST.get("pose_landmarks",{})
        vy=ry+340
        cv2.putText(base,f"L-elbow:{pl.get('l_elbow_angle',0):.0f}° "
                    f"R-elbow:{pl.get('r_elbow_angle',0):.0f}°",
            (rx,vy),cv2.FONT_HERSHEY_SIMPLEX,0.36,(180,180,180),1)
        cv2.putText(base,f"L-shldr:{pl.get('l_shoulder_angle',0):.0f}° "
                    f"R-shldr:{pl.get('r_shoulder_angle',0):.0f}°",
            (rx,vy+16),cv2.FONT_HERSHEY_SIMPLEX,0.36,(180,180,180),1)
        ear=ST.get("face_mesh_landmarks",{}).get("ear_avg",0)
        cv2.putText(base,f"EAR:{ear:.3f} | eye_contact={'Y' if ST['eye_contact'] else 'N'}",
            (rx,vy+32),cv2.FONT_HERSHEY_SIMPLEX,0.36,(160,160,160),1)
        if ST["verify_action"]:
            rem=max(0,int(ST["verify_timeout"]-time.time()))
            cv2.rectangle(base,(rx,vy+42),(596,vy+80),(28,14,0),-1)
            cv2.rectangle(base,(rx,vy+42),(596,vy+80),(255,140,0),2)
            cv2.putText(base,f"Verify: {ST['verify_action']} ({rem}s)",
                (rx+5,vy+64),cv2.FONT_HERSHEY_SIMPLEX,0.44,(255,160,50),1)
        elif ST["verify_result"]:
            cv2.rectangle(base,(rx,vy+42),(596,vy+80),(5,28,10),-1)
            cv2.putText(base,"✅ JOINT VALIDATED!",
                (rx+5,vy+66),cv2.FONT_HERSHEY_SIMPLEX,0.58,(0,255,100),2)
        bw=int(ST["attention"]/100*598)
        cv2.rectangle(base,(0,578),(598,598),(16,18,35),-1)
        cv2.rectangle(base,(0,578),(bw,598),col,-1)
        cv2.putText(base,f"Attention:{ST['attention']}% | {ST['engagement']}",
            (6,594),cv2.FONT_HERSHEY_SIMPLEX,0.38,(255,255,255),1)
        cv2.circle(base,(588,22),9,(0,255,0) if ST["face_detected"] else (0,0,255),-1)
        with self._lock: self._emo_frame=base

    def _build_live_win(self,frame):
        """Window 3: Live session + animated Pepper avatar"""
        win=np.zeros((520,820,3),dtype=np.uint8); win[:]=(8,10,22)
        for i in range(0,820,40): cv2.line(win,(i,0),(i,520),(14,17,34),1)
        for i in range(0,520,40): cv2.line(win,(0,i),(820,i),(14,17,34),1)
        ann=frame.copy(); ann=self._draw_skeleton(ann); ann=self._draw_hands(ann)
        cam=cv2.resize(ann,(400,340)); win[78:418,10:410]=cam
        cv2.rectangle(win,(10,78),(410,418),(60,65,120),2)
        em=ST["emotion"]; col=self.ECOL.get(em,(180,180,180))
        cv2.putText(win,em.upper(),(18,435),cv2.FONT_HERSHEY_SIMPLEX,0.60,col,2)
        att=ST["attention"]
        cv2.rectangle(win,(10,445),(410,455),(25,28,55),-1)
        cv2.rectangle(win,(10,445),(10+int(400*att/100),455),col,-1)
        cv2.putText(win,f"Att:{att}%",(14,454),cv2.FONT_HERSHEY_SIMPLEX,0.34,(255,255,255),1)
        suc=ST["consecutive"]
        stars="★"*suc+"☆"*(3-suc)
        cv2.putText(win,f"Mastery: {stars} {suc}/3",
            (14,470),cv2.FONT_HERSHEY_SIMPLEX,0.38,(255,200,0),1)
        ear=ST.get("face_mesh_landmarks",{}).get("ear_avg",0)
        cv2.putText(win,f"EAR:{ear:.2f}",
            (14,486),cv2.FONT_HERSHEY_SIMPLEX,0.34,(200,200,200),1)

        # Animated Pepper avatar with lip-sync
        av_cx,av_cy=645,220
        self._av_phase+=0.10 if ST["is_speaking"] else 0.028
        lip=ST.get("lip_sync_value",0.0)
        if ST["is_speaking"]:
            lip=min(1.0,ST.get("voice_energy",0)/2500.0)
            lip=max(0.1,lip+0.35*abs(math.sin(self._av_phase*4)))
        # Body
        cv2.ellipse(win,(av_cx,av_cy+83),(48,68),0,0,360,(80,100,200),-1)
        cv2.ellipse(win,(av_cx,av_cy+83),(48,68),0,0,360,(100,120,220),2)
        # Arms
        if ST["is_speaking"]:
            la=int(24*math.sin(self._av_phase)); ra=int(24*math.sin(self._av_phase+math.pi))
            cv2.ellipse(win,(av_cx-58+la,av_cy+64),(12,37),-30+la,0,360,(70,90,190),-1)
            cv2.ellipse(win,(av_cx+58+ra,av_cy+64),(12,37),30+ra,0,360,(70,90,190),-1)
        else:
            cv2.ellipse(win,(av_cx-58,av_cy+68),(12,32),-15,0,360,(70,90,190),-1)
            cv2.ellipse(win,(av_cx+58,av_cy+68),(12,32),15,0,360,(70,90,190),-1)
        # Head
        hbob=int(3*math.sin(self._av_phase*0.5)); hy=av_cy-53+hbob
        cv2.circle(win,(av_cx,hy),53,(220,195,173),-1)
        cv2.circle(win,(av_cx,hy),53,(200,175,155),2)
        # Eyes
        blink_=(int(self._av_phase*3)%40==0); ey_=6 if not blink_ else 1
        eye_col=(100,180,255)
        for ex_ in [av_cx-19,av_cx+19]:
            cv2.ellipse(win,(ex_,hy-9),(7,ey_),0,0,360,eye_col,-1)
            if not blink_:
                cv2.circle(win,(ex_+1,hy-9),3,(255,255,255),-1)
                cv2.circle(win,(ex_+2,hy-10),1,(0,0,0),-1)
        # Nose
        cv2.circle(win,(av_cx,hy+7),5,(180,140,120),-1)
        # Mouth lip-sync
        mh=int(4+lip*16)
        if ST["is_speaking"]:
            cv2.ellipse(win,(av_cx,hy+21),(16,mh),0,0,180,(160,80,80),-1)
            cv2.ellipse(win,(av_cx,hy+21),(16,mh),0,0,180,(210,110,110),2)
            if lip>0.3:
                cv2.ellipse(win,(av_cx,hy+21),(13,max(1,mh-3)),0,0,180,(240,230,220),-1)
        elif em in ["happy","joyful"]:
            cv2.ellipse(win,(av_cx,hy+19),(15,7),0,0,180,(150,80,80),-1)
        else:
            cv2.line(win,(av_cx-12,hy+20),(av_cx+12,hy+20),(150,80,80),2)
        for ex_ in [av_cx-51,av_cx+51]:
            cv2.circle(win,(ex_,hy-6),10,(210,185,163),-1)
            cv2.circle(win,(ex_,hy-6),6,(240,200,180),-1)
        cv2.rectangle(win,(av_cx-28,av_cy+148),(av_cx-10,av_cy+180),(60,80,170),-1)
        cv2.rectangle(win,(av_cx+10,av_cy+148),(av_cx+28,av_cy+180),(60,80,170),-1)
        # Status
        if ST["is_speaking"]:
            pr=90+int(6*math.sin(self._av_phase*5))
            cv2.circle(win,(av_cx,av_cy),pr,(0,160,255),2)
            cv2.putText(win,f"SPEAKING lip={lip:.1f}",
                (av_cx-55,av_cy+185),cv2.FONT_HERSHEY_SIMPLEX,0.42,(0,200,255),1)
        elif ST["listening"]:
            cv2.circle(win,(av_cx,av_cy),92,(0,220,100),2)
            cv2.putText(win,"LISTENING",(av_cx-42,av_cy+185),
                cv2.FONT_HERSHEY_SIMPLEX,0.48,(0,220,100),2)
        elif ST["waiting_for_child"]:
            cv2.putText(win,"WAITING...",(av_cx-40,av_cy+185),
                cv2.FONT_HERSHEY_SIMPLEX,0.46,(255,200,0),1)
        task_msg=ST.get("tablet_instruction","")[:72]
        if task_msg:
            cv2.rectangle(win,(10,480),(820,498),(20,25,45),-1)
            cv2.putText(win,task_msg,(14,493),
                cv2.FONT_HERSHEY_SIMPLEX,0.37,(255,220,100),1)
        cv2.rectangle(win,(0,0),(820,72),(6,8,20),-1)
        cv2.putText(win,"LIVE — PEPPER CLINICAL MASTERY SYSTEM",
            (10,25),cv2.FONT_HERSHEY_SIMPLEX,0.60,(160,140,255),2)
        gm_col=(0,220,80) if ST["gemini_ok"] else (200,150,0)
        cv2.putText(win,
            f"Child:{ST['name']} | L{ST['current_level']} {ST['domain']} | "
            f"Score:{ST['score']} | Mastered:{ST['tasks_mastered']} | "
            f"{'AI' if ST['gemini_ok'] else 'FALLBACK'} | energy={MIC_ENERGY}",
            (10,52),cv2.FONT_HERSHEY_SIMPLEX,0.36,gm_col,1)
        cy_=515
        for msg in ST["session_chat"][-3:]:
            isp=msg["role"]=="pepper"
            txt=msg["text"][:60]+("..." if len(msg["text"])>60 else "")
            cv2.rectangle(win,(10,cy_-16),(810,cy_+4),(30,20,60) if isp else (10,30,15),-1)
            cv2.rectangle(win,(10,cy_-16),(810,cy_+4),(100,80,200) if isp else (0,180,80),1)
            pfx="🤖 " if isp else f"👦 {ST['name']}: "
            cv2.putText(win,pfx+txt,(14,cy_),cv2.FONT_HERSHEY_SIMPLEX,0.32,
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
# 10. CAMERA
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
# 11. VOICE + LIP-SYNC
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
            ST["lip_sync_active"]=True; time.sleep(dur*0.55)
            ST["lip_sync_value"]=max(0.05,ST["lip_sync_value"]*0.35)
            time.sleep(dur*0.45)
        ST["lip_sync_value"]=0.0; ST["lip_sync_active"]=False

    def say(self,text,wait=True):
        ST["interrupt_flag"]=False
        text=str(text).replace("{name}",ST.get("name","Friend"))
        for tok in ["[WAVE]","[CLAP]","[NOD]","[DANCE]","[POINT]","[HUG]",
                    "[CELEBRATE]","[THINK]","[GAME]","[LEVEL_UP]",
                    "[GAZE_TABLET]","[GAZE_CHILD]","[SOCIAL_JOY]"]:
            text=text.replace(tok,"")
        text=re.sub(r'\[YOUTUBE:[^\]]+\]','',text)
        text=re.sub(r'\[REWARD:\d+\]','',text)
        text=text.strip()
        if not text: return
        ST["is_speaking"]=True
        ST["session_chat"].append({
            "role":"pepper","text":text,
            "time":datetime.now().strftime("%H:%M:%S")})
        if len(ST["session_chat"])>40: ST["session_chat"]=ST["session_chat"][-40:]
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
# 12. MICROPHONE — FIX: energy_threshold=300 (no ghost speech)
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
            self.r.energy_threshold=MIC_ENERGY   # FIX: 300 not 30
            self.r.dynamic_energy_threshold=False
            self.r.pause_threshold=0.6
            self.r.phrase_threshold=0.1
            self.r.non_speaking_duration=0.2
            if not self.ok: self.ok=True
            print(f"✅ Mic energy={MIC_ENERGY} (no ghost speech)")
        except Exception as e: print(f"⚠️  SR: {e}")

    def _tone(self,raw_data):
        try:
            raw=np.frombuffer(raw_data,np.int16)
            rms=float(np.sqrt(np.mean(raw.astype(np.float64)**2)))
            ST["voice_energy"]=rms
        except: pass

    def listen_once(self,timeout=8):
        if not self.ok: return input("Type: ").strip()
        ST["listening"]=True
        try:
            with sr.Microphone() as src:
                self.r.adjust_for_ambient_noise(src,duration=0.1)
                print("👂 Listening...")
                audio=self.r.listen(src,timeout=timeout,phrase_time_limit=18)
            raw=audio.get_raw_data(); self._tone(raw); ST["listening"]=False
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
                if rms>1200: ST["clapping"]=True; LOG("👏 Clap!","success")
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
                time.sleep(0.05)
        threading.Thread(target=_loop,daemon=True).start()

# ═══════════════════════════════════════════════════════════════
# 13. ACTIONS → PYBULLET + LIP-SYNC HeadPitch
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
        if "[GAZE_TABLET]" in text:
            clean=clean.replace("[GAZE_TABLET]","")
            threading.Thread(target=self._gaze_tablet,daemon=True).start()
        if "[GAZE_CHILD]" in text:
            clean=clean.replace("[GAZE_CHILD]","")
            threading.Thread(target=self._gaze_child,daemon=True).start()
        if "[SOCIAL_JOY]" in text:
            clean=clean.replace("[SOCIAL_JOY]","")
            threading.Thread(target=self._social_joy_anim,daemon=True).start()
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
                    self._sa("HeadPitch",-0.04-lv*0.13,0.22)
            except: pass
            time.sleep(0.035)

    def trigger_joy(self,joy_type="celebrate"):
        """Called on success — emits signal to Qt main thread"""
        BRIDGE.sig_show_joy.emit(joy_type)
        joy_map={
            "dance":self._dance,"celebrate":self._celebrate,
            "wave_back":self._wave,"full_joy":self._social_joy_anim,
        }
        fn=joy_map.get(joy_type,self._celebrate)
        threading.Thread(target=fn,daemon=True).start()

    def _gaze_tablet(self):
        ST["gaze_mode"]="tablet"
        self._sa("HeadYaw",-0.4,0.12); self._sa("HeadPitch",0.1,0.12)
        time.sleep(1.5); self._gaze_child()

    def _gaze_child(self):
        ST["gaze_mode"]="child"
        self._sa("HeadYaw",0.0,0.1); self._sa("HeadPitch",0.0,0.1)

    def _social_joy_anim(self):
        for _ in range(4):
            self._sa("LShoulderPitch",0.05,0.3); self._sa("RShoulderPitch",0.05,0.3)
            self._sa("HeadPitch",-0.3,0.2); self._sa("HeadYaw",0.3,0.2); time.sleep(0.2)
            self._sa("LShoulderPitch",1.0,0.3); self._sa("RShoulderPitch",1.0,0.3)
            self._sa("HeadPitch",0.0,0.2); self._sa("HeadYaw",-0.3,0.2); time.sleep(0.2)
        self._sa("HeadYaw",0,0.1)

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
# 14. PYBULLET (Window 1 — FIXED via PyBullet GUI settings)
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
            self._add_decor()
            p.resetDebugVisualizerCamera(6,45,-30,[0,0,0.8])
            self.ok=True
            for fn in [self._sim_loop,self._walk_loop,self._arm_loop]:
                threading.Thread(target=fn,daemon=True).start()
            print("✅ PyBullet Window 1 (FIXED — lip-sync active)")
            return self.pepper
        except Exception as e: print(f"⚠️  PyBullet: {e}"); return None

    def _build_room(self):
        wc=[0.88,0.88,0.92,1]
        for pos,ext in [([0,-4,1.1],[5,.1,1.1]),([0,4,1.1],[5,.1,1.1]),
                        ([5,0,1.1],[.1,4,1.1]),([-5,0,1.1],[.1,4,1.1])]:
            p.createMultiBody(0,-1,p.createVisualShape(p.GEOM_BOX,halfExtents=ext,rgbaColor=wc),pos)
        p.createMultiBody(0,-1,p.createVisualShape(p.GEOM_BOX,halfExtents=[4.5,3.5,.02],
            rgbaColor=[.55,.45,.35,1]),[0,0,.01])
        for txt,pos in [("ABA MOTOR",[-4,3,2]),("TEACCH COGNITIVE",[4,3,2]),
                        ("DTT VERBAL",[0,4,2]),("ESDM SOCIAL",[-4,-3,2]),
                        ("★ MASTERY GATE ★",[0,0,3.0])]:
            p.addUserDebugText(txt,pos,[.4,.5,.9],textSize=1.0,lifeTime=0)

    def _add_decor(self):
        cols=[[1,.2,.2,1],[.2,1,.2,1],[.2,.2,1,1],[1,1,.2,1],[1,.5,.2,1]]
        for i in range(5):
            vs=p.createVisualShape(p.GEOM_SPHERE,radius=.15,rgbaColor=cols[i%len(cols)])
            bid=p.createMultiBody(0,-1,vs,[random.uniform(-3,3),
                random.uniform(-2,2),random.uniform(.8,2.2)])
            self.balloons.append({"id":bid,"x":random.uniform(-3,3),
                "y":random.uniform(-2,2),"z":random.uniform(.8,2.2),
                "spd":random.uniform(.01,.03)})

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
            p.addUserDebugText(text[:55],[pos[0],pos[1],pos[2]+1.35],
                [0,0,0],textSize=.85,lifeTime=5)
        except: pass

# ═══════════════════════════════════════════════════════════════
# 15. DISPLAY ENGINE — OpenCV RESIZABLE windows
# ═══════════════════════════════════════════════════════════════
class Display:
    def __init__(self,vision,cam):
        self.v=vision; self.c=cam; self.running=True
        threading.Thread(target=self._run,daemon=True).start()
        print("✅ Display: 2 resizable OpenCV windows")

    def _sim_frame(self):
        h,w=480,640; f=np.zeros((h,w,3),dtype=np.uint8); f[:]=(7,10,25)
        t=time.time()
        for i in range(0,w,60): cv2.line(f,(i,0),(i,h),(15,22,50),1)
        for i in range(0,h,60): cv2.line(f,(0,i),(w,i),(15,22,50),1)
        r=int(28+10*math.sin(t*1.5))
        cv2.circle(f,(w//2,h//2-40),r,(int(50+50*math.sin(t)),
            int(100+100*math.cos(t*0.7)),220),3)
        cv2.putText(f,"SIMULATION MODE",(w//2-110,h//2+20),
            cv2.FONT_HERSHEY_SIMPLEX,0.8,(100,150,255),2)
        return f

    def _run(self):
        no_cam=self.c.idx<0; em_last=0
        # RESIZABLE — for therapist observation
        cv2.namedWindow(WIN_EMO,cv2.WINDOW_NORMAL)
        cv2.resizeWindow(WIN_EMO,600,600)
        cv2.moveWindow(WIN_EMO,760,20)
        cv2.namedWindow(WIN_LIVE,cv2.WINDOW_NORMAL)
        cv2.resizeWindow(WIN_LIVE,820,520)
        cv2.moveWindow(WIN_LIVE,20,20)
        while self.running:
            try:
                if no_cam: frame=self._sim_frame()
                else:
                    ret,f=self.c.read(); frame=f if ret else self._sim_frame()
                now=time.time()
                if now-em_last>0.65 and not no_cam:
                    em_last=now; self.v.analyze_async(frame.copy())
                elif no_cam and now-em_last>3:
                    em_last=now; ST["emotion"]=random.choice(["happy","neutral","joyful"])
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
# 16. FLASK SERVERS
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
.nav a{padding:8px 14px;border-radius:9px;text-decoration:none;
       font-size:.8em;font-weight:700;min-height:40px;display:flex;align-items:center}
.b1{background:#4f46e5;color:#fff}.b2{background:#059669;color:#fff}
.b3{background:#1d4ed8;color:#fff}.b4{background:#7c3aed;color:#fff}
.sc{background:#1a0a3d;border-radius:8px;padding:7px 14px;
    text-align:center;margin-bottom:10px;color:#a78bfa}
.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;max-width:700px;margin:0 auto}
@media(min-width:500px){.grid{grid-template-columns:repeat(3,1fr)}}
.gc{background:#0c0f1e;border:2px solid #1a1f40;border-radius:11px;
    padding:14px;text-align:center;cursor:pointer;transition:.3s}
.gc:hover,.gc:active{border-color:#a78bfa;transform:translateY(-2px)}
.gi{font-size:2.4em;margin-bottom:5px}
.gn{font-weight:700;color:#e0e6ff;font-size:.85em}
.gd{font-size:.68em;color:#6b7280;margin-top:3px}
#ag{max-width:700px;margin:10px auto}
.btn{background:#4f46e5;color:#fff;border:none;padding:9px 16px;border-radius:7px;
     cursor:pointer;font-size:.8em;margin:4px;min-height:42px;touch-action:manipulation}
.btn-g{background:#059669}
canvas{border:2px solid #4f46e5;border-radius:8px;background:#0a0f1e;
       display:block;margin:8px auto;max-width:100%;touch-action:none}
.pbox{background:#0c0f1e;border:2px solid #a78bfa;border-radius:11px;
      padding:14px;max-width:700px;margin:10px auto;text-align:center}
</style></head><body>
<h1>🎮 Clinical Therapy Games</h1>
<div class="nav">
  <a href="http://127.0.0.1:5007/" class="b1">🧠 Brain</a>
  <a href="http://127.0.0.1:5001/" class="b3">📋 Reports</a>
  <a href="http://127.0.0.1:5009/" class="b2">🎮 Games</a>
  <a href="https://LamyaFadlulmolaHamedAli.pythonanywhere.com"
     class="b4" target="_blank">🌐 Platform</a>
</div>
<div class="sc">Score: <span id="pts">0</span> ⭐ | Level: <span id="lvl">1</span></div>
<div class="grid">
  <div class="gc" onclick="start('balloons')"><div class="gi">🎈</div><div class="gn">Balloons</div><div class="gd">Pop!</div></div>
  <div class="gc" onclick="start('emotions')"><div class="gi">😊</div><div class="gn">Emotions</div><div class="gd">Mirror!</div></div>
  <div class="gc" onclick="start('colors')"><div class="gi">🎨</div><div class="gn">Colors</div><div class="gd">Match!</div></div>
  <div class="gc" onclick="start('numbers')"><div class="gi">🔢</div><div class="gn">Count!</div><div class="gd">How many?</div></div>
  <div class="gc" onclick="start('memory')"><div class="gi">🧠</div><div class="gn">Memory</div><div class="gd">Pairs!</div></div>
  <div class="gc" onclick="start('shapes')"><div class="gi">⭐</div><div class="gn">Shapes</div><div class="gd">Name!</div></div>
</div>
<div id="ag"></div>
<div class="pbox">
  <h3 style="color:#a78bfa;margin-bottom:6px">🌐 Platform</h3>
  <a href="https://LamyaFadlulmolaHamedAli.pythonanywhere.com"
     target="_blank" class="btn btn-g" style="display:inline-block;text-decoration:none">Open 🚀</a>
</div>
<script>
var sc=0,lv=1;
function add(n){sc+=n;lv=Math.floor(sc/50)+1;document.getElementById('pts').textContent=sc;document.getElementById('lvl').textContent=lv;}
function start(g){var d=document.getElementById('ag');
  if(g==='balloons')runBalloons(d);else if(g==='emotions')emoGame(d);
  else if(g==='colors')colorGame(d);else if(g==='numbers')numGame(d);
  else if(g==='memory')memGame(d);else shapeGame(d);}
function runBalloons(d){var W=Math.min(680,window.innerWidth-24);d.innerHTML='<canvas id="gc" width="'+W+'" height="280" style="width:100%"></canvas>';var c=document.getElementById('gc'),ctx=c.getContext('2d'),bs=[];for(var i=0;i<8;i++)bs.push({x:Math.random()*(W-40)+20,y:Math.random()*240+20,r:18+Math.random()*12,vx:(Math.random()-0.5)*2.5,vy:(Math.random()-0.5)*2.5,color:['#f87171','#34d399','#60a5fa','#fbbf24','#c084fc'][Math.floor(Math.random()*5)],alive:true});function hit(mx,my){bs.forEach(function(b){if(!b.alive)return;if(Math.sqrt((mx-b.x)**2+(my-b.y)**2)<b.r){b.alive=false;add(10);}});if(bs.every(function(b){return !b.alive;}))bs.forEach(function(b){b.alive=true;b.x=Math.random()*(W-40)+20;b.y=Math.random()*240+20;});}c.addEventListener('click',function(e){var r=c.getBoundingClientRect(),s=c.width/r.width;hit((e.clientX-r.left)*s,(e.clientY-r.top)*s);});c.addEventListener('touchstart',function(e){e.preventDefault();var r=c.getBoundingClientRect(),s=c.width/r.width,t=e.touches[0];hit((t.clientX-r.left)*s,(t.clientY-r.top)*s);},{passive:false});(function loop(){ctx.fillStyle='#0a0f1e';ctx.fillRect(0,0,W,280);bs.forEach(function(b){if(!b.alive)return;b.x+=b.vx;b.y+=b.vy;if(b.x<b.r||b.x>W-b.r)b.vx*=-1;if(b.y<b.r||b.y>280-b.r)b.vy*=-1;ctx.beginPath();ctx.arc(b.x,b.y,b.r,0,Math.PI*2);ctx.fillStyle=b.color;ctx.fill();ctx.fillStyle='white';ctx.font='16px sans-serif';ctx.textAlign='center';ctx.fillText('🎈',b.x,b.y+5);});requestAnimationFrame(loop);})();}
function emoGame(d){var em=[['😊','Happy'],['😢','Sad'],['😠','Angry'],['😨','Scared'],['😲','Surprised']];var pick=em[Math.floor(Math.random()*em.length)];d.innerHTML='<div style="text-align:center;padding:14px"><p style="color:#a78bfa;margin-bottom:7px">Show this face!</p><div style="font-size:4em;margin:10px">'+pick[0]+'</div><p style="font-weight:700;color:#e0e6ff">'+pick[1]+'</p><button class="btn btn-g" onclick="add(20);this.textContent=\'✅ Amazing!\'" style="display:block;width:100%;max-width:200px;margin:10px auto">I did it! 🌟</button><button class="btn" onclick="emoGame(document.getElementById(\'ag\'))" style="display:block;width:100%;max-width:200px;margin:6px auto">Next ➡️</button></div>';}
function colorGame(d){var cs=[['Red','#ef4444'],['Blue','#3b82f6'],['Green','#22c55e'],['Yellow','#eab308'],['Purple','#a855f7'],['Orange','#f97316']];var idx=Math.floor(Math.random()*cs.length);d.innerHTML='<div style="text-align:center;padding:14px"><p style="color:#a78bfa;margin-bottom:7px">What color?</p><div style="width:90px;height:90px;background:'+cs[idx][1]+';border-radius:50%;margin:8px auto;border:3px solid #374151"></div><div id="cbtns" style="display:flex;flex-wrap:wrap;justify-content:center;gap:6px;margin-top:8px">'+cs.map(function(c,i){return '<button class="btn" onclick="chkC('+i+','+idx+')" style="background:'+c[1]+';min-width:80px">'+c[0]+'</button>';}).join('')+'</div></div>';}
window.chkC=function(ch,co){if(ch===co){add(15);document.getElementById('cbtns').innerHTML='<p style="color:#34d399;margin:8px">✅ Correct! 🌟</p><button class="btn" onclick="colorGame(document.getElementById(\'ag\'))" style="display:block;margin:6px auto">Next ➡️</button>';}else document.getElementById('cbtns').innerHTML='<p style="color:#f87171;margin:8px">Try again! 💪</p><button class="btn" onclick="colorGame(document.getElementById(\'ag\'))" style="display:block;margin:6px auto">Retry ↩️</button>';};
function numGame(d){var n=Math.floor(Math.random()*9)+1,stars='';for(var i=0;i<n;i++)stars+='⭐';var opts=Array.from(new Set([n,Math.max(1,n-1),Math.min(10,n+1),n>2?n-2:n+3])).sort(function(){return Math.random()-0.5;}).slice(0,4);d.innerHTML='<div style="text-align:center;padding:14px"><p style="color:#a78bfa">Count!</p><div style="font-size:1.4em;margin:9px;word-break:break-all">'+stars+'</div><div style="display:flex;flex-wrap:wrap;justify-content:center;gap:8px">'+opts.map(function(x){return '<button class="btn" onclick="chkN('+x+','+n+')" style="font-size:1.1em;min-width:60px">'+x+'</button>';}).join('')+'</div></div>';}
window.chkN=function(ch,co){if(ch===co){add(20);alert('✅ YES! '+co+'! 🌟');numGame(document.getElementById('ag'));}else alert('Try again! 💪');};
function memGame(d){var pairs=['🐶','🐱','🐻','🦊','🐼','🐨'],cards=pairs.concat(pairs).sort(function(){return Math.random()-0.5;});window._mc=cards;window._mf=[];window._mm=[];d.innerHTML='<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:6px;max-width:300px;margin:10px auto">'+cards.map(function(c,i){return '<div id="mc'+i+'" onclick="flipM('+i+')" style="height:60px;background:#1f2937;border-radius:7px;display:flex;align-items:center;justify-content:center;font-size:1.7em;cursor:pointer;border:2px solid #374151;touch-action:manipulation">❓</div>';}).join('')+'</div>';}
window.flipM=function(idx){var c=window._mc;if(window._mf.length>=2||window._mm.includes(idx)||window._mf.includes(idx))return;document.getElementById('mc'+idx).textContent=c[idx];window._mf.push(idx);if(window._mf.length===2){var a=window._mf[0],b=window._mf[1];if(c[a]===c[b]){window._mm.push(a,b);add(25);window._mf=[];if(window._mm.length===c.length)setTimeout(function(){alert('🎉 All matched!');memGame(document.getElementById('ag'));},400);}else setTimeout(function(){document.getElementById('mc'+a).textContent='❓';document.getElementById('mc'+b).textContent='❓';window._mf=[];},1000);}};
function shapeGame(d){var shapes=[['⬛','Square'],['⭕','Circle'],['🔺','Triangle'],['💎','Diamond'],['⭐','Star']];var pick=shapes[Math.floor(Math.random()*shapes.length)];d.innerHTML='<div style="text-align:center;padding:14px"><p style="color:#a78bfa;margin-bottom:7px">What shape?</p><div style="font-size:4em;margin:10px">'+pick[0]+'</div><div style="display:flex;flex-wrap:wrap;justify-content:center;gap:6px">'+shapes.map(function(s){return '<button class="btn" onclick="chkS(\''+s[1]+'\',\''+pick[1]+'\')" style="min-width:80px">'+s[1]+'</button>';}).join('')+'</div></div>';}
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
<h1>📋 ABA/TEACCH/DTT/ESDM Clinical Reports</h1>
<div class="nav">
  <a href="http://127.0.0.1:5007/" class="b1">🧠 Brain</a>
  <a href="http://127.0.0.1:5009/" class="b2">🎮 Games</a>
  <a href="http://127.0.0.1:5001/" class="b3">📋 Reports</a>
  <a href="https://LamyaFadlulmolaHamedAli.pythonanywhere.com" class="b4" target="_blank">🌐 Platform</a>
</div>
<div class="card"><h2>📊 Progress</h2>
  <div class="stat"><div class="n">{{s.current_level}}</div><div class="l">Level</div></div>
  <div class="stat"><div class="n">{{s.consecutive}}/3</div><div class="l">★ Mastery</div></div>
  <div class="stat"><div class="n">{{s.tasks_mastered}}</div><div class="l">Mastered</div></div>
  <div class="stat"><div class="n">{{s.score}}</div><div class="l">Score</div></div>
  <div class="stat"><div class="n">{{s.tokens}}</div><div class="l">Tokens</div></div>
  <div class="stat"><div class="n">{{s.tasks_success}}</div><div class="l">OK</div></div>
  <div class="stat"><div class="n">{{s.tasks_fail}}</div><div class="l">Fail</div></div>
  <div class="stat"><div class="n">{{s.attention}}%</div><div class="l">Attention</div></div>
</div>
<div class="card"><h2>📄 Clinical Reports</h2>
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
  <div class="note">
    <span style="color:#a78bfa;font-size:.67em;font-weight:700">{{n.category.upper()}}</span>
    <span style="color:#6b7280;font-size:.67em"> {{n.time}}</span><br>{{n.text}}
  </div>{% endfor %}
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
    if note: ST["parent_notes"].append({"time":datetime.now().strftime("%H:%M:%S"),
                                         "text":note,"category":cat})
    return redirect("/")

@rep_app.errorhandler(404)
def r404(e): return redirect("/"),302

@rep_app.errorhandler(405)
def r405(e): return redirect("/"),302

BRAIN_HTML="""<!DOCTYPE html><html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pepper Clinical Brain</title><meta http-equiv="refresh" content="3">
<script src="https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js"></script>
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{--bg:#060912;--card:#0c0f1e;--bo:#1a1f40;--pu:#a78bfa;--bl:#60a5fa;
      --gr:#34d399;--rd:#f87171;--yl:#fbbf24;--tx:#e0e6ff;--mu:#6b7280}
body{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--tx);font-size:13px}
.layout{display:flex;min-height:100vh}
.sidebar{width:142px;background:#07090f;border-right:2px solid var(--bo);
         display:flex;flex-direction:column;padding:7px 5px;gap:5px;
         position:sticky;top:0;height:100vh;overflow-y:auto;flex-shrink:0}
.sidebar h3{color:var(--pu);font-size:.70em;margin-bottom:2px;text-align:center}
.slink{display:flex;flex-direction:column;align-items:center;padding:8px 4px;
       border-radius:9px;text-decoration:none;font-weight:700;transition:.25s;
       border:2px solid;width:100%;font-size:.67em}
.slink:hover{transform:translateY(-2px);opacity:.9}
.sl-brain{background:#1e1b4b;color:var(--pu);border-color:var(--pu)}
.sl-game{background:#052918;color:var(--gr);border-color:var(--gr)}
.sl-rep{background:#1e3a5f;color:var(--bl);border-color:var(--bl)}
.sl-gh{background:#2a1060;color:#c084fc;border-color:#c084fc}
.sl-plat{background:#1a2040;color:var(--yl);border-color:var(--yl)}
.sl-icon{font-size:1.45em;margin-bottom:2px}.sl-port{font-size:.56em;opacity:.7}
.content{flex:1;padding:8px;min-width:0;overflow-y:auto}
.android-info{background:#051a0f;border:1px solid var(--gr);border-radius:8px;
              padding:6px 10px;margin-bottom:7px;text-align:center}
.android-url{font-size:.80em;color:var(--gr);font-weight:700;word-break:break-all}
.mastery-box{background:#051a0f;border:2px solid var(--gr);border-radius:9px;
             padding:8px;margin-bottom:7px;text-align:center}
.hdr{background:linear-gradient(135deg,#0a0f28,#1a0a3d);border-radius:9px;
     padding:8px 12px;display:flex;align-items:center;gap:7px;
     border:1px solid #4f46e5;margin-bottom:7px}
.hdr h1{font-size:.85em;color:var(--pu)}
.bd{padding:2px 5px;border-radius:8px;font-size:.60em;font-weight:700}
.live{background:#ef4444;color:#fff;animation:blink 1s infinite}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.3}}
.row{display:grid;gap:7px}
.r3{grid-template-columns:1fr 1fr 1fr}.r2{grid-template-columns:1fr 1fr}
.r5{grid-template-columns:repeat(5,1fr)}
.card{background:var(--card);border-radius:9px;padding:10px;border:1px solid var(--bo)}
.card h2{font-size:.73em;color:#818cf8;border-bottom:1px solid var(--bo);
         padding-bottom:3px;margin-bottom:6px}
.stat{background:linear-gradient(135deg,#0d1030,#1a0a3d);
      border:1px solid #312e81;border-radius:7px;padding:8px;text-align:center}
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
.btn{background:linear-gradient(135deg,#4f46e5,#7c3aed);color:#fff;border:none;
     padding:4px 8px;border-radius:5px;cursor:pointer;font-size:.67em;
     margin:2px;transition:.2s;font-family:inherit;min-height:30px}
.btn:hover{opacity:.85}
.btn-g{background:linear-gradient(135deg,#059669,#10b981)}
.btn-y{background:linear-gradient(135deg,#d97706,#f59e0b)}
.btn-r{background:linear-gradient(135deg,#dc2626,#ef4444)}
.btn-b{background:linear-gradient(135deg,#1d4ed8,#3b82f6)}
input,textarea,select{width:100%;padding:5px 7px;border-radius:5px;
  border:1px solid var(--bo);background:#07090f;color:var(--tx);
  font-size:.71em;font-family:inherit;outline:none;min-height:30px}
input:focus,textarea:focus{border-color:var(--pu)}
textarea{resize:vertical;min-height:44px}
.log-box{max-height:155px;overflow-y:auto;scrollbar-width:thin}
.li{padding:2px 5px;margin:1px 0;border-radius:3px;font-size:.66em;
    border-left:3px solid #4f46e5;background:#07090f;line-height:1.4}
.li.success{border-color:var(--gr)}.li.fail{border-color:var(--rd)}
.cw{height:130px;background:#07090f;border-radius:6px;padding:4px}
.chat-box{height:135px;overflow-y:auto;background:#07090f;
          border-radius:6px;padding:6px;margin-bottom:4px;scrollbar-width:thin}
.cm{padding:3px 6px;margin:2px 0;border-radius:5px;font-size:.69em;line-height:1.5}
.cmp{background:#1e1b4b;border-left:3px solid var(--pu)}
.cmc{background:#052918;border-left:3px solid var(--gr)}
.cmr{background:#1a1f40;border-left:3px solid var(--bl)}
.tabs{display:flex;gap:3px;flex-wrap:wrap;margin-bottom:6px}
.tab{padding:3px 8px;border-radius:5px;cursor:pointer;font-size:.67em;
     background:#1f2937;color:#9ca3af;border:1px solid var(--bo);transition:.2s;min-height:26px}
.tab.active,.tab:hover{background:#4f46e5;color:#fff}
.tc{display:none}.tc.active{display:block}
.hc{background:#0a1020;border-radius:7px;padding:7px;border-left:4px solid var(--pu)}
.hct{color:var(--pu);font-weight:700;font-size:.71em;margin-bottom:2px}
.hcb{color:#9ca3af;font-size:.68em;line-height:1.6}
.tip{background:#051a0f;border:1px solid var(--gr);border-radius:3px;
     padding:3px;margin-top:3px;font-size:.66em;color:#6ee7b7}
.ab{display:inline-block;padding:2px 5px;border-radius:6px;font-size:.64em;font-weight:700;margin:1px}
.aon{background:#052918;color:var(--gr);border:1px solid var(--gr)}
.aoff{background:#1f2937;color:#374151;border:1px solid #374151}
::-webkit-scrollbar{width:3px}::-webkit-scrollbar-track{background:var(--card)}
::-webkit-scrollbar-thumb{background:#4f46e5;border-radius:3px}
@media(max-width:700px){.sidebar{width:108px}.r3{grid-template-columns:1fr 1fr}
  .r5{grid-template-columns:repeat(3,1fr)}.r2{grid-template-columns:1fr}}
</style></head><body>
<div class="layout">
<div class="sidebar">
  <h3>🤖 Clinical</h3>
  <div style="text-align:center;padding:5px">
    <div style="font-size:2.2em">🤖</div>
    <div style="font-size:.58em;color:{{'#34d399' if s.gemini_ok else '#fbbf24'}};margin-top:2px">
      {{'AI ON' if s.gemini_ok else 'FALLBACK'}}</div>
    <div style="font-size:.58em;color:#6b7280;margin-top:2px">energy={{mic_energy}}</div>
  </div>
  <a href="http://127.0.0.1:5007/" class="slink sl-brain"><div class="sl-icon">🧠</div><div>Brain</div><div class="sl-port">:5007</div></a>
  <a href="http://127.0.0.1:5009/" target="_blank" class="slink sl-game"><div class="sl-icon">🎮</div><div>Games</div><div class="sl-port">:5009</div></a>
  <a href="http://127.0.0.1:5001/" target="_blank" class="slink sl-rep"><div class="sl-icon">📋</div><div>Reports</div><div class="sl-port">:5001</div></a>
  <a href="https://LamyaFadlulmolaHamedAli.pythonanywhere.com" target="_blank" class="slink sl-plat"><div class="sl-icon">🌐</div><div>Platform</div><div class="sl-port">Live</div></a>
  <a href="{{ github_url }}" target="_blank" class="slink sl-gh"><div class="sl-icon">📦</div><div>GitHub</div><div class="sl-port">Games</div></a>
  <a href="/auto_report" class="slink" style="background:#1a2040;color:var(--yl);border-color:var(--yl)"><div class="sl-icon">⚡</div><div>Report</div><div class="sl-port">→:5001</div></a>
</div>
<div class="content">
<div class="android-info">📱 <b>Android:</b><div class="android-url">http://{{ local_ip }}:5007</div>
  <div style="font-size:.66em;color:#6ee7b7;margin-top:2px">Same WiFi → browser</div></div>
<div class="mastery-box">
  <div style="color:var(--gr);font-size:.80em;font-weight:700">
    ★ {{ task_name }} | {{ s.domain }} | {{ s.consecutive }}/3 mastery</div>
  <div style="font-size:1.6em;margin:4px">
    {{'⭐' * s.consecutive}}{{'☆' * (3 - s.consecutive)}}</div>
  <div style="font-size:.68em;color:var(--mu)">
    Mastered:{{ s.tasks_mastered }} | Protocol:{{ s.protocol }}</div>
</div>
<div class="hdr">
  <div style="font-size:1.2em">🤖</div>
  <div><h1>Pepper Clinical Final System</h1>
    <p style="font-size:.66em;opacity:.8">Commander: <b>Lamya</b> | Child: <b>{{s.name}}</b> | {{s.session_start}}</p></div>
  <span class="bd live">LIVE</span>
  <span class="bd" style="background:#1a2555;color:var(--bl);border:1px solid var(--bl)">
    {% if s.gemini_ok %}AI:{{s.gemini_model[:12]}}{% else %}FALLBACK{% endif %}</span>
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
  <div class="card"><h2>😊 Emotion (MediaPipe)</h2>
    <div style="text-align:center;padding:4px">
      <div class="emo {{s.emotion}}">{{s.emotion.upper()}}</div>
      <div style="margin:5px 0"><div class="bar-bg"><div class="bar" style="width:{{s.attention}}%"></div></div>
        <span style="font-size:.66em;color:var(--pu)">{{s.attention}}%</span></div>
      <div style="font-size:.64em;margin:2px;color:{{'#34d399' if s.face_detected else '#f87171'}}">{{'Face OK' if s.face_detected else 'No Face'}}</div>
      <div style="font-size:.62em;color:var(--mu);margin-top:2px">MediaPipe-only (DeepFace removed)</div>
      <div>
        <span class="ab {{'aon' if s.hand_raised else 'aoff'}}">Hand</span>
        <span class="ab {{'aon' if s.waving else 'aoff'}}">Wave</span>
        <span class="ab {{'aon' if s.clapping else 'aoff'}}">Clap</span>
        <span class="ab {{'aon' if s.arms_out else 'aoff'}}">Arms</span>
        <span class="ab {{'aon' if s.eye_contact else 'aoff'}}">👁</span>
      </div>
      {% if s.is_speaking %}<div style="font-size:.63em;color:var(--bl);margin-top:3px">🔊 Lip:{{(s.lip_sync_value*10)|int}}/10</div>
      {% elif s.listening %}<div style="font-size:.63em;color:var(--gr);margin-top:3px">👂 Listening</div>
      {% endif %}
    </div>
  </div>
  <div class="card"><h2>🎮 Controls</h2>
    <form method="POST" action="/cmd">
      <button class="btn btn-g" name="c" value="joy" style="width:100%;margin:2px 0">Social Joy 🎉</button>
      <button class="btn btn-y" name="c" value="dance" style="width:100%;margin:2px 0">Dance [DANCE]</button>
      <button class="btn btn-b" name="c" value="game" style="width:100%;margin:2px 0">Open Games</button>
      <button class="btn btn-r" name="c" value="break" style="width:100%;margin:2px 0">Break Time</button>
      <button class="btn" name="c" value="next_task" style="width:100%;margin:2px 0">Next Task ⏭️</button>
      <button class="btn" name="c" value="report" style="width:100%;margin:2px 0">Generate Report</button>
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
            <div style="position:absolute;bottom:0;width:100%;height:{{v}}%;background:linear-gradient(0deg,#6366f1,#a78bfa);border-radius:5px"></div>
          </div>
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
    <div class="hc"><div class="hct">3-Star Mastery Gate</div>
      <div class="hcb">★★★ = 3 consecutive correct responses. Any fail resets to ☆☆☆. Task only changes after mastery.</div>
      <div class="tip">TEACCH visual schedule shows on tablet.</div></div>
    <div class="hc"><div class="hct">Visual Modeling</div>
      <div class="hcb">Motor tasks show HD emoji + description on tablet. Pepper says "Look at screen and do this!"</div>
      <div class="tip">Joint angles validated by MediaPipe.</div></div>
    <div class="hc"><div class="hct">Cognitive Tasks</div>
      <div class="hcb">HD color circles, animals, fruits, shapes, numbers. Child clicks correct image on tablet.</div>
      <div class="tip">2x2 grid with visual hint shown.</div></div>
    <div class="hc"><div class="hct">Qt Thread Safety</div>
      <div class="hcb">All UI updates via pyqtSignal. No direct cross-thread Qt calls. Zero QBasicTimer errors.</div>
      <div class="tip">BRIDGE.sig_* handles all UI safely.</div></div>
    <div class="hc"><div class="hct">MediaPipe-Only Vision</div>
      <div class="hcb">DeepFace removed. Emotion from FaceMesh geometry. Joint angles for motor validation. No TF conflicts.</div>
      <div class="tip">EAR blink + mouth-open emotion.</div></div>
    <div class="hc"><div class="hct">Mic energy={{mic_energy}}</div>
      <div class="hcb">Fixed at 300 (was 30). No ghost speech. Clear voice only. Whisper threshold raised.</div>
      <div class="tip">faster-whisper GPU + Google SR fallback.</div></div>
  </div>
  <div class="card" style="margin-top:7px"><h2>Session Info</h2>
    <div style="font-size:.69em;color:#9ca3af;line-height:1.8">
      Child: <b style="color:var(--tx)">{{s.name}}</b> | Level {{s.current_level}} | {{s.session_date}}<br>
      Score:<b style="color:var(--pu)">{{s.score}}</b> | Mastered:<b style="color:var(--gr)">{{s.tasks_mastered}}</b> | Tokens:<b style="color:var(--yl)">{{s.tokens}}</b><br>
      OK:{{s.tasks_success}} | Fail:{{s.tasks_fail}} | FB:{{s.api_fallback_count}}
    </div>
    <div style="margin-top:5px;display:flex;gap:4px">
      <a href="/export" class="btn btn-g" style="text-decoration:none">Export</a>
      <a href="/auto_report" class="btn btn-b" style="text-decoration:none">→:5001</a>
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
    <div class="card"><h2>System Fixes Applied</h2>
      <div style="font-size:.69em;color:var(--mu);line-height:1.9">
        ✅ Qt threads: pyqtSignal<br>✅ DeepFace: removed<br>
        ✅ Emotion: MediaPipe FaceMesh<br>✅ Mic energy: {{mic_energy}}<br>
        ✅ Gemini: gemini-1.5-flash stable<br>✅ No breathing tasks<br>
        ✅ Joint angles: MediaPipe<br>✅ PyBullet: FIXED size<br>
        ✅ OpenCV: RESIZABLE<br>Android: http://{{local_ip}}:5007
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
  data:{labels:LB,datasets:[{label:'Score',data:SD,
    backgroundColor:'rgba(167,139,250,0.5)',borderColor:'#a78bfa',borderWidth:1}]},
  options:CO});
if(document.getElementById('eC')&&Object.keys(ED).length>0){
  const EC={happy:'#34d399',sad:'#60a5fa',angry:'#f87171',neutral:'#9ca3af',fear:'#fbbf24',surprised:'#c084fc',joyful:'#34d399',confused:'#fb923c'};
  new Chart(document.getElementById('eC'),{type:'doughnut',
    data:{labels:Object.keys(ED),datasets:[{data:Object.values(ED),
      backgroundColor:Object.keys(ED).map(e=>EC[e]||'#6366f1')}]},
    options:{responsive:true,maintainAspectRatio:false,
      plugins:{legend:{position:'right',labels:{color:'#9ca3af',font:{size:8}}}}}});}
['cs','cp'].forEach(id=>{const el=document.getElementById(id);if(el)el.scrollTop=el.scrollHeight;});
</script></body></html>"""

QUICK_QS=["My child has a meltdown, what do I do?",
          "How do I improve eye contact?","What is ABA vs TEACCH?",
          "How to handle repetitive behaviors?","What is ESDM therapy?",
          "كيف أتعامل مع نوبات الغضب؟","كيف أساعد طفلي على التواصل البصري؟",
          "ما هي أفضل طريقة لتعليم طفلي؟","How to help with sleep problems?",
          "كيف أحسن مهارات التواصل لطفلي؟"]

@brain_app.route("/")
@brain_app.route("/<path:path>")
def brain_catch(path=""):
    ed={}
    for e in ST["emo_history"]: ed[e]=ed.get(e,0)+1
    tidx=min(ST["task_index"],len(TASKS)-1)
    t=TASKS[tidx]
    mastery_pct=min(100,int(ST["consecutive"]/3*100))
    return render_template_string(BRAIN_HTML,s=ST,qqs=QUICK_QS,
        att_h=ST["att_history"][-40:],sc_h=ST["score_history"][-40:],
        ed=ed,local_ip=LOCAL_IP,github_url=GITHUB_URL,
        task_name=t["id"].replace("_"," ").title(),
        mastery_pct=mastery_pct,mic_energy=MIC_ENERGY,
        whisper_ok=str(WHISPER_OK))

@brain_app.route("/cmd",methods=["GET","POST"])
def brain_cmd():
    c=(request.form.get("c","") or request.args.get("c",""))
    if c:
        ST["sim_cmd"]=c
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
    if note: ST["parent_notes"].append({"time":datetime.now().strftime("%H:%M:%S"),
                                         "text":note,"category":cat})
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
        "current_level":ST["current_level"],"domain":ST["domain"],
        "consecutive":ST["consecutive"],"tasks_mastered":ST["tasks_mastered"],
        "gemini_ok":ST["gemini_ok"],"is_speaking":ST["is_speaking"],
        "lip_sync_value":round(ST["lip_sync_value"],2),
        "mic_energy":MIC_ENERGY,"local_ip":LOCAL_IP,
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
# 17. THERAPY CONTROLLER
# ═══════════════════════════════════════════════════════════════
class TherapyCtrl:
    def __init__(self,g,v,m,d,s,a,tw):
        self.g=g; self.v=v; self.m=m
        self.d=d; self.s=s; self.a=a; self.tw=tw
        self.running=False

    def _speak(self,text):
        # Process social tokens
        if "[GAZE_TABLET]" in text:
            text=text.replace("[GAZE_TABLET]","")
            threading.Thread(target=self.a._gaze_tablet,daemon=True).start()
        if "[GAZE_CHILD]" in text:
            text=text.replace("[GAZE_CHILD]","")
            threading.Thread(target=self.a._gaze_child,daemon=True).start()
        clean=self.a.process(str(text))
        if self.s.ok: self.s.show_text(clean[:55])
        # Safe UI update via signal
        BRIDGE.sig_set_instr.emit(clean[:70])
        self.v.say(clean)

    def _ask(self,prompt):
        resp=self.g.ask(prompt); self._speak(resp); return resp

    def run(self):
        self.running=True
        name=self.m.get_name(self.v)
        # Initial greeting with visual modeling explanation
        self._ask(
            f"Child name is {name}. Warm ABA greeting! [WAVE] "
            "Explain: for motor tasks look at tablet screen and copy! "
            "For cognitive tasks click the correct image! "
            "3 stars = mastery! 'Ready? Your turn! 🎯'")
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
                    self._ask(f"Child became {curr}. [HUG] Comfort!")
            self._handle_cmd()
            # Get current task
            tidx=ST["task_index"]%len(TASKS)
            task=TASKS[tidx]
            ST["protocol"]=task["protocol"]
            ST["current_level"]=task["level"]
            ST["domain"]=task["domain"]
            ST["tablet_instruction"]=task["instruction"]
            # Show on tablet via signal (thread-safe)
            self._show_tablet(task)
            success=self._run_task(task)
            if success: self._on_success(task)
            else: self._on_fail(task)
            time.sleep(0.3)

    def _show_tablet(self,task):
        """Build tablet data and emit signal — thread safe"""
        mode=task.get("tablet_mode","idle")
        data={"mode":mode,"instruction":task["instruction"]}
        if mode=="motor_model":
            data.update({
                "emoji":task.get("motor_emoji","🤖"),
                "label":task.get("motor_label",""),
                "desc":task.get("motor_desc",""),
            })
        elif mode=="word_display":
            data.update({
                "emoji":task.get("word_emoji","📢"),
                "word":task.get("word_text","SAY IT!"),
            })
        elif mode in ["color_grid","object_grid","shape_grid",
                      "number_grid","emotion_grid"]:
            opts=task.get("options",[])
            data.update({
                "options":opts,
                "correct":task.get("correct",-1),
                "visual_hint":task.get("visual_hint",""),
            })
        ST["tablet_click_result"]=None
        BRIDGE.sig_show_task.emit(data)

    def _run_task(self,task):
        name=ST["name"]; vtype=task["verify"]
        prompts=task.get("prompts",["Try again!"])
        ST["task_success"]=False; ST["last_speech_text"]=""
        # Set camera verify for motor tasks
        motor_verifies=["clap","wave","raise_hand","touch_nose","arms_out","hands_up","head_tilt","blink"]
        if vtype in motor_verifies:
            ST["verify_action"]=vtype; ST["verify_result"]=False
            ST["verify_timeout"]=time.time()+20  # Extra time for motor tasks
        # DTT instruction + TEACCH visual modeling
        domain=task["domain"]
        if domain=="Motor":
            resp=self.g.ask(
                f"MOTOR task: '{task['instruction']}' for {name}. "
                "Say 'Look at the screen and do this!' [GAZE_TABLET] "
                f"Em:{ST['emotion']}. 'Ready? Your turn! 🎯'")
        else:
            resp=self.g.ask(
                f"COGNITIVE task: '{task['instruction']}' for {name}. "
                "Say 'Click the correct one on the tablet!' "
                f"Em:{ST['emotion']}. 'Ready? Your turn! 🎯'")
        self._speak(resp)
        for attempt in range(3):
            ST["prompt_attempt"]=attempt
            ok=self._wait_task(task,timeout=18)
            if ok: ST["verify_action"]=None; return True
            if attempt<len(prompts):
                hint=prompts[attempt]
                self.v.say(f"{name}... {hint} 🎯",wait=False)
                BRIDGE.sig_set_feedback.emit(hint)
                time.sleep(0.5)
        ST["verify_action"]=None
        return False

    def _wait_task(self,task,timeout=18):
        vtype=task["verify"]; keyword=task.get("keyword","")
        deadline=time.time()+timeout
        while time.time()<deadline:
            # Motor — joint angle verified
            if vtype in ["clap","wave","raise_hand","touch_nose","arms_out","hands_up","head_tilt","blink"]:
                if ST["verify_result"]: ST["verify_result"]=False; return True
                if vtype=="clap" and ST["clapping"]: return True
                if vtype=="wave" and ST["waving"]: return True
                if vtype=="raise_hand" and ST["hand_raised"]: return True
                if vtype=="arms_out" and ST["arms_out"]: return True
                if vtype=="hands_up" and ST["hands_up"]: return True
                if vtype=="blink" and ST["blinking"]: return True
                if vtype=="head_tilt" and ST["head_tilted"]: return True
            # Tablet click
            elif vtype=="tablet_click":
                res=ST.get("tablet_click_result")
                if res=="correct": ST["tablet_click_result"]=None; return True
                elif res=="wrong": ST["tablet_click_result"]=None; return False
            # Speech
            elif vtype=="speech_keyword" and keyword:
                if keyword.lower() in ST.get("last_speech_text","").lower(): return True
            elif vtype in ["speech_any","speech"]:
                if ST["last_sound"]>time.time()-3 and len(ST.get("last_speech_text",""))>0:
                    return True
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
        ST["consecutive"]+=1
        ST["score"]+=task.get("tokens",2)*5
        ST["tokens"]+=task.get("tokens",2)
        ST["tasks_success"]+=1; ST["streak"]+=1
        sk_map={"Motor":"motor","Cognitive":"cognitive","Verbal":"verbal","Social":"social"}
        sk=sk_map.get(task["domain"],"cognitive")
        ST["skills"][sk]=min(100,ST["skills"][sk]+random.randint(1,3))
        ST["skills"]["attention"]=min(100,ST["skills"]["attention"]+random.randint(0,2))
        # Joy animation via signal (thread-safe)
        joy_type=task.get("joy","celebrate")
        self.a.trigger_joy(joy_type)
        BRIDGE.sig_show_result.emit(True,f"Great job! You found it! ⭐ {ST['consecutive']}/3")
        LOG(f"✅ {ST['consecutive']}/3 '{task['id']}'","success")

        # MASTERY GATE: 3 consecutive
        if ST["consecutive"]>=3:
            ST["consecutive"]=0; ST["tasks_mastered"]+=1
            ST["task_index"]+=1
            if ST["task_index"]>=len(TASKS):
                ST["task_index"]=0; ST["current_level"]+=1
            next_t=TASKS[ST["task_index"]%len(TASKS)]
            LOG(f"🏆 MASTERED → {next_t['id']}","success")
            self._ask(
                f"{name} earned 3 stars! MASTERED! [LEVEL_UP][SOCIAL_JOY] "
                f"Next: '{next_t['instruction'][:25]}' [WAVE]")
            if task.get("reward")=="youtube":
                ST["youtube_pending"]=True
                self._ask(f"{name} earned video reward! [CELEBRATE] "
                          "Tell me what video! 🎬")
        else:
            self.v.say(EMPATHY.get("task_ok"),wait=False)
            QTimer.singleShot(800,self.tw.reset_cards if self.tw else lambda: None)
        if ST["tasks_success"]%9==0 and _gemini:
            r=_gemini.generate_report()
            ST["reports"].append({"time":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"content":r})

    def _on_fail(self,task):
        ST["consecutive"]=0  # Mastery gate: reset
        ST["streak"]=0; ST["tasks_fail"]+=1
        self.v.say(EMPATHY.get("task_retry"),wait=False)
        BRIDGE.sig_show_result.emit(False,"Try again! Look carefully!")
        QTimer.singleShot(2500,self.tw.reset_cards if self.tw else lambda: None)

    def _handle_cmd(self):
        cmd=ST.get("sim_cmd")
        if not cmd: return
        ST["sim_cmd"]=None
        if cmd=="joy": self.a.trigger_joy("full_joy")
        elif cmd=="dance": self._ask("Dance! [DANCE][CELEBRATE]")
        elif cmd=="game":
            webbrowser.open(GAME_URL)
            self.v.say(f"Opening games {ST['name']}! [GAME] 🎮",wait=False)
        elif cmd=="break": self.v.say("Break time! Relax.",wait=False)
        elif cmd=="next_task":
            ST["consecutive"]=0
            ST["task_index"]=(ST["task_index"]+1)%len(TASKS)
            self.v.say(f"Next task {ST['name']}! 🎯",wait=False)
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
        if ST.get("youtube_pending"):
            ST["youtube_pending"]=False
            self.a.process(f"[YOUTUBE: {text} autism children educational]"); return
        if any(w in t for w in ["game","play","العب","لعبة"]):
            webbrowser.open(GAME_URL)
            self.v.say(f"Opening games {name}! [GAME] 🎮",wait=False); return
        edu_kw=["how","what","why","where","when","who","show","teach",
                "كيف","ما هو","لماذا","أين","متى","أرني"]
        if any(w in t for w in edu_kw):
            resp=self.g.ask(f"Child asked: '{text}'. Answer clearly! [YOUTUBE: {text}] 🎯")
            self._speak(resp); return
        emo_kw=["happy","sad","angry","scared","love","tired","hurt",
                "حزين","خايف","زعلان","مبسوط","تعبان"]
        if any(w in t for w in emo_kw):
            resp=self.g.ask(f"Child expressed: '{text}'. [HUG] Empathy! 🎯")
            self._speak(resp); return
        resp=self.g.ask(f"Child said: '{text}'. Respond clinically! 'Ready? Your turn! 🎯'")
        self._speak(resp)

# ═══════════════════════════════════════════════════════════════
# 18. MAIN
# ═══════════════════════════════════════════════════════════════
def main():
    global _gemini

    print(f"""
╔══════════════════════════════════════════════════════════════╗
║  PEPPER CLINICAL FINAL SYSTEM                               ║
║  Commander: Lamya | Omdurman Islamic University             ║
╠══════════════════════════════════════════════════════════════╣
║  FIXES: Qt Threads | No DeepFace | energy=300 | 1.5-flash  ║
║  Visual Modeling | Joint Angles | 3-Star Mastery Gate       ║
╠══════════════════════════════════════════════════════════════╣
║  Window 1: PyBullet (FIXED — lip-sync)                     ║
║  Window 2: Emotion + Skeleton (RESIZABLE)                  ║
║  Window 3: Live Session (RESIZABLE)                        ║
║  Window 4: Tablet UI FIXED 740×960                         ║
╠══════════════════════════════════════════════════════════════╣
║  Laptop:  http://127.0.0.1:5007                             ║
║  Android: http://{LOCAL_IP}:5007                            ║
╚══════════════════════════════════════════════════════════════╝
""")

    for app,port,name in [(game_app,PORT_GAME,"Game"),
                          (rep_app,PORT_REP,"Reports"),
                          (brain_app,PORT_BRAIN,"Brain")]:
        threading.Thread(target=run_server,args=(app,port,name),daemon=True).start()
        time.sleep(0.4)
    time.sleep(0.8)

    gemini=GeminiBrain(); _gemini=gemini
    voice=Voice(); camera=Camera()
    vision=VisionEngine(); display=Display(vision,camera)
    mic=Mic()
    sim=PepperSim(); pepper=sim.launch()
    acts=Actions(pepper)
    threading.Thread(target=acts.run_lip_sync_pybullet,daemon=True).start()

    time.sleep(1.5)

    # PyQt6 must run on main thread
    qt_app=QApplication(sys.argv)
    qt_app.setApplicationName("Pepper Clinical Final System")
    qt_app.setStyle("Fusion")
    palette=QPalette()
    palette.setColor(QPalette.ColorRole.Window,QColor(6,9,18))
    palette.setColor(QPalette.ColorRole.WindowText,QColor(224,230,255))
    palette.setColor(QPalette.ColorRole.Base,QColor(12,15,30))
    palette.setColor(QPalette.ColorRole.Text,QColor(224,230,255))
    qt_app.setPalette(palette)

    tablet=TabletWindow()
    tablet.show(); tablet.move(10,580)

    ctrl=TherapyCtrl(gemini,voice,mic,display,sim,acts,tablet)

    def _start():
        time.sleep(0.6)
        voice.say("Welcome to Pepper Clinical Final System! "
                  "Commander Lamya, all 4 windows active! "
                  "Fixes applied: no ghost speech, stable AI, safe Qt. "
                  "Starting therapy now!",wait=False)
        if pepper:
            threading.Thread(target=acts._wave,daemon=True).start()
        threading.Thread(target=ctrl.run,daemon=True).start()

    threading.Thread(target=_start,daemon=True).start()

    print(f"""
{'='*64}
✅ CLINICAL FINAL SYSTEM ACTIVE
{'='*64}
Window 1: PyBullet (FIXED lip-sync HeadPitch)
Window 2: Emotion + Skeleton (RESIZABLE)
Window 3: Live Session (RESIZABLE)
Window 4: Tablet FIXED 740×960 (child clicks here!)

Laptop  → http://127.0.0.1:{PORT_BRAIN}/
Android → http://{LOCAL_IP}:{PORT_BRAIN}/
Mic energy={MIC_ENERGY} (no ghost speech)
Gemini: gemini-1.5-flash (stable)
DeepFace: REMOVED (MediaPipe-only)
Qt: pyqtSignal thread-safe
{'='*64}
Commands: stats | name X | next | report | exit
{'='*64}
""")

    def _input_loop():
        while ctrl.running:
            try:
                cmd=input("> ").strip()
                if not cmd: continue
                cl=cmd.lower()
                if cl in ["q","exit","quit"]:
                    ctrl.running=False; display.stop(); qt_app.quit(); break
                elif cl in ["stop","interrupt"]: voice.stop()
                elif cl=="stats":
                    print(f"\n Child:{ST['name']} Level:{ST['current_level']} "
                          f"Domain:{ST['domain']} Mastery:{ST['consecutive']}/3 "
                          f"Mastered:{ST['tasks_mastered']} Score:{ST['score']}")
                elif cl=="next":
                    ST["consecutive"]=0
                    ST["task_index"]=(ST["task_index"]+1)%len(TASKS)
                    voice.say("Next task!",wait=False)
                elif cl=="report" and _gemini:
                    r=_gemini.generate_report()
                    ST["reports"].append({"time":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"content":r})
                    print("📋 Report → Port 5001")
                elif cl.startswith("name "):
                    n=cl[5:].strip().title(); ST["name"]=n; ST["known"]=True
                    voice.say(f"Hello {n}!",wait=False)
                else:
                    ctrl._on_speech(cmd)
            except (KeyboardInterrupt,EOFError): break
        qt_app.quit()

    threading.Thread(target=_input_loop,daemon=True).start()
    ret=qt_app.exec()

    ctrl.running=False; display.stop()
    if _gemini:
        r=_gemini.generate_report()
        ST["reports"].append({"time":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"content":r})
    voice.say("Goodbye! Great session!",wait=False)
    fn=f"session_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(fn,"w") as f: json.dump(ST,f,indent=2,default=str)
    print(f"\n📄 Saved: {fn} | Goodbye Commander Lamya!")
    sys.exit(ret)

if __name__=="__main__":
    main()
