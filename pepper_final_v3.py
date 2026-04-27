#!/usr/bin/env python3
"""
PEPPER THERAPY STATION v3 - COMPLETE FIX
Port: 5007 (Parents Dashboard)
Camera: 300x300 emotion window
High sensitivity voice + emotion
Charts + Progress + Parent Notes
"""

import cv2, numpy as np, threading, time, random
import json, sys, os, math, re, warnings
import webbrowser, urllib.parse
warnings.filterwarnings('ignore')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

import pyttsx3
import speech_recognition as sr
from flask import Flask, request, jsonify, render_template_string
from datetime import datetime

import pybullet as p
import pybullet_data
sys.path.insert(0, '/home/lamya/pepper_duo/src')

import google.generativeai as genai

# ============================================================
# GEMINI SETUP - FIXED MODEL NAME
# ============================================================
GEMINI_KEY = "AIzaSyDEdleVKiQ5E00wMcjMbji0G9JcYT2TvE8"
genai.configure(api_key=GEMINI_KEY)

GEMINI_SYSTEM = """You are Pepper, an enthusiastic robotic ASD therapist.
PROTOCOLS: ABA, DTT, TEACCH, TIE
RULES: Short sentences (max 2). Immediate reinforcement. Use child's name.
TOKENS: [WAVE] [CLAP] [NOD] [DANCE] [POINT] [HUG]
TRIGGERS: [YOUTUBE: query] [GAME] [IMAGE: query]
EMOTION: happy→celebrate+harder | sad→comfort+easier[HUG] | angry→breathe[NOD]
Always end with task or question."""

# ============================================================
# SHARED STATE
# ============================================================
STATE = {
    "emotion":       "neutral",
    "emotion_scores":{},
    "face_detected": False,
    "attention":     70,
    "engagement":    "moderate",
    "child_name":    "Friend",
    "child_known":   False,
    "last_sound":    time.time(),
    "logs":          [],
    "score":         0,
    "protocol":      "GREETING",
    "prompt_level":  0,
    "is_speaking":   False,
    "clap_detected": False,
    "difficulty":    "easy",
    "consecutive":   0,
    "task_done":     False,
    "sim_cmd":       None,
    "gemini_ok":     False,
    "session_start": datetime.now().strftime("%H:%M"),
    # Charts data
    "attention_history": [],
    "score_history":     [],
    "emotion_history":   [],
    "time_history":      [],
    # Parent notes
    "parent_notes":      [],
    "session_notes":     "",
}

EMO_COLORS = {
    "happy":    (0, 220, 80),
    "sad":      (100, 100, 220),
    "angry":    (0, 0, 220),
    "fear":     (0, 180, 220),
    "surprise": (200, 50, 220),
    "disgust":  (0, 180, 100),
    "neutral":  (180, 180, 180),
}

_log_lock = threading.Lock()

def add_log(msg, log_type="info", protocol=None):
    """FIXED: correct signature"""
    with _log_lock:
        entry = {
            "time":     datetime.now().strftime("%H:%M:%S"),
            "msg":      str(msg)[:100],
            "type":     log_type,
            "protocol": protocol or STATE["protocol"],
            "emotion":  STATE["emotion"],
            "child":    STATE["child_name"],
        }
        STATE["logs"].append(entry)
        # Update history for charts
        now_str = datetime.now().strftime("%H:%M:%S")
        STATE["attention_history"].append(STATE["attention"])
        STATE["score_history"].append(STATE["score"])
        STATE["emotion_history"].append(STATE["emotion"])
        STATE["time_history"].append(now_str)
        # Keep last 50 points
        for key in ["attention_history","score_history",
                    "emotion_history","time_history"]:
            if len(STATE[key]) > 50:
                STATE[key] = STATE[key][-50:]
    print(f"[{entry['time']}][{log_type.upper()}] {msg[:70]}")

# ============================================================
# GEMINI BRAIN - FIXED MODEL
# ============================================================
class GeminiBrain:
    MODELS = [
        "gemini-1.5-flash-latest",
        "gemini-1.5-flash",
        "gemini-pro",
        "gemini-1.0-pro",
    ]

    def __init__(self):
        self.ok   = False
        self.chat = None
        self.model_name = None

        for model_name in self.MODELS:
            try:
                model = genai.GenerativeModel(
                    model_name,
                    system_instruction=GEMINI_SYSTEM,
                    generation_config=genai.GenerationConfig(
                        temperature=0.8,
                        max_output_tokens=120,
                    )
                )
                chat = model.start_chat(history=[])
                resp = chat.send_message("Say READY in 2 words")
                self.model = model
                self.chat  = chat
                self.model_name = model_name
                self.ok    = True
                STATE["gemini_ok"] = True
                print(f"✅ Gemini connected: {model_name}")
                break
            except Exception as e:
                print(f"⚠️  {model_name}: {e}")

        if not self.ok:
            print("⚠️  Gemini unavailable - using fallback")

    def ask(self, prompt):
        if not self.ok:
            return self._fallback()
        ctx = (
            f"[child={STATE['child_name']},"
            f"emotion={STATE['emotion']},"
            f"attention={STATE['attention']}%,"
            f"protocol={STATE['protocol']},"
            f"score={STATE['score']},"
            f"difficulty={STATE['difficulty']}] "
        )
        try:
            resp = self.chat.send_message(ctx + prompt)
            return resp.text.strip()
        except Exception as e:
            print(f"⚠️  Gemini ask: {e}")
            # Try reconnect
            self._reconnect()
            return self._fallback()

    def _reconnect(self):
        try:
            self.chat = self.model.start_chat(history=[])
        except: pass

    def _fallback(self):
        name = STATE["child_name"]
        tasks = [
            f"Clap your hands {name}! 👏",
            f"Touch your nose {name}! 👃",
            f"Wave hello {name}! 👋",
            f"Show happy face {name}! 😊",
            f"Stand up {name}! 🧍",
        ]
        return random.choice(tasks)

