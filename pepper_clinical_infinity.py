#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║  PEPPER CLINICAL INFINITY                                       ║
║  pepper_clinical_infinity.py                                    ║
║  Commander: Lamya | Omdurman Islamic University                 ║
╠══════════════════════════════════════════════════════════════════╣
║  QUAD-WINDOW DASHBOARD:                                         ║
║  W1: PyBullet (lip-sync, blink, head-tilt, nose-twitch)        ║
║  W2: Emotion + Skeleton (OpenCV resizable)                     ║
║  W3: Live Station + Avatar (OpenCV resizable)                  ║
║  W4: HD Tablet UI (PyQt6 FIXED — touch-click interaction)     ║
║                                                                  ║
║  CLINICAL: ABA/DTT/TEACCH/ESDM                                 ║
║  INFINITE: Motor + Cognitive + Math + Verbal                   ║
║  MULTI-PATIENT: fresh CSV per child, clean-slate every run     ║
║  HIGH-SENSITIVITY: energy=200, instant click validation        ║
║  ALL Qt UI via pyqtSignal — zero threading violations          ║
╚══════════════════════════════════════════════════════════════════╝
"""

# ═══════════════════════════════════════════════════════════════
# 0. ENV & AUTO-INSTALL
# ═══════════════════════════════════════════════════════════════
import os, sys, subprocess, ctypes, warnings, socket, signal, time
import threading, random, math, re, json, csv, base64, wave, tempfile
from datetime import datetime
from io import BytesIO

os.environ.update({
    'TF_CPP_MIN_LOG_LEVEL': '3', 'PYTHONWARNINGS': 'ignore',
    'OPENCV_LOG_LEVEL': 'ERROR', 'CUDA_VISIBLE_DEVICES': '0',
    'QT_LOGGING_RULES': '*.debug=false', 'QT_QPA_PLATFORM': 'xcb',
    'QT_QPA_FONTDIR': '/usr/share/fonts', 'TF_ENABLE_ONEDNN_OPTS': '0',
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
                '--break-system-packages','-q'],capture_output=True,timeout=90)
            return True
        except: return False

for pkg,imp in [('PyQt6','PyQt6'),('mediapipe','mediapipe'),
    ('faster-whisper','faster_whisper'),('pyttsx3','pyttsx3'),
    ('speechrecognition','speech_recognition'),('opencv-python','cv2'),
    ('numpy','numpy'),('flask','flask'),('Pillow','PIL')]:
    auto_install(pkg,imp)

def kill_ports(*ports):
    for port in ports:
        try: os.system(f"fuser -k {port}/tcp 2>/dev/null")
        except: pass
        for _ in range(8):
            try:
                s=socket.socket(); s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
                s.bind(('0.0.0.0',port)); s.close(); break
            except: time.sleep(0.3)

kill_ports(5001,5007,5009)

# ═══════════════════════════════════════════════════════════════
# 1. IMPORTS
# ═══════════════════════════════════════════════════════════════
import cv2, numpy as np
import pyttsx3, speech_recognition as sr
from PIL import Image, ImageDraw, ImageFont
import mediapipe as mp

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QGridLayout, QProgressBar,
    QGraphicsOpacityEffect,
)
from PyQt6.QtCore import (
    Qt, QTimer, pyqtSignal, QObject, QThread, QPropertyAnimation,
    QEasingCurve, QPoint, QRect,
)
from PyQt6.QtGui import (
    QFont, QColor, QPalette, QPixmap, QImage, QPainter, QPainterPath,
    QLinearGradient,
)

try:
    from faster_whisper import WhisperModel
    WHISPER_OK = True
except: WHISPER_OK = False

import google.generativeai as genai

# ═══════════════════════════════════════════════════════════════
# 2. CONFIG & MULTI-PATIENT SETUP
# ═══════════════════════════════════════════════════════════════
GEMINI_KEY = "AIzaSyDEdleVKiQ5E00wMcjMbji0G9JcYT2TvE8"
MIC_ENERGY = 200   # High sensitivity
MASTERY_N  = 3     # Consecutive successes for mastery

genai.configure(api_key=GEMINI_KEY)

def get_local_ip():
    try:
        s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        s.connect(("8.8.8.8",80)); ip=s.getsockname()[0]; s.close(); return ip
    except: return "127.0.0.1"

LOCAL_IP = get_local_ip()

# ── MULTI-PATIENT: prompt for child name at launch ──
print("\n" + "═"*64)
print("  PEPPER CLINICAL INFINITY — Commander: Lamya")
print("  Omdurman Islamic University")
print("═"*64)
CHILD_NAME = input("\n👦 Enter Child's Name (for CSV log): ").strip()
if not CHILD_NAME: CHILD_NAME = "Child"
CHILD_NAME_SAFE = re.sub(r'[^a-zA-Z0-9_]','_', CHILD_NAME)
CSV_FILE = f"{CHILD_NAME_SAFE}_Results.csv"

# Create fresh CSV (clean slate every run)
with open(CSV_FILE,'w',newline='') as f:
    w=csv.writer(f)
    w.writerow(["Timestamp","Child","Task","Domain","Level","Result",
                "Consecutive","Score","Emotion","Attention"])
print(f"✅ Fresh log: {CSV_FILE}")

def log_csv(task_id, domain, level, result, consecutive, score, emotion, attention):
    with open(CSV_FILE,'a',newline='') as f:
        csv.writer(f).writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            CHILD_NAME, task_id, domain, level,
            "SUCCESS" if result else "FAIL",
            consecutive, score, emotion, attention])

# ═══════════════════════════════════════════════════════════════
# 3. INFINITE TASK GENERATOR
# ═══════════════════════════════════════════════════════════════
def _make_figure(movement:str, size:int=280)->str:
    """Stick-figure PNG → base64 data URI"""
    img=Image.new("RGBA",(size,size),(245,248,255,255))
    dr=ImageDraw.Draw(img)
    cx,cy=size//2,size//2+10; lw=4; col="#2c3e50"; hl="#e74c3c"
    # Head
    dr.ellipse([cx-28,cy-86,cx+28,cy-30],outline=col,width=lw)
    # Body
    dr.line([cx,cy-30,cx,cy+54],fill=col,width=lw)
    # Legs
    dr.line([cx,cy+54,cx-26,cy+100],fill=col,width=lw)
    dr.line([cx,cy+54,cx+26,cy+100],fill=col,width=lw)
    if movement=="clap":
        dr.line([cx-44,cy-4,cx-6,cy+16],fill=col,width=lw)
        dr.line([cx+44,cy-4,cx+6,cy+16],fill=col,width=lw)
        dr.ellipse([cx-10,cy+10,cx+10,cy+28],fill=hl)
    elif movement=="wave":
        dr.line([cx-40,cy-6,cx-20,cy+14],fill=col,width=lw)
        dr.line([cx+40,cy-14,cx+64,cy-46],fill=col,width=lw)
        dr.line([cx+64,cy-46,cx+58,cy-66],fill=hl,width=4)
    elif movement=="raise_hand":
        dr.line([cx-40,cy-6,cx-20,cy+14],fill=col,width=lw)
        dr.line([cx+40,cy-14,cx+50,cy-72],fill=hl,width=5)
        dr.ellipse([cx+42,cy-86,cx+62,cy-66],fill=hl)
    elif movement=="touch_nose":
        nx,ny=cx,cy-58; dr.ellipse([nx-7,ny-7,nx+7,ny+7],fill=hl)
        dr.line([cx-40,cy-4,cx-8,cy-54],fill=hl,width=5)
        dr.line([cx+40,cy-4,cx+20,cy+14],fill=col,width=lw)
    elif movement=="arms_out":
        dr.line([cx-40,cy-6,cx-88,cy-6],fill=hl,width=5)
        dr.line([cx+40,cy-6,cx+88,cy-6],fill=hl,width=5)
    elif movement=="hands_up":
        dr.line([cx-40,cy-6,cx-54,cy-68],fill=hl,width=5)
        dr.line([cx+40,cy-6,cx+54,cy-68],fill=hl,width=5)
        dr.ellipse([cx-66,cy-82,cx-44,cy-62],fill=hl)
        dr.ellipse([cx+44,cy-82,cx+66,cy-62],fill=hl)
    elif movement=="point":
        dr.line([cx-40,cy-6,cx-20,cy+14],fill=col,width=lw)
        dr.line([cx+40,cy-14,cx+80,cy-6],fill=col,width=lw)
        dr.line([cx+80,cy-6,cx+100,cy-8],fill=hl,width=5)
        dr.ellipse([cx+96,cy-16,cx+110,cy-2],fill=hl)
    else:
        dr.line([cx-40,cy-6,cx-60,cy+12],fill=col,width=lw)
        dr.line([cx+40,cy-6,cx+60,cy+12],fill=col,width=lw)
    # "Do it!" arrow
    dr.text((cx-40,size-26),"👇 YOUR TURN! 👇",fill=(231,76,60,255))
    buf=BytesIO(); img.save(buf,"PNG")
    return "data:image/png;base64,"+base64.b64encode(buf.getvalue()).decode()

# Pre-render motor figures
MOTOR_FIGS = {m:_make_figure(m) for m in
    ["clap","wave","raise_hand","touch_nose","arms_out","hands_up","point"]}

# ── TASK POOLS ───────────────────────────────────────────────
_COLORS=[
    {"id":"red",    "color":"#ef4444","label":"🔴 RED"},
    {"id":"blue",   "color":"#3b82f6","label":"🔵 BLUE"},
    {"id":"green",  "color":"#22c55e","label":"🟢 GREEN"},
    {"id":"yellow", "color":"#eab308","label":"🟡 YELLOW"},
    {"id":"purple", "color":"#a855f7","label":"🟣 PURPLE"},
    {"id":"orange", "color":"#f97316","label":"🟠 ORANGE"},
    {"id":"pink",   "color":"#ec4899","label":"🩷 PINK"},
    {"id":"brown",  "color":"#92400e","label":"🟤 BROWN"},
]
_ANIMALS=[
    {"id":"dog","emoji":"🐶","label":"Dog"},
    {"id":"cat","emoji":"🐱","label":"Cat"},
    {"id":"lion","emoji":"🦁","label":"Lion"},
    {"id":"elephant","emoji":"🐘","label":"Elephant"},
    {"id":"rabbit","emoji":"🐰","label":"Rabbit"},
    {"id":"bear","emoji":"🐻","label":"Bear"},
    {"id":"monkey","emoji":"🐵","label":"Monkey"},
    {"id":"tiger","emoji":"🐯","label":"Tiger"},
    {"id":"giraffe","emoji":"🦒","label":"Giraffe"},
    {"id":"penguin","emoji":"🐧","label":"Penguin"},
    {"id":"dolphin","emoji":"🐬","label":"Dolphin"},
    {"id":"owl","emoji":"🦉","label":"Owl"},
]
_FRUITS=[
    {"id":"apple","emoji":"🍎","label":"Apple"},
    {"id":"banana","emoji":"🍌","label":"Banana"},
    {"id":"orange","emoji":"🍊","label":"Orange"},
    {"id":"grapes","emoji":"🍇","label":"Grapes"},
    {"id":"strawberry","emoji":"🍓","label":"Strawberry"},
    {"id":"watermelon","emoji":"🍉","label":"Watermelon"},
    {"id":"mango","emoji":"🥭","label":"Mango"},
    {"id":"pineapple","emoji":"🍍","label":"Pineapple"},
    {"id":"cherry","emoji":"🍒","label":"Cherry"},
    {"id":"peach","emoji":"🍑","label":"Peach"},
]
_SHAPES=[
    {"id":"circle","emoji":"⭕","label":"Circle"},
    {"id":"square","emoji":"⬛","label":"Square"},
    {"id":"triangle","emoji":"🔺","label":"Triangle"},
    {"id":"diamond","emoji":"💎","label":"Diamond"},
    {"id":"star","emoji":"⭐","label":"Star"},
    {"id":"heart","emoji":"❤️","label":"Heart"},
    {"id":"moon","emoji":"🌙","label":"Moon"},
    {"id":"sun","emoji":"☀️","label":"Sun"},
]
_MOTORS=[
    {"id":"clap","name":"👏 Clap","verify":"clap",
     "instruction":"Look at the screen and CLAP your hands!",
     "waiting":"I am waiting — clap your hands! 👏",
     "success":"Amazing! You clapped! ✅","fail":"Try again — clap your hands!"},
    {"id":"wave","name":"👋 Wave","verify":"wave",
     "instruction":"Look at the screen and WAVE hello!",
     "waiting":"Wave your hand! 👋",
     "success":"Wonderful! You waved! ✅","fail":"Wave side to side!"},
    {"id":"raise_hand","name":"✋ Raise Hand","verify":"raise_hand",
     "instruction":"Look at the screen and RAISE your hand HIGH!",
     "waiting":"Raise your hand! ✋","success":"Perfect! ✅","fail":"Lift arm above head!"},
    {"id":"touch_nose","name":"👆 Touch Nose","verify":"touch_nose",
     "instruction":"Look at the screen and TOUCH your NOSE!",
     "waiting":"Touch your nose! 👆","success":"Brilliant! ✅","fail":"Point finger to nose!"},
    {"id":"arms_out","name":"🤸 Arms Wide","verify":"arms_out",
     "instruction":"Stretch BOTH arms wide like an airplane!",
     "waiting":"Spread arms wide! 🤸","success":"Like an airplane! ✅","fail":"Spread both arms!"},
    {"id":"hands_up","name":"🙌 Hands Up","verify":"hands_up",
     "instruction":"Put BOTH hands UP HIGH!",
     "waiting":"Both hands up! 🙌","success":"Superstar! ✅","fail":"Lift both arms!"},
    {"id":"point","name":"👉 Point","verify":"point",
     "instruction":"POINT your finger forward!",
     "waiting":"Point your finger! 👉","success":"Great pointing! ✅","fail":"Stretch finger forward!"},
]
_NUMBERS=list(range(1,11))
_WORDS=["apple","ball","cat","dog","elephant","fish","good","happy","jump","kite",
        "love","milk","no","okay","play","quiet","red","sun","tree","up",
        "very","water","yes","zero","blue","green","one","two","three"]

def generate_task_pool(n=2000):
    """Generate n random clinical tasks"""
    pool=[]
    # Motor (30%)
    for _ in range(int(n*0.30)):
        m=random.choice(_MOTORS)
        pool.append({**m,"domain":"Motor","level":1,"tablet_mode":"motor_model",
            "figure":MOTOR_FIGS.get(m["verify"],""),
            "tokens":2,"joy":"dance"})
    # Cognitive colors (12%)
    for _ in range(int(n*0.12)):
        target=random.choice(_COLORS)
        distractors=random.sample([c for c in _COLORS if c["id"]!=target["id"]],3)
        opts=[target]+distractors; random.shuffle(opts)
        correct=next(i for i,o in enumerate(opts) if o["id"]==target["id"])
        pool.append({"id":f"color_{target['id']}","domain":"Cognitive","level":2,
            "name":f"🎨 Find {target['label']}",
            "instruction":f"Click the {target['label']} color!",
            "waiting":f"Find and click {target['label']}!",
            "success":f"Correct! That is {target['label']}! ✅",
            "fail":f"Not quite! Find {target['label']}!",
            "tablet_mode":"color_grid","options":opts,"correct":correct,
            "tokens":3,"joy":"celebrate"})
    # Cognitive animals (12%)
    for _ in range(int(n*0.12)):
        target=random.choice(_ANIMALS)
        distractors=random.sample([a for a in _ANIMALS if a["id"]!=target["id"]],3)
        opts=[target]+distractors; random.shuffle(opts)
        correct=next(i for i,o in enumerate(opts) if o["id"]==target["id"])
        pool.append({"id":f"animal_{target['id']}","domain":"Cognitive","level":3,
            "name":f"🐾 Find {target['label']}",
            "instruction":f"Click the {target['label']}!",
            "waiting":f"Find the {target['label']}!",
            "success":f"Yes! That is the {target['label']}! ✅",
            "fail":f"Look for the {target['label']}!",
            "tablet_mode":"object_grid","options":opts,"correct":correct,
            "tokens":4,"joy":"dance"})
    # Cognitive fruits (12%)
    for _ in range(int(n*0.12)):
        target=random.choice(_FRUITS)
        distractors=random.sample([f for f in _FRUITS if f["id"]!=target["id"]],3)
        opts=[target]+distractors; random.shuffle(opts)
        correct=next(i for i,o in enumerate(opts) if o["id"]==target["id"])
        pool.append({"id":f"fruit_{target['id']}","domain":"Cognitive","level":4,
            "name":f"🍎 Find {target['label']}",
            "instruction":f"Click the {target['label']}!",
            "waiting":f"Find the {target['label']}!",
            "success":f"Delicious {target['label']}! ✅",
            "fail":f"Look for the {target['label']}!",
            "tablet_mode":"object_grid","options":opts,"correct":correct,
            "tokens":4,"joy":"celebrate"})
    # Cognitive shapes (8%)
    for _ in range(int(n*0.08)):
        target=random.choice(_SHAPES)
        distractors=random.sample([s for s in _SHAPES if s["id"]!=target["id"]],3)
        opts=[target]+distractors; random.shuffle(opts)
        correct=next(i for i,o in enumerate(opts) if o["id"]==target["id"])
        pool.append({"id":f"shape_{target['id']}","domain":"Cognitive","level":5,
            "name":f"🔷 Find {target['label']}",
            "instruction":f"Click the {target['label']}!",
            "waiting":f"Find the {target['label']}!",
            "success":f"Correct shape! {target['label']}! ✅",
            "fail":f"Look for the {target['label']}!",
            "tablet_mode":"object_grid","options":opts,"correct":correct,
            "tokens":4,"joy":"dance"})
    # Math finger counting (13%)
    for _ in range(int(n*0.13)):
        num=random.choice(_NUMBERS)
        pool.append({"id":f"count_{num}","domain":"Math","level":5,
            "name":f"🔢 Count {num}",
            "instruction":f"Hold up {num} finger{'s' if num>1 else ''}! Show me {num}!",
            "waiting":f"Show me {num} fingers! 🖐️",
            "success":f"Yes! {num} finger{'s' if num>1 else ''}! Amazing! ✅",
            "fail":f"Try again! I need {num} fingers!",
            "tablet_mode":"number_display","target_number":num,
            "verify":"finger_count","tokens":5,"joy":"celebrate"})
    # Verbal (13%)
    for _ in range(int(n*0.13)):
        word=random.choice(_WORDS)
        pool.append({"id":f"say_{word}","domain":"Verbal","level":6,
            "name":f"🗣️ Say '{word}'",
            "instruction":f"Say the word: {word.upper()}!",
            "waiting":f"Say {word}! 🎤",
            "success":f"I heard {word}! Perfect! ✅",
            "fail":f"Try again! Say {word}!",
            "tablet_mode":"word_display","word_emoji":"🗣️",
            "word_text":word.upper(),"verify":"speech_keyword",
            "keyword":word,"tokens":4,"joy":"dance"})
    random.shuffle(pool)
    return pool

print(f"🎲 Generating infinite task pool...")
TASK_POOL = generate_task_pool(2000)
print(f"✅ {len(TASK_POOL)} tasks generated!")

# ═══════════════════════════════════════════════════════════════
# 4. SHARED STATE — clean-slate per run
# ═══════════════════════════════════════════════════════════════
ST={
    "name":CHILD_NAME,"known":True,"age":6,"diagnosis":"ASD Level 2",
    "task_index":0,"consecutive":0,"mastery_needed":MASTERY_N,
    "tasks_mastered":0,"current_level":1,"domain":"Motor","protocol":"ABA-Motor",
    # Tablet
    "tablet_locked":True,"tablet_click_result":None,"tablet_correct":-1,
    "tablet_instruction":"Welcome!",
    # Vision — MediaPipe only
    "emotion":"neutral","face_detected":False,"attention":70,
    "hand_raised":False,"waving":False,"clapping":False,
    "arms_out":False,"hands_up":False,"pointing":False,
    "head_tilted":False,"blinking":False,"eye_contact":False,
    "finger_count":0,
    "pose_landmarks":{},"face_mesh_landmarks":{},
    "verify_action":None,"verify_result":False,"verify_timeout":0.0,
    "last_speech_text":"","last_sound":time.time(),"voice_energy":0.0,
    # Session
    "is_speaking":False,"interrupt_flag":False,
    "listening":False,"waiting_for_child":False,"recording":False,
    "task_success":False,"sim_cmd":None,
    "lip_sync_value":0.0,"gaze_mode":"child",
    "social_joy_active":False,"eye_color":(100,180,255),
    # Micro-animations
    "blink_timer":0.0,"head_tilt_val":0.0,"nose_twitch":0.0,
    # Progress
    "score":0,"tokens":0,"streak":0,
    "tasks_success":0,"tasks_fail":0,
    "session_chat":[],"logs":[],
    "session_start":datetime.now().strftime("%H:%M"),
    "session_date":datetime.now().strftime("%Y-%m-%d"),
    "uptime":time.time(),
    # Celebration
    "show_celebration":False,"celebration_timer":0.0,
}

_log_lock=threading.Lock()
def LOG(msg,t="info"):
    with _log_lock:
        e={"time":datetime.now().strftime("%H:%M:%S"),"msg":str(msg)[:120],"type":t}
        ST["logs"].append(e)
        if len(ST["logs"])>300: ST["logs"]=ST["logs"][-300:]
    print(f"[{datetime.now().strftime('%H:%M:%S')}][{t.upper()}] {msg[:70]}")

# ═══════════════════════════════════════════════════════════════
# 5. TABLET BRIDGE — ALL Qt UI via pyqtSignal
# ═══════════════════════════════════════════════════════════════
class TabletBridge(QObject):
    sig_new_task     = pyqtSignal(dict)
    sig_show_success = pyqtSignal(str)
    sig_show_fail    = pyqtSignal(str)
    sig_set_feedback = pyqtSignal(str)
    sig_set_instr    = pyqtSignal(str)
    sig_set_waiting  = pyqtSignal(str)
    sig_unlock       = pyqtSignal()
    sig_lock         = pyqtSignal()
    sig_reset_cards  = pyqtSignal()
    sig_joy          = pyqtSignal(str)
    sig_update_frame = pyqtSignal(object)   # QImage from camera
    sig_update_stats = pyqtSignal()
    sig_celebration  = pyqtSignal()         # balloons animation
    sig_rec_start    = pyqtSignal()
    sig_rec_stop     = pyqtSignal(str)

BRIDGE=TabletBridge()

# ═══════════════════════════════════════════════════════════════
# 6. CAMERA + MEDIAPIPE THREAD (QThread)
# ═══════════════════════════════════════════════════════════════
class CameraThread(QThread):
    def __init__(self):
        super().__init__()
        self.running=False; self.cap=None
        self._pose=None; self._hands=None; self._face=None
        self._phase=0.0; self._prev_gray=None
        self._hand_hist=[]; self._motion_buf=[]
        self._init_mp(); self._init_cam()

    def _init_mp(self):
        try:
            self._pose=mp.solutions.pose.Pose(
                min_detection_confidence=0.5,min_tracking_confidence=0.5,model_complexity=1)
            print("✅ MP Pose")
        except Exception as e: print(f"⚠️  Pose: {e}")
        try:
            self._hands=mp.solutions.hands.Hands(max_num_hands=2,
                min_detection_confidence=0.6,min_tracking_confidence=0.5)
            print("✅ MP Hands")
        except Exception as e: print(f"⚠️  Hands: {e}")
        try:
            self._face=mp.solutions.face_mesh.FaceMesh(
                max_num_faces=1,min_detection_confidence=0.5,
                min_tracking_confidence=0.5,refine_landmarks=True)
            print("✅ MP FaceMesh")
        except Exception as e: print(f"⚠️  FaceMesh: {e}")

    def _init_cam(self):
        for idx in [1,0,2,3]:
            try:
                c=cv2.VideoCapture(idx)
                if c.isOpened():
                    ret,f=c.read()
                    if ret and f is not None and f.size>0:
                        c.set(cv2.CAP_PROP_FRAME_WIDTH,640)
                        c.set(cv2.CAP_PROP_FRAME_HEIGHT,480)
                        c.set(cv2.CAP_PROP_FPS,30)
                        self.cap=c; print(f"✅ Camera {idx}"); return
                    c.release()
            except: pass
        print("⚠️  No camera — sim mode")

    def _joint_angle(self,a,b,c_):
        try:
            ab=np.array([a.x-b.x,a.y-b.y,a.z-b.z])
            cb=np.array([c_.x-b.x,c_.y-b.y,c_.z-b.z])
            cos_a=np.dot(ab,cb)/(np.linalg.norm(ab)*np.linalg.norm(cb)+1e-6)
            return math.degrees(math.acos(np.clip(cos_a,-1,1)))
        except: return 0.0

    def _count_fingers(self,lm):
        try:
            tips=[8,12,16,20]; count=0
            if lm.landmark[4].x<lm.landmark[3].x: count+=1
            for tip in tips:
                if lm.landmark[tip].y<lm.landmark[tip-2].y: count+=1
            return count
        except: return 0

    def _infer_emotion(self,fm):
        ear=fm.get("ear_avg",0.3); mouth=fm.get("mouth_open",0.02)
        if ear<0.20: return "surprised"
        elif mouth>0.06: return "happy"
        elif mouth>0.04: return "joyful"
        elif ear<0.22 and mouth<0.02: return "sad"
        return "neutral"

    def _validate_motor(self):
        va=ST.get("verify_action")
        if not va: return
        if time.time()>ST["verify_timeout"]: ST["verify_action"]=None; return
        pl=ST.get("pose_landmarks",{}); fm=ST.get("face_mesh_landmarks",{})
        ok=False
        if va=="clap":        ok=ST["clapping"]
        elif va=="wave":      ok=ST["waving"]
        elif va=="raise_hand":
            lwy=pl.get("l_wrist_y",1); rwy=pl.get("r_wrist_y",1)
            lsy=pl.get("l_shoulder_y",0); rsy=pl.get("r_shoulder_y",0)
            lea=pl.get("l_elbow_angle",0); rea=pl.get("r_elbow_angle",0)
            ok=((lwy<lsy-0.08 and lea>120) or (rwy<rsy-0.08 and rea>120))
        elif va=="touch_nose":
            nx=fm.get("nose_x",-1); ny=fm.get("nose_y",-1)
            fw=fm.get("frame_w",640); fh=fm.get("frame_h",480)
            if nx>0 and pl:
                lix=pl.get("l_index_x",0)*fw; liy=pl.get("l_index_y",0)*fh
                rix=pl.get("r_index_x",0)*fw; riy=pl.get("r_index_y",0)*fh
                ok=(math.dist((lix,liy),(nx,ny))<fw*0.12 or
                    math.dist((rix,riy),(nx,ny))<fw*0.12)
        elif va=="arms_out":  ok=ST.get("arms_out",False)
        elif va=="hands_up":  ok=ST.get("hands_up",False)
        elif va=="point":
            if pl:
                rix=pl.get("r_index_x",0); riy=pl.get("r_index_y",0)
                rwy=pl.get("r_wrist_y",1); rwy2=pl.get("r_shoulder_y",0)
                ok=(rix>0.55 and abs(riy-rwy)<0.15)
        elif va=="finger_count":
            target=ST.get("finger_target",1)
            ok=(ST["finger_count"]==target)
        if ok:
            ST["verify_result"]=True; ST["verify_action"]=None
            ST["verify_timeout"]=0.0; LOG("✅ Motor verified!","success")

    def _draw_hud(self,frame):
        h,w=frame.shape[:2]
        ov=frame.copy(); cv2.rectangle(ov,(0,0),(w,58),(8,10,24),-1)
        frame=cv2.addWeighted(ov,0.75,frame,0.25,0)
        tidx=min(ST["task_index"],len(TASK_POOL)-1)
        t=TASK_POOL[tidx]
        cv2.putText(frame,f"Task: {t.get('name',t['id'])}",
            (10,22),cv2.FONT_HERSHEY_SIMPLEX,0.55,(200,200,255),1)
        stars="★"*ST["consecutive"]+"☆"*(3-ST["consecutive"])
        cv2.putText(frame,
            f"★{stars} | Score:{ST['score']} | {CHILD_NAME}",
            (10,44),cv2.FONT_HERSHEY_SIMPLEX,0.50,(255,220,0),1)
        if ST["recording"]:
            cv2.circle(frame,(w-20,20),10,(0,0,255),-1)
            cv2.putText(frame,"REC",(w-50,26),cv2.FONT_HERSHEY_SIMPLEX,0.45,(0,0,255),2)
        fc=ST.get("finger_count",0)
        if fc>0:
            cv2.putText(frame,f"Fingers:{fc}",
                (w-110,h-14),cv2.FONT_HERSHEY_SIMPLEX,0.50,(255,200,0),1)
        for lbl,active,y_ in [
            ("CLAP",ST["clapping"],h-14),("WAVE",ST["waving"],h-30),
            ("HAND↑",ST["hand_raised"],h-46),("ARMS",ST["arms_out"],h-62),]:
            col=(0,255,100) if active else (50,50,70)
            cv2.putText(frame,lbl,(10,y_),cv2.FONT_HERSHEY_SIMPLEX,0.38,col,1)
        return frame

    def _sim_frame(self):
        h,w=480,640; f=np.zeros((h,w,3),dtype=np.uint8); f[:]=(10,12,28)
        self._phase+=0.04
        r=int(30+12*math.sin(self._phase))
        cv2.circle(f,(w//2,h//2-50),r,
            (int(80+80*math.sin(self._phase)),int(120+120*math.cos(self._phase*0.7)),220),3)
        cv2.putText(f,"SIMULATION — NO CAMERA",
            (w//2-170,h//2+20),cv2.FONT_HERSHEY_SIMPLEX,0.70,(100,150,255),2)
        tidx=min(ST["task_index"],len(TASK_POOL)-1)
        cv2.putText(f,TASK_POOL[tidx].get("name","?"),
            (10,h-14),cv2.FONT_HERSHEY_SIMPLEX,0.50,(200,200,200),1)
        return f

    def run(self):
        self.running=True
        while self.running:
            if self.cap and self.cap.isOpened():
                ret,frame=self.cap.read()
                frame=cv2.flip(frame,1) if ret and frame is not None else self._sim_frame()
            else:
                frame=self._sim_frame()

            # Motion
            gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
            gray=cv2.GaussianBlur(gray,(21,21),0)
            if self._prev_gray is not None:
                diff=cv2.absdiff(self._prev_gray,gray)
                _,th=cv2.threshold(diff,25,255,cv2.THRESH_BINARY)
                m=float(np.mean(th)); self._motion_buf.append(m)
                if len(self._motion_buf)>12: self._motion_buf.pop(0)
                if len(self._motion_buf)>=4:
                    avg=sum(self._motion_buf[:-2])/max(len(self._motion_buf)-2,1)
                    ST["clapping"]=(self._motion_buf[-1]>avg*3.5 and self._motion_buf[-1]>15)
                h2,w2=gray.shape
                lm_=float(np.mean(th[:,:w2//2])); rm_=float(np.mean(th[:,w2//2:]))
                self._hand_hist.append("L" if lm_>rm_+3 else "R" if rm_>lm_+3 else "N")
                if len(self._hand_hist)>10: self._hand_hist.pop(0)
                chg=sum(1 for i in range(1,len(self._hand_hist))
                        if self._hand_hist[i]!=self._hand_hist[i-1]
                        and self._hand_hist[i]!="N")
                ST["waving"]=chg>=4
            self._prev_gray=gray

            # Pose
            if self._pose:
                try:
                    rgb=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
                    res=self._pose.process(rgb)
                    if res.pose_landmarks:
                        mp.solutions.drawing_utils.draw_landmarks(
                            frame,res.pose_landmarks,mp.solutions.pose.POSE_CONNECTIONS,
                            mp.solutions.drawing_utils.DrawingSpec(color=(0,255,100),thickness=2,circle_radius=3),
                            mp.solutions.drawing_utils.DrawingSpec(color=(0,150,255),thickness=2))
                        lm=res.pose_landmarks.landmark; PL=mp.solutions.pose.PoseLandmark
                        lsa=self._joint_angle(lm[PL.LEFT_ELBOW],lm[PL.LEFT_SHOULDER],lm[PL.LEFT_HIP])
                        rsa=self._joint_angle(lm[PL.RIGHT_ELBOW],lm[PL.RIGHT_SHOULDER],lm[PL.RIGHT_HIP])
                        lea=self._joint_angle(lm[PL.LEFT_SHOULDER],lm[PL.LEFT_ELBOW],lm[PL.LEFT_WRIST])
                        rea=self._joint_angle(lm[PL.RIGHT_SHOULDER],lm[PL.RIGHT_ELBOW],lm[PL.RIGHT_WRIST])
                        h2,w2=frame.shape[:2]
                        pl={
                            "nose_x":lm[PL.NOSE].x,"nose_y":lm[PL.NOSE].y,
                            "l_ear_x":lm[PL.LEFT_EAR].x,"r_ear_x":lm[PL.RIGHT_EAR].x,
                            "l_shoulder_y":lm[PL.LEFT_SHOULDER].y,"r_shoulder_y":lm[PL.RIGHT_SHOULDER].y,
                            "l_wrist_y":lm[PL.LEFT_WRIST].y,"r_wrist_y":lm[PL.RIGHT_WRIST].y,
                            "l_wrist_x":lm[PL.LEFT_WRIST].x,"r_wrist_x":lm[PL.RIGHT_WRIST].x,
                            "l_index_x":lm[PL.LEFT_INDEX].x,"l_index_y":lm[PL.LEFT_INDEX].y,
                            "r_index_x":lm[PL.RIGHT_INDEX].x,"r_index_y":lm[PL.RIGHT_INDEX].y,
                            "l_elbow_angle":lea,"r_elbow_angle":rea,
                            "l_shoulder_angle":lsa,"r_shoulder_angle":rsa,
                        }
                        ST["pose_landmarks"]=pl
                        ST["hand_raised"]=(pl["l_wrist_y"]<pl["l_shoulder_y"]-0.08 or
                                           pl["r_wrist_y"]<pl["r_shoulder_y"]-0.08)
                        ST["arms_out"]=(lsa>70 and rsa>70)
                        ST["hands_up"]=(pl["l_wrist_y"]<pl["l_shoulder_y"]-0.08 and
                                        pl["r_wrist_y"]<pl["r_shoulder_y"]-0.08)
                        ST["head_tilted"]=(abs(pl["nose_x"]-pl["l_ear_x"])<0.12 or
                                           abs(pl["nose_x"]-pl["r_ear_x"])<0.12)
                        ST["face_detected"]=True
                        ST["attention"]=min(100,ST["attention"]+1)
                        ST["face_mesh_landmarks"].update({
                            "nose_x":lm[PL.NOSE].x*w2,"nose_y":lm[PL.NOSE].y*h2,
                            "frame_w":w2,"frame_h":h2})
                except: pass

            # FaceMesh
            if self._face:
                try:
                    rgb=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
                    fres=self._face.process(rgb)
                    if fres.multi_face_landmarks:
                        fl=fres.multi_face_landmarks[0].landmark
                        h2,w2=frame.shape[:2]
                        re_=[33,160,158,133,153,144]; le_=[362,385,387,263,373,380]
                        def ear(eye_idx):
                            pts=[(fl[i].x*w2,fl[i].y*h2) for i in eye_idx]
                            A=math.dist(pts[1],pts[5]); B=math.dist(pts[2],pts[4])
                            C=math.dist(pts[0],pts[3]); return (A+B)/(2*C) if C>0 else 0.3
                        ear_avg=(ear(re_)+ear(le_))/2.0
                        ST["blinking"]=ear_avg<0.20; ST["eye_contact"]=ear_avg>0.25
                        ul_y=fl[13].y*h2; ll_y=fl[14].y*h2
                        mouth_open=(ll_y-ul_y)/h2
                        fm={"ear_avg":ear_avg,"mouth_open":mouth_open,
                            "nose_x":fl[1].x*w2,"nose_y":fl[1].y*h2,
                            "frame_w":w2,"frame_h":h2}
                        ST["face_mesh_landmarks"].update(fm)
                        ST["emotion"]=self._infer_emotion(fm)
                        # Micro-animation values
                        ST["blink_timer"]=ear_avg
                        ST["head_tilt_val"]=fl[1].x-0.5  # nose offset
                        ST["nose_twitch"]=abs(fl[4].y-fl[1].y)*10
                except: pass

            # Hands + finger count
            if self._hands:
                try:
                    rgb=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
                    hres=self._hands.process(rgb)
                    if hres.multi_hand_landmarks:
                        for hlm in hres.multi_hand_landmarks:
                            mp.solutions.drawing_utils.draw_landmarks(
                                frame,hlm,mp.solutions.hands.HAND_CONNECTIONS,
                                mp.solutions.drawing_utils.DrawingSpec(color=(255,100,0),thickness=2,circle_radius=3),
                                mp.solutions.drawing_utils.DrawingSpec(color=(255,200,0),thickness=2))
                        fc=max(self._count_fingers(h) for h in hres.multi_hand_landmarks)
                        ST["finger_count"]=fc
                        if len(hres.multi_hand_landmarks)>=2:
                            h1=hres.multi_hand_landmarks[0].landmark[0]
                            h2_=hres.multi_hand_landmarks[1].landmark[0]
                            if abs(h1.x-h2_.x)<0.18 and abs(h1.y-h2_.y)<0.18:
                                ST["clapping"]=True
                    else:
                        ST["finger_count"]=0
                except: pass

            self._validate_motor()
            frame=self._draw_hud(frame)

            # Emit to UI
            rgb=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
            h_,w_,ch=rgb.shape
            qi=QImage(rgb.data.tobytes(),w_,h_,w_*ch,QImage.Format.Format_RGB888)
            BRIDGE.sig_update_frame.emit(qi)
            self.msleep(16)  # ~60 fps

    def stop(self):
        self.running=False; self.quit(); self.wait(2000)
        if self.cap: self.cap.release()

# ═══════════════════════════════════════════════════════════════
# 7. TOUCH RECORDER — only on button press
# ═══════════════════════════════════════════════════════════════
class TouchRecorder:
    def __init__(self):
        self._lock=threading.Lock(); self._recording=False; self._audio=None
        self.whisper=None
        self.r=sr.Recognizer()
        self.r.energy_threshold=MIC_ENERGY
        self.r.dynamic_energy_threshold=True
        self.r.pause_threshold=0.7; self.r.phrase_threshold=0.05
        try:
            with sr.Microphone() as src:
                self.r.adjust_for_ambient_noise(src,duration=0.5)
            print(f"✅ Mic energy={self.r.energy_threshold:.0f}")
        except Exception as e: print(f"⚠️  Mic: {e}")
        if WHISPER_OK:
            try:
                device="cuda" if os.path.exists("/dev/nvidia0") else "cpu"
                self.whisper=WhisperModel("tiny",device=device,
                    compute_type="float16" if device=="cuda" else "int8")
                print(f"✅ faster-whisper ({device})")
            except Exception as e: print(f"⚠️  Whisper: {e}")

    def start(self):
        with self._lock:
            if self._recording: return
            self._recording=True; self._audio=None
        ST["recording"]=True
        BRIDGE.sig_rec_start.emit()
        threading.Thread(target=self._capture,daemon=True).start()
        LOG("🎤 Recording start","info")

    def _capture(self):
        try:
            with sr.Microphone() as src:
                self.r.adjust_for_ambient_noise(src,duration=0.08)
                audio=self.r.listen(src,timeout=10,phrase_time_limit=8)
                with self._lock: self._audio=audio
        except: pass
        finally:
            with self._lock: self._recording=False
            ST["recording"]=False

    def stop_and_recognise(self)->str:
        for _ in range(25):
            with self._lock:
                if not self._recording: break
            time.sleep(0.05)
        with self._lock: audio=self._audio
        if not audio: return ""
        if self.whisper:
            try:
                raw=audio.get_raw_data(convert_rate=16000,convert_width=2)
                with tempfile.NamedTemporaryFile(suffix=".wav",delete=False) as tmp:
                    tp=tmp.name
                with wave.open(tp,"wb") as wf:
                    wf.setnchannels(1); wf.setsampwidth(2)
                    wf.setframerate(16000); wf.writeframes(raw)
                segs,_=self.whisper.transcribe(tp,language="en",beam_size=1)
                text=" ".join(s.text.strip() for s in segs).strip()
                os.unlink(tp)
                if text: LOG(f"Whisper: {text}","info"); return text
            except Exception as e: LOG(f"Whisper err: {e}","warn")
        try:
            text=self.r.recognize_google(audio); LOG(f"Google SR: {text}","info"); return text
        except: return ""

# ═══════════════════════════════════════════════════════════════
# 8. VOICE (TTS + lip-sync)
# ═══════════════════════════════════════════════════════════════
class Voice:
    def __init__(self):
        self.ok=False; self._lk=threading.Lock()
        try:
            self.e=pyttsx3.init(); self.e.setProperty('rate',116)
            self.e.setProperty('volume',1.0)
            for v in self.e.getProperty('voices'):
                if any(x in v.name.lower() for x in ['female','zira','hazel','karen']):
                    self.e.setProperty('voice',v.id); break
            self.ok=True; print("✅ TTS Voice")
        except Exception as ex: print(f"⚠️  TTS: {ex}")

    def _lip_thread(self,text):
        for word in text.split():
            if not ST["is_speaking"]: break
            d=max(0.07,len(word)/13.0)
            ST["lip_sync_value"]=min(1.0,0.5+random.uniform(0.1,0.45))
            time.sleep(d*0.55)
            ST["lip_sync_value"]=max(0.05,ST["lip_sync_value"]*0.35)
            time.sleep(d*0.45)
        ST["lip_sync_value"]=0.0

    def say(self,text,wait=True):
        ST["interrupt_flag"]=False
        clean=re.sub(r'\[[^\]]+\]','',str(text)).strip()
        if not clean: return
        ST["is_speaking"]=True
        ST["session_chat"].append({"role":"pepper","text":clean,
            "time":datetime.now().strftime("%H:%M:%S")})
        if len(ST["session_chat"])>50: ST["session_chat"]=ST["session_chat"][-50:]
        print(f"\n🔊 Pepper: {clean}")
        threading.Thread(target=self._lip_thread,args=(clean,),daemon=True).start()
        if self.ok and not ST["interrupt_flag"]:
            with self._lk:
                try: self.e.say(clean); self.e.runAndWait()
                except: pass
        ST["is_speaking"]=False; ST["lip_sync_value"]=0.0
        if wait: ST["waiting_for_child"]=True; time.sleep(0.2)

    def stop(self):
        ST["interrupt_flag"]=True; ST["is_speaking"]=False; ST["lip_sync_value"]=0.0
        if self.ok:
            try: self.e.stop()
            except: pass

# ═══════════════════════════════════════════════════════════════
# 9. CLICK CARDS — instant response (PyQt6)
# ═══════════════════════════════════════════════════════════════
class ClickCard(QPushButton):
    def __init__(self,data,idx,mode,parent=None):
        super().__init__(parent)
        self.idx=idx; self.mode=mode; self._data=data
        self.setFixedSize(155,155); self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._set_normal()
        # INSTANT response — direct connection, no lambda delay
        self.clicked.connect(self._instant_click)

    def _instant_click(self):
        """Zero-lag click: immediately emit to bridge"""
        BRIDGE.sig_new_task.emit({"action":"click","idx":self.idx})

    def _set_normal(self):
        d=self._data; m=self.mode
        if m=="color_grid":
            self.setText(f"\n\n{d['label']}")
            self.setFont(QFont("Arial",12,QFont.Weight.Bold))
            self.setStyleSheet(f"""QPushButton{{background:{d['color']};
                border-radius:77px;border:5px solid rgba(255,255,255,0.3);
                color:white;font-weight:bold;
                text-shadow:1px 1px 4px rgba(0,0,0,0.9);}}
                QPushButton:hover{{border:5px solid white;}}""")
        elif m in ["object_grid","shape_grid","emotion_grid"]:
            self.setText(f"{d['emoji']}\n{d['label']}")
            self.setFont(QFont("Arial",13,QFont.Weight.Bold))
            self.setStyleSheet("""QPushButton{background:qlineargradient(
                x1:0,y1:0,x2:0,y2:1,stop:0 #1e1b4b,stop:1 #0c0f2e);
                border-radius:20px;border:4px solid #4f46e5;
                color:#e0e6ff;font-weight:bold;padding:8px;}
                QPushButton:hover{border:4px solid #a78bfa;}""")
        elif m=="number_grid":
            colors=["#6366f1","#ec4899","#f59e0b","#10b981"]
            c=colors[self.idx%len(colors)]
            self.setText(f"{d['num']}\n{d['label']}")
            self.setFont(QFont("Arial",30,QFont.Weight.Bold))
            self.setStyleSheet(f"""QPushButton{{background:qlineargradient(
                x1:0,y1:0,x2:1,y2:1,stop:0 {c}aa,stop:1 {c}55);
                border-radius:20px;border:4px solid {c};
                color:white;font-weight:bold;}}
                QPushButton:hover{{border:5px solid white;}}""")

    def flash_correct(self):
        base=self.styleSheet().split("QPushButton:hover")[0]
        self.setStyleSheet(base+"QPushButton{border:8px solid #22c55e !important;}")
    def flash_wrong(self):
        base=self.styleSheet().split("QPushButton:hover")[0]
        self.setStyleSheet(base+"QPushButton{border:8px solid #ef4444 !important;opacity:0.45;}")
    def reset(self): self._set_normal()

# ═══════════════════════════════════════════════════════════════
# 10. BALLOON WIDGET — floating celebration animation
# ═══════════════════════════════════════════════════════════════
class BalloonWidget(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._balloons=[]
        self._timer=QTimer(); self._timer.timeout.connect(self._update)
        self.hide()

    def launch(self,duration_ms=3000):
        pw=self.parent()
        if pw: self.setGeometry(pw.rect())
        self._balloons=[{
            "x":random.randint(50,600),"y":random.randint(600,800),
            "vx":random.uniform(-1.5,1.5),"vy":random.uniform(-4,-2),
            "color":random.choice(["#ef4444","#3b82f6","#22c55e","#fbbf24",
                                   "#a855f7","#ec4899","#f97316"]),
            "r":random.randint(22,40),
            "emoji":random.choice(["🎈","🎉","⭐","🌟","🎊","✨"])
        } for _ in range(20)]
        self.show(); self.raise_()
        self._timer.start(30)
        QTimer.singleShot(duration_ms,self._stop)

    def _update(self):
        for b in self._balloons:
            b["x"]+=b["vx"]; b["y"]+=b["vy"]; b["vy"]*=0.98
            b["vx"]+=random.uniform(-0.2,0.2)
        self._balloons=[b for b in self._balloons if b["y"]>-80]
        self.update()
        if not self._balloons: self._stop()

    def paintEvent(self,e):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        for b in self._balloons:
            col=QColor(b["color"])
            col.setAlpha(200); p.setBrush(col); p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(int(b["x"]-b["r"]),int(b["y"]-b["r"]),b["r"]*2,b["r"]*2)
            p.setPen(QColor(b["color"]).darker(140))
            p.drawLine(int(b["x"]),int(b["y"]+b["r"]),int(b["x"]+random.randint(-6,6)),int(b["y"]+b["r"]+18))
        p.end()

    def _stop(self):
        self._timer.stop(); self.hide(); self._balloons=[]

# ═══════════════════════════════════════════════════════════════
# 11. TABLET WINDOW — PyQt6, FIXED 1280×780
#     Left: camera feed | Right: task UI
# ═══════════════════════════════════════════════════════════════
class TabletWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Pepper Clinical Infinity — {CHILD_NAME}")
        self.setFixedSize(1280,780)
        self.setWindowFlags(Qt.WindowType.Window|
            Qt.WindowType.WindowStaysOnTopHint|
            Qt.WindowType.CustomizeWindowHint|
            Qt.WindowType.WindowTitleHint)
        self._cards=[]; self._locked=True; self._correct_idx=-1
        self._joy_phase=0.0
        self._joy_timer=QTimer(); self._joy_timer.timeout.connect(self._joy_tick)
        self._recorder=TouchRecorder()
        self._setup_ui()
        self._connect_bridge()
        self._stats_t=QTimer(); self._stats_t.timeout.connect(self._refresh_stats)
        self._stats_t.start(400)

    def _setup_ui(self):
        root=QWidget(); self.setCentralWidget(root)
        root.setStyleSheet("QWidget{background:#060918;}")
        main=QHBoxLayout(root); main.setSpacing(0); main.setContentsMargins(0,0,0,0)

        # ── LEFT: Camera 640×480 ──────────────────────────
        cf=QFrame(); cf.setFixedWidth(640)
        cf.setStyleSheet("QFrame{background:#0a0d1e;border-right:2px solid #1a1f40;}")
        cl=QVBoxLayout(cf); cl.setContentsMargins(0,0,0,0)
        self.cam_lbl=QLabel(); self.cam_lbl.setFixedSize(640,480)
        self.cam_lbl.setStyleSheet("background:#000;")
        self.cam_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cl.addWidget(self.cam_lbl)
        # Finger count
        self.finger_lbl=QLabel("✋ Fingers: 0")
        self.finger_lbl.setFont(QFont("Arial",15,QFont.Weight.Bold))
        self.finger_lbl.setStyleSheet("color:#fbbf24;padding:6px;")
        self.finger_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cl.addWidget(self.finger_lbl)
        # Rec status
        self.rec_status=QLabel("🎤 TAP MIC TO SPEAK")
        self.rec_status.setFont(QFont("Arial",10,QFont.Weight.Bold))
        self.rec_status.setStyleSheet("color:#6b7280;padding:2px;")
        self.rec_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cl.addWidget(self.rec_status)
        # Session chat preview
        self.chat_lbl=QLabel("")
        self.chat_lbl.setFont(QFont("Arial",8))
        self.chat_lbl.setStyleSheet("color:#4b5563;padding:4px;")
        self.chat_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignTop)
        self.chat_lbl.setWordWrap(True)
        cl.addWidget(self.chat_lbl)
        cl.addStretch()
        main.addWidget(cf)

        # ── RIGHT: Task panel ─────────────────────────────
        tf=QWidget(); tf.setFixedWidth(640)
        tl=QVBoxLayout(tf); tl.setSpacing(5); tl.setContentsMargins(10,6,10,6)

        # Header
        hdr=QFrame(); hdr.setFixedHeight(72)
        hdr.setStyleSheet("""QFrame{background:qlineargradient(
            x1:0,y1:0,x2:1,y2:0,stop:0 #1a0a3d,stop:0.5 #0a0f28,stop:1 #1a0a3d);
            border-radius:13px;border:2px solid #4f46e5;}""")
        hl=QHBoxLayout(hdr); hl.setContentsMargins(12,4,12,4)
        self.av_lbl=QLabel("🤖")
        self.av_lbl.setFont(QFont("Arial",26)); self.av_lbl.setStyleSheet("color:#a78bfa;")
        hl.addWidget(self.av_lbl)
        tw_=QWidget(); tl2=QVBoxLayout(tw_); tl2.setSpacing(1)
        self.title_lbl=QLabel("PEPPER CLINICAL INFINITY")
        self.title_lbl.setFont(QFont("Arial",12,QFont.Weight.Bold))
        self.title_lbl.setStyleSheet("color:#a78bfa;")
        tl2.addWidget(self.title_lbl)
        self.child_lbl=QLabel(f"Child: {CHILD_NAME}")
        self.child_lbl.setFont(QFont("Arial",8)); self.child_lbl.setStyleSheet("color:#60a5fa;")
        tl2.addWidget(self.child_lbl)
        hl.addWidget(tw_,1)
        sw_=QWidget(); sl_=QVBoxLayout(sw_); sl_.setSpacing(1)
        self.state_lbl=QLabel("💤 Ready")
        self.state_lbl.setFont(QFont("Arial",8)); self.state_lbl.setStyleSheet("color:#9ca3af;")
        sl_.addWidget(self.state_lbl,alignment=Qt.AlignmentFlag.AlignRight)
        self.ai_lbl=QLabel("● AI")
        self.ai_lbl.setFont(QFont("Arial",8,QFont.Weight.Bold))
        self.ai_lbl.setStyleSheet("color:#34d399;")
        sl_.addWidget(self.ai_lbl,alignment=Qt.AlignmentFlag.AlignRight)
        self.csv_lbl=QLabel(f"📊 {CSV_FILE}")
        self.csv_lbl.setFont(QFont("Arial",7)); self.csv_lbl.setStyleSheet("color:#6b7280;")
        sl_.addWidget(self.csv_lbl,alignment=Qt.AlignmentFlag.AlignRight)
        hl.addWidget(sw_)
        tl.addWidget(hdr)

        # TEACCH schedule
        sched=QFrame(); sched.setFixedHeight(52)
        sched.setStyleSheet("QFrame{background:#0c0f1e;border-radius:11px;border:1px solid #1a1f40;}")
        sc=QHBoxLayout(sched); sc.setContentsMargins(10,5,10,5); sc.setSpacing(7)
        self.sched_task=QLabel("📋 Task")
        self.sched_task.setFont(QFont("Arial",9,QFont.Weight.Bold))
        self.sched_task.setStyleSheet(
            "color:#a78bfa;background:#1e1b4b;border-radius:7px;padding:3px 8px;border:2px solid #4f46e5;")
        sc.addWidget(self.sched_task)
        sc.addWidget(self._arr())
        sw2=QWidget(); sl2_=QVBoxLayout(sw2); sl2_.setSpacing(0); sl2_.setContentsMargins(0,0,0,0)
        self.stars_lbl=QLabel("☆ ☆ ☆")
        self.stars_lbl.setFont(QFont("Arial",16)); self.stars_lbl.setStyleSheet("color:#4b5563;")
        self.stars_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter); sl2_.addWidget(self.stars_lbl)
        self.mastery_sub=QLabel("0 / 3")
        self.mastery_sub.setFont(QFont("Arial",7)); self.mastery_sub.setStyleSheet("color:#6b7280;")
        self.mastery_sub.setAlignment(Qt.AlignmentFlag.AlignCenter); sl2_.addWidget(self.mastery_sub)
        sc.addWidget(sw2,1)
        sc.addWidget(self._arr())
        self.reward_lbl=QLabel("⭐")
        self.reward_lbl.setFont(QFont("Arial",20))
        self.reward_lbl.setStyleSheet(
            "color:#fbbf24;background:#2a1a00;border-radius:7px;padding:2px 8px;border:2px solid #f59e0b;")
        sc.addWidget(self.reward_lbl)
        tl.addWidget(sched)

        # Instruction
        if_fr=QFrame(); if_fr.setFixedHeight(80)
        if_fr.setStyleSheet("""QFrame{background:qlineargradient(
            x1:0,y1:0,x2:0,y2:1,stop:0 #1e1b4b,stop:1 #0c0f2e);
            border-radius:12px;border:2px solid #4f46e5;}""")
        il=QVBoxLayout(if_fr); il.setContentsMargins(12,4,12,4)
        self.instr_icon=QLabel("📋")
        self.instr_icon.setFont(QFont("Arial",16))
        self.instr_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        il.addWidget(self.instr_icon)
        self.instr_lbl=QLabel("Getting ready...")
        self.instr_lbl.setFont(QFont("Arial",13,QFont.Weight.Bold))
        self.instr_lbl.setStyleSheet("color:#e0e6ff;")
        self.instr_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.instr_lbl.setWordWrap(True)
        il.addWidget(self.instr_lbl)
        tl.addWidget(if_fr)

        # Content area
        self.content_fr=QFrame()
        self.content_fr.setMinimumHeight(275)
        self.content_fr.setStyleSheet("""QFrame{background:rgba(12,15,30,0.90);
            border-radius:14px;border:2px solid #1a1f40;}""")
        self.content_lay=QVBoxLayout(self.content_fr)
        self.content_lay.setContentsMargins(12,12,12,12)
        self.content_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._show_idle()
        tl.addWidget(self.content_fr,1)

        # Feedback
        fb_fr=QFrame(); fb_fr.setFixedHeight(52)
        fb_fr.setStyleSheet("QFrame{background:#0c0f1e;border-radius:11px;border:1px solid #1a1f40;}")
        fl=QHBoxLayout(fb_fr); fl.setContentsMargins(12,6,12,6)
        self.fb_icon=QLabel("💤"); self.fb_icon.setFont(QFont("Arial",20)); fl.addWidget(self.fb_icon)
        self.fb_lbl=QLabel("Waiting for Pepper...")
        self.fb_lbl.setFont(QFont("Arial",11,QFont.Weight.Bold))
        self.fb_lbl.setStyleSheet("color:#9ca3af;"); self.fb_lbl.setWordWrap(True)
        fl.addWidget(self.fb_lbl,1)
        tl.addWidget(fb_fr)

        # MIC BUTTON
        self.mic_btn=QPushButton("🎤  TOUCH & HOLD TO SPEAK")
        self.mic_btn.setFixedHeight(60)
        self.mic_btn.setFont(QFont("Arial",14,QFont.Weight.Bold))
        self.mic_btn.setStyleSheet("""
        QPushButton{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,
            stop:0 #dc2626,stop:1 #ef4444);
            color:white;border-radius:30px;border:3px solid #fca5a5;}
        QPushButton:pressed{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,
            stop:0 #991b1b,stop:1 #dc2626);border:4px solid white;}""")
        self.mic_btn.pressed.connect(self._on_mic_press)
        self.mic_btn.released.connect(self._on_mic_release)
        tl.addWidget(self.mic_btn)

        # Stats bar
        sb=QFrame(); sb.setFixedHeight(42)
        sb.setStyleSheet("QFrame{background:#07090f;border-radius:9px;border:1px solid #1a1f40;}")
        stl=QHBoxLayout(sb); stl.setContentsMargins(10,3,10,3)
        for label,attr,color in [
            ("Score","stat_score","#a78bfa"),("Tokens","stat_tokens","#fbbf24"),
            ("Mastered","stat_mastered","#34d399"),("Streak","stat_streak","#60a5fa"),
            ("Domain","stat_domain","#60a5fa"),
        ]:
            w_=QWidget(); wl_=QVBoxLayout(w_); wl_.setSpacing(0); wl_.setContentsMargins(0,0,0,0)
            val=QLabel("0"); val.setFont(QFont("Arial",10,QFont.Weight.Bold))
            val.setStyleSheet(f"color:{color};"); val.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lb_=QLabel(label); lb_.setFont(QFont("Arial",6))
            lb_.setStyleSheet("color:#6b7280;"); lb_.setAlignment(Qt.AlignmentFlag.AlignCenter)
            wl_.addWidget(val); wl_.addWidget(lb_); stl.addWidget(w_)
            setattr(self,attr,val)
        tl.addWidget(sb)
        main.addWidget(tf)

        # Lock overlay
        self.lock_ov=QLabel("🔒")
        self.lock_ov.setParent(self.content_fr)
        self.lock_ov.setGeometry(0,0,616,275)
        self.lock_ov.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lock_ov.setFont(QFont("Arial",48))
        self.lock_ov.setStyleSheet(
            "QLabel{background:rgba(0,0,0,0.52);border-radius:14px;color:#a78bfa;}")
        self.lock_ov.hide()

        # Balloon widget
        self.balloons=BalloonWidget(root)

    def _arr(self):
        a=QLabel("▶"); a.setFont(QFont("Arial",12)); a.setStyleSheet("color:#4f46e5;"); return a

    def _show_idle(self):
        self._clear_content()
        d=QLabel("🤖\nPepper is preparing your task...")
        d.setFont(QFont("Arial",14)); d.setStyleSheet("color:#6b7280;")
        d.setAlignment(Qt.AlignmentFlag.AlignCenter); self.content_lay.addWidget(d)

    def _clear_content(self):
        while self.content_lay.count():
            item=self.content_lay.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        self._cards.clear()

    def _connect_bridge(self):
        BRIDGE.sig_new_task.connect(self._on_new_task)
        BRIDGE.sig_show_success.connect(self._on_success_overlay)
        BRIDGE.sig_show_fail.connect(self._on_fail_overlay)
        BRIDGE.sig_set_feedback.connect(self._set_feedback)
        BRIDGE.sig_set_instr.connect(self._set_instr)
        BRIDGE.sig_set_waiting.connect(self._set_waiting)
        BRIDGE.sig_unlock.connect(self._do_unlock)
        BRIDGE.sig_lock.connect(self._do_lock)
        BRIDGE.sig_reset_cards.connect(self._reset_cards)
        BRIDGE.sig_joy.connect(self._on_joy)
        BRIDGE.sig_update_frame.connect(self._update_camera)
        BRIDGE.sig_update_stats.connect(self._refresh_stats)
        BRIDGE.sig_celebration.connect(self._on_celebration)
        BRIDGE.sig_rec_start.connect(self._on_rec_start)
        BRIDGE.sig_rec_stop.connect(self._on_rec_stop)

    def _update_camera(self,qimg):
        if isinstance(qimg,QImage):
            pix=QPixmap.fromImage(qimg).scaled(
                640,480,Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation)
            self.cam_lbl.setPixmap(pix)
        fc=ST.get("finger_count",0)
        self.finger_lbl.setText(f"Fingers: {fc}  {'☝'*fc if fc>0 else '—'}")
        # Chat preview
        recent=ST["session_chat"][-4:]
        lines=[]
        for m in recent:
            pfx="🤖" if m["role"]=="pepper" else f"👦"
            lines.append(f"{pfx} {m['text'][:40]}")
        self.chat_lbl.setText("\n".join(lines))

    def _refresh_stats(self):
        self.stat_score.setText(str(ST["score"]))
        self.stat_tokens.setText(str(ST["tokens"]))
        self.stat_mastered.setText(str(ST["tasks_mastered"]))
        self.stat_streak.setText(str(ST["streak"]))
        self.stat_domain.setText(ST["domain"][:8])
        self.child_lbl.setText(f"Child: {ST['name']}")
        n=ST["consecutive"]
        self.stars_lbl.setText("⭐"*n+"☆"*(3-n) if n else "☆ ☆ ☆")
        self.mastery_sub.setText(f"{n} / 3")
        sc={0:"#4b5563",1:"#d97706",2:"#fbbf24",3:"#f59e0b"}
        self.stars_lbl.setStyleSheet(f"color:{sc.get(n,'#4b5563')};")
        tidx=min(ST["task_index"],len(TASK_POOL)-1)
        t=TASK_POOL[tidx]
        self.sched_task.setText(f"📋 {t.get('name',t['id'])[:20]}")
        if ST["is_speaking"]:
            self.fb_icon.setText("🔊"); self.state_lbl.setText("🔊 Speaking")
            self.fb_lbl.setStyleSheet("color:#60a5fa;")
        elif ST["recording"]:
            self.fb_icon.setText("🔴"); self.state_lbl.setText("🎤 Recording")
        elif ST["listening"]:
            self.fb_icon.setText("👂"); self.state_lbl.setText("👂 Listening")
        elif ST["waiting_for_child"]:
            self.fb_icon.setText("⏳"); self.state_lbl.setText("⏳ Waiting")
        else:
            self.fb_icon.setText("💤"); self.state_lbl.setText("💤 Ready")

    # ── TASK DISPLAY ────────────────────────────────────────
    def _on_new_task(self,data):
        action=data.get("action","")
        if action=="click": self._handle_click(data.get("idx",-1)); return
        mode=data.get("mode","idle")
        instr=data.get("instruction","")
        self.instr_lbl.setText(instr)
        self.fb_lbl.setText("Your turn! Touch to answer!")
        self.fb_lbl.setStyleSheet("color:#60a5fa;")
        self._build_content(data); self._do_unlock()

    def _build_content(self,data):
        self._clear_content(); mode=data.get("mode","idle")
        if mode=="idle": self._show_idle(); return
        if mode=="motor_model":
            vw=QWidget(); vl=QVBoxLayout(vw); vl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            fig=data.get("figure","")
            if fig and "base64," in fig:
                raw=base64.b64decode(fig.split(",",1)[1])
                qi=QImage(); qi.loadFromData(raw)
                pix=QPixmap.fromImage(qi).scaled(230,230,
                    Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation)
                fl=QLabel(); fl.setPixmap(pix); fl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                vl.addWidget(fl)
            lb=QLabel(data.get("label",""))
            lb.setFont(QFont("Arial",15,QFont.Weight.Bold))
            lb.setStyleSheet("color:#a78bfa;"); lb.setAlignment(Qt.AlignmentFlag.AlignCenter)
            vl.addWidget(lb)
            ar=QLabel("👇 NOW YOU DO IT! 👇")
            ar.setFont(QFont("Arial",12,QFont.Weight.Bold))
            ar.setStyleSheet("color:#34d399;"); ar.setAlignment(Qt.AlignmentFlag.AlignCenter)
            vl.addWidget(ar)
            self.content_lay.addWidget(vw); return
        if mode=="word_display":
            wf=QFrame(); wf.setStyleSheet("""QFrame{background:qlineargradient(
                x1:0,y1:0,x2:0,y2:1,stop:0 #1e1b4b,stop:1 #0c0f1e);
                border-radius:18px;border:3px solid #4f46e5;min-height:150px;}""")
            wfl=QVBoxLayout(wf); wfl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            el=QLabel(data.get("emoji","📢")); el.setFont(QFont("Arial",50))
            el.setAlignment(Qt.AlignmentFlag.AlignCenter); wfl.addWidget(el)
            wl=QLabel(data.get("word","SAY IT!"))
            wl.setFont(QFont("Arial",32,QFont.Weight.Bold))
            wl.setStyleSheet("color:#a78bfa;"); wl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            wfl.addWidget(wl)
            hl=QLabel("🎤 Tap mic and say it!")
            hl.setFont(QFont("Arial",11)); hl.setStyleSheet("color:#6b7280;")
            hl.setAlignment(Qt.AlignmentFlag.AlignCenter); wfl.addWidget(hl)
            self.content_lay.addWidget(wf); return
        if mode=="number_display":
            nf=QFrame(); nf.setStyleSheet("""QFrame{background:qlineargradient(
                x1:0,y1:0,x2:0,y2:1,stop:0 #1a3320,stop:1 #0c1a10);
                border-radius:18px;border:3px solid #22c55e;min-height:150px;}""")
            nfl=QVBoxLayout(nf); nfl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            nl=QLabel(str(data.get("target_number","?")))
            nl.setFont(QFont("Arial",72,QFont.Weight.Bold))
            nl.setStyleSheet("color:#34d399;"); nl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            nfl.addWidget(nl)
            hl=QLabel("Show me with your fingers! 🖐️")
            hl.setFont(QFont("Arial",13)); hl.setStyleSheet("color:#6b7280;")
            hl.setAlignment(Qt.AlignmentFlag.AlignCenter); nfl.addWidget(hl)
            self.content_lay.addWidget(nf); return
        # Grid tasks
        opts=data.get("options",[]); self._correct_idx=data.get("correct",-1)
        gw=QWidget(); grid=QGridLayout(gw); grid.setSpacing(10)
        grid.setAlignment(Qt.AlignmentFlag.AlignCenter)
        for i,opt in enumerate(opts):
            card=ClickCard(opt,i,mode); self._cards.append(card)
            grid.addWidget(card,i//2,i%2,Qt.AlignmentFlag.AlignCenter)
        self.content_lay.addWidget(gw)

    def _handle_click(self,idx):
        """INSTANT response — called on main thread via signal"""
        if self._locked: return
        correct=self._correct_idx
        if correct==-1:  # free choice
            ST["tablet_click_result"]="correct"
            if idx<len(self._cards): self._cards[idx].flash_correct()
            self.fb_lbl.setText("✅ Great choice!")
            self.fb_lbl.setStyleSheet("color:#34d399;")
            self._do_lock(); LOG(f"Free click {idx}","success"); return
        if idx==correct:
            ST["tablet_click_result"]="correct"
            if idx<len(self._cards): self._cards[idx].flash_correct()
            LOG(f"CORRECT idx={idx}","success")
        else:
            ST["tablet_click_result"]="wrong"
            if idx<len(self._cards): self._cards[idx].flash_wrong()
            if 0<=correct<len(self._cards): self._cards[correct].flash_correct()
            LOG(f"WRONG idx={idx}","fail")
        self._do_lock()

    # ── SUCCESS / FAIL overlays ─────────────────────────────
    def _on_success_overlay(self,msg):
        self._clear_content()
        ov=QWidget(); ol=QVBoxLayout(ov); ol.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ck=QLabel("✅"); ck.setFont(QFont("Arial",110))
        ck.setAlignment(Qt.AlignmentFlag.AlignCenter); ol.addWidget(ck)
        ml=QLabel(msg); ml.setFont(QFont("Arial",14,QFont.Weight.Bold))
        ml.setStyleSheet("color:#34d399;"); ml.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ml.setWordWrap(True); ol.addWidget(ml)
        self.content_lay.addWidget(ov)
        self.fb_lbl.setText(msg); self.fb_lbl.setStyleSheet("color:#34d399;font-size:14px;")
        self.instr_icon.setText("✅")
        QTimer.singleShot(2500,self._show_idle)
        QTimer.singleShot(2500,lambda: self.instr_icon.setText("📋"))

    def _on_fail_overlay(self,msg):
        self.fb_lbl.setText(f"❌ {msg}"); self.fb_lbl.setStyleSheet("color:#f87171;font-size:13px;")
        self.instr_icon.setText("❌")
        QTimer.singleShot(2000,lambda: self.instr_icon.setText("📋"))
        QTimer.singleShot(2000,lambda: self.fb_lbl.setStyleSheet("color:#9ca3af;"))

    def _on_celebration(self):
        """Launch balloon animation"""
        self.balloons.launch(3500)

    def _on_joy(self,jtype):
        self._joy_phase=0.0; self._joy_timer.start(55)
        msgs={"dance":"🕺 DANCE! 🎉","celebrate":"🎊 AMAZING! ⭐",
              "wave_back":"👋 HIGH FIVE! 🌟","full_joy":"🏆 CHAMPION! 🎉🌟"}
        self.fb_lbl.setText(msgs.get(jtype,"🌟 AMAZING! 🎉"))
        self.fb_lbl.setStyleSheet("color:#fbbf24;font-size:15px;")
        QTimer.singleShot(3000,self._end_joy)

    def _joy_tick(self):
        self._joy_phase+=0.22
        ems=["🎉","🌟","⭐","🏆","✨","🎊","💫","🎈","🌈"]
        self.av_lbl.setText(ems[int(self._joy_phase)%len(ems)])
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
    def _set_instr(self,txt):    self.instr_lbl.setText(txt)
    def _set_waiting(self,txt):
        self.fb_lbl.setText(txt); self.fb_lbl.setStyleSheet("color:#fbbf24;")
        self.fb_icon.setText("⏳")
    def _reset_cards(self):
        for c in self._cards: c.reset()
        ST["tablet_click_result"]=None

    # ── MIC BUTTON (touch-to-record) ─────────────────────────
    def _on_mic_press(self):
        self.rec_status.setText("🔴 RECORDING... RELEASE TO STOP")
        self.rec_status.setStyleSheet("color:#ef4444;font-size:11px;font-weight:bold;padding:2px;")
        self.mic_btn.setText("🔴  RECORDING... RELEASE TO STOP")
        self._recorder.start()

    def _on_mic_release(self):
        self.mic_btn.setText("🎤  TOUCH & HOLD TO SPEAK")
        self.rec_status.setText("⏳ Processing speech...")
        self.rec_status.setStyleSheet("color:#fbbf24;padding:2px;")
        threading.Thread(target=self._do_recognise,daemon=True).start()

    def _do_recognise(self):
        text=self._recorder.stop_and_recognise()
        BRIDGE.sig_rec_stop.emit(text)

    def _on_rec_start(self): pass

    def _on_rec_stop(self,text):
        if text:
            self.rec_status.setText(f"✅ Heard: \"{text[:30]}\"")
            self.rec_status.setStyleSheet("color:#34d399;font-size:10px;padding:2px;")
            ST["last_speech_text"]=text; ST["last_sound"]=time.time()
            ST["session_chat"].append({"role":"child","text":text,
                "time":datetime.now().strftime("%H:%M:%S")})
            if len(ST["session_chat"])>50: ST["session_chat"]=ST["session_chat"][-50:]
            LOG(f"Heard: {text}","info")
        else:
            self.rec_status.setText("❌ Could not hear — try again!")
            self.rec_status.setStyleSheet("color:#f87171;padding:2px;")
        QTimer.singleShot(3000,lambda: self.rec_status.setText("🎤 TAP MIC TO SPEAK"))
        QTimer.singleShot(3000,lambda: self.rec_status.setStyleSheet("color:#6b7280;padding:2px;"))

# ═══════════════════════════════════════════════════════════════
# 12. PYBULLET SIMULATOR (Window 1)
#     Lip-sync + blink + head-tilt + nose-twitch
# ═══════════════════════════════════════════════════════════════
class PepperSim:
    def __init__(self):
        self.pepper=None; self.ok=False
        self.rx=self.ry=0.0; self.balloons=[]

    def launch(self):
        try:
            from qibullet import SimulationManager as QS
            import pybullet as p, pybullet_data
            self.p=p; self.qisim=QS()
            self.client=self.qisim.launchSimulation(gui=True)
            p.setRealTimeSimulation(1); p.setGravity(0,0,-9.81)
            p.setAdditionalSearchPath(pybullet_data.getDataPath())
            p.loadURDF("plane.urdf"); self._build_room(p)
            self.pepper=self.qisim.spawnPepper(self.client)
            self.pepper.goToPosture("Stand",0.5)
            p.resetDebugVisualizerCamera(6,45,-30,[0,0,0.8])
            self.ok=True
            for fn in [self._arm_loop,self._walk_loop,self._sim_loop]:
                threading.Thread(target=fn,daemon=True).start()
            print("✅ PyBullet W1 — lip-sync + micro-animations")
            return self.pepper
        except Exception as e:
            print(f"⚠️  PyBullet: {e}"); return None

    def _build_room(self,p):
        wc=[0.88,0.88,0.92,1]
        for pos,ext in [([0,-4,1.1],[5,.1,1.1]),([0,4,1.1],[5,.1,1.1]),
                        ([5,0,1.1],[.1,4,1.1]),([-5,0,1.1],[.1,4,1.1])]:
            p.createMultiBody(0,-1,p.createVisualShape(p.GEOM_BOX,halfExtents=ext,rgbaColor=wc),pos)
        p.createMultiBody(0,-1,p.createVisualShape(p.GEOM_BOX,halfExtents=[4.5,3.5,.02],
            rgbaColor=[.55,.45,.35,1]),[0,0,.01])
        for txt,pos in [("ABA MOTOR",[-4,3,2]),("TEACCH COG",[4,3,2]),
                        ("DTT VERBAL",[0,4,2]),("ESDM SOCIAL",[-4,-3,2]),
                        (f"★ {CHILD_NAME} ★",[0,0,3.1])]:
            p.addUserDebugText(txt,pos,[.4,.5,.9],textSize=1.0,lifeTime=0)

    def _sa(self,j,a,s=0.15):
        if self.pepper:
            try: self.pepper.setAngles(j,a,s)
            except: pass

    def _arm_loop(self):
        ph=0
        while True:
            try:
                lip=ST.get("lip_sync_value",0.0)
                # Lip-sync: HeadPitch
                if ST["is_speaking"]:
                    ph+=.07
                    L=.5+.3*math.sin(ph); R=.5+.3*math.sin(ph+math.pi*.6)
                    self._sa("LShoulderPitch",L,.07); self._sa("RShoulderPitch",R,.07)
                    self._sa("HeadPitch",-0.04-lip*0.14,.20)
                elif ST["listening"] or ST["recording"]:
                    self._sa("HeadYaw",0.25,.06); self._sa("HeadPitch",0.12,.06)
                elif ST["gaze_mode"]=="tablet":
                    self._sa("HeadYaw",-0.4,.08); self._sa("HeadPitch",0.1,.08)
                else:
                    # Idle: micro-animations
                    self._sa("LShoulderPitch",1.,.04); self._sa("RShoulderPitch",1.,.04)
                    # Head tilt from FaceMesh
                    ht=ST.get("head_tilt_val",0.0)
                    self._sa("HeadYaw",ht*0.5,.03)
                    # Eye blink → HeadPitch micro-dip
                    if ST.get("blinking",False):
                        self._sa("HeadPitch",0.08,.12)
                    else:
                        self._sa("HeadPitch",0.0,.03)
                    # Nose twitch → small HeadRoll
                    nt=ST.get("nose_twitch",0.0)
                    self._sa("HeadRoll",nt*0.01,.05)
                # Social joy: arm wave
                if ST.get("social_joy_active",False):
                    ph2=time.time()*4
                    self._sa("LShoulderPitch",0.05+0.3*abs(math.sin(ph2)),.25)
                    self._sa("RShoulderPitch",0.05+0.3*abs(math.sin(ph2+math.pi)),.25)
                    self._sa("HeadPitch",-0.25+0.1*math.sin(ph2*0.5),.15)
            except: pass
            time.sleep(.04)

    def _walk_loop(self):
        t=0
        while True:
            t+=.015; self.rx+=.016*math.cos(t*.4); self.ry+=.016*math.sin(t*.5)
            self.rx=max(-3.5,min(3.5,self.rx)); self.ry=max(-2.8,min(2.8,self.ry))
            try: self.pepper.setPosition([self.rx,self.ry,.8])
            except: pass
            time.sleep(.06)

    def _sim_loop(self):
        while True:
            try: self.p.stepSimulation()
            except: pass
            time.sleep(1/240.)

    def show_text(self,text):
        if not self.ok: return
        try:
            pos=self.p.getBasePositionAndOrientation(self.pepper.body)[0]
            self.p.addUserDebugText(text[:55],[pos[0],pos[1],pos[2]+1.35],
                [0,0,0],textSize=.82,lifeTime=5)
        except: pass

# ═══════════════════════════════════════════════════════════════
# 13. OPENCV WINDOWS (W2 + W3)
# ═══════════════════════════════════════════════════════════════
class OpenCVDisplay:
    WIN2="W2: Emotion + Skeleton"
    WIN3="W3: Live Station + Avatar"
    ECOL={"happy":(0,220,80),"joyful":(0,255,180),"sad":(100,100,220),
          "angry":(0,0,220),"fear":(0,180,220),"surprised":(200,50,220),
          "confused":(200,150,0),"neutral":(180,180,180)}

    def __init__(self,cam_thread):
        self.cam=cam_thread; self.running=True; self._phase=0.0
        threading.Thread(target=self._run,daemon=True).start()
        print("✅ OpenCV W2+W3 (resizable)")

    def _sim_frame(self):
        f=np.zeros((480,640,3),dtype=np.uint8); f[:]=(10,12,28)
        self._phase+=0.04; r=int(30+12*math.sin(self._phase))
        cv2.circle(f,(320,200),r,(int(80+80*math.sin(self._phase)),
            int(120+120*math.cos(self._phase*.7)),220),3)
        cv2.putText(f,"NO CAMERA",(230,240),cv2.FONT_HERSHEY_SIMPLEX,0.8,(100,150,255),2)
        return f

    def _build_w2(self,frame):
        """Window 2: Emotion + Skeleton monitor"""
        base=cv2.resize(frame,(600,600))
        ov=base.copy(); cv2.rectangle(ov,(0,0),(234,600),(0,0,0),-1)
        base=cv2.addWeighted(ov,0.70,base,0.30,0)
        em=ST["emotion"]; col=self.ECOL.get(em,(180,180,180))
        cv2.rectangle(base,(0,0),(600,52),(0,0,0),-1)
        cv2.putText(base,f"W2: EMOTION+SKELETON | {CHILD_NAME}",
            (8,18),cv2.FONT_HERSHEY_SIMPLEX,0.50,(0,200,255),1)
        suc=ST["consecutive"]
        cv2.putText(base,f"★{'★'*suc}{'☆'*(3-suc)} | {em.upper()} | Att:{ST['attention']}%",
            (8,40),cv2.FONT_HERSHEY_SIMPLEX,0.52,col,2)
        # Emotion bars
        emos=["happy","joyful","sad","angry","fear","surprised","confused","neutral"]
        scores=ST.get("emotion_scores",{})
        for i,emo in enumerate(emos):
            sc=scores.get(emo,0.125)
            y=56+i*62; bar=int(sc*218); ec=self.ECOL.get(emo,(150,150,150))
            cv2.rectangle(base,(5,y),(226,y+52),(22,25,45),-1)
            if bar>0: cv2.rectangle(base,(5,y),(5+bar,y+52),ec,-1)
            cv2.rectangle(base,(5,y),(226,y+52),(55,60,85),1)
            cv2.putText(base,f"{emo[:8]}: {sc:.0%}",
                (9,y+32),cv2.FONT_HERSHEY_SIMPLEX,0.52,(255,255,255),1)
        # Gestures
        rx,ry=240,56
        suc_pct=min(100,int(suc/3*100))
        cv2.putText(base,"MASTERY",(rx,ry-4),cv2.FONT_HERSHEY_SIMPLEX,0.42,(200,200,200),1)
        cv2.rectangle(base,(rx,ry+2),(596,ry+18),(25,28,50),-1)
        cv2.rectangle(base,(rx,ry+2),(rx+int(356*suc_pct/100),ry+18),(0,200,100),-1)
        cv2.putText(base,f"{suc}/3 ({suc_pct}%)",(rx+5,ry+13),cv2.FONT_HERSHEY_SIMPLEX,0.38,(255,255,255),1)
        acts=[("Hand↑",ST["hand_raised"],(0,255,100)),
              ("Waving",ST["waving"],(0,200,255)),
              ("Clapping",ST["clapping"],(255,200,0)),
              ("Arms Wide",ST["arms_out"],(255,120,0)),
              ("Hands Up",ST["hands_up"],(0,255,200)),
              ("Eye Ctct",ST["eye_contact"],(200,100,255)),
              ("Blinking",ST["blinking"],(180,180,180)),
              ("Pointing",ST.get("pointing",False),(255,180,100))]
        for i,(lbl,active,ac) in enumerate(acts):
            y=ry+22+i*44
            bg=(5,30,15) if active else (18,20,32)
            cv2.rectangle(base,(rx,y),(596,y+34),bg,-1)
            cv2.rectangle(base,(rx,y),(596,y+34),ac if active else (55,60,85),2 if active else 1)
            cv2.putText(base,lbl,(rx+8,y+22),cv2.FONT_HERSHEY_SIMPLEX,
                0.46,ac if active else (65,68,80),2 if active else 1)
        # Finger count
        fc=ST.get("finger_count",0)
        if fc>0:
            vy=ry+380
            cv2.rectangle(base,(rx,vy),(596,vy+36),(5,25,40),-1)
            cv2.rectangle(base,(rx,vy),(596,vy+36),(0,200,255),2)
            cv2.putText(base,f"FINGERS: {fc}  {'☝'*min(fc,5)}",
                (rx+8,vy+24),cv2.FONT_HERSHEY_SIMPLEX,0.58,(0,200,255),2)
        pl=ST.get("pose_landmarks",{}); vy2=ry+420
        cv2.putText(base,
            f"Elbow L:{pl.get('l_elbow_angle',0):.0f}° R:{pl.get('r_elbow_angle',0):.0f}°",
            (rx,vy2),cv2.FONT_HERSHEY_SIMPLEX,0.36,(160,160,160),1)
        bw=int(ST["attention"]/100*596)
        cv2.rectangle(base,(0,576),(596,596),(16,18,35),-1)
        cv2.rectangle(base,(0,576),(bw,596),col,-1)
        cv2.putText(base,f"Attention:{ST['attention']}%",
            (6,592),cv2.FONT_HERSHEY_SIMPLEX,0.38,(255,255,255),1)
        cv2.circle(base,(588,22),9,(0,255,0) if ST["face_detected"] else (0,0,255),-1)
        if ST["verify_action"]:
            rem=max(0,int(ST["verify_timeout"]-time.time()))
            cv2.rectangle(base,(rx,ry+440),(596,ry+478),(28,14,0),-1)
            cv2.rectangle(base,(rx,ry+440),(596,ry+478),(255,140,0),2)
            cv2.putText(base,f"Verify: {ST['verify_action']} ({rem}s)",
                (rx+5,ry+464),cv2.FONT_HERSHEY_SIMPLEX,0.42,(255,160,50),1)
        return base

    def _build_w3(self,frame):
        """Window 3: Live station + animated avatar"""
        win=np.zeros((520,820,3),dtype=np.uint8); win[:]=(8,10,22)
        for i in range(0,820,40): cv2.line(win,(i,0),(i,520),(14,17,34),1)
        for i in range(0,520,40): cv2.line(win,(0,i),(820,i),(14,17,34),1)
        cam=cv2.resize(frame,(400,340)); win[76:416,10:410]=cam
        cv2.rectangle(win,(10,76),(410,416),(60,65,120),2)
        em=ST["emotion"]; col=self.ECOL.get(em,(180,180,180))
        cv2.putText(win,em.upper(),(18,432),cv2.FONT_HERSHEY_SIMPLEX,0.58,col,2)
        fc=ST.get("finger_count",0)
        if fc>0:
            cv2.putText(win,f"Fingers:{fc} {'☝'*min(fc,5)}",
                (14,450),cv2.FONT_HERSHEY_SIMPLEX,0.48,(255,200,0),2)
        suc=ST["consecutive"]
        cv2.putText(win,f"{'★'*suc}{'☆'*(3-suc)} {suc}/3",
            (14,468),cv2.FONT_HERSHEY_SIMPLEX,0.42,(255,200,0),1)

        # ── AVATAR with lip-sync + micro-animations ──────────
        self._phase+=0.10 if ST["is_speaking"] else 0.03
        lip=ST.get("lip_sync_value",0.0)
        if ST["is_speaking"]:
            lip=max(0.1,lip+0.35*abs(math.sin(self._phase*4)))
        av_cx,av_cy=645,220
        # Body
        cv2.ellipse(win,(av_cx,av_cy+83),(48,68),0,0,360,(80,100,200),-1)
        cv2.ellipse(win,(av_cx,av_cy+83),(48,68),0,0,360,(100,120,220),2)
        # Arms — social joy
        if ST.get("social_joy_active",False):
            jt=time.time()
            la=int(30*math.sin(jt*4)); ra=int(30*math.sin(jt*4+1))
            cv2.ellipse(win,(av_cx-58+la,av_cy+28),(12,52),-62+la,0,360,(70,90,190),-1)
            cv2.ellipse(win,(av_cx+58+ra,av_cy+28),(12,52),62+ra,0,360,(70,90,190),-1)
        elif ST["is_speaking"]:
            la=int(22*math.sin(self._phase)); ra=int(22*math.sin(self._phase+math.pi))
            cv2.ellipse(win,(av_cx-58+la,av_cy+64),(12,37),-30+la,0,360,(70,90,190),-1)
            cv2.ellipse(win,(av_cx+58+ra,av_cy+64),(12,37),30+ra,0,360,(70,90,190),-1)
        else:
            cv2.ellipse(win,(av_cx-58,av_cy+68),(12,32),-15,0,360,(70,90,190),-1)
            cv2.ellipse(win,(av_cx+58,av_cy+68),(12,32),15,0,360,(70,90,190),-1)
        # Head with micro-animations
        hbob=int(3*math.sin(self._phase*0.5))
        ht_val=ST.get("head_tilt_val",0.0)*10  # head tilt px
        hy=av_cy-53+hbob
        # Draw tilted head
        cv2.circle(win,(av_cx+int(ht_val),hy),53,(220,195,173),-1)
        cv2.circle(win,(av_cx+int(ht_val),hy),53,(200,175,155),2)
        # Eyes — blink + social joy color change
        blink_=(ST.get("blinking",False) or (int(self._phase*3)%45==0))
        ey_=6 if not blink_ else 1
        if ST.get("social_joy_active",False):
            ec=ST["eye_color"]
        else:
            ec=(100,180,255)
        hx=av_cx+int(ht_val)
        for ex_ in [hx-19,hx+19]:
            cv2.ellipse(win,(ex_,hy-9),(7,ey_),0,0,360,ec,-1)
            if not blink_:
                cv2.circle(win,(ex_+1,hy-9),3,(255,255,255),-1)
                cv2.circle(win,(ex_+2,hy-10),1,(0,0,0),-1)
        # Nose twitch
        nt=ST.get("nose_twitch",0.0)
        nose_ox=int(nt*0.5)
        cv2.circle(win,(hx+nose_ox,hy+7),5,(180,140,120),-1)
        # Mouth lip-sync
        mh=int(4+lip*18)
        if ST["is_speaking"]:
            cv2.ellipse(win,(hx,hy+22),(16,mh),0,0,180,(160,80,80),-1)
            cv2.ellipse(win,(hx,hy+22),(16,mh),0,0,180,(210,110,110),2)
            if lip>0.3:
                cv2.ellipse(win,(hx,hy+22),(13,max(1,mh-3)),0,0,180,(240,230,220),-1)
        elif em in ["happy","joyful"]:
            cv2.ellipse(win,(hx,hy+20),(15,7),0,0,180,(150,80,80),-1)
        else:
            cv2.line(win,(hx-12,hy+21),(hx+12,hy+21),(150,80,80),2)
        for ex_ in [av_cx-51,av_cx+51]:
            cv2.circle(win,(ex_,hy-6),10,(210,185,163),-1)
            cv2.circle(win,(ex_,hy-6),6,(240,200,180),-1)
        cv2.rectangle(win,(av_cx-28,av_cy+148),(av_cx-10,av_cy+180),(60,80,170),-1)
        cv2.rectangle(win,(av_cx+10,av_cy+148),(av_cx+28,av_cy+180),(60,80,170),-1)
        # Status ring
        if ST.get("social_joy_active",False):
            jt=time.time()
            pr=85+int(15*abs(math.sin(jt*4)))
            jc=(int(128+127*math.sin(jt*3)),int(200+55*math.sin(jt*2)),255)
            cv2.circle(win,(av_cx,av_cy),pr,jc,3)
            cv2.putText(win,"SOCIAL JOY!",(av_cx-50,av_cy+192),
                cv2.FONT_HERSHEY_SIMPLEX,0.50,(255,220,0),2)
        elif ST["is_speaking"]:
            pr=90+int(6*math.sin(self._phase*5))
            cv2.circle(win,(av_cx,av_cy),pr,(0,160,255),2)
            cv2.putText(win,f"SPEAKING lip={lip:.1f}",
                (av_cx-55,av_cy+192),cv2.FONT_HERSHEY_SIMPLEX,0.42,(0,200,255),1)
        elif ST["recording"]:
            cv2.circle(win,(av_cx,av_cy),92,(0,0,255),2)
            cv2.putText(win,"RECORDING",(av_cx-42,av_cy+192),
                cv2.FONT_HERSHEY_SIMPLEX,0.48,(0,0,255),2)
        elif ST["listening"]:
            cv2.circle(win,(av_cx,av_cy),92,(0,220,100),2)
            cv2.putText(win,"LISTENING",(av_cx-42,av_cy+192),
                cv2.FONT_HERSHEY_SIMPLEX,0.48,(0,220,100),2)
        # Task msg
        tmsg=ST.get("tablet_instruction","")[:72]
        if tmsg:
            cv2.rectangle(win,(10,478),(820,498),(20,25,45),-1)
            cv2.putText(win,tmsg,(14,492),cv2.FONT_HERSHEY_SIMPLEX,0.37,(255,220,100),1)
        # Header
        cv2.rectangle(win,(0,0),(820,72),(6,8,20),-1)
        cv2.putText(win,f"W3: LIVE STATION — {CHILD_NAME} | Pepper Clinical Infinity",
            (10,24),cv2.FONT_HERSHEY_SIMPLEX,0.58,(160,140,255),2)
        cv2.putText(win,
            f"L{ST['current_level']} {ST['domain']} | Score:{ST['score']} | "
            f"Mastered:{ST['tasks_mastered']} | Streak:{ST['streak']} | CSV:{CSV_FILE}",
            (10,50),cv2.FONT_HERSHEY_SIMPLEX,0.36,(0,200,100) if ST["face_detected"] else (200,150,0),1)
        # Recent chat
        cy_=514
        for msg in ST["session_chat"][-3:]:
            isp=msg["role"]=="pepper"
            txt=msg["text"][:58]+("…" if len(msg["text"])>58 else "")
            cv2.rectangle(win,(10,cy_-15),(810,cy_+4),(30,20,60) if isp else (10,30,15),-1)
            cv2.rectangle(win,(10,cy_-15),(810,cy_+4),(100,80,200) if isp else (0,180,80),1)
            cv2.putText(win,("🤖 " if isp else f"👦 {CHILD_NAME}: ")+txt,
                (14,cy_),cv2.FONT_HERSHEY_SIMPLEX,0.32,
                (180,160,255) if isp else (100,220,100),1)
            cy_-=21
        return win

    def _run(self):
        no_cam=not (self.cam.cap and self.cam.cap.isOpened())
        em_last=0
        cv2.namedWindow(self.WIN2,cv2.WINDOW_NORMAL); cv2.resizeWindow(self.WIN2,600,600)
        cv2.moveWindow(self.WIN2,20,20)
        cv2.namedWindow(self.WIN3,cv2.WINDOW_NORMAL); cv2.resizeWindow(self.WIN3,820,520)
        cv2.moveWindow(self.WIN3,640,20)
        while self.running:
            try:
                if no_cam: frame=self._sim_frame()
                else:
                    ret,f=self.cam.cap.read() if self.cam.cap else (False,None)
                    frame=cv2.flip(f,1) if ret and f is not None else self._sim_frame()
                w2=self._build_w2(frame.copy())
                if w2 is not None: cv2.imshow(self.WIN2,w2)
                w3=self._build_w3(frame.copy())
                if w3 is not None: cv2.imshow(self.WIN3,w3)
                key=cv2.waitKey(1)&0xFF
                if key in [ord('q'),27]: self.running=False; break
            except Exception as e: print(f"⚠️  CV: {e}"); time.sleep(0.1)
            time.sleep(0.016)   # ~60fps
        try: cv2.destroyAllWindows()
        except: pass

    def stop(self): self.running=False; time.sleep(0.3)
        
# ═══════════════════════════════════════════════════════════════
# 14. GEMINI BRAIN (fallback empathy)
# ═══════════════════════════════════════════════════════════════
CLINICAL_PROMPT=f"""You are PEPPER, a Clinical Therapist robot for ASD.
Child: {CHILD_NAME}. Protocols: ABA, DTT, TEACCH, ESDM.
3 consecutive correct = mastery. Be warm, specific, encouraging.
MAX 2 sentences. End: "Ready? Your turn! 🎯"
Tokens: [WAVE][CLAP][NOD][DANCE][CELEBRATE][HUG][THINK][LEVEL_UP]"""

EMPATHY_LIB={
    "task_ok":["PERFECT! You did it! [CLAP][CELEBRATE]","WOW! Amazing! [DANCE]","BRILLIANT! [CELEBRATE]"],
    "task_retry":["Not quite! Try again! 🎯","Almost! One more time! 🎯","You can do it! 🎯"],
    "level_up":["LEVEL UP! [DANCE][CELEBRATE]","CHAMPION! [CELEBRATE]"],
    "silence":["Ready when you are! 🎯","Take your time! 🎯"],
    "default":["Great effort! [CLAP]","Ready? Your turn! 🎯"],
}
_emp_last={}
def empathy(cat="default"):
    pool=EMPATHY_LIB.get(cat,EMPATHY_LIB["default"])
    last=_emp_last.get(cat,-1)
    choices=[i for i in range(len(pool)) if i!=last]
    if not choices: choices=list(range(len(pool)))
    idx=random.choice(choices); _emp_last[cat]=idx
    return pool[idx]

class GeminiBrain:
    MODELS=["gemini-1.5-flash","gemini-1.5-flash-8b","gemini-1.5-pro",
            "gemini-2.0-flash","gemini-2.0-flash-lite","gemini-pro"]
    def __init__(self):
        self.ok=False; self._lk=threading.Lock()
        self.model_name="fallback"; self.chat=None; self.ctx=[]
        try:
            disc=[]
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    disc.append(m.name.replace('models/',''))
            for d in reversed(disc):
                if d not in self.MODELS and "exp" not in d:
                    self.MODELS.insert(0,d)
        except: pass
        for mn in self.MODELS:
            try:
                m=genai.GenerativeModel(mn,system_instruction=CLINICAL_PROMPT,
                    generation_config=genai.GenerationConfig(temperature=0.82,max_output_tokens=140))
                c=m.start_chat(history=[])
                r=c.send_message("Say: READY")
                if r.text and len(r.text)>2:
                    self.model=m; self.chat=c; self.model_name=mn
                    self.ok=True; ST["gemini_ok"]=True if "ST" in dir() else True
                    print(f"✅ Gemini: {mn}"); break
            except Exception as e:
                if "403" in str(e): print(f"⚠️  {mn}: 403 — rotate API key")
                else: print(f"⚠️  {mn}: {str(e)[:50]}")
        if not self.ok: print("⚠️  Gemini unavailable → empathy mode")

    def ask(self,prompt):
        self.ctx.append(prompt[:50])
        if len(self.ctx)>6: self.ctx.pop(0)
        if not self.ok: return empathy("default")
        ctx=(f"[child={CHILD_NAME} age=6 level={ST['current_level']} "
             f"domain={ST['domain']} mastery={ST['consecutive']}/3 "
             f"emotion={ST['emotion']} attention={ST['attention']}%] ")
        with self._lk:
            try:
                resp=self.chat.send_message(ctx+prompt)
                LOG(f"AI: {resp.text[:55]}"); return resp.text.strip()
            except Exception as e:
                LOG(f"API: {str(e)[:40]}","warn")
                try: self.chat=self.model.start_chat(history=[])
                except: pass
                return empathy("default")

# ═══════════════════════════════════════════════════════════════
# 15. THERAPY CONTROLLER — conscious, infinite, logged
# ═══════════════════════════════════════════════════════════════
class TherapyCtrl:
    def __init__(self,voice:Voice,gemini:GeminiBrain,sim:PepperSim):
        self.v=voice; self.g=gemini; self.s=sim
        self.running=False

    def _say(self,text,wait=True):
        clean=re.sub(r'\[[^\]]+\]','',str(text)).strip()
        BRIDGE.sig_set_instr.emit(clean[:70])
        if self.s.ok: self.s.show_text(clean[:55])
        self.v.say(text,wait=wait)

    def run(self):
        self.running=True
        self._say(
            f"Hello {CHILD_NAME}! I am Pepper your Smart Therapist! "
            "Watch the screen and copy my movements! "
            "Tap the red microphone button to speak! "
            "Let us earn 3 stars for every task! Ready? [WAVE]")
        time.sleep(0.5)
        last_em=ST["emotion"]; em_t=time.time()

        while self.running:
            # Silence check
            if time.time()-ST["last_sound"]>15:
                ST["last_sound"]=time.time()
                self.v.say(empathy("silence"),wait=False)
            # Emotion support
            curr=ST["emotion"]
            if curr!=last_em and time.time()-em_t>8:
                last_em=curr; em_t=time.time()
                if curr in ["sad","angry","fear"]:
                    self._say(
                        f"{CHILD_NAME} I see you feel {curr}. "
                        "It is okay. I am here with you. [HUG]",wait=False)
            self._handle_cmd()

            # ── Get current task ──────────────────────────────
            tidx=ST["task_index"]%len(TASK_POOL)
            task=TASK_POOL[tidx]
            ST["tablet_instruction"]=task["instruction"]
            ST["domain"]=task.get("domain","Motor")
            ST["protocol"]=task.get("protocol","ABA-Motor")
            ST["current_level"]=task.get("level",1)

            # Show on tablet (signal)
            self._show_tablet(task)

            # Announce
            if task["domain"]=="Motor":
                self._say(task["instruction"]+" Look at the screen!",wait=False)
                # ESDM gaze to tablet
                ST["gaze_mode"]="tablet"
                threading.Thread(target=self._gaze_sequence,daemon=True).start()
            elif task["domain"]=="Math":
                self._say(task["instruction"],wait=False)
            else:
                self._say(task["instruction"]+" Click the correct one!",wait=False)

            # Run task (conscious loop)
            success=self._run_task(task)

            # ── CSV LOG ──────────────────────────────────────
            log_csv(task["id"],task["domain"],task["level"],
                success,ST["consecutive"],ST["score"],
                ST["emotion"],ST["attention"])

            # ── Check response ────────────────────────────────
            if success:
                self._on_success(task)
                self._say(
                    f"{CHILD_NAME}! {task.get('success','Amazing!')} "
                    "Now the next task! [CELEBRATE]",wait=False)
            else:
                self._on_fail(task)
                self._say(
                    f"{CHILD_NAME}! {task.get('fail','Not quite!')} "
                    "Let us try again! [THINK]",wait=False)
            time.sleep(0.4)

    def _show_tablet(self,task):
        mode=task.get("tablet_mode","idle")
        data={"mode":mode,"instruction":task["instruction"]}
        if task["domain"]=="Motor" or mode=="motor_model":
            data.update({"mode":"motor_model",
                "figure":task.get("figure",""),
                "label":task.get("name",""),
                "emoji":task.get("verify","🤖")})
        elif mode=="word_display":
            data.update({"emoji":task.get("word_emoji","📢"),
                "word":task.get("word_text","SAY IT!")})
        elif mode=="number_display":
            data.update({"target_number":task.get("target_number",1)})
        elif mode in ["color_grid","object_grid","shape_grid",
                      "number_grid","emotion_grid"]:
            data.update({"options":task.get("options",[]),
                "correct":task.get("correct",-1)})
        ST["tablet_click_result"]=None
        BRIDGE.sig_new_task.emit(data)

    def _gaze_sequence(self):
        ST["gaze_mode"]="tablet"; time.sleep(1.5)
        ST["gaze_mode"]="child"

    def _run_task(self,task):
        vtype=task.get("verify","motor")
        motor_v=["clap","wave","raise_hand","touch_nose","arms_out","hands_up","point"]
        if vtype in motor_v:
            ST["verify_action"]=vtype; ST["verify_result"]=False
            ST["verify_timeout"]=time.time()+22
        elif vtype=="finger_count":
            ST["verify_action"]="finger_count"; ST["verify_result"]=False
            ST["finger_target"]=task.get("target_number",1)
            ST["verify_timeout"]=time.time()+22
        ST["last_speech_text"]=""; prompts=task.get("prompts",["Try again!"])
        waiting=task.get("waiting","I am waiting!")
        deadline=time.time()+65; last_p=time.time(); pidx=0

        while time.time()<deadline:
            res=self._check(task)
            if res=="success": return True
            if res=="fail":    return False
            if time.time()-last_p>6:
                last_p=time.time()
                self.v.say(f"{CHILD_NAME}... {prompts[pidx%len(prompts)]}",wait=False)
                BRIDGE.sig_set_waiting.emit(waiting)
                pidx+=1
            self._handle_cmd()
            time.sleep(0.18)
        ST["verify_action"]=None; return False

    def _check(self,task):
        vtype=task.get("verify","motor")
        mc=task.get("verify","")
        if mc in ["clap","wave","raise_hand","touch_nose","arms_out","hands_up","point"]:
            if ST["verify_result"]: ST["verify_result"]=False; return "success"
            if mc=="clap" and ST["clapping"]: return "success"
            if mc=="wave" and ST["waving"]: return "success"
            if mc=="raise_hand" and ST["hand_raised"]: return "success"
            if mc=="arms_out" and ST["arms_out"]: return "success"
            if mc=="hands_up" and ST["hands_up"]: return "success"
        elif vtype=="finger_count":
            target=task.get("target_number",1)
            if ST["finger_count"]==target: return "success"
        elif vtype=="tablet_click":
            r=ST.get("tablet_click_result")
            if r=="correct": ST["tablet_click_result"]=None; return "success"
            if r=="wrong":   ST["tablet_click_result"]=None; return "fail"
        elif vtype=="speech_keyword":
            kw=task.get("keyword","")
            if kw and kw.lower() in ST.get("last_speech_text","").lower():
                ST["last_speech_text"]=""; return "success"
        elif vtype=="speech_any":
            if ST["last_sound"]>time.time()-3 and len(ST.get("last_speech_text",""))>0:
                ST["last_speech_text"]=""; return "success"
        return None

    def _on_success(self,task):
        ST["consecutive"]+=1; pts=task.get("tokens",2)*5
        ST["score"]+=pts; ST["tokens"]+=task.get("tokens",2)
        ST["tasks_success"]+=1; ST["streak"]+=1
        BRIDGE.sig_show_success.emit(task.get("success","Amazing! ✅"))
        BRIDGE.sig_joy.emit(task.get("joy","celebrate"))
        BRIDGE.sig_update_stats.emit()
        LOG(f"✅ {ST['consecutive']}/3 '{task['id']}'","success")
        if ST["consecutive"]>=MASTERY_N:
            ST["consecutive"]=0; ST["tasks_mastered"]+=1
            ST["task_index"]+=1
            if ST["task_index"]>=len(TASK_POOL):
                ST["task_index"]=0; ST["current_level"]+=1
            ntask=TASK_POOL[ST["task_index"]%len(TASK_POOL)]
            LOG(f"🏆 MASTERED → {ntask['id']}","success")
            # Social joy + balloons
            ST["social_joy_active"]=True
            # Eye color change
            ST["eye_color"]=(int(128+127*math.sin(time.time()*3)),
                             int(200+55*math.sin(time.time()*2)),255)
            BRIDGE.sig_celebration.emit()   # balloons
            self._say(
                f"{CHILD_NAME} earned 3 stars! MASTERED! [LEVEL_UP] "
                f"Moving to next task: {ntask.get('name','')}! [WAVE]",
                wait=False)
            QTimer.singleShot(4000,lambda: ST.update(
                {"social_joy_active":False,"eye_color":(100,180,255)}))

    def _on_fail(self,task):
        ST["consecutive"]=0; ST["streak"]=0; ST["tasks_fail"]+=1
        BRIDGE.sig_show_fail.emit(task.get("fail","Not quite! Try again!"))
        QTimer.singleShot(2500,lambda: BRIDGE.sig_reset_cards.emit())

    def _handle_cmd(self):
        cmd=ST.get("sim_cmd")
        if not cmd: return
        ST["sim_cmd"]=None
        if cmd=="next":
            ST["consecutive"]=0
            ST["task_index"]=(ST["task_index"]+1)%len(TASK_POOL)
            self.v.say("Next task!",wait=False)
        elif cmd=="break": self.v.say("Break time! Rest.",wait=False)
        elif cmd=="report":
            print(f"\n{'='*50}")
            print(f"Session Report — {CHILD_NAME}")
            print(f"Score:{ST['score']} | Mastered:{ST['tasks_mastered']}")
            print(f"OK:{ST['tasks_success']} | Fail:{ST['tasks_fail']}")
            print(f"CSV: {CSV_FILE}")
            print('='*50)

# ═══════════════════════════════════════════════════════════════
# 16. MAIN
# ═══════════════════════════════════════════════════════════════
def main():
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║  PEPPER CLINICAL INFINITY — {CHILD_NAME:<30}║
╠══════════════════════════════════════════════════════════════╣
║  Quad-Window: PyBullet + OpenCV×2 + PyQt6 Tablet           ║
║  Tasks: {len(TASK_POOL):<5} | Mastery: {MASTERY_N}/3 consecutive         ║
║  CSV Log: {CSV_FILE:<42}║
╚══════════════════════════════════════════════════════════════╝
""")

    # PyQt6 app — main thread
    qt_app=QApplication(sys.argv)
    qt_app.setApplicationName(f"Pepper Clinical Infinity — {CHILD_NAME}")
    qt_app.setStyle("Fusion")
    palette=QPalette()
    palette.setColor(QPalette.ColorRole.Window,    QColor(6,9,18))
    palette.setColor(QPalette.ColorRole.WindowText,QColor(224,230,255))
    palette.setColor(QPalette.ColorRole.Base,      QColor(12,15,30))
    palette.setColor(QPalette.ColorRole.Text,      QColor(224,230,255))
    qt_app.setPalette(palette)

    # Tablet (W4) — main thread
    tablet=TabletWindow(); tablet.show(); tablet.move(20,580)

    # Camera (QThread)
    cam_thread=CameraThread(); cam_thread.start()

    # OpenCV (W2+W3) — daemon threads inside class
    cv_display=OpenCVDisplay(cam_thread)

    # PyBullet (W1)
    sim=PepperSim(); pepper=sim.launch()

    # TTS + Gemini
    voice=Voice(); gemini=GeminiBrain()

    # Therapy ctrl
    ctrl=TherapyCtrl(voice,gemini,sim)

    def _start():
        time.sleep(1.5)
        ctrl.run()

    t=threading.Thread(target=_start,daemon=True); t.start()

    print(f"""
{'='*64}
✅ CLINICAL INFINITY ACTIVE
{'='*64}
W1: PyBullet    (FIXED — lip-sync + blink + head-tilt)
W2: Emotion     (RESIZABLE — emotion + skeleton)
W3: Live        (RESIZABLE — avatar + status)
W4: Tablet      (FIXED 1280×780 — camera left, task right)

Child: {CHILD_NAME}
CSV:   {CSV_FILE}
Tasks: {len(TASK_POOL)} variations

Terminal commands:
  n / next  — skip task     r / report — print report
  b / break — break time    q / exit   — quit
{'='*64}
""")

    def _input_loop():
        while ctrl.running:
            try:
                cmd=input("> ").strip().lower()
                if cmd in ["q","exit","quit"]:
                    ctrl.running=False; cam_thread.stop()
                    cv_display.stop(); qt_app.quit(); break
                elif cmd in ["n","next"]: ST["sim_cmd"]="next"
                elif cmd in ["b","break"]: ST["sim_cmd"]="break"
                elif cmd in ["r","report"]: ST["sim_cmd"]="report"
                elif cmd=="stats":
                    tidx=min(ST["task_index"],len(TASK_POOL)-1)
                    t=TASK_POOL[tidx]
                    print(f"\nTask:{t['id']} {t['domain']} "
                          f"★{ST['consecutive']}/3 "
                          f"Score:{ST['score']} "
                          f"Mastered:{ST['tasks_mastered']} "
                          f"Fingers:{ST['finger_count']}")
            except (KeyboardInterrupt,EOFError): break
        qt_app.quit()

    threading.Thread(target=_input_loop,daemon=True).start()

    ret=qt_app.exec()
    ctrl.running=False; cam_thread.stop(); cv_display.stop()

    # Final CSV summary
    dur=int((time.time()-ST["uptime"])/60)
    print(f"\n{'='*64}")
    print(f"🎉 SESSION COMPLETE — {CHILD_NAME}")
    print(f"{'='*64}")
    print(f"Duration:  {dur} minutes")
    print(f"Score:     {ST['score']}")
    print(f"Mastered:  {ST['tasks_mastered']} tasks")
    print(f"OK/Fail:   {ST['tasks_success']} / {ST['tasks_fail']}")
    print(f"CSV:       {CSV_FILE}")
    print('='*64)
    sys.exit(ret)

if __name__=="__main__":
    main()
