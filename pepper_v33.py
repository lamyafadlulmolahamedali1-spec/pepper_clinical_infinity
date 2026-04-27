#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PEPPER CLINICAL INFINITY v3.3 — DEFINITIVE
Commander: Lamya | Omdurman Islamic University

TTS  → espeak subprocess (zero Qt conflict, Pepper always talks)
EMO  → 500×500 fixed window (cv2.WINDOW_AUTOSIZE)
LIVE → shared frame buffer (no cap sharing, no freeze)
SPEECH → queue-based, keyword-only fails
TASKS → 5000+ endless ESDM/ABA/TEACCH/DTT
"""

# ── 0. Env flags BEFORE any other import ────────────────────────────
import os, sys
os.environ.update({
    "QT_QPA_PLATFORM": "xcb",
    "QT_LOGGING_RULES": "*.debug=false",
    "QT_QPA_FONTDIR": "/usr/share/fonts",
    "OPENCV_LOG_LEVEL": "ERROR",
    "TF_CPP_MIN_LOG_LEVEL": "3",
    "PYTHONWARNINGS": "ignore",
    "CUDA_VISIBLE_DEVICES": "0",
    "TF_ENABLE_ONEDNN_OPTS": "0",
    "PULSE_LATENCY_MSEC": "30",
    "MPLBACKEND": "Agg",
    "GDK_BACKEND": "x11",
})

import ctypes, warnings, socket, time, threading, queue, subprocess
import random, math, re, csv, base64, wave, tempfile
from datetime import datetime
from io import BytesIO
from collections import deque

warnings.filterwarnings("ignore")
try:
    _a = ctypes.cdll.LoadLibrary("libasound.so.2")
    _a.snd_lib_error_set_handler(ctypes.c_void_p(None))
except: pass

# ── 1. Core imports ──────────────────────────────────────────────────
import cv2, numpy as np
from PIL import Image, ImageDraw
import mediapipe as mp
import speech_recognition as sr
from flask import Flask, jsonify, request, render_template_string
from flask_cors import CORS

# Qt — imported AFTER env flags
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QGridLayout, QLineEdit, QTextEdit,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QThread
from PyQt6.QtGui import (
    QFont, QColor, QPalette, QPixmap, QImage, QPainter, QPen,
)

try:
    from faster_whisper import WhisperModel
    WHISPER_OK = True
except: WHISPER_OK = False

try:
    import google.generativeai as genai
    GEMINI_AVAIL = True
except: GEMINI_AVAIL = False

# ── 2. Config ────────────────────────────────────────────────────────
GEMINI_KEY   = "AIzaSyDEdleVKiQ5E00wMcjMbji0G9JcYT2TvE8"
MIC_ENERGY   = 120
MASTERY_N    = 3
MAX_WRONG    = 2
TASK_TIMEOUT = 50
EMO_WIN_SIZE = 500      # emotion window exact pixel size

if GEMINI_AVAIL:
    try: genai.configure(api_key=GEMINI_KEY)
    except: GEMINI_AVAIL = False

def get_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80)); ip = s.getsockname()[0]; s.close(); return ip
    except: return "127.0.0.1"
LOCAL_IP = get_ip()

# ── 3. Child setup ───────────────────────────────────────────────────
print("\n" + "═"*56)
print("  PEPPER CLINICAL INFINITY v3.3")
print("  Omdurman Islamic University — Commander: Lamya")
print("═"*56)
CHILD_NAME = input("\n👦 Child's name: ").strip() or "Child"
CHILD_SAFE = re.sub(r"[^a-zA-Z0-9_]", "_", CHILD_NAME)
CSV_FILE   = f"{CHILD_SAFE}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
with open(CSV_FILE, "w", newline="") as f:
    csv.writer(f).writerow([
        "Time","Child","Task","Domain","Protocol","Level",
        "Result","WrongCount","Consecutive","Score",
        "Emotion","Attention","Duration_s","AutoAdvanced"])
print(f"✅ CSV: {CSV_FILE}")

def log_row(tid,dom,proto,lv,ok,wc,cons,sc,em,att,dur,auto):
    with open(CSV_FILE,"a",newline="") as f:
        csv.writer(f).writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            CHILD_NAME,tid,dom,proto,lv,
            "SUCCESS" if ok else ("AUTO" if auto else "FAIL"),
            wc,cons,sc,em,att,f"{dur:.1f}","YES" if auto else "NO"])

# ── 4. TTS — espeak subprocess (zero Qt conflict) ────────────────────
class TTS:
    """
    Speak via espeak subprocess.
    Never touches Qt, never touches pyttsx3 event loops.
    Completely thread-safe. Pepper will ALWAYS talk.
    """
    _q    = queue.Queue()
    _lock = threading.Lock()
    _proc = None

    @classmethod
    def _worker(cls):
        """Drain the queue and speak each item."""
        while True:
            text = cls._q.get()
            if text is None: break
            cls._speak_now(text)
            cls._q.task_done()

    @classmethod
    def _speak_now(cls, text):
        clean = re.sub(r"\[[^\]]+\]", "", str(text)).strip()
        if not clean: return
        ST["is_speaking"] = True
        # Start lip animation in parallel
        threading.Thread(target=cls._lip, args=(clean,), daemon=True).start()
        # Try espeak first, fall back to pyttsx3 in-thread
        spoken = False
        try:
            result = subprocess.run(
                ["espeak-ng", "-s", "120", "-v", "en-gb-x-gbclan", clean],
                capture_output=True, timeout=30)
            spoken = result.returncode == 0
        except FileNotFoundError:
            pass
        except Exception: pass
        if not spoken:
            try:
                result = subprocess.run(
                    ["espeak", "-s", "120", clean],
                    capture_output=True, timeout=30)
                spoken = result.returncode == 0
            except Exception: pass
        if not spoken:
            # Last resort: pyttsx3 in THIS thread (not Qt thread) 
            try:
                import pyttsx3 as _p
                e = _p.init()
                e.setProperty("rate", 115)
                e.say(clean)
                e.runAndWait()
                spoken = True
            except Exception as ex:
                print(f"⚠️  TTS all methods failed: {ex}")
        ST["is_speaking"] = False
        ST["lip"] = 0.0

    @classmethod
    def _lip(cls, text):
        for word in text.split():
            if not ST["is_speaking"]: break
            d = max(0.06, len(word)/14.0)
            ST["lip"] = min(1.0, 0.4 + random.uniform(0.1, 0.5))
            time.sleep(d * 0.55)
            ST["lip"] = max(0.05, ST["lip"] * 0.3)
            time.sleep(d * 0.45)
        ST["lip"] = 0.0

    @classmethod
    def say(cls, text):
        """Queue text — safe from ANY thread including Qt."""
        clean = re.sub(r"\[[^\]]+\]", "", str(text)).strip()
        if not clean: return
        ST["session_chat"].append({
            "role":"pepper","text":clean,
            "time":datetime.now().strftime("%H:%M:%S")})
        if len(ST["session_chat"]) > 100:
            ST["session_chat"] = ST["session_chat"][-100:]
        print(f"\n🔊 Pepper: {clean}")
        cls._q.put(clean)

    @classmethod
    def start(cls):
        t = threading.Thread(target=cls._worker, daemon=True, name="TTS")
        t.start()
        print("✅ TTS ready (espeak subprocess)")

    @classmethod
    def stop(cls):
        cls._q.put(None)

# Start TTS worker immediately
TTS.start()

# ── 5. Stick figures ─────────────────────────────────────────────────
def make_fig(mv, sz=260):
    img = Image.new("RGBA",(sz,sz),(240,245,255,255))
    dr  = ImageDraw.Draw(img)
    cx,cy = sz//2, sz//2+8
    lw=4; c="#2c3e50"; h="#e74c3c"
    dr.ellipse([cx-26,cy-84,cx+26,cy-32], outline=c, width=lw)
    dr.line([cx,cy-32,cx,cy+52], fill=c, width=lw)
    dr.line([cx,cy+52,cx-24,cy+98], fill=c, width=lw)
    dr.line([cx,cy+52,cx+24,cy+98], fill=c, width=lw)
    if mv=="clap":
        dr.line([cx-42,cy-2,cx-4,cy+14],fill=h,width=5)
        dr.line([cx+42,cy-2,cx+4,cy+14],fill=h,width=5)
        dr.ellipse([cx-8,cy+8,cx+8,cy+24],fill=h)
    elif mv=="wave":
        dr.line([cx-38,cy-4,cx-18,cy+12],fill=c,width=lw)
        dr.line([cx+38,cy-12,cx+62,cy-44],fill=h,width=5)
    elif mv=="raise_hand":
        dr.line([cx-38,cy-4,cx-18,cy+12],fill=c,width=lw)
        dr.line([cx+38,cy-12,cx+48,cy-70],fill=h,width=5)
        dr.ellipse([cx+40,cy-84,cx+60,cy-64],fill=h)
    elif mv=="touch_nose":
        dr.ellipse([cx-6,cy-58,cx+6,cy-46],fill=h)
        dr.line([cx-38,cy-2,cx-6,cy-52],fill=h,width=5)
        dr.line([cx+38,cy-2,cx+18,cy+12],fill=c,width=lw)
    elif mv=="arms_out":
        dr.line([cx-38,cy-4,cx-86,cy-4],fill=h,width=5)
        dr.line([cx+38,cy-4,cx+86,cy-4],fill=h,width=5)
    elif mv=="hands_up":
        dr.line([cx-38,cy-4,cx-52,cy-66],fill=h,width=5)
        dr.line([cx+38,cy-4,cx+52,cy-66],fill=h,width=5)
        dr.ellipse([cx-64,cy-80,cx-42,cy-60],fill=h)
        dr.ellipse([cx+42,cy-80,cx+64,cy-60],fill=h)
    elif mv=="jump":
        dr.line([cx-38,cy-4,cx-52,cy-44],fill=h,width=5)
        dr.line([cx+38,cy-4,cx+52,cy-44],fill=h,width=5)
        dr.line([cx,cy+52,cx-30,cy+72],fill=h,width=4)
        dr.line([cx,cy+52,cx+30,cy+72],fill=h,width=4)
    elif mv=="stomp":
        dr.line([cx,cy+52,cx+30,cy+102],fill=h,width=5)
        dr.line([cx-38,cy-4,cx-18,cy+12],fill=c,width=lw)
        dr.line([cx+38,cy-4,cx+18,cy+12],fill=c,width=lw)
    elif mv=="spin":
        dr.line([cx-42,cy-4,cx-70,cy-20],fill=h,width=5)
        dr.line([cx+42,cy-4,cx+70,cy-20],fill=h,width=5)
        for a in range(0,360,60):
            ax=cx+int(22*math.cos(math.radians(a)))-5
            ay=cy-int(22*math.sin(math.radians(a)))-5
            dr.ellipse([ax,ay,ax+10,ay+10],fill="#3498db")
    elif mv=="march":
        dr.line([cx+38,cy-4,cx+48,cy-24],fill=h,width=5)
        dr.line([cx,cy+52,cx-30,cy+80],fill=h,width=5)
    else:
        dr.line([cx-38,cy-4,cx-58,cy+10],fill=c,width=lw)
        dr.line([cx+38,cy-4,cx+58,cy+10],fill=c,width=lw)
    dr.text((cx-38,sz-28),"👇 YOUR TURN!",fill=(231,76,60,255))
    buf=BytesIO(); img.save(buf,"PNG")
    return "data:image/png;base64,"+base64.b64encode(buf.getvalue()).decode()

MOVS = ["clap","wave","raise_hand","touch_nose","arms_out",
        "hands_up","jump","stomp","spin","march"]
FIGS = {m: make_fig(m) for m in MOVS}

# ── 6. Task pools ────────────────────────────────────────────────────
_COL = [
    {"id":"red",   "color":"#ef4444","label":"🔴 RED",   "name":"Red"},
    {"id":"blue",  "color":"#3b82f6","label":"🔵 BLUE",  "name":"Blue"},
    {"id":"green", "color":"#22c55e","label":"🟢 GREEN", "name":"Green"},
    {"id":"yellow","color":"#eab308","label":"🟡 YELLOW","name":"Yellow"},
    {"id":"purple","color":"#a855f7","label":"🟣 PURPLE","name":"Purple"},
    {"id":"orange","color":"#f97316","label":"🟠 ORANGE","name":"Orange"},
    {"id":"pink",  "color":"#ec4899","label":"🩷 PINK",  "name":"Pink"},
    {"id":"brown", "color":"#92400e","label":"🟤 BROWN", "name":"Brown"},
]
_ANI = [
    {"id":"dog","emoji":"🐶","label":"Dog"},{"id":"cat","emoji":"🐱","label":"Cat"},
    {"id":"lion","emoji":"🦁","label":"Lion"},{"id":"elephant","emoji":"🐘","label":"Elephant"},
    {"id":"rabbit","emoji":"🐰","label":"Rabbit"},{"id":"bear","emoji":"🐻","label":"Bear"},
    {"id":"monkey","emoji":"🐵","label":"Monkey"},{"id":"tiger","emoji":"🐯","label":"Tiger"},
    {"id":"giraffe","emoji":"🦒","label":"Giraffe"},{"id":"penguin","emoji":"🐧","label":"Penguin"},
    {"id":"horse","emoji":"🐴","label":"Horse"},{"id":"cow","emoji":"🐮","label":"Cow"},
]
_FRT = [
    {"id":"apple","emoji":"🍎","label":"Apple"},{"id":"banana","emoji":"🍌","label":"Banana"},
    {"id":"orange","emoji":"🍊","label":"Orange"},{"id":"grapes","emoji":"🍇","label":"Grapes"},
    {"id":"strawberry","emoji":"🍓","label":"Strawberry"},
    {"id":"mango","emoji":"🥭","label":"Mango"},{"id":"cherry","emoji":"🍒","label":"Cherry"},
]
_SHP = [
    {"id":"circle","emoji":"⭕","label":"Circle"},{"id":"square","emoji":"⬛","label":"Square"},
    {"id":"triangle","emoji":"🔺","label":"Triangle"},{"id":"star","emoji":"⭐","label":"Star"},
    {"id":"heart","emoji":"❤️","label":"Heart"},{"id":"moon","emoji":"🌙","label":"Moon"},
]
_EMO = [
    {"id":"happy","emoji":"😊","label":"Happy"},{"id":"sad","emoji":"😢","label":"Sad"},
    {"id":"angry","emoji":"😠","label":"Angry"},{"id":"surprised","emoji":"😲","label":"Surprised"},
    {"id":"scared","emoji":"😨","label":"Scared"},{"id":"excited","emoji":"🤩","label":"Excited"},
]
_VEH = [
    {"id":"car","emoji":"🚗","label":"Car"},{"id":"bus","emoji":"🚌","label":"Bus"},
    {"id":"train","emoji":"🚂","label":"Train"},{"id":"airplane","emoji":"✈️","label":"Airplane"},
    {"id":"boat","emoji":"⛵","label":"Boat"},{"id":"bicycle","emoji":"🚲","label":"Bicycle"},
]
_MTR = [
    {"id":"clap","name":"👏 Clap","verify":"clap","protocol":"ABA",
     "instruction":"CLAP your hands! 👏","waiting":"Clap clap clap! 👏",
     "success":"Amazing clap! ✅","fail":"Clap your hands!"},
    {"id":"wave","name":"👋 Wave","verify":"wave","protocol":"ESDM",
     "instruction":"WAVE hello to Pepper! 👋","waiting":"Wave your hand! 👋",
     "success":"Great wave! ✅","fail":"Wave side to side!"},
    {"id":"raise_hand","name":"✋ Raise Hand","verify":"raise_hand","protocol":"DTT",
     "instruction":"RAISE your hand HIGH! ✋","waiting":"Raise your hand! ✋",
     "success":"Perfect! ✅","fail":"Lift arm above head!"},
    {"id":"touch_nose","name":"👆 Touch Nose","verify":"touch_nose","protocol":"TEACCH",
     "instruction":"TOUCH your NOSE! 👆","waiting":"Touch your nose! 👆",
     "success":"Found your nose! ✅","fail":"Point to your nose!"},
    {"id":"arms_out","name":"🤸 Arms Wide","verify":"arms_out","protocol":"ESDM",
     "instruction":"Stretch BOTH arms WIDE! 🤸","waiting":"Arms wide open! 🤸",
     "success":"Like a big bird! ✅","fail":"Spread arms to sides!"},
    {"id":"hands_up","name":"🙌 Hands Up","verify":"hands_up","protocol":"ABA",
     "instruction":"Both hands UP HIGH! 🙌","waiting":"Both hands up! 🙌",
     "success":"Superstar! ✅","fail":"Raise both arms!"},
    {"id":"jump","name":"⬆️ Jump","verify":"body_motion","protocol":"ESDM",
     "instruction":"JUMP up! Jump jump! ⬆️","waiting":"Jump! ⬆️",
     "success":"Great jump! ✅","fail":"Bend knees and jump!"},
    {"id":"stomp","name":"🦶 Stomp","verify":"body_motion","protocol":"DTT",
     "instruction":"STOMP your feet! 🦶","waiting":"Stomp stomp! 🦶",
     "success":"Loud stomper! ✅","fail":"Lift foot and stomp!"},
    {"id":"spin","name":"🌀 Spin","verify":"body_motion","protocol":"TEACCH",
     "instruction":"SPIN in a circle! 🌀","waiting":"Spin spin! 🌀",
     "success":"Great spinning! ✅","fail":"Turn your whole body!"},
    {"id":"march","name":"🪖 March","verify":"body_motion","protocol":"ESDM",
     "instruction":"MARCH! Left right! 🪖","waiting":"March march! 🪖",
     "success":"Great marching! ✅","fail":"Lift knees and march!"},
]
_WDS = ["apple","ball","cat","dog","elephant","fish","good","happy","jump",
        "kite","love","milk","no","okay","play","quiet","red","sun","tree",
        "up","very","water","yes","zero","blue","green","one","two","three",
        "four","five","six","seven","eight","nine","ten"]
_SOC = ["hello","goodbye","please","thank you","help","more","stop",
        "go","come","look","listen","sit","stand","walk","eat","drink"]

def _grid(pool, exclude_id):
    t = random.choice(pool)
    d = random.sample([x for x in pool if x["id"]!=t["id"]],3)
    opts = [t]+d; random.shuffle(opts)
    cor  = next(i for i,o in enumerate(opts) if o["id"]==t["id"])
    return t, opts, cor

def build_pool(n=5000):
    P=[]; protos=["ABA","ESDM","TEACCH","DTT"]
    # Motor 25%
    for _ in range(int(n*.25)):
        m=random.choice(_MTR)
        P.append({**m,"domain":"Motor","level":1,"tablet_mode":"motor_model",
                  "figure":FIGS.get(m["id"],""),"tokens":2,"joy":"dance"})
    # Colors 10%
    for _ in range(int(n*.10)):
        t,opts,cor=_grid(_COL,None)
        P.append({"id":f"color_{t['id']}","domain":"Cognitive","protocol":random.choice(protos),
                  "level":2,"name":f"🎨 Find {t['name']}",
                  "instruction":f"Touch the {t['name']} color!",
                  "waiting":f"Find {t['name']}! 🎨","success":f"{t['name']}! ✅",
                  "fail":f"Find {t['name']}!","tablet_mode":"color_grid",
                  "options":opts,"correct":cor,"verify":"tablet_click","tokens":3,"joy":"celebrate"})
    # Animals 10%
    for _ in range(int(n*.10)):
        t,opts,cor=_grid(_ANI,None)
        P.append({"id":f"animal_{t['id']}","domain":"Cognitive","protocol":random.choice(protos),
                  "level":3,"name":f"🐾 Find {t['label']}",
                  "instruction":f"Touch the {t['label']}!",
                  "waiting":f"Find the {t['label']}! 🐾","success":f"{t['label']}! ✅",
                  "fail":f"Look for {t['label']}!","tablet_mode":"object_grid",
                  "options":opts,"correct":cor,"verify":"tablet_click","tokens":3,"joy":"dance"})
    # Fruits 8%
    for _ in range(int(n*.08)):
        t,opts,cor=_grid(_FRT,None)
        P.append({"id":f"fruit_{t['id']}","domain":"Cognitive","protocol":"TEACCH",
                  "level":3,"name":f"🍎 Find {t['label']}",
                  "instruction":f"Touch the {t['label']}!",
                  "waiting":f"Find {t['label']}! 🍎","success":f"Yummy {t['label']}! ✅",
                  "fail":f"Find {t['label']}!","tablet_mode":"object_grid",
                  "options":opts,"correct":cor,"verify":"tablet_click","tokens":3,"joy":"celebrate"})
    # Shapes 6%
    for _ in range(int(n*.06)):
        t,opts,cor=_grid(_SHP,None)
        P.append({"id":f"shape_{t['id']}","domain":"Cognitive","protocol":"TEACCH",
                  "level":4,"name":f"🔷 Find {t['label']}",
                  "instruction":f"Touch the {t['label']}!",
                  "waiting":f"Find {t['label']}! 🔷","success":"Correct shape! ✅",
                  "fail":f"Find {t['label']}!","tablet_mode":"object_grid",
                  "options":opts,"correct":cor,"verify":"tablet_click","tokens":3,"joy":"dance"})
    # Emotions 5%
    for _ in range(int(n*.05)):
        t,opts,cor=_grid(_EMO,None)
        P.append({"id":f"emo_{t['id']}","domain":"Social","protocol":"ESDM",
                  "level":4,"name":f"😊 Find {t['label']}",
                  "instruction":f"Which face looks {t['label']}?",
                  "waiting":f"Find {t['label']} face! 😊","success":f"Yes! {t['label']}! ✅",
                  "fail":f"Find the {t['label']} face!","tablet_mode":"object_grid",
                  "options":opts,"correct":cor,"verify":"tablet_click","tokens":4,"joy":"celebrate"})
    # Vehicles 4%
    for _ in range(int(n*.04)):
        t,opts,cor=_grid(_VEH,None)
        P.append({"id":f"vehicle_{t['id']}","domain":"Cognitive","protocol":"DTT",
                  "level":3,"name":f"🚗 Find {t['label']}",
                  "instruction":f"Touch the {t['label']}!",
                  "waiting":f"Find the {t['label']}! 🚗","success":f"{t['label']}! ✅",
                  "fail":f"Find {t['label']}!","tablet_mode":"object_grid",
                  "options":opts,"correct":cor,"verify":"tablet_click","tokens":3,"joy":"dance"})
    # Finger count 12%
    for _ in range(int(n*.12)):
        num=random.randint(1,10)
        P.append({"id":f"count_{num}","domain":"Math","protocol":random.choice(protos),
                  "level":5,"name":f"🔢 Show {num}",
                  "instruction":f"Show me {num} fingers! 🖐️",
                  "waiting":f"Show {num} fingers!","success":f"{num} fingers! ✅",
                  "fail":f"Show me {num} fingers!","tablet_mode":"number_display",
                  "target_number":num,"verify":"finger_count","tokens":5,"joy":"celebrate"})
    # Basic words 8%
    for _ in range(int(n*.08)):
        w=random.choice(_WDS)
        P.append({"id":f"say_{w}","domain":"Verbal","protocol":random.choice(protos),
                  "level":6,"name":f"🗣️ Say '{w}'",
                  "instruction":f"SAY the word: {w.upper()}! 🗣️",
                  "waiting":f"Just say: {w}! Listening! 🎤",
                  "success":f"I heard '{w}'! ✅","fail":f"Try saying: {w}!",
                  "tablet_mode":"word_display","word_emoji":"🗣️","word_text":w.upper(),
                  "verify":"speech_keyword","keyword":w,"tokens":4,"joy":"dance"})
    # Social words 5%
    for _ in range(int(n*.05)):
        w=random.choice(_SOC)
        P.append({"id":f"social_{w.replace(' ','_')}","domain":"Verbal","protocol":"ESDM",
                  "level":7,"name":f"💬 Say '{w}'",
                  "instruction":f"Say '{w.upper()}'! 💬",
                  "waiting":f"Say: {w}! 🎤","success":"Great! ✅","fail":f"Say: {w}!",
                  "tablet_mode":"word_display","word_emoji":"💬","word_text":w.upper(),
                  "verify":"speech_keyword","keyword":w,"tokens":5,"joy":"celebrate"})
    # Letters 4%
    for _ in range(int(n*.04)):
        lt=random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        P.append({"id":f"letter_{lt}","domain":"Verbal","protocol":"DTT",
                  "level":7,"name":f"🔤 Say '{lt}'",
                  "instruction":f"Say the letter: {lt}! 🔤",
                  "waiting":f"Say: {lt}! 🔤","success":f"Letter {lt}! ✅",
                  "fail":f"Say letter {lt}!","tablet_mode":"word_display",
                  "word_emoji":"🔤","word_text":lt,"verify":"speech_keyword",
                  "keyword":lt.lower(),"tokens":4,"joy":"dance"})
    random.shuffle(P)
    return P

print("🎲 Building task pool...")
POOL = build_pool(5000)
print(f"✅ {len(POOL)} tasks ready (endless)")

# ── 7. Shared state ──────────────────────────────────────────────────
ST = {
    "name":CHILD_NAME,"age":6,
    "task_index":0,"consecutive":0,"wrong_count":0,
    "tasks_mastered":0,"level":1,"domain":"Motor","protocol":"ABA",
    "score":0,"tokens":0,"streak":0,
    "tasks_ok":0,"tasks_fail":0,"tasks_timeout":0,"tasks_auto":0,
    "tablet_locked":True,"tablet_click_result":None,"tablet_instruction":"",
    # vision
    "emotion":"neutral","emotion_scores":{"neutral":1.0},
    "emotion_history":deque(maxlen=120),
    "face_detected":False,"attention":70,
    "hand_raised":False,"waving":False,"clapping":False,
    "arms_out":False,"hands_up":False,
    "blinking":False,"eye_contact":False,
    "finger_count":0,"body_motion":0.0,
    "pose_lm":{},"face_lm":{},
    "verify_action":None,"verify_result":False,"verify_timeout":0.0,
    # speech
    "speech_q":queue.Queue(),"last_speech":"","last_sound":time.time(),
    "heard_flag":False,"recording":False,"listening":True,
    # TTS state (set by TTS class)
    "is_speaking":False,"lip":0.0,
    # session
    "gaze":"child","social_joy":False,"eye_color":[100,180,255],
    "blink_v":0.3,"tilt_v":0.0,"nose_tw":0.0,
    "session_chat":[],"logs":[],
    "session_start":datetime.now().strftime("%H:%M"),
    "uptime":time.time(),"sim_cmd":None,
    "chat_msgs":[],
    "task_history":[],
    "emo_timeline":[],
    # shared frame buffer (CaptureThread → all readers)
    "latest_frame":None,
    "frame_lock":threading.Lock(),
}

def LOG(msg, t="info"):
    ST["logs"].append({"time":datetime.now().strftime("%H:%M:%S"),
                       "msg":str(msg)[:120],"type":t})
    if len(ST["logs"]) > 400: ST["logs"] = ST["logs"][-400:]
    print(f"[{t.upper()}] {str(msg)[:70]}")

# ── 8. Signal bridge ─────────────────────────────────────────────────
class Bridge(QObject):
    sig_task     = pyqtSignal(dict)
    sig_success  = pyqtSignal(str)
    sig_fail_msg = pyqtSignal(str)
    sig_feedback = pyqtSignal(str)
    sig_instr    = pyqtSignal(str)
    sig_waiting  = pyqtSignal(str)
    sig_unlock   = pyqtSignal()
    sig_lock     = pyqtSignal()
    sig_reset    = pyqtSignal()
    sig_joy      = pyqtSignal(str)
    sig_stats    = pyqtSignal()
    sig_balloons = pyqtSignal()
    sig_rec_on   = pyqtSignal()
    sig_rec_off  = pyqtSignal(str)
    sig_chat     = pyqtSignal(str,str,str)

BR = Bridge()

# ── 9. Capture thread — single owner of VideoCapture ────────────────
class CaptureThread(threading.Thread):
    """Owns VideoCapture. Writes to ST['latest_frame']. Thread-safe."""
    def __init__(self):
        super().__init__(daemon=True, name="Capture")
        self.running = False; self.cap = None
        self._ph = 0.0
        self._init_cam()

    def _init_cam(self):
        for idx in [1,0,2,3]:
            try:
                c = cv2.VideoCapture(idx)
                if c.isOpened():
                    ret,f = c.read()
                    if ret and f is not None and f.size > 0:
                        c.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                        c.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                        c.set(cv2.CAP_PROP_FPS, 30)
                        self.cap = c
                        print(f"✅ Camera idx={idx}"); return
                    c.release()
            except: pass
        print("⚠️  No camera — simulation mode")

    def _sim(self):
        f = np.zeros((480,640,3),dtype=np.uint8); f[:]=(10,12,28)
        self._ph += 0.04
        r = int(28+10*math.sin(self._ph))
        cv2.circle(f,(320,200),r,(80,120,220),2)
        cv2.putText(f,"NO CAMERA",(210,240),
                    cv2.FONT_HERSHEY_SIMPLEX,0.66,(100,150,255),2)
        return f

    def run(self):
        self.running = True
        while self.running:
            if self.cap and self.cap.isOpened():
                ret,frame = self.cap.read()
                if ret and frame is not None:
                    frame = cv2.flip(frame,1)
                else:
                    frame = self._sim()
            else:
                frame = self._sim(); self._ph += 0.04
            with ST["frame_lock"]:
                ST["latest_frame"] = frame.copy()
            time.sleep(0.016)   # 60 fps capture

    def get(self):
        with ST["frame_lock"]:
            f = ST["latest_frame"]
        return f.copy() if f is not None else self._sim()

    def stop(self):
        self.running = False
        if self.cap: self.cap.release()

# ── 10. MediaPipe thread ─────────────────────────────────────────────
class MPThread(threading.Thread):
    """Reads frames from capture, updates ST with body/face/hands data."""
    def __init__(self, cap: CaptureThread):
        super().__init__(daemon=True, name="MediaPipe")
        self.cap = cap; self.running = False
        self._pose=None; self._hands=None; self._face=None
        self._prev_gray=None; self._mbuf=[]; self._hhist=[]
        self._init_mp()

    def _init_mp(self):
        try:
            self._pose = mp.solutions.pose.Pose(
                min_detection_confidence=0.35,
                min_tracking_confidence=0.35, model_complexity=1)
            print("✅ MP Pose (sens=0.35)")
        except Exception as e: print(f"⚠️  Pose: {e}")
        try:
            self._hands = mp.solutions.hands.Hands(
                max_num_hands=2,
                min_detection_confidence=0.35,
                min_tracking_confidence=0.35)
            print("✅ MP Hands 10-finger")
        except Exception as e: print(f"⚠️  Hands: {e}")
        try:
            self._face = mp.solutions.face_mesh.FaceMesh(
                max_num_faces=1,
                min_detection_confidence=0.35,
                min_tracking_confidence=0.35,
                refine_landmarks=True)
            print("✅ MP FaceMesh")
        except Exception as e: print(f"⚠️  FaceMesh: {e}")

    def _angle(self,a,b,c_):
        try:
            ab=np.array([a.x-b.x,a.y-b.y,a.z-b.z])
            cb=np.array([c_.x-b.x,c_.y-b.y,c_.z-b.z])
            cos=np.dot(ab,cb)/(np.linalg.norm(ab)*np.linalg.norm(cb)+1e-6)
            return math.degrees(math.acos(np.clip(cos,-1,1)))
        except: return 0.0

    def _fingers(self,hlm):
        try:
            n=0
            if hlm.landmark[4].x < hlm.landmark[3].x: n+=1
            for tip in [8,12,16,20]:
                if hlm.landmark[tip].y < hlm.landmark[tip-2].y: n+=1
            return n
        except: return 0

    def _validate(self):
        va=ST.get("verify_action")
        if not va: return
        if time.time()>ST["verify_timeout"]: ST["verify_action"]=None; return
        pl=ST.get("pose_lm",{}); fm=ST.get("face_lm",{})
        ok=False
        if va=="clap":       ok=ST["clapping"]
        elif va=="wave":     ok=ST["waving"]
        elif va=="raise_hand":
            ok=(pl.get("lwy",1)<pl.get("lsy",0)-0.05 or
                pl.get("rwy",1)<pl.get("rsy",0)-0.05)
        elif va=="touch_nose":
            nx=fm.get("nose_x",-1); ny=fm.get("nose_y",-1)
            fw=fm.get("fw",640); fh=fm.get("fh",480)
            if nx>0:
                li=(pl.get("lix",0)*fw,pl.get("liy",0)*fh)
                ri=(pl.get("rix",0)*fw,pl.get("riy",0)*fh)
                ok=(math.dist(li,(nx,ny))<fw*0.15 or
                    math.dist(ri,(nx,ny))<fw*0.15)
        elif va=="arms_out":  ok=ST["arms_out"]
        elif va=="hands_up":  ok=ST["hands_up"]
        elif va=="body_motion": ok=ST["body_motion"]>14
        elif va=="finger_count":
            ok=ST["finger_count"]==ST.get("finger_target",1)
        if ok:
            ST["verify_result"]=True; ST["verify_action"]=None
            LOG(f"✅ Verified: {va}","success")

    def run(self):
        self.running=True
        while self.running:
            frame = self.cap.get()

            # Motion detection — sensitive
            gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
            gray=cv2.GaussianBlur(gray,(13,13),0)
            if self._prev_gray is not None:
                diff=cv2.absdiff(self._prev_gray,gray)
                _,th=cv2.threshold(diff,10,255,cv2.THRESH_BINARY)
                m=float(np.mean(th))
                self._mbuf.append(m)
                if len(self._mbuf)>10: self._mbuf.pop(0)
                ST["body_motion"]=m
                avg=sum(self._mbuf[:-1])/max(len(self._mbuf)-1,1)
                ST["clapping"]=(m>avg*2.2 and m>7)
                h2,w2=gray.shape
                lm_=float(np.mean(th[:,:w2//2]))
                rm_=float(np.mean(th[:,w2//2:]))
                self._hhist.append(
                    "L" if lm_>rm_+2 else "R" if rm_>lm_+2 else "N")
                if len(self._hhist)>10: self._hhist.pop(0)
                chg=sum(1 for i in range(1,len(self._hhist))
                        if self._hhist[i]!=self._hhist[i-1]
                        and self._hhist[i]!="N")
                ST["waving"]=chg>=3
            self._prev_gray=gray

            rgb=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)

            # Pose
            if self._pose:
                try:
                    res=self._pose.process(rgb)
                    if res.pose_landmarks:
                        lm=res.pose_landmarks.landmark
                        PL=mp.solutions.pose.PoseLandmark
                        h2,w2=frame.shape[:2]
                        pl={
                            "nx":lm[PL.NOSE].x,"ny":lm[PL.NOSE].y,
                            "lsy":lm[PL.LEFT_SHOULDER].y,"rsy":lm[PL.RIGHT_SHOULDER].y,
                            "lwy":lm[PL.LEFT_WRIST].y,"rwy":lm[PL.RIGHT_WRIST].y,
                            "lix":lm[PL.LEFT_INDEX].x,"liy":lm[PL.LEFT_INDEX].y,
                            "rix":lm[PL.RIGHT_INDEX].x,"riy":lm[PL.RIGHT_INDEX].y,
                            "lsa":self._angle(lm[PL.LEFT_ELBOW],lm[PL.LEFT_SHOULDER],lm[PL.LEFT_HIP]),
                            "rsa":self._angle(lm[PL.RIGHT_ELBOW],lm[PL.RIGHT_SHOULDER],lm[PL.RIGHT_HIP]),
                        }
                        ST["pose_lm"]=pl
                        ST["hand_raised"]=(pl["lwy"]<pl["lsy"]-0.05 or pl["rwy"]<pl["rsy"]-0.05)
                        ST["arms_out"]=(pl["lsa"]>55 and pl["rsa"]>55)
                        ST["hands_up"]=(pl["lwy"]<pl["lsy"]-0.05 and pl["rwy"]<pl["rsy"]-0.05)
                        ST["face_detected"]=True
                        ST["attention"]=min(100,ST["attention"]+1)
                        ST["face_lm"].update({
                            "nose_x":pl["nx"]*w2,"nose_y":pl["ny"]*h2,"fw":w2,"fh":h2})
                    else:
                        ST["attention"]=max(0,ST["attention"]-2)
                except: pass

            # FaceMesh — emotion + micro-anim
            if self._face:
                try:
                    fr=self._face.process(rgb)
                    if fr.multi_face_landmarks:
                        fl=fr.multi_face_landmarks[0].landmark
                        h2,w2=frame.shape[:2]
                        ri=[33,160,158,133,153,144]; li=[362,385,387,263,373,380]
                        def ear(idx):
                            pts=[(fl[i].x*w2,fl[i].y*h2) for i in idx]
                            A=math.dist(pts[1],pts[5]); B=math.dist(pts[2],pts[4])
                            C=math.dist(pts[0],pts[3])
                            return (A+B)/(2*C) if C>0 else 0.3
                        ea=(ear(ri)+ear(li))/2.0
                        ST["blinking"]=ea<0.22; ST["eye_contact"]=ea>0.22
                        uly=fl[13].y*h2; lly=fl[14].y*h2
                        mo=(lly-uly)/h2
                        ST["face_lm"].update({
                            "ear_avg":ea,"mouth_open":mo,
                            "nose_x":fl[1].x*w2,"nose_y":fl[1].y*h2,"fw":w2,"fh":h2})
                        ST["tilt_v"]=fl[1].x-0.5; ST["nose_tw"]=abs(fl[4].y-fl[1].y)*10
                        ST["blink_v"]=ea
                        # Emotion from face mesh
                        sc={"neutral":0.4}
                        if ea<0.19:       sc={"surprised":0.85,"neutral":0.15}
                        elif mo>0.07:     sc={"happy":0.88,"neutral":0.12}
                        elif mo>0.045:    sc={"happy":0.60,"joyful":0.40}
                        elif ea<0.22 and mo<0.015: sc={"sad":0.70,"neutral":0.30}
                        elif mo>0.03 and ea>0.28:  sc={"excited":0.65,"happy":0.35}
                        em=max(sc,key=sc.get)
                        ST["emotion"]=em; ST["emotion_scores"]=sc
                        ST["emotion_history"].append(em)
                        ST["emo_timeline"].append({
                            "time":datetime.now().strftime("%H:%M:%S"),
                            "emotion":em,"score":ST["score"]})
                        if len(ST["emo_timeline"])>500:
                            ST["emo_timeline"]=ST["emo_timeline"][-500:]
                except: pass

            # Hands — 10 fingers (both hands)
            if self._hands:
                try:
                    hr=self._hands.process(rgb)
                    if hr.multi_hand_landmarks:
                        total=min(sum(self._fingers(h) for h in hr.multi_hand_landmarks),10)
                        ST["finger_count"]=total
                        if len(hr.multi_hand_landmarks)>=2:
                            h1=hr.multi_hand_landmarks[0].landmark[0]
                            h2_=hr.multi_hand_landmarks[1].landmark[0]
                            if abs(h1.x-h2_.x)<0.22 and abs(h1.y-h2_.y)<0.22:
                                ST["clapping"]=True
                    else:
                        ST["finger_count"]=0
                except: pass

            self._validate()
            time.sleep(0.025)   # ~40 fps analysis

    def stop(self): self.running=False

# ── 11. Emotion window — EXACTLY 500×500 ────────────────────────────
class EmotionWin(threading.Thread):
    """
    Fixed 500×500 OpenCV window.
    cv2.WINDOW_AUTOSIZE = window size locked to image size.
    Reads frames from CaptureThread (no cap sharing).
    """
    WIN="Emotions [500x500]"
    COLS={
        "happy":(0,220,80),"joyful":(0,255,180),"sad":(80,80,200),
        "angry":(0,0,220),"fear":(0,150,200),"surprised":(200,50,220),
        "disgust":(0,160,100),"neutral":(160,160,160),"excited":(0,255,255),
    }
    EMJS={
        "happy":"😊 HAPPY","joyful":"😄 JOYFUL","sad":"😢 SAD",
        "angry":"😠 ANGRY","fear":"😨 SCARED","surprised":"😲 SURPRISED",
        "disgust":"🤢 DISGUST","neutral":"😐 NEUTRAL","excited":"🤩 EXCITED",
    }

    def __init__(self, cap: CaptureThread):
        super().__init__(daemon=True, name="EmotionWin")
        self.cap=cap; self.running=True
        self._fc=0; self._face_crop=None

    def run(self):
        W=H=EMO_WIN_SIZE    # 500×500

        # WINDOW_AUTOSIZE: window is exactly the image size, NOT resizable
        cv2.namedWindow(self.WIN, cv2.WINDOW_AUTOSIZE)
        cv2.moveWindow(self.WIN, 10, 10)
        cv2.setWindowTitle(self.WIN,
            f"Emotions 500×500 — {CHILD_NAME}")

        while self.running:
            self._fc+=1
            # Update face crop every 2 frames
            if self._fc%2==0:
                frame=self.cap.get()
                fh,fw=frame.shape[:2]
                fm=ST.get("face_lm",{})
                nx=fm.get("nose_x",-1); ny=fm.get("nose_y",-1)
                if nx>0 and ny>0:
                    fs=int(min(fw,fh)*0.44)
                    x1=max(0,int(nx)-fs//2); y1=max(0,int(ny)-int(fs*0.7))
                    x2=min(fw,x1+fs);        y2=min(fh,y1+int(fs*1.1))
                    if x2>x1+10 and y2>y1+10:
                        self._face_crop=frame[y1:y2,x1:x2].copy()
                else:
                    ST["face_detected"]=False

            panel=self._build(W,H)
            cv2.imshow(self.WIN, panel)

            key=cv2.waitKey(1)&0xFF
            if key in [ord("q"),27]: break
            time.sleep(0.033)

        try: cv2.destroyWindow(self.WIN)
        except: pass

    def _build(self, W, H):
        em  =ST["emotion"]
        sco =ST["emotion_scores"]
        col =self.COLS.get(em,(160,160,160))

        canvas=np.zeros((H,W,3),dtype=np.uint8)
        canvas[:]=(10,12,28)

        # ── Face crop top section ────────────────────────
        face_h=int(H*0.40)   # 40% = 200px of 500
        fc=self._face_crop
        if fc is not None and fc.size>0:
            try:
                fc_r=cv2.resize(fc,(W,face_h))
                canvas[0:face_h,0:W]=fc_r
                cv2.rectangle(canvas,(0,0),(W-1,face_h-1),col,3)
            except: pass
        else:
            canvas[0:face_h,:]=(18,22,48)
            cv2.putText(canvas,"NO FACE DETECTED",(W//2-120,face_h//2),
                cv2.FONT_HERSHEY_SIMPLEX,0.85,(60,60,90),2)

        # ── Large emotion label ──────────────────────────
        lbl_y=face_h+2; lbl_h=44
        cv2.rectangle(canvas,(0,lbl_y),(W,lbl_y+lbl_h),(0,0,0),-1)
        cv2.rectangle(canvas,(0,lbl_y),(W,lbl_y+lbl_h),col,2)
        lbl_txt=self.EMJS.get(em,em.upper())
        cv2.putText(canvas,lbl_txt,(10,lbl_y+30),
            cv2.FONT_HERSHEY_SIMPLEX,0.82,col,2)
        # Face detected dot
        dc=(0,200,0) if ST["face_detected"] else (0,0,180)
        cv2.circle(canvas,(W-22,lbl_y+22),12,dc,-1)
        cv2.putText(canvas,"FACE" if ST["face_detected"] else "NO FACE",
            (W-95,lbl_y+28),cv2.FONT_HERSHEY_SIMPLEX,0.38,
            (0,180,0) if ST["face_detected"] else (0,0,180),1)

        # ── Emotion bars filling remaining space ─────────
        emos=["happy","sad","angry","surprised",
              "fear","disgust","neutral","excited","joyful"]
        bars_top=lbl_y+lbl_h+4
        bars_h=H-bars_top-4
        bar_h=max(18, bars_h//len(emos))

        for i,e in enumerate(emos):
            y=bars_top+i*bar_h
            if y+bar_h>H: break
            sc  =sco.get(e,0.0)
            act =(e==em)
            ec  =self.COLS.get(e,(120,120,120))

            # background
            cv2.rectangle(canvas,(0,y),(W,y+bar_h-2),(16,18,34),-1)
            # fill bar
            fw=int(sc*W)
            if fw>0:
                cv2.rectangle(canvas,(0,y),(fw,y+bar_h-2),ec,-1)
            # border
            brd=3 if act else 1
            cv2.rectangle(canvas,(0,y),(W,y+bar_h-2),
                ec if act else (35,38,58),brd)
            # label text — larger for 500px window
            lsize=0.42 if act else 0.36
            lwt =2 if act else 1
            cv2.putText(canvas,
                f"  {e.upper()}: {sc:.0%}",
                (4,y+bar_h-4),
                cv2.FONT_HERSHEY_SIMPLEX, lsize,
                (255,255,255) if act else (130,130,130), lwt)

        # ── Bottom: attention bar ────────────────────────
        att=ST["attention"]
        bw=int(W*att/100)
        cv2.rectangle(canvas,(0,H-20),(W,H),(14,16,32),-1)
        att_col=(0,200,80) if att>70 else (200,160,0) if att>40 else (200,0,0)
        cv2.rectangle(canvas,(0,H-20),(bw,H),att_col,-1)
        cv2.putText(canvas,f"ATTENTION: {att}%",(8,H-6),
            cv2.FONT_HERSHEY_SIMPLEX,0.38,(255,255,255),1)

        return canvas   # exactly 500×500

    def stop(self): self.running=False

# ── 12. Avatar draw (OpenCV) ─────────────────────────────────────────
def draw_av(img,cx,cy,ph,lip,spk,lst,joy,blink,tilt,scale=1.0):
    s=scale; hbob=int(4*math.sin(ph*0.5)*s); ht=int(tilt*14*s)
    hy=cy-int(54*s)+hbob; hx=cx+ht
    cv2.ellipse(img,(cx,cy+int(82*s)),(int(48*s),int(70*s)),0,0,360,(70,90,190),-1)
    cv2.ellipse(img,(cx,cy+int(82*s)),(int(48*s),int(70*s)),0,0,360,(100,120,220),2)
    cl=(0,220,200) if spk else (0,100,200)
    cv2.circle(img,(cx,cy+int(58*s)),int(9*s),cl,-1)
    cv2.circle(img,(cx,cy+int(58*s)),int(11*s),(0,180,255),1)
    if joy:
        jt=time.time()
        la=int(30*math.sin(jt*4)*s); ra=int(30*math.sin(jt*4+1)*s)
        cv2.ellipse(img,(cx-int(58*s)+la,cy+int(28*s)),(int(12*s),int(52*s)),-62+la,0,360,(70,90,190),-1)
        cv2.ellipse(img,(cx+int(58*s)+ra,cy+int(28*s)),(int(12*s),int(52*s)),62+ra,0,360,(70,90,190),-1)
    elif spk:
        la=int(22*math.sin(ph)*s); ra=int(22*math.sin(ph+math.pi)*s)
        cv2.ellipse(img,(cx-int(58*s)+la,cy+int(62*s)),(int(11*s),int(36*s)),-30+la,0,360,(70,90,190),-1)
        cv2.ellipse(img,(cx+int(58*s)+ra,cy+int(62*s)),(int(11*s),int(36*s)),30+ra,0,360,(70,90,190),-1)
    else:
        cv2.ellipse(img,(cx-int(58*s),cy+int(68*s)),(int(11*s),int(32*s)),-15,0,360,(70,90,190),-1)
        cv2.ellipse(img,(cx+int(58*s),cy+int(68*s)),(int(11*s),int(32*s)),15,0,360,(70,90,190),-1)
    cv2.rectangle(img,(cx-int(28*s),cy+int(148*s)),(cx-int(10*s),cy+int(180*s)),(55,75,165),-1)
    cv2.rectangle(img,(cx+int(10*s),cy+int(148*s)),(cx+int(28*s),cy+int(180*s)),(55,75,165),-1)
    cv2.circle(img,(hx,hy),int(53*s),(220,195,173),-1)
    cv2.circle(img,(hx,hy),int(53*s),(200,175,155),2)
    for ex in [hx-int(52*s),hx+int(52*s)]:
        cv2.circle(img,(ex,hy-int(5*s)),int(10*s),(210,185,163),-1)
        cv2.circle(img,(ex,hy-int(5*s)),int(7*s),(240,200,180),-1)
    eyh=max(1,int(7*s)) if not blink else 1
    ec=tuple(int(x) for x in ST["eye_color"])
    for ex in [hx-int(19*s),hx+int(19*s)]:
        cv2.ellipse(img,(ex,hy-int(9*s)),(int(7*s),eyh),0,0,360,ec,-1)
        if not blink:
            cv2.circle(img,(ex+1,hy-int(9*s)),int(3*s),(255,255,255),-1)
            cv2.circle(img,(ex+2,hy-int(10*s)),int(1*s),(0,0,0),-1)
    nt=int(ST.get("nose_tw",0)*0.5*s)
    cv2.circle(img,(hx+nt,hy+int(7*s)),int(5*s),(180,140,120),-1)
    mh=int((4+lip*20)*s)
    if spk:
        cv2.ellipse(img,(hx,hy+int(22*s)),(int(15*s),max(2,mh)),0,0,180,(160,80,80),-1)
        cv2.ellipse(img,(hx,hy+int(22*s)),(int(15*s),max(2,mh)),0,0,180,(210,110,110),2)
    elif ST["emotion"] in ["happy","joyful","excited"]:
        cv2.ellipse(img,(hx,hy+int(20*s)),(int(14*s),int(7*s)),0,0,180,(150,80,80),-1)
    else:
        cv2.line(img,(hx-int(12*s),hy+int(21*s)),(hx+int(12*s),hy+int(21*s)),(150,80,80),2)
    if joy:
        jt=time.time(); pr=int((84+14*abs(math.sin(jt*4)))*s)
        jc=(int(128+127*math.sin(jt*3)),int(200+55*math.sin(jt*2)),255)
        cv2.circle(img,(cx,cy),pr,jc,3)
    elif spk:
        pr=int((88+5*math.sin(ph*5))*s)
        cv2.circle(img,(cx,cy),pr,(0,160,255),2)
    elif lst:
        cv2.circle(img,(cx,cy),int(90*s),(0,220,100),2)
    return img

# ── 13. Live window W3 ───────────────────────────────────────────────
class LiveWin(threading.Thread):
    WIN="W3: Live Session — Pepper Clinical v3.3"
    ECOL={"happy":(0,220,80),"joyful":(0,255,180),"sad":(80,80,200),
          "angry":(0,0,220),"fear":(0,150,200),"surprised":(200,50,220),
          "disgust":(0,160,100),"neutral":(160,160,160),"excited":(0,255,255)}

    def __init__(self, cap: CaptureThread):
        super().__init__(daemon=True, name="LiveWin")
        self.cap=cap; self.running=True; self._ph=0.0

    def run(self):
        cv2.namedWindow(self.WIN, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.WIN, 1100, 620)
        cv2.moveWindow(self.WIN, 530, 20)
        while self.running:
            try:
                frame=self.cap.get()
                win=self._build(frame)
                cv2.imshow(self.WIN, win)
                key=cv2.waitKey(1)&0xFF
                if key in [ord("q"),27]: break
            except Exception as e:
                LOG(f"LiveWin:{e}","warn")
            time.sleep(0.033)   # 30 fps display
        try: cv2.destroyWindow(self.WIN)
        except: pass

    def _build(self, frame):
        W,H=1100,620
        win=np.zeros((H,W,3),dtype=np.uint8); win[:]=(8,10,22)
        for i in range(0,W,44): cv2.line(win,(i,0),(i,H),(13,16,33),1)
        for i in range(0,H,44): cv2.line(win,(0,i),(W,i),(13,16,33),1)

        # Camera left
        cp=cv2.resize(frame,(440,358)); win[58:416,8:448]=cp
        cv2.rectangle(win,(8,58),(448,416),(60,65,120),2)
        em=ST["emotion"]; col=self.ECOL.get(em,(160,160,160))
        cv2.putText(win,f"{em.upper()} | Att:{ST['attention']}%",
            (12,430),cv2.FONT_HERSHEY_SIMPLEX,0.50,col,2)
        fc=ST["finger_count"]
        if fc>0:
            cv2.putText(win,f"Fingers:{fc}/10 {'☝'*min(fc,10)}",
                (12,450),cv2.FONT_HERSHEY_SIMPLEX,0.44,(255,200,0),2)
        cv2.putText(win,
            f"Motion:{ST['body_motion']:.0f} | ★{ST['consecutive']}/3 | "
            f"Wrong:{ST['wrong_count']}/{MAX_WRONG}",
            (12,468),cv2.FONT_HERSHEY_SIMPLEX,0.36,(160,160,255),1)

        # Avatar center
        self._ph+=0.10 if ST["is_speaking"] else 0.03
        lip=ST.get("lip",0.0)
        if ST["is_speaking"]: lip=max(0.1,lip+0.3*abs(math.sin(self._ph*4)))
        blink=ST.get("blinking",False) or int(self._ph*3)%44==0
        draw_av(win,cx=640,cy=255,ph=self._ph,lip=lip,
                spk=ST["is_speaking"],lst=ST["listening"],
                joy=ST.get("social_joy",False),
                blink=blink,tilt=ST.get("tilt_v",0.0),scale=1.1)
        avlbl=("🔊 SPEAKING" if ST["is_speaking"] else
               ("🔴 REC" if ST["recording"] else
                ("🎤 LISTENING" if ST["listening"] else "💤")))
        avc=((0,180,255) if ST["is_speaking"] else
             ((0,0,220) if ST["recording"] else
              ((0,220,100) if ST["listening"] else (100,100,100))))
        cv2.putText(win,avlbl,(584,458),cv2.FONT_HERSHEY_SIMPLEX,0.48,avc,2)
        if ST.get("social_joy"):
            cv2.putText(win,"SOCIAL JOY!",(575,478),
                cv2.FONT_HERSHEY_SIMPLEX,0.50,(255,220,0),2)

        # Chat right
        cx1,cy1,cx2=758,58,1092
        cv2.rectangle(win,(cx1,cy1),(cx2,H-24),(12,14,30),-1)
        cv2.rectangle(win,(cx1,cy1),(cx2,H-24),(80,60,160),2)
        cv2.putText(win,"💬 CHAT",(cx1+8,cy1+18),
            cv2.FONT_HERSHEY_SIMPLEX,0.46,(160,140,255),2)
        msy=cy1+24
        for msg in ST["session_chat"][-14:]:
            isp=msg["role"]=="pepper"
            txt=("🤖 " if isp else "👦 ")+msg["text"][:42]
            bg=(28,18,54) if isp else (10,28,14)
            bc=(100,80,200) if isp else (0,180,80)
            cv2.rectangle(win,(cx1+2,msy),(cx2-2,msy+20),bg,-1)
            cv2.rectangle(win,(cx1+2,msy),(cx2-2,msy+20),bc,1)
            cv2.putText(win,txt,(cx1+5,msy+13),
                cv2.FONT_HERSHEY_SIMPLEX,0.30,
                (180,160,255) if isp else (100,220,100),1)
            msy+=22
            if msy>H-80: break
        cv2.rectangle(win,(cx1+2,H-46),(cx2-2,H-26),(16,20,42),-1)
        cv2.putText(win,"[Type in tablet chat — ask anything!]",
            (cx1+5,H-34),cv2.FONT_HERSHEY_SIMPLEX,0.29,(100,100,140),1)
        cv2.putText(win,"[Ask 'wash hands' → YouTube video opens]",
            (cx1+5,H-18),cv2.FONT_HERSHEY_SIMPLEX,0.28,(80,80,120),1)

        # Task bar
        tidx=ST["task_index"]%len(POOL); t=POOL[tidx]
        cv2.rectangle(win,(0,H-22),(W,H),(10,14,30),-1)
        cv2.putText(win,
            f"Task:{t.get('name','?')} | {t.get('protocol','?')} | "
            f"Score:{ST['score']} | Mastered:{ST['tasks_mastered']} | {CSV_FILE}",
            (6,H-6),cv2.FONT_HERSHEY_SIMPLEX,0.30,
            (0,200,100) if ST["face_detected"] else (200,150,0),1)

        # Header
        cv2.rectangle(win,(0,0),(W,54),(6,8,20),-1)
        cv2.putText(win,
            f"PEPPER v3.3 — {CHILD_NAME} — ABA/ESDM/TEACCH/DTT",
            (8,22),cv2.FONT_HERSHEY_SIMPLEX,0.54,(160,140,255),2)
        cv2.putText(win,
            f"Dashboard:http://{LOCAL_IP}:5007  "
            f"Games:http://{LOCAL_IP}:5009  "
            f"API:http://{LOCAL_IP}:5001",
            (8,42),cv2.FONT_HERSHEY_SIMPLEX,0.33,(80,180,120),1)
        return win

    def stop(self): self.running=False

# ── 14. Qt widgets ───────────────────────────────────────────────────
class Card(QPushButton):
    def __init__(self,data,idx,mode,parent=None):
        super().__init__(parent)
        self.idx=idx; self.mode=mode; self._d=data
        self.setFixedSize(158,158)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._sty(); self.clicked.connect(self._click)

    def _click(self):
        if not ST["tablet_locked"]:
            BR.sig_task.emit({"action":"click","idx":self.idx})

    def _sty(self):
        d=self._d; m=self.mode
        if m=="color_grid":
            self.setText(f"\n\n{d.get('label','')}")
            self.setFont(QFont("Arial",11,QFont.Weight.Bold))
            self.setStyleSheet(
                f"QPushButton{{background:{d['color']};border-radius:79px;"
                f"border:5px solid rgba(255,255,255,0.28);color:white;font-weight:bold;}}"
                f"QPushButton:hover{{border:6px solid white;}}"
                f"QPushButton:pressed{{border:7px solid #ffe066;}}")
        else:
            self.setText(f"{d.get('emoji','?')}\n{d.get('label','')}")
            self.setFont(QFont("Arial",14,QFont.Weight.Bold))
            self.setStyleSheet(
                "QPushButton{background:qlineargradient(x1:0,y1:0,x2:0,y2:1,"
                "stop:0 #1e1b4b,stop:1 #0c0f2e);border-radius:20px;"
                "border:4px solid #4f46e5;color:#e0e6ff;font-weight:bold;padding:6px;}"
                "QPushButton:hover{border:5px solid #a78bfa;}"
                "QPushButton:pressed{border:5px solid white;}")

    def ok(self):  self.setStyleSheet(self.styleSheet()+"QPushButton{border:8px solid #22c55e!important;}")
    def bad(self): self.setStyleSheet(self.styleSheet()+"QPushButton{border:8px solid #ef4444!important;opacity:0.5;}")
    def rst(self): self._sty()

class Balloons(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._b=[]; self._t=QTimer(self); self._t.timeout.connect(self._tick)
        self.hide()

    def launch(self,ms=3500):
        pw=self.parent()
        if pw: self.setGeometry(pw.rect())
        self._b=[{"x":random.randint(50,1200),"y":random.randint(700,900),
                  "vx":random.uniform(-2,2),"vy":random.uniform(-5,-2.5),
                  "color":random.choice(["#ef4444","#3b82f6","#22c55e",
                      "#fbbf24","#a855f7","#ec4899","#f97316"]),
                  "r":random.randint(22,44)} for _ in range(24)]
        self.show(); self.raise_(); self._t.start(28)
        QTimer.singleShot(ms,self._stop)

    def _tick(self):
        for b in self._b:
            b["x"]+=b["vx"]; b["y"]+=b["vy"]
            b["vy"]*=0.985; b["vx"]+=random.uniform(-0.25,0.25)
        self._b=[b for b in self._b if b["y"]>-100]
        self.update()
        if not self._b: self._stop()

    def paintEvent(self,e):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        for b in self._b:
            c=QColor(b["color"]); c.setAlpha(210)
            p.setBrush(c); p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(int(b["x"]-b["r"]),int(b["y"]-b["r"]),b["r"]*2,b["r"]*2)
        p.end()

    def _stop(self): self._t.stop(); self.hide(); self._b=[]

class AvWidget(QWidget):
    def __init__(self,w=200,h=240,parent=None):
        super().__init__(parent); self.setFixedSize(w,h)
        self._ph=0.0; self._s=w/200.0
        self.setStyleSheet("background:transparent;")
        t=QTimer(self); t.timeout.connect(self._tick); t.start(50)

    def _tick(self): self._ph+=0.10 if ST["is_speaking"] else 0.03; self.update()

    def paintEvent(self,e):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        s=self._s; cx=self.width()//2; cy=int(88*s)
        lip=ST.get("lip",0.0); spk=ST.get("is_speaking",False)
        em=ST.get("emotion","neutral")
        blink=ST.get("blinking",False) or int(self._ph*3)%44==0
        hbob=int(4*math.sin(self._ph*0.5)*s); ht=int(ST.get("tilt_v",0.0)*14*s)
        hy=cy-int(52*s)+hbob; hx=cx+ht

        p.setBrush(QColor(70,90,190)); p.setPen(QColor(100,120,220))
        p.drawEllipse(cx-int(44*s),cy+int(14*s),int(88*s),int(128*s))
        cl=QColor(0,220,200) if spk else QColor(0,100,200)
        p.setBrush(cl); p.setPen(QColor(0,180,255))
        p.drawEllipse(cx-int(8*s),cy+int(50*s),int(16*s),int(16*s))
        p.setBrush(QColor(70,90,190)); p.setPen(Qt.PenStyle.NoPen)
        if spk:
            la=int(18*math.sin(self._ph)*s)
            p.drawEllipse(cx-int(64*s)+la,cy+int(36*s),int(18*s),int(62*s))
            p.drawEllipse(cx+int(46*s)-la,cy+int(36*s),int(18*s),int(62*s))
        else:
            p.drawEllipse(cx-int(64*s),cy+int(40*s),int(18*s),int(58*s))
            p.drawEllipse(cx+int(46*s),cy+int(40*s),int(18*s),int(58*s))
        p.setBrush(QColor(220,195,173)); p.setPen(QColor(200,175,155))
        p.drawEllipse(hx-int(50*s),hy-int(50*s),int(100*s),int(100*s))
        eyh=max(1,int(7*s)) if not blink else 1
        ec=QColor(*ST["eye_color"])
        p.setBrush(ec); p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(hx-int(24*s),hy-int(15*s),int(12*s),eyh*2)
        p.drawEllipse(hx+int(12*s),hy-int(15*s),int(12*s),eyh*2)
        if not blink:
            p.setBrush(QColor(255,255,255))
            p.drawEllipse(hx-int(21*s),hy-int(14*s),int(5*s),int(5*s))
            p.drawEllipse(hx+int(14*s),hy-int(14*s),int(5*s),int(5*s))
        mh=max(2,int((4+lip*18)*s))
        if spk:
            p.setBrush(QColor(160,80,80)); p.setPen(QColor(210,110,110))
            from PyQt6.QtCore import QRect as QR
            p.drawChord(QR(hx-int(13*s),hy+int(14*s),int(26*s),mh*2),0,-180*16)
        elif em in ["happy","joyful","excited"]:
            p.setBrush(QColor(150,80,80)); p.setPen(Qt.PenStyle.NoPen)
            from PyQt6.QtCore import QRect as QR
            p.drawChord(QR(hx-int(12*s),hy+int(11*s),int(24*s),int(12*s)),0,-180*16)
        else:
            from PyQt6.QtGui import QPen as QP
            p.setPen(QP(QColor(150,80,80),2))
            p.drawLine(hx-int(11*s),hy+int(20*s),hx+int(11*s),hy+int(20*s))
        if ST.get("social_joy"):
            from PyQt6.QtGui import QPen as QP
            jt=time.time()
            jc=QColor(int(128+127*math.sin(jt*3)),int(200+55*math.sin(jt*2)),255)
            p.setPen(QP(jc,3)); p.setBrush(Qt.BrushStyle.NoBrush)
            pr=int(85*s)
            p.drawEllipse(cx-pr,cy-pr,pr*2,pr*2)
        elif spk:
            from PyQt6.QtGui import QPen as QP
            pr=int((86+5*math.sin(self._ph*5))*s)
            p.setPen(QP(QColor(0,160,255),2)); p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(cx-pr,cy-pr,pr*2,pr*2)
        p.end()

# ── 15. Tablet window ────────────────────────────────────────────────
class Tablet(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Pepper Tablet v3.3 — {CHILD_NAME}")
        self.setFixedSize(1280,810)
        self.setWindowFlags(
            Qt.WindowType.Window|Qt.WindowType.WindowStaysOnTopHint|
            Qt.WindowType.CustomizeWindowHint|Qt.WindowType.WindowTitleHint)
        self._cards=[]; self._locked=True; self._corr=-1
        self._joy_ph=0.0; self._cap=None; self._speech=None; self._gemini=None
        self._joy_t=QTimer(); self._joy_t.timeout.connect(self._joy_tick)
        self._build_ui(); self._connect()
        self._st_t=QTimer(); self._st_t.timeout.connect(self._stats); self._st_t.start(350)
        self._cam_t=QTimer(); self._cam_t.timeout.connect(self._update_cam); self._cam_t.start(33)

    def set_cap(self,c): self._cap=c
    def set_speech(self,s): self._speech=s
    def set_gemini(self,g): self._gemini=g

    def _build_ui(self):
        root=QWidget(); self.setCentralWidget(root)
        root.setStyleSheet("QWidget{background:#060918;}")
        ml=QHBoxLayout(root); ml.setSpacing(0); ml.setContentsMargins(0,0,0,0)

        # Left
        lf=QFrame(); lf.setFixedWidth(640)
        lf.setStyleSheet("QFrame{background:#0a0d1e;border-right:2px solid #1a1f40;}")
        ll=QVBoxLayout(lf); ll.setContentsMargins(0,0,0,0); ll.setSpacing(2)
        self.cam_lbl=QLabel(); self.cam_lbl.setFixedSize(640,452)
        self.cam_lbl.setStyleSheet("background:#000;")
        self.cam_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter); ll.addWidget(self.cam_lbl)
        frow=QHBoxLayout()
        self.fi_lbl=QLabel("Fingers: 0/10")
        self.fi_lbl.setFont(QFont("Arial",14,QFont.Weight.Bold))
        self.fi_lbl.setStyleSheet("color:#fbbf24;padding:3px;"); frow.addWidget(self.fi_lbl,1)
        self.av=AvWidget(185,215); frow.addWidget(self.av); ll.addLayout(frow)
        self.rec_lbl=QLabel("🎤 Always listening — just speak!")
        self.rec_lbl.setFont(QFont("Arial",10,QFont.Weight.Bold))
        self.rec_lbl.setStyleSheet("color:#34d399;padding:2px;")
        self.rec_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter); ll.addWidget(self.rec_lbl)
        cl=QLabel("💬 Chat — ask anything! (e.g. how to wash hands → YouTube)")
        cl.setFont(QFont("Arial",8,QFont.Weight.Bold))
        cl.setStyleSheet("color:#a78bfa;padding:2px 4px;"); ll.addWidget(cl)
        self.chat_box=QTextEdit(); self.chat_box.setReadOnly(True)
        self.chat_box.setFixedHeight(108)
        self.chat_box.setStyleSheet(
            "QTextEdit{background:#080a18;color:#c0c8ff;"
            "border:1px solid #2a2f60;border-radius:6px;"
            "font-size:9px;font-family:Arial;padding:3px;}"); ll.addWidget(self.chat_box)
        ci=QHBoxLayout()
        self.chat_in=QLineEdit()
        self.chat_in.setPlaceholderText("Type message or question here...")
        self.chat_in.setStyleSheet(
            "QLineEdit{background:#10142a;color:#e0e6ff;"
            "border:2px solid #4f46e5;border-radius:8px;padding:5px;font-size:10px;}"
            "QLineEdit:focus{border:2px solid #a78bfa;}")
        self.chat_in.returnPressed.connect(self._chat_send); ci.addWidget(self.chat_in,1)
        sb=QPushButton("Send"); sb.setFixedWidth(58)
        sb.setStyleSheet(
            "QPushButton{background:#4f46e5;color:white;border-radius:8px;"
            "font-size:10px;font-weight:bold;padding:5px;}"
            "QPushButton:hover{background:#6366f1;}")
        sb.clicked.connect(self._chat_send); ci.addWidget(sb)
        ll.addLayout(ci); ll.addStretch(); ml.addWidget(lf)

        # Right
        rf=QWidget(); rf.setFixedWidth(640)
        rl=QVBoxLayout(rf); rl.setSpacing(4); rl.setContentsMargins(10,5,10,5)

        hdr=QFrame(); hdr.setFixedHeight(68)
        hdr.setStyleSheet(
            "QFrame{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #1a0a3d,stop:0.5 #0a0f28,stop:1 #1a0a3d);"
            "border-radius:13px;border:2px solid #4f46e5;}")
        hl=QHBoxLayout(hdr); hl.setContentsMargins(12,3,12,3)
        self.av_lbl=QLabel("🤖"); self.av_lbl.setFont(QFont("Arial",26))
        self.av_lbl.setStyleSheet("color:#a78bfa;"); hl.addWidget(self.av_lbl)
        tw=QWidget(); tl2=QVBoxLayout(tw); tl2.setSpacing(1)
        self.title_lbl=QLabel("PEPPER CLINICAL INFINITY v3.3")
        self.title_lbl.setFont(QFont("Arial",11,QFont.Weight.Bold))
        self.title_lbl.setStyleSheet("color:#a78bfa;"); tl2.addWidget(self.title_lbl)
        self.child_lbl=QLabel(f"Child: {CHILD_NAME} | ABA/ESDM/TEACCH/DTT")
        self.child_lbl.setFont(QFont("Arial",8))
        self.child_lbl.setStyleSheet("color:#60a5fa;"); tl2.addWidget(self.child_lbl)
        hl.addWidget(tw,1)
        sw=QWidget(); sl=QVBoxLayout(sw); sl.setSpacing(1)
        self.state_lbl=QLabel("🎤 Listening")
        self.state_lbl.setFont(QFont("Arial",8)); self.state_lbl.setStyleSheet("color:#34d399;")
        sl.addWidget(self.state_lbl,alignment=Qt.AlignmentFlag.AlignRight)
        self.wrong_lbl=QLabel("Wrong: 0/2")
        self.wrong_lbl.setFont(QFont("Arial",8,QFont.Weight.Bold))
        self.wrong_lbl.setStyleSheet("color:#f87171;")
        sl.addWidget(self.wrong_lbl,alignment=Qt.AlignmentFlag.AlignRight)
        hl.addWidget(sw); rl.addWidget(hdr)

        sf=QFrame(); sf.setFixedHeight(48)
        sf.setStyleSheet("QFrame{background:#0c0f1e;border-radius:11px;border:1px solid #1a1f40;}")
        sc=QHBoxLayout(sf); sc.setContentsMargins(10,4,10,4)
        self.task_lbl=QLabel("📋 Task")
        self.task_lbl.setFont(QFont("Arial",9,QFont.Weight.Bold))
        self.task_lbl.setStyleSheet(
            "color:#a78bfa;background:#1e1b4b;border-radius:7px;"
            "padding:3px 8px;border:2px solid #4f46e5;"); sc.addWidget(self.task_lbl)
        sw2=QWidget(); sl2=QVBoxLayout(sw2); sl2.setSpacing(0); sl2.setContentsMargins(0,0,0,0)
        self.stars=QLabel("☆ ☆ ☆"); self.stars.setFont(QFont("Arial",16))
        self.stars.setStyleSheet("color:#4b5563;")
        self.stars.setAlignment(Qt.AlignmentFlag.AlignCenter); sl2.addWidget(self.stars)
        self.m_sub=QLabel("0/3"); self.m_sub.setFont(QFont("Arial",7))
        self.m_sub.setStyleSheet("color:#6b7280;")
        self.m_sub.setAlignment(Qt.AlignmentFlag.AlignCenter); sl2.addWidget(self.m_sub)
        sc.addWidget(sw2,1)
        self.reward=QLabel("⭐"); self.reward.setFont(QFont("Arial",20))
        self.reward.setStyleSheet(
            "color:#fbbf24;background:#2a1a00;border-radius:7px;"
            "padding:2px 8px;border:2px solid #f59e0b;"); sc.addWidget(self.reward)
        rl.addWidget(sf)

        inf=QFrame(); inf.setFixedHeight(72)
        inf.setStyleSheet(
            "QFrame{background:qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            "stop:0 #1e1b4b,stop:1 #0c0f2e);"
            "border-radius:12px;border:2px solid #4f46e5;}")
        il=QVBoxLayout(inf); il.setContentsMargins(12,3,12,3)
        self.instr_ic=QLabel("📋"); self.instr_ic.setFont(QFont("Arial",15))
        self.instr_ic.setAlignment(Qt.AlignmentFlag.AlignCenter); il.addWidget(self.instr_ic)
        self.instr=QLabel("Getting ready...")
        self.instr.setFont(QFont("Arial",13,QFont.Weight.Bold))
        self.instr.setStyleSheet("color:#e0e6ff;")
        self.instr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.instr.setWordWrap(True); il.addWidget(self.instr); rl.addWidget(inf)

        self.cf=QFrame(); self.cf.setMinimumHeight(258)
        self.cf.setStyleSheet(
            "QFrame{background:rgba(12,15,30,0.92);border-radius:14px;border:2px solid #1a1f40;}")
        self.cl=QVBoxLayout(self.cf)
        self.cl.setContentsMargins(12,10,12,10)
        self.cl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._idle(); rl.addWidget(self.cf,1)

        fbf=QFrame(); fbf.setFixedHeight(46)
        fbf.setStyleSheet("QFrame{background:#0c0f1e;border-radius:11px;border:1px solid #1a1f40;}")
        fbl=QHBoxLayout(fbf); fbl.setContentsMargins(12,4,12,4)
        self.fb_ic=QLabel("🎤"); self.fb_ic.setFont(QFont("Arial",18)); fbl.addWidget(self.fb_ic)
        self.fb=QLabel("Always listening — speak or tap!")
        self.fb.setFont(QFont("Arial",11,QFont.Weight.Bold))
        self.fb.setStyleSheet("color:#34d399;"); self.fb.setWordWrap(True)
        fbl.addWidget(self.fb,1); rl.addWidget(fbf)

        self.mic=QPushButton("🎤  HOLD TO SPEAK")
        self.mic.setFixedHeight(48); self.mic.setFont(QFont("Arial",13,QFont.Weight.Bold))
        self.mic.setStyleSheet(
            "QPushButton{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #dc2626,stop:1 #ef4444);"
            "color:white;border-radius:24px;border:3px solid #fca5a5;}"
            "QPushButton:pressed{background:#991b1b;border:4px solid white;}")
        self.mic.pressed.connect(self._mic_dn)
        self.mic.released.connect(self._mic_up); rl.addWidget(self.mic)

        sb2=QFrame(); sb2.setFixedHeight(40)
        sb2.setStyleSheet("QFrame{background:#07090f;border-radius:9px;border:1px solid #1a1f40;}")
        stl=QHBoxLayout(sb2); stl.setContentsMargins(8,2,8,2)
        for lbl,attr,col in [
            ("Score","s_sc","#a78bfa"),("Tokens","s_tk","#fbbf24"),
            ("Mastered","s_ms","#34d399"),("Streak","s_st","#60a5fa"),
            ("Wrong","s_wr","#f87171"),("Auto","s_au","#fb923c"),
        ]:
            ww=QWidget(); wl=QVBoxLayout(ww); wl.setSpacing(0); wl.setContentsMargins(0,0,0,0)
            v=QLabel("0"); v.setFont(QFont("Arial",10,QFont.Weight.Bold))
            v.setStyleSheet(f"color:{col};"); v.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lb=QLabel(lbl); lb.setFont(QFont("Arial",6))
            lb.setStyleSheet("color:#6b7280;"); lb.setAlignment(Qt.AlignmentFlag.AlignCenter)
            wl.addWidget(v); wl.addWidget(lb); stl.addWidget(ww); setattr(self,attr,v)
        rl.addWidget(sb2); ml.addWidget(rf)

        self.lov=QLabel("🔒"); self.lov.setParent(self.cf)
        self.lov.setGeometry(0,0,616,258)
        self.lov.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lov.setFont(QFont("Arial",48))
        self.lov.setStyleSheet(
            "QLabel{background:rgba(0,0,0,0.44);border-radius:14px;color:#a78bfa;}")
        self.lov.hide()
        self.blns=Balloons(root)

    def _update_cam(self):
        if self._cap is None: return
        frame=self._cap.get()
        frame=self._hud(frame.copy())
        rgb=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
        h_,w_,ch=rgb.shape
        qi=QImage(rgb.data.tobytes(),w_,h_,w_*ch,QImage.Format.Format_RGB888)
        pix=QPixmap.fromImage(qi).scaled(640,452,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation)
        self.cam_lbl.setPixmap(pix)
        fc=ST["finger_count"]
        self.fi_lbl.setText(f"Fingers: {fc}/10  {'☝'*min(fc,10) if fc>0 else '—'}")
        self._upd_chat()

    def _hud(self,frame):
        h,w=frame.shape[:2]
        cv2.rectangle(frame,(0,0),(w,50),(8,10,24),-1)
        tidx=ST["task_index"]%len(POOL); t=POOL[tidx]
        cv2.putText(frame,f"Task: {t.get('name','?')}",
            (8,18),cv2.FONT_HERSHEY_SIMPLEX,0.50,(200,200,255),1)
        cv2.putText(frame,
            f"★{'★'*ST['consecutive']}{'☆'*(3-ST['consecutive'])} "
            f"Score:{ST['score']} Wrong:{ST['wrong_count']}/{MAX_WRONG}",
            (8,38),cv2.FONT_HERSHEY_SIMPLEX,0.44,(255,220,0),1)
        fc=ST["finger_count"]
        if fc>0:
            cv2.rectangle(frame,(w-155,h-30),(w-2,h-2),(0,40,20),-1)
            cv2.rectangle(frame,(w-155,h-30),(w-2,h-2),(0,200,100),2)
            cv2.putText(frame,f"Fingers:{fc}/10",
                (w-150,h-10),cv2.FONT_HERSHEY_SIMPLEX,0.50,(0,255,120),2)
        mot=ST["body_motion"]
        bw=int((w-2)*min(mot/50.0,1.0))
        cv2.rectangle(frame,(0,h-16),(bw,h),(0,160,255) if mot>8 else (30,40,60),-1)
        if ST["recording"]:
            cv2.circle(frame,(w-18,18),11,(0,0,255),-1)
            cv2.putText(frame,"REC",(w-52,24),cv2.FONT_HERSHEY_SIMPLEX,0.44,(0,0,255),2)
        return frame

    def _connect(self):
        BR.sig_task.connect(self._on_task)
        BR.sig_success.connect(self._on_suc)
        BR.sig_fail_msg.connect(self._on_fail)
        BR.sig_feedback.connect(lambda t: self.fb.setText(t))
        BR.sig_instr.connect(lambda t: self.instr.setText(t))
        BR.sig_waiting.connect(lambda t: (
            self.fb.setText(t),self.fb.setStyleSheet("color:#fbbf24;"),
            self.fb_ic.setText("⏳")))
        BR.sig_unlock.connect(self._unlock)
        BR.sig_lock.connect(self._lock)
        BR.sig_reset.connect(self._reset)
        BR.sig_joy.connect(self._joy)
        BR.sig_stats.connect(self._stats)
        BR.sig_balloons.connect(lambda: self.blns.launch())
        BR.sig_rec_on.connect(self._rec_on)
        BR.sig_rec_off.connect(self._rec_off)
        BR.sig_chat.connect(self._on_chat_sig)

    def _stats(self):
        for attr,val in [
            ("s_sc",str(ST["score"])),("s_tk",str(ST["tokens"])),
            ("s_ms",str(ST["tasks_mastered"])),("s_st",str(ST["streak"])),
            ("s_wr",str(ST["wrong_count"])),("s_au",str(ST.get("tasks_auto",0))),
        ]:
            if hasattr(self,attr): getattr(self,attr).setText(val)
        n=ST["consecutive"]
        self.stars.setText("⭐"*n+"☆"*(3-n) if n else "☆ ☆ ☆")
        self.m_sub.setText(f"{n}/3")
        self.wrong_lbl.setText(f"Wrong: {ST['wrong_count']}/{MAX_WRONG}")
        cols={0:"#4b5563",1:"#d97706",2:"#fbbf24",3:"#f59e0b"}
        self.stars.setStyleSheet(f"color:{cols.get(n,'#4b5563')};")
        tidx=ST["task_index"]%len(POOL); t=POOL[tidx]
        self.task_lbl.setText(f"📋 {t.get('name','?')[:22]}")
        if ST["is_speaking"]:
            self.fb_ic.setText("🔊"); self.state_lbl.setText("🔊 Speaking")
            self.fb.setStyleSheet("color:#60a5fa;")
        elif ST["recording"]:
            self.fb_ic.setText("🔴"); self.state_lbl.setText("🔴 Recording")
        elif ST["listening"]:
            self.fb_ic.setText("🎤"); self.state_lbl.setText("🎤 Listening")
        else:
            self.fb_ic.setText("💤"); self.state_lbl.setText("💤 Ready")

    def _on_task(self,data):
        if data.get("action")=="click":
            self._click(data.get("idx",-1)); return
        mode=data.get("mode","idle")
        self.instr.setText(data.get("instruction",""))
        self.fb.setText("Your turn! Touch or speak!")
        self.fb.setStyleSheet("color:#60a5fa;")
        self._build(data)
        if mode not in ["motor_model","word_display","number_display"]:
            self._unlock()
        else:
            self._locked=False; ST["tablet_locked"]=False; self.lov.hide()

    def _build(self,data):
        self._clr(); mode=data.get("mode","idle")
        if mode=="idle": self._idle(); return
        if mode=="motor_model":
            vw=QWidget(); vl=QVBoxLayout(vw)
            vl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            fig=data.get("figure","")
            if fig and "base64," in fig:
                raw=base64.b64decode(fig.split(",",1)[1])
                qi=QImage(); qi.loadFromData(raw)
                pix=QPixmap.fromImage(qi).scaled(220,220,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation)
                fl=QLabel(); fl.setPixmap(pix)
                fl.setAlignment(Qt.AlignmentFlag.AlignCenter); vl.addWidget(fl)
            lb=QLabel(data.get("label",""))
            lb.setFont(QFont("Arial",15,QFont.Weight.Bold))
            lb.setStyleSheet("color:#a78bfa;")
            lb.setAlignment(Qt.AlignmentFlag.AlignCenter); vl.addWidget(lb)
            ar=QLabel("👇 NOW YOU DO IT! 👇")
            ar.setFont(QFont("Arial",12,QFont.Weight.Bold))
            ar.setStyleSheet("color:#34d399;")
            ar.setAlignment(Qt.AlignmentFlag.AlignCenter); vl.addWidget(ar)
            self.cl.addWidget(vw); return
        if mode=="word_display":
            wf=QFrame(); wf.setStyleSheet(
                "QFrame{background:qlineargradient(x1:0,y1:0,x2:0,y2:1,"
                "stop:0 #1e1b4b,stop:1 #0c0f1e);"
                "border-radius:18px;border:3px solid #4f46e5;min-height:138px;}")
            wl=QVBoxLayout(wf); wl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            el=QLabel(data.get("emoji","📢")); el.setFont(QFont("Arial",46))
            el.setAlignment(Qt.AlignmentFlag.AlignCenter); wl.addWidget(el)
            tl=QLabel(data.get("word","SAY IT!"))
            tl.setFont(QFont("Arial",34,QFont.Weight.Bold))
            tl.setStyleSheet("color:#a78bfa;")
            tl.setAlignment(Qt.AlignmentFlag.AlignCenter); wl.addWidget(tl)
            hl=QLabel("🎤 I AM ALWAYS LISTENING — just say it!")
            hl.setFont(QFont("Arial",11)); hl.setStyleSheet("color:#34d399;")
            hl.setAlignment(Qt.AlignmentFlag.AlignCenter); wl.addWidget(hl)
            self.cl.addWidget(wf); return
        if mode=="number_display":
            nf=QFrame(); nf.setStyleSheet(
                "QFrame{background:qlineargradient(x1:0,y1:0,x2:0,y2:1,"
                "stop:0 #1a3320,stop:1 #0c1a10);"
                "border-radius:18px;border:3px solid #22c55e;min-height:138px;}")
            nl=QVBoxLayout(nf); nl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            num=QLabel(str(data.get("target_number","?")))
            num.setFont(QFont("Arial",80,QFont.Weight.Bold))
            num.setStyleSheet("color:#34d399;")
            num.setAlignment(Qt.AlignmentFlag.AlignCenter); nl.addWidget(num)
            hl=QLabel("Show fingers on BOTH hands! 🖐️🖐️")
            hl.setFont(QFont("Arial",13)); hl.setStyleSheet("color:#22c55e;")
            hl.setAlignment(Qt.AlignmentFlag.AlignCenter); nl.addWidget(hl)
            self.cl.addWidget(nf); return
        # Grid
        opts=data.get("options",[]); self._corr=data.get("correct",-1)
        gw=QWidget(); gr=QGridLayout(gw); gr.setSpacing(10)
        gr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        for i,opt in enumerate(opts):
            card=Card(opt,i,mode); self._cards.append(card)
            gr.addWidget(card,i//2,i%2,Qt.AlignmentFlag.AlignCenter)
        self.cl.addWidget(gw)

    def _click(self,idx):
        if self._locked: return
        if ST.get("tablet_click_result") is not None: return
        self._locked=True; ST["tablet_locked"]=True
        corr=self._corr
        if corr==-1:
            ST["tablet_click_result"]="correct"
            if idx<len(self._cards): self._cards[idx].ok()
            self.fb.setText("✅ Great choice!")
            self.fb.setStyleSheet("color:#34d399;font-size:15px;"); return
        if idx==corr:
            ST["tablet_click_result"]="correct"
            if idx<len(self._cards): self._cards[idx].ok()
            self.fb.setText("✅ CORRECT! Amazing!")
            self.fb.setStyleSheet("color:#34d399;font-size:15px;font-weight:bold;")
        else:
            ST["tablet_click_result"]="wrong"
            if idx<len(self._cards): self._cards[idx].bad()
            if 0<=corr<len(self._cards): self._cards[corr].ok()
            self.fb.setText("❌ Not quite! Try again!")
            self.fb.setStyleSheet("color:#f87171;font-size:13px;")
        self.lov.show(); self.lov.raise_()

    def _on_suc(self,msg):
        self._clr()
        ov=QWidget(); ol=QVBoxLayout(ov); ol.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ck=QLabel("✅"); ck.setFont(QFont("Arial",96))
        ck.setAlignment(Qt.AlignmentFlag.AlignCenter); ol.addWidget(ck)
        ml=QLabel(msg); ml.setFont(QFont("Arial",13,QFont.Weight.Bold))
        ml.setStyleSheet("color:#34d399;")
        ml.setAlignment(Qt.AlignmentFlag.AlignCenter); ml.setWordWrap(True); ol.addWidget(ml)
        self.cl.addWidget(ov); self.instr_ic.setText("✅")
        QTimer.singleShot(2200,self._idle)
        QTimer.singleShot(2200,lambda: self.instr_ic.setText("📋"))

    def _on_fail(self,msg):
        self.fb.setText(f"❌ {msg}")
        self.fb.setStyleSheet("color:#f87171;font-size:13px;")
        self.instr_ic.setText("❌")
        QTimer.singleShot(1800,lambda: self.instr_ic.setText("📋"))

    def _joy(self,jt):
        self._joy_ph=0.0; self._joy_t.start(55)
        msgs={"dance":"🕺 DANCE! 🎉","celebrate":"🎊 AMAZING! ⭐",
              "wave_back":"👋 HIGH FIVE!","full_joy":"🏆 CHAMPION!"}
        self.fb.setText(msgs.get(jt,"🌟 AMAZING!"))
        self.fb.setStyleSheet("color:#fbbf24;font-size:16px;")
        QTimer.singleShot(3000,self._end_joy)

    def _joy_tick(self):
        self._joy_ph+=0.22
        ems=["🎉","🌟","⭐","🏆","✨","🎊","💫","🎈"]
        self.av_lbl.setText(ems[int(self._joy_ph)%len(ems)])
        if self._joy_ph>20: self._end_joy()

    def _end_joy(self):
        self._joy_t.stop(); self.av_lbl.setText("🤖")
        QTimer.singleShot(500,lambda: self.fb.setStyleSheet("color:#9ca3af;"))

    def _unlock(self):
        self._locked=False; ST["tablet_locked"]=False; self.lov.hide()
        for c in self._cards: c.setEnabled(True)

    def _lock(self):
        self._locked=True; ST["tablet_locked"]=True; self.lov.show(); self.lov.raise_()
        for c in self._cards: c.setEnabled(False)

    def _reset(self):
        for c in self._cards: c.rst()
        ST["tablet_click_result"]=None
        self._locked=False; ST["tablet_locked"]=False; self.lov.hide()
        for c in self._cards: c.setEnabled(True)

    def _idle(self):
        self._clr()
        d=QLabel("🤖\nPepper is preparing your task...")
        d.setFont(QFont("Arial",13)); d.setStyleSheet("color:#6b7280;")
        d.setAlignment(Qt.AlignmentFlag.AlignCenter); self.cl.addWidget(d)

    def _clr(self):
        while self.cl.count():
            it=self.cl.takeAt(0)
            if it.widget(): it.widget().deleteLater()
        self._cards.clear()

    def _mic_dn(self):
        self.mic.setText("🔴 RECORDING...")
        self.rec_lbl.setText("🔴 Recording — release to stop")
        self.rec_lbl.setStyleSheet("color:#ef4444;font-weight:bold;padding:2px;")
        if self._speech: self._speech.start_manual()

    def _mic_up(self):
        self.mic.setText("🎤  HOLD TO SPEAK")
        self.rec_lbl.setText("⏳ Processing...")
        if self._speech:
            threading.Thread(target=self._speech.stop_manual,daemon=True).start()

    def _rec_on(self):
        self.rec_lbl.setText("🔴 Recording...")
        self.rec_lbl.setStyleSheet("color:#ef4444;padding:2px;")

    def _rec_off(self,text):
        if text:
            self.rec_lbl.setText(f"✅ Heard: \"{text[:28]}\"")
            self.rec_lbl.setStyleSheet("color:#34d399;font-size:10px;padding:2px;")
        else:
            self.rec_lbl.setText("🎤 Always listening...")
            self.rec_lbl.setStyleSheet("color:#34d399;padding:2px;")
        QTimer.singleShot(3500,lambda: self.rec_lbl.setText("🎤 Always listening — just speak!"))
        QTimer.singleShot(3500,lambda: self.rec_lbl.setStyleSheet("color:#34d399;padding:2px;"))

    def _chat_send(self):
        txt=self.chat_in.text().strip()
        if not txt: return
        self.chat_in.clear()
        ST["session_chat"].append({"role":"child","text":txt,
            "time":datetime.now().strftime("%H:%M:%S")})
        ST["speech_q"].put(txt.lower()); ST["heard_flag"]=True
        ST["last_speech"]=txt.lower(); self._upd_chat()
        threading.Thread(target=self._chat_handle,args=(txt,),daemon=True).start()

    def _chat_handle(self,text):
        tl=text.lower(); yt=""
        how_map={
            "wash hands":"how+to+wash+hands+for+kids",
            "wash face":"how+to+wash+face+for+kids",
            "brush teeth":"how+to+brush+teeth+for+kids",
            "tie shoes":"how+to+tie+shoes+for+kids",
            "get dressed":"how+to+get+dressed+for+kids",
            "eat":"how+to+eat+with+fork+for+kids",
            "drink":"drinking+water+kids","toilet":"potty+training+kids",
            "count":"counting+1+to+10+kids+song","abc":"abc+alphabet+song+kids",
            "color":"colors+for+kids+learn","animal":"animals+sounds+kids",
            "shape":"shapes+song+for+kids","dance":"kids+dance+along",
            "hello":"hello+song+for+kids",
        }
        for kw,q in how_map.items():
            if kw in tl:
                yt=f"https://www.youtube.com/results?search_query={q}"; break
        if not yt and any(w in tl for w in ["how","teach","show me","what is","help"]):
            q="+".join(tl.split()[:5])+"+for+kids"
            yt=f"https://www.youtube.com/results?search_query={q}"
        reply=""
        if self._gemini and self._gemini.ok:
            reply=self._gemini.ask(
                f"Child says: '{text}'. Short warm child-friendly reply (1 sentence).")
        if not reply:
            reply=(f"Great question {CHILD_NAME}! " +
                   ("Let me find a video for you! 🎬" if yt else
                    "Keep asking — I love your curiosity! 🌟"))
        ST["session_chat"].append({"role":"pepper","text":reply,
            "time":datetime.now().strftime("%H:%M:%S")})
        BR.sig_chat.emit("pepper",reply,yt)
        TTS.say(reply)

    def _on_chat_sig(self,role,text,yt):
        self._upd_chat()
        if yt:
            self.fb.setText(f"🎬 {yt[:50]}...")
            self.fb.setStyleSheet("color:#fbbf24;")

    def _upd_chat(self):
        msgs=ST["session_chat"][-20:]
        html=""
        for m in msgs:
            isp=m["role"]=="pepper"
            col="#b0a0ff" if isp else "#80e880"
            pfx="🤖 Pepper: " if isp else f"👦 {CHILD_NAME}: "
            html+=f'<p style="color:{col};margin:1px 0">{pfx}{m["text"][:55]}</p>'
        self.chat_box.setHtml(html)
        self.chat_box.verticalScrollBar().setValue(
            self.chat_box.verticalScrollBar().maximum())

# ── 16. Always-on speech ─────────────────────────────────────────────
class Speech(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True,name="Speech")
        self._running=True; self._manual=False
        self._maudio=None; self._mlk=threading.Lock()
        self.whisper=None
        self.r=sr.Recognizer()
        self.r.energy_threshold=MIC_ENERGY
        self.r.dynamic_energy_threshold=True
        self.r.dynamic_energy_adjustment_damping=0.10
        self.r.pause_threshold=0.5
        self.r.phrase_threshold=0.03
        self.r.non_speaking_duration=0.3
        try:
            with sr.Microphone() as src:
                self.r.adjust_for_ambient_noise(src,duration=0.6)
            print(f"✅ Mic always-on (threshold={self.r.energy_threshold:.0f})")
        except Exception as e: print(f"⚠️  Mic: {e}")
        if WHISPER_OK:
            try:
                dev="cuda" if os.path.exists("/dev/nvidia0") else "cpu"
                self.whisper=WhisperModel("tiny",device=dev,
                    compute_type="float16" if dev=="cuda" else "int8")
                print(f"✅ Whisper ({dev})")
            except Exception as e: print(f"⚠️  Whisper: {e}")

    def _transcribe(self,audio)->str:
        if self.whisper:
            try:
                raw=audio.get_raw_data(convert_rate=16000,convert_width=2)
                with tempfile.NamedTemporaryFile(suffix=".wav",delete=False) as tmp: tp=tmp.name
                with wave.open(tp,"wb") as wf:
                    wf.setnchannels(1); wf.setsampwidth(2)
                    wf.setframerate(16000); wf.writeframes(raw)
                segs,_=self.whisper.transcribe(tp,language="en",
                    beam_size=1,vad_filter=False)
                text=" ".join(s.text.strip() for s in segs).strip()
                try: os.unlink(tp)
                except: pass
                if text: LOG(f"Whisper: {text}"); return text.lower()
            except Exception as e: LOG(f"Whisper:{e}","warn")
        try:
            text=self.r.recognize_google(audio)
            LOG(f"Google SR: {text}"); return text.lower()
        except sr.UnknownValueError: return ""
        except Exception as e: LOG(f"SR:{e}","warn"); return ""

    def _heard(self,text:str):
        if not text: return
        text=text.strip().lower()
        ST["last_speech"]=text; ST["last_sound"]=time.time()
        ST["heard_flag"]=True; ST["speech_q"].put(text)
        ST["session_chat"].append({"role":"child","text":text,
            "time":datetime.now().strftime("%H:%M:%S")})
        if len(ST["session_chat"])>100: ST["session_chat"]=ST["session_chat"][-100:]
        BR.sig_rec_off.emit(text)

    def run(self):
        while self._running:
            try:
                with sr.Microphone() as src:
                    self.r.adjust_for_ambient_noise(src,duration=0.06)
                    ST["listening"]=True
                    try:
                        audio=self.r.listen(src,timeout=4,phrase_time_limit=8)
                        ST["recording"]=True; BR.sig_rec_on.emit()
                        text=self._transcribe(audio)
                        ST["recording"]=False
                        if text: self._heard(text)
                    except sr.WaitTimeoutError: pass
                    finally: ST["recording"]=False; ST["listening"]=True
            except Exception: time.sleep(0.5)
            time.sleep(0.04)

    def start_manual(self):
        with self._mlk: self._manual=True
        ST["recording"]=True; BR.sig_rec_on.emit()
        threading.Thread(target=self._do_manual,daemon=True).start()

    def _do_manual(self):
        try:
            with sr.Microphone() as src:
                self.r.adjust_for_ambient_noise(src,duration=0.04)
                audio=self.r.listen(src,timeout=12,phrase_time_limit=8)
                with self._mlk: self._maudio=audio
        except: pass
        finally:
            ST["recording"]=False
            with self._mlk: self._manual=False

    def stop_manual(self)->str:
        for _ in range(30):
            with self._mlk:
                if not self._manual: break
            time.sleep(0.1)
        with self._mlk: audio=self._maudio; self._maudio=None
        if not audio: return ""
        text=self._transcribe(audio)
        if text: self._heard(text)
        return text

    def stop(self): self._running=False

# ── 17. PyBullet ─────────────────────────────────────────────────────
class Sim:
    def __init__(self): self.ok=False; self.rx=self.ry=0.0; self.pepper=None
    def launch(self):
        try:
            from qibullet import SimulationManager as QS
            import pybullet as pb, pybullet_data
            self.pb=pb; self.qisim=QS()
            self.client=self.qisim.launchSimulation(gui=True)
            pb.setRealTimeSimulation(1); pb.setGravity(0,0,-9.81)
            pb.setAdditionalSearchPath(pybullet_data.getDataPath())
            pb.loadURDF("plane.urdf")
            wc=[0.88,0.88,0.92,1]
            for pos,ext in [([0,-4,1.1],[5,.1,1.1]),([0,4,1.1],[5,.1,1.1]),
                            ([5,0,1.1],[.1,4,1.1]),([-5,0,1.1],[.1,4,1.1])]:
                pb.createMultiBody(0,-1,pb.createVisualShape(
                    pb.GEOM_BOX,halfExtents=ext,rgbaColor=wc),pos)
            for txt,pos in [("ABA",[-4,3,2.2]),("ESDM",[4,3,2.2]),
                            ("TEACCH",[0,4,2.2]),("DTT",[-4,-3,2.2]),
                            (f"★{CHILD_NAME}★",[0,0,3.2])]:
                pb.addUserDebugText(txt,pos,[.4,.5,.9],textSize=1.0,lifeTime=0)
            self.pepper=self.qisim.spawnPepper(self.client)
            self.pepper.goToPosture("Stand",0.5)
            pb.resetDebugVisualizerCamera(6,45,-30,[0,0,0.8])
            self.ok=True
            for fn in [self._arms,self._walk,self._step]:
                threading.Thread(target=fn,daemon=True).start()
            print("✅ PyBullet W1")
        except Exception as e: print(f"⚠️  PyBullet: {e}")

    def _sa(self,j,a,s=0.14):
        if self.pepper:
            try: self.pepper.setAngles(j,a,s)
            except: pass

    def _arms(self):
        ph=0
        while True:
            try:
                lip=ST.get("lip",0.0)
                if ST["is_speaking"]:
                    ph+=.07
                    self._sa("LShoulderPitch",.5+.3*math.sin(ph),.07)
                    self._sa("RShoulderPitch",.5+.3*math.sin(ph+math.pi*.6),.07)
                    self._sa("HeadPitch",-0.04-lip*0.14,.20)
                elif ST["listening"] or ST["recording"]:
                    self._sa("HeadYaw",0.25,.06); self._sa("HeadPitch",0.12,.06)
                else:
                    self._sa("LShoulderPitch",1.,.04); self._sa("RShoulderPitch",1.,.04)
                    self._sa("HeadYaw",ST.get("tilt_v",0.0)*0.5,.03)
                    self._sa("HeadPitch",.08 if ST.get("blinking") else 0.0,.03)
                if ST.get("social_joy"):
                    jt=time.time()*4
                    self._sa("LShoulderPitch",.05+.3*abs(math.sin(jt)),.25)
                    self._sa("RShoulderPitch",.05+.3*abs(math.sin(jt+math.pi)),.25)
            except: pass
            time.sleep(.04)

    def _walk(self):
        t=0
        while True:
            t+=.015; self.rx+=.015*math.cos(t*.4); self.ry+=.015*math.sin(t*.5)
            self.rx=max(-3.4,min(3.4,self.rx)); self.ry=max(-2.8,min(2.8,self.ry))
            try: self.pepper.setPosition([self.rx,self.ry,.8])
            except: pass
            time.sleep(.06)

    def _step(self):
        while True:
            try: self.pb.stepSimulation()
            except: pass
            time.sleep(1/240.)

# ── 18. Gemini ───────────────────────────────────────────────────────
EMPATHY={
    "ok":["PERFECT! [CLAP]","WOW! [DANCE]","BRILLIANT! [CELEBRATE]"],
    "retry":["Try again! 🎯","Almost! One more time!","You can do it!"],
    "up":["LEVEL UP! [DANCE]","CHAMPION! [CELEBRATE]"],
    "timeout":["No problem! Next task! 🎯","Moving on! Great effort!"],
    "wrong2":["Let us try a new task! Good try!","Moving on! Well done!"],
    "silence":["Ready when you are! 🎯","Take your time!"],
    "default":["Great effort! [CLAP]","Keep going! Amazing!"],
}
_el={}
def emp(cat="default"):
    p=EMPATHY.get(cat,EMPATHY["default"]); l=_el.get(cat,-1)
    c=[i for i in range(len(p)) if i!=l]
    if not c: c=list(range(len(p)))
    idx=random.choice(c); _el[cat]=idx; return p[idx]

class Gemini:
    MODELS=["gemini-1.5-flash","gemini-1.5-flash-8b","gemini-2.0-flash","gemini-pro"]
    def __init__(self):
        self.ok=False; self._lk=threading.Lock(); self.chat=None; self.model=None
        if not GEMINI_AVAIL: print("⚠️  Gemini N/A → empathy mode"); return
        sp=(f"You are PEPPER, clinical robot therapist for autism. "
            f"Child: {CHILD_NAME}. Protocols: ABA/ESDM/TEACCH/DTT. "
            f"Be warm, encouraging, child-friendly. Max 2 sentences.")
        for mn in self.MODELS:
            try:
                m=genai.GenerativeModel(mn,system_instruction=sp,
                    generation_config=genai.GenerationConfig(temperature=0.82,max_output_tokens=120))
                c=m.start_chat(history=[])
                r=c.send_message("Say READY")
                if r.text:
                    self.model=m; self.chat=c; self.ok=True
                    print(f"✅ Gemini: {mn}"); break
            except Exception as e: print(f"⚠️  {mn}: {str(e)[:50]}")
        if not self.ok: print("⚠️  Gemini → empathy mode")

    def ask(self,prompt):
        if not self.ok: return emp()
        ctx=(f"[child={CHILD_NAME} lv={ST['level']} dom={ST['domain']} "
             f"cons={ST['consecutive']}/3 wrong={ST['wrong_count']}/{MAX_WRONG} "
             f"em={ST['emotion']}] ")
        with self._lk:
            try: r=self.chat.send_message(ctx+prompt); return r.text.strip()
            except Exception as e:
                LOG(f"Gemini:{e}","warn")
                try: self.chat=self.model.start_chat(history=[])
                except: pass
                return emp()

# ── 19. Flask servers ─────────────────────────────────────────────────
api_app=Flask("api"); CORS(api_app)

@api_app.route("/")
def _ar(): return jsonify({"service":"Pepper API v3.3","child":CHILD_NAME})

@api_app.route("/status")
def _as():
    return jsonify({
        "child":CHILD_NAME,"score":ST["score"],"tokens":ST["tokens"],
        "mastered":ST["tasks_mastered"],"consecutive":ST["consecutive"],
        "wrong":ST["wrong_count"],"emotion":ST["emotion"],
        "attention":ST["attention"],"domain":ST["domain"],"protocol":ST["protocol"],
        "face_detected":ST["face_detected"],"listening":ST["listening"],
        "fingers":ST["finger_count"],"body_motion":round(ST["body_motion"],1),
        "timestamp":datetime.now().isoformat()})

@api_app.route("/session")
def _ase():
    return jsonify({
        "child":CHILD_NAME,"start":ST["session_start"],
        "score":ST["score"],"mastered":ST["tasks_mastered"],
        "ok":ST["tasks_ok"],"fail":ST["tasks_fail"],
        "timeout":ST.get("tasks_timeout",0),"auto":ST.get("tasks_auto",0),
        "emotion_history":list(ST["emotion_history"])[-30:],
        "chat":ST["session_chat"][-20:]})

@api_app.route("/timeline")
def _atl(): return jsonify({"timeline":ST.get("emo_timeline",[])[-100:]})

@api_app.route("/chat",methods=["POST"])
def _ach():
    d=request.json or {}; msg=d.get("message","")
    if msg:
        ST["speech_q"].put(msg.lower()); ST["heard_flag"]=True
        ST["last_speech"]=msg.lower()
        ST["session_chat"].append({"role":"child","text":msg,
            "time":datetime.now().strftime("%H:%M:%S")})
    return jsonify({"ok":True})

@api_app.route("/command",methods=["POST"])
def _acm():
    d=request.json or {}; cmd=d.get("cmd","")
    if cmd in ["next","break","report"]: ST["sim_cmd"]=cmd
    return jsonify({"ok":True,"cmd":cmd})

DASH_HTML="""<!DOCTYPE html><html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pepper — Parental Dashboard</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',sans-serif;background:#050810;color:#e0e6ff;min-height:100vh}
.hdr{background:linear-gradient(135deg,#1a0a3d,#0a0f28);padding:14px 22px;
  border-bottom:2px solid #4f46e5;display:flex;justify-content:space-between;align-items:center}
.hdr h1{font-size:1.28em;color:#a78bfa}.sub{color:#60a5fa;font-size:.82em}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(255px,1fr));gap:12px;padding:14px}
.card{background:#0c0f1e;border:1px solid #1a1f40;border-radius:13px;padding:14px}
.card h3{font-size:.80em;color:#6b7280;text-transform:uppercase;letter-spacing:.05em;margin-bottom:8px}
.num{font-size:2.1em;font-weight:bold}
.g{color:#34d399}.b{color:#60a5fa}.y{color:#fbbf24}.r{color:#f87171}.p{color:#a78bfa}
.ebar{height:20px;border-radius:3px;margin:2px 0;position:relative;overflow:hidden}
.ebar .fill{position:absolute;left:0;top:0;bottom:0;border-radius:3px}
.ebar .lbl{position:relative;z-index:1;font-size:.65em;font-weight:bold;padding:3px 5px}
.cp{background:#1e1b4b;color:#b0a0ff;padding:4px 7px;border-radius:5px;margin:2px 0;font-size:.76em}
.cc{background:#0a2818;color:#80e880;padding:4px 7px;border-radius:5px;margin:2px 0;font-size:.76em}
.ring{width:78px;height:78px;border-radius:50%;display:flex;align-items:center;
  justify-content:center;font-size:1.4em;font-weight:bold;border:4px solid #34d399}
.tl{display:flex;gap:7px;padding:3px 0;border-bottom:1px solid #1a1f40;font-size:.74em}
.rfb{background:#4f46e5;color:white;border:none;border-radius:7px;
  padding:5px 13px;cursor:pointer;font-size:.78em}
.rfb:hover{background:#6366f1}.s2{grid-column:span 2}
</style></head>
<body>
<div class="hdr">
  <div><h1>🤖 Parental Dashboard — Pepper Clinical v3.3</h1>
    <div class="sub">Child: <strong id="cn">...</strong> | Start: <span id="ss">-</span> | <span id="lu" style="color:#6b7280">-</span></div>
  </div>
  <button class="rfb" onclick="load()">⟳ Refresh</button>
</div>
<div class="grid">
  <div class="card">
    <h3>Progress</h3>
    <div style="display:flex;gap:12px;flex-wrap:wrap">
      <div style="text-align:center"><div class="num p" id="sc">0</div><div style="color:#6b7280;font-size:.72em">Score</div></div>
      <div style="text-align:center"><div class="num g" id="ms">0</div><div style="color:#6b7280;font-size:.72em">Mastered</div></div>
      <div style="text-align:center"><div class="num y" id="tk">0</div><div style="color:#6b7280;font-size:.72em">Tokens</div></div>
      <div style="text-align:center"><div class="num r" id="wr">0</div><div style="color:#6b7280;font-size:.72em">Wrong</div></div>
    </div>
  </div>
  <div class="card">
    <h3>Emotion</h3>
    <div style="font-size:2.5em;text-align:center" id="ee">😐</div>
    <div style="text-align:center;color:#a78bfa;font-size:.95em;margin:4px 0" id="el">neutral</div>
    <div id="eb"></div>
  </div>
  <div class="card">
    <h3>Attention & Body</h3>
    <div style="display:flex;gap:11px;align-items:center">
      <div class="ring" id="ar">70%</div>
      <div>
        <div style="color:#6b7280;font-size:.75em">Face</div><div style="font-size:1.1em" id="fd">-</div>
        <div style="color:#6b7280;font-size:.75em;margin-top:4px">Fingers</div><div style="font-size:1.1em;color:#fbbf24" id="fc">-</div>
        <div style="color:#6b7280;font-size:.75em;margin-top:4px">Motion</div><div style="font-size:1.1em;color:#60a5fa" id="bm">-</div>
      </div>
    </div>
  </div>
  <div class="card">
    <h3>Current Task</h3>
    <div style="color:#a78bfa;font-size:.92em;margin-bottom:5px" id="tn">-</div>
    <div style="color:#6b7280;font-size:.74em">Domain</div><div style="color:#60a5fa;font-size:.88em" id="td">-</div>
    <div style="color:#6b7280;font-size:.74em;margin-top:5px">Protocol</div><div style="color:#34d399;font-size:.88em" id="tp">-</div>
    <div style="color:#6b7280;font-size:.74em;margin-top:5px">Consecutive</div><div style="font-size:1.1em;color:#fbbf24" id="co">0/3</div>
  </div>
  <div class="card s2">
    <h3>Summary</h3>
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px">
      <div><div style="color:#6b7280;font-size:.72em">Success</div><div class="num g" id="ok" style="font-size:1.5em">0</div></div>
      <div><div style="color:#6b7280;font-size:.72em">Fail</div><div class="num r" id="fl" style="font-size:1.5em">0</div></div>
      <div><div style="color:#6b7280;font-size:.72em">Auto</div><div class="num" id="au" style="font-size:1.5em;color:#fb923c">0</div></div>
      <div><div style="color:#6b7280;font-size:.72em">Streak</div><div class="num y" id="st" style="font-size:1.5em">0</div></div>
    </div>
  </div>
  <div class="card s2">
    <h3>Emotion Timeline (last 20)</h3>
    <div id="tl" style="max-height:140px;overflow-y:auto"></div>
  </div>
  <div class="card s2">
    <h3>Chat Log (last 20)</h3>
    <div id="ch" style="max-height:150px;overflow-y:auto"></div>
  </div>
</div>
<script>
const EC={happy:"#22c55e",joyful:"#00ffb0",sad:"#6366f1",angry:"#ef4444",fear:"#0891b2",
  surprised:"#a855f7",disgust:"#14b8a6",neutral:"#9ca3af",excited:"#fbbf24"};
const EE={happy:"😊",joyful:"😄",sad:"😢",angry:"😠",fear:"😨",
  surprised:"😲",disgust:"🤢",neutral:"😐",excited:"🤩"};
async function load(){
  try{
    const[s,se,tl]=await Promise.all([
      fetch('/api/status').then(r=>r.json()),
      fetch('/api/session').then(r=>r.json()),
      fetch('/api/timeline').then(r=>r.json())]);
    document.getElementById('cn').textContent=s.child;
    document.getElementById('ss').textContent=se.start;
    document.getElementById('lu').textContent='Updated: '+new Date().toLocaleTimeString();
    document.getElementById('sc').textContent=s.score;
    document.getElementById('ms').textContent=s.mastered;
    document.getElementById('tk').textContent=s.tokens;
    document.getElementById('wr').textContent=s.wrong;
    document.getElementById('ok').textContent=se.ok;
    document.getElementById('fl').textContent=se.fail;
    document.getElementById('au').textContent=se.auto||0;
    document.getElementById('st').textContent=s.consecutive;
    document.getElementById('co').textContent=s.consecutive+'/3';
    document.getElementById('fd').textContent=s.face_detected?'✅ Yes':'❌ No';
    document.getElementById('fc').textContent=(s.fingers||0)+'/10';
    document.getElementById('bm').textContent=(s.body_motion||0).toFixed(1);
    document.getElementById('el').textContent=s.emotion;
    document.getElementById('ee').textContent=EE[s.emotion]||'😐';
    document.getElementById('ee').style.color=EC[s.emotion]||'#9ca3af';
    const att=Math.round(s.attention);
    document.getElementById('ar').textContent=att+'%';
    document.getElementById('ar').style.borderColor=att>70?'#34d399':att>40?'#fbbf24':'#ef4444';
    const hist=se.emotion_history||[];const cnt={};
    hist.forEach(e=>{cnt[e]=(cnt[e]||0)+1});const tot=hist.length||1;
    let bh='';
    for(const[e,c] of Object.entries(cnt)){
      const pct=Math.round(c/tot*100);
      bh+=`<div class="ebar" style="background:#16182e">
        <div class="fill" style="background:${EC[e]||'#4f46e5'};width:${pct}%"></div>
        <span class="lbl">${e.toUpperCase()}: ${pct}%</span></div>`;}
    document.getElementById('eb').innerHTML=bh;
    let ch='';
    (se.chat||[]).slice(-20).forEach(m=>{
      const cls=m.role==='pepper'?'cp':'cc';
      const pfx=m.role==='pepper'?'🤖 Pepper':'👦 '+s.child;
      ch+=`<div class="${cls}"><b>${pfx}:</b> ${m.text}</div>`;});
    document.getElementById('ch').innerHTML=ch;
    document.getElementById('ch').scrollTop=9999;
    let tlh='';
    (tl.timeline||[]).slice(-20).forEach(t=>{
      tlh+=`<div class="tl"><span style="color:#6b7280">${t.time}</span>
        <span style="color:${EC[t.emotion]||'#9ca3af'}">${EE[t.emotion]||'😐'} ${t.emotion}</span>
        <span style="color:#fbbf24">Score:${t.score}</span></div>`;});
    document.getElementById('tl').innerHTML=tlh;
  }catch(e){console.error(e)}}
load();setInterval(load,2500);
</script></body></html>"""

dash_app=Flask("dash"); CORS(dash_app)
@dash_app.route("/")
def _dr(): return render_template_string(DASH_HTML)
@dash_app.route("/api/status")
def _ds():
    return jsonify({
        "child":CHILD_NAME,"score":ST["score"],"tokens":ST["tokens"],
        "mastered":ST["tasks_mastered"],"consecutive":ST["consecutive"],
        "wrong":ST["wrong_count"],"emotion":ST["emotion"],
        "attention":ST["attention"],"domain":ST["domain"],"protocol":ST["protocol"],
        "face_detected":ST["face_detected"],"listening":ST["listening"],
        "fingers":ST["finger_count"],"body_motion":round(ST["body_motion"],1)})
@dash_app.route("/api/session")
def _dse():
    return jsonify({
        "child":CHILD_NAME,"start":ST["session_start"],
        "score":ST["score"],"mastered":ST["tasks_mastered"],
        "ok":ST["tasks_ok"],"fail":ST["tasks_fail"],
        "timeout":ST.get("tasks_timeout",0),"auto":ST.get("tasks_auto",0),
        "emotion_history":list(ST["emotion_history"])[-40:],
        "chat":ST["session_chat"][-20:]})
@dash_app.route("/api/timeline")
def _dtl(): return jsonify({"timeline":ST.get("emo_timeline",[])[-100:]})

GAMES_HTML="""<!DOCTYPE html><html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pepper Games</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',sans-serif;background:#050810;color:#e0e6ff;min-height:100vh}
.hdr{background:linear-gradient(135deg,#1a0a3d,#0a0f28);padding:13px 20px;border-bottom:2px solid #4f46e5}
.hdr h1{font-size:1.3em;color:#a78bfa}.hdr p{color:#60a5fa;font-size:.78em;margin-top:2px}
.fb{padding:5px 12px;border-radius:14px;border:2px solid #1a1f40;background:#0c0f1e;
  color:#9ca3af;cursor:pointer;font-size:.76em;transition:all .2s}
.fb:hover,.fb.on{background:#4f46e5;color:white;border-color:#4f46e5}
.fbar{padding:9px 18px;display:flex;gap:6px;flex-wrap:wrap;background:#080a1a;border-bottom:1px solid #1a1f40}
.srch{padding:5px 12px;border-radius:14px;border:2px solid #1a1f40;background:#0c0f1e;
  color:#e0e6ff;font-size:.76em;width:170px}
.srch:focus{outline:none;border-color:#4f46e5}
.gg{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:9px;padding:12px}
.gc{background:#0c0f1e;border:1px solid #1a1f40;border-radius:12px;padding:13px;
  cursor:pointer;transition:all .2s;position:relative}
.gc:hover{border-color:#4f46e5;transform:translateY(-2px)}
.ge{font-size:1.9em;text-align:center;margin-bottom:4px}
.gn{font-size:.85em;font-weight:bold;color:#a78bfa;margin-bottom:2px}
.gd{font-size:.70em;color:#6b7280;margin-bottom:5px}
.gm{display:flex;gap:4px;flex-wrap:wrap}
.tag{padding:1px 6px;border-radius:5px;font-size:.62em;font-weight:bold}
.tm{background:#1e3a5f;color:#60a5fa}.tc{background:#2d1f5e;color:#a78bfa}
.tv{background:#1a3320;color:#34d399}.th{background:#2d1a00;color:#fbbf24}
.ts{background:#3d0a1e;color:#f472b6}
.ta{background:#1e1b4b;color:#818cf8}.te{background:#0e2a3a;color:#38bdf8}
.tt{background:#2d0d5a;color:#c084fc}.td2{background:#3a0d2a;color:#f472b6}
.pb{position:absolute;top:8px;right:8px;background:#4f46e5;color:white;border:none;
  border-radius:6px;padding:3px 8px;font-size:.65em;font-weight:bold;cursor:pointer;
  opacity:0;transition:opacity .2s}
.gc:hover .pb{opacity:1}.pb:hover{background:#6366f1}
.sbar{position:fixed;bottom:0;left:0;right:0;background:#060918;
  border-top:1px solid #1a1f40;padding:7px 14px;display:flex;gap:14px;font-size:.76em}
.sbar span{color:#6b7280}.sbar strong{color:#a78bfa}
.modal{display:none;position:fixed;inset:0;background:rgba(0,0,0,.8);
  z-index:100;align-items:center;justify-content:center}
.modal.open{display:flex}
.mbox{background:#0c0f1e;border:2px solid #4f46e5;border-radius:15px;
  padding:22px;max-width:420px;width:90%;text-align:center}
.mbox h2{color:#a78bfa;margin-bottom:7px}.mbox p{color:#9ca3af;font-size:.84em;margin-bottom:13px}
.mac{display:flex;gap:7px;justify-content:center}
.bp{background:#4f46e5;color:white;border:none;border-radius:8px;
  padding:8px 18px;font-size:.84em;font-weight:bold;cursor:pointer}
.bc{background:#1a1f40;color:#9ca3af;border:none;border-radius:8px;
  padding:8px 18px;font-size:.84em;cursor:pointer}
</style></head>
<body>
<div class="hdr">
  <h1>🎮 Pepper Games — 52+ Clinical Games</h1>
  <p>ABA • ESDM • TEACCH • DTT — Autism Therapy | Omdurman Islamic University</p>
</div>
<div class="fbar">
  <input class="srch" id="srch" placeholder="🔍 Search..." oninput="render()">
  <button class="fb on" onclick="filt('all',this)">All</button>
  <button class="fb" onclick="filt('Motor',this)">🏃 Motor</button>
  <button class="fb" onclick="filt('Cognitive',this)">🧠 Cognitive</button>
  <button class="fb" onclick="filt('Verbal',this)">🗣️ Verbal</button>
  <button class="fb" onclick="filt('Math',this)">🔢 Math</button>
  <button class="fb" onclick="filt('Social',this)">😊 Social</button>
  <button class="fb" onclick="filt('ABA',this)">ABA</button>
  <button class="fb" onclick="filt('ESDM',this)">ESDM</button>
  <button class="fb" onclick="filt('TEACCH',this)">TEACCH</button>
  <button class="fb" onclick="filt('DTT',this)">DTT</button>
</div>
<div class="gg" id="gg"></div>
<div class="sbar">
  <span>Child: <strong id="sc">-</strong></span>
  <span>Score: <strong id="ss">0</strong></span>
  <span>Emotion: <strong id="se">-</strong></span>
  <span>Listening: <strong id="sl">-</strong></span>
</div>
<div class="modal" id="mod">
  <div class="mbox">
    <div style="font-size:2.6em" id="me">🎮</div>
    <h2 id="mn">Game</h2><p id="md">-</p>
    <div style="display:flex;gap:5px;justify-content:center;margin-bottom:11px" id="mt"></div>
    <div class="mac">
      <button class="bp" onclick="play()">▶ Play Now</button>
      <button class="bc" onclick="closeM()">Cancel</button>
    </div>
  </div>
</div>
<script>
const GAMES=[
  {n:"Clap Hands",e:"👏",dom:"Motor",pr:"ABA",d:"Clap hands"},
  {n:"Wave Hello",e:"👋",dom:"Motor",pr:"ESDM",d:"Wave to Pepper"},
  {n:"Raise Hand",e:"✋",dom:"Motor",pr:"DTT",d:"Raise hand high"},
  {n:"Touch Nose",e:"👆",dom:"Motor",pr:"TEACCH",d:"Touch nose"},
  {n:"Arms Wide",e:"🤸",dom:"Motor",pr:"ESDM",d:"Arms wide"},
  {n:"Hands Up",e:"🙌",dom:"Motor",pr:"ABA",d:"Hands up high"},
  {n:"Jump",e:"⬆️",dom:"Motor",pr:"ESDM",d:"Jump up"},
  {n:"Stomp",e:"🦶",dom:"Motor",pr:"DTT",d:"Stomp feet"},
  {n:"Spin",e:"🌀",dom:"Motor",pr:"TEACCH",d:"Spin around"},
  {n:"March",e:"🪖",dom:"Motor",pr:"ESDM",d:"March left right"},
  {n:"Find Red",e:"🔴",dom:"Cognitive",pr:"ABA",d:"Touch red color"},
  {n:"Find Blue",e:"🔵",dom:"Cognitive",pr:"DTT",d:"Touch blue color"},
  {n:"Find Green",e:"🟢",dom:"Cognitive",pr:"TEACCH",d:"Touch green"},
  {n:"Find Yellow",e:"🟡",dom:"Cognitive",pr:"ESDM",d:"Touch yellow"},
  {n:"Find Purple",e:"🟣",dom:"Cognitive",pr:"ABA",d:"Touch purple"},
  {n:"Find Dog",e:"🐶",dom:"Cognitive",pr:"ABA",d:"Identify dog"},
  {n:"Find Cat",e:"🐱",dom:"Cognitive",pr:"DTT",d:"Identify cat"},
  {n:"Find Lion",e:"🦁",dom:"Cognitive",pr:"ESDM",d:"Find lion"},
  {n:"Find Elephant",e:"🐘",dom:"Cognitive",pr:"TEACCH",d:"Find elephant"},
  {n:"Find Apple",e:"🍎",dom:"Cognitive",pr:"ABA",d:"Touch apple"},
  {n:"Find Banana",e:"🍌",dom:"Cognitive",pr:"DTT",d:"Find banana"},
  {n:"Find Circle",e:"⭕",dom:"Cognitive",pr:"TEACCH",d:"Touch circle"},
  {n:"Find Star",e:"⭐",dom:"Cognitive",pr:"ESDM",d:"Find star"},
  {n:"Find Heart",e:"❤️",dom:"Cognitive",pr:"ABA",d:"Find heart"},
  {n:"Happy Face",e:"😊",dom:"Social",pr:"ESDM",d:"Find happy face"},
  {n:"Sad Face",e:"😢",dom:"Social",pr:"ESDM",d:"Find sad face"},
  {n:"Angry Face",e:"😠",dom:"Social",pr:"ESDM",d:"Find angry face"},
  {n:"Surprised",e:"😲",dom:"Social",pr:"ESDM",d:"Find surprised"},
  {n:"Find Car",e:"🚗",dom:"Cognitive",pr:"DTT",d:"Touch car"},
  {n:"Find Bus",e:"🚌",dom:"Cognitive",pr:"ABA",d:"Find bus"},
  {n:"Count 1",e:"1️⃣",dom:"Math",pr:"ABA",d:"Show 1 finger"},
  {n:"Count 2",e:"2️⃣",dom:"Math",pr:"DTT",d:"Show 2 fingers"},
  {n:"Count 3",e:"3️⃣",dom:"Math",pr:"TEACCH",d:"Show 3 fingers"},
  {n:"Count 5",e:"5️⃣",dom:"Math",pr:"ABA",d:"Show 5 fingers"},
  {n:"Count 10",e:"🔟",dom:"Math",pr:"DTT",d:"Show 10 fingers"},
  {n:"Say Apple",e:"🗣️",dom:"Verbal",pr:"ABA",d:"Say APPLE"},
  {n:"Say Hello",e:"💬",dom:"Verbal",pr:"ESDM",d:"Say HELLO"},
  {n:"Say Please",e:"💬",dom:"Verbal",pr:"ESDM",d:"Say PLEASE"},
  {n:"Say Thank You",e:"💬",dom:"Verbal",pr:"ESDM",d:"Say THANK YOU"},
  {n:"Say Help",e:"💬",dom:"Verbal",pr:"ABA",d:"Say HELP"},
  {n:"Say Stop",e:"🛑",dom:"Verbal",pr:"DTT",d:"Say STOP"},
  {n:"Say More",e:"➕",dom:"Verbal",pr:"ABA",d:"Say MORE"},
  {n:"Say Yes",e:"✅",dom:"Verbal",pr:"ABA",d:"Say YES"},
  {n:"Say No",e:"❌",dom:"Verbal",pr:"DTT",d:"Say NO"},
  {n:"Say Ball",e:"🗣️",dom:"Verbal",pr:"DTT",d:"Say BALL"},
  {n:"Say Dog",e:"🗣️",dom:"Verbal",pr:"ABA",d:"Say DOG"},
  {n:"Say Cat",e:"🗣️",dom:"Verbal",pr:"DTT",d:"Say CAT"},
  {n:"Say Red",e:"🗣️",dom:"Verbal",pr:"ABA",d:"Say RED"},
  {n:"Say Blue",e:"🗣️",dom:"Verbal",pr:"DTT",d:"Say BLUE"},
  {n:"Say One",e:"🔢",dom:"Verbal",pr:"ABA",d:"Say ONE"},
  {n:"Say Sun",e:"🗣️",dom:"Verbal",pr:"ESDM",d:"Say SUN"},
  {n:"Say Water",e:"🗣️",dom:"Verbal",pr:"TEACCH",d:"Say WATER"},
];
const TC={Motor:'tm',Cognitive:'tc',Verbal:'tv',Math:'th',Social:'ts',
  ABA:'ta',ESDM:'te',TEACCH:'tt',DTT:'td2'};
let CF='all',CG=null;
function filt(f,b){CF=f;document.querySelectorAll('.fb').forEach(x=>x.classList.remove('on'));b.classList.add('on');render();}
function render(){
  const s=document.getElementById('srch').value.toLowerCase();
  const f=GAMES.filter(g=>(CF==='all'||g.dom===CF||g.pr===CF)&&(!s||g.n.toLowerCase().includes(s)||g.d.toLowerCase().includes(s)));
  document.getElementById('gg').innerHTML=f.map(g=>`
    <div class="gc" onclick="openM(${JSON.stringify(g).replace(/"/g,'&quot;')})">
      <div class="ge">${g.e}</div><div class="gn">${g.n}</div><div class="gd">${g.d}</div>
      <div class="gm"><span class="tag ${TC[g.dom]||'ta'}">${g.dom}</span>
        <span class="tag ${TC[g.pr]||'ta'}">${g.pr}</span></div>
      <button class="pb">▶</button></div>`).join('');}
function openM(g){CG=g;document.getElementById('me').textContent=g.e;
  document.getElementById('mn').textContent=g.n;document.getElementById('md').textContent=g.d;
  document.getElementById('mt').innerHTML=`<span class="tag ${TC[g.dom]||'ta'}">${g.dom}</span><span class="tag ${TC[g.pr]||'ta'}">${g.pr}</span>`;
  document.getElementById('mod').classList.add('open');}
function closeM(){document.getElementById('mod').classList.remove('open');CG=null;}
async function play(){if(!CG)return;try{await fetch('http://localhost:5001/command',
  {method:'POST',headers:{'Content-Type':'application/json'},
   body:JSON.stringify({cmd:'next'})});closeM();alert('"'+CG.n+'" sent to Pepper!');}
  catch(e){alert('Pepper not running.');}}
async function ls(){try{const r=await fetch('http://localhost:5001/status').then(r=>r.json());
  document.getElementById('sc').textContent=r.child;document.getElementById('ss').textContent=r.score;
  document.getElementById('se').textContent=r.emotion;document.getElementById('sl').textContent=r.listening?'Yes':'No';}catch(e){}}
render();ls();setInterval(ls,3000);
document.getElementById('mod').addEventListener('click',function(e){if(e.target===this)closeM();});
</script></body></html>"""

games_app=Flask("games"); CORS(games_app)
@games_app.route("/")
def _gr(): return render_template_string(GAMES_HTML)

def run_srv(app,port):
    try: app.run(host="0.0.0.0",port=port,debug=False,use_reloader=False)
    except Exception as e: print(f"⚠️  Port {port}: {e}")

# ── 20. Therapy controller ───────────────────────────────────────────
class Ctrl:
    def __init__(self,gemini,sim):
        self.g=gemini; self.s=sim; self.running=False

    def _say(self,text,wait=True):
        clean=re.sub(r"\[[^\]]+\]","",str(text)).strip()
        BR.sig_instr.emit(clean[:70])
        ST["tablet_instruction"]=clean
        TTS.say(text)
        if wait:
            t0=time.time()
            while ST["is_speaking"] and time.time()-t0<10:
                time.sleep(0.1)
            time.sleep(0.15)

    def run(self):
        self.running=True
        self._say(
            f"Hello {CHILD_NAME}! I am Pepper your Therapy Robot! "
            "I am always listening — just speak anytime! "
            f"Two wrong answers and we try a new task. "
            "Let us play and learn! Ready?")
        time.sleep(0.3)
        last_em=ST["emotion"]; em_t=time.time()

        while self.running:
            if time.time()-ST["last_sound"]>25:
                ST["last_sound"]=time.time(); TTS.say(emp("silence"))
            curr=ST["emotion"]
            if curr!=last_em and time.time()-em_t>12:
                last_em=curr; em_t=time.time()
                if curr in ["sad","angry","fear"]:
                    TTS.say(f"{CHILD_NAME} I see you feel {curr}. "
                            "It is okay. I am here. [HUG]")
            self._cmd()

            tidx=ST["task_index"]%len(POOL)
            task=POOL[tidx]
            ST["tablet_instruction"]=task["instruction"]
            ST["domain"]=task.get("domain","Motor")
            ST["protocol"]=task.get("protocol","ABA")
            ST["level"]=task.get("level",1)
            self._show(task)
            if task["domain"]=="Motor":
                self._say(task["instruction"]+" Watch the screen!",wait=False)
                ST["gaze"]="tablet"
                threading.Thread(target=lambda:(time.sleep(1.5),
                    ST.update({"gaze":"child"})),daemon=True).start()
            else:
                self._say(task["instruction"]+" Touch or say the answer!",wait=False)

            t0=time.time()
            ok,timeout,wc=self._run(task)
            dur=time.time()-t0

            log_row(task["id"],task["domain"],task["protocol"],task["level"],
                ok,wc,ST["consecutive"],ST["score"],
                ST["emotion"],ST["attention"],dur,timeout)
            ST["task_history"].append({
                "task":task["id"],"domain":task["domain"],"protocol":task["protocol"],
                "result":"ok" if ok else ("auto" if timeout else "fail"),
                "wrong":wc,"time":datetime.now().strftime("%H:%M:%S")})
            if len(ST["task_history"])>200: ST["task_history"]=ST["task_history"][-200:]

            if timeout:
                ST["tasks_timeout"]+=1; ST["tasks_auto"]+=1
                ST["consecutive"]=0; ST["streak"]=0; ST["wrong_count"]=0
                BR.sig_stats.emit(); TTS.say(emp("timeout"))
                ST["task_index"]=(ST["task_index"]+1)%len(POOL)
                LOG("⏱ Timeout → next","warn")
            elif ok:
                self._on_ok(task)
                TTS.say(f"{CHILD_NAME}! {task.get('success','Amazing!')} [CELEBRATE]")
            else:
                if wc>=MAX_WRONG:
                    ST["tasks_fail"]+=1; ST["consecutive"]=0
                    ST["streak"]=0; ST["tasks_auto"]+=1; ST["wrong_count"]=0
                    BR.sig_fail_msg.emit(task.get("fail","Not quite!"))
                    BR.sig_stats.emit(); TTS.say(emp("wrong2"))
                    ST["task_index"]=(ST["task_index"]+1)%len(POOL)
                    LOG(f"❌×{MAX_WRONG} → next","warn")
                else:
                    ST["tasks_fail"]+=1; self._on_fail(task)
                    TTS.say(f"{CHILD_NAME}! {task.get('fail','Try again!')} [THINK]")
            time.sleep(0.3)

    def _show(self,task):
        mode=task.get("tablet_mode","idle")
        data={"mode":mode,"instruction":task["instruction"]}
        if task["domain"]=="Motor" or mode=="motor_model":
            data.update({"mode":"motor_model",
                "figure":task.get("figure",""),"label":task.get("name","")})
        elif mode=="word_display":
            data.update({"emoji":task.get("word_emoji","📢"),
                "word":task.get("word_text","SAY IT!")})
        elif mode=="number_display":
            data.update({"target_number":task.get("target_number",1)})
        elif mode in ["color_grid","object_grid","shape_grid"]:
            data.update({"options":task.get("options",[]),
                "correct":task.get("correct",-1)})
        ST["tablet_click_result"]=None; ST["wrong_count"]=0
        ST["heard_flag"]=False; ST["last_speech"]=""
        while not ST["speech_q"].empty():
            try: ST["speech_q"].get_nowait()
            except: break
        BR.sig_task.emit(data); BR.sig_unlock.emit()

    def _run(self,task):
        vt=task.get("verify","motor")
        ml=["clap","wave","raise_hand","touch_nose","arms_out","hands_up","body_motion"]
        if vt in ml:
            ST["verify_action"]=vt; ST["verify_result"]=False
            ST["verify_timeout"]=time.time()+TASK_TIMEOUT
        elif vt=="finger_count":
            ST["verify_action"]="finger_count"; ST["verify_result"]=False
            ST["finger_target"]=task.get("target_number",1)
            ST["verify_timeout"]=time.time()+TASK_TIMEOUT

        local_wrong=0
        deadline=time.time()+TASK_TIMEOUT
        last_p=time.time(); pidx=0
        wt=task.get("waiting","I am waiting!")
        prompts=[wt,task["instruction"],f"{CHILD_NAME}! {wt}"]

        while time.time()<deadline:
            res=self._check(task)
            if res=="success": return True,False,local_wrong
            if res=="fail":
                local_wrong+=1; ST["wrong_count"]=local_wrong
                BR.sig_stats.emit()
                if local_wrong>=MAX_WRONG:
                    ST["verify_action"]=None; return False,False,local_wrong
                hint=task.get("fail","Try again!")
                TTS.say(hint); BR.sig_fail_msg.emit(hint)
                QTimer.singleShot(1900,lambda: BR.sig_reset.emit())
                time.sleep(0.5)
            if time.time()-last_p>9:
                last_p=time.time(); TTS.say(prompts[pidx%len(prompts)])
                BR.sig_waiting.emit(wt); pidx+=1
            self._cmd(); time.sleep(0.13)

        ST["verify_action"]=None; return False,True,local_wrong

    def _check(self,task):
        vt=task.get("verify","motor"); mc=task.get("verify","")
        if mc in ["clap","wave","raise_hand","touch_nose","arms_out","hands_up","body_motion"]:
            if ST["verify_result"]: ST["verify_result"]=False; return "success"
            if mc=="clap" and ST["clapping"]: return "success"
            if mc=="wave" and ST["waving"]: return "success"
            if mc=="raise_hand" and ST["hand_raised"]: return "success"
            if mc=="arms_out" and ST["arms_out"]: return "success"
            if mc=="hands_up" and ST["hands_up"]: return "success"
            if mc=="body_motion" and ST["body_motion"]>14: return "success"
        elif vt=="finger_count":
            if ST["finger_count"]==ST.get("finger_target",1): return "success"
        elif vt=="tablet_click":
            r=ST.get("tablet_click_result")
            if r=="correct": ST["tablet_click_result"]=None; return "success"
            if r=="wrong":   ST["tablet_click_result"]=None; return "fail"
        elif vt=="speech_keyword":
            kw=task.get("keyword","").lower()
            if not kw: return None
            if ST.get("heard_flag"):
                txt=ST.get("last_speech",""); ST["heard_flag"]=False
                while not ST["speech_q"].empty():
                    try:
                        qt=ST["speech_q"].get_nowait()
                        if kw in qt: return "success"
                    except: break
                if kw in txt: return "success"
                # Only fail if they said something real (>2 chars, not noise)
                if len(txt.strip())>2:
                    LOG(f"❌ Said '{txt}' not '{kw}'","warn"); return "fail"
                return None   # noise/too short — ignore
        elif vt=="speech_any":
            if ST.get("heard_flag") and len(ST.get("last_speech",""))>0:
                ST["heard_flag"]=False; return "success"
        return None

    def _on_ok(self,task):
        ST["consecutive"]+=1; ST["wrong_count"]=0
        ST["score"]+=task.get("tokens",2)*5
        ST["tokens"]+=task.get("tokens",2)
        ST["tasks_ok"]+=1; ST["streak"]+=1
        BR.sig_success.emit(task.get("success","✅"))
        BR.sig_joy.emit(task.get("joy","celebrate")); BR.sig_stats.emit()
        if ST["consecutive"]>=MASTERY_N:
            ST["consecutive"]=0; ST["tasks_mastered"]+=1
            ST["task_index"]=(ST["task_index"]+1)%len(POOL)
            ntask=POOL[ST["task_index"]%len(POOL)]
            ST["social_joy"]=True
            ST["eye_color"]=[int(128+127*math.sin(time.time()*3)),
                             int(200+55*math.sin(time.time()*2)),255]
            BR.sig_balloons.emit()
            TTS.say(f"{CHILD_NAME} earned 3 stars! MASTERED! "
                    f"Now: {ntask.get('name','')}!")
            QTimer.singleShot(4000,lambda: ST.update(
                {"social_joy":False,"eye_color":[100,180,255]}))

    def _on_fail(self,task):
        ST["consecutive"]=0; ST["streak"]=0
        BR.sig_fail_msg.emit(task.get("fail","Not quite! Try again!"))
        QTimer.singleShot(2000,lambda: BR.sig_reset.emit())

    def _cmd(self):
        cmd=ST.get("sim_cmd")
        if not cmd: return
        ST["sim_cmd"]=None
        if cmd=="next":
            ST["consecutive"]=0; ST["wrong_count"]=0
            ST["task_index"]=(ST["task_index"]+1)%len(POOL); TTS.say("Next task!")
        elif cmd=="break":
            TTS.say(f"Break time {CHILD_NAME}! Rest!")
        elif cmd=="report":
            dur=int((time.time()-ST["uptime"])/60)
            print(f"\n{'═'*60}\nSESSION REPORT — {CHILD_NAME}")
            print(f"Duration:{dur}min | Score:{ST['score']} | Mastered:{ST['tasks_mastered']}")
            print(f"OK:{ST['tasks_ok']} Fail:{ST['tasks_fail']} Auto:{ST.get('tasks_auto',0)}")
            print(f"CSV:{CSV_FILE}\nDashboard:http://{LOCAL_IP}:5007\n{'═'*60}")

# ── 21. Main ─────────────────────────────────────────────────────────
def main():
    print(f"""
╔══════════════════════════════════════════════════════════════════╗
║  PEPPER CLINICAL INFINITY v3.3 — {CHILD_NAME:<26}║
╠══════════════════════════════════════════════════════════════════╣
║  ✅ TTS: espeak subprocess — Pepper TALKS!                      ║
║  ✅ Emotion window: EXACTLY 500×500 pixels                      ║
║  ✅ Live session: no freeze (shared buffer)                     ║
║  ✅ Speech: keyword-only fails (no noise false-fails)           ║
║  ✅ {len(POOL)} endless tasks: ESDM/ABA/TEACCH/DTT                    ║
╠══════════════════════════════════════════════════════════════════╣
║  Dashboard: http://{LOCAL_IP}:5007{' '*(27-len(LOCAL_IP))}║
║  Games:     http://{LOCAL_IP}:5009{' '*(27-len(LOCAL_IP))}║
║  API:       http://{LOCAL_IP}:5001{' '*(27-len(LOCAL_IP))}║
╚══════════════════════════════════════════════════════════════════╝
""")

    # Flask servers (daemon threads)
    for app,port in [(api_app,5001),(dash_app,5007),(games_app,5009)]:
        threading.Thread(target=run_srv,args=(app,port),daemon=True).start()
        print(f"✅ Server :{port}")
    time.sleep(0.6)

    # Qt app — MUST be created on main thread
    qt=QApplication(sys.argv)
    qt.setAttribute(Qt.ApplicationAttribute.AA_DontCreateNativeWidgetSiblings)
    qt.setApplicationName("Pepper Clinical v3.3")
    qt.setStyle("Fusion")
    pal=QPalette()
    pal.setColor(QPalette.ColorRole.Window,    QColor(6,9,18))
    pal.setColor(QPalette.ColorRole.WindowText,QColor(224,230,255))
    pal.setColor(QPalette.ColorRole.Base,      QColor(12,15,30))
    pal.setColor(QPalette.ColorRole.Text,      QColor(224,230,255))
    qt.setPalette(pal)

    # Camera capture (single owner of VideoCapture)
    cap=CaptureThread(); cap.start()
    time.sleep(0.5)

    # MediaPipe (reads from capture, never from cap directly)
    mp_t=MPThread(cap); mp_t.start()

    # Tablet (Qt main thread, reads from capture via QTimer)
    tablet=Tablet(); tablet.set_cap(cap); tablet.show(); tablet.move(20,600)

    # Speech always-on
    speech=Speech(); speech.start(); tablet.set_speech(speech)

    # Emotion window — 500×500 fixed, own thread
    emo=EmotionWin(cap); emo.start()

    # Live window W3 — own thread, reads from capture
    live=LiveWin(cap); live.start()

    # PyBullet W1
    sim=Sim(); sim.launch()

    # Gemini AI
    gemini=Gemini(); tablet.set_gemini(gemini)

    # Therapy controller (background thread)
    ctrl=Ctrl(gemini,sim)
    threading.Thread(target=lambda:(time.sleep(2.0),ctrl.run()),daemon=True).start()

    print(f"""
{'═'*64}
✅ ALL SYSTEMS ACTIVE — Pepper v3.3

  W1: PyBullet simulation (lip-sync + walk)
  W2: Emotion — 500×500 FIXED (MediaPipe face mesh)
  W3: Live Session (30fps, never freezes)
  W4: Tablet 1280×810 (mini avatar + always-on speech)

  🔊 TTS: espeak subprocess — PEPPER TALKS EVERY TIME
  🎤 Mic: always-on background listener
  👦 Wrong ×2: auto-advance + CSV report

  Dashboard: http://{LOCAL_IP}:5007
  Games:     http://{LOCAL_IP}:5009
  API:       http://{LOCAL_IP}:5001

  Child:  {CHILD_NAME}
  CSV:    {CSV_FILE}
  Tasks:  {len(POOL)} endless (ABA/ESDM/TEACCH/DTT)

Commands: n=next  b=break  r=report  q=quit  stats=info
{'═'*64}
""")

    def _input():
        while ctrl.running:
            try:
                cmd=input("> ").strip().lower()
                if cmd in ["q","quit","exit"]:
                    ctrl.running=False
                    cap.stop(); speech.stop(); live.stop(); emo.stop(); TTS.stop()
                    qt.quit(); break
                elif cmd in ["n","next"]: ST["sim_cmd"]="next"
                elif cmd in ["b","break"]: ST["sim_cmd"]="break"
                elif cmd in ["r","report"]: ST["sim_cmd"]="report"
                elif cmd=="stats":
                    tidx=ST["task_index"]%len(POOL); t=POOL[tidx]
                    print(f"\nTask:{t['id']} Dom:{t['domain']} Proto:{t['protocol']} "
                          f"★{ST['consecutive']}/3 Score:{ST['score']} "
                          f"Wrong:{ST['wrong_count']}/{MAX_WRONG} "
                          f"Fingers:{ST['finger_count']}/10 Emotion:{ST['emotion']}")
            except (KeyboardInterrupt,EOFError): break
        qt.quit()

    threading.Thread(target=_input,daemon=True).start()
    ret=qt.exec()
    ctrl.running=False; cap.stop(); speech.stop(); live.stop(); emo.stop(); TTS.stop()
    dur=int((time.time()-ST["uptime"])/60)
    print(f"\nSESSION COMPLETE — {CHILD_NAME}")
    print(f"Duration:{dur}min Score:{ST['score']} Mastered:{ST['tasks_mastered']}")
    print(f"OK:{ST['tasks_ok']} Fail:{ST['tasks_fail']} Auto:{ST.get('tasks_auto',0)}")
    print(f"CSV:{CSV_FILE}  Dashboard:http://{LOCAL_IP}:5007")
    sys.exit(ret)

if __name__=="__main__":
    main()