# ============================================================
# EMOTION DETECTOR - OpenCV (300x300 window)
# ============================================================
class EmotionDetector:
    """
    OpenCV Haar Cascades - HIGH ACCURACY
    Dedicated 300x300 emotion window
    """
    def __init__(self):
        self.face_cascade  = None
        self.smile_cascade = None
        self.eye_cascade   = None
        self.ok            = False
        self.emotion_window= None
        self._emo_lock     = threading.Lock()

        try:
            cp = cv2.data.haarcascades
            self.face_cascade = cv2.CascadeClassifier(
                cp + 'haarcascade_frontalface_default.xml')
            self.smile_cascade= cv2.CascadeClassifier(
                cp + 'haarcascade_smile.xml')
            self.eye_cascade  = cv2.CascadeClassifier(
                cp + 'haarcascade_eye.xml')

            if (not self.face_cascade.empty() and
                not self.smile_cascade.empty()):
                self.ok = True
                print("✅ Emotion detector ready (300x300)")
        except Exception as e:
            print(f"⚠️  EmotionDetector: {e}")

    def analyze(self, frame):
        """Analyze frame, update STATE, return scores"""
        if frame is None or not self.ok:
            return {}

        # Resize to 300x300 for processing
        small = cv2.resize(frame, (300, 300))
        gray  = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        # Enhance contrast
        gray  = cv2.equalizeHist(gray)

        scores   = {}
        face_found = False

        # Detect faces
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.05,  # more sensitive
            minNeighbors=3,    # lower = more sensitive
            minSize=(20,20),
            flags=cv2.CASCADE_SCALE_IMAGE)

        if len(faces) > 0:
            face_found = True
            STATE["attention"] = min(
                100, STATE["attention"] + 3)

            # Largest face
            x,y,w,h = sorted(faces,
                key=lambda f: f[2]*f[3], reverse=True)[0]
            roi_gray  = gray[y:y+h, x:x+w]
            roi_color = small[y:y+h, x:x+w]

            # Smile detection (high sensitivity)
            smiles = self.smile_cascade.detectMultiScale(
                roi_gray,
                scaleFactor=1.5,
                minNeighbors=8,   # lower = more sensitive
                minSize=(15,15))

            # Eye detection
            eyes = self.eye_cascade.detectMultiScale(
                roi_gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(10,10))

            n_smiles = len(smiles)
            n_eyes   = len(eyes)

            # Brightness analysis
            brightness = np.mean(roi_gray)

            # Build emotion scores
            if n_smiles > 0:
                smile_conf = min(1.0, n_smiles * 0.4)
                scores = {
                    "happy":   0.50 + smile_conf * 0.30,
                    "neutral": 0.25,
                    "surprise":0.15,
                    "sad":     0.05,
                    "angry":   0.05,
                }
            elif n_eyes >= 2:
                # Eyes open = alert
                if brightness > 140:
                    scores = {
                        "neutral": 0.55,
                        "happy":   0.25,
                        "surprise":0.10,
                        "sad":     0.05,
                        "fear":    0.05,
                    }
                else:
                    scores = {
                        "sad":     0.40,
                        "neutral": 0.30,
                        "fear":    0.15,
                        "angry":   0.10,
                        "disgust": 0.05,
                    }
            elif n_eyes == 1:
                scores = {
                    "neutral": 0.45,
                    "sad":     0.25,
                    "fear":    0.20,
                    "angry":   0.10,
                }
            else:
                scores = {
                    "angry":   0.35,
                    "disgust": 0.25,
                    "sad":     0.20,
                    "neutral": 0.15,
                    "fear":    0.05,
                }

            # Draw on 300x300 emotion window
            self._draw_emotion_window(small, faces,
                                       smiles, eyes, scores)
        else:
            STATE["face_detected"] = False
            STATE["attention"] = max(
                0, STATE["attention"] - 2)
            scores = {"neutral": 1.0}

        # Update state
        if scores:
            dominant = max(scores, key=scores.get)
            old_em   = STATE["emotion"]
            STATE["emotion"]        = dominant
            STATE["emotion_scores"] = scores
            STATE["face_detected"]  = face_found

            pos = scores.get("happy",0)+scores.get("surprise",0)
            neg = scores.get("sad",0)+scores.get("angry",0)+\
                  scores.get("fear",0)
            if pos > 0.5:   STATE["engagement"] = "high"
            elif neg > 0.5: STATE["engagement"] = "distressed"
            else:           STATE["engagement"] = "moderate"

        return scores

    def _draw_emotion_window(self, frame, faces,
                              smiles, eyes, scores):
        """Draw 300x300 dedicated emotion window"""
        disp = frame.copy()
        # Draw face boxes
        for (x,y,w,h) in faces:
            em  = STATE["emotion"]
            col = EMO_COLORS.get(em, (180,180,180))
            cv2.rectangle(disp,(x,y),(x+w,y+h),col,2)
            # Emotion label
            cv2.putText(disp, em.upper(),
                (x, y-8), cv2.FONT_HERSHEY_SIMPLEX,
                0.55, col, 2)
        # Draw eyes
        for (ex,ey,ew,eh) in eyes[:2]:
            cv2.circle(disp,
                (faces[0][0]+ex+ew//2,
                 faces[0][1]+ey+eh//2),
                ew//2, (255,255,0), 1)
        # Draw smiles
        for (sx,sy,sw,sh) in smiles[:1]:
            cv2.rectangle(disp,
                (faces[0][0]+sx,faces[0][1]+sy),
                (faces[0][0]+sx+sw,faces[0][1]+sy+sh),
                (0,255,100),1)

        # Score bars (right side)
        bx = 5
        for i,(em,sc) in enumerate(
                sorted(scores.items(),key=lambda x:-x[1])):
            y   = 10 + i*28
            bl  = int(sc * 120)
            col = EMO_COLORS.get(em,(150,150,150))
            cv2.rectangle(disp,(bx,y),(bx+bl,y+18),col,-1)
            cv2.putText(disp,f"{em[:4]}:{sc:.0%}",
                (bx+2,y+13),
                cv2.FONT_HERSHEY_SIMPLEX,0.35,
                (255,255,255),1)

        # Header
        cv2.rectangle(disp,(0,0),(300,22),(0,0,0),-1)
        cv2.putText(disp,"EMOTION DETECTOR (300x300)",
            (3,15),cv2.FONT_HERSHEY_SIMPLEX,
            0.38,(0,200,255),1)

        # Attention bar at bottom
        att = STATE["attention"]
        bw  = int(att/100*298)
        cv2.rectangle(disp,(0,285),(298,299),(30,30,60),-1)
        col = EMO_COLORS.get(STATE["emotion"],(180,180,180))
        cv2.rectangle(disp,(0,285),(bw,299),col,-1)
        cv2.putText(disp,f"Att:{att}%",
            (3,297),cv2.FONT_HERSHEY_SIMPLEX,
            0.32,(255,255,255),1)

        with self._emo_lock:
            self.emotion_window = disp.copy()

    def get_window(self):
        with self._emo_lock:
            return self.emotion_window.copy() \
                if self.emotion_window is not None else None

# ============================================================
# CAMERA MANAGER
# ============================================================
class Camera:
    def __init__(self):
        self.cap   = None
        self.idx   = -1
        self.frame = None
        self._lock = threading.Lock()

        for i in [1, 0, 2, 3, 4]:
            try:
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    ret, f = cap.read()
                    if ret and f is not None and f.size > 0:
                        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                        cap.set(cv2.CAP_PROP_FPS, 30)
                        cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)
                        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)
                        self.cap = cap
                        self.idx = i
                        print(f"✅ Camera: index {i}")
                        break
                    cap.release()
            except: pass

        if self.idx < 0:
            print("⚠️  No camera - simulation mode")

    def read(self):
        if not self.cap:
            return False, None
        ret, frame = self.cap.read()
        if ret and frame is not None:
            frame = cv2.flip(frame, 1)
            with self._lock:
                self.frame = frame.copy()
            return True, frame
        return False, None

    def get_frame(self):
        with self._lock:
            return self.frame.copy() \
                if self.frame is not None else None

# ============================================================
# VOICE ENGINE
# ============================================================
class Voice:
    def __init__(self):
        self.ok    = False
        self._lock = threading.Lock()
        self._queue= []
        try:
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', 128)
            self.engine.setProperty('volume', 1.0)
            for v in self.engine.getProperty('voices'):
                if any(x in v.name.lower()
                       for x in ['female','zira','hazel','karen']):
                    self.engine.setProperty('voice', v.id)
                    break
            self.ok = True
            print("✅ Voice ready (rate=128)")
        except Exception as e:
            print(f"⚠️  Voice: {e}")

    def say(self, text):
        name = STATE.get("child_name") or "Friend"
        text = str(text).replace("{name}", name)
        # Strip tokens
        for tok in ["[WAVE]","[CLAP]","[NOD]",
                    "[DANCE]","[POINT]","[HUG]","[GAME]"]:
            text = text.replace(tok, "")
        text = re.sub(r'\[YOUTUBE:[^\]]+\]','',text)
        text = re.sub(r'\[IMAGE:[^\]]+\]','',text)
        text = text.strip()
        if not text: return

        STATE["is_speaking"] = True
        print(f"\n🔊 Pepper: {text}")

        if self.ok:
            with self._lock:
                try:
                    self.engine.say(text)
                    self.engine.runAndWait()
                except Exception as e:
                    print(f"⚠️  TTS: {e}")
        STATE["is_speaking"] = False

# ============================================================
# HIGH-SENSITIVITY MICROPHONE (energy=20)
# ============================================================
class Mic:
    def __init__(self):
        self.ok      = False
        self.running = False
        try:
            self.r = sr.Recognizer()
            # MAXIMUM SENSITIVITY
            self.r.energy_threshold               = 20
            self.r.dynamic_energy_threshold       = True
            self.r.dynamic_energy_adjustment_ratio= 1.5
            self.r.pause_threshold                = 0.4
            self.r.phrase_threshold               = 0.1
            self.r.non_speaking_duration          = 0.1
            self.ok = True
            print("✅ Mic (energy=20, MAX sensitivity)")
        except Exception as e:
            print(f"⚠️  Mic: {e}")

    def listen(self, timeout=5):
        if not self.ok:
            return input("👶 Type: ").strip()
        try:
            with sr.Microphone() as src:
                self.r.adjust_for_ambient_noise(src, 0.15)
                audio = self.r.listen(
                    src, timeout=timeout,
                    phrase_time_limit=15)
            try:
                text = self.r.recognize_google(
                    audio, language="en-US")
                STATE["last_sound"] = time.time()
                add_log(f"Heard: {text}")
                return text
            except sr.UnknownValueError:
                self._clap_check(audio)
                STATE["last_sound"] = time.time()
                return "[sound]"
            except sr.RequestError:
                return ""
        except sr.WaitTimeoutError:
            return ""
        except Exception:
            return ""

    def _clap_check(self, audio):
        try:
            raw = np.frombuffer(
                audio.get_raw_data(), np.int16)
            rms = float(np.sqrt(
                np.mean(raw.astype(np.float64)**2)))
            if rms > 1200:
                STATE["clap_detected"] = True
                add_log("👏 Clap!", "success")
        except: pass

    def get_name(self, voice):
        if STATE["child_known"]:
            return STATE["child_name"]
        voice.say("Hello! I am Pepper! What is your name?")
        for _ in range(3):
            r = self.listen(8)
            if r and r != "[sound]":
                n = self._extract(r)
                if n:
                    STATE["child_name"]  = n
                    STATE["child_known"] = True
                    add_log(f"Name: {n}", "success")
                    return n
        STATE["child_name"]  = "Friend"
        STATE["child_known"] = True
        return "Friend"

    def _extract(self, text):
        t = text.lower()
        for rm in ["my name is","i am","i'm",
                   "call me","name is"]:
            t = t.replace(rm,"").strip()
        w = t.split()
        return w[0].capitalize() if w else None

    def listen_bg(self, callback):
        def _loop():
            self.running = True
            while self.running:
                if STATE["is_speaking"]:
                    time.sleep(0.2)
                    continue
                text = self.listen(4)
                if text:
                    try: callback(text)
                    except Exception as e:
                        print(f"⚠️  callback: {e}")
                time.sleep(0.05)
        threading.Thread(target=_loop, daemon=True).start()

