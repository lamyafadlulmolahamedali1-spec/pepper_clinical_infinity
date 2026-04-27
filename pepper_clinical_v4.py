#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════╗
║  PEPPER CLINICAL INFINITY V4 — MEDAL-GRADE PRODUCTION SYSTEM       ║
║  Commander: Lamya | Omdurman Islamic University                     ║
╠══════════════════════════════════════════════════════════════════════╣
║  ARCHITECTURE:                                                       ║
║  • Single QMainWindow — Avatar EMBEDDED in dashboard                ║
║  • PyBullet subprocess (watchdog-supervised, auto-restart)          ║
║  • MediaPipe FaceMesh TESSELATION — real-time emotion grid          ║
║  • Emotion breakdown with live % bars (7 emotions)                  ║
║  • Full body skeleton + 10-finger hand tracking                     ║
║  • ABA/DTT/TEACCH/ESDM infinite tasks (3000+)                      ║
║  • Smart skip: 2 fails → log + encourage + next task               ║
║  • YouTube educational video embed on request                        ║
║  • QPropertyAnimation balloon celebration (non-blocking)            ║
║  • Child Welcome Screen with name personalisation                   ║
║  • Flask dashboards: 5007 (parent) 5001 (clinical) 5009 (games)    ║
║  • ALL Qt UI via pyqtSignal — zero threading violations             ║
╚══════════════════════════════════════════════════════════════════════╝
"""

# ══════════════════════════════════════════════════════════════════════
# 0.  ENVIRONMENT  (before ANY other import)
# ══════════════════════════════════════════════════════════════════════
import os, sys, warnings, ctypes

os.environ.update({
    "TF_CPP_MIN_LOG_LEVEL":  "3",
    "PYTHONWARNINGS":         "ignore",
    "OPENCV_LOG_LEVEL":       "ERROR",
    "CUDA_VISIBLE_DEVICES":   "0",
    "QT_LOGGING_RULES":       "*.debug=false;qt.qpa.*=false",
    "QT_QPA_PLATFORM":        "xcb",
    "QT_QPA_FONTDIR":         "/usr/share/fonts",
    "TF_ENABLE_ONEDNN_OPTS":  "0",
    "MEDIAPIPE_DISABLE_GPU":  "1",          # use CPU for mediapipe (stable)
    "OMP_NUM_THREADS":        "4",
})
warnings.filterwarnings("ignore")
try:
    _a = ctypes.cdll.LoadLibrary("libasound.so.2")
    _a.snd_lib_error_set_handler(ctypes.c_void_p(None))
except Exception:
    pass

# ══════════════════════════════════════════════════════════════════════
# 1.  STANDARD IMPORTS
# ══════════════════════════════════════════════════════════════════════
import threading, subprocess, socket, time, random, math
import re, json, csv, base64, wave, tempfile, queue, signal
import webbrowser, urllib.parse
from datetime  import datetime
from io        import BytesIO

import cv2
import numpy as np
from PIL import Image, ImageDraw

import mediapipe as mp

import pyttsx3
import speech_recognition as sr

try:
    from faster_whisper import WhisperModel as FW
    _FW_OK = True
except Exception:
    _FW_OK = False

from flask import Flask, render_template_string, jsonify, request, redirect

# Qt  — imported AFTER env is set
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QGridLayout, QLineEdit, QTextEdit,
    QProgressBar, QStackedWidget, QSizePolicy, QScrollArea,
    QGraphicsOpacityEffect,
)
from PyQt6.QtCore import (
    Qt, QTimer, pyqtSignal, QObject, QThread,
    QPropertyAnimation, QEasingCurve, QPoint, QRect, QSize,
)
from PyQt6.QtGui import (
    QFont, QColor, QPalette, QPixmap, QImage,
    QPainter, QLinearGradient, QBrush, QPen,
)

# ══════════════════════════════════════════════════════════════════════
# 2.  PATIENT SETUP
# ══════════════════════════════════════════════════════════════════════
def kill_ports(*ports):
    for p in ports:
        try: os.system(f"fuser -k {p}/tcp 2>/dev/null")
        except: pass
        for _ in range(6):
            try:
                s = socket.socket()
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(("0.0.0.0", p)); s.close(); break
            except: time.sleep(0.25)

kill_ports(5001, 5007, 5009)

def get_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80)); ip = s.getsockname()[0]; s.close(); return ip
    except: return "127.0.0.1"

LOCAL_IP = get_ip()

print("\n" + "═"*62)
print("  PEPPER CLINICAL INFINITY V4 — Commander: Lamya")
print("═"*62)
CHILD_NAME = input("\n👦 Child's Name: ").strip() or "Child"
CHILD_AGE  = input("   Age (default 6): ").strip() or "6"
SAFE_NAME  = re.sub(r"[^a-zA-Z0-9_]", "_", CHILD_NAME)
CSV_FILE   = f"{SAFE_NAME}_Results.csv"

with open(CSV_FILE, "w", newline="") as f:
    csv.writer(f).writerow([
        "Time","Child","Task","Domain","Level","Result",
        "Consecutive","FailCount","Score","Emotion","Attention"])

def log_csv(task_id, domain, level, result, consec, fails, score, emotion, att):
    try:
        with open(CSV_FILE, "a", newline="") as f:
            csv.writer(f).writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                CHILD_NAME, task_id, domain, level,
                "SUCCESS" if result else "FAIL",
                consec, fails, score, emotion, att])
    except Exception: pass

# ══════════════════════════════════════════════════════════════════════
# 3.  PYBULLET SUBPROCESS SCRIPT
# ══════════════════════════════════════════════════════════════════════
_PB_SCRIPT = r"""
import sys, os, time, math, json, select
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

try:
    import pybullet as p, pybullet_data
    sys.path.insert(0, "/home/lamya/pepper_duo/src")
    from qibullet import SimulationManager
except Exception as e:
    print(f"PB_ERROR: {e}", flush=True)
    while True:
        try:
            r = select.select([sys.stdin],[],[],0)[0]
            if r and "EXIT" in sys.stdin.readline(): break
        except: break
    sys.exit(0)

child = sys.argv[1] if len(sys.argv) > 1 else "Child"
qisim  = SimulationManager()
client = qisim.launchSimulation(gui=True)
p.setRealTimeSimulation(1); p.setGravity(0, 0, -9.81)
p.setAdditionalSearchPath(pybullet_data.getDataPath())
p.loadURDF("plane.urdf")

wc = [0.92, 0.92, 0.96, 1]
for pos, ext in [([0,-4,1.1],[5,.1,1.1]),([0,4,1.1],[5,.1,1.1]),
                 ([5,0,1.1],[.1,4,1.1]),([-5,0,1.1],[.1,4,1.1])]:
    p.createMultiBody(0,-1,p.createVisualShape(p.GEOM_BOX,halfExtents=ext,rgbaColor=wc),pos)
p.createMultiBody(0,-1,p.createVisualShape(p.GEOM_BOX,halfExtents=[4.5,3.5,.02],
    rgbaColor=[.60,.50,.38,1]),[0,0,.01])
for txt, pos in [("ABA MOTOR",[-4,3,2]),("TEACCH COGNITIVE",[4,3,2]),
                 ("DTT VERBAL",[0,4.2,2]),("ESDM SOCIAL",[-4,-3,2]),
                 (f"★ {child} ★",[0,0,3.2])]:
    p.addUserDebugText(txt, pos, [.4,.5,.9], textSize=1.0, lifeTime=0)

pepper = qisim.spawnPepper(client)
pepper.goToPosture("Stand", 0.5)
p.resetDebugVisualizerCamera(6, 45, -30, [0, 0, 0.8])
print("PYBULLET_READY", flush=True)

rx = ry = 0.0; ph = 0.0
st = {"is_speaking":False,"listening":False,"recording":False,
      "lip":0.0,"ht":0.0,"blink":False,"sj":False,"gaze":"child"}

while True:
    try:
        r = select.select([sys.stdin],[],[],0)[0]
        if r:
            ln = sys.stdin.readline()
            if not ln or ln.strip() == "EXIT": break
            try: st.update(json.loads(ln))
            except: pass
    except: pass
    p.stepSimulation()
    lip = float(st.get("lip", 0.0))
    try:
        if st["is_speaking"]:
            ph += .07
            L = .5 + .3*math.sin(ph); R = .5 + .3*math.sin(ph + math.pi*.6)
            pepper.setAngles("LShoulderPitch", L, .07)
            pepper.setAngles("RShoulderPitch", R, .07)
            pepper.setAngles("HeadPitch", -0.04 - lip*0.13, .20)
        elif st.get("sj", False):
            jt = time.time()
            pepper.setAngles("LShoulderPitch", 0.05+0.3*abs(math.sin(jt*4)), .25)
            pepper.setAngles("RShoulderPitch", 0.05+0.3*abs(math.sin(jt*4+math.pi)), .25)
            pepper.setAngles("HeadPitch", -0.25+0.1*math.sin(jt*.5), .15)
        elif st.get("gaze") == "tablet":
            pepper.setAngles("HeadYaw", -0.4, .08)
            pepper.setAngles("HeadPitch", 0.1, .08)
        else:
            pepper.setAngles("LShoulderPitch", 1., .04)
            pepper.setAngles("RShoulderPitch", 1., .04)
            ht = float(st.get("ht", 0.0))
            pepper.setAngles("HeadYaw", ht*0.5, .03)
            pepper.setAngles("HeadPitch",
                0.07 if st.get("blink", False) else 0.0, .05)
    except: pass
    t_ = time.time()
    rx += .015*math.cos(t_*.4); ry += .015*math.sin(t_*.5)
    rx = max(-3.5, min(3.5, rx)); ry = max(-2.8, min(2.8, ry))
    try: pepper.setPosition([rx, ry, .8])
    except: pass
    time.sleep(1/60.)
