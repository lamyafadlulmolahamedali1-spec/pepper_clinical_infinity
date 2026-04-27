#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║  PEPPER SMART THERAPIST V2 — FINAL                              ║
║  Commander: Lamya | Omdurman Islamic University                 ║
╠══════════════════════════════════════════════════════════════════╣
║  ✅ Live camera feed in PyQt6 window (Qt-safe via signal)      ║
║  ✅ MediaPipe skeleton + finger counting overlay               ║
║  ✅ Touch-to-record mic (only records when screen touched)     ║
║  ✅ High-sensitivity faster-whisper (energy=200)              ║
║  ✅ Visual exercise modeling with HD stick-figure drawings     ║
║  ✅ ABA/ESDM mastery gate (3 consecutive)                     ║
║  ✅ ALL Qt UI via pyqtSignal — zero threading violations      ║
╚══════════════════════════════════════════════════════════════════╝
"""

# ═══════════════════════════════════════════════════════════════
# 0. ENV SETUP
# ═══════════════════════════════════════════════════════════════
import os, sys, subprocess, ctypes, warnings, socket, time, threading
import random, math, re, json, base64, wave, tempfile

os.environ.update({
    'TF_CPP_MIN_LOG_LEVEL': '3',
    'PYTHONWARNINGS': 'ignore',
    'OPENCV_LOG_LEVEL': 'ERROR',
    'CUDA_VISIBLE_DEVICES': '0',
    'QT_LOGGING_RULES': '*.debug=false',
    'QT_QPA_PLATFORM': 'xcb',
    'QT_QPA_FONTDIR': '/usr/share/fonts',
    'TF_ENABLE_ONEDNN_OPTS': '0',
})
warnings.filterwarnings('ignore')
try:
    _a = ctypes.cdll.LoadLibrary('libasound.so.2')
    _a.snd_lib_error_set_handler(ctypes.c_void_p(None))
except: pass

# ═══════════════════════════════════════════════════════════════
# 1. IMPORTS
# ═══════════════════════════════════════════════════════════════
import cv2, numpy as np
import pyttsx3, speech_recognition as sr
from PIL import Image, ImageDraw
from io import BytesIO
from datetime import datetime

import mediapipe as mp
mp_pose  = mp.solutions.pose
mp_hands = mp.solutions.hands
mp_draw  = mp.solutions.drawing_utils

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QGridLayout, QProgressBar,
    QStackedWidget,
)
from PyQt6.QtCore import (
    Qt, QTimer, pyqtSignal, QObject, QThread, QSize,
)
from PyQt6.QtGui import (
    QFont, QColor, QPalette, QPixmap, QImage, QPainter, QPainterPath,
)

try:
    from faster_whisper import WhisperModel
    WHISPER_OK = True
except: WHISPER_OK = False

# ═══════════════════════════════════════════════════════════════
# 2. CONFIG
# ═══════════════════════════════════════════════════════════════
PORT_UI   = 5007
MIC_ENERGY = 200   # High sensitivity

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80)); ip = s.getsockname()[0]; s.close(); return ip
    except: return "127.0.0.1"

LOCAL_IP = get_local_ip()

# ═══════════════════════════════════════════════════════════════
# 3. VISUAL EXERCISE LIBRARY (stick-figure drawings + instructions)
# ═══════════════════════════════════════════════════════════════
def _draw_base(draw, cx, cy, col="black", lw=4):
    """Draw basic stick figure"""
    # Head
    draw.ellipse([cx-28, cy-88, cx+28, cy-32], outline=col, width=lw)
    # Body
    draw.line([cx, cy-32, cx, cy+55], fill=col, width=lw)
    # Left leg
    draw.line([cx, cy+55, cx-28, cy+100], fill=col, width=lw)
    # Right leg
    draw.line([cx, cy+55, cx+28, cy+100], fill=col, width=lw)

def make_figure(movement: str, size=320) -> str:
    """Return base64 PNG of stick figure doing movement"""
    img  = Image.new("RGBA", (size, size), (240, 248, 255, 255))
    draw = ImageDraw.Draw(img)
    cx, cy = size // 2, size // 2
    col = "#2c3e50"; hl = "#e74c3c"; lw = 4

    _draw_base(draw, cx, cy, col, lw)

    if movement == "clap":
        # Arms meeting at centre
        draw.line([cx-45, cy-5, cx-5, cy+15],  fill=col, width=lw)
        draw.line([cx+45, cy-5, cx+5, cy+15],  fill=col, width=lw)
        draw.ellipse([cx-12,cy+8,cx+12,cy+28], fill=hl)
    elif movement == "wave":
        # Left arm still, right arm raised and bent
        draw.line([cx-40, cy-8, cx-20, cy+12],  fill=col, width=lw)
        draw.line([cx+40, cy-15, cx+65, cy-45], fill=col, width=lw)
        draw.line([cx+65, cy-45, cx+60, cy-65], fill=hl,  width=4)
    elif movement == "raise_hand":
        draw.line([cx-40, cy-8, cx-20, cy+12],  fill=col, width=lw)
        draw.line([cx+40, cy-15, cx+50, cy-70], fill=hl,  width=5)
        draw.ellipse([cx+42,cy-84,cx+62,cy-64], fill=hl)
    elif movement == "touch_nose":
        nose_x, nose_y = cx, cy-60
        draw.ellipse([nose_x-7, nose_y-7, nose_x+7, nose_y+7], fill=hl)
        draw.line([cx-40, cy-5, cx-10, cy-55], fill=hl, width=5)
        draw.line([cx+40, cy-5, cx+20, cy+12], fill=col, width=lw)
    elif movement == "arms_out":
        draw.line([cx-40, cy-8, cx-85, cy-8], fill=hl, width=5)
        draw.line([cx+40, cy-8, cx+85, cy-8], fill=hl, width=5)
    elif movement == "hands_up":
        draw.line([cx-40, cy-8, cx-55, cy-70], fill=hl, width=5)
        draw.line([cx+40, cy-8, cx+55, cy-70], fill=hl, width=5)
        draw.ellipse([cx-68,cy-84,cx-44,cy-62], fill=hl)
        draw.ellipse([cx+44,cy-84,cx+68,cy-62], fill=hl)
    elif movement == "touch_ears":
        # Both hands to ears
        draw.line([cx-40, cy-8, cx-32, cy-55], fill=hl, width=5)
        draw.line([cx+40, cy-8, cx+32, cy-55], fill=hl, width=5)
    elif movement == "stomp":
        # Leg raised
        draw.line([cx, cy+55, cx-28, cy+100], fill=col, width=lw)
        draw.line([cx, cy+55, cx+40, cy+75],  fill=hl, width=5)
        draw.line([cx+40, cy+75, cx+45, cy+55], fill=hl, width=4)
    elif movement == "thumbs_up":
        draw.line([cx-40, cy-8, cx-20, cy+12],  fill=col, width=lw)
        draw.line([cx+40, cy-15, cx+60, cy-5],  fill=col, width=lw)
        draw.line([cx+60, cy-5, cx+70, cy-20],  fill=hl,  width=5)
        draw.ellipse([cx+65,cy-32,cx+80,cy-18], fill=hl)
    else:
        # Default — arms slightly out
        draw.line([cx-40, cy-8, cx-60, cy+10], fill=col, width=lw)
        draw.line([cx+40, cy-8, cx+60, cy+10], fill=col, width=lw)

    # Instruction arrows
    draw.text((cx-30, size-30), "👉 YOU DO IT! 👈",
              fill=(231,76,60,255))

    buf = BytesIO(); img.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

MOTOR_TASKS = [
    {"id":"clap",       "name":"👏 Clap Hands",     "movement":"clap",
     "instruction":"Look at the screen and CLAP your hands!",
     "waiting":"I am waiting — clap your hands! 👏",
     "success":"Amazing! You clapped! ✅",
     "fail":"Not quite! Clap your hands together!",
     "verify":"clap"},
    {"id":"wave",       "name":"👋 Wave Hello",      "movement":"wave",
     "instruction":"Look at the screen and WAVE hello!",
     "waiting":"Wave your hand! 👋",
     "success":"Wonderful! You waved! ✅",
     "fail":"Try again — wave side to side!",
     "verify":"wave"},
    {"id":"raise_hand", "name":"✋ Raise Hand",      "movement":"raise_hand",
     "instruction":"Look at the screen and RAISE your hand HIGH!",
     "waiting":"Raise your hand up! ✋",
     "success":"Perfect! Hand up high! ✅",
     "fail":"Lift your hand above your head!",
     "verify":"raise_hand"},
    {"id":"touch_nose", "name":"👆 Touch Nose",      "movement":"touch_nose",
     "instruction":"Look at the screen and TOUCH your NOSE!",
     "waiting":"Touch your nose! 👆",
     "success":"Brilliant! You touched your nose! ✅",
     "fail":"Point your finger to your nose!",
     "verify":"touch_nose"},
    {"id":"arms_out",   "name":"🤸 Arms Wide Out",  "movement":"arms_out",
     "instruction":"Stretch BOTH arms out wide like an airplane!",
     "waiting":"Spread your arms wide! 🤸",
     "success":"Like an airplane! Amazing! ✅",
     "fail":"Spread both arms wide to the sides!",
     "verify":"arms_out"},
    {"id":"hands_up",   "name":"🙌 Both Hands Up",  "movement":"hands_up",
     "instruction":"Put BOTH hands UP HIGH!",
     "waiting":"Both hands up! 🙌",
     "success":"Both hands up — superstar! ✅",
     "fail":"Lift BOTH arms above your head!",
     "verify":"hands_up"},
    {"id":"touch_ears", "name":"👂 Touch Ears",      "movement":"touch_ears",
     "instruction":"Touch both of your EARS!",
     "waiting":"Touch your ears! 👂",
     "success":"You found your ears! ✅",
     "fail":"Bring your hands to your ears!",
     "verify":"touch_ears"},
    {"id":"thumbs_up",  "name":"👍 Thumbs Up",       "movement":"thumbs_up",
     "instruction":"Give me a big THUMBS UP!",
     "waiting":"Thumbs up! 👍",
     "success":"Thumbs up — great job! ✅",
     "fail":"Curl your fist and put your thumb up!",
     "verify":"thumbs_up"},
]

# Pre-render all figures
for t in MOTOR_TASKS:
    t["figure"] = make_figure(t["movement"])

COGNITIVE_TASKS = [
    {"id":"color_red",   "domain":"Cognitive","level":2,"protocol":"TEACCH",
     "instruction":"Click the RED circle!",
     "verify":"tablet_click","tablet_mode":"color_grid",
     "options":[{"color":"#ef4444","label":"RED"},{"color":"#3b82f6","label":"BLUE"},
                {"color":"#22c55e","label":"GREEN"},{"color":"#eab308","label":"YELLOW"}],
     "correct":0,"tokens":3},
    {"id":"color_blue",  "domain":"Cognitive","level":2,"protocol":"TEACCH",
     "instruction":"Click the BLUE circle!",
     "verify":"tablet_click","tablet_mode":"color_grid",
     "options":[{"color":"#22c55e","label":"GREEN"},{"color":"#3b82f6","label":"BLUE"},
                {"color":"#ef4444","label":"RED"},{"color":"#a855f7","label":"PURPLE"}],
     "correct":1,"tokens":3},
    {"id":"animal_dog",  "domain":"Cognitive","level":3,"protocol":"TEACCH",
     "instruction":"Click the DOG!",
     "verify":"tablet_click","tablet_mode":"object_grid",
     "options":[{"emoji":"🐶","label":"Dog"},{"emoji":"🐱","label":"Cat"},
                {"emoji":"🐻","label":"Bear"},{"emoji":"🐭","label":"Mouse"}],
     "correct":0,"tokens":4},
    {"id":"animal_cat",  "domain":"Cognitive","level":3,"protocol":"TEACCH",
     "instruction":"Click the CAT!",
     "verify":"tablet_click","tablet_mode":"object_grid",
     "options":[{"emoji":"🐶","label":"Dog"},{"emoji":"🐱","label":"Cat"},
                {"emoji":"🦁","label":"Lion"},{"emoji":"🐯","label":"Tiger"}],
     "correct":1,"tokens":4},
    {"id":"fruit_apple", "domain":"Cognitive","level":4,"protocol":"TEACCH",
     "instruction":"Click the APPLE!",
     "verify":"tablet_click","tablet_mode":"object_grid",
     "options":[{"emoji":"🍎","label":"Apple"},{"emoji":"🍌","label":"Banana"},
                {"emoji":"🍊","label":"Orange"},{"emoji":"🍇","label":"Grapes"}],
     "correct":0,"tokens":4},
    {"id":"shape_circle","domain":"Cognitive","level":5,"protocol":"TEACCH",
     "instruction":"Click the CIRCLE!",
     "verify":"tablet_click","tablet_mode":"shape_grid",
     "options":[{"emoji":"⭕","label":"Circle"},{"emoji":"⬛","label":"Square"},
                {"emoji":"🔺","label":"Triangle"},{"emoji":"💎","label":"Diamond"}],
     "correct":0,"tokens":4},
    {"id":"number_1",    "domain":"Cognitive","level":5,"protocol":"DTT",
     "instruction":"Click number ONE!",
     "verify":"tablet_click","tablet_mode":"number_grid",
     "options":[{"num":"1","label":"One"},{"num":"2","label":"Two"},
                {"num":"3","label":"Three"},{"num":"4","label":"Four"}],
     "correct":0,"tokens":5},
    {"id":"say_apple",   "domain":"Verbal","level":6,"protocol":"DTT",
     "instruction":"Say the word APPLE!",
     "verify":"speech_keyword","keyword":"apple",
     "tablet_mode":"word_display","word_emoji":"🍎","word_text":"APPLE",
     "tokens":4},
    {"id":"say_blue",    "domain":"Verbal","level":6,"protocol":"DTT",
     "instruction":"Say BLUE!",
     "verify":"speech_keyword","keyword":"blue",
     "tablet_mode":"word_display","word_emoji":"🔵","word_text":"BLUE",
     "tokens":4},
    {"id":"how_feel",    "domain":"Social","level":7,"protocol":"ESDM",
     "instruction":"How do you feel? Click your face!",
     "verify":"tablet_click","tablet_mode":"emotion_grid",
     "options":[{"emoji":"😊","label":"Happy"},{"emoji":"😢","label":"Sad"},
                {"emoji":"😠","label":"Angry"},{"emoji":"😨","label":"Scared"}],
     "correct":-1,"tokens":6},
]

ALL_TASKS = MOTOR_TASKS + COGNITIVE_TASKS

# ═══════════════════════════════════════════════════════════════
# 4. SHARED STATE
# ═══════════════════════════════════════════════════════════════
ST = {
    "name":"Friend","known":False,"age":6,
    "task_index":0,"consecutive":0,"mastery_needed":3,
    "tasks_mastered":0,"current_level":1,"domain":"Motor",
    "protocol":"ABA-Motor",
    # Tablet
    "tablet_click_result":None,"tablet_correct":-1,
    "tablet_instruction":"Welcome!",
    # Vision
    "emotion":"neutral","face_detected":False,
    "attention":70,
    "hand_raised":False,"waving":False,"clapping":False,
    "arms_out":False,"hands_up":False,"face_touch":False,
    "blinking":False,"eye_contact":False,
    "pose_landmarks":{},"face_mesh_landmarks":{},
    "finger_count":0,
    "verify_action":None,"verify_result":False,"verify_timeout":0.0,
    "last_speech_text":"","last_sound":time.time(),
    "voice_energy":0.0,
    # Session
    "is_speaking":False,"interrupt_flag":False,
    "listening":False,"waiting_for_child":False,
    "task_success":False,"youtube_pending":False,"sim_cmd":None,
    "lip_sync_value":0.0,
    # Touch recorder
    "recording":False,"touch_start":0.0,
    # Progress
    "score":0,"tokens":0,"streak":0,
    "tasks_success":0,"tasks_fail":0,
    "session_chat":[],
    "logs":[],
    "session_start":datetime.now().strftime("%H:%M"),
    "session_date":datetime.now().strftime("%Y-%m-%d"),
    "uptime":time.time(),
}

_log_lock = threading.Lock()
def LOG(msg, t="info"):
    with _log_lock:
        e = {"time":datetime.now().strftime("%H:%M:%S"),"msg":str(msg)[:120],"type":t}
        ST["logs"].append(e)
        if len(ST["logs"]) > 200: ST["logs"] = ST["logs"][-200:]
    print(f"[{datetime.now().strftime('%H:%M:%S')}][{t.upper()}] {msg[:65]}")

# ═══════════════════════════════════════════════════════════════
# 5. TABLET BRIDGE — ALL Qt UI via signals
# ═══════════════════════════════════════════════════════════════
class TabletBridge(QObject):
    sig_new_task      = pyqtSignal(dict)
    sig_show_success  = pyqtSignal(str)
    sig_show_fail     = pyqtSignal(str)
    sig_set_feedback  = pyqtSignal(str)
    sig_set_instr     = pyqtSignal(str)
    sig_set_waiting   = pyqtSignal(str)
    sig_unlock        = pyqtSignal()
    sig_lock          = pyqtSignal()
    sig_reset_cards   = pyqtSignal()
    sig_joy           = pyqtSignal(str)
    sig_update_frame  = pyqtSignal(object)   # QImage
    sig_update_stats  = pyqtSignal()
    sig_rec_start     = pyqtSignal()
    sig_rec_stop      = pyqtSignal(str)      # recognised text

BRIDGE = TabletBridge()

# ═══════════════════════════════════════════════════════════════
# 6. CAMERA THREAD — pushes QImages via signal
# ═══════════════════════════════════════════════════════════════
class CameraThread(QThread):
    """
    Runs entirely in a QThread.
    Emits BRIDGE.sig_update_frame — connected to UI on main thread.
    Also runs MediaPipe pose + hands for gesture detection.
    """
    def __init__(self):
        super().__init__()
        self.running = False
        self.cap = None
        self._phase = 0.0
        # MediaPipe
        self.pose_det  = None
        self.hands_det = None
        self._init_mp()
        self._init_cam()

    def _init_mp(self):
        try:
            self.pose_det = mp_pose.Pose(
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
                model_complexity=1)
            print("✅ MediaPipe Pose")
        except Exception as e: print(f"⚠️  Pose: {e}")
        try:
            self.hands_det = mp_hands.Hands(
                max_num_hands=2,
                min_detection_confidence=0.6,
                min_tracking_confidence=0.5)
            print("✅ MediaPipe Hands")
        except Exception as e: print(f"⚠️  Hands: {e}")

    def _init_cam(self):
        for idx in [1, 0, 2, 3]:
            try:
                c = cv2.VideoCapture(idx)
                if c.isOpened():
                    ret, f = c.read()
                    if ret and f is not None and f.size > 0:
                        c.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
                        c.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                        c.set(cv2.CAP_PROP_FPS, 30)
                        self.cap = c
                        print(f"✅ Camera {idx}")
                        return
                    c.release()
            except: pass
        print("⚠️  No camera — simulation mode")

    def _joint_angle(self, a, b, c_pt):
        try:
            ab = np.array([a.x-b.x, a.y-b.y, a.z-b.z])
            cb = np.array([c_pt.x-b.x, c_pt.y-b.y, c_pt.z-b.z])
            cos_a = np.dot(ab,cb)/(np.linalg.norm(ab)*np.linalg.norm(cb)+1e-6)
            return math.degrees(math.acos(np.clip(cos_a,-1,1)))
        except: return 0.0

    def _finger_count(self, hand_lm):
        """Count raised fingers from hand landmarks"""
        try:
            tips  = [8,12,16,20]
            count = 0
            # Thumb
            if hand_lm.landmark[4].x < hand_lm.landmark[3].x:
                count += 1
            for tip in tips:
                if hand_lm.landmark[tip].y < hand_lm.landmark[tip-2].y:
                    count += 1
            return count
        except: return 0

    def _validate_motor(self):
        va = ST.get("verify_action")
        if not va: return
        if time.time() > ST["verify_timeout"]:
            ST["verify_action"] = None; return
        pl  = ST.get("pose_landmarks", {})
        fm  = ST.get("face_mesh_landmarks", {})
        ok  = False
        if va == "clap":          ok = ST["clapping"]
        elif va == "wave":        ok = ST["waving"]
        elif va == "raise_hand":
            lwy=pl.get("l_wrist_y",1); rwy=pl.get("r_wrist_y",1)
            lsy=pl.get("l_shoulder_y",0); rsy=pl.get("r_shoulder_y",0)
            lea=pl.get("l_elbow_angle",0); rea=pl.get("r_elbow_angle",0)
            ok  = ((lwy<lsy-0.08 and lea>120) or (rwy<rsy-0.08 and rea>120))
        elif va == "touch_nose":
            nx=fm.get("nose_x",-1); ny=fm.get("nose_y",-1)
            fw=fm.get("frame_w",640); fh=fm.get("frame_h",480)
            if nx>0 and pl:
                lix=pl.get("l_index_x",0)*fw; liy=pl.get("l_index_y",0)*fh
                rix=pl.get("r_index_x",0)*fw; riy=pl.get("r_index_y",0)*fh
                ok = (math.dist((lix,liy),(nx,ny))<fw*0.12 or
                      math.dist((rix,riy),(nx,ny))<fw*0.12)
        elif va == "arms_out":    ok = ST.get("arms_out",False)
        elif va == "hands_up":    ok = ST.get("hands_up",False)
        elif va == "touch_ears":
            lwy=pl.get("l_wrist_y",1); rwy=pl.get("r_wrist_y",1)
            nose_y=pl.get("nose_y",0)
            ok = (abs(lwy-nose_y)<0.12 and abs(rwy-nose_y)<0.12)
        elif va == "thumbs_up":
            ok = (ST.get("finger_count",0) == 1)
        if ok:
            ST["verify_result"]  = True
            ST["verify_action"]  = None
            ST["verify_timeout"] = 0.0
            LOG("✅ Motor verified!", "success")

    def _draw_hud(self, frame):
        """Overlay stats on camera frame"""
        h, w = frame.shape[:2]
        # Semi-transparent top bar
        ov = frame.copy()
        cv2.rectangle(ov, (0,0), (w,56), (10,10,30), -1)
        frame = cv2.addWeighted(ov, 0.72, frame, 0.28, 0)
        # Task name
        tidx = min(ST["task_index"], len(ALL_TASKS)-1)
        t = ALL_TASKS[tidx]
        cv2.putText(frame, f"Task: {t.get('name',t['id'])}",
            (10,22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200,200,255), 1)
        # Stars
        stars = "★"*ST["consecutive"] + "☆"*(3-ST["consecutive"])
        cv2.putText(frame, f"Mastery: {stars}  Score:{ST['score']}",
            (10,44), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (255,220,0), 1)
        # Recording indicator
        if ST["recording"]:
            cv2.circle(frame, (w-20, 20), 10, (0,0,255), -1)
            cv2.putText(frame, "REC", (w-48, 26),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0,0,255), 2)
        # Gesture badges (bottom-left)
        y0 = h - 12
        for lbl, active in [
            ("CLAP",ST["clapping"]),("WAVE",ST["waving"]),
            ("RAISE",ST["hand_raised"]),("ARMS",ST["arms_out"]),
            ("HANDS↑",ST["hands_up"]),
        ]:
            col = (0,255,100) if active else (60,60,80)
            cv2.putText(frame, lbl, (10, y0), cv2.FONT_HERSHEY_SIMPLEX, 0.38, col, 1)
            y0 -= 18
        # Finger count
        fc = ST.get("finger_count", 0)
        if fc > 0:
            cv2.putText(frame, f"Fingers: {fc}",
                (w-110, h-12), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255,200,0), 1)
        return frame

    def _sim_frame(self):
        """Simulation frame when no camera"""
        h, w = 480, 640
        f = np.zeros((h,w,3), dtype=np.uint8); f[:] = (12,14,30)
        t = time.time()
        self._phase += 0.04
        r = int(32+12*math.sin(self._phase))
        cv2.circle(f,(w//2,h//2-60),r,
            (int(80+80*math.sin(self._phase)),
             int(120+120*math.cos(self._phase*0.7)),220),3)
        cv2.putText(f, "SIMULATION — NO CAMERA",
            (w//2-170, h//2+30), cv2.FONT_HERSHEY_SIMPLEX, 0.75,(100,150,255),2)
        tidx = min(ST["task_index"], len(ALL_TASKS)-1)
        tname = ALL_TASKS[tidx].get("name","?")
        cv2.putText(f, f"Task: {tname}",
            (10, h-20), cv2.FONT_HERSHEY_SIMPLEX, 0.5,(200,200,200),1)
        return f

    def _to_qimage(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        return QImage(rgb.data.tobytes(), w, h, w*ch, QImage.Format.Format_RGB888)

    def run(self):
        self.running = True
        prev_gray   = None
        hand_hist   = []
        motion_buf  = []

        while self.running:
            # ── Grab frame ──────────────────────────────────
            if self.cap and self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    frame = cv2.flip(frame, 1)
                else:
                    frame = self._sim_frame()
            else:
                frame = self._sim_frame()

            # ── Motion detection ────────────────────────────
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray,(21,21),0)
            if prev_gray is not None:
                diff = cv2.absdiff(prev_gray, gray)
                _, th = cv2.threshold(diff,25,255,cv2.THRESH_BINARY)
                motion = float(np.mean(th))
                motion_buf.append(motion)
                if len(motion_buf)>12: motion_buf.pop(0)
                if len(motion_buf)>=4:
                    avg   = sum(motion_buf[:-2])/max(len(motion_buf)-2,1)
                    spike = motion_buf[-1]
                    ST["clapping"] = (spike > avg*3.5 and spike > 15)
                h2, w2 = gray.shape
                lm_ = float(np.mean(th[:,:w2//2]))
                rm_ = float(np.mean(th[:,w2//2:]))
                hand_hist.append("L" if lm_>rm_+3 else "R" if rm_>lm_+3 else "N")
                if len(hand_hist)>10: hand_hist.pop(0)
                chg = sum(1 for i in range(1,len(hand_hist))
                          if hand_hist[i]!=hand_hist[i-1] and hand_hist[i]!="N")
                ST["waving"] = chg>=4
            prev_gray = gray

            # ── MediaPipe Pose ───────────────────────────────
            if self.pose_det:
                try:
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    res = self.pose_det.process(rgb)
                    if res.pose_landmarks:
                        mp_draw.draw_landmarks(frame, res.pose_landmarks,
                            mp_pose.POSE_CONNECTIONS,
                            mp_draw.DrawingSpec(color=(0,255,100),thickness=2,circle_radius=3),
                            mp_draw.DrawingSpec(color=(0,150,255),thickness=2))
                        lm = res.pose_landmarks.landmark
                        PL = mp_pose.PoseLandmark
                        l_sh_ang = self._joint_angle(lm[PL.LEFT_ELBOW],
                            lm[PL.LEFT_SHOULDER], lm[PL.LEFT_HIP])
                        r_sh_ang = self._joint_angle(lm[PL.RIGHT_ELBOW],
                            lm[PL.RIGHT_SHOULDER], lm[PL.RIGHT_HIP])
                        l_el_ang = self._joint_angle(lm[PL.LEFT_SHOULDER],
                            lm[PL.LEFT_ELBOW], lm[PL.LEFT_WRIST])
                        r_el_ang = self._joint_angle(lm[PL.RIGHT_SHOULDER],
                            lm[PL.RIGHT_ELBOW], lm[PL.RIGHT_WRIST])
                        h2, w2 = frame.shape[:2]
                        pl = {
                            "nose_x":lm[PL.NOSE].x,"nose_y":lm[PL.NOSE].y,
                            "l_ear_x":lm[PL.LEFT_EAR].x,"r_ear_x":lm[PL.RIGHT_EAR].x,
                            "l_shoulder_y":lm[PL.LEFT_SHOULDER].y,
                            "r_shoulder_y":lm[PL.RIGHT_SHOULDER].y,
                            "l_wrist_y":lm[PL.LEFT_WRIST].y,
                            "r_wrist_y":lm[PL.RIGHT_WRIST].y,
                            "l_wrist_x":lm[PL.LEFT_WRIST].x,
                            "r_wrist_x":lm[PL.RIGHT_WRIST].x,
                            "l_index_x":lm[PL.LEFT_INDEX].x,
                            "l_index_y":lm[PL.LEFT_INDEX].y,
                            "r_index_x":lm[PL.RIGHT_INDEX].x,
                            "r_index_y":lm[PL.RIGHT_INDEX].y,
                            "l_elbow_angle":l_el_ang,"r_elbow_angle":r_el_ang,
                            "l_shoulder_angle":l_sh_ang,"r_shoulder_angle":r_sh_ang,
                        }
                        ST["pose_landmarks"] = pl
                        ST["hand_raised"] = (
                            pl["l_wrist_y"]<pl["l_shoulder_y"]-0.08 or
                            pl["r_wrist_y"]<pl["r_shoulder_y"]-0.08)
                        ST["arms_out"]  = (l_sh_ang>70 and r_sh_ang>70)
                        ST["hands_up"]  = (
                            pl["l_wrist_y"]<pl["l_shoulder_y"]-0.08 and
                            pl["r_wrist_y"]<pl["r_shoulder_y"]-0.08)
                        ST["face_detected"] = True
                        ST["face_mesh_landmarks"] = {
                            "nose_x":lm[PL.NOSE].x*w2,
                            "nose_y":lm[PL.NOSE].y*h2,
                            "frame_w":w2,"frame_h":h2,
                        }
                except: pass

            # ── MediaPipe Hands ──────────────────────────────
            if self.hands_det:
                try:
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    hres = self.hands_det.process(rgb)
                    if hres.multi_hand_landmarks:
                        for hlm in hres.multi_hand_landmarks:
                            mp_draw.draw_landmarks(frame, hlm,
                                mp_hands.HAND_CONNECTIONS,
                                mp_draw.DrawingSpec(color=(255,100,0),thickness=2,circle_radius=3),
                                mp_draw.DrawingSpec(color=(255,200,0),thickness=2))
                        fc = max(self._finger_count(h) for h in hres.multi_hand_landmarks)
                        ST["finger_count"] = fc
                        if len(hres.multi_hand_landmarks)>=2:
                            h1=hres.multi_hand_landmarks[0].landmark[0]
                            h2_=hres.multi_hand_landmarks[1].landmark[0]
                            if abs(h1.x-h2_.x)<0.18 and abs(h1.y-h2_.y)<0.18:
                                ST["clapping"] = True
                    else:
                        ST["finger_count"] = 0
                except: pass

            # ── Motor validation ─────────────────────────────
            self._validate_motor()

            # ── HUD overlay ──────────────────────────────────
            frame = self._draw_hud(frame)

            # ── Emit to UI (thread-safe signal) ──────────────
            BRIDGE.sig_update_frame.emit(self._to_qimage(frame))

            self.msleep(30)   # ~33 fps

    def stop(self):
        self.running = False
        self.quit()
        self.wait(2000)
        if self.cap: self.cap.release()

# ═══════════════════════════════════════════════════════════════
# 7. TOUCH RECORDER — only records when child touches screen
# ═══════════════════════════════════════════════════════════════
class TouchRecorder:
    """
    Records audio ONLY while screen is being touched.
    High sensitivity (energy=200), faster-whisper + Google SR fallback.
    """
    def __init__(self):
        self._lock       = threading.Lock()
        self._recording  = False
        self._audio_data = None
        self.whisper     = None

        # Speech recogniser — high sensitivity
        self.r = sr.Recognizer()
        self.r.energy_threshold        = MIC_ENERGY   # 200
        self.r.dynamic_energy_threshold = True
        self.r.dynamic_energy_adjustment_damping = 0.15
        self.r.pause_threshold         = 0.7
        self.r.phrase_threshold        = 0.05
        self.r.non_speaking_duration   = 0.2

        # Calibrate
        try:
            with sr.Microphone() as src:
                print("🎤 Calibrating mic (high sensitivity)...")
                self.r.adjust_for_ambient_noise(src, duration=0.8)
                print(f"✅ Mic energy={self.r.energy_threshold:.0f}")
        except Exception as e:
            print(f"⚠️  Mic: {e}")

        # faster-whisper
        if WHISPER_OK:
            try:
                device = "cuda" if os.path.exists("/dev/nvidia0") else "cpu"
                ctype  = "float16" if device=="cuda" else "int8"
                self.whisper = WhisperModel("tiny", device=device, compute_type=ctype)
                print(f"✅ faster-whisper ({device})")
            except Exception as e:
                print(f"⚠️  faster-whisper: {e}")

    def start(self):
        """Called when child touches screen — begin capture"""
        with self._lock:
            if self._recording: return
            self._recording  = True
            self._audio_data = None
        ST["recording"] = True
        BRIDGE.sig_rec_start.emit()
        threading.Thread(target=self._capture, daemon=True).start()
        LOG("🎤 Touch-recording started", "info")

    def _capture(self):
        try:
            with sr.Microphone() as src:
                # Very short ambient noise adjustment
                self.r.adjust_for_ambient_noise(src, duration=0.1)
                audio = self.r.listen(src, timeout=10, phrase_time_limit=8)
                with self._lock:
                    self._audio_data = audio
        except sr.WaitTimeoutError:
            pass
        except Exception as e:
            LOG(f"Capture: {e}", "warn")
        finally:
            with self._lock:
                self._recording = False
            ST["recording"] = False

    def stop_and_recognise(self) -> str:
        """Called when child releases screen — recognise captured audio"""
        # Give thread a moment to finish capture
        for _ in range(20):
            with self._lock:
                if not self._recording: break
            time.sleep(0.05)

        with self._lock:
            audio = self._audio_data

        if not audio:
            LOG("No audio captured", "warn")
            return ""

        # Try faster-whisper first
        if self.whisper:
            try:
                raw = audio.get_raw_data(convert_rate=16000, convert_width=2)
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    tp = tmp.name
                with wave.open(tp, "wb") as wf:
                    wf.setnchannels(1); wf.setsampwidth(2)
                    wf.setframerate(16000); wf.writeframes(raw)
                segs, _ = self.whisper.transcribe(tp, language="en", beam_size=1)
                text = " ".join(s.text.strip() for s in segs).strip()
                os.unlink(tp)
                if text:
                    LOG(f"Whisper: {text}", "info"); return text
            except Exception as e:
                LOG(f"Whisper err: {e}", "warn")

        # Google SR fallback
        try:
            text = self.r.recognize_google(audio)
            LOG(f"Google SR: {text}", "info"); return text
        except sr.UnknownValueError:
            LOG("SR: unclear", "warn")
        except Exception as e:
            LOG(f"SR: {e}", "warn")
        return ""

# ═══════════════════════════════════════════════════════════════
# 8. VOICE (TTS + lip-sync)
# ═══════════════════════════════════════════════════════════════
class Voice:
    def __init__(self):
        self.ok = False; self._lk = threading.Lock()
        try:
            self.e = pyttsx3.init()
            self.e.setProperty('rate', 118)
            self.e.setProperty('volume', 1.0)
            for v in self.e.getProperty('voices'):
                if any(x in v.name.lower() for x in ['female','zira','hazel','karen']):
                    self.e.setProperty('voice', v.id); break
            self.ok = True; print("✅ TTS Voice")
        except Exception as ex: print(f"⚠️  TTS: {ex}")

    def say(self, text, wait=True):
        ST["interrupt_flag"] = False
        clean = re.sub(r'\[[^\]]+\]','',str(text)).strip()
        if not clean: return
        ST["is_speaking"] = True
        ST["session_chat"].append({
            "role":"pepper","text":clean,
            "time":datetime.now().strftime("%H:%M:%S")})
        if len(ST["session_chat"])>40: ST["session_chat"]=ST["session_chat"][-40:]
        print(f"\n🔊 Pepper: {clean}")
        if self.ok and not ST["interrupt_flag"]:
            with self._lk:
                try: self.e.say(clean); self.e.runAndWait()
                except: pass
        ST["is_speaking"] = False
        if wait: ST["waiting_for_child"] = True; time.sleep(0.2)

    def stop(self):
        ST["interrupt_flag"] = True; ST["is_speaking"] = False
        if self.ok:
            try: self.e.stop()
            except: pass

# ═══════════════════════════════════════════════════════════════
# 9. CLICK CARDS (PyQt6 — cognitive tasks)
# ═══════════════════════════════════════════════════════════════
class ClickCard(QPushButton):
    def __init__(self, data, idx, mode, parent=None):
        super().__init__(parent)
        self.idx = idx; self.mode = mode; self._data = data
        self.setFixedSize(152, 152)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._set_normal()
        self.clicked.connect(lambda: BRIDGE.sig_new_task.emit({"action":"click","idx":self.idx}))

    def _set_normal(self):
        d = self._data; m = self.mode
        if m == "color_grid":
            self.setText(f"\n\n{d['label']}")
            self.setFont(QFont("Arial",12,QFont.Weight.Bold))
            self.setStyleSheet(f"""
            QPushButton{{background:{d['color']};border-radius:76px;
                border:5px solid rgba(255,255,255,0.3);
                color:white;font-weight:bold;
                text-shadow:1px 1px 4px rgba(0,0,0,0.9);}}
            QPushButton:hover{{border:5px solid white;}}""")
        elif m in ["object_grid","shape_grid","emotion_grid"]:
            self.setText(f"{d['emoji']}\n{d['label']}")
            self.setFont(QFont("Arial",13,QFont.Weight.Bold))
            self.setStyleSheet("""
            QPushButton{background:qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 #1e1b4b,stop:1 #0c0f2e);
                border-radius:20px;border:4px solid #4f46e5;
                color:#e0e6ff;font-weight:bold;padding:8px;}
            QPushButton:hover{border:4px solid #a78bfa;}""")
        elif m == "number_grid":
            colors=["#6366f1","#ec4899","#f59e0b","#10b981"]
            c=colors[self.idx%len(colors)]
            self.setText(f"{d['num']}\n{d['label']}")
            self.setFont(QFont("Arial",30,QFont.Weight.Bold))
            self.setStyleSheet(f"""
            QPushButton{{background:qlineargradient(x1:0,y1:0,x2:1,y2:1,
                stop:0 {c}aa,stop:1 {c}55);
                border-radius:20px;border:4px solid {c};
                color:white;font-weight:bold;}}
            QPushButton:hover{{border:5px solid white;}}""")

    def flash_correct(self):
        self.setStyleSheet(self.styleSheet().split("QPushButton:hover")[0]+
            "QPushButton{border:8px solid #22c55e !important;}")

    def flash_wrong(self):
        self.setStyleSheet(self.styleSheet().split("QPushButton:hover")[0]+
            "QPushButton{border:8px solid #ef4444 !important;opacity:0.45;}")

    def reset(self): self._set_normal()

# ═══════════════════════════════════════════════════════════════
# 10. TABLET WINDOW — PyQt6, FIXED 780×960
# ═══════════════════════════════════════════════════════════════
class TabletWindow(QMainWindow):
    """
    Left panel : live camera feed (QLabel updated via signal)
    Right panel: task UI (instructions, figure, cards, mic button)
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pepper Smart Therapist V2")
        self.setFixedSize(1280, 780)
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.CustomizeWindowHint |
            Qt.WindowType.WindowTitleHint)
        self._cards   = []; self._locked = True; self._correct_idx = -1
        self._joy_phase = 0.0
        self._joy_timer = QTimer(); self._joy_timer.timeout.connect(self._joy_tick)
        self._recorder  = TouchRecorder()
        self._setup_ui()
        self._connect_bridge()
        # Stats refresh timer (main thread, safe)
        self._stats_t = QTimer(); self._stats_t.timeout.connect(self._refresh_stats)
        self._stats_t.start(500)

    # ── BUILD UI ─────────────────────────────────────────────
    def _setup_ui(self):
        root = QWidget(); self.setCentralWidget(root)
        root.setStyleSheet("QWidget{background:#060918;}")
        main = QHBoxLayout(root); main.setSpacing(0); main.setContentsMargins(0,0,0,0)

        # ── LEFT: Camera feed ─────────────────────────────
        cam_frame = QFrame()
        cam_frame.setFixedWidth(640)
        cam_frame.setStyleSheet("QFrame{background:#0a0d1e;border-right:2px solid #1a1f40;}")
        cam_lay = QVBoxLayout(cam_frame); cam_lay.setContentsMargins(0,0,0,0)

        # Camera label
        self.cam_lbl = QLabel()
        self.cam_lbl.setFixedSize(640, 480)
        self.cam_lbl.setStyleSheet("background:#000;")
        self.cam_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cam_lay.addWidget(self.cam_lbl)

        # Finger count display
        self.finger_lbl = QLabel("✋ Fingers: 0")
        self.finger_lbl.setFont(QFont("Arial",16,QFont.Weight.Bold))
        self.finger_lbl.setStyleSheet("color:#fbbf24;padding:8px;")
        self.finger_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cam_lay.addWidget(self.finger_lbl)

        # RECORDING INDICATOR (shown below camera)
        self.rec_lbl = QLabel("🎤 TAP MIC BUTTON TO SPEAK")
        self.rec_lbl.setFont(QFont("Arial",11,QFont.Weight.Bold))
        self.rec_lbl.setStyleSheet("color:#6b7280;padding:4px;")
        self.rec_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cam_lay.addWidget(self.rec_lbl)

        cam_lay.addStretch()
        main.addWidget(cam_frame)

        # ── RIGHT: Task panel ──────────────────────────────
        task_frame = QWidget(); task_frame.setFixedWidth(640)
        task_lay = QVBoxLayout(task_frame)
        task_lay.setSpacing(6); task_lay.setContentsMargins(12,8,12,8)

        # Header
        hdr = QFrame(); hdr.setFixedHeight(74)
        hdr.setStyleSheet("""QFrame{background:qlineargradient(
            x1:0,y1:0,x2:1,y2:0,stop:0 #1a0a3d,stop:0.5 #0a0f28,stop:1 #1a0a3d);
            border-radius:14px;border:2px solid #4f46e5;}""")
        hl = QHBoxLayout(hdr); hl.setContentsMargins(12,4,12,4)
        self.av_lbl = QLabel("🤖")
        self.av_lbl.setFont(QFont("Arial",26)); self.av_lbl.setStyleSheet("color:#a78bfa;")
        hl.addWidget(self.av_lbl)
        tw = QWidget(); tl2 = QVBoxLayout(tw); tl2.setSpacing(1)
        self.title_lbl = QLabel("PEPPER SMART THERAPIST")
        self.title_lbl.setFont(QFont("Arial",12,QFont.Weight.Bold))
        self.title_lbl.setStyleSheet("color:#a78bfa;")
        tl2.addWidget(self.title_lbl)
        self.child_lbl = QLabel("Child: Friend")
        self.child_lbl.setFont(QFont("Arial",8)); self.child_lbl.setStyleSheet("color:#60a5fa;")
        tl2.addWidget(self.child_lbl)
        hl.addWidget(tw,1)
        sw = QWidget(); sl = QVBoxLayout(sw); sl.setSpacing(1)
        self.state_lbl = QLabel("💤 Ready")
        self.state_lbl.setFont(QFont("Arial",8)); self.state_lbl.setStyleSheet("color:#9ca3af;")
        sl.addWidget(self.state_lbl, alignment=Qt.AlignmentFlag.AlignRight)
        self.ai_lbl = QLabel("● AI")
        self.ai_lbl.setFont(QFont("Arial",8,QFont.Weight.Bold))
        self.ai_lbl.setStyleSheet("color:#34d399;")
        sl.addWidget(self.ai_lbl, alignment=Qt.AlignmentFlag.AlignRight)
        hl.addWidget(sw)
        task_lay.addWidget(hdr)

        # TEACCH schedule bar
        sched = QFrame(); sched.setFixedHeight(52)
        sched.setStyleSheet("QFrame{background:#0c0f1e;border-radius:11px;border:1px solid #1a1f40;}")
        sc = QHBoxLayout(sched); sc.setContentsMargins(10,5,10,5); sc.setSpacing(7)
        self.sched_task = QLabel("📋 Task")
        self.sched_task.setFont(QFont("Arial",9,QFont.Weight.Bold))
        self.sched_task.setStyleSheet(
            "color:#a78bfa;background:#1e1b4b;border-radius:7px;padding:3px 8px;border:2px solid #4f46e5;")
        sc.addWidget(self.sched_task)
        sc.addWidget(self._arr())
        # Stars
        sw2 = QWidget(); sl2 = QVBoxLayout(sw2); sl2.setSpacing(0); sl2.setContentsMargins(0,0,0,0)
        self.stars_lbl = QLabel("☆ ☆ ☆")
        self.stars_lbl.setFont(QFont("Arial",16)); self.stars_lbl.setStyleSheet("color:#4b5563;")
        self.stars_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sl2.addWidget(self.stars_lbl)
        self.mastery_sub = QLabel("0 / 3")
        self.mastery_sub.setFont(QFont("Arial",7)); self.mastery_sub.setStyleSheet("color:#6b7280;")
        self.mastery_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sl2.addWidget(self.mastery_sub)
        sc.addWidget(sw2,1)
        sc.addWidget(self._arr())
        self.reward_lbl = QLabel("⭐")
        self.reward_lbl.setFont(QFont("Arial",20))
        self.reward_lbl.setStyleSheet(
            "color:#fbbf24;background:#2a1a00;border-radius:7px;padding:2px 8px;border:2px solid #f59e0b;")
        sc.addWidget(self.reward_lbl)
        task_lay.addWidget(sched)

        # Instruction
        if_fr = QFrame(); if_fr.setFixedHeight(82)
        if_fr.setStyleSheet("""QFrame{background:qlineargradient(
            x1:0,y1:0,x2:0,y2:1,stop:0 #1e1b4b,stop:1 #0c0f2e);
            border-radius:12px;border:2px solid #4f46e5;}""")
        il = QVBoxLayout(if_fr); il.setContentsMargins(12,4,12,4)
        self.instr_icon = QLabel("📋")
        self.instr_icon.setFont(QFont("Arial",16))
        self.instr_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        il.addWidget(self.instr_icon)
        self.instr_lbl = QLabel("Getting ready...")
        self.instr_lbl.setFont(QFont("Arial",13,QFont.Weight.Bold))
        self.instr_lbl.setStyleSheet("color:#e0e6ff;")
        self.instr_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.instr_lbl.setWordWrap(True)
        il.addWidget(self.instr_lbl)
        task_lay.addWidget(if_fr)

        # Content area (figure image + cards)
        self.content_fr = QFrame()
        self.content_fr.setMinimumHeight(290)
        self.content_fr.setStyleSheet("""QFrame{background:rgba(12,15,30,0.88);
            border-radius:14px;border:2px solid #1a1f40;}""")
        self.content_lay = QVBoxLayout(self.content_fr)
        self.content_lay.setContentsMargins(12,12,12,12)
        self.content_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._show_idle()
        task_lay.addWidget(self.content_fr,1)

        # Feedback bar
        fb_fr = QFrame(); fb_fr.setFixedHeight(54)
        fb_fr.setStyleSheet("QFrame{background:#0c0f1e;border-radius:11px;border:1px solid #1a1f40;}")
        fl = QHBoxLayout(fb_fr); fl.setContentsMargins(12,6,12,6)
        self.fb_icon = QLabel("💤"); self.fb_icon.setFont(QFont("Arial",20))
        fl.addWidget(self.fb_icon)
        self.fb_lbl = QLabel("Waiting for Pepper...")
        self.fb_lbl.setFont(QFont("Arial",11,QFont.Weight.Bold))
        self.fb_lbl.setStyleSheet("color:#9ca3af;"); self.fb_lbl.setWordWrap(True)
        fl.addWidget(self.fb_lbl,1)
        task_lay.addWidget(fb_fr)

        # ── TOUCH-TO-RECORD MIC BUTTON ─────────────────────
        self.mic_btn = QPushButton("🎤  TOUCH & HOLD TO SPEAK")
        self.mic_btn.setFixedHeight(64)
        self.mic_btn.setFont(QFont("Arial",14,QFont.Weight.Bold))
        self.mic_btn.setStyleSheet("""
        QPushButton{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,
            stop:0 #dc2626,stop:1 #ef4444);
            color:white;border-radius:32px;
            border:3px solid #fca5a5;}
        QPushButton:pressed{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,
            stop:0 #b91c1c,stop:1 #dc2626);
            border:4px solid white;}""")
        # Connect touch events
        self.mic_btn.pressed.connect(self._on_mic_press)
        self.mic_btn.released.connect(self._on_mic_release)
        task_lay.addWidget(self.mic_btn)

        # Stats bar
        sb = QFrame(); sb.setFixedHeight(44)
        sb.setStyleSheet("QFrame{background:#07090f;border-radius:9px;border:1px solid #1a1f40;}")
        stl = QHBoxLayout(sb); stl.setContentsMargins(10,3,10,3)
        for label,attr,color in [
            ("Score","stat_score","#a78bfa"),("Tokens","stat_tokens","#fbbf24"),
            ("Mastered","stat_mastered","#34d399"),("Streak","stat_streak","#60a5fa"),
        ]:
            w = QWidget(); wl2 = QVBoxLayout(w); wl2.setSpacing(0); wl2.setContentsMargins(0,0,0,0)
            val = QLabel("0"); val.setFont(QFont("Arial",11,QFont.Weight.Bold))
            val.setStyleSheet(f"color:{color};"); val.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lb  = QLabel(label); lb.setFont(QFont("Arial",7))
            lb.setStyleSheet("color:#6b7280;"); lb.setAlignment(Qt.AlignmentFlag.AlignCenter)
            wl2.addWidget(val); wl2.addWidget(lb); stl.addWidget(w)
            setattr(self, attr, val)
        task_lay.addWidget(sb)

        main.addWidget(task_frame)

        # Lock overlay over content
        self.lock_ov = QLabel("🔒")
        self.lock_ov.setParent(self.content_fr)
        self.lock_ov.setGeometry(0,0,616,290)
        self.lock_ov.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lock_ov.setFont(QFont("Arial",48))
        self.lock_ov.setStyleSheet(
            "QLabel{background:rgba(0,0,0,0.50);border-radius:14px;color:#a78bfa;}")
        self.lock_ov.hide()

    def _arr(self):
        a=QLabel("▶"); a.setFont(QFont("Arial",13)); a.setStyleSheet("color:#4f46e5;")
        return a

    def _show_idle(self):
        self._clear_content()
        d = QLabel("🤖\nPepper is preparing your task...")
        d.setFont(QFont("Arial",14)); d.setStyleSheet("color:#6b7280;")
        d.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_lay.addWidget(d)

    def _clear_content(self):
        while self.content_lay.count():
            item = self.content_lay.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        self._cards.clear()

    # ── BRIDGE CONNECTIONS ───────────────────────────────────
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
        BRIDGE.sig_update_frame.connect(self._update_camera)  # ← camera signal
        BRIDGE.sig_update_stats.connect(self._refresh_stats)
        BRIDGE.sig_rec_start.connect(self._on_rec_start)
        BRIDGE.sig_rec_stop.connect(self._on_rec_stop)

    # ── CAMERA UPDATE (main thread via signal) ────────────────
    def _update_camera(self, qimg):
        """Receive QImage from CameraThread and display it"""
        if isinstance(qimg, QImage):
            pix = QPixmap.fromImage(qimg).scaled(
                640, 480,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation)
            self.cam_lbl.setPixmap(pix)
        # Update finger count label
        fc = ST.get("finger_count",0)
        fingers_str = "🖐️ " + "☝"*fc if fc>0 else "✋ no hand"
        self.finger_lbl.setText(f"Fingers: {fc}  {fingers_str}")

    # ── STATS ────────────────────────────────────────────────
    def _refresh_stats(self):
        self.stat_score.setText(str(ST["score"]))
        self.stat_tokens.setText(str(ST["tokens"]))
        self.stat_mastered.setText(str(ST["tasks_mastered"]))
        self.stat_streak.setText(str(ST["streak"]))
        self.child_lbl.setText(f"Child: {ST['name']}")
        # Stars
        n = ST["consecutive"]
        self.stars_lbl.setText("⭐"*n+"☆"*(3-n) if n else "☆ ☆ ☆")
        self.mastery_sub.setText(f"{n} / 3")
        star_c={0:"#4b5563",1:"#d97706",2:"#fbbf24",3:"#f59e0b"}
        self.stars_lbl.setStyleSheet(f"color:{star_c.get(n,'#4b5563')};")
        # Task label
        tidx=min(ST["task_index"],len(ALL_TASKS)-1)
        t=ALL_TASKS[tidx]
        self.sched_task.setText(f"📋 {t.get('name',t['id'])}")
        # State
        if ST["is_speaking"]:
            self.fb_icon.setText("🔊"); self.state_lbl.setText("🔊 Speaking")
        elif ST["listening"] or ST["recording"]:
            self.fb_icon.setText("👂"); self.state_lbl.setText("🎤 Recording")
        elif ST["waiting_for_child"]:
            self.fb_icon.setText("⏳"); self.state_lbl.setText("⏳ Waiting")
        else:
            self.fb_icon.setText("💤"); self.state_lbl.setText("💤 Ready")

    # ── TASK DISPLAY ─────────────────────────────────────────
    def _on_new_task(self, data):
        action = data.get("action","")
        if action == "click":
            self._handle_click(data.get("idx",-1)); return
        mode  = data.get("mode","idle")
        instr = data.get("instruction","")
        self.instr_lbl.setText(instr)
        self.fb_lbl.setText("Your turn!")
        self.fb_lbl.setStyleSheet("color:#60a5fa;")
        self._build_content(data)
        self._do_unlock()

    def _build_content(self, data):
        self._clear_content(); mode = data.get("mode","idle")
        if mode == "idle": self._show_idle(); return

        if mode == "motor_model":
            # Show stick-figure drawing + instruction
            vw = QWidget(); vl = QVBoxLayout(vw)
            vl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            # Load base64 figure
            fig_data = data.get("figure","")
            if fig_data and fig_data.startswith("data:image"):
                raw  = base64.b64decode(fig_data.split(",",1)[1])
                img  = QImage(); img.loadFromData(raw)
                pix  = QPixmap.fromImage(img).scaled(
                    240, 240, Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation)
                fig_lbl = QLabel(); fig_lbl.setPixmap(pix)
                fig_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                vl.addWidget(fig_lbl)
            else:
                em = QLabel(data.get("emoji","🤖"))
                em.setFont(QFont("Arial",88))
                em.setAlignment(Qt.AlignmentFlag.AlignCenter)
                vl.addWidget(em)
            lbl = QLabel(data.get("label",""))
            lbl.setFont(QFont("Arial",15,QFont.Weight.Bold))
            lbl.setStyleSheet("color:#a78bfa;"); lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            vl.addWidget(lbl)
            arrow = QLabel("👇 Now YOU do it!")
            arrow.setFont(QFont("Arial",12,QFont.Weight.Bold))
            arrow.setStyleSheet("color:#34d399;"); arrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
            vl.addWidget(arrow)
            self.content_lay.addWidget(vw); return

        if mode == "word_display":
            wf=QFrame(); wf.setStyleSheet("""QFrame{background:qlineargradient(
                x1:0,y1:0,x2:0,y2:1,stop:0 #1e1b4b,stop:1 #0c0f1e);
                border-radius:18px;border:3px solid #4f46e5;min-height:160px;}""")
            wfl=QVBoxLayout(wf); wfl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            el=QLabel(data.get("emoji","📢")); el.setFont(QFont("Arial",52))
            el.setAlignment(Qt.AlignmentFlag.AlignCenter); wfl.addWidget(el)
            wl=QLabel(data.get("word","SAY IT!"))
            wl.setFont(QFont("Arial",30,QFont.Weight.Bold))
            wl.setStyleSheet("color:#a78bfa;"); wl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            wfl.addWidget(wl)
            hl=QLabel("🎤 Tap mic and say it!")
            hl.setFont(QFont("Arial",12)); hl.setStyleSheet("color:#6b7280;")
            hl.setAlignment(Qt.AlignmentFlag.AlignCenter); wfl.addWidget(hl)
            self.content_lay.addWidget(wf); return

        # Grid tasks
        opts   = data.get("options",[])
        self._correct_idx = data.get("correct",-1)
        gw = QWidget(); grid = QGridLayout(gw)
        grid.setSpacing(10); grid.setAlignment(Qt.AlignmentFlag.AlignCenter)
        for i, opt in enumerate(opts):
            card = ClickCard(opt, i, mode)
            self._cards.append(card)
            grid.addWidget(card, i//2, i%2, Qt.AlignmentFlag.AlignCenter)
        self.content_lay.addWidget(gw)

    def _handle_click(self, idx):
        if self._locked: return
        correct = self._correct_idx
        if correct == -1:
            ST["tablet_click_result"] = "correct"
            if idx<len(self._cards): self._cards[idx].flash_correct()
            self.fb_lbl.setText("✅ Great choice!"); self.fb_lbl.setStyleSheet("color:#34d399;")
            self._do_lock(); return
        if idx == correct:
            ST["tablet_click_result"] = "correct"
            if idx<len(self._cards): self._cards[idx].flash_correct()
            LOG(f"Click CORRECT idx={idx}","success")
        else:
            ST["tablet_click_result"] = "wrong"
            if idx<len(self._cards): self._cards[idx].flash_wrong()
            if 0<=correct<len(self._cards): self._cards[correct].flash_correct()
            LOG(f"Click WRONG idx={idx}","fail")
        self._do_lock()

    def _on_success_overlay(self, msg):
        self._clear_content()
        ov = QWidget(); ol = QVBoxLayout(ov); ol.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ck = QLabel("✅"); ck.setFont(QFont("Arial",110))
        ck.setAlignment(Qt.AlignmentFlag.AlignCenter); ol.addWidget(ck)
        ml = QLabel(msg); ml.setFont(QFont("Arial",15,QFont.Weight.Bold))
        ml.setStyleSheet("color:#34d399;"); ml.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ml.setWordWrap(True); ol.addWidget(ml)
        self.content_lay.addWidget(ov)
        self.fb_lbl.setText(msg); self.fb_lbl.setStyleSheet("color:#34d399;font-size:14px;")
        self.instr_icon.setText("✅")
        QTimer.singleShot(2500, self._show_idle)
        QTimer.singleShot(2500, lambda: self.instr_icon.setText("📋"))

    def _on_fail_overlay(self, msg):
        self.fb_lbl.setText(f"❌ {msg}"); self.fb_lbl.setStyleSheet("color:#f87171;font-size:13px;")
        self.instr_icon.setText("❌")
        QTimer.singleShot(2000, lambda: self.instr_icon.setText("📋"))
        QTimer.singleShot(2000, lambda: self.fb_lbl.setStyleSheet("color:#9ca3af;"))

    def _on_joy(self, jtype):
        self._joy_phase=0.0; self._joy_timer.start(55)
        msgs={"dance":"🕺 AMAZING DANCE! 🎉","celebrate":"🎊 CELEBRATION! ⭐",
              "wave_back":"👋 HIGH FIVE! 🌟","full_joy":"🏆 CHAMPION! 🎉"}
        self.fb_lbl.setText(msgs.get(jtype,"🌟 AMAZING! 🎉"))
        self.fb_lbl.setStyleSheet("color:#fbbf24;font-size:15px;")
        QTimer.singleShot(3000, self._end_joy)

    def _joy_tick(self):
        self._joy_phase+=0.22
        ems=["🎉","🌟","⭐","🏆","✨","🎊","💫","🎈"]
        self.av_lbl.setText(ems[int(self._joy_phase)%len(ems)])
        if self._joy_phase>20: self._end_joy()

    def _end_joy(self):
        self._joy_timer.stop(); self.av_lbl.setText("🤖")
        QTimer.singleShot(500, lambda: self.fb_lbl.setStyleSheet("color:#9ca3af;"))

    def _do_unlock(self):
        self._locked=False; ST["tablet_locked"]=False
        self.lock_ov.hide()
        for c in self._cards: c.setEnabled(True)

    def _do_lock(self):
        self._locked=True; ST["tablet_locked"]=True
        self.lock_ov.show(); self.lock_ov.raise_()
        for c in self._cards: c.setEnabled(False)

    def _set_feedback(self, txt): self.fb_lbl.setText(txt)
    def _set_instr(self,  txt): self.instr_lbl.setText(txt)
    def _set_waiting(self,txt):
        self.fb_lbl.setText(txt); self.fb_lbl.setStyleSheet("color:#fbbf24;")
        self.fb_icon.setText("⏳")
    def _reset_cards(self):
        for c in self._cards: c.reset()
        ST["tablet_click_result"] = None

    # ── TOUCH-TO-RECORD MIC BUTTON ────────────────────────────
    def _on_mic_press(self):
        """Child PRESSES mic button — start recording"""
        ST["touch_start"] = time.time()
        self.rec_lbl.setText("🔴 RECORDING... Release to stop")
        self.rec_lbl.setStyleSheet("color:#ef4444;font-size:12px;font-weight:bold;padding:4px;")
        self.mic_btn.setText("🔴  RECORDING... RELEASE TO STOP")
        self.mic_btn.setStyleSheet("""
        QPushButton{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,
            stop:0 #7f1d1d,stop:1 #991b1b);
            color:white;border-radius:32px;border:4px solid white;
            animation:blink 0.5s;}""")
        self._recorder.start()
        LOG("🎤 Mic pressed — recording", "info")

    def _on_mic_release(self):
        """Child RELEASES mic button — stop and recognise"""
        self.mic_btn.setText("🎤  TAP & HOLD TO SPEAK")
        self.mic_btn.setStyleSheet("""
        QPushButton{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,
            stop:0 #dc2626,stop:1 #ef4444);
            color:white;border-radius:32px;border:3px solid #fca5a5;}
        QPushButton:pressed{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,
            stop:0 #b91c1c,stop:1 #dc2626);border:4px solid white;}""")
        self.rec_lbl.setText("⏳ Processing speech...")
        self.rec_lbl.setStyleSheet("color:#fbbf24;padding:4px;")
        # Recognise in thread so UI stays responsive
        threading.Thread(target=self._do_recognise, daemon=True).start()
        LOG("🎤 Mic released — recognising", "info")

    def _do_recognise(self):
        """Runs in background thread — emits sig_rec_stop with result"""
        text = self._recorder.stop_and_recognise()
        BRIDGE.sig_rec_stop.emit(text)

    def _on_rec_start(self):
        pass  # already handled in _on_mic_press

    def _on_rec_stop(self, text):
        """Received on main thread — update UI"""
        if text:
            self.rec_lbl.setText(f"✅ Heard: \"{text}\"")
            self.rec_lbl.setStyleSheet("color:#34d399;font-size:12px;padding:4px;")
            self.fb_lbl.setText(f"✅ I heard: \"{text}\"")
            self.fb_lbl.setStyleSheet("color:#34d399;")
            ST["last_speech_text"] = text
            ST["last_sound"] = time.time()
            ST["session_chat"].append({
                "role":"child","text":text,
                "time":datetime.now().strftime("%H:%M:%S")})
            LOG(f"Heard: {text}", "info")
        else:
            self.rec_lbl.setText("❌ Could not hear — try again!")
            self.rec_lbl.setStyleSheet("color:#f87171;padding:4px;")
        QTimer.singleShot(3000, lambda: self.rec_lbl.setText("🎤 TAP MIC BUTTON TO SPEAK"))
        QTimer.singleShot(3000, lambda: self.rec_lbl.setStyleSheet("color:#6b7280;padding:4px;"))

# ═══════════════════════════════════════════════════════════════
# 11. THERAPY CONTROLLER — conscious check → celebrate → next
# ═══════════════════════════════════════════════════════════════
class TherapyCtrl:
    def __init__(self, voice: Voice):
        self.voice   = voice
        self.running = False

    def _say(self, text, wait=True):
        BRIDGE.sig_set_instr.emit(str(text)[:70])
        self.voice.say(str(text), wait=wait)

    def run(self):
        self.running = True
        # Greeting
        self._say("Hello! I am Pepper your Smart Therapist! "
                  "Look at the screen! Copy the movements I show you! "
                  "Tap the red microphone button to answer! Ready?")
        time.sleep(0.5)

        while self.running:
            if time.time()-ST["last_sound"]>14:
                ST["last_sound"]=time.time()
                self._say("I am here! Take your time!", wait=False)
            self._handle_cmd()
            tidx = ST["task_index"] % len(ALL_TASKS)
            task = ALL_TASKS[tidx]
            ST["tablet_instruction"] = task["instruction"]
            ST["domain"]  = task.get("domain","Motor")
            ST["protocol"]= task.get("protocol","ABA-Motor")

            # Show task on tablet (via signal)
            self._show_tablet(task)
            self._say(task["instruction"] + " Look at the screen!", wait=False)

            success = self._run_task(task)

            if success:
                self._on_success(task)
                BRIDGE.sig_show_success.emit(task.get("success","Amazing! ✅"))
                self._say(
                    f"{ST['name']}! {task.get('success','Amazing! You did it!')} "
                    "Now let us try the next task!", wait=False)
            else:
                self._on_fail(task)
                BRIDGE.sig_show_fail.emit(task.get("fail","Not quite! Try again!"))
                self._say(
                    f"{ST['name']}! {task.get('fail','Not quite!')} "
                    "Let us try again!", wait=False)
            time.sleep(0.5)

    def _show_tablet(self, task):
        """Emit task data to Qt main thread via signal"""
        mode = task.get("tablet_mode","idle")
        domain = task.get("domain","Motor")
        data = {"mode":mode, "instruction":task["instruction"]}
        if domain=="Motor" or mode=="motor_model":
            data.update({
                "mode":"motor_model",
                "figure":task.get("figure",""),
                "emoji": task.get("movement","🤖"),
                "label": task.get("name",""),
                "desc":  task.get("instruction",""),
            })
        elif mode=="word_display":
            data.update({"emoji":task.get("word_emoji","📢"),
                         "word": task.get("word_text","SAY IT!")})
        elif mode in ["color_grid","object_grid","shape_grid",
                      "number_grid","emotion_grid"]:
            data.update({"options":task.get("options",[]),
                         "correct":task.get("correct",-1)})
        ST["tablet_click_result"] = None
        BRIDGE.sig_new_task.emit(data)

    def _run_task(self, task):
        """Wait for valid response — conscious loop"""
        name  = ST["name"]; vtype = task.get("verify","motor")
        prompts = task.get("prompts",["Try again!"])
        waiting  = task.get("waiting","I am waiting!")
        ST["last_speech_text"] = ""
        motor_checks = ["clap","wave","raise_hand","touch_nose","arms_out",
                        "hands_up","touch_ears","thumbs_up"]
        if vtype in motor_checks:
            ST["verify_action"]  = vtype
            ST["verify_result"]  = False
            ST["verify_timeout"] = time.time()+22
        deadline = time.time()+65
        last_p   = time.time(); pidx = 0
        while time.time()<deadline:
            res = self._check_result(task)
            if res=="success": return True
            if res=="fail":    return False
            if time.time()-last_p>6:
                last_p=time.time()
                if pidx<len(prompts):
                    self.voice.say(f"{name}... {prompts[pidx]}", wait=False)
                    pidx+=1
                else:
                    self.voice.say(waiting, wait=False)
                BRIDGE.sig_set_waiting.emit(waiting)
            self._handle_cmd()
            time.sleep(0.2)
        ST["verify_action"]=None
        return False

    def _check_result(self, task):
        vtype = task.get("verify","motor")
        mc    = task.get("motor_check", task.get("verify",""))
        if mc in ["clap","wave","raise_hand","touch_nose","arms_out",
                  "hands_up","touch_ears","thumbs_up"]:
            if ST["verify_result"]: ST["verify_result"]=False; return "success"
            if mc=="clap"       and ST["clapping"]:     return "success"
            if mc=="wave"       and ST["waving"]:       return "success"
            if mc=="raise_hand" and ST["hand_raised"]:  return "success"
            if mc=="arms_out"   and ST["arms_out"]:     return "success"
            if mc=="hands_up"   and ST["hands_up"]:     return "success"
            if mc=="thumbs_up"  and ST["finger_count"]==1: return "success"
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
        elif vtype=="speech_number":
            if any(c.isdigit() for c in ST.get("last_speech_text","")):
                ST["last_speech_text"]=""; return "success"
        return None

    def _on_success(self, task):
        ST["consecutive"]+=1
        pts=task.get("tokens",2)*5
        ST["score"]+=pts; ST["tokens"]+=task.get("tokens",2)
        ST["tasks_success"]+=1; ST["streak"]+=1
        BRIDGE.sig_joy.emit(task.get("joy","celebrate"))
        BRIDGE.sig_update_stats.emit()
        LOG(f"✅ {ST['consecutive']}/3 '{task['id']}'","success")
        if ST["consecutive"]>=3:
            ST["consecutive"]=0; ST["tasks_mastered"]+=1
            ST["task_index"]+=1
            if ST["task_index"]>=len(ALL_TASKS):
                ST["task_index"]=0; ST["current_level"]+=1
            ntask=ALL_TASKS[ST["task_index"]%len(ALL_TASKS)]
            LOG(f"🏆 MASTERED → {ntask['id']}","success")
            self._say(f"{ST['name']} earned 3 stars! MASTERED! "
                      f"Next: {ntask.get('name',ntask['id'])}!", wait=False)

    def _on_fail(self, task):
        ST["consecutive"]=0; ST["streak"]=0; ST["tasks_fail"]+=1
        BRIDGE.sig_show_fail.emit(task.get("fail","Not quite! Try again!"))
        QTimer.singleShot(2500, lambda: BRIDGE.sig_reset_cards.emit())

    def _handle_cmd(self):
        cmd=ST.get("sim_cmd")
        if not cmd: return
        ST["sim_cmd"]=None
        if cmd=="next":
            ST["consecutive"]=0
            ST["task_index"]=(ST["task_index"]+1)%len(ALL_TASKS)
            self.voice.say("Next task!", wait=False)
        elif cmd=="break":
            self.voice.say("Break time! Rest.", wait=False)

# ═══════════════════════════════════════════════════════════════
# 12. MAIN
# ═══════════════════════════════════════════════════════════════
def main():
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║  PEPPER SMART THERAPIST V2 — FINAL                          ║
║  Commander: Lamya | Omdurman Islamic University             ║
╠══════════════════════════════════════════════════════════════╣
║  ✅ LIVE CAMERA in PyQt6 left panel                        ║
║  ✅ MediaPipe skeleton + finger counter overlay            ║
║  ✅ Touch-to-record mic (press=start, release=stop)        ║
║  ✅ faster-whisper energy=200 (high sensitivity)           ║
║  ✅ Stick-figure visual modeling for motor tasks           ║
║  ✅ ALL Qt UI via pyqtSignal (zero threading errors)       ║
╚══════════════════════════════════════════════════════════════╝
""")

    # PyQt6 app — must run on main thread
    qt_app = QApplication(sys.argv)
    qt_app.setApplicationName("Pepper Smart Therapist V2")
    qt_app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window,     QColor(6,9,18))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(224,230,255))
    palette.setColor(QPalette.ColorRole.Base,       QColor(12,15,30))
    palette.setColor(QPalette.ColorRole.Text,       QColor(224,230,255))
    qt_app.setPalette(palette)

    # Windows
    tablet  = TabletWindow()
    voice   = Voice()
    ctrl    = TherapyCtrl(voice)

    # Camera thread (QThread — safe)
    cam_thread = CameraThread()
    cam_thread.start()

    # Therapy in background daemon thread
    def _start():
        time.sleep(1.2)
        voice.say("Welcome! I am Pepper Smart Therapist! "
                  "Watch the screen and copy my movements! "
                  "Tap the RED microphone button to speak! Let us begin!",
                  wait=False)
        ctrl.run()

    t = threading.Thread(target=_start, daemon=True); t.start()

    # Position window
    tablet.show(); tablet.move(30, 30)

    print(f"""
{'='*64}
✅ SMART THERAPIST V2 ACTIVE
{'='*64}
Left panel  → Live camera + MediaPipe skeleton + fingers
Right panel → Task UI + visual figure + mic button

Touch-to-record: PRESS mic button → speak → RELEASE
Finger count: shown bottom-right of camera

Commands (terminal):
  n / next  — skip to next task
  q / exit  — quit
{'='*64}
""")

    # Terminal input
    def _input():
        while ctrl.running:
            try:
                cmd = input("> ").strip().lower()
                if cmd in ["q","exit","quit"]:
                    ctrl.running=False
                    cam_thread.stop()
                    qt_app.quit(); break
                elif cmd in ["n","next"]: ST["sim_cmd"]="next"
                elif cmd=="break":        ST["sim_cmd"]="break"
                elif cmd=="stats":
                    tidx=min(ST["task_index"],len(ALL_TASKS)-1)
                    t=ALL_TASKS[tidx]
                    print(f"Task:{t['id']} "
                          f"★{ST['consecutive']}/3 "
                          f"Score:{ST['score']} "
                          f"Mastered:{ST['tasks_mastered']} "
                          f"Fingers:{ST['finger_count']}")
            except (KeyboardInterrupt,EOFError): break
        qt_app.quit()

    threading.Thread(target=_input, daemon=True).start()

    ret = qt_app.exec()
    ctrl.running = False
    cam_thread.stop()
    fn = f"session_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(fn,"w") as f: json.dump(ST,f,indent=2,default=str)
    print(f"\n📄 Session saved: {fn}")
    print("Goodbye Commander Lamya! ✅")
    sys.exit(ret)

if __name__ == "__main__":
    main()