# ============================================================
# ACTION TOKENS
# ============================================================
class Actions:
    def __init__(self, pepper=None):
        self.pepper = pepper

    def process(self, text):
        clean = text
        for tok,fn in [
            ("[WAVE]",  self._wave),
            ("[CLAP]",  self._clap),
            ("[NOD]",   self._nod),
            ("[DANCE]", self._dance),
            ("[POINT]", self._point),
            ("[HUG]",   self._hug),
        ]:
            if tok in text:
                clean = clean.replace(tok,"")
                threading.Thread(
                    target=fn, daemon=True).start()

        yt = re.search(r'\[YOUTUBE:\s*(.+?)\]', text)
        if yt:
            clean = clean.replace(yt.group(0),"")
            q = yt.group(1).strip()
            url = ("https://www.youtube.com/results?"
                   "search_query="+urllib.parse.quote(
                       q+" autism children educational"))
            webbrowser.open(url)
            add_log(f"📺 YouTube: {q}")

        img = re.search(r'\[IMAGE:\s*(.+?)\]', text)
        if img:
            clean = clean.replace(img.group(0),"")
            webbrowser.open("https://www.google.com/search?"
                "tbm=isch&q="+urllib.parse.quote(
                    img.group(1).strip()))

        if "[GAME]" in text:
            clean = clean.replace("[GAME]","")
            webbrowser.open("http://localhost:5007")
            add_log("🎮 Game!")

        return clean.strip()

    def _sa(self, j, a, s=0.15):
        if self.pepper:
            try: self.pepper.setAngles(j,a,s)
            except: pass

    def _wave(self):
        self._sa("RShoulderPitch",0.2,0.2)
        self._sa("RElbowRoll",0.8,0.2)
        time.sleep(0.3)
        for _ in range(3):
            self._sa("RWristYaw",0.5,0.25); time.sleep(0.2)
            self._sa("RWristYaw",-0.5,0.25); time.sleep(0.2)
        self._sa("RShoulderPitch",1.0,0.15)

    def _clap(self):
        for _ in range(4):
            self._sa("LShoulderPitch",0.8,0.25)
            self._sa("RShoulderPitch",0.8,0.25); time.sleep(0.18)
            self._sa("LShoulderPitch",1.1,0.25)
            self._sa("RShoulderPitch",1.1,0.25); time.sleep(0.18)

    def _nod(self):
        for _ in range(2):
            self._sa("HeadPitch",0.3,0.2); time.sleep(0.3)
            self._sa("HeadPitch",-0.1,0.2); time.sleep(0.3)
        self._sa("HeadPitch",0.0,0.15)

    def _dance(self):
        for _ in range(4):
            self._sa("LShoulderPitch",0.2,0.2)
            self._sa("RShoulderPitch",0.9,0.2)
            self._sa("HeadYaw",0.3,0.2); time.sleep(0.25)
            self._sa("LShoulderPitch",0.9,0.2)
            self._sa("RShoulderPitch",0.2,0.2)
            self._sa("HeadYaw",-0.3,0.2); time.sleep(0.25)
        self._sa("HeadYaw",0,0.1)

    def _point(self):
        self._sa("LShoulderPitch",0.1,0.15)
        self._sa("LElbowYaw",-1.5,0.15); time.sleep(1.0)
        self._sa("LShoulderPitch",1.0,0.15)

    def _hug(self):
        self._sa("LShoulderPitch",0.5,0.1)
        self._sa("RShoulderPitch",0.5,0.1)
        self._sa("LShoulderRoll",0.3,0.1)
        self._sa("RShoulderRoll",-0.3,0.1); time.sleep(1.2)
        self._sa("LShoulderPitch",1.0,0.1)
        self._sa("RShoulderPitch",1.0,0.1)
        self._sa("LShoulderRoll",0.0,0.1)
        self._sa("RShoulderRoll",0.0,0.1)