"""

# ══════════════════════════════════════════════════════════════════════
# 4.  PYBULLET WATCHDOG
# ══════════════════════════════════════════════════════════════════════
class PBWatchdog:
    """Supervised PyBullet subprocess — auto-restarts on crash."""
    def __init__(self, child_name: str):
        self.child    = child_name
        self._proc    = None
        self._ready   = False
        self._lock    = threading.Lock()
        self._running = False

    def start(self):
        self._running = True
        threading.Thread(target=self._supervise, daemon=True).start()

    def _launch(self):
        try:
            self._proc = subprocess.Popen(
                [sys.executable, "-c", _PB_SCRIPT, self.child],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, text=True, bufsize=1)
            deadline = time.time() + 25
            while time.time() < deadline:
                line = self._proc.stdout.readline()
                if "PYBULLET_READY" in line:
                    self._ready = True
                    print("✅ PyBullet W1 (subprocess watchdog)")
                    return True
                if "PB_ERROR" in line:
                    print(f"⚠️  {line.strip()}")
                    return False
                time.sleep(0.1)
        except Exception as e:
            print(f"⚠️  PyBullet launch: {e}")
        return False

    def _supervise(self):
        while self._running:
            ok = self._launch()
            if ok:
                self._proc.wait()  # blocks until crash/exit
            if not self._running: break
            self._ready = False
            print("⚠️  PyBullet crashed — restarting in 3s…")
            time.sleep(3)

    def send(self, **kwargs):
        if not self._ready or not self._proc: return
        with self._lock:
            try:
                self._proc.stdin.write(json.dumps(kwargs) + "\n")
                self._proc.stdin.flush()
            except Exception: pass

    def stop(self):
        self._running = False
        with self._lock:
            if self._proc:
                try:
                    self._proc.stdin.write("EXIT\n")
                    self._proc.stdin.flush()
                except: pass
                time.sleep(0.4)
                try: self._proc.terminate()
                except: pass

# ══════════════════════════════════════════════════════════════════════
# 5.  TASK POOL GENERATOR
# ══════════════════════════════════════════════════════════════════════
def _fig(mov: str, size: int = 240) -> str:
    img = Image.new("RGBA", (size, size), (245, 248, 255, 255))
    dr  = ImageDraw.Draw(img)
    cx, cy = size//2, size//2+8
    lw = 4; col = "#2c3e50"; hl = "#e74c3c"
    dr.ellipse([cx-24,cy-80,cx+24,cy-28],outline=col,width=lw)
    dr.line([cx,cy-28,cx,cy+48],fill=col,width=lw)
    dr.line([cx,cy+48,cx-22,cy+92],fill=col,width=lw)
    dr.line([cx,cy+48,cx+22,cy+92],fill=col,width=lw)
    if mov=="clap":
        dr.line([cx-40,cy,cx-4,cy+16],fill=col,width=lw)
        dr.line([cx+40,cy,cx+4,cy+16],fill=col,width=lw)
        dr.ellipse([cx-8,cy+12,cx+8,cy+26],fill=hl)
    elif mov=="wave":
        dr.line([cx-36,cy-2,cx-16,cy+16],fill=col,width=lw)
        dr.line([cx+36,cy-10,cx+60,cy-42],fill=col,width=lw)
        dr.line([cx+60,cy-42,cx+54,cy-60],fill=hl,width=4)
    elif mov=="raise_hand":
        dr.line([cx-36,cy-2,cx-16,cy+16],fill=col,width=lw)
        dr.line([cx+36,cy-10,cx+46,cy-66],fill=hl,width=5)
        dr.ellipse([cx+38,cy-80,cx+56,cy-62],fill=hl)
    elif mov=="touch_nose":
        nx,ny=cx,cy-54; dr.ellipse([nx-6,ny-6,nx+6,ny+6],fill=hl)
        dr.line([cx-36,cy,cx-6,cy-50],fill=hl,width=5)
        dr.line([cx+36,cy,cx+16,cy+16],fill=col,width=lw)
    elif mov=="arms_out":
        dr.line([cx-36,cy-2,cx-82,cy-2],fill=hl,width=5)
        dr.line([cx+36,cy-2,cx+82,cy-2],fill=hl,width=5)
    elif mov=="hands_up":
        dr.line([cx-36,cy-2,cx-50,cy-62],fill=hl,width=5)
        dr.line([cx+36,cy-2,cx+50,cy-62],fill=hl,width=5)
        dr.ellipse([cx-62,cy-76,cx-40,cy-56],fill=hl)
        dr.ellipse([cx+40,cy-76,cx+62,cy-56],fill=hl)
    elif mov=="point":
        dr.line([cx-36,cy-2,cx-16,cy+16],fill=col,width=lw)
        dr.line([cx+36,cy-10,cx+76,cy-2],fill=col,width=lw)
        dr.line([cx+76,cy-2,cx+96,cy-4],fill=hl,width=5)
    else:
        dr.line([cx-36,cy-2,cx-56,cy+14],fill=col,width=lw)
        dr.line([cx+36,cy-2,cx+56,cy+14],fill=col,width=lw)
    dr.text((cx-36,size-22),"👇 YOUR TURN!",fill=(231,76,60,255))
    buf = BytesIO(); img.save(buf,"PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

print("🎲 Rendering figures…")
FIGS = {m: _fig(m) for m in
        ["clap","wave","raise_hand","touch_nose","arms_out","hands_up","point"]}

COLORS  = [{"id":"red",   "color":"#ef4444","label":"🔴 RED"},
           {"id":"blue",  "color":"#3b82f6","label":"🔵 BLUE"},
           {"id":"green", "color":"#22c55e","label":"🟢 GREEN"},
           {"id":"yellow","color":"#eab308","label":"🟡 YELLOW"},
           {"id":"purple","color":"#a855f7","label":"🟣 PURPLE"},
           {"id":"orange","color":"#f97316","label":"🟠 ORANGE"},
           {"id":"pink",  "color":"#ec4899","label":"🩷 PINK"}]
ANIMALS = [{"id":"dog","emoji":"🐶","label":"Dog"},{"id":"cat","emoji":"🐱","label":"Cat"},
           {"id":"lion","emoji":"🦁","label":"Lion"},{"id":"elephant","emoji":"🐘","label":"Elephant"},
           {"id":"rabbit","emoji":"🐰","label":"Rabbit"},{"id":"bear","emoji":"🐻","label":"Bear"},
           {"id":"monkey","emoji":"🐵","label":"Monkey"},{"id":"tiger","emoji":"🐯","label":"Tiger"}]
FRUITS  = [{"id":"apple","emoji":"🍎","label":"Apple"},{"id":"banana","emoji":"🍌","label":"Banana"},
           {"id":"orange","emoji":"🍊","label":"Orange"},{"id":"grapes","emoji":"🍇","label":"Grapes"},
           {"id":"strawberry","emoji":"🍓","label":"Strawberry"},{"id":"mango","emoji":"🥭","label":"Mango"}]
SHAPES  = [{"id":"circle","emoji":"⭕","label":"Circle"},{"id":"square","emoji":"⬛","label":"Square"},
           {"id":"triangle","emoji":"🔺","label":"Triangle"},{"id":"star","emoji":"⭐","label":"Star"},
           {"id":"heart","emoji":"❤️","label":"Heart"},{"id":"diamond","emoji":"💎","label":"Diamond"}]
MOTORS  = [
    {"id":"clap","name":"👏 Clap","verify":"clap","prompts":["Clap!","Hands together!"],
     "instruction":"Look and CLAP your hands!","waiting":"I am waiting — clap! 👏",
     "success":"AMAZING! You clapped! ✅","fail":"Clap your hands together!"},
    {"id":"wave","name":"👋 Wave","verify":"wave","prompts":["Wave!","Side to side!"],
     "instruction":"Look and WAVE hello!","waiting":"Wave your hand! 👋",
     "success":"WONDERFUL! You waved! ✅","fail":"Wave side to side!"},
    {"id":"raise_hand","name":"✋ Raise Hand","verify":"raise_hand","prompts":["Hand up!","Higher!"],
     "instruction":"RAISE your hand HIGH!","waiting":"Raise your hand! ✋",
     "success":"PERFECT! Hand up! ✅","fail":"Lift arm above your head!"},
    {"id":"touch_nose","name":"👆 Touch Nose","verify":"touch_nose","prompts":["Touch nose!","Nose!"],
     "instruction":"TOUCH your NOSE!","waiting":"Touch your nose! 👆",
     "success":"BRILLIANT! You touched it! ✅","fail":"Point finger to nose!"},
    {"id":"arms_out","name":"🤸 Arms Wide","verify":"arms_out","prompts":["Arms out!","Wide!"],
     "instruction":"Stretch BOTH arms out WIDE!","waiting":"Spread arms! 🤸",
     "success":"AMAZING! Like an airplane! ✅","fail":"Spread both arms wide!"},
    {"id":"hands_up","name":"🙌 Hands Up","verify":"hands_up","prompts":["Both hands!","Up!"],
     "instruction":"Put BOTH hands UP!","waiting":"Both hands up! 🙌",
     "success":"SUPERSTAR! ✅","fail":"Lift BOTH arms above head!"},
    {"id":"point","name":"👉 Point","verify":"point","prompts":["Point!","Finger!"],
     "instruction":"POINT your finger!","waiting":"Point! 👉",
     "success":"GREAT pointing! ✅","fail":"Stretch index finger forward!"},
]
WORDS = ["apple","ball","cat","dog","elephant","fish","good","happy","jump",
         "kite","love","milk","play","red","sun","tree","water","yes","no",
         "one","two","three","four","five","six","seven","eight","nine","ten",
         "blue","green","bird","book","cup","door","eye","foot","hand","head"]

def gen_pool(n: int = 3000) -> list:
    pool = []
    for _ in range(int(n*.28)):
        m = random.choice(MOTORS)
        pool.append({**m,"domain":"Motor","level":1,"tablet_mode":"motor_model",
            "figure":FIGS.get(m["verify"],""),"tokens":2,"joy":"dance"})
    for _ in range(int(n*.13)):
        tgt=random.choice(COLORS); dis=random.sample([c for c in COLORS if c["id"]!=tgt["id"]],3)
        opts=[tgt]+dis; random.shuffle(opts); cor=next(i for i,o in enumerate(opts) if o["id"]==tgt["id"])
        pool.append({"id":f"color_{tgt['id']}","domain":"Cognitive","level":2,
            "name":f"🎨 {tgt['label']}","instruction":f"Click the {tgt['label']} color!",
            "waiting":f"Find {tgt['label']}!","success":f"CORRECT! {tgt['label']}! ✅",
            "fail":f"Find {tgt['label']}!","tablet_mode":"color_grid",
            "options":opts,"correct":cor,"tokens":3,"joy":"celebrate",
            "prompts":[f"Find {tgt['label']}!","Look carefully!"]})
    for _ in range(int(n*.12)):
        tgt=random.choice(ANIMALS); dis=random.sample([a for a in ANIMALS if a["id"]!=tgt["id"]],3)
        opts=[tgt]+dis; random.shuffle(opts); cor=next(i for i,o in enumerate(opts) if o["id"]==tgt["id"])
        pool.append({"id":f"animal_{tgt['id']}","domain":"Cognitive","level":3,
            "name":f"🐾 {tgt['label']}","instruction":f"Click the {tgt['label']}!",
            "waiting":f"Find the {tgt['label']}!","success":f"YES! {tgt['label']}! ✅",
            "fail":f"Find the {tgt['label']}!","tablet_mode":"object_grid",
            "options":opts,"correct":cor,"tokens":4,"joy":"dance","prompts":[f"Find {tgt['label']}!","Look!"]})
    for _ in range(int(n*.10)):
        tgt=random.choice(FRUITS); dis=random.sample([f for f in FRUITS if f["id"]!=tgt["id"]],3)
        opts=[tgt]+dis; random.shuffle(opts); cor=next(i for i,o in enumerate(opts) if o["id"]==tgt["id"])
        pool.append({"id":f"fruit_{tgt['id']}","domain":"Cognitive","level":4,
            "name":f"🍎 {tgt['label']}","instruction":f"Click the {tgt['label']}!",
            "waiting":f"Find {tgt['label']}!","success":f"DELICIOUS {tgt['label']}! ✅",
            "fail":f"Find {tgt['label']}!","tablet_mode":"object_grid",
            "options":opts,"correct":cor,"tokens":4,"joy":"celebrate","prompts":[f"Find {tgt['label']}!"]})
    for _ in range(int(n*.08)):
        tgt=random.choice(SHAPES); dis=random.sample([s for s in SHAPES if s["id"]!=tgt["id"]],3)
        opts=[tgt]+dis; random.shuffle(opts); cor=next(i for i,o in enumerate(opts) if o["id"]==tgt["id"])
        pool.append({"id":f"shape_{tgt['id']}","domain":"Cognitive","level":5,
            "name":f"🔷 {tgt['label']}","instruction":f"Click the {tgt['label']}!",
            "waiting":f"Find {tgt['label']}!","success":f"CORRECT SHAPE! ✅",
            "fail":f"Find the {tgt['label']}!","tablet_mode":"object_grid",
            "options":opts,"correct":cor,"tokens":4,"joy":"dance","prompts":[f"Find {tgt['label']}!"]})
    for _ in range(int(n*.10)):
        num = random.randint(1,10)
        pool.append({"id":f"count_{num}","domain":"Math","level":5,
            "name":f"🔢 Count {num}","instruction":f"Show me {num} finger{'s' if num>1 else ''}!",
            "waiting":f"Hold up {num} fingers! 🖐️","success":f"YES! {num} fingers! ✅",
            "fail":f"Show {num} fingers!","tablet_mode":"number_display","target_number":num,
            "verify":"finger_count","tokens":5,"joy":"celebrate","prompts":[f"Show {num}!","Count!"]})
    for _ in range(int(n*.17)):
        word=random.choice(WORDS)
        pool.append({"id":f"say_{word}","domain":"Verbal","level":6,
            "name":f"🗣️ Say '{word}'","instruction":f"Say the word: {word.upper()}!",
            "waiting":f"Tap mic → say {word}! 🎤","success":f"I HEARD {word.upper()}! ✅",
            "fail":f"Try again! Say: {word}!","tablet_mode":"word_display",
            "word_emoji":"🗣️","word_text":word.upper(),
            "verify":"speech_keyword","keyword":word,"tokens":4,"joy":"dance",
            "prompts":[f"Say {word}!",f"Tap mic → {word}!"]})
    random.shuffle(pool); return pool

print("🎲 Generating 3000 tasks…")
TASK_POOL = gen_pool(3000)
print(f"✅ {len(TASK_POOL)} tasks ready!")

# ══════════════════════════════════════════════════════════════════════
# 6.  SHARED STATE
# ══════════════════════════════════════════════════════════════════════
MAX_FAILS = 2; MASTERY_N = 3; MIC_ENERGY = 150

ST = {
    "name":CHILD_NAME,"age":int(CHILD_AGE) if CHILD_AGE.isdigit() else 6,
    "task_index":0,"consecutive":0,"fail_count":0,
    "tasks_mastered":0,"current_level":1,"domain":"Motor","protocol":"ABA",
    "tablet_click_result":None,"tablet_instruction":"Welcome!",
    # Vision
    "emotion":"neutral","emotion_pct":{"happy":0,"joyful":0,"sad":0,"angry":0,
                                        "fear":0,"surprised":0,"neutral":100},
    "emotion_conf":0.5,"face_detected":False,"attention":70,
    "hand_raised":False,"waving":False,"clapping":False,
    "arms_out":False,"hands_up":False,"pointing":False,
    "head_tilted":False,"blinking":False,"eye_contact":False,
    "finger_count":0,"finger_target":1,"body_motion":0.0,
    "pose_landmarks":{},"face_mesh_landmarks":{},
    "verify_action":None,"verify_result":False,"verify_timeout":0.0,
    "last_speech_text":"","last_sound":time.time(),"voice_energy":0.0,
    # Session
    "is_speaking":False,"interrupt_flag":False,"listening":False,
    "waiting_for_child":False,"recording":False,
    "sim_cmd":None,"lip_sync_value":0.0,"gaze_mode":"child",
    "social_joy_active":False,"eye_color":(100,180,255),
    "blink_timer":0.3,"head_tilt_val":0.0,
    # Progress
    "score":0,"tokens":0,"streak":0,
    "tasks_success":0,"tasks_fail":0,"tasks_skipped":0,
    "session_chat":[],"logs":[],"parent_notes":[],
    "skill_motor":50,"skill_cognitive":50,"skill_verbal":50,"skill_math":50,
    "att_history":[],"score_history":[],
    "session_start":datetime.now().strftime("%H:%M"),
    "session_date":datetime.now().strftime("%Y-%m-%d"),
    "uptime":time.time(),
    # YouTube embed
    "yt_url":"","yt_active":False,
    # Last camera frame (shared via bytes)
    "_camera_bytes":b"",
}
_ll = threading.Lock()

def LOG(msg, t="info"):
    with _ll:
        e = {"time":datetime.now().strftime("%H:%M:%S"),
             "msg":str(msg)[:120],"type":t,
             "emo":ST["emotion"],"proto":ST.get("protocol","—")}
        ST["logs"].append(e)
        if len(ST["logs"]) > 500: ST["logs"] = ST["logs"][-500:]
    print(f"[{datetime.now().strftime('%H:%M:%S')}][{t.upper()}] {msg[:70]}")

# ══════════════════════════════════════════════════════════════════════
# 7.  BRIDGE (ALL Qt UI via signals — prevents QBasicTimer crashes)
# ══════════════════════════════════════════════════════════════════════
class Bridge(QObject):
    sig_task       = pyqtSignal(dict)
    sig_success    = pyqtSignal(str)
    sig_fail       = pyqtSignal(str)
    sig_skip       = pyqtSignal(str)
    sig_feedback   = pyqtSignal(str)
    sig_instr      = pyqtSignal(str)
    sig_waiting    = pyqtSignal(str)
    sig_unlock     = pyqtSignal()
    sig_lock       = pyqtSignal()
    sig_reset      = pyqtSignal()
    sig_joy        = pyqtSignal(str)
    sig_camera     = pyqtSignal(object)   # QImage
    sig_stats      = pyqtSignal()
    sig_chat       = pyqtSignal(str,str)  # role,text
    sig_rec_start  = pyqtSignal()
    sig_rec_stop   = pyqtSignal(str)
    sig_youtube    = pyqtSignal(str)      # url

BRIDGE = Bridge()

# ══════════════════════════════════════════════════════════════════════
# 8.  CAMERA + MEDIAPIPE THREAD
#     FaceMesh TESSELATION for real-time emotion grid
# ══════════════════════════════════════════════════════════════════════
class CameraThread(QThread):
    def __init__(self):
        super().__init__()
        self.running = False; self.cap = None
        self._pose = None; self._hands = None; self._face = None
        self._phase = 0.0; self._prev_gray = None
        self._hand_hist = []; self._motion_buf = []
        self._emo_smooth = {k:0.0 for k in
            ["happy","joyful","sad","angry","fear","surprised","neutral"]}
        self._init_mp(); self._init_cam()

    def _init_mp(self):
        try:
            self._pose = mp.solutions.pose.Pose(
                min_detection_confidence=0.55, min_tracking_confidence=0.55,
                model_complexity=1); print("✅ MP Pose")
        except Exception as e: print(f"⚠️  Pose: {e}")
        try:
            self._hands = mp.solutions.hands.Hands(
                max_num_hands=2, min_detection_confidence=0.55,
                min_tracking_confidence=0.55); print("✅ MP Hands (10-finger)")
        except Exception as e: print(f"⚠️  Hands: {e}")
        try:
            self._face = mp.solutions.face_mesh.FaceMesh(
                max_num_faces=1, min_detection_confidence=0.5,
                min_tracking_confidence=0.5, refine_landmarks=True)
            print("✅ MP FaceMesh TESSELATION (emotion grid)")
        except Exception as e: print(f"⚠️  FaceMesh: {e}")

    def _init_cam(self):
        for idx in [1, 0, 2]:
            try:
                c = cv2.VideoCapture(idx)
                if c.isOpened():
                    ret, f = c.read()
                    if ret and f is not None and f.size > 0:
                        c.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                        c.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                        c.set(cv2.CAP_PROP_FPS, 30)
                        self.cap = c; print(f"✅ Camera {idx}"); return
                    c.release()
            except: pass
        print("⚠️  No camera — sim")

    def _angle(self, a, b, c_):
        try:
            ab=np.array([a.x-b.x,a.y-b.y,a.z-b.z])
            cb=np.array([c_.x-b.x,c_.y-b.y,c_.z-b.z])
            cos_a=np.dot(ab,cb)/(np.linalg.norm(ab)*np.linalg.norm(cb)+1e-6)
            return math.degrees(math.acos(np.clip(cos_a,-1,1)))
        except: return 0.0

    def _fingers(self, lm):
        try:
            tips=[8,12,16,20]; n=0
            if lm.landmark[4].x < lm.landmark[3].x: n+=1
            for t in tips:
                if lm.landmark[t].y < lm.landmark[t-2].y: n+=1
            return n
        except: return 0

    def _emotion_geometry(self, lm, w, h):
        """
        Full FaceMesh geometry → emotion scores dict.
        Returns dict {emotion: 0-100}
        """
        try:
            def ear(eye):
                pts=[(lm[i].x*w,lm[i].y*h) for i in eye]
                A=math.dist(pts[1],pts[5]); B=math.dist(pts[2],pts[4])
                C=math.dist(pts[0],pts[3]); return (A+B)/(2*C+1e-6)
            ear_l = ear([362,385,387,263,373,380])
            ear_r = ear([33,160,158,133,153,144])
            ear_avg=(ear_l+ear_r)/2.0
            ul=lm[13]; ll=lm[14]; lc=lm[78]; rc=lm[308]
            mar=(math.dist((ul.x*w,ul.y*h),(ll.x*w,ll.y*h))/
                 (math.dist((lc.x*w,lc.y*h),(rc.x*w,rc.y*h))+1e-6))
            lb=lm[107]; le_t=lm[159]; rb=lm[336]; re_t=lm[386]
            brow=((lb.y-le_t.y)+(rb.y-re_t.y))/2.0
            lch=lm[116]; rch=lm[345]; nose=lm[4]
            cheek_h=((lch.y+rch.y)/2.0-nose.y)*h
            # Compute raw scores (0-1)
            sc={k:0.0 for k in self._emo_smooth}
            sc["happy"]    = min(1.0, max(0,(mar-0.20)*3.5)   * (1 if cheek_h<-3 else 0.5))
            sc["joyful"]   = min(1.0, max(0,(mar-0.25)*2.5))
            sc["surprised"]= min(1.0, max(0,(0.22-ear_avg)*8))
            sc["angry"]    = min(1.0, max(0, brow*30)          * max(0,(0.25-mar)*4))
            sc["sad"]      = min(1.0, max(0, brow*20)          * max(0,(0.30-mar)*3))
            sc["fear"]     = min(1.0, max(0,(0.22-ear_avg)*5)  * max(0,(0.25-mar)*3))
            total = sum(sc.values()) or 1e-6
            for k in sc: sc[k] = sc[k]/total
            sc["neutral"] = max(0.0, 1.0-sum(sc[k] for k in sc if k!="neutral"))
            total2 = sum(sc.values()) or 1e-6
            for k in sc: sc[k] /= total2
            # Smooth with EMA
            for k in self._emo_smooth:
                self._emo_smooth[k] = 0.80*self._emo_smooth[k] + 0.20*sc.get(k,0)
            # Pick dominant
            dom = max(self._emo_smooth, key=self._emo_smooth.get)
            conf= self._emo_smooth[dom]
            return dom, conf, {k:int(v*100) for k,v in self._emo_smooth.items()}
        except Exception:
            return "neutral", 0.5, {k:0 for k in self._emo_smooth}

    def _validate_motor(self):
        va = ST.get("verify_action")
        if not va: return
        if time.time() > ST["verify_timeout"]: ST["verify_action"]=None; return
        pl = ST.get("pose_landmarks",{}); fm = ST.get("face_mesh_landmarks",{})
        ok = False
        if   va=="clap":       ok=ST["clapping"]
        elif va=="wave":       ok=ST["waving"]
        elif va=="raise_hand":
            lwy=pl.get("l_wrist_y",1); rwy=pl.get("r_wrist_y",1)
            lsy=pl.get("l_shoulder_y",0); rsy=pl.get("r_shoulder_y",0)
            lea=pl.get("l_elbow_angle",0); rea=pl.get("r_elbow_angle",0)
            ok=((lwy<lsy-0.07 and lea>110) or (rwy<rsy-0.07 and rea>110))
        elif va=="touch_nose":
            nx=fm.get("nose_x",-1); ny=fm.get("nose_y",-1)
            fw=fm.get("frame_w",640); fh=fm.get("frame_h",480)
            if nx>0 and pl:
                lix=pl.get("l_index_x",0)*fw; liy=pl.get("l_index_y",0)*fh
                rix=pl.get("r_index_x",0)*fw; riy=pl.get("r_index_y",0)*fh
                ok=(math.dist((lix,liy),(nx,ny))<fw*0.13 or
                    math.dist((rix,riy),(nx,ny))<fw*0.13)
        elif va=="arms_out":  ok=(pl.get("l_shoulder_angle",0)>65 and pl.get("r_shoulder_angle",0)>65)
        elif va=="hands_up":  ok=ST.get("hands_up",False)
        elif va=="point":
            if pl:
                rix=pl.get("r_index_x",0); riy=pl.get("r_index_y",0)
                rwy2=pl.get("r_wrist_y",1)
                ok=(rix>0.57 and abs(riy-rwy2)<0.12)
        elif va=="finger_count": ok=(ST["finger_count"]==ST["finger_target"])
        if ok:
            ST["verify_result"]=True; ST["verify_action"]=None
            ST["verify_timeout"]=0.0; LOG("✅ Motor verified!","success")

    def _sim_frame(self):
        self._phase+=0.04
        f=np.zeros((480,640,3),dtype=np.uint8); f[:]=(10,12,28)
        r=int(28+10*math.sin(self._phase))
        cv2.circle(f,(320,200),r,
            (int(80+80*math.sin(self._phase)),
             int(120+120*math.cos(self._phase*.7)),220),3)
        cv2.putText(f,"NO CAMERA",(220,240),cv2.FONT_HERSHEY_SIMPLEX,0.7,(100,150,255),2)
        return f

    def run(self):
        self.running = True
        while self.running:
            # Grab
            if self.cap and self.cap.isOpened():
                ret,frame=self.cap.read()
                frame=cv2.flip(frame,1) if (ret and frame is not None) else self._sim_frame()
            else:
                frame=self._sim_frame()

            # ── Motion ──────────────────────────────────────────
            gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
            gray=cv2.GaussianBlur(gray,(21,21),0)
            if self._prev_gray is not None:
                diff=cv2.absdiff(self._prev_gray,gray)
                _,th=cv2.threshold(diff,25,255,cv2.THRESH_BINARY)
                motion=float(np.mean(th)); ST["body_motion"]=motion
                self._motion_buf.append(motion)
                if len(self._motion_buf)>12: self._motion_buf.pop(0)
                if len(self._motion_buf)>=4:
                    avg=sum(self._motion_buf[:-2])/max(len(self._motion_buf)-2,1)
                    ST["clapping"]=(self._motion_buf[-1]>avg*3.2 and self._motion_buf[-1]>12)
                h2,w2=gray.shape
                lm_=float(np.mean(th[:,:w2//2])); rm_=float(np.mean(th[:,w2//2:]))
                self._hand_hist.append("L" if lm_>rm_+3 else "R" if rm_>lm_+3 else "N")
                if len(self._hand_hist)>10: self._hand_hist.pop(0)
                chg=sum(1 for i in range(1,len(self._hand_hist))
                        if self._hand_hist[i]!=self._hand_hist[i-1] and self._hand_hist[i]!="N")
                ST["waving"]=chg>=3
            self._prev_gray=gray

            # ── Pose ─────────────────────────────────────────────
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
                        lsa=self._angle(lm[PL.LEFT_ELBOW],lm[PL.LEFT_SHOULDER],lm[PL.LEFT_HIP])
                        rsa=self._angle(lm[PL.RIGHT_ELBOW],lm[PL.RIGHT_SHOULDER],lm[PL.RIGHT_HIP])
                        lea=self._angle(lm[PL.LEFT_SHOULDER],lm[PL.LEFT_ELBOW],lm[PL.LEFT_WRIST])
                        rea=self._angle(lm[PL.RIGHT_SHOULDER],lm[PL.RIGHT_ELBOW],lm[PL.RIGHT_WRIST])
                        h_,w_=frame.shape[:2]
                        pl={"nose_x":lm[PL.NOSE].x,"nose_y":lm[PL.NOSE].y,
                            "l_ear_x":lm[PL.LEFT_EAR].x,"r_ear_x":lm[PL.RIGHT_EAR].x,
                            "l_shoulder_y":lm[PL.LEFT_SHOULDER].y,"r_shoulder_y":lm[PL.RIGHT_SHOULDER].y,
                            "l_wrist_y":lm[PL.LEFT_WRIST].y,"r_wrist_y":lm[PL.RIGHT_WRIST].y,
                            "l_wrist_x":lm[PL.LEFT_WRIST].x,"r_wrist_x":lm[PL.RIGHT_WRIST].x,
                            "l_index_x":lm[PL.LEFT_INDEX].x,"l_index_y":lm[PL.LEFT_INDEX].y,
                            "r_index_x":lm[PL.RIGHT_INDEX].x,"r_index_y":lm[PL.RIGHT_INDEX].y,
                            "l_elbow_angle":lea,"r_elbow_angle":rea,
                            "l_shoulder_angle":lsa,"r_shoulder_angle":rsa}
                        ST["pose_landmarks"]=pl
                        ST["hand_raised"]=(pl["l_wrist_y"]<pl["l_shoulder_y"]-0.07 or
                                           pl["r_wrist_y"]<pl["r_shoulder_y"]-0.07)
                        ST["arms_out"]=(lsa>65 and rsa>65)
                        ST["hands_up"]=(pl["l_wrist_y"]<pl["l_shoulder_y"]-0.07 and
                                        pl["r_wrist_y"]<pl["r_shoulder_y"]-0.07)
                        ST["head_tilted"]=(abs(pl["nose_x"]-pl["l_ear_x"])<0.11 or
                                           abs(pl["nose_x"]-pl["r_ear_x"])<0.11)
                        ST["face_detected"]=True; ST["attention"]=min(100,ST["attention"]+1)
                        ST["face_mesh_landmarks"].update(
                            {"nose_x":lm[PL.NOSE].x*w_,"nose_y":lm[PL.NOSE].y*h_,
                             "frame_w":w_,"frame_h":h_})
                except: pass

            # ── FaceMesh + TESSELATION emotion grid ───────────────
            if self._face:
                try:
                    rgb=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
                    fres=self._face.process(rgb)
                    if fres.multi_face_landmarks:
                        h_,w_=frame.shape[:2]
                        fl=fres.multi_face_landmarks[0].landmark
                        # Draw TESSELATION grid
                        mp.solutions.drawing_utils.draw_landmarks(
                            frame,fres.multi_face_landmarks[0],
                            mp.solutions.face_mesh.FACEMESH_TESSELATION,
                            landmark_drawing_spec=None,
                            connection_drawing_spec=mp.solutions.drawing_utils.DrawingSpec(
                                color=(0,200,255),thickness=1))
                        # Contours
                        mp.solutions.drawing_utils.draw_landmarks(
                            frame,fres.multi_face_landmarks[0],
                            mp.solutions.face_mesh.FACEMESH_CONTOURS,
                            landmark_drawing_spec=None,
                            connection_drawing_spec=mp.solutions.drawing_utils.DrawingSpec(
                                color=(255,100,0),thickness=1))
                        em,conf,pct=self._emotion_geometry(fl,w_,h_)
                        ST["emotion"]=em; ST["emotion_conf"]=conf
                        ST["emotion_pct"]=pct; ST["face_detected"]=True
                        ST["attention"]=min(100,ST["attention"]+2)
                        def ear(eye):
                            pts=[(fl[i].x*w_,fl[i].y*h_) for i in eye]
                            A=math.dist(pts[1],pts[5]); B=math.dist(pts[2],pts[4])
                            C=math.dist(pts[0],pts[3]); return (A+B)/(2*C+1e-6)
                        ea=(ear([33,160,158,133,153,144])+ear([362,385,387,263,373,380]))/2
                        ST["blinking"]=ea<0.17; ST["eye_contact"]=ea>0.23
                        ST["blink_timer"]=ea; ST["head_tilt_val"]=fl[1].x-0.5
                        ul=fl[13]; ll=fl[14]
                        ST["face_mesh_landmarks"].update(
                            {"nose_x":fl[1].x*w_,"nose_y":fl[1].y*h_,
                             "ear_avg":ea,"frame_w":w_,"frame_h":h_,
                             "mouth_open":(ll.y-ul.y)*h_})
                    else:
                        ST["face_detected"]=False; ST["attention"]=max(0,ST["attention"]-2)
                except: pass

            # ── Hands ─────────────────────────────────────────────
            if self._hands:
                try:
                    rgb=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
                    hres=self._hands.process(rgb)
                    if hres.multi_hand_landmarks:
                        total=0
                        for hlm in hres.multi_hand_landmarks:
                            mp.solutions.drawing_utils.draw_landmarks(
                                frame,hlm,mp.solutions.hands.HAND_CONNECTIONS,
                                mp.solutions.drawing_utils.DrawingSpec(color=(255,100,0),thickness=2,circle_radius=3),
                                mp.solutions.drawing_utils.DrawingSpec(color=(255,200,0),thickness=2))
                            total+=self._fingers(hlm)
                        ST["finger_count"]=min(10,total)
                        if len(hres.multi_hand_landmarks)>=2:
                            h1=hres.multi_hand_landmarks[0].landmark[0]
                            h2_=hres.multi_hand_landmarks[1].landmark[0]
                            if abs(h1.x-h2_.x)<0.18 and abs(h1.y-h2_.y)<0.18:
                                ST["clapping"]=True
                    else: ST["finger_count"]=0
                except: pass

            self._validate_motor()

            # HUD
            h_,w_=frame.shape[:2]
            cv2.rectangle(frame,(0,0),(w_,42),(8,10,24),-1)
            tidx=min(ST["task_index"],len(TASK_POOL)-1)
            t_=TASK_POOL[tidx]
            cv2.putText(frame,f"Task:{t_.get('name',t_['id'])[:24]}",
                (8,18),cv2.FONT_HERSHEY_SIMPLEX,0.50,(200,200,255),1)
            suc=ST["consecutive"]
            cv2.putText(frame,f"{'★'*suc}{'☆'*(3-suc)} | {ST['emotion']} | {CHILD_NAME}",
                (8,36),cv2.FONT_HERSHEY_SIMPLEX,0.44,(255,220,0),1)
            if ST["recording"]:
                cv2.circle(frame,(w_-18,18),8,(0,0,255),-1)

            # Emit to Qt
            rgb=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
            h_,w_,ch=rgb.shape
            qi=QImage(rgb.data.tobytes(),w_,h_,w_*ch,QImage.Format.Format_RGB888)
            BRIDGE.sig_camera.emit(qi)

            if int(time.time())%3==0:
                ST["att_history"].append(ST["attention"])
                ST["score_history"].append(ST["score"])
                for k in ["att_history","score_history"]:
                    if len(ST[k])>60: ST[k]=ST[k][-60:]

            self.msleep(16)

    def stop(self):
        self.running=False; self.quit(); self.wait(2000)
        if self.cap: self.cap.release()

# ══════════════════════════════════════════════════════════════════════
# 9.  VOICE
# ══════════════════════════════════════════════════════════════════════
class Voice:
    def __init__(self):
        self.ok=False; self._lk=threading.Lock()
        try:
            self.e=pyttsx3.init(); self.e.setProperty("rate",116)
            self.e.setProperty("volume",1.0)
            for v in self.e.getProperty("voices"):
                if any(x in v.name.lower() for x in ["female","zira","hazel","karen"]):
                    self.e.setProperty("voice",v.id); break
            self.ok=True; print("✅ TTS Voice")
        except Exception as ex: print(f"⚠️  TTS: {ex}")

    def _lip(self,text):
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
        clean=re.sub(r"\[[^\]]+\]","",str(text)).strip()
        if not clean: return
        ST["is_speaking"]=True
        ST["session_chat"].append({"role":"pepper","text":clean,
            "time":datetime.now().strftime("%H:%M:%S")})
        if len(ST["session_chat"])>60: ST["session_chat"]=ST["session_chat"][-60:]
        print(f"\n🔊 Pepper: {clean}")
        threading.Thread(target=self._lip,args=(clean,),daemon=True).start()
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

# ══════════════════════════════════════════════════════════════════════
# 10. TOUCH RECORDER
# ══════════════════════════════════════════════════════════════════════
class TouchRecorder:
    def __init__(self):
        self._lock=threading.Lock(); self._recording=False; self._audio=None
        self.whisper=None
        self.r=sr.Recognizer()
        self.r.energy_threshold=MIC_ENERGY
        self.r.dynamic_energy_threshold=True
        self.r.pause_threshold=0.6; self.r.phrase_threshold=0.04
        self.r.non_speaking_duration=0.2
        try:
            with sr.Microphone() as src:
                print("🎤 Calibrating mic…")
                self.r.adjust_for_ambient_noise(src,duration=0.4)
            print(f"✅ Mic energy={self.r.energy_threshold:.0f}")
        except Exception as e: print(f"⚠️  Mic: {e}")
        if _FW_OK:
            try:
                dev="cuda" if os.path.exists("/dev/nvidia0") else "cpu"
                self.whisper=FW("tiny",device=dev,
                    compute_type="float16" if dev=="cuda" else "int8")
                print(f"✅ faster-whisper ({dev})")
            except Exception as e: print(f"⚠️  Whisper: {e}")

    def start(self):
        with self._lock:
            if self._recording: return
            self._recording=True; self._audio=None
        ST["recording"]=True; BRIDGE.sig_rec_start.emit()
        threading.Thread(target=self._capture,daemon=True).start()

    def _capture(self):
        try:
            with sr.Microphone() as src:
                self.r.adjust_for_ambient_noise(src,duration=0.06)
                audio=self.r.listen(src,timeout=12,phrase_time_limit=10)
                with self._lock: self._audio=audio
        except: pass
        finally:
            with self._lock: self._recording=False
            ST["recording"]=False

    def stop_and_recognise(self)->str:
        for _ in range(30):
            with self._lock:
                if not self._recording: break
            time.sleep(0.05)
        with self._lock: audio=self._audio
        if not audio: return ""
        if self.whisper:
            try:
                raw=audio.get_raw_data(convert_rate=16000,convert_width=2)
                with tempfile.NamedTemporaryFile(suffix=".wav",delete=False) as tmp: tp=tmp.name
                with wave.open(tp,"wb") as wf:
                    wf.setnchannels(1); wf.setsampwidth(2)
                    wf.setframerate(16000); wf.writeframes(raw)
                segs,_=self.whisper.transcribe(tp,language="en",beam_size=2,
                    condition_on_previous_text=False)
                text=" ".join(s.text.strip() for s in segs).strip()
                os.unlink(tp)
                if text: LOG(f"Whisper: {text}"); return text.lower()
            except Exception as e: LOG(f"Whisper err: {e}","warn")
        try:
            text=self.r.recognize_google(audio); LOG(f"Google: {text}"); return text.lower()
        except: return ""

# ══════════════════════════════════════════════════════════════════════
# 11. BALLOON CELEBRATION (QPropertyAnimation — non-blocking)
# ══════════════════════════════════════════════════════════════════════
class BalloonLabel(QLabel):
    def __init__(self,parent,emoji,start_x,start_y):
        super().__init__(emoji,parent)
        self.setFont(QFont("Arial",random.randint(24,40)))
        self.setStyleSheet("background:transparent;color:transparent;")
        self.setText(emoji)
        self.move(start_x,start_y)
        self.show(); self.raise_()
        self._anim=QPropertyAnimation(self,b"pos")
        self._anim.setDuration(random.randint(2500,4000))
        self._anim.setStartValue(QPoint(start_x,start_y))
        self._anim.setEndValue(QPoint(start_x+random.randint(-120,120),-60))
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.finished.connect(self.deleteLater)
        self._anim.start()

def launch_balloons(parent:QWidget, n:int=18):
    emojis=["🎈","🎉","⭐","🌟","🎊","✨","💫","🏆","🎁","💝"]
    w=parent.width()
    for _ in range(n):
        sx=random.randint(40,max(50,w-40))
        sy=parent.height()+20
        BalloonLabel(parent,random.choice(emojis),sx,sy)

# ══════════════════════════════════════════════════════════════════════
# 12. CLICK CARDS
# ══════════════════════════════════════════════════════════════════════
class ClickCard(QPushButton):
    def __init__(self,data,idx,mode,parent=None):
        super().__init__(parent)
        self.idx=idx; self.mode=mode; self._data=data
        self.setFixedSize(144,144); self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._set_normal()
        self.clicked.connect(lambda:BRIDGE.sig_task.emit({"action":"click","idx":self.idx}))
    def _set_normal(self):
        d=self._data; m=self.mode
        if m=="color_grid":
            self.setText(f"\n\n{d['label']}")
            self.setFont(QFont("Arial",11,QFont.Weight.Bold))
            self.setStyleSheet(f"""QPushButton{{background:{d['color']};border-radius:72px;
                border:5px solid rgba(255,255,255,0.3);color:white;font-weight:bold;
                text-shadow:1px 1px 4px rgba(0,0,0,.9);}}QPushButton:hover{{border:5px solid white;}}""")
        elif m in ["object_grid","shape_grid","emotion_grid"]:
            self.setText(f"{d['emoji']}\n{d['label']}")
            self.setFont(QFont("Arial",12,QFont.Weight.Bold))
            self.setStyleSheet("""QPushButton{background:qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 #1e1b4b,stop:1 #0c0f2e);border-radius:18px;
                border:4px solid #4f46e5;color:#e0e6ff;font-weight:bold;padding:6px;}
                QPushButton:hover{border:4px solid #a78bfa;}""")
    def flash_correct(self):
        b=self.styleSheet().split("QPushButton:hover")[0]
        self.setStyleSheet(b+"QPushButton{border:8px solid #22c55e !important;}")
    def flash_wrong(self):
        b=self.styleSheet().split("QPushButton:hover")[0]
        self.setStyleSheet(b+"QPushButton{border:8px solid #ef4444 !important;opacity:0.45;}")
    def reset(self): self._set_normal()

# ══════════════════════════════════════════════════════════════════════
# 13. AVATAR WIDGET (embedded in main window)
# ══════════════════════════════════════════════════════════════════════
class AvatarWidget(QWidget):
    """
    Animated Pepper avatar painted in pure Qt.
    Embedded directly in the dashboard — NOT a separate window.
    """
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setFixedSize(220,280)
        self._phase=0.0
        self._timer=QTimer()
        self._timer.timeout.connect(self._tick)
        self._timer.start(40)   # 25 fps

    def _tick(self):
        self._phase+=0.12 if ST["is_speaking"] else 0.03
        self.update()   # trigger paintEvent — safe on main thread

    def paintEvent(self,event):
        p=QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(),QColor(8,10,22))

        em=ST["emotion"]; lip=ST.get("lip_sync_value",0.0)
        sj=ST.get("social_joy_active",False)
        blink=ST.get("blinking",False) or (int(self._phase*3)%44==0)
        ht=ST.get("head_tilt_val",0.0)*6
        cx,cy=110,130

        # Body
        g=QLinearGradient(cx-42,cy+50,cx+42,cy+130)
        g.setColorAt(0,QColor(70,90,190)); g.setColorAt(1,QColor(50,70,160))
        p.setBrush(QBrush(g)); p.setPen(QPen(QColor(100,120,210),2))
        p.drawEllipse(cx-42,cy+50,84,80)

        # Arms
        jt=time.time()
        p.setPen(QPen(QColor(70,90,190),14,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap))
        if sj:
            la=int(22*math.sin(jt*4)); ra=int(22*math.sin(jt*4+1))
            p.drawLine(cx-42,cy+60,cx-80+la,cy+20+la)
            p.drawLine(cx+42,cy+60,cx+80+ra,cy+20+ra)
        elif ST["is_speaking"]:
            la=int(16*math.sin(self._phase))
            p.drawLine(cx-42,cy+65,cx-70+la,cy+95+la)
            p.drawLine(cx+42,cy+65,cx+70-la,cy+95-la)
        else:
            p.drawLine(cx-42,cy+68,cx-68,cy+100)
            p.drawLine(cx+42,cy+68,cx+68,cy+100)
        # Legs
        p.drawLine(cx-18,cy+128,cx-28,cy+160)
        p.drawLine(cx+18,cy+128,cx+28,cy+160)

        # Head
        hbob=int(3*math.sin(self._phase*0.5))
        hx=cx+int(ht); hy=cy-55+hbob
        p.setBrush(QBrush(QColor(220,195,173)))
        p.setPen(QPen(QColor(200,175,155),2))
        p.drawEllipse(hx-44,hy-44,88,88)

        # Eyes
        ec=QColor(*ST["eye_color"]) if sj else QColor(100,180,255)
        p.setBrush(QBrush(ec)); p.setPen(Qt.PenStyle.NoPen)
        ey=5 if not blink else 1
        for ex_ in [hx-15,hx+15]:
            p.drawEllipse(ex_-5,hy-ey-6,10,ey*2)
            if not blink:
                p.setBrush(QBrush(QColor(255,255,255)))
                p.drawEllipse(ex_,hy-10,4,4)
                p.setBrush(QBrush(QColor(0,0,0)))
                p.drawEllipse(ex_+1,hy-9,2,2)
                p.setBrush(QBrush(ec))
        # Nose
        p.setBrush(QBrush(QColor(180,140,120))); p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(hx-4,hy+4,8,8)
        # Mouth
        p.setPen(QPen(QColor(160,80,80),2))
        mh=int(4+lip*14)
        if ST["is_speaking"]:
            p.setBrush(QBrush(QColor(160,80,80)))
            p.drawChord(hx-12,hy+16,24,mh*2,0,-180*16)
            if lip>0.3:
                p.setBrush(QBrush(QColor(240,230,220)))
                p.drawChord(hx-9,hy+18,18,max(2,mh*2-4),0,-180*16)
        elif em in ["happy","joyful"]:
            p.setBrush(QBrush(QColor(150,80,80)))
            p.drawChord(hx-11,hy+17,22,12,0,-180*16)
        else:
            p.drawLine(hx-10,hy+20,hx+10,hy+20)
        # Ears
        p.setBrush(QBrush(QColor(210,185,163))); p.setPen(Qt.PenStyle.NoPen)
        for ex_ in [hx-44,hx+36]:
            p.drawEllipse(ex_,hy-8,16,16)
        # Status ring
        if sj:
            pr=int(80+12*abs(math.sin(jt*4)))
            jc=QColor(int(128+127*math.sin(jt*3)),int(200+55*math.sin(jt*2)),255)
            p.setPen(QPen(jc,3)); p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(cx-pr,cy-pr,pr*2,pr*2)
        elif ST["is_speaking"]:
            pr=int(80+5*math.sin(self._phase*5))
            p.setPen(QPen(QColor(0,160,255),2)); p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(cx-pr,cy-pr,pr*2,pr*2)
        elif ST["recording"]:
            p.setPen(QPen(QColor(255,0,0),2)); p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(cx-78,cy-78,156,156)
        # Status text
        p.setPen(QColor(160,140,255)); f=QFont("Arial",7,QFont.Weight.Bold)
        p.setFont(f)
        if sj:    p.drawText(self.rect().adjusted(0,240,0,0),Qt.AlignmentFlag.AlignCenter,"SOCIAL JOY! 🎉")
        elif ST["is_speaking"]: p.drawText(self.rect().adjusted(0,240,0,0),Qt.AlignmentFlag.AlignCenter,"SPEAKING 🔊")
        elif ST["recording"]:   p.drawText(self.rect().adjusted(0,240,0,0),Qt.AlignmentFlag.AlignCenter,"RECORDING 🔴")
        elif ST["listening"]:   p.drawText(self.rect().adjusted(0,240,0,0),Qt.AlignmentFlag.AlignCenter,"LISTENING 👂")
        else:                   p.drawText(self.rect().adjusted(0,240,0,0),Qt.AlignmentFlag.AlignCenter,"READY 💤")
        p.end()

# ══════════════════════════════════════════════════════════════════════
# 14. EMOTION PANEL WIDGET (embedded — live % bars)
# ══════════════════════════════════════════════════════════════════════
ECOL_QT = {
    "happy":(0,220,80),"joyful":(0,255,180),"sad":(100,100,220),
    "angry":(255,60,60),"fear":(0,180,220),"surprised":(200,50,220),
    "neutral":(180,180,180),
}

class EmotionPanel(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setFixedSize(220,280)
        self._timer=QTimer(); self._timer.timeout.connect(self.update); self._timer.start(200)

    def paintEvent(self,event):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(),QColor(10,12,28))
        # Title
        p.setPen(QColor(0,200,255)); p.setFont(QFont("Arial",9,QFont.Weight.Bold))
        p.drawText(QRect(0,2,220,18),Qt.AlignmentFlag.AlignCenter,"EMOTION GRID")
        # Big emotion circle
        em=ST["emotion"]; conf=ST.get("emotion_conf",0.5)
        col=QColor(*ECOL_QT.get(em,(180,180,180)))
        p.setBrush(QBrush(col)); p.setPen(QPen(QColor(255,255,255),2))
        p.drawEllipse(80,22,60,60)
        p.setPen(QColor(255,255,255)); p.setFont(QFont("Arial",8,QFont.Weight.Bold))
        p.drawText(QRect(80,22,60,60),Qt.AlignmentFlag.AlignCenter,em[:7].upper())
        # Conf bar
        bw=int(conf*210); p.setBrush(QBrush(QColor(25,28,50))); p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(5,88,210,10,4,4)
        p.setBrush(QBrush(col)); p.drawRoundedRect(5,88,bw,10,4,4)
        p.setPen(QColor(200,200,200)); p.setFont(QFont("Arial",7))
        p.drawText(QRect(0,100,220,14),Qt.AlignmentFlag.AlignCenter,
                   f"Conf:{conf:.0%}  Face:{'✓' if ST['face_detected'] else '✗'}")
        # Per-emotion bars
        pct=ST.get("emotion_pct",{})
        emos=list(ECOL_QT.keys()); y0=116
        for em_ in emos:
            val=pct.get(em_,0); bar=int(val*1.44); ec_=QColor(*ECOL_QT.get(em_,(150,150,150)))
            p.setBrush(QBrush(QColor(22,25,45))); p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(4,y0,145,14,3,3)
            if bar>0: p.setBrush(QBrush(ec_)); p.drawRoundedRect(4,y0,bar,14,3,3)
            p.setPen(QColor(200,200,200)); p.setFont(QFont("Arial",7))
            p.drawText(QRect(152,y0,64,14),Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter,
                       f"{em_[:6]} {val}%")
            y0+=18
        # Finger count
        fc=ST["finger_count"]
        p.setPen(QColor(255,200,0)); p.setFont(QFont("Arial",8,QFont.Weight.Bold))
        p.drawText(QRect(0,244,220,18),Qt.AlignmentFlag.AlignCenter,
                   f"Fingers:{fc} {'|'*min(fc,10)}")
        p.setPen(QColor(100,100,140)); p.setFont(QFont("Arial",7))
        p.drawText(QRect(0,260,220,16),Qt.AlignmentFlag.AlignCenter,
                   f"Att:{ST['attention']}% | Motion:{ST.get('body_motion',0):.1f}")
        p.end()

# ══════════════════════════════════════════════════════════════════════
# 15. SINGLE MAIN WINDOW
# ══════════════════════════════════════════════════════════════════════
class MainWindow(QMainWindow):
    """
    Single QMainWindow — no separate windows.
    Layout:
      ┌──────────────────────────────────────────────────────────────┐
      │  LEFT COLUMN (660px)         │  RIGHT COLUMN (660px)         │
      │  ┌────────────┐ ┌──────────┐│  [Header]                     │
      │  │Camera 440px│ │Avatar    ││  [TEACCH Schedule]            │
      │  │            │ │220×280   ││  [Instruction]                │
      │  │            │ ├──────────┤│  [Content — cards/figure]     │
      │  │            │ │Emotion   ││  [Feedback]                   │
      │  │            │ │Panel     ││  [Mic button]                 │
      │  │            │ │220×280   ││  [Stats]                      │
      │  └────────────┘ └──────────┘│                               │
      │  [Chat area + input]        │                               │
      └──────────────────────────────────────────────────────────────┘
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Pepper Clinical Infinity V4 — {CHILD_NAME}")
        self.setFixedSize(1320,800)
        self.setWindowFlags(Qt.WindowType.Window|
            Qt.WindowType.WindowStaysOnTopHint|
            Qt.WindowType.CustomizeWindowHint|
            Qt.WindowType.WindowTitleHint)
        self._cards=[]; self._locked=True; self._correct_idx=-1
        self._joy_phase=0.0
        self._joy_timer=QTimer(); self._joy_timer.timeout.connect(self._joy_tick)
        self._recorder=TouchRecorder()
        self._build_ui()
        self._connect_bridge()
        self._stats_t=QTimer(); self._stats_t.timeout.connect(self._refresh_stats)
        self._stats_t.start(400)

    # ── BUILD ─────────────────────────────────────────────────────
    def _build_ui(self):
        root=QWidget(); self.setCentralWidget(root)
        root.setStyleSheet("QWidget{background:#060918;}")
        main=QHBoxLayout(root); main.setSpacing(0); main.setContentsMargins(0,0,0,0)

        # ════ LEFT COLUMN ════════════════════════════════════════
        left=QFrame(); left.setFixedWidth(660)
        left.setStyleSheet("QFrame{background:#0a0d1e;border-right:2px solid #1a1f40;}")
        ll=QVBoxLayout(left); ll.setContentsMargins(0,0,0,0); ll.setSpacing(0)

        # Camera + Avatar + Emotion  (horizontal row)
        top_row=QWidget(); tr=QHBoxLayout(top_row)
        tr.setContentsMargins(0,0,0,0); tr.setSpacing(0)

        # Camera label
        self.cam_lbl=QLabel(); self.cam_lbl.setFixedSize(440,440)
        self.cam_lbl.setStyleSheet("background:#000;")
        self.cam_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tr.addWidget(self.cam_lbl)

        # Avatar + Emotion stacked vertically
        side=QWidget(); side.setFixedWidth(220)
        sl=QVBoxLayout(side); sl.setContentsMargins(0,0,0,0); sl.setSpacing(0)
        self.avatar=AvatarWidget(); sl.addWidget(self.avatar)
        self.emo_panel=EmotionPanel(); sl.addWidget(self.emo_panel)
        tr.addWidget(side)
        ll.addWidget(top_row)

        # Chat header
        ch=QLabel("💬 Chat — ask anything or type answers!")
        ch.setFont(QFont("Arial",8,QFont.Weight.Bold))
        ch.setStyleSheet("color:#a78bfa;background:#0c0f1e;padding:3px;")
        ch.setAlignment(Qt.AlignmentFlag.AlignCenter); ll.addWidget(ch)

        # Chat area
        self.chat_area=QTextEdit(); self.chat_area.setReadOnly(True)
        self.chat_area.setFont(QFont("Arial",9))
        self.chat_area.setStyleSheet(
            "QTextEdit{background:#07090f;color:#e0e6ff;border:1px solid #1a1f40;padding:4px;}")
        self.chat_area.setFixedHeight(140); ll.addWidget(self.chat_area)

        # Chat input row
        cir=QWidget(); cirow=QHBoxLayout(cir)
        cirow.setContentsMargins(4,2,4,2); cirow.setSpacing(4)
        self.chat_input=QLineEdit()
        self.chat_input.setPlaceholderText(
            "Type here… 'how to wash my face?' opens YouTube! (Enter to send)")
        self.chat_input.setFont(QFont("Arial",10))
        self.chat_input.setStyleSheet(
            "QLineEdit{background:#0c0f1e;color:#e0e6ff;border:2px solid #4f46e5;"
            "border-radius:8px;padding:5px;}")
        self.chat_input.setFixedHeight(36)
        self.chat_input.returnPressed.connect(self._send_chat)
        cirow.addWidget(self.chat_input,1)
        sb=QPushButton("Send"); sb.setFixedSize(60,36)
        sb.setStyleSheet("QPushButton{background:#4f46e5;color:white;border-radius:8px;font-weight:bold;}")
        sb.clicked.connect(self._send_chat); cirow.addWidget(sb)
        ll.addWidget(cir)

        # Finger / status strip
        self.finger_lbl=QLabel(f"✋ {CHILD_NAME} | Fingers: 0 | 😊 neutral | Att:70%")
        self.finger_lbl.setFont(QFont("Arial",9,QFont.Weight.Bold))
        self.finger_lbl.setStyleSheet("color:#fbbf24;padding:3px;background:#07090f;")
        self.finger_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ll.addWidget(self.finger_lbl)
        main.addWidget(left)

        # ════ RIGHT COLUMN ════════════════════════════════════════
        right=QWidget(); right.setFixedWidth(660)
        rl=QVBoxLayout(right); rl.setSpacing(5); rl.setContentsMargins(10,6,10,6)

        # Header
        hdr=QFrame(); hdr.setFixedHeight(68)
        hdr.setStyleSheet("""QFrame{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,
            stop:0 #1a0a3d,stop:0.5 #0a0f28,stop:1 #1a0a3d);
            border-radius:12px;border:2px solid #4f46e5;}""")
        hl=QHBoxLayout(hdr); hl.setContentsMargins(12,4,12,4)
        self.av_lbl=QLabel("🤖"); self.av_lbl.setFont(QFont("Arial",24))
        self.av_lbl.setStyleSheet("color:#a78bfa;"); hl.addWidget(self.av_lbl)
        tw_=QWidget(); tl2=QVBoxLayout(tw_); tl2.setSpacing(1)
        self.title_lbl=QLabel("PEPPER CLINICAL INFINITY V4")
        self.title_lbl.setFont(QFont("Arial",11,QFont.Weight.Bold))
        self.title_lbl.setStyleSheet("color:#a78bfa;"); tl2.addWidget(self.title_lbl)
        self.child_lbl=QLabel(f"Child: {CHILD_NAME} | ABA/DTT/TEACCH/ESDM")
        self.child_lbl.setFont(QFont("Arial",8)); self.child_lbl.setStyleSheet("color:#60a5fa;")
        tl2.addWidget(self.child_lbl); hl.addWidget(tw_,1)
        sw_=QWidget(); sl_=QVBoxLayout(sw_); sl_.setSpacing(1)
        self.state_lbl=QLabel("💤 Ready")
        self.state_lbl.setFont(QFont("Arial",8)); self.state_lbl.setStyleSheet("color:#9ca3af;")
        sl_.addWidget(self.state_lbl,alignment=Qt.AlignmentFlag.AlignRight)
        self.csv_lbl=QLabel(f"📊 {CSV_FILE}")
        self.csv_lbl.setFont(QFont("Arial",7)); self.csv_lbl.setStyleSheet("color:#6b7280;")
        sl_.addWidget(self.csv_lbl,alignment=Qt.AlignmentFlag.AlignRight)
        hl.addWidget(sw_); rl.addWidget(hdr)

        # TEACCH Schedule
        sched=QFrame(); sched.setFixedHeight(50)
        sched.setStyleSheet("QFrame{background:#0c0f1e;border-radius:11px;border:1px solid #1a1f40;}")
        sc=QHBoxLayout(sched); sc.setContentsMargins(10,5,10,5); sc.setSpacing(7)
        self.sched_task=QLabel("📋 Task")
        self.sched_task.setFont(QFont("Arial",9,QFont.Weight.Bold))
        self.sched_task.setStyleSheet(
            "color:#a78bfa;background:#1e1b4b;border-radius:7px;padding:3px 8px;border:2px solid #4f46e5;")
        sc.addWidget(self.sched_task); sc.addWidget(self._arr())
        sw2=QWidget(); sl2_=QVBoxLayout(sw2); sl2_.setSpacing(0); sl2_.setContentsMargins(0,0,0,0)
        self.stars_lbl=QLabel("☆ ☆ ☆")
        self.stars_lbl.setFont(QFont("Arial",14)); self.stars_lbl.setStyleSheet("color:#4b5563;")
        self.stars_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter); sl2_.addWidget(self.stars_lbl)
        self.mastery_sub=QLabel("0/3 | Fails:0/2")
        self.mastery_sub.setFont(QFont("Arial",7)); self.mastery_sub.setStyleSheet("color:#6b7280;")
        self.mastery_sub.setAlignment(Qt.AlignmentFlag.AlignCenter); sl2_.addWidget(self.mastery_sub)
        sc.addWidget(sw2,1); sc.addWidget(self._arr())
        self.reward_lbl=QLabel("⭐"); self.reward_lbl.setFont(QFont("Arial",18))
        self.reward_lbl.setStyleSheet(
            "color:#fbbf24;background:#2a1a00;border-radius:7px;padding:2px 7px;border:2px solid #f59e0b;")
        sc.addWidget(self.reward_lbl); rl.addWidget(sched)

        # Instruction
        if_fr=QFrame(); if_fr.setFixedHeight(78)
        if_fr.setStyleSheet("""QFrame{background:qlineargradient(x1:0,y1:0,x2:0,y2:1,
            stop:0 #1e1b4b,stop:1 #0c0f2e);border-radius:11px;border:2px solid #4f46e5;}""")
        il=QVBoxLayout(if_fr); il.setContentsMargins(12,3,12,3)
        self.instr_icon=QLabel("📋"); self.instr_icon.setFont(QFont("Arial",15))
        self.instr_icon.setAlignment(Qt.AlignmentFlag.AlignCenter); il.addWidget(self.instr_icon)
        self.instr_lbl=QLabel("Getting ready…")
        self.instr_lbl.setFont(QFont("Arial",13,QFont.Weight.Bold))
        self.instr_lbl.setStyleSheet("color:#e0e6ff;")
        self.instr_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.instr_lbl.setWordWrap(True); il.addWidget(self.instr_lbl); rl.addWidget(if_fr)

        # Content
        self.content_fr=QFrame(); self.content_fr.setMinimumHeight(250)
        self.content_fr.setStyleSheet(
            "QFrame{background:rgba(12,15,30,0.90);border-radius:13px;border:2px solid #1a1f40;}")
        self.content_lay=QVBoxLayout(self.content_fr)
        self.content_lay.setContentsMargins(12,10,12,10)
        self.content_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._show_idle(); rl.addWidget(self.content_fr,1)

        # Lock overlay
        self.lock_ov=QLabel("🔒"); self.lock_ov.setParent(self.content_fr)
        self.lock_ov.setGeometry(0,0,636,250)
        self.lock_ov.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lock_ov.setFont(QFont("Arial",44))
        self.lock_ov.setStyleSheet(
            "QLabel{background:rgba(0,0,0,0.52);border-radius:13px;color:#a78bfa;}")
        self.lock_ov.hide()

        # Feedback
        fb_fr=QFrame(); fb_fr.setFixedHeight(50)
        fb_fr.setStyleSheet("QFrame{background:#0c0f1e;border-radius:10px;border:1px solid #1a1f40;}")
        fl=QHBoxLayout(fb_fr); fl.setContentsMargins(12,6,12,6)
        self.fb_icon=QLabel("💤"); self.fb_icon.setFont(QFont("Arial",19)); fl.addWidget(self.fb_icon)
        self.fb_lbl=QLabel("Waiting for Pepper…")
        self.fb_lbl.setFont(QFont("Arial",11,QFont.Weight.Bold))
        self.fb_lbl.setStyleSheet("color:#9ca3af;"); self.fb_lbl.setWordWrap(True)
        fl.addWidget(self.fb_lbl,1); rl.addWidget(fb_fr)

        # Mic button
        self.mic_btn=QPushButton("🎤  TOUCH & HOLD TO SPEAK")
        self.mic_btn.setFixedHeight(54)
        self.mic_btn.setFont(QFont("Arial",13,QFont.Weight.Bold))
        self.mic_btn.setStyleSheet("""
        QPushButton{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,
            stop:0 #dc2626,stop:1 #ef4444);
            color:white;border-radius:27px;border:3px solid #fca5a5;}
        QPushButton:pressed{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,
            stop:0 #991b1b,stop:1 #dc2626);border:4px solid white;}""")
        self.mic_btn.pressed.connect(self._on_mic_press)
        self.mic_btn.released.connect(self._on_mic_release); rl.addWidget(self.mic_btn)

        self.rec_status=QLabel("🎤 Tap mic to speak — works for ALL verbal tasks and chat!")
        self.rec_status.setFont(QFont("Arial",8)); self.rec_status.setStyleSheet("color:#6b7280;padding:1px;")
        self.rec_status.setAlignment(Qt.AlignmentFlag.AlignCenter); rl.addWidget(self.rec_status)

        # Stats bar
        sb_=QFrame(); sb_.setFixedHeight(40)
        sb_.setStyleSheet("QFrame{background:#07090f;border-radius:8px;border:1px solid #1a1f40;}")
        stl=QHBoxLayout(sb_); stl.setContentsMargins(10,2,10,2)
        for lbl,attr,col in [("Score","stat_score","#a78bfa"),("Tokens","stat_tokens","#fbbf24"),
                               ("Mastered","stat_mastered","#34d399"),("Streak","stat_streak","#60a5fa"),
                               ("Skipped","stat_skipped","#f87171"),("Domain","stat_domain","#60a5fa")]:
            w_=QWidget(); wl_=QVBoxLayout(w_); wl_.setSpacing(0); wl_.setContentsMargins(0,0,0,0)
            val=QLabel("0"); val.setFont(QFont("Arial",10,QFont.Weight.Bold))
            val.setStyleSheet(f"color:{col};"); val.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lb_=QLabel(lbl); lb_.setFont(QFont("Arial",6)); lb_.setStyleSheet("color:#6b7280;")
            lb_.setAlignment(Qt.AlignmentFlag.AlignCenter)
            wl_.addWidget(val); wl_.addWidget(lb_); stl.addWidget(w_)
            setattr(self,attr,val)
        rl.addWidget(sb_); main.addWidget(right)

    def _arr(self):
        a=QLabel("▶"); a.setFont(QFont("Arial",11)); a.setStyleSheet("color:#4f46e5;"); return a

    # ── BRIDGE CONNECTIONS ────────────────────────────────────────
    def _connect_bridge(self):
        BRIDGE.sig_task.connect(self._on_task)
        BRIDGE.sig_success.connect(self._on_success_ov)
        BRIDGE.sig_fail.connect(self._on_fail_ov)
        BRIDGE.sig_skip.connect(self._on_skip_ov)
        BRIDGE.sig_feedback.connect(self._set_fb)
        BRIDGE.sig_instr.connect(self._set_instr)
        BRIDGE.sig_waiting.connect(self._set_waiting)
        BRIDGE.sig_unlock.connect(self._do_unlock)
        BRIDGE.sig_lock.connect(self._do_lock)
        BRIDGE.sig_reset.connect(self._reset_cards)
        BRIDGE.sig_joy.connect(self._on_joy)
        BRIDGE.sig_camera.connect(self._update_cam)
        BRIDGE.sig_stats.connect(self._refresh_stats)
        BRIDGE.sig_chat.connect(self._add_chat)
        BRIDGE.sig_rec_start.connect(self._on_rec_start)
        BRIDGE.sig_rec_stop.connect(self._on_rec_stop)
        BRIDGE.sig_youtube.connect(self._on_youtube)

    def _update_cam(self,qimg):
        if isinstance(qimg,QImage):
            pix=QPixmap.fromImage(qimg).scaled(440,440,
                Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation)
            self.cam_lbl.setPixmap(pix)
        fc=ST["finger_count"]; em=ST["emotion"]
        self.finger_lbl.setText(
            f"👦 {CHILD_NAME} | Fingers:{fc} {'|'*min(fc,10)} | 😊 {em.upper()} | Att:{ST['attention']}%")

    def _refresh_stats(self):
        self.stat_score.setText(str(ST["score"]))
        self.stat_tokens.setText(str(ST["tokens"]))
        self.stat_mastered.setText(str(ST["tasks_mastered"]))
        self.stat_streak.setText(str(ST["streak"]))
        self.stat_skipped.setText(str(ST["tasks_skipped"]))
        self.stat_domain.setText(ST["domain"][:7])
        n=ST["consecutive"]; fc=ST["fail_count"]
        self.stars_lbl.setText("⭐"*n+"☆"*(3-n) if n else "☆ ☆ ☆")
        self.mastery_sub.setText(f"{n}/3 | Fails:{fc}/{MAX_FAILS}")
        sc={0:"#4b5563",1:"#d97706",2:"#fbbf24",3:"#f59e0b"}
        self.stars_lbl.setStyleSheet(f"color:{sc.get(n,'#4b5563')};")
        tidx=min(ST["task_index"],len(TASK_POOL)-1)
        t_=TASK_POOL[tidx]; self.sched_task.setText(f"📋 {t_.get('name',t_['id'])[:18]}")
        if   ST["is_speaking"]: self.fb_icon.setText("🔊"); self.state_lbl.setText("🔊 Speaking")
        elif ST["recording"]:   self.fb_icon.setText("🔴"); self.state_lbl.setText("🎤 Recording")
        elif ST["listening"]:   self.fb_icon.setText("👂"); self.state_lbl.setText("👂 Listening")
        elif ST["waiting_for_child"]: self.fb_icon.setText("⏳"); self.state_lbl.setText("⏳ Waiting")
        else:                   self.fb_icon.setText("💤"); self.state_lbl.setText("💤 Ready")

    # ── TASK DISPLAY ──────────────────────────────────────────────
    def _show_idle(self):
        self._clear()
        d=QLabel("🤖\nPepper is preparing your task…")
        d.setFont(QFont("Arial",13)); d.setStyleSheet("color:#6b7280;")
        d.setAlignment(Qt.AlignmentFlag.AlignCenter); self.content_lay.addWidget(d)

    def _clear(self):
        while self.content_lay.count():
            item=self.content_lay.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        self._cards.clear()

    def _on_task(self,data):
        if data.get("action")=="click": self._handle_click(data.get("idx",-1)); return
        mode=data.get("mode","idle")
        self.instr_lbl.setText(data.get("instruction",""))
        self.fb_lbl.setText("Your turn! Click or do the task!")
        self.fb_lbl.setStyleSheet("color:#60a5fa;")
        self._build_content(data); self._do_unlock()

    def _build_content(self,data):
        self._clear(); mode=data.get("mode","idle")
        if mode=="idle": self._show_idle(); return
        if mode=="motor_model":
            vw=QWidget(); vl=QVBoxLayout(vw); vl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            fig=data.get("figure","")
            if fig and "base64," in fig:
                raw=base64.b64decode(fig.split(",",1)[1]); qi=QImage(); qi.loadFromData(raw)
                pix=QPixmap.fromImage(qi).scaled(190,190,Qt.AspectRatioMode.KeepAspectRatio,
                                                  Qt.TransformationMode.SmoothTransformation)
                fl=QLabel(); fl.setPixmap(pix); fl.setAlignment(Qt.AlignmentFlag.AlignCenter); vl.addWidget(fl)
            lb=QLabel(data.get("label",""))
            lb.setFont(QFont("Arial",14,QFont.Weight.Bold)); lb.setStyleSheet("color:#a78bfa;")
            lb.setAlignment(Qt.AlignmentFlag.AlignCenter); vl.addWidget(lb)
            ar=QLabel("👇 NOW YOU DO IT! 👇")
            ar.setFont(QFont("Arial",11,QFont.Weight.Bold)); ar.setStyleSheet("color:#34d399;")
            ar.setAlignment(Qt.AlignmentFlag.AlignCenter); vl.addWidget(ar)
            self.content_lay.addWidget(vw); return
        if mode=="word_display":
            wf=QFrame(); wf.setStyleSheet("""QFrame{background:qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 #1e1b4b,stop:1 #0c0f1e);border-radius:16px;border:3px solid #4f46e5;min-height:140px;}""")
            wfl=QVBoxLayout(wf); wfl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            el=QLabel(data.get("emoji","📢")); el.setFont(QFont("Arial",44))
            el.setAlignment(Qt.AlignmentFlag.AlignCenter); wfl.addWidget(el)
            wl=QLabel(data.get("word","SAY IT!"))
            wl.setFont(QFont("Arial",30,QFont.Weight.Bold)); wl.setStyleSheet("color:#a78bfa;")
            wl.setAlignment(Qt.AlignmentFlag.AlignCenter); wfl.addWidget(wl)
            hl=QLabel("🎤 Tap the mic button and say this word!")
            hl.setFont(QFont("Arial",11)); hl.setStyleSheet("color:#34d399;")
            hl.setAlignment(Qt.AlignmentFlag.AlignCenter); wfl.addWidget(hl)
            self.content_lay.addWidget(wf); return
        if mode=="number_display":
            nf=QFrame(); nf.setStyleSheet("""QFrame{background:qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 #1a3320,stop:1 #0c1a10);border-radius:16px;border:3px solid #22c55e;min-height:140px;}""")
            nfl=QVBoxLayout(nf); nfl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            nl=QLabel(str(data.get("target_number","?")))
            nl.setFont(QFont("Arial",70,QFont.Weight.Bold)); nl.setStyleSheet("color:#34d399;")
            nl.setAlignment(Qt.AlignmentFlag.AlignCenter); nfl.addWidget(nl)
            hl2=QLabel("Show me with your fingers! 🖐️")
            hl2.setFont(QFont("Arial",12)); hl2.setStyleSheet("color:#6b7280;")
            hl2.setAlignment(Qt.AlignmentFlag.AlignCenter); nfl.addWidget(hl2)
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
        if self._locked: return
        correct=self._correct_idx
        if correct==-1:
            ST["tablet_click_result"]="correct"
            if idx<len(self._cards): self._cards[idx].flash_correct()
            self.fb_lbl.setText("✅ Great choice!"); self.fb_lbl.setStyleSheet("color:#34d399;")
            self._do_lock(); return
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

    def _on_success_ov(self,msg):
        self._clear()
        ov=QWidget(); ol=QVBoxLayout(ov); ol.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ck=QLabel("✅"); ck.setFont(QFont("Arial",96)); ck.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ol.addWidget(ck)
        ml=QLabel(msg); ml.setFont(QFont("Arial",14,QFont.Weight.Bold))
        ml.setStyleSheet("color:#34d399;"); ml.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ml.setWordWrap(True); ol.addWidget(ml); self.content_lay.addWidget(ov)
        self.fb_lbl.setText(msg); self.fb_lbl.setStyleSheet("color:#34d399;font-size:14px;")
        self.instr_icon.setText("✅")
        # Balloon celebration (QPropertyAnimation — non-blocking)
        launch_balloons(self.centralWidget(), 20)
        QTimer.singleShot(2800,self._show_idle)
        QTimer.singleShot(2800,lambda: self.instr_icon.setText("📋"))

    def _on_fail_ov(self,msg):
        self.fb_lbl.setText(f"❌ {msg}"); self.fb_lbl.setStyleSheet("color:#f87171;font-size:13px;")
        self.instr_icon.setText("❌")
        QTimer.singleShot(2000,lambda: self.instr_icon.setText("📋"))
        QTimer.singleShot(2000,lambda: self.fb_lbl.setStyleSheet("color:#9ca3af;"))

    def _on_skip_ov(self,msg):
        self.fb_lbl.setText(f"⏭️ {msg}"); self.fb_lbl.setStyleSheet("color:#f97316;font-size:12px;")
        QTimer.singleShot(3000,lambda: self.fb_lbl.setStyleSheet("color:#9ca3af;"))

    def _on_joy(self,jtype):
        self._joy_phase=0.0; self._joy_timer.start(55)
        msgs={"dance":"🕺 AMAZING! 🎉","celebrate":"🎊 BRILLIANT! ⭐",
              "wave_back":"👋 HIGH FIVE! 🌟","full_joy":"🏆 CHAMPION! 🎉🌟"}
        self.fb_lbl.setText(msgs.get(jtype,"🌟 AMAZING! 🎉"))
        self.fb_lbl.setStyleSheet("color:#fbbf24;font-size:15px;")
        QTimer.singleShot(3000,self._end_joy)

    def _joy_tick(self):
        self._joy_phase+=0.22
        ems=["🎉","🌟","⭐","🏆","✨","🎊","💫","🎈"]
        self.av_lbl.setText(ems[int(self._joy_phase)%len(ems)])
        if self._joy_phase>20: self._end_joy()

    def _end_joy(self):
        self._joy_timer.stop(); self.av_lbl.setText("🤖")
        QTimer.singleShot(500,lambda: self.fb_lbl.setStyleSheet("color:#9ca3af;"))

    def _do_unlock(self):
        self._locked=False; ST["tablet_locked"]=False; self.lock_ov.hide()
        for c in self._cards: c.setEnabled(True)

    def _do_lock(self):
        self._locked=True; ST["tablet_locked"]=True
        self.lock_ov.show(); self.lock_ov.raise_()
        for c in self._cards: c.setEnabled(False)

    def _set_fb(self,txt):    self.fb_lbl.setText(txt)
    def _set_instr(self,txt): self.instr_lbl.setText(txt)
    def _set_waiting(self,txt):
        self.fb_lbl.setText(txt); self.fb_lbl.setStyleSheet("color:#fbbf24;"); self.fb_icon.setText("⏳")

    def _reset_cards(self):
        for c in self._cards: c.reset()
        ST["tablet_click_result"]=None

    # ── MIC ───────────────────────────────────────────────────────
    def _on_mic_press(self):
        self.rec_status.setText("🔴 RECORDING… Release to stop")
        self.rec_status.setStyleSheet("color:#ef4444;font-size:10px;font-weight:bold;padding:1px;")
        self.mic_btn.setText("🔴  RECORDING… RELEASE TO STOP")
        self._recorder.start()

    def _on_mic_release(self):
        self.mic_btn.setText("🎤  TOUCH & HOLD TO SPEAK")
        self.rec_status.setText("⏳ Processing speech…")
        self.rec_status.setStyleSheet("color:#fbbf24;padding:1px;")
        threading.Thread(target=self._do_rec,daemon=True).start()

    def _do_rec(self):
        text=self._recorder.stop_and_recognise(); BRIDGE.sig_rec_stop.emit(text)

    def _on_rec_start(self): pass

    def _on_rec_stop(self,text):
        if text:
            self.rec_status.setText(f'✅ Heard: "{text[:25]}"')
            self.rec_status.setStyleSheet("color:#34d399;font-size:10px;padding:1px;")
            ST["last_speech_text"]=text.lower(); ST["last_sound"]=time.time()
            ST["session_chat"].append({"role":"child","text":text,
                "time":datetime.now().strftime("%H:%M:%S")})
            if len(ST["session_chat"])>60: ST["session_chat"]=ST["session_chat"][-60:]
            self._add_chat("child",text)
        else:
            self.rec_status.setText("❌ Could not hear — speak closer and try again!")
            self.rec_status.setStyleSheet("color:#f87171;padding:1px;")
        QTimer.singleShot(3500,lambda: self.rec_status.setText(
            "🎤 Tap mic to speak — works for ALL verbal tasks and chat!"))
        QTimer.singleShot(3500,lambda: self.rec_status.setStyleSheet("color:#6b7280;padding:1px;"))

    # ── CHAT ──────────────────────────────────────────────────────
    def _send_chat(self):
        text=self.chat_input.text().strip()
        if not text: return
        self.chat_input.clear()
        self._add_chat("child",text)
        ST["last_speech_text"]=text.lower(); ST["last_sound"]=time.time()
        ST["session_chat"].append({"role":"child","text":text,
            "time":datetime.now().strftime("%H:%M:%S")})
        threading.Thread(target=self._process_chat,args=(text,),daemon=True).start()

    def _process_chat(self,text):
        t=text.lower()
        yt_kw=["how to","show me","teach me","youtube","video","watch","learn",
                "letters","numbers","shapes","colors","animals"]
        if any(kw in t for kw in yt_kw):
            q=re.sub(r"how to|show me|teach me|youtube|video|watch|learn","",t).strip() or text
            url=("https://www.youtube.com/results?search_query="
                 +urllib.parse.quote(q+" for kids educational"))
            webbrowser.open(url)
            reply=f"Opening YouTube video about '{q}' for kids! 🎬 Enjoy learning!"
            BRIDGE.sig_chat.emit("pepper",reply)
            BRIDGE.sig_youtube.emit(url)
            BRIDGE.sig_feedback.emit(f"📺 YouTube: {q}")
            ST["session_chat"].append({"role":"pepper","text":reply,
                "time":datetime.now().strftime("%H:%M:%S")}); return
        reply=self._quick_reply(t)
        BRIDGE.sig_chat.emit("pepper",reply)
        ST["session_chat"].append({"role":"pepper","text":reply,
            "time":datetime.now().strftime("%H:%M:%S")})

    def _quick_reply(self,t):
        nm=CHILD_NAME
        if any(w in t for w in ["hello","hi","hey"]): return f"Hello {nm}! 👋 Great to talk with you!"
        if any(w in t for w in ["good","great","yes","okay","done"]): return f"Wonderful {nm}! Keep going! 🌟"
        if any(w in t for w in ["help","confused","don't know"]): return "No worries! I will show you again! 🎯"
        if any(w in t for w in ["tired","stop","break"]): return f"Okay {nm}! Short break! Rest and come back! 💙"
        if any(w in t for w in ["good morning"]): return f"Good morning {nm}! Ready to learn? ☀️"
        if any(w in t for w in ["good night"]): return f"Good night {nm}! Amazing work today! 🌙⭐"
        if any(w in t for w in ["what is","who is","why","where"]): return f"Great question! Ask me: 'show me a video about it!' 🎬"
        return f"Great {nm}! Let us keep learning! 🎯"

    def _add_chat(self,role,text):
        c="#34d399" if role=="child" else "#a78bfa"
        n=CHILD_NAME if role=="child" else "Pepper 🤖"
        self.chat_area.append(
            f'<span style="color:{c};font-weight:bold">{n}:</span> '
            f'<span style="color:#e0e6ff">{text}</span>')
        sb=self.chat_area.verticalScrollBar(); sb.setValue(sb.maximum())

    def _on_youtube(self,url):
        LOG(f"📺 YouTube: {url[:55]}","info")

# ══════════════════════════════════════════════════════════════════════
# 16. THERAPY CONTROLLER
# ══════════════════════════════════════════════════════════════════════
class TherapyCtrl:
    def __init__(self,voice:Voice,pb:PBWatchdog):
        self.v=voice; self.pb=pb; self.running=False

    def _say(self,text,wait=True):
        clean=re.sub(r"\[[^\]]+\]","",str(text)).strip()
        BRIDGE.sig_instr.emit(clean[:70]); self.v.say(text,wait=wait)

    def _pb_sync(self):
        self.pb.send(is_speaking=ST["is_speaking"],listening=ST["listening"],
                     recording=ST["recording"],lip=ST["lip_sync_value"],
                     ht=ST.get("head_tilt_val",0.0),blink=ST.get("blinking",False),
                     sj=ST.get("social_joy_active",False),gaze=ST["gaze_mode"])

    def run(self):
        self.running=True
        threading.Thread(target=self._pb_loop,daemon=True).start()
        self._say(
            f"Hello {CHILD_NAME}! I am Pepper your Clinical Therapist! "
            "Look at the screen and copy my movements! "
            "Tap the red microphone button to speak! "
            "Type questions in the chat and I will open a video for you! "
            "Let us earn 3 stars for every task! Ready?")
        time.sleep(0.5)
        last_em=ST["emotion"]; em_t=time.time()

        while self.running:
            if time.time()-ST["last_sound"]>16:
                ST["last_sound"]=time.time()
                self.v.say(f"{CHILD_NAME}, ready when you are! 🎯",wait=False)
            curr=ST["emotion"]
            if curr!=last_em and time.time()-em_t>8:
                last_em=curr; em_t=time.time()
                if curr in ["sad","angry","fear"]:
                    self._say(f"{CHILD_NAME}, I see you. It is okay. I am here. 💙",wait=False)
            self._handle_cmd()
            tidx=ST["task_index"]%len(TASK_POOL)
            task=TASK_POOL[tidx]
            ST["tablet_instruction"]=task["instruction"]
            ST["domain"]=task.get("domain","Motor")
            ST["protocol"]=task.get("protocol","ABA")
            ST["current_level"]=task.get("level",1)
            ST["fail_count"]=0
            self._show(task)
            if task["domain"]=="Motor":
                ST["gaze_mode"]="tablet"
                threading.Thread(target=self._gaze_seq,daemon=True).start()
                self._say(task["instruction"]+" Look at the screen!",wait=False)
            else:
                self._say(task["instruction"],wait=False)
            success=self._run_dtt(task)
            log_csv(task["id"],task["domain"],task["level"],success,
                    ST["consecutive"],ST["fail_count"],
                    ST["score"],ST["emotion"],ST["attention"])
            if success:
                self._on_success(task)
                self._say(f"{CHILD_NAME}! {task.get('success','Amazing!')} "
                          "Now the NEXT task! [CELEBRATE]",wait=False)
            else:
                self._on_skip(task)
            time.sleep(0.3)

    def _pb_loop(self):
        while self.running: self._pb_sync(); time.sleep(0.05)

    def _show(self,task):
        mode=task.get("tablet_mode","idle")
        data={"mode":mode,"instruction":task["instruction"]}
        if task["domain"]=="Motor" or mode=="motor_model":
            data.update({"mode":"motor_model","figure":task.get("figure",""),"label":task.get("name","")})
        elif mode=="word_display":
            data.update({"emoji":task.get("word_emoji","📢"),"word":task.get("word_text","SAY IT!")})
        elif mode=="number_display":
            data.update({"target_number":task.get("target_number",1)})
        elif mode in ["color_grid","object_grid","shape_grid","number_grid","emotion_grid"]:
            data.update({"options":task.get("options",[]),"correct":task.get("correct",-1)})
        ST["tablet_click_result"]=None; BRIDGE.sig_task.emit(data)

    def _gaze_seq(self):
        ST["gaze_mode"]="tablet"; time.sleep(1.5); ST["gaze_mode"]="child"

    def _run_dtt(self,task)->bool:
        vtype=task.get("verify","motor")
        motor_v=["clap","wave","raise_hand","touch_nose","arms_out","hands_up","point"]
        if vtype in motor_v:
            ST["verify_action"]=vtype; ST["verify_result"]=False
            ST["verify_timeout"]=time.time()+22
        elif vtype=="finger_count":
            ST["verify_action"]="finger_count"; ST["verify_result"]=False
            ST["finger_target"]=task.get("target_number",1)
            ST["verify_timeout"]=time.time()+22
        ST["last_speech_text"]=""
        prompts=task.get("prompts",["Try again!"]); waiting=task.get("waiting","I am waiting!")
        deadline=time.time()+60; last_p=time.time(); pidx=0; fail_count=0
        while time.time()<deadline:
            res=self._check(task)
            if res=="success": ST["fail_count"]=fail_count; return True
            if res=="fail":
                fail_count+=1; ST["fail_count"]=fail_count
                LOG(f"Fail {fail_count}/{MAX_FAILS} on {task['id']}","fail")
                BRIDGE.sig_fail.emit(task.get("fail","Not quite! Try again!"))
                if fail_count>=MAX_FAILS: return False
                self.v.say(f"{CHILD_NAME}! {prompts[pidx%len(prompts)]}",wait=False); pidx+=1
                ST["tablet_click_result"]=None
                QTimer.singleShot(2000,lambda: BRIDGE.sig_reset.emit())
                time.sleep(2.2); continue
            if time.time()-last_p>6:
                last_p=time.time()
                self.v.say(f"{CHILD_NAME}… {prompts[pidx%len(prompts)]}",wait=False)
                BRIDGE.sig_waiting.emit(waiting); pidx+=1
            self._handle_cmd(); time.sleep(0.18)
        ST["verify_action"]=None; ST["fail_count"]=fail_count; return False

    def _check(self,task)->str:
        vtype=task.get("verify","motor"); mc=task.get("verify","")
        if mc in ["clap","wave","raise_hand","touch_nose","arms_out","hands_up","point"]:
            if ST["verify_result"]: ST["verify_result"]=False; return "success"
            if mc=="clap" and ST["clapping"]: return "success"
            if mc=="wave" and ST["waving"]: return "success"
            if mc=="raise_hand" and ST["hand_raised"]: return "success"
            if mc=="arms_out" and ST["arms_out"]: return "success"
            if mc=="hands_up" and ST["hands_up"]: return "success"
        elif vtype=="finger_count":
            if ST["finger_count"]==ST["finger_target"]: return "success"
        elif vtype=="tablet_click":
            r=ST.get("tablet_click_result")
            if r=="correct": ST["tablet_click_result"]=None; return "success"
            if r=="wrong":   ST["tablet_click_result"]=None; return "fail"
        elif vtype=="speech_keyword":
            kw=task.get("keyword",""); lt=ST.get("last_speech_text","").lower()
            if kw and kw.lower() in lt: ST["last_speech_text"]=""; return "success"
        elif vtype=="speech_any":
            if ST["last_sound"]>time.time()-3 and len(ST.get("last_speech_text",""))>0:
                ST["last_speech_text"]=""; return "success"
        return None

    def _on_success(self,task):
        ST["consecutive"]+=1; pts=task.get("tokens",2)*5
        ST["score"]+=pts; ST["tokens"]+=task.get("tokens",2)
        ST["tasks_success"]+=1; ST["streak"]+=1
        d=task["domain"]
        if   d=="Motor":     ST["skill_motor"]    =min(100,ST["skill_motor"]+random.randint(1,4))
        elif d=="Cognitive": ST["skill_cognitive"] =min(100,ST["skill_cognitive"]+random.randint(1,4))
        elif d=="Verbal":    ST["skill_verbal"]    =min(100,ST["skill_verbal"]+random.randint(1,4))
        elif d=="Math":      ST["skill_math"]      =min(100,ST["skill_math"]+random.randint(1,4))
        BRIDGE.sig_success.emit(task.get("success","Amazing! ✅"))
        BRIDGE.sig_joy.emit(task.get("joy","celebrate"))
        BRIDGE.sig_stats.emit()
        BRIDGE.sig_chat.emit("pepper",f"⭐ Well done {CHILD_NAME}! Score:{ST['score']}")
        LOG(f"✅ {ST['consecutive']}/3 '{task['id']}'","success")
        if ST["consecutive"]>=MASTERY_N:
            ST["consecutive"]=0; ST["tasks_mastered"]+=1
            ST["task_index"]+=1
            if ST["task_index"]>=len(TASK_POOL): ST["task_index"]=0; ST["current_level"]+=1
            ntask=TASK_POOL[ST["task_index"]%len(TASK_POOL)]
            ST["social_joy_active"]=True
            ST["eye_color"]=(int(128+127*math.sin(time.time()*3)),
                             int(200+55*math.sin(time.time()*2)),255)
            LOG(f"🏆 MASTERED → {ntask['id']}","success")
            self._say(f"{CHILD_NAME} earned 3 stars! MASTERED! "
                      f"Moving to: {ntask.get('name','')}! [LEVEL_UP]",wait=False)
            BRIDGE.sig_chat.emit("pepper",f"🏆 LEVEL UP! Mastered:{task.get('name',task['id'])}!")
            def _clr(): ST["social_joy_active"]=False; ST["eye_color"]=(100,180,255)
            threading.Timer(4.0,_clr).start()

    def _on_skip(self,task):
        ST["tasks_fail"]+=1; ST["tasks_skipped"]+=1; ST["streak"]=0; ST["consecutive"]=0
        ST["task_index"]=(ST["task_index"]+1)%len(TASK_POOL)
        report=(f"📋 Task '{task.get('name',task['id'])}' skipped after {MAX_FAILS} attempts. "
                f"Domain:{task['domain']}. Recommendation: more practice.")
        BRIDGE.sig_chat.emit("pepper",report)
        BRIDGE.sig_skip.emit(f"Skipping after {MAX_FAILS} tries. Moving on!")
        ST["parent_notes"].append({"time":datetime.now().strftime("%H:%M"),
            "text":f"AUTO: Skipped '{task.get('name',task['id'])}' — needs attention"})
        self._say(f"{CHILD_NAME}, good try! Let us try something different!",wait=False)
        LOG(f"⏭️ SKIPPED {task['id']}","info"); time.sleep(0.8)

    def _handle_cmd(self):
        cmd=ST.get("sim_cmd")
        if not cmd: return
        ST["sim_cmd"]=None
        if cmd=="next": ST["consecutive"]=0; ST["task_index"]=(ST["task_index"]+1)%len(TASK_POOL); self.v.say("Next task!",wait=False)
        elif cmd=="break": self.v.say("Break time!",wait=False)
        elif cmd=="report":
            dur=int((time.time()-ST["uptime"])/60)
            print(f"\n{'='*55}\nREPORT — {CHILD_NAME} | {dur} min\n"
                  f"Score:{ST['score']} | Mastered:{ST['tasks_mastered']} | Skip:{ST['tasks_skipped']}\n"
                  f"Motor:{ST['skill_motor']}% Cog:{ST['skill_cognitive']}% "
                  f"Verbal:{ST['skill_verbal']}% Math:{ST['skill_math']}%\nCSV:{CSV_FILE}\n{'='*55}")

# ══════════════════════════════════════════════════════════════════════
# 17. FLASK SERVERS
# ══════════════════════════════════════════════════════════════════════
parent_app=Flask("parent"); report_app=Flask("report"); games_app=Flask("games")

PARENT_HTML="""<!DOCTYPE html><html><head>
<meta charset="UTF-8"><title>Parent Dashboard — {{child}}</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="4">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#060912;color:#e0e6ff;font-family:'Segoe UI',sans-serif;padding:12px}
h1{color:#a78bfa;margin-bottom:8px}
.nav{display:flex;gap:5px;margin-bottom:8px;flex-wrap:wrap}
.nav a{padding:6px 12px;border-radius:8px;text-decoration:none;font-size:.78em;font-weight:700}
.b1{background:#4f46e5;color:#fff}.b2{background:#059669;color:#fff}
.b3{background:#1d4ed8;color:#fff}.b4{background:#7c3aed;color:#fff}
.row{display:grid;grid-template-columns:repeat(4,1fr);gap:7px;margin-bottom:8px}
.stat{background:#0c0f1e;border-radius:10px;padding:10px;border:1px solid #1a1f40;text-align:center}
.n{font-size:1.5em;font-weight:700;color:#a78bfa}.l{font-size:.63em;color:#6b7280;margin-top:2px}
.n-g{color:#34d399}.n-y{color:#fbbf24}.n-b{color:#60a5fa}.n-r{color:#f87171}
.card{background:#0c0f1e;border-radius:10px;padding:12px;border:1px solid #1a1f40;margin-bottom:8px}
.card h2{color:#818cf8;margin-bottom:6px;font-size:.82em}
.emo{display:inline-block;padding:4px 12px;border-radius:12px;font-weight:700;font-size:.9em}
.happy,.joyful{background:#05291555;color:#34d399;border:1px solid #34d399}
.sad{background:#1e3a5f55;color:#60a5fa;border:1px solid #60a5fa}
.angry{background:#45090a55;color:#f87171;border:1px solid #f87171}
.fear{background:#1c190055;color:#fbbf24;border:1px solid #fbbf24}
.surprised{background:#2e106555;color:#c084fc;border:1px solid #c084fc}
.neutral{background:#1f293755;color:#9ca3af;border:1px solid #9ca3af}
.pct-row{display:flex;align-items:center;gap:6px;margin:3px 0;font-size:.72em}
.pct-bar-bg{flex:1;height:7px;background:#1f2937;border-radius:4px}
.pct-bar{height:7px;border-radius:4px}
.skill-g{display:grid;grid-template-columns:repeat(4,1fr);gap:6px}
.si{text-align:center;background:#07090f;border-radius:8px;padding:8px}
.sv{font-size:1.2em;font-weight:700;color:#a78bfa}
.log-box{max-height:200px;overflow-y:auto}
.li{padding:2px 5px;margin:1px 0;font-size:.66em;border-left:3px solid #4f46e5;background:#07090f}
.li.success{border-color:#34d399}.li.fail{border-color:#f87171}
.chat-box{max-height:180px;overflow-y:auto;font-size:.75em}
.cm{padding:3px 6px;margin:2px 0;border-radius:5px}
.cmp{background:#1e1b4b;border-left:3px solid #a78bfa}
.cmc{background:#052918;border-left:3px solid #34d399}
input,textarea{width:100%;padding:6px;border-radius:6px;border:1px solid #1a1f40;
  background:#07090f;color:#e0e6ff;font-size:.78em;outline:none;min-height:34px}
.btn{background:#4f46e5;color:#fff;border:none;padding:6px 12px;border-radius:6px;
     cursor:pointer;font-size:.75em;margin-top:4px;min-height:32px}
.btn-g{background:#059669}
.note{background:#0a1020;border-left:3px solid #a78bfa;padding:5px;margin:2px 0;font-size:.72em}
::-webkit-scrollbar{width:3px}::-webkit-scrollbar-thumb{background:#4f46e5;border-radius:3px}
@media(max-width:600px){.row{grid-template-columns:repeat(2,1fr)}}
</style></head><body>
<h1>👨‍👩‍👦 Parent Dashboard — {{child}} (Age {{age}})</h1>
<div class="nav">
  <a href="http://127.0.0.1:5007/" class="b1">📊 Dashboard</a>
  <a href="http://127.0.0.1:5001/" class="b2">📋 Reports</a>
  <a href="http://127.0.0.1:5009/" class="b3">🎮 Games</a>
  <a href="http://{{lip}}:5007/" class="b4">📱 Android</a>
</div>
<div class="row">
  <div class="stat"><div class="n n-g">{{score}}</div><div class="l">⭐ Score</div></div>
  <div class="stat"><div class="n n-y">{{mastered}}</div><div class="l">🏆 Mastered</div></div>
  <div class="stat"><div class="n n-b">{{att}}%</div><div class="l">🎯 Attention</div></div>
  <div class="stat"><div class="n n-r">{{skipped}}</div><div class="l">⏭️ Skipped</div></div>
</div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
<div>
  <div class="card"><h2>😊 Emotion Breakdown</h2>
    <div style="text-align:center;margin-bottom:8px">
      <div class="emo {{em}}">{{em.upper()}} {{conf}}%</div>
      <div style="font-size:.65em;color:#6b7280;margin-top:4px">
        Face:{{'✅' if face else '❌'}} | Fingers:{{fc}} | Streak:{{streak}} | Fails:{{fails}}/2</div>
    </div>
    {% for emo_,pct_ in pct.items() %}
    <div class="pct-row">
      <span style="width:60px;color:#9ca3af">{{emo_[:6]}}</span>
      <div class="pct-bar-bg"><div class="pct-bar" style="width:{{pct_}}%;
        background:{{'#22c55e' if emo_=='happy' or emo_=='joyful' else '#f87171' if emo_=='angry' else '#60a5fa' if emo_=='sad' else '#c084fc' if emo_=='surprised' else '#fbbf24' if emo_=='fear' else '#9ca3af'}}"></div></div>
      <span style="width:36px;text-align:right;color:#e0e6ff">{{pct_}}%</span>
    </div>{% endfor %}
  </div>
  <div class="card"><h2>📊 Skills Profile</h2>
    <div class="skill-g">
      <div class="si"><div class="sv">{{sm}}%</div><div style="font-size:.7em;color:#6b7280">Motor</div></div>
      <div class="si"><div class="sv">{{sc}}%</div><div style="font-size:.7em;color:#6b7280">Cognitive</div></div>
      <div class="si"><div class="sv">{{sv}}%</div><div style="font-size:.7em;color:#6b7280">Verbal</div></div>
      <div class="si"><div class="sv">{{smath}}%</div><div style="font-size:.7em;color:#6b7280">Math</div></div>
    </div>
  </div>
  <div class="card"><h2>📝 Notes</h2>
    <form method="POST" action="/note">
      <textarea name="note" placeholder="Write observation…" rows="2"></textarea>
      <button class="btn btn-g" style="width:100%">Save Note</button>
    </form>
    {% for n in notes[-8:]|reverse %}<div class="note">{{n.time}}: {{n.text}}</div>{% endfor %}
  </div>
</div>
<div>
  <div class="card"><h2>💬 Session Chat</h2>
    <div class="chat-box">
      {% for m in chat[-25:]|reverse %}
      <div class="cm {{'cmp' if m.role=='pepper' else 'cmc'}}">
        <span style="font-size:.6em;color:{{'#a78bfa' if m.role=='pepper' else '#34d399'}}">
          {{'🤖' if m.role=='pepper' else '👦'}} {{m.time}}</span><br>{{m.text}}</div>{% endfor %}
    </div>
  </div>
  <div class="card"><h2>📋 Session Log</h2>
    <div class="log-box">
      {% for lg in logs[-30:]|reverse %}
      <div class="li {{lg.type}}"><span style="color:#6366f1">{{lg.time}}</span> {{lg.msg}}</div>{% endfor %}
    </div>
  </div>
  <div class="card"><h2>🏆 Summary</h2>
    <div style="font-size:.75em;line-height:1.8;color:#9ca3af">
      Child:<b style="color:#e0e6ff">{{child}}</b> | {{date}}<br>
      OK:<span style="color:#34d399">{{ok}}</span> |
      Fail:<span style="color:#f87171">{{fail}}</span> |
      Skip:<span style="color:#f97316">{{skipped}}</span><br>
      CSV:<span style="color:#60a5fa">{{csv}}</span>
    </div>
  </div>
</div></div></body></html>"""

@parent_app.route("/")
def parent_home():
    pct=ST.get("emotion_pct",{k:0 for k in ["happy","joyful","sad","angry","fear","surprised","neutral"]})
    return render_template_string(PARENT_HTML,
        child=CHILD_NAME,age=ST["age"],score=ST["score"],
        mastered=ST["tasks_mastered"],att=ST["attention"],skipped=ST["tasks_skipped"],
        em=ST["emotion"],conf=int(ST.get("emotion_conf",0)*100),
        face=ST["face_detected"],fc=ST["finger_count"],streak=ST["streak"],
        fails=ST["fail_count"],pct=pct,
        sm=ST["skill_motor"],sc=ST["skill_cognitive"],
        sv=ST["skill_verbal"],smath=ST["skill_math"],
        notes=ST["parent_notes"],chat=ST["session_chat"],logs=ST["logs"],
        date=ST["session_date"],ok=ST["tasks_success"],fail=ST["tasks_fail"],
        csv=CSV_FILE,lip=LOCAL_IP)

@parent_app.route("/note",methods=["POST"])
def parent_note():
    note=request.form.get("note","").strip()
    if note: ST["parent_notes"].append({"time":datetime.now().strftime("%H:%M"),"text":note})
    return redirect("/")

@parent_app.route("/api/state")
def parent_api():
    return jsonify({"emotion":ST["emotion"],"emotion_pct":ST.get("emotion_pct",{}),
                    "attention":ST["attention"],"score":ST["score"],
                    "mastered":ST["tasks_mastered"],"finger_count":ST["finger_count"],
                    "domain":ST["domain"],"streak":ST["streak"],"face":ST["face_detected"]})

@parent_app.errorhandler(404)
def p404(e): return redirect("/"),302

REPORT_HTML="""<!DOCTYPE html><html><head>
<meta charset="UTF-8"><title>Clinical Report — {{child}}</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="5">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#060912;color:#e0e6ff;font-family:'Segoe UI',sans-serif;padding:14px}
h1{color:#a78bfa;margin-bottom:8px}
.nav{display:flex;gap:5px;margin-bottom:8px;flex-wrap:wrap}
.nav a{padding:6px 12px;border-radius:8px;text-decoration:none;font-size:.78em;font-weight:700}
.b1{background:#4f46e5;color:#fff}.b2{background:#059669;color:#fff}.b3{background:#1d4ed8;color:#fff}
.card{background:#0c0f1e;border-radius:10px;padding:12px;border:1px solid #1a1f40;margin-bottom:8px}
.card h2{color:#818cf8;margin-bottom:6px;font-size:.82em}
.stat{display:inline-block;background:#1a0a3d;border-radius:7px;padding:5px 10px;margin:3px;text-align:center}
.n{font-size:1.3em;font-weight:700;color:#a78bfa}.l{font-size:.63em;color:#6b7280}
table{width:100%;border-collapse:collapse;font-size:.72em}
th{background:#1a1f40;padding:5px;text-align:left;color:#a78bfa}
td{padding:4px 5px;border-bottom:1px solid #1a1f40}
.ok{background:#05291555;color:#34d399;padding:2px 6px;border-radius:8px;font-size:.7em}
.fl{background:#45090a55;color:#f87171;padding:2px 6px;border-radius:8px;font-size:.7em}
.sk{background:#2a1a0055;color:#f97316;padding:2px 6px;border-radius:8px;font-size:.7em}
</style></head><body>
<h1>📋 ABA/DTT/TEACCH/ESDM Clinical Report — {{child}}</h1>
<div class="nav">
  <a href="http://127.0.0.1:5007/" class="b1">📊 Dashboard</a>
  <a href="http://127.0.0.1:5001/" class="b2">📋 Reports</a>
  <a href="http://127.0.0.1:5009/" class="b3">🎮 Games</a>
</div>
<div class="card"><h2>📊 Statistics</h2>
  <div class="stat"><div class="n">{{score}}</div><div class="l">Score</div></div>
  <div class="stat"><div class="n">{{mastered}}</div><div class="l">Mastered</div></div>
  <div class="stat"><div class="n">{{ok}}</div><div class="l">Correct</div></div>
  <div class="stat"><div class="n">{{fail}}</div><div class="l">Fail</div></div>
  <div class="stat"><div class="n">{{skipped}}</div><div class="l">Skipped</div></div>
  <div class="stat"><div class="n">{{att}}%</div><div class="l">Attention</div></div>
</div>
<div class="card"><h2>🎯 Skills</h2>
<table><tr><th>Skill</th><th>Level</th><th>Status</th></tr>
<tr><td>Motor (ABA)</td><td>{{sm}}%</td><td>{{'✅ Good' if sm>60 else '⚠️ Needs work'}}</td></tr>
<tr><td>Cognitive (TEACCH)</td><td>{{sc}}%</td><td>{{'✅ Good' if sc>60 else '⚠️ Needs work'}}</td></tr>
<tr><td>Verbal (DTT)</td><td>{{sv}}%</td><td>{{'✅ Good' if sv>60 else '⚠️ Needs work'}}</td></tr>
<tr><td>Math (Count)</td><td>{{smath}}%</td><td>{{'✅ Good' if smath>60 else '⚠️ Needs work'}}</td></tr>
</table></div>
<div class="card"><h2>📋 Session Log</h2>
<table><tr><th>Time</th><th>Task</th><th>Result</th><th>Emotion</th></tr>
{% for lg in logs[-40:]|reverse %}
<tr><td>{{lg.time}}</td><td>{{lg.msg[:40]}}</td>
<td><span class="{{'ok' if lg.type=='success' else 'fl' if lg.type=='fail' else 'sk'}}">
  {{lg.type.upper()}}</span></td><td>{{lg.emo}}</td></tr>{% endfor %}
</table></div>
<div class="card"><h2>Parent Notes</h2>
{% for n in notes %}<div style="padding:4px;border-left:3px solid #a78bfa;margin:3px 0;font-size:.75em">
  {{n.time}}: {{n.text}}</div>{% endfor %}
{% if not notes %}<p style="color:#6b7280;font-size:.75em">No notes yet.</p>{% endif %}
</div>
<div class="card"><h2>📱 Android Access</h2>
  <p style="color:#34d399;font-size:.8em">Same WiFi → http://{{lip}}:5007</p>
</div>
</body></html>"""

@report_app.route("/")
def report_home():
    return render_template_string(REPORT_HTML,
        child=CHILD_NAME,score=ST["score"],mastered=ST["tasks_mastered"],
        ok=ST["tasks_success"],fail=ST["tasks_fail"],skipped=ST["tasks_skipped"],
        att=ST["attention"],sm=ST["skill_motor"],sc=ST["skill_cognitive"],
        sv=ST["skill_verbal"],smath=ST["skill_math"],
        logs=ST["logs"],notes=ST["parent_notes"],csv=CSV_FILE,lip=LOCAL_IP)

@report_app.errorhandler(404)
def r404(e): return redirect("/"),302

GAMES_HTML="""<!DOCTYPE html><html><head>
<meta charset="UTF-8"><title>Therapy Games — {{child}}</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#060912;color:#e0e6ff;font-family:'Segoe UI',sans-serif;padding:12px}
h1{color:#a78bfa;text-align:center;margin-bottom:8px}
.nav{display:flex;gap:5px;justify-content:center;margin-bottom:8px;flex-wrap:wrap}
.nav a{padding:6px 12px;border-radius:8px;text-decoration:none;font-size:.78em;font-weight:700}
.b1{background:#4f46e5;color:#fff}.b2{background:#059669;color:#fff}.b3{background:#1d4ed8;color:#fff}
.sc{background:#1a0a3d;border-radius:8px;padding:6px 14px;text-align:center;margin-bottom:8px;color:#a78bfa}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;max-width:800px;margin:0 auto}
@media(max-width:500px){.grid{grid-template-columns:repeat(2,1fr)}}
.gc{background:#0c0f1e;border:2px solid #1a1f40;border-radius:11px;padding:12px;
    text-align:center;cursor:pointer;transition:.25s}
.gc:hover,.gc:active{border-color:#a78bfa;transform:translateY(-2px)}
.gi{font-size:2em;margin-bottom:4px}.gn{font-weight:700;color:#e0e6ff;font-size:.85em}
.gd{font-size:.67em;color:#6b7280;margin-top:2px}
#ag{max-width:800px;margin:10px auto}
.btn{background:#4f46e5;color:#fff;border:none;padding:9px 16px;border-radius:7px;
     cursor:pointer;font-size:.82em;margin:4px;min-height:42px;touch-action:manipulation}
.btn-g{background:#059669}
canvas{border:2px solid #4f46e5;border-radius:8px;background:#0a0f1e;
       display:block;margin:8px auto;max-width:100%;touch-action:none}
</style></head><body>
<h1>🎮 Therapy Games — {{child}}</h1>
<div class="nav">
  <a href="http://127.0.0.1:5007/" class="b1">📊 Dashboard</a>
  <a href="http://127.0.0.1:5001/" class="b2">📋 Reports</a>
  <a href="http://127.0.0.1:5009/" class="b3">🎮 Games</a>
</div>
<div class="sc">Score: <span id="pts">0</span> ⭐ | Level: <span id="lvl">1</span></div>
<div class="grid">
  <div class="gc" onclick="start('balloons')"><div class="gi">🎈</div><div class="gn">Balloons</div><div class="gd">Pop them!</div></div>
  <div class="gc" onclick="start('emotions')"><div class="gi">😊</div><div class="gn">Emotions</div><div class="gd">Mirror!</div></div>
  <div class="gc" onclick="start('colors')"><div class="gi">🎨</div><div class="gn">Colors</div><div class="gd">Find it!</div></div>
  <div class="gc" onclick="start('numbers')"><div class="gi">🔢</div><div class="gn">Count</div><div class="gd">How many?</div></div>
  <div class="gc" onclick="start('memory')"><div class="gi">🧠</div><div class="gn">Memory</div><div class="gd">Find pairs!</div></div>
  <div class="gc" onclick="start('shapes')"><div class="gi">⭐</div><div class="gn">Shapes</div><div class="gd">Name it!</div></div>
  <div class="gc" onclick="start('animals')"><div class="gi">🐾</div><div class="gn">Animals</div><div class="gd">Which one?</div></div>
  <div class="gc" onclick="start('fruits')"><div class="gi">🍎</div><div class="gn">Fruits</div><div class="gd">Find it!</div></div>
  <div class="gc" onclick="start('words')"><div class="gi">🔤</div><div class="gn">Words</div><div class="gd">Say it!</div></div>
</div>
<div id="ag"></div>
<script>
var sc=0,lv=1;
function add(n){sc+=n;lv=Math.floor(sc/50)+1;document.getElementById('pts').textContent=sc;document.getElementById('lvl').textContent=lv;}
function start(g){var d=document.getElementById('ag');
  if(g==='balloons')balloons(d);else if(g==='emotions')emoGame(d);
  else if(g==='colors')colorGame(d);else if(g==='numbers')numGame(d);
  else if(g==='memory')memGame(d);else if(g==='shapes')shapeGame(d);
  else if(g==='animals')animalGame(d);else if(g==='fruits')fruitGame(d);else wordGame(d);}
function balloons(d){var W=Math.min(760,window.innerWidth-24);
  d.innerHTML='<canvas id="gc" width="'+W+'" height="300" style="width:100%"></canvas>';
  var c=document.getElementById('gc'),ctx=c.getContext('2d'),bs=[];
  for(var i=0;i<12;i++)bs.push({x:Math.random()*(W-40)+20,y:Math.random()*260+20,r:16+Math.random()*12,
    vx:(Math.random()-0.5)*2.5,vy:(Math.random()-0.5)*2.5,
    color:['#f87171','#34d399','#60a5fa','#fbbf24','#c084fc','#f97316'][Math.floor(Math.random()*6)],alive:true});
  function hit(mx,my){bs.forEach(function(b){if(!b.alive)return;if(Math.sqrt((mx-b.x)**2+(my-b.y)**2)<b.r){b.alive=false;add(10);}});
    if(bs.every(function(b){return !b.alive;}))bs.forEach(function(b){b.alive=true;b.x=Math.random()*(W-40)+20;b.y=Math.random()*260+20;});}
  c.addEventListener('click',function(e){var r=c.getBoundingClientRect(),s=c.width/r.width;hit((e.clientX-r.left)*s,(e.clientY-r.top)*s);});
  c.addEventListener('touchstart',function(e){e.preventDefault();var r=c.getBoundingClientRect(),s=c.width/r.width,t=e.touches[0];hit((t.clientX-r.left)*s,(t.clientY-r.top)*s);},{passive:false});
  (function loop(){ctx.fillStyle='#0a0f1e';ctx.fillRect(0,0,W,300);
    bs.forEach(function(b){if(!b.alive)return;b.x+=b.vx;b.y+=b.vy;
      if(b.x<b.r||b.x>W-b.r)b.vx*=-1;if(b.y<b.r||b.y>300-b.r)b.vy*=-1;
      ctx.beginPath();ctx.arc(b.x,b.y,b.r,0,Math.PI*2);ctx.fillStyle=b.color;ctx.fill();
      ctx.fillStyle='white';ctx.font='14px sans-serif';ctx.textAlign='center';ctx.fillText('🎈',b.x,b.y+5);});requestAnimationFrame(loop);})();}
function emoGame(d){var em=[['😊','Happy'],['😢','Sad'],['😠','Angry'],['😨','Scared'],['😲','Surprised'],['😄','Joyful']];
  var pick=em[Math.floor(Math.random()*em.length)];
  d.innerHTML='<div style="text-align:center;padding:16px"><p style="color:#a78bfa;margin-bottom:8px;font-size:1.1em">Show this face!</p>'+
    '<div style="font-size:5em;margin:12px">'+pick[0]+'</div>'+
    '<p style="font-weight:700;color:#e0e6ff;font-size:1.2em">'+pick[1]+'</p>'+
    '<button class="btn btn-g" onclick="add(20);this.textContent=\'✅ Amazing!\'" style="display:block;width:100%;max-width:220px;margin:12px auto">I did it! 🌟</button>'+
    '<button class="btn" onclick="emoGame(document.getElementById(\'ag\'))" style="display:block;width:100%;max-width:220px;margin:6px auto">Next ➡️</button></div>';}
function colorGame(d){var cs=[['Red','#ef4444'],['Blue','#3b82f6'],['Green','#22c55e'],['Yellow','#eab308'],['Purple','#a855f7'],['Orange','#f97316'],['Pink','#ec4899']];
  var idx=Math.floor(Math.random()*cs.length);
  d.innerHTML='<div style="text-align:center;padding:14px"><p style="color:#a78bfa;margin-bottom:8px">What color?</p>'+
    '<div style="width:100px;height:100px;background:'+cs[idx][1]+';border-radius:50%;margin:10px auto;border:3px solid #374151"></div>'+
    '<div id="cbtns" style="display:flex;flex-wrap:wrap;justify-content:center;gap:6px;margin-top:8px">'+
    cs.map(function(c,i){return '<button class="btn" onclick="chkC('+i+','+idx+')" style="background:'+c[1]+';min-width:80px">'+c[0]+'</button>';}).join('')+'</div></div>';}
window.chkC=function(ch,co){var el=document.getElementById('cbtns');
  if(ch===co){add(15);el.innerHTML='<p style="color:#34d399;margin:8px;font-size:1.1em">✅ Correct! 🌟</p><button class="btn" onclick="colorGame(document.getElementById(\'ag\'))" style="display:block;margin:6px auto">Next ➡️</button>';}
  else el.innerHTML='<p style="color:#f87171;margin:8px">Try again! 💪</p><button class="btn" onclick="colorGame(document.getElementById(\'ag\'))" style="display:block;margin:6px auto">Retry ↩️</button>';};
function numGame(d){var n=Math.floor(Math.random()*10)+1,stars='';for(var i=0;i<n;i++)stars+='⭐';
  var opts=Array.from(new Set([n,Math.max(1,n-1),Math.min(10,n+1),n>2?n-2:n+3])).sort(function(){return Math.random()-0.5;}).slice(0,4);
  d.innerHTML='<div style="text-align:center;padding:14px"><p style="color:#a78bfa;font-size:1.1em">Count the stars!</p>'+
    '<div style="font-size:1.6em;margin:10px;word-break:break-all">'+stars+'</div>'+
    '<div style="display:flex;flex-wrap:wrap;justify-content:center;gap:8px">'+
    opts.map(function(x){return '<button class="btn" onclick="chkN('+x+','+n+')" style="font-size:1.2em;min-width:60px;padding:10px">'+x+'</button>';}).join('')+'</div></div>';}
window.chkN=function(ch,co){if(ch===co){add(20);alert('✅ YES! '+co+'! 🌟');numGame(document.getElementById('ag'));}else alert('Try again! 💪');};
function memGame(d){var pairs=['🐶','🐱','🐻','🦊','🐼','🐨','🦁','🐯'];
  var cards=pairs.concat(pairs).sort(function(){return Math.random()-0.5;});
  window._mc=cards;window._mf=[];window._mm=[];
  d.innerHTML='<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:6px;max-width:360px;margin:10px auto">'+
    cards.map(function(c,i){return '<div id="mc'+i+'" onclick="flipM('+i+')" style="height:70px;background:#1f2937;border-radius:9px;display:flex;align-items:center;justify-content:center;font-size:2em;cursor:pointer;border:2px solid #374151;touch-action:manipulation">❓</div>';}).join('')+'</div>';}
window.flipM=function(idx){var c=window._mc;if(window._mf.length>=2||window._mm.includes(idx)||window._mf.includes(idx))return;
  document.getElementById('mc'+idx).textContent=c[idx];window._mf.push(idx);
  if(window._mf.length===2){var a=window._mf[0],b=window._mf[1];
    if(c[a]===c[b]){window._mm.push(a,b);add(30);window._mf=[];if(window._mm.length===c.length)setTimeout(function(){alert('🎉 ALL MATCHED!');memGame(document.getElementById('ag'));},400);}
    else setTimeout(function(){document.getElementById('mc'+a).textContent='❓';document.getElementById('mc'+b).textContent='❓';window._mf=[];},900);}};
function shapeGame(d){var shapes=[['⬛','Square'],['⭕','Circle'],['🔺','Triangle'],['💎','Diamond'],['⭐','Star'],['❤️','Heart']];
  var pick=shapes[Math.floor(Math.random()*shapes.length)];
  d.innerHTML='<div style="text-align:center;padding:14px"><p style="color:#a78bfa;margin-bottom:8px;font-size:1.1em">What shape?</p>'+
    '<div style="font-size:4.5em;margin:10px">'+pick[0]+'</div>'+
    '<div style="display:flex;flex-wrap:wrap;justify-content:center;gap:6px">'+
    shapes.map(function(s){return '<button class="btn" onclick="chkS(\''+s[1]+'\',\''+pick[1]+'\')" style="min-width:80px">'+s[1]+'</button>';}).join('')+'</div></div>';}
window.chkS=function(ch,co){if(ch===co){add(15);alert('✅ Correct! 🌟');shapeGame(document.getElementById('ag'));}else alert('Try again! 💪');};
function animalGame(d){var animals=[['🐶','Dog'],['🐱','Cat'],['🦁','Lion'],['🐘','Elephant'],['🐰','Rabbit'],['🐻','Bear'],['🐯','Tiger'],['🐧','Penguin']];
  var pick=animals[Math.floor(Math.random()*animals.length)];
  d.innerHTML='<div style="text-align:center;padding:14px"><p style="color:#a78bfa;margin-bottom:8px;font-size:1.1em">Which animal?</p>'+
    '<div style="font-size:5em;margin:10px">'+pick[0]+'</div>'+
    '<div style="display:flex;flex-wrap:wrap;justify-content:center;gap:6px">'+
    animals.slice(0,5).concat([pick]).sort(function(){return Math.random()-0.5;}).slice(0,6).map(function(a){return '<button class="btn" onclick="chkA(\''+a[1]+'\',\''+pick[1]+'\')" style="min-width:80px">'+a[1]+'</button>';}).join('')+'</div></div>';}
window.chkA=function(ch,co){if(ch===co){add(15);alert('✅ Correct! 🌟');animalGame(document.getElementById('ag'));}else alert('Try again! 💪');};
function fruitGame(d){var fruits=[['🍎','Apple'],['🍌','Banana'],['🍊','Orange'],['🍇','Grapes'],['🍓','Strawberry'],['🍉','Watermelon'],['🥭','Mango']];
  var pick=fruits[Math.floor(Math.random()*fruits.length)];
  d.innerHTML='<div style="text-align:center;padding:14px"><p style="color:#a78bfa;margin-bottom:8px;font-size:1.1em">Which fruit?</p>'+
    '<div style="font-size:5em;margin:10px">'+pick[0]+'</div>'+
    '<div style="display:flex;flex-wrap:wrap;justify-content:center;gap:6px">'+
    fruits.slice(0,5).concat([pick]).sort(function(){return Math.random()-0.5;}).slice(0,6).map(function(a){return '<button class="btn" onclick="chkF(\''+a[1]+'\',\''+pick[1]+'\')" style="min-width:80px">'+a[1]+'</button>';}).join('')+'</div></div>';}
window.chkF=function(ch,co){if(ch===co){add(15);alert('✅ Correct! 🌟');fruitGame(document.getElementById('ag'));}else alert('Try again! 💪');};
function wordGame(d){var words=['APPLE','BALL','CAT','DOG','ELEPHANT','FISH','GOOD','HAPPY','JUMP','KITE','LOVE','MILK','PLAY','RED','SUN','TREE','WATER','YES','ONE','TWO','THREE'];
  var word=words[Math.floor(Math.random()*words.length)];
  d.innerHTML='<div style="text-align:center;padding:16px">'+
    '<p style="color:#a78bfa;margin-bottom:8px;font-size:1.1em">Can you say this word?</p>'+
    '<div style="font-size:2.5em;font-weight:700;color:#a78bfa;margin:12px;background:#1e1b4b;padding:15px;border-radius:15px">'+word+'</div>'+
    '<button class="btn btn-g" onclick="add(20);this.textContent=\'✅ Said it!\'" style="display:block;width:100%;max-width:200px;margin:10px auto">I said it! 🎤</button>'+
    '<button class="btn" onclick="wordGame(document.getElementById(\'ag\'))" style="display:block;width:100%;max-width:200px;margin:6px auto">Next ➡️</button></div>';}
</script></body></html>"""

@games_app.route("/")
def games_home(): return render_template_string(GAMES_HTML,child=CHILD_NAME)

@games_app.errorhandler(404)
def g404(e): return redirect("/"),302

def run_server(app,port,name):
    from werkzeug.serving import make_server
    try:
        srv=make_server("0.0.0.0",port,app,threaded=True)
        srv.socket.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        print(f"✅ {name}: http://{LOCAL_IP}:{port}/"); srv.serve_forever()
    except Exception as e: print(f"⚠️  {name}: {e}")

# ══════════════════════════════════════════════════════════════════════
# 18. MAIN — QApplication FIRST on main thread
# ══════════════════════════════════════════════════════════════════════
def main():
    print(f"""
╔══════════════════════════════════════════════════════════╗
║  PEPPER CLINICAL INFINITY V4 — MEDAL GRADE              ║
║  {CHILD_NAME:<52}║
╠══════════════════════════════════════════════════════════╣
║  ✅ QApplication first on main thread (no segfault)    ║
║  ✅ PyBullet watchdog subprocess (auto-restart)        ║
║  ✅ Avatar EMBEDDED in single window                   ║
║  ✅ FaceMesh TESSELATION emotion grid + % bars         ║
║  ✅ QPropertyAnimation balloon celebration             ║
║  ✅ YouTube chat integration                           ║
║  ✅ DTT 2-fail skip + auto parent note                 ║
╚══════════════════════════════════════════════════════════╝
""")

    # QApplication MUST be first on main thread
    qt_app=QApplication(sys.argv)
    qt_app.setApplicationName(f"Pepper Clinical Infinity V4 — {CHILD_NAME}")
    qt_app.setStyle("Fusion")
    palette=QPalette()
    palette.setColor(QPalette.ColorRole.Window,    QColor(6,9,18))
    palette.setColor(QPalette.ColorRole.WindowText,QColor(224,230,255))
    palette.setColor(QPalette.ColorRole.Base,      QColor(12,15,30))
    palette.setColor(QPalette.ColorRole.Text,      QColor(224,230,255))
    qt_app.setPalette(palette)

    # Single main window (W4 + Avatar + Emotion embedded)
    window=MainWindow(); window.show(); window.move(10,560)

    # Flask servers
    for app_,port,name in [(parent_app,5007,"Parent Dashboard"),
                            (report_app,5001,"Clinical Reports"),
                            (games_app, 5009,"Games")]:
        threading.Thread(target=run_server,args=(app_,port,name),daemon=True).start()
        time.sleep(0.3)
    time.sleep(0.5)

    # Camera (QThread — safe)
    cam=CameraThread(); cam.start()

    # PyBullet watchdog subprocess (W1)
    pb=PBWatchdog(CHILD_NAME); pb.start()

    # Voice + Therapy
    voice=Voice(); ctrl=TherapyCtrl(voice,pb)

    def _start():
        time.sleep(1.8); ctrl.run()

    threading.Thread(target=_start,daemon=True).start()

    print(f"""
{'='*62}
✅ CLINICAL INFINITY V4 ACTIVE — SINGLE WINDOW
{'='*62}
W1: PyBullet    (subprocess watchdog — auto-restart on crash)
W4: Main Window (1320×800 — camera + avatar + emotion + tasks)
    LEFT:  Camera(440px) | Avatar(220×280) | Emotion bars
           Chat area + mic + input
    RIGHT: TEACCH schedule | Instructions | Task content
           Feedback | Mic button | Stats

Child:   {CHILD_NAME} | Age:{ST['age']}
CSV:     {CSV_FILE}
Tasks:   {len(TASK_POOL)} variations

Parent:  http://127.0.0.1:5007/
Reports: http://127.0.0.1:5001/
Games:   http://127.0.0.1:5009/
Android: http://{LOCAL_IP}:5007/

n=next | b=break | r=report | q=quit
{'='*62}
""")

    def _input_loop():
        while ctrl.running:
            try:
                cmd=input("> ").strip().lower()
                if cmd in ["q","exit","quit"]:
                    ctrl.running=False; cam.stop(); pb.stop(); qt_app.quit(); break
                elif cmd in ["n","next"]:  ST["sim_cmd"]="next"
                elif cmd in ["b","break"]: ST["sim_cmd"]="break"
                elif cmd in ["r","report"]:ST["sim_cmd"]="report"
                elif cmd=="stats":
                    tidx=min(ST["task_index"],len(TASK_POOL)-1); t_=TASK_POOL[tidx]
                    print(f"\nTask:{t_['id']} | ★{ST['consecutive']}/3 | "
                          f"Fails:{ST['fail_count']}/{MAX_FAILS} | "
                          f"Score:{ST['score']} | Fingers:{ST['finger_count']} | "
                          f"Emotion:{ST['emotion']} | "
                          f"Pct:{ST.get('emotion_pct',{})}")
            except (KeyboardInterrupt,EOFError): break
        qt_app.quit()

    threading.Thread(target=_input_loop,daemon=True).start()
    ret=qt_app.exec()

    ctrl.running=False; cam.stop(); pb.stop()
    dur=int((time.time()-ST["uptime"])/60)
    fn=f"session_{SAFE_NAME}_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(fn,"w") as f: json.dump(ST,f,indent=2,default=str)
    print(f"\n{'='*55}\nSESSION COMPLETE — {CHILD_NAME} | {dur} min\n"
          f"Score:{ST['score']} | Mastered:{ST['tasks_mastered']} | Skip:{ST['tasks_skipped']}\n"
          f"CSV:{CSV_FILE} | JSON:{fn}\n{'='*55}")
    sys.exit(ret)

if __name__=="__main__":
    main()