# ============================================================
# VIDEO UI - SAFE THREADING (no crash)
# ============================================================
class VideoUI:
    def __init__(self, em_det, camera):
        self.em   = em_det
        self.cam  = camera
        self.running   = False
        self.task_text = ""
        self.task_t    = 0
        self.praise_t  = 0
        self.praise_text = ""
        self.gemini_text = ""
        self.gemini_t  = 0
        self.last_em   = 0
        self.avatar    = self._avatar()
        self._ui_lock  = threading.Lock()

        # Start in main-safe thread
        self.running = True
        self._thread = threading.Thread(
            target=self._run, daemon=True)
        self._thread.start()
        print("✅ Video UI started!")

    def _avatar(self):
        img = np.zeros((220,170,3),dtype=np.uint8)
        img[:] = (12,18,40)
        cv2.circle(img,(85,55),42,(220,195,175),-1)
        for ex in [70,100]:
            cv2.circle(img,(ex,48),9,(0,140,255),-1)
            cv2.circle(img,(ex,48),4,(255,255,255),-1)
            cv2.circle(img,(ex+1,47),2,(0,0,0),-1)
        cv2.ellipse(img,(85,68),(13,6),0,0,180,(80,40,40),2)
        cv2.rectangle(img,(55,95),(115,175),(130,140,190),-1)
        cv2.rectangle(img,(20,100),(55,132),(130,140,190),-1)
        cv2.rectangle(img,(115,100),(150,132),(130,140,190),-1)
        cv2.putText(img,"PEPPER",(28,200),
            cv2.FONT_HERSHEY_SIMPLEX,0.6,(80,180,255),2)
        cv2.putText(img,"Gemini AI",(25,215),
            cv2.FONT_HERSHEY_SIMPLEX,0.35,(150,220,255),1)
        return img

    def _run(self):
        """Main camera loop - SAFE"""
        no_cam = self.cam.idx < 0
        em_win_x = None  # position of emotion window

        while self.running:
            try:
                # Read camera
                if no_cam:
                    frame = self._sim_frame()
                else:
                    ret, f = self.cam.read()
                    frame  = f if ret else self._sim_frame()

                # Analyze emotion every 0.7s
                now = time.time()
                if now - self.last_em > 0.7:
                    self.last_em = now
                    fc = frame.copy()
                    threading.Thread(
                        target=self.em.analyze,
                        args=(fc,), daemon=True).start()

                # Build main UI
                ui = self._build(frame)

                # Show main window
                cv2.imshow("Pepper Therapy", ui)

                # Show 300x300 emotion window
                em_win = self.em.get_window()
                if em_win is not None:
                    cv2.imshow("Emotion Detection (300x300)",
                               em_win)

                key = cv2.waitKey(1) & 0xFF
                if key in [ord('q'),ord('Q'),27]:
                    self.running = False
                    break

            except Exception as e:
                print(f"⚠️  UI: {e}")
                time.sleep(0.1)

            time.sleep(0.02)

        try: cv2.destroyAllWindows()
        except: pass

    def _sim_frame(self):
        h,w = 720,1280
        f   = np.zeros((h,w,3),dtype=np.uint8)
        f[:] = (8,12,28)
        for i in range(0,w,100):
            cv2.line(f,(i,0),(i,h),(18,24,50),1)
        for i in range(0,h,100):
            cv2.line(f,(0,i),(w,i),(18,24,50),1)
        t = time.time()
        r = int(35 + 12*math.sin(t*2))
        cv2.circle(f,(w//2,h//2-60),r,
            (int(50+50*math.sin(t)),
             int(100+100*math.cos(t)),220),3)
        cv2.putText(f,"SIMULATION - NO CAMERA",
            (w//2-170,h//2+40),
            cv2.FONT_HERSHEY_SIMPLEX,0.8,(100,150,255),2)
        return f

    def _build(self, frame):
        h,w = frame.shape[:2]
        ui  = frame.copy()

        # Header
        ov = ui.copy()
        cv2.rectangle(ov,(0,0),(w,78),(8,12,28),-1)
        ui = cv2.addWeighted(ov,0.82,ui,0.18,0)

        name  = STATE["child_name"]
        prot  = STATE["protocol"]
        score = STATE["score"]
        diff  = STATE["difficulty"].upper()
        gem   = "✅" if STATE["gemini_ok"] else "⚠️"

        cv2.putText(ui,
            f"Pepper Gemini Therapy  {gem} Gemini",
            (15,30),cv2.FONT_HERSHEY_SIMPLEX,
            0.75,(255,255,255),2)
        cv2.putText(ui,
            f"Child:{name}  Protocol:{prot}  "
            f"Score:{score}  Level:{diff}  "
            f"Port:5007",
            (15,60),cv2.FONT_HERSHEY_SIMPLEX,
            0.46,(140,190,255),1)

        # Pepper avatar PIP
        av   = self.avatar.copy()
        ah,aw= av.shape[:2]
        if STATE["is_speaking"]:
            t  = int(time.time()*6)%4
            cv2.rectangle(av,(0,0),(aw-1,ah-1),
                (0,160+t*20,255),2+t//2)
            # Animate mouth
            off = int(3*math.sin(time.time()*10))
            cv2.ellipse(av,(85,68+off),(13,6+off),
                0,0,180,(80,40,40),2)

        x1 = w-aw-12; y1 = h-ah-88
        ui[y1-2:y1+ah+2,x1-2:x1+aw+2] = (12,18,40)
        ui[y1:y1+ah,x1:x1+aw] = av
        bc = (0,200,255) if STATE["is_speaking"] \
             else (50,50,90)
        cv2.rectangle(ui,(x1-2,y1-2),
            (x1+aw+2,y1+ah+2),bc,2)

        # Bottom bar
        ov2 = ui.copy()
        cv2.rectangle(ov2,(0,h-88),(w,h),(8,12,28),-1)
        ui  = cv2.addWeighted(ov2,0.78,ui,0.22,0)

        em  = STATE["emotion"]
        ec  = EMO_COLORS.get(em,(180,180,180))
        att = STATE["attention"]

        cv2.putText(ui,f"Emotion: {em.upper()}",
            (15,h-58),cv2.FONT_HERSHEY_SIMPLEX,
            0.75,ec,2)
        # Attention bar
        bw2 = int(att/100*(w-200))
        cv2.rectangle(ui,(15,h-42),(w-185,h-32),
            (30,30,60),-1)
        cv2.rectangle(ui,(15,h-42),(15+bw2,h-32),ec,-1)
        cv2.putText(ui,
            f"Attention:{att}%  Engagement:{STATE['engagement']}",
            (15,h-15),cv2.FONT_HERSHEY_SIMPLEX,
            0.46,(255,230,100),1)

        # Prompt level
        pl   = STATE["prompt_level"]
        plc  = [(0,200,0),(200,200,0),(200,100,0),(200,0,0)][min(pl,3)]
        cv2.circle(ui,(w-48,h-52),20,plc,-1)
        cv2.putText(ui,f"P{pl}",
            (w-56,h-44),cv2.FONT_HERSHEY_SIMPLEX,
            0.62,(255,255,255),2)

        # Face detection dot
        fdc = (0,255,0) if STATE["face_detected"] else (0,0,255)
        cv2.circle(ui,(w-12,18),7,fdc,-1)

        # Task
        now = time.time()
        if self.task_text and now-self.task_t < 7:
            tl = min(len(self.task_text)*13,w-60)
            tx = max(10,w//2-tl//2)
            cv2.rectangle(ui,(tx-5,h//2-42),
                (tx+tl+5,h//2+8),(15,50,120),-1)
            cv2.rectangle(ui,(tx-5,h//2-42),
                (tx+tl+5,h//2+8),(0,140,255),2)
            cv2.putText(ui,self.task_text[:55],
                (tx,h//2-12),cv2.FONT_HERSHEY_SIMPLEX,
                0.68,(255,255,255),2)

        # Praise
        if self.praise_text and now-self.praise_t < 4:
            pl2 = min(len(self.praise_text)*17,w-60)
            px  = max(10,w//2-pl2//2)
            cv2.rectangle(ui,(px-5,h//2+28),
                (px+pl2+5,h//2+74),(0,70,0),-1)
            cv2.putText(ui,self.praise_text[:38],
                (px,h//2+60),cv2.FONT_HERSHEY_SIMPLEX,
                0.88,(0,255,100),2)

        # Gemini text preview
        if self.gemini_text and now-self.gemini_t < 5:
            lines = [self.gemini_text[i:i+60]
                     for i in range(0,
                     min(len(self.gemini_text),120),60)]
            for li,line in enumerate(lines[:2]):
                cv2.putText(ui,line,
                    (15,h-100-li*20),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.40,(200,255,200),1)

        # REC
        cv2.circle(ui,(36,26),8,(0,0,220),-1)
        cv2.putText(ui,"REC",(48,32),
            cv2.FONT_HERSHEY_SIMPLEX,0.42,(0,0,220),1)

        # Clap flash
        if STATE["clap_detected"]:
            cv2.putText(ui,"👏 CLAP DETECTED!",
                (w//2-100,85),cv2.FONT_HERSHEY_SIMPLEX,
                1.1,(0,255,100),3)

        return ui

    def show_task(self, t):
        self.task_text = t; self.task_t = time.time()
    def show_praise(self, t):
        self.praise_text = t; self.praise_t = time.time()
    def show_gemini(self, t):
        self.gemini_text = t[:120]
        self.gemini_t = time.time()
    def stop(self):
        self.running = False
        time.sleep(0.3)
        try: cv2.destroyAllWindows()
        except: pass

# ============================================================
# PYBULLET SIMULATION
# ============================================================
class Sim:
    def __init__(self):
        self.pepper = None
        self.ok     = False
        self.rx = self.ry = 0.0
        self.auto_walk = True
        self.balloons  = []

    def launch(self):
        try:
            from qibullet import SimulationManager as QS
            self.qisim  = QS()
            self.client = self.qisim.launchSimulation(gui=True)
            p.setRealTimeSimulation(1)
            p.setGravity(0,0,-9.81)
            p.setAdditionalSearchPath(pybullet_data.getDataPath())
            p.loadURDF("plane.urdf")
            self._room()
            self.pepper = self.qisim.spawnPepper(self.client)
            self.pepper.goToPosture("Stand",0.5)
            self._balloons()
            self._kids()
            p.resetDebugVisualizerCamera(7,45,-35,[0,0,0.5])
            self.ok = True
            for fn in [self._sim_loop,
                       self._walk_loop,self._arm_loop]:
                threading.Thread(target=fn,daemon=True).start()
            print("✅ PyBullet ready!")
            return self.pepper
        except Exception as e:
            print(f"⚠️  PyBullet: {e}")
            return None

    def _room(self):
        wc=[0.85,0.85,0.9,1]
        for pos,ext in [
            ([0,-4,1.1],[5,.1,1.1]),([0,4,1.1],[5,.1,1.1]),
            ([5,0,1.1],[.1,4,1.1]),([-5,0,1.1],[.1,4,1.1])]:
            p.createMultiBody(0,-1,
                p.createVisualShape(p.GEOM_BOX,
                    halfExtents=ext,rgbaColor=wc),pos)
        p.createMultiBody(0,-1,
            p.createVisualShape(p.GEOM_BOX,
                halfExtents=[4.5,3.5,.02],
                rgbaColor=[.5,.4,.3,1]),[0,0,.01])
        for txt,pos in [
            ("ABA",[-4,3,2]),("DTT",[4,3,2]),
            ("TEACCH",[0,4,2]),("TIE",[-4,-3,2])]:
            p.addUserDebugText(txt,pos,
                [.4,.5,.9],textSize=1.2,lifeTime=0)

    def _balloons(self):
        cols=[[1,.2,.2,1],[.2,1,.2,1],[.2,.2,1,1],
              [1,1,.2,1],[1,.5,.2,1],[.8,.2,.8,1]]
        for i in range(8):
            vs=p.createVisualShape(p.GEOM_SPHERE,
               radius=.15,rgbaColor=cols[i%len(cols)])
            bid=p.createMultiBody(0,-1,vs,
               [random.uniform(-3,3),
                random.uniform(-2,2),
                random.uniform(.8,2.2)])
            self.balloons.append({
                "id":bid,"x":random.uniform(-3,3),
                "y":random.uniform(-2,2),
                "z":random.uniform(.8,2.2),
                "spd":random.uniform(.01,.03)})

    def _kids(self):
        for nm,pos,col in [
            ("Ahmed",[1.5,-1.2,0],[.2,.85,.2,1]),
            ("Sara",[-1.2,1.3,0],[1.,.6,.0,1]),
            ("Yusuf",[.5,-2.,0],[.9,.15,.15,1])]:
            p.createMultiBody(0,-1,
                p.createVisualShape(p.GEOM_BOX,
                    halfExtents=[.13,.09,.21],rgbaColor=col),
                [pos[0],pos[1],.41])
            p.createMultiBody(0,-1,
                p.createVisualShape(p.GEOM_SPHERE,
                    radius=.11,rgbaColor=[1.,.82,.65,1.]),
                [pos[0],pos[1],.74])
            p.addUserDebugText(nm,[pos[0],pos[1],1.05],
                [0,0,0],textSize=.85,lifeTime=0)

    def _sim_loop(self):
        while True:
            p.stepSimulation()
            for b in self.balloons:
                b["z"]+=b["spd"]
                if b["z"]>2.8:
                    b["z"]=.6
                    b["x"]=random.uniform(-3,3)
                    b["y"]=random.uniform(-2,2)
                try:
                    p.resetBasePositionAndOrientation(
                        b["id"],[b["x"],b["y"],b["z"]],
                        [0,0,0,1])
                except: pass
            time.sleep(1/240.)

    def _walk_loop(self):
        t=0
        while True:
            if self.auto_walk:
                t+=.015
                self.rx+=.018*math.cos(t*.4)
                self.ry+=.018*math.sin(t*.5)
                self.rx=max(-3.5,min(3.5,self.rx))
                self.ry=max(-2.8,min(2.8,self.ry))
                try:
                    self.pepper.setPosition(
                        [self.rx,self.ry,.8])
                except: pass
            time.sleep(.06)

    def _arm_loop(self):
        ph=0
        while True:
            try:
                if STATE["is_speaking"]:
                    ph+=.07
                    L=.5+.3*math.sin(ph)
                    R=.5+.3*math.sin(ph+math.pi*.6)
                    self.pepper.setAngles(
                        "LShoulderPitch",L,.07)
                    self.pepper.setAngles(
                        "RShoulderPitch",R,.07)
                else:
                    self.pepper.setAngles(
                        "LShoulderPitch",1.,.04)
                    self.pepper.setAngles(
                        "RShoulderPitch",1.,.04)
            except: pass
            time.sleep(.04)

    def show_text(self, text):
        if not self.ok: return
        try:
            pos=p.getBasePositionAndOrientation(
                self.pepper.body)[0]
            p.addUserDebugText(text[:55],
                [pos[0],pos[1],pos[2]+1.3],
                [0,0,0],textSize=.85,lifeTime=5)
        except: pass

# ============================================================
# FLASK DASHBOARD - PORT 5007 - WITH CHARTS
# ============================================================
flask_app = Flask(__name__)

DASHBOARD = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>🤖 Pepper Parent Dashboard</title>
<meta http-equiv="refresh" content="3">
<script src="https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js"></script>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',sans-serif;
     background:#060912;color:#e0e6ff;font-size:14px}
.hdr{background:linear-gradient(135deg,#0a0f28,#1a0a3d);
     padding:14px 22px;display:flex;
     align-items:center;gap:12px;
     border-bottom:2px solid #4f46e5}
.hdr h1{font-size:1.2em;color:#a78bfa}
.live{background:#ef4444;color:#fff;padding:2px 8px;
      border-radius:12px;font-size:.7em;
      animation:blink 1s infinite}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.3}}
.gem{background:#1a2555;color:#60a5fa;
     padding:3px 9px;border-radius:10px;font-size:.68em;
     border:1px solid #3b82f6}
.cont{max-width:1300px;margin:0 auto;padding:14px;
      display:grid;grid-template-columns:1fr 1fr 1fr;
      gap:12px}
.full{grid-column:1/-1}
.two{grid-column:span 2}
.card{background:#0c0f1e;border-radius:11px;
      padding:14px;border:1px solid #1a1f40}
.card h2{font-size:.82em;color:#818cf8;
         border-bottom:1px solid #1a1f40;
         padding-bottom:6px;margin-bottom:10px;
         display:flex;align-items:center;gap:6px}
/* Stats */
.stats{display:grid;grid-template-columns:repeat(5,1fr);
       gap:10px;margin-bottom:12px}
.stat{background:linear-gradient(135deg,#0d1030,#1a0a3d);
      border:1px solid #312e81;border-radius:9px;
      padding:12px;text-align:center}
.n{font-size:1.9em;font-weight:700;color:#a78bfa}
.l{font-size:.7em;color:#6b7280;margin-top:2px}
/* Emotion */
.emo{display:inline-block;padding:5px 14px;
     border-radius:15px;font-weight:700;font-size:1.1em}
.happy{background:#05291555;color:#34d399;border:1px solid #34d399}
.sad{background:#1e3a5f55;color:#60a5fa;border:1px solid #60a5fa}
.angry{background:#45090a55;color:#f87171;border:1px solid #f87171}
.neutral{background:#1f293755;color:#9ca3af;border:1px solid #9ca3af}
.fear{background:#1c190055;color:#fbbf24;border:1px solid #fbbf24}
.surprise{background:#2e106555;color:#c084fc;border:1px solid #c084fc}
/* Bars */
.bar-bg{background:#1f2937;border-radius:7px;
        height:10px;margin:5px 0}
.bar{height:10px;border-radius:7px;
     background:linear-gradient(90deg,#6366f1,#a78bfa)}
/* Buttons */
.btn{background:linear-gradient(135deg,#4f46e5,#7c3aed);
     color:#fff;border:none;padding:7px 13px;
     border-radius:7px;cursor:pointer;font-size:.78em;
     margin:3px;transition:.2s;display:inline-block}
.btn:hover{opacity:.85}
.btn-g{background:linear-gradient(135deg,#059669,#10b981)}
.btn-y{background:linear-gradient(135deg,#d97706,#f59e0b)}
.btn-r{background:linear-gradient(135deg,#dc2626,#ef4444)}
/* Log */
.log-box{max-height:280px;overflow-y:auto}
.log{padding:5px 8px;margin:2px 0;border-radius:5px;
     font-size:.74em;border-left:3px solid #4f46e5;
     background:#07090f;line-height:1.4}
.log.success{border-color:#10b981}
.log.fail{border-color:#ef4444}
.log.info{border-color:#3b82f6}
/* Protocol */
.prot{display:inline-block;padding:2px 7px;
      border-radius:8px;font-size:.68em;font-weight:700}
.ABA{background:#1e1b4b55;color:#818cf8}
.DTT{background:#2e1b0055;color:#fb923c}
.TEACCH{background:#05291555;color:#34d399}
.TIE{background:#2e106555;color:#c084fc}
.GREETING{background:#1e3a5f55;color:#60a5fa}
/* Input */
input,textarea{width:100%;padding:7px 10px;border-radius:6px;
      border:1px solid #374151;background:#07090f;
      color:#e0e6ff;font-size:.8em;font-family:inherit}
textarea{resize:vertical;min-height:70px}
/* Notes */
.note{background:#0a1020;border-left:3px solid #818cf8;
      padding:8px 10px;margin:4px 0;border-radius:0 6px 6px 0;
      font-size:.75em;line-height:1.5}
/* Chart container */
.chart-wrap{position:relative;height:180px;
            background:#07090f;border-radius:8px;
            padding:8px}
/* Help section */
.help-item{background:#0a1020;border-radius:8px;
           padding:10px;margin:6px 0;
           border-left:4px solid #a78bfa}
.help-title{color:#a78bfa;font-weight:700;
            font-size:.82em;margin-bottom:4px}
.help-text{color:#9ca3af;font-size:.76em;line-height:1.5}
.tip{background:#051a0f;border:1px solid #10b981;
     border-radius:6px;padding:8px;margin:4px 0;
     font-size:.74em;color:#6ee7b7}
/* Chat */
#chat-box{height:200px;overflow-y:auto;
          background:#07090f;border-radius:8px;
          padding:10px;margin-bottom:8px}
.chat-msg{padding:6px 10px;margin:4px 0;
          border-radius:8px;font-size:.8em;line-height:1.5}
.chat-pepper{background:#1e1b4b;border-left:3px solid #818cf8}
.chat-parent{background:#052918;border-left:3px solid #10b981;
             text-align:right}
</style>
</head>
<body>

<div class="hdr">
  <div style="font-size:1.8em">🤖</div>
  <div>
    <h1>Pepper Parent Dashboard — Port 5007</h1>
    <p style="font-size:.78em;opacity:.8">
      Child: <b>{{s.child_name}}</b> |
      <span class="prot {{s.protocol}}">{{s.protocol}}</span> |
      {{s.difficulty.upper()}} | Started: {{s.session_start}}
    </p>
  </div>
  <span class="live">● LIVE</span>
  <span class="gem" id="gem-status">
    {% if s.gemini_ok %}⚡ Gemini AI Active
    {% else %}⚠️ Gemini Offline{% endif %}
  </span>
</div>

<div style="max-width:1300px;margin:0 auto;padding:14px">

  <!-- STATS ROW -->
  <div class="stats">
    <div class="stat">
      <div class="n" id="score">{{s.score}}</div>
      <div class="l">🏆 Score</div>
    </div>
    <div class="stat">
      <div class="n" id="att">{{s.attention}}%</div>
      <div class="l">👀 Attention</div>
    </div>
    <div class="stat">
      <div class="n">P{{s.prompt_level}}</div>
      <div class="l">💡 Prompt Level</div>
    </div>
    <div class="stat">
      <div class="n">{{s.consecutive}}</div>
      <div class="l">🔥 Streak</div>
    </div>
    <div class="stat">
      <div class="n">{{s.logs|length}}</div>
      <div class="l">💬 Interactions</div>
    </div>
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr 1fr;
              gap:12px;margin-bottom:12px">

    <!-- EMOTION -->
    <div class="card">
      <h2>😊 Live Emotion Stream</h2>
      <div style="text-align:center;padding:8px">
        <div class="emo {{s.emotion}}">
          {{s.emotion.upper()}}
        </div>
        <div style="margin:10px 0">
          <div style="font-size:.75em;color:#6b7280">
            Attention</div>
          <div class="bar-bg">
            <div class="bar"
                 style="width:{{s.attention}}%"></div>
          </div>
          <span style="font-size:.75em;color:#818cf8">
            {{s.attention}}%</span>
        </div>
        <div style="font-size:.78em;color:#6b7280">
          Engagement:
          <b style="color:#e0e6ff">{{s.engagement}}</b>
        </div>
        <div style="margin-top:5px;font-size:.72em;
          color:{{'#34d399' if s.face_detected else '#ef4444'}}">
          {{'✅ Face Detected' if s.face_detected
            else '❌ No Face - Move Closer!'}}
        </div>
        {% if s.clap_detected %}
        <div style="color:#fbbf24;font-weight:700;margin-top:5px">
          👏 CLAP DETECTED!</div>{% endif %}
        <!-- Emotion scores -->
        <div style="margin-top:10px;text-align:left">
          {% for em,sc in s.emotion_scores.items() %}
          {% if sc > 0.05 %}
          <div style="display:flex;align-items:center;
                      gap:5px;margin:3px 0">
            <span style="width:58px;font-size:.68em;
                         color:#9ca3af">{{em[:7]}}</span>
            <div style="flex:1;background:#1f2937;
                        height:8px;border-radius:4px">
              <div style="width:{{(sc*100)|int}}%;
                          height:8px;border-radius:4px;
                          background:#6366f1"></div>
            </div>
            <span style="font-size:.68em;color:#818cf8;
                         width:32px">
              {{(sc*100)|int}}%</span>
          </div>{% endif %}{% endfor %}
        </div>
      </div>
    </div>

    <!-- CONTROLS -->
    <div class="card">
      <h2>🎮 Therapy Controls</h2>
      <form method="POST" action="/cmd">
        <button class="btn" name="c" value="aba">
          📚 ABA</button>
        <button class="btn" name="c" value="dtt">
          🎯 DTT</button>
        <button class="btn" name="c" value="teacch">
          📅 TEACCH</button>
        <button class="btn" name="c" value="tie">
          🧠 TIE</button>
        <button class="btn btn-g" name="c" value="dance">
          💃 Dance!</button>
        <button class="btn btn-y" name="c" value="game">
          🎮 Game</button>
        <button class="btn btn-r" name="c" value="stop">
          ⏹ Stop</button>
      </form>

      <div style="margin-top:12px">
        <div style="font-size:.75em;color:#6b7280;
                    margin-bottom:5px">📺 Educational Videos</div>
        <div style="display:flex;flex-wrap:wrap;gap:3px">
          {% for sk in skills %}
          <form method="POST" action="/skill"
                style="display:inline">
            <button class="btn btn-y" name="s"
                    value="{{sk}}"
                    style="font-size:.68em;padding:4px 7px">
              {{sk}}</button>
          </form>{% endfor %}
        </div>
      </div>

      <div style="margin-top:10px">
        <div style="font-size:.75em;color:#6b7280;
                    margin-bottom:4px">🔍 Search Video</div>
        <form method="POST" action="/search"
              style="display:flex;gap:5px">
          <input name="q"
                 placeholder="Search educational...">
          <button class="btn">Go</button>
        </form>
      </div>

      <div style="margin-top:10px">
        <div style="font-size:.75em;color:#6b7280;
                    margin-bottom:4px">👦 Set Child Name</div>
        <form method="POST" action="/name"
              style="display:flex;gap:5px">
          <input name="n" placeholder="Child's name...">
          <button class="btn">✓</button>
        </form>
      </div>
    </div>

    <!-- LIVE CHAT WITH PEPPER -->
    <div class="card">
      <h2>💬 Live Chat with Pepper</h2>
      <div id="chat-box">
        {% for log in s.logs[-15:]|reverse %}
        {% if 'Said:' in log.msg %}
        <div class="chat-msg chat-pepper">
          <span style="color:#818cf8;font-size:.7em">
            🤖 Pepper [{{log.time}}]</span><br>
          {{log.msg.replace('Said: ','')}}
        </div>
        {% elif 'Heard:' in log.msg %}
        <div class="chat-msg chat-parent">
          <span style="color:#34d399;font-size:.7em">
            👦 Child [{{log.time}}]</span><br>
          {{log.msg.replace('Heard: ','')}}
        </div>
        {% endif %}{% endfor %}
      </div>
      <!-- Parent send message -->
      <form method="POST" action="/parent_msg"
            style="display:flex;gap:5px">
        <input name="msg"
               placeholder="Send message to child via Pepper...">
        <button class="btn btn-g">Send</button>
      </form>
    </div>
  </div>

  <!-- CHARTS ROW -->
  <div style="display:grid;grid-template-columns:1fr 1fr;
              gap:12px;margin-bottom:12px">

    <!-- Attention Chart -->
    <div class="card">
      <h2>📈 Attention Over Time</h2>
      <div class="chart-wrap">
        <canvas id="attChart"></canvas>
      </div>
    </div>

    <!-- Score Chart -->
    <div class="card">
      <h2>🏆 Score Progress</h2>
      <div class="chart-wrap">
        <canvas id="scoreChart"></canvas>
      </div>
    </div>
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr;
              gap:12px;margin-bottom:12px">

    <!-- Session Log -->
    <div class="card">
      <h2>📋 Session Log</h2>
      <div class="log-box">
        {% for log in s.logs[-30:]|reverse %}
        <div class="log {{log.type}}">
          <span style="color:#6366f1">{{log.time}}</span>
          <span class="prot {{log.protocol}}">
            {{log.protocol}}</span>
          <b style="color:#a78bfa">{{log.child}}</b>:
          {{log.msg}}
          <span style="color:#374151;font-size:.75em">
            |{{log.emotion}}</span>
        </div>{% endfor %}
      </div>
      <div style="margin-top:8px">
        <a href="/export"
           style="color:#6366f1;font-size:.76em">
          📄 Export Full Report</a>
      </div>
    </div>

    <!-- Parent Notes -->
    <div class="card">
      <h2>📝 Parent Notes & Observations</h2>
      <form method="POST" action="/add_note"
            style="margin-bottom:10px">
        <textarea name="note"
                  placeholder="Add observation about your child's behavior, progress, or concerns..."></textarea>
        <button class="btn btn-g"
                style="margin-top:6px;width:100%">
          ➕ Add Note</button>
      </form>
      <div style="max-height:180px;overflow-y:auto">
        {% for note in s.parent_notes[-10:]|reverse %}
        <div class="note">
          <span style="color:#818cf8;font-size:.7em">
            {{note.time}}</span><br>
          {{note.text}}
        </div>{% endfor %}
      </div>
    </div>
  </div>

  <!-- PARENT HELP GUIDE -->
  <div class="card">
    <h2>💡 Parent Helping Notes & ASD Therapy Guide</h2>
    <div style="display:grid;
                grid-template-columns:1fr 1fr 1fr;gap:10px">

      <div class="help-item">
        <div class="help-title">🎯 ABA - Applied Behavior Analysis</div>
        <div class="help-text">
          Break tasks into small steps. Give immediate praise
          when your child succeeds. Use tokens or stickers
          as rewards. Repeat consistently every day.
        </div>
        <div class="tip">💡 Tip: If child fails 3 times,
          switch to an easier task immediately.</div>
      </div>

      <div class="help-item">
        <div class="help-title">📚 DTT - Discrete Trial Training</div>
        <div class="help-text">
          Give one clear instruction at a time. Wait 5 seconds
          for response. Praise correct attempts even if not
          perfect. Keep sessions under 20 minutes.
        </div>
        <div class="tip">💡 Tip: Use the same words every time
          for the same task - consistency is key!</div>
      </div>

      <div class="help-item">
        <div class="help-title">📅 TEACCH - Visual Schedules</div>
        <div class="help-text">
          Create a visual daily schedule with pictures. Show
          child what comes next. Structure reduces anxiety.
          Use visual timers for transitions.
        </div>
        <div class="tip">💡 Tip: Print today's schedule and
          let child check off completed activities.</div>
      </div>

      <div class="help-item">
        <div class="help-title">⚠️ When Child Shows Distress</div>
        <div class="help-text">
          Stop all tasks immediately. Speak softly and slowly.
          Give physical space. Offer sensory toy or comfort
          item. Do NOT force eye contact.
        </div>
        <div class="tip">💡 Tip: Keep a calm-down kit with
          fidget toys, headphones, and a comfort object.</div>
      </div>

      <div class="help-item">
        <div class="help-title">👏 Reinforcement Strategies</div>
        <div class="help-text">
          Praise immediately (within 2 seconds). Be specific:
          "Great clapping!" not just "Good job!" Use child's
          preferred reward - not all children like the same things.
        </div>
        <div class="tip">💡 Tip: Find your child's TOP 3
          motivators and use them as special rewards.</div>
      </div>

      <div class="help-item">
        <div class="help-title">📊 Reading the Dashboard</div>
        <div class="help-text">
          <b>Attention &gt; 70%</b> = Child is engaged ✅<br>
          <b>Prompt Level P0</b> = Child doing great ✅<br>
          <b>Prompt Level P3</b> = Child needs support ⚠️<br>
          <b>Engagement = distressed</b> = Take a break 🛑
        </div>
        <div class="tip">💡 Tip: Screenshot the dashboard
          to share with your child's specialist.</div>
      </div>

    </div>

    <!-- Session Summary for Specialist -->
    <div style="margin-top:12px;padding:10px;
                background:#0a1020;border-radius:8px;
                border:1px solid #312e81">
      <div style="font-size:.8em;font-weight:700;
                  color:#a78bfa;margin-bottom:6px">
        📋 Session Summary (Share with Specialist)</div>
      <div style="font-size:.76em;color:#9ca3af;
                  line-height:1.8">
        Child: <b style="color:#e0e6ff">{{s.child_name}}</b> |
        Date: <b style="color:#e0e6ff">
          {{s.session_start}}</b> |
        Final Score: <b style="color:#a78bfa">
          {{s.score}}</b> |
        Interactions: <b style="color:#a78bfa">
          {{s.logs|length}}</b><br>
        Dominant Emotion: <b style="color:#e0e6ff">
          {{s.emotion}}</b> |
        Last Protocol: <b style="color:#e0e6ff">
          {{s.protocol}}</b> |
        Difficulty Reached: <b style="color:#34d399">
          {{s.difficulty.upper()}}</b><br>
        Parent Notes: <b style="color:#e0e6ff">
          {{s.parent_notes|length}} notes recorded</b>
      </div>
      <a href="/export"
         style="display:inline-block;margin-top:8px"
         class="btn btn-g">
        📥 Download Full Report (JSON)</a>
    </div>
  </div>

</div><!-- end main -->

<script>
// Chart.js charts
const attData = {{att_history|tojson}};
const scoreData = {{score_history|tojson}};
const labels = Array.from({length: attData.length},
    (_,i) => i+1);

// Attention chart
new Chart(document.getElementById('attChart'), {
    type: 'line',
    data: {
        labels: labels,
        datasets: [{
            label: 'Attention %',
            data: attData,
            borderColor: '#6366f1',
            backgroundColor: 'rgba(99,102,241,0.15)',
            tension: 0.4, fill: true,
            pointRadius: 2,
        }]
    },
    options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: {
            labels: {color:'#9ca3af', font:{size:10}} }},
        scales: {
            x: {ticks:{color:'#6b7280',font:{size:9}},
                grid:{color:'#1f2937'}},
            y: {min:0,max:100,
                ticks:{color:'#6b7280',font:{size:9}},
                grid:{color:'#1f2937'}}
        }
    }
});

// Score chart
new Chart(document.getElementById('scoreChart'), {
    type: 'bar',
    data: {
        labels: labels,
        datasets: [{
            label: 'Score',
            data: scoreData,
            backgroundColor: 'rgba(167,139,250,0.6)',
            borderColor: '#a78bfa', borderWidth: 1,
        }]
    },
    options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: {
            labels: {color:'#9ca3af', font:{size:10}} }},
        scales: {
            x: {ticks:{color:'#6b7280',font:{size:9}},
                grid:{color:'#1f2937'}},
            y: {ticks:{color:'#6b7280',font:{size:9}},
                grid:{color:'#1f2937'}}
        }
    }
});

// Auto-scroll chat
const cb = document.getElementById('chat-box');
if(cb) cb.scrollTop = cb.scrollHeight;
</script>
</body>
</html>
"""

SKILLS = ["wash face","brush teeth","wash hands","emotions",
          "colors","numbers","alphabet","animals",
          "sharing","ocean","space","eat food"]

@flask_app.route("/")
def dash():
    return render_template_string(
        DASHBOARD, s=STATE, skills=SKILLS,
        att_history=STATE["attention_history"][-30:],
        score_history=STATE["score_history"][-30:])

@flask_app.route("/update_context", methods=["POST"])
def upd():
    d = request.json or {}
    STATE["emotion"]      = d.get("emotion","neutral")
    STATE["face_detected"]= True
    return jsonify({"status":"ok"})

@flask_app.route("/cmd", methods=["POST"])
def cmd():
    STATE["sim_cmd"] = request.form.get("c","")
    return dash()

@flask_app.route("/name", methods=["POST"])
def set_name():
    n = request.form.get("n","").strip().title()
    if n:
        STATE["child_name"]  = n
        STATE["child_known"] = True
        add_log(f"Name set: {n}", "success")
    return dash()

@flask_app.route("/skill", methods=["POST"])
def skill():
    s   = request.form.get("s","")
    url = ("https://www.youtube.com/results?search_query=" +
           urllib.parse.quote(s+" autism children educational"))
    webbrowser.open(url)
    add_log(f"YouTube: {s}")
    return dash()

@flask_app.route("/search", methods=["POST"])
def search():
    q   = request.form.get("q","")
    url = ("https://www.youtube.com/results?search_query=" +
           urllib.parse.quote(q+" autism educational"))
    webbrowser.open(url)
    return dash()

@flask_app.route("/add_note", methods=["POST"])
def add_note():
    note = request.form.get("note","").strip()
    if note:
        STATE["parent_notes"].append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "text": note
        })
        add_log(f"Parent note: {note[:40]}", "info")
    return dash()

@flask_app.route("/parent_msg", methods=["POST"])
def parent_msg():
    msg = request.form.get("msg","").strip()
    if msg:
        STATE["sim_cmd"] = f"parent_msg:{msg}"
        add_log(f"Parent→Pepper: {msg}", "info")
    return dash()

@flask_app.route("/export")
def export():
    fn = f"session_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(fn,"w") as f:
        json.dump(STATE, f, indent=2, default=str)
    return jsonify({"saved":fn, "score":STATE["score"],
                    "child":STATE["child_name"]})

@flask_app.route("/report")
def report():
    return jsonify(STATE)

@flask_app.route("/api/state")
def api_state():
    return jsonify({
        "emotion":    STATE["emotion"],
        "attention":  STATE["attention"],
        "score":      STATE["score"],
        "child":      STATE["child_name"],
        "protocol":   STATE["protocol"],
    })

def run_flask():
    flask_app.run(port=5007, debug=False,
                  use_reloader=False, threaded=True)

# ============================================================
# THERAPY CONTROLLER
# ============================================================
class Therapy:
    def __init__(self, gemini, voice, mic, video, sim, actions):
        self.g = gemini
        self.v = voice
        self.m = mic
        self.ui= video
        self.s = sim
        self.a = actions
        self.running = False

    def _speak(self, text):
        clean = self.a.process(str(text))
        self.ui.show_gemini(clean)
        if self.s.ok:
            self.s.show_text(clean[:55])
        self.v.say(clean)

    def run(self):
        self.running = True
        STATE["protocol"] = "GREETING"

        # Get name
        name = self.m.get_name(self.v)
        resp = self.g.ask(
            f"Child name is {name}. "
            "Greet warmly! Use [WAVE]. Give first task.")
        self._speak(resp)
        time.sleep(0.5)

        # Background mic
        self.m.listen_bg(self._on_speech)

        # Therapy loop
        protocols = ["ABA","DTT","TEACCH","TIE"]
        p_idx     = 0
        last_em   = STATE["emotion"]
        em_t      = time.time()

        while self.running:
            # No sound check
            if time.time()-STATE["last_sound"] > 10:
                STATE["last_sound"] = time.time()
                resp = self.g.ask(
                    "Child silent 10 seconds. "
                    "Gentle fun prompt!")
                self._speak(resp)

            # Prompt level
            self._prompt_check()

            # Emotion change
            curr = STATE["emotion"]
            if curr != last_em and time.time()-em_t > 6:
                last_em = curr; em_t = time.time()
                if curr in ["sad","angry","fear"]:
                    resp = self.g.ask(
                        f"Child emotion: {curr}. React!")
                    self._speak(resp)

            # Dashboard cmd
            self._handle_cmd()

            # Protocol
            prot = protocols[p_idx%len(protocols)]
            p_idx+=1; STATE["protocol"]=prot
            self._protocol(prot)
            time.sleep(0.3)

    def _prompt_check(self):
        em  = STATE["emotion"]
        att = STATE["attention"]
        eng = STATE["engagement"]
        fd  = STATE["face_detected"]

        if fd and att>60 and em in ["happy","neutral"]:
            STATE["prompt_level"] = 0
        elif not fd or att<40:
            if STATE["prompt_level"]<1:
                STATE["prompt_level"] = 1
                self._speak(self.g.ask(
                    "Child distracted. Verbal prompt! [POINT]"))
        if eng=="distressed" and STATE["prompt_level"]<3:
            STATE["prompt_level"] = 3
            self._speak(self.g.ask(
                f"Child distressed ({em}). Calm now! [HUG]"))

    def _handle_cmd(self):
        cmd = STATE.get("sim_cmd")
        if not cmd: return
        STATE["sim_cmd"] = None

        if cmd == "dance":
            self._speak(self.g.ask("Dance celebrate! [DANCE]"))
        elif cmd == "game":
            webbrowser.open("http://localhost:5007")
            self._speak(self.g.ask("Open game! [GAME]"))
        elif cmd.startswith("parent_msg:"):
            msg = cmd[11:]
            self._speak(self.g.ask(
                f"Parent wants you to tell child: {msg}"))
        elif cmd in ["aba","dtt","teacch","tie"]:
            STATE["protocol"] = cmd.upper()
        elif cmd == "stop":
            self.s.auto_walk = False

    def _protocol(self, prot):
        name = STATE["child_name"]
        em   = STATE["emotion"]
        att  = STATE["attention"]

        if prot == "ABA":
            tasks = {
                "easy":  ["Clap hands!","Touch nose!",
                          "Wave hello!","Show happy face!"],
                "medium":["Stand up!","Touch ears!",
                          "Point door!","Count 3 fingers!"],
                "hard":  ["Say your name!",
                          "Sky color?","Name animal!"],
            }
            diff  = STATE["difficulty"]
            task  = random.choice(tasks.get(diff,tasks["easy"]))
            STATE["current_task"] = task

            resp = self.g.ask(
                f"ABA task '{task}' for {name}. "
                f"Emotion:{em} Att:{att}%")
            self._speak(resp)
            self.ui.show_task(task)

            ok = self._wait(task, 12)
            if ok:
                STATE["score"]       += 10
                STATE["consecutive"] += 1
                STATE["clap_detected"]= False
                STATE["task_done"]    = False
                resp = self.g.ask(
                    f"{name} did {task}! Celebrate! [CLAP]")
                self._speak(resp)
                self.ui.show_praise("AMAZING! ⭐")
                add_log(f"ABA: {task} ✅", "success", "ABA")

                # Level up
                if STATE["consecutive"]>=3:
                    if STATE["difficulty"]=="easy":
                        STATE["difficulty"]="medium"
                    elif STATE["difficulty"]=="medium":
                        STATE["difficulty"]="hard"
                    STATE["consecutive"]=0
                    resp = self.g.ask(
                        "Child leveled up! Celebrate hard! [DANCE]")
                    self._speak(resp)
            else:
                STATE["consecutive"]=0
                resp = self.g.ask(
                    f"{name} needs help with {task}. Retry gently.")
                self._speak(resp)
                add_log(f"ABA: {task} ❌", "fail", "ABA")
            time.sleep(2)

        elif prot=="DTT":
            resp = self.g.ask(
                f"ONE DTT trial for {name}. "
                f"Diff:{STATE['difficulty']} Em:{em}")
            self._speak(resp)
            self.ui.show_task("DTT Trial")
            ok = self._wait("DTT",10)
            if ok:
                STATE["score"]+=12
                self._speak(self.g.ask(
                    f"DTT success {name}! [CLAP]"))
                add_log("DTT ✅","success","DTT")
            else:
                add_log("DTT ❌","fail","DTT")
            time.sleep(2)

        elif prot=="TEACCH":
            resp = self.g.ask(
                f"TEACCH schedule step for {name}. Em:{em}")
            self._speak(resp)
            time.sleep(3)
            if STATE["emotion"]=="happy":
                STATE["score"]+=15
            add_log("TEACCH ✅","success","TEACCH")

        elif prot=="TIE":
            resp = self.g.ask(
                f"TIE adaptive for {name}. "
                f"Em:{em} Att:{att}% "
                f"Eng:{STATE['engagement']}")
            self._speak(resp)
            time.sleep(3)
            STATE["score"]+=8
            add_log("TIE ✅","success","TIE")

    def _wait(self, task, timeout=12):
        deadline = time.time()+timeout
        while time.time()<deadline:
            if STATE["clap_detected"] and \
               "clap" in task.lower():
                return True
            if STATE["task_done"]:
                return True
            if STATE["emotion"]=="happy" and \
               STATE["attention"]>65:
                return True
            time.sleep(0.25)
        return False

    def _on_speech(self, text):
        STATE["last_sound"] = time.time()
        if not text: return
        t    = text.lower()
        name = STATE["child_name"]

        if text == "[sound]":
            self.v.say(f"I heard you {name}! 👍")
            return

        # Name
        if not STATE["child_known"]:
            n = self.m._extract(text)
            if n:
                STATE["child_name"]  = n
                STATE["child_known"] = True
                self._speak(self.g.ask(
                    f"Child name is {n}. Welcome! [WAVE]"))
            return

        # How-to → YouTube
        if any(w in t for w in
               ["how","what is","show","what does",
                "teach","explain","what are"]):
            resp = self.g.ask(
                f"Child asked: '{text}'. "
                "Answer simply. Use [YOUTUBE:...] for video.")
            self._speak(resp)
            return

        # Game
        if any(w in t for w in
               ["play","game","fun","games"]):
            self._speak(self.g.ask(
                f"{name} wants game! [GAME]"))
            return

        # Task success
        task = STATE.get("current_task","")
        if task:
            if any(w in t for w in task.lower().split()):
                STATE["task_done"] = True

        # Gemini
        resp = self.g.ask(
            f"Child said: '{text}'. Therapy response.")
        self._speak(resp)

# ============================================================
# MAIN
# ============================================================
def main():
    print("""
╔═══════════════════════════════════════════════════╗
║  PEPPER THERAPY v3 - COMPLETE                    ║
║  Port 5007 | Charts | Notes | 300x300 Emotion    ║
╚═══════════════════════════════════════════════════╝
""")

    # Flask on port 5007
    threading.Thread(target=run_flask, daemon=True).start()
    print("✅ Dashboard: http://localhost:5007")
    time.sleep(0.8)

    # Init components
    gemini = GeminiBrain()
    voice  = Voice()
    camera = Camera()
    em_det = EmotionDetector()
    video  = VideoUI(em_det, camera)
    mic    = Mic()
    sim    = Sim()
    pepper = sim.launch()
    actions= Actions(pepper)

    time.sleep(1.5)
    STATE["child_name"] = "Friend"

    voice.say(
        "Hello! I am Pepper! Let us start therapy!")
    if pepper:
        threading.Thread(
            target=actions._wave, daemon=True).start()

    therapy = Therapy(
        gemini, voice, mic, video, sim, actions)
    threading.Thread(
        target=therapy.run, daemon=True).start()

    print("\n" + "="*50)
    print("✅ ACTIVE | Dashboard: http://localhost:5007")
    print("  Camera: 2 windows open")
    print("  Press Q in camera to quit")
    print("="*50+"\n")

    while getattr(video,'running',True):
        try:
            cmd = input("> ").strip()
            if not cmd: continue
            cl  = cmd.lower()
            if cl in ["q","exit","quit"]:
                therapy.running=False
                video.stop()
                break
            elif cl=="report":
                print(f"Score:{STATE['score']} "
                      f"Emotion:{STATE['emotion']} "
                      f"Att:{STATE['attention']}%")
            elif cl.startswith("name "):
                n = cl[5:].strip().title()
                STATE["child_name"]=n
                STATE["child_known"]=True
                voice.say(f"Hello {n}!")
            else:
                therapy._on_speech(cmd)
        except (KeyboardInterrupt, EOFError):
            break

    therapy.running = False
    voice.say("Goodbye! Great session!")
    fn = f"session_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(fn,"w") as f:
        json.dump(STATE,f,indent=2,default=str)
    print(f"📄 Saved: {fn}")

if __name__=="__main__":
    main()

