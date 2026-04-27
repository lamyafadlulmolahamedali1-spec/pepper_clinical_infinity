#!/usr/bin/env python3
"""
PEPPER MASTER STATION
- Real video/voice therapy between Pepper and child
- Knows child's name via speech
- Multi-level prompting (ABA)
- YouTube skill library
- Emotion-driven DTT/TEACCH/TIE
"""

import sys, os, time, math, random, threading, json, queue
import pybullet as p
import pybullet_data
import pyttsx3
import requests
import webbrowser
import urllib.parse
import subprocess
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string

sys.path.insert(0, '/home/lamya/pepper_duo/src')
from qibullet import SimulationManager

# ========== SHARED STATE ==========
STATE = {
    "emotion":        "neutral",
    "attention":      70,
    "engagement":     "moderate",
    "face_detected":  False,
    "child_name":     None,        # اسم الطفل الحقيقي
    "child_known":    False,       # هل عرفنا اسمه؟
    "prompt_level":   0,           # 0,1,2,3
    "session_logs":   [],
    "total_score":    0,
    "protocol":       "GREETING",
    "sim_cmd":        None,
    "session_start":  datetime.now().strftime("%H:%M"),
    "youtube_opened": False,
}

YOUTUBE_SKILLS = {
    "wash face":      "https://www.youtube.com/watch?v=6Yv5n4BQHH4",
    "brush teeth":    "https://www.youtube.com/watch?v=0QiKVLyHJNk",
    "wash hands":     "https://www.youtube.com/watch?v=d914EnpU4Fo",
    "get dressed":    "https://www.youtube.com/watch?v=8tP0BcGHiLI",
    "say hello":      "https://www.youtube.com/watch?v=vCMDJSo9HGo",
    "share toys":     "https://www.youtube.com/watch?v=bFJhKHER-tA",
    "emotions":       "https://www.youtube.com/watch?v=ub82Xb1C8os",
    "count":          "https://www.youtube.com/watch?v=0TgLtF3PMOc",
    "alphabet":       "https://www.youtube.com/watch?v=75p-N9YKqNo",
    "colors":         "https://www.youtube.com/watch?v=3a7dFKGTGzM",
    "eat healthy":    "https://www.youtube.com/watch?v=UnsGnlkFj20",
    "tie shoes":      "https://www.youtube.com/watch?v=FinRSFTzTBk",
}

def add_log(msg, log_type="info", protocol=None):
    STATE["session_logs"].append({
        "time":     datetime.now().strftime("%H:%M:%S"),
        "message":  msg,
        "type":     log_type,
        "protocol": protocol or STATE["protocol"],
        "emotion":  STATE["emotion"],
        "child":    STATE.get("child_name","Unknown"),
    })
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

# ========== FLASK DASHBOARD ==========
flask_app = Flask(__name__)

DASHBOARD = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>🤖 Pepper Master Station</title>
<meta http-equiv="refresh" content="2">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',sans-serif;background:#0a0e1a;color:#e0e6ff}
.hdr{background:linear-gradient(135deg,#1a1f3c,#2d1b69);
     padding:16px 28px;display:flex;
     align-items:center;gap:15px;
     border-bottom:1px solid #2a3060}
.hdr h1{font-size:1.3em;color:#a78bfa}
.live{background:#ef4444;color:#fff;padding:3px 9px;
      border-radius:20px;font-size:0.75em;
      animation:blink 1s infinite}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.4}}
.cont{max-width:1200px;margin:0 auto;padding:18px}
.g3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px;margin-bottom:18px}
.g2{display:grid;grid-template-columns:1.2fr 1fr;gap:14px}
.card{background:#111827;border-radius:14px;
      padding:16px;border:1px solid #1f2937}
.card h2{font-size:.88em;color:#6b7280;
         border-bottom:1px solid #1f2937;
         padding-bottom:8px;margin-bottom:12px}
.stat{background:linear-gradient(135deg,#1e1b4b,#312e81);
      border:1px solid #4338ca44;border-radius:12px;
      padding:16px;text-align:center}
.stat .n{font-size:2.3em;font-weight:700;color:#818cf8}
.stat .l{font-size:.78em;color:#6b7280;margin-top:3px}
.emo{display:inline-block;padding:7px 18px;
     border-radius:20px;font-weight:700;font-size:1.05em}
.happy{background:#052e1644;color:#34d399;border:1px solid #34d399}
.sad{background:#1e3a5f44;color:#60a5fa;border:1px solid #60a5fa}
.angry{background:#450a0a44;color:#f87171;border:1px solid #f87171}
.neutral{background:#1f293744;color:#9ca3af;border:1px solid #9ca3af}
.fear{background:#1c190044;color:#fbbf24;border:1px solid #fbbf24}
.surprise{background:#2e1065 44;color:#c084fc;border:1px solid #c084fc}
.bar-bg{background:#1f2937;border-radius:8px;height:10px;margin:6px 0}
.bar{height:10px;border-radius:8px;
     background:linear-gradient(90deg,#6366f1,#a78bfa)}
.btn{background:linear-gradient(135deg,#4f46e5,#7c3aed);
     color:#fff;border:none;padding:9px 16px;
     border-radius:8px;cursor:pointer;font-size:.85em;
     margin:3px;transition:.2s}
.btn:hover{opacity:.85}
.btn-g{background:linear-gradient(135deg,#059669,#10b981)}
.btn-r{background:linear-gradient(135deg,#dc2626,#ef4444)}
.btn-y{background:linear-gradient(135deg,#d97706,#f59e0b)}
.log-box{max-height:380px;overflow-y:auto}
.log{padding:7px 11px;margin:3px 0;border-radius:7px;
     font-size:.8em;border-left:3px solid #4f46e5;
     background:#0d1117}
.log.success{border-color:#10b981}
.log.fail{border-color:#ef4444}
.log.info{border-color:#3b82f6}
.prot{display:inline-block;padding:2px 8px;
      border-radius:10px;font-size:.75em;font-weight:700}
.GREETING{background:#1e3a5f44;color:#60a5fa}
.ABA{background:#1e1b4b44;color:#818cf8}
.DTT{background:#2e1b0044;color:#fb923c}
.TEACCH{background:#052e1644;color:#34d399}
.TIE{background:#2e1065 44;color:#c084fc}
.child-box{background:#1a1f3c;border:2px solid #6366f1;
           border-radius:12px;padding:14px;margin-bottom:14px;
           text-align:center}
.child-name{font-size:1.6em;font-weight:700;color:#a78bfa}
.prom-badge{display:inline-block;padding:5px 14px;
            border-radius:20px;font-size:.85em;font-weight:700}
.p0{background:#05293044;color:#22d3ee;border:1px solid #22d3ee}
.p1{background:#05290044;color:#86efac;border:1px solid #86efac}
.p2{background:#2e1b0044;color:#fb923c;border:1px solid #fb923c}
.p3{background:#450a0a44;color:#f87171;border:1px solid #f87171}
input[type=text]{width:100%;padding:8px 12px;
                 border-radius:8px;border:1px solid #374151;
                 background:#0d1117;color:#e0e6ff;font-size:.88em}
</style>
</head>
<body>
<div class="hdr">
  <div style="font-size:2em">🤖</div>
  <div>
    <h1>Pepper Master Station — Real Therapy Session</h1>
    <p style="font-size:.83em;opacity:.8">
      Zoom-Style Voice + Video |
      Protocol:
      <span class="prot {{s.protocol}}">{{s.protocol}}</span> |
      Started: {{s.session_start}}
    </p>
  </div>
  <span class="live">● LIVE</span>
</div>

<div class="cont">

  <!-- Child Identity -->
  <div class="child-box">
    {% if s.child_known %}
    <div style="color:#6b7280;font-size:.85em">Therapy Child</div>
    <div class="child-name">👦 {{s.child_name}}</div>
    <div style="margin-top:6px">
      <span class="prom-badge p{{s.prompt_level}}">
        Prompt Level {{s.prompt_level}}
      </span>
    </div>
    {% else %}
    <div style="color:#f59e0b;font-size:1.1em">
      ⏳ Waiting to learn child's name...
    </div>
    {% endif %}
  </div>

  <!-- Stats -->
  <div class="g3">
    <div class="stat">
      <div class="n">{{s.total_score}}</div>
      <div class="l">Session Score</div>
    </div>
    <div class="stat">
      <div class="n">{{s.attention}}%</div>
      <div class="l">Attention</div>
    </div>
    <div class="stat">
      <div class="n">{{s.session_logs|length}}</div>
      <div class="l">Interactions</div>
    </div>
  </div>

  <div class="g2">
    <!-- LEFT -->
    <div>
      <!-- Emotion -->
      <div class="card" style="margin-bottom:14px">
        <h2>😊 Live Emotion Stream</h2>
        <div style="text-align:center;padding:8px">
          <div class="emo {{s.emotion}}">
            {{emo_emoji}} {{s.emotion.upper()}}
          </div>
          <div style="margin-top:12px">
            <div style="font-size:.82em;color:#6b7280">
              Attention</div>
            <div class="bar-bg">
              <div class="bar" style="width:{{s.attention}}%"></div>
            </div>
            <div style="font-size:.8em;color:#818cf8">
              {{s.attention}}%</div>
          </div>
          <div style="margin-top:8px;font-size:.82em;color:#6b7280">
            Engagement:
            <b style="color:#e0e6ff">{{s.engagement}}</b>
          </div>
          <div style="margin-top:5px;font-size:.78em;
            color:{{'#34d399' if s.face_detected else '#ef4444'}}">
            {{'✓ Face Detected' if s.face_detected else '✗ No Face'}}
          </div>
        </div>
      </div>

      <!-- Game Center -->
      <div class="card" style="margin-bottom:14px">
        <h2>🎮 Pepper Control Panel</h2>
        <form method="POST" action="/cmd">
          <button class="btn btn-g" name="c" value="balloon">
            🎈 Balloon Chase (Reward)</button>
          <button class="btn btn-y" name="c" value="dance">
            💃 Dance Reward</button>
          <button class="btn" name="c" value="dtt">
            📚 DTT Session</button>
          <button class="btn" name="c" value="teacch">
            📅 TEACCH</button>
          <button class="btn" name="c" value="tie">
            🧠 TIE Mode</button>
          <button class="btn btn-r" name="c" value="stop">
            ⏹ Stop</button>
        </form>
      </div>

      <!-- YouTube Skills -->
      <div class="card">
        <h2>📺 Skill Videos for Child</h2>
        <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px">
          {% for skill in skills %}
          <form method="POST" action="/open_skill" style="display:inline">
            <button class="btn btn-y" name="skill"
                    value="{{skill}}" style="font-size:.78em;padding:6px 11px">
              {{skill}}
            </button>
          </form>
          {% endfor %}
        </div>
        <form method="POST" action="/search_video"
              style="display:flex;gap:8px">
          <input type="text" name="q"
                 placeholder="Ask: How do I wash my face?">
          <button class="btn">🔍</button>
        </form>
      </div>
    </div>

    <!-- RIGHT: Logs -->
    <div class="card">
      <h2>📋 Live Therapy Log</h2>
      <div class="log-box">
        {% for log in s.session_logs[-25:]|reverse %}
        <div class="log {{log.type}}">
          <span style="color:#6366f1">{{log.time}}</span>
          <span class="prot {{log.protocol}}">{{log.protocol}}</span>
          {% if log.child and log.child != 'Unknown' %}
          <b style="color:#a78bfa">{{log.child}}</b>:
          {% endif %}
          {{log.message}}
          <span style="color:#4b5563;font-size:.82em">
            | 😊{{log.emotion}}</span>
        </div>
        {% endfor %}
      </div>
      <div style="margin-top:10px;display:flex;
                  justify-content:space-between;align-items:center">
        <a href="/export" style="color:#6366f1;font-size:.82em">
          📄 Export Report</a>
        <form method="POST" action="/set_name"
              style="display:flex;gap:6px">
          <input type="text" name="name"
                 placeholder="Set child name..."
                 style="width:140px;padding:5px 8px">
          <button class="btn" style="padding:5px 10px">✓</button>
        </form>
      </div>
    </div>
  </div>
</div>
</body>
</html>
"""

EMO_EMOJI = {
    "happy":"😊","sad":"😢","angry":"😠",
    "neutral":"😐","fear":"😨","surprise":"😲","disgust":"🤢"
}

@flask_app.route("/")
def dashboard():
    return render_template_string(
        DASHBOARD,
        s=STATE,
        emo_emoji=EMO_EMOJI.get(STATE["emotion"],"😐"),
        skills=list(YOUTUBE_SKILLS.keys()))

@flask_app.route("/update_context", methods=["POST"])
def update_context():
    data = request.json or {}
    em   = data.get("emotion","neutral")
    STATE["emotion"]      = em
    STATE["face_detected"]= True
    STATE["attention"]    = data.get("attention", STATE["attention"])
    if em == "happy":
        STATE["engagement"] = "high"
    elif em in ["sad","angry","fear"]:
        STATE["engagement"] = "distressed"
    else:
        STATE["engagement"] = "moderate"
    return jsonify({"status":"ok"})

@flask_app.route("/cmd", methods=["POST"])
def cmd():
    STATE["sim_cmd"] = request.form.get("c","")
    add_log(f"Dashboard cmd: {STATE['sim_cmd']}","info")
    return dashboard()

@flask_app.route("/set_name", methods=["POST"])
def set_name():
    name = request.form.get("name","").strip().title()
    if name:
        STATE["child_name"]  = name
        STATE["child_known"] = True
        add_log(f"Child name set: {name}","success")
    return dashboard()

@flask_app.route("/open_skill", methods=["POST"])
def open_skill():
    skill = request.form.get("skill","")
    url   = YOUTUBE_SKILLS.get(skill)
    if url:
        webbrowser.open(url)
        add_log(f"Opened skill video: {skill}","info")
    return dashboard()

@flask_app.route("/search_video", methods=["POST"])
def search_video():
    q = request.form.get("q","").lower()
    _open_skill_video(q)
    return dashboard()

@flask_app.route("/report")
def report():
    return jsonify(STATE)

@flask_app.route("/export")
def export():
    fn = f"therapy_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(fn,"w") as f:
        json.dump(STATE, f, indent=2, default=str)
    return jsonify({"saved":fn})

def _open_skill_video(query):
    """فتح فيديو مناسب"""
    q = query.lower()
    for key, url in YOUTUBE_SKILLS.items():
        if key in q:
            webbrowser.open(url)
            add_log(f"📺 Opened: {key}","info")
            return url
    # بحث عام
    search = f"{query} autism children educational"
    url = "https://www.youtube.com/results?search_query="+\
          urllib.parse.quote(search)
    webbrowser.open(url)
    add_log(f"📺 YouTube search: {query}","info")
    return url

def run_flask():
    flask_app.run(
        port=5009, debug=False, use_reloader=False)

# ========== VOICE ==========
class Voice:
    def __init__(self):
        try:
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', 138)
            self.engine.setProperty('volume', 1.0)
            for v in self.engine.getProperty('voices'):
                if any(x in v.name.lower()
                       for x in ['female','zira','hazel','susan']):
                    self.engine.setProperty('voice', v.id)
                    break
            self.ok = True
            print("✅ Voice ready!")
        except Exception as e:
            print(f"⚠️  Voice: {e}")
            self.ok = False

    def say(self, text, child_name=None):
        if child_name:
            text = text.replace("{name}", child_name)
        print(f"\n🔊 Pepper: {text}")
        add_log(f"Pepper said: {text[:70]}", "info")
        if not self.ok: return
        try:
            self.engine.say(text)
            self.engine.runAndWait()
        except: pass

# ========== SPEECH RECOGNITION ==========
class SpeechListener:
    def __init__(self, voice):
        self.voice   = voice
        self.ok      = False
        self.running = False
        self.result_q= queue.Queue()
        try:
            import speech_recognition as sr
            self.sr   = sr
            self.recog= sr.Recognizer()
            self.recog.energy_threshold      = 300
            self.recog.dynamic_energy_threshold = True
            self.ok = True
            print("✅ Speech recognition ready!")
        except Exception as e:
            print(f"⚠️  SpeechRecognition: {e}")

    def listen_once(self, prompt=""):
        """استماع مرة واحدة"""
        if not self.ok:
            return input(f"[Type] {prompt}: ").strip()
        try:
            with self.sr.Microphone() as src:
                print(f"🎤 {prompt} (listening...)")
                self.recog.adjust_for_ambient_noise(src,0.5)
                audio = self.recog.listen(
                    src, timeout=8, phrase_time_limit=10)
            text = self.recog.recognize_google(audio)
            print(f"👶 Child said: {text}")
            add_log(f"Child said: {text}","info")
            return text
        except Exception as e:
            print(f"⚠️  Listen error: {e}")
            return ""

    def get_child_name(self):
        """معرفة اسم الطفل"""
        if STATE["child_known"]:
            return STATE["child_name"]

        self.voice.say(
            "Hello! I am Pepper, your therapy robot friend! "
            "What is your name?")
        time.sleep(0.5)

        # محاولتان للاستماع
        for attempt in range(2):
            response = self.listen_once(
                "What is your name?")
            if response:
                # استخرج الاسم
                name = self._extract_name(response)
                if name:
                    STATE["child_name"]  = name
                    STATE["child_known"] = True
                    self.voice.say(
                        f"Hello {name}! "
                        "I am so happy to meet you! "
                        "Let us have fun together today!")
                    add_log(
                        f"Child name learned: {name}",
                        "success","GREETING")
                    return name

        # fallback
        STATE["child_name"]  = "Friend"
        STATE["child_known"] = True
        self.voice.say(
            "I will call you my special friend! "
            "Let us start!")
        return "Friend"

    def _extract_name(self, text):
        """استخرج الاسم من الجملة"""
        text = text.lower().strip()
        # حذف الكلمات الشائعة
        removes = ["my name is","i am","i'm","iam",
                   "call me","name is","it's","its"]
        for r in removes:
            text = text.replace(r,"").strip()
        # أول كلمة = الاسم
        words = text.split()
        if words:
            return words[0].capitalize()
        return None

    def listen_continuous(self, callback):
        """استماع مستمر في background"""
        if not self.ok: return

        def _loop():
            self.running = True
            while self.running:
                try:
                    text = self.listen_once("")
                    if text:
                        callback(text)
                except: pass
                time.sleep(0.5)

        threading.Thread(target=_loop, daemon=True).start()

# ========== CAMERA + EMOTION ==========
class TherapyCamera:
    def __init__(self):
        self.ok          = False
        self.deepface_ok = False
        self.yolo_ok     = False
        self.cap         = None
        self.frame       = None
        self.running     = False

        try:
            import cv2
            self.cv2 = cv2
        except:
            print("⚠️  OpenCV not found")
            self._start_sim()
            return

        # DeepFace
        try:
            from deepface import DeepFace
            self.DeepFace    = DeepFace
            self.deepface_ok = True
            print("✅ DeepFace ready!")
        except:
            print("⚠️  DeepFace - using basic detection")

        # YOLO
        try:
            from ultralytics import YOLO
            self.yolo    = YOLO('yolov8n.pt')
            self.yolo_ok = True
            print("✅ YOLOv8 ready!")
        except:
            print("⚠️  YOLO not available")

        # كاميرا
        self.cap = cv2.VideoCapture(0)
        if self.cap.isOpened():
            self.ok      = True
            self.running = True
            threading.Thread(
                target=self._run, daemon=True).start()
            print("✅ Camera ready - Zoom style!")
        else:
            print("⚠️  No camera")
            self._start_sim()

    def _run(self):
        fc = 0
        while self.running:
            ret, frame = self.cap.read()
            if not ret: continue
            fc += 1
            self.frame = frame.copy()

            # YOLO
            if self.yolo_ok and fc % 6 == 0:
                self._detect_person(frame)

            # DeepFace
            if self.deepface_ok and fc % 25 == 0:
                threading.Thread(
                    target=self._analyze_emotion,
                    args=(frame.copy(),),
                    daemon=True).start()

            # Overlay
            self._draw_overlay(frame)
            self.cv2.imshow(
                "🤖 Pepper Therapy - Live Session", frame)

            key = self.cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            time.sleep(0.025)

    def _detect_person(self, frame):
        try:
            results = self.yolo(frame, verbose=False)
            for r in results:
                for box in r.boxes:
                    nm = self.yolo.names[int(box.cls[0])]
                    if nm == "person":
                        x1,y1,x2,y2 = map(int,box.xyxy[0])
                        name = STATE.get("child_name","Child")
                        self.cv2.rectangle(
                            frame,(x1,y1),(x2,y2),(99,235,99),2)
                        self.cv2.putText(
                            frame, f"👦 {name}",
                            (x1,y1-10),
                            self.cv2.FONT_HERSHEY_SIMPLEX,
                            0.7,(99,235,99),2)
                        STATE["face_detected"] = True
                        STATE["attention"] = min(
                            100, STATE["attention"]+3)
        except: pass

    def _analyze_emotion(self, frame):
        try:
            res = self.DeepFace.analyze(
                frame, actions=['emotion'],
                enforce_detection=False, silent=True)
            if res:
                em = res[0]['dominant_emotion']
                STATE["emotion"]      = em
                STATE["face_detected"]= True
                sc = res[0]['emotion']
                pos= sc.get('happy',0)+sc.get('surprise',0)
                neg= sc.get('sad',0)+sc.get('angry',0)+\
                     sc.get('fear',0)
                if pos > 40:   STATE["engagement"]="high"
                elif neg > 50: STATE["engagement"]="distressed"
                else:          STATE["engagement"]="moderate"

                # إرسال للسيرفر
                try:
                    requests.post(
                        'http://localhost:5009/update_context',
                        json={"emotion":em},timeout=0.3)
                except: pass
        except: pass

    def _draw_overlay(self, frame):
        """Zoom-style overlay"""
        h,w = frame.shape[:2]
        em   = STATE["emotion"]
        att  = STATE["attention"]
        name = STATE.get("child_name","...")
        prot = STATE["protocol"]

        colors = {
            "happy":(99,235,99),"sad":(99,160,235),
            "angry":(99,99,235),"neutral":(180,180,180),
            "fear":(99,200,235),"surprise":(200,99,235)
        }
        col = colors.get(em,(220,220,220))

        # شريط أسفل
        ov = frame.copy()
        self.cv2.rectangle(ov,(0,h-75),(w,h),(10,14,20),-1)
        frame[:] = self.cv2.addWeighted(ov,0.75,frame,0.25,0)

        self.cv2.putText(
            frame, f"😊 {em.upper()} | 👦 {name}",
            (10,h-50),self.cv2.FONT_HERSHEY_SIMPLEX,
            0.65,col,2)
        self.cv2.putText(
            frame, f"Attention: {att}% | Protocol: {prot}",
            (10,h-22),self.cv2.FONT_HERSHEY_SIMPLEX,
            0.52,(150,150,220),1)

        # Prompt level badge
        pl = STATE["prompt_level"]
        pl_colors = [(99,235,99),(235,200,99),
                     (235,140,99),(235,99,99)]
        pl_col = pl_colors[min(pl,3)]
        self.cv2.circle(frame,(w-20,20),10,pl_col,-1)
        self.cv2.putText(
            frame,f"P{pl}",(w-28,25),
            self.cv2.FONT_HERSHEY_SIMPLEX,0.45,(0,0,0),1)

        # REC dot
        self.cv2.circle(frame,(w-50,20),7,(0,0,235),-1)
        self.cv2.putText(
            frame,"REC",(w-85,26),
            self.cv2.FONT_HERSHEY_SIMPLEX,0.45,(0,0,235),1)

    def _start_sim(self):
        """محاكاة بدون كاميرا"""
        def _loop():
            pool=["happy","happy","neutral","neutral","sad"]
            while True:
                STATE["emotion"]      = random.choice(pool)
                STATE["face_detected"]= random.random()>0.15
                STATE["attention"]    = random.randint(50,90)
                time.sleep(5)
        threading.Thread(target=_loop,daemon=True).start()
        print("📷 Camera simulation mode active")

    def stop(self):
        self.running = False
        if self.cap: self.cap.release()
        try:    self.cv2.destroyAllWindows()
        except: pass

# ========== ASD CHILD (PyBullet) ==========
class ASDChild:
    P={
        "mild":    {"r":.75,"a":12,"m":.05,"rep":.20},
        "moderate":{"r":.45,"a":7, "m":.15,"rep":.45},
        "severe":  {"r":.15,"a":3, "m":.35,"rep":.75},
    }
    BH={
        "mild":    ["wandering","smiling","pointing"],
        "moderate":["hand_flapping","rocking","ignoring"],
        "severe":  ["spinning","covering_ears","stimming"],
    }
    CL={
        "mild":    [.2,.85,.2,1],
        "moderate":[1.,.6,.0,1],
        "severe":  [.9,.15,.15,1],
    }

    def __init__(self,name,pos,sev):
        self.name=name; self.base=list(pos)
        self.pos=list(pos); self.sev=sev
        self.pr=self.P[sev]
        self.bh="wandering"; self.em="calm"
        self.melt=False; self.mt=0
        self.lt=time.time()
        self.vel=[random.uniform(-.005,.005),
                  random.uniform(-.005,.005)]
        self.off=[0.,0.]
        self.inter=0; self.suc=0; self.score=0
        self.tid=self.hid=None
        self._build()

    def _build(self):
        vs=p.createVisualShape(p.GEOM_BOX,
            halfExtents=[.13,.09,.21],rgbaColor=self.CL[self.sev])
        cs=p.createCollisionShape(p.GEOM_BOX,
            halfExtents=[.13,.09,.21])
        self.tid=p.createMultiBody(
            0,cs,vs,[self.pos[0],self.pos[1],.41])
        vs2=p.createVisualShape(p.GEOM_SPHERE,
            radius=.11,rgbaColor=[1.,.82,.65,1.])
        cs2=p.createCollisionShape(p.GEOM_SPHERE,radius=.11)
        self.hid=p.createMultiBody(
            0,cs2,vs2,[self.pos[0],self.pos[1],.74])
        em={"mild":"🟢","moderate":"🟠","severe":"🔴"}
        p.addUserDebugText(
            f"{self.name} {em[self.sev]}",
            [self.pos[0],self.pos[1],1.05],
            [0,0,0],textSize=.9,lifeTime=0)

    def update(self):
        now=time.time()
        if now-self.lt>self.pr["a"]:
            self.lt=now
            if not self.melt and random.random()<self.pr["m"]:
                self.melt=True; self.mt=now
                self.em="overwhelmed"
                self.bh=random.choice(self.BH[self.sev])
            elif self.melt and now-self.mt>10:
                self.melt=False; self.em="calm"
                self.bh="wandering"
            else:
                pool=self.BH[self.sev] \
                    if random.random()<self.pr["rep"] \
                    else ["wandering"]
                self.bh=random.choice(pool)
                self.em=random.choice(
                    ["calm","happy","anxious","sad"])
        spd=.005 if not self.melt else .009
        for i in range(2):
            self.vel[i]+=random.uniform(-.001,.001)
            self.vel[i]=max(-spd,min(spd,self.vel[i]))
            self.off[i]+=self.vel[i]
            if abs(self.off[i])>.4:
                self.vel[i]*=-1
        self.pos[0]=self.base[0]+self.off[0]
        self.pos[1]=self.base[1]+self.off[1]
        try:
            p.resetBasePositionAndOrientation(
                self.tid,[self.pos[0],self.pos[1],.41],[0,0,0,1])
            p.resetBasePositionAndOrientation(
                self.hid,[self.pos[0],self.pos[1],.74],[0,0,0,1])
        except: pass

    def respond(self):
        self.inter+=1
        if self.melt: return False
        base=self.pr["r"]
        if STATE["emotion"]=="happy":        base+=.15
        if STATE["attention"]>70:            base+=.10
        if STATE["engagement"]=="high":      base+=.10
        if STATE["engagement"]=="distressed":base-=.20
        ok=random.random()<max(.05,min(.95,base))
        if ok:
            self.suc+=1; self.score+=10
            STATE["total_score"]+=10
        return ok

    def rate(self):
        return 0 if not self.inter \
            else round(self.suc/self.inter*100,1)

# ========== MASTER CONTROLLER ==========
class PepperMasterStation:
    def __init__(self):
        print("\n"+"="*60)
        print("🤖 PEPPER MASTER STATION STARTING")
        print("="*60)

        self.voice    = Voice()
        self.camera   = TherapyCamera()
        self.listener = SpeechListener(self.voice)

        # PyBullet
        self.sim    = SimulationManager()
        self.client = self.sim.launchSimulation(gui=True)
        p.setRealTimeSimulation(1)
        p.setGravity(0,0,-9.81)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.loadURDF("plane.urdf")
        self._build_room()

        # Pepper
        print("🤖 Spawning Pepper...")
        self.pepper     = self.sim.spawnPepper(self.client)
        self.pepper.goToPosture("Stand",0.5)
        self.rx=self.ry = 0.0
        self.head_yaw   = 0.0
        self.auto_walk  = True
        self.is_talking = False
        self.balloons   = []
        self._create_balloons()

        # أطفال
        self.children = [
            ASDChild("Ahmed",[ 1.5,-1.2,0],"mild"),
            ASDChild("Sara", [-1.2, 1.3,0],"moderate"),
            ASDChild("Yusuf",[ 0.5,-2.0,0],"severe"),
            ASDChild("Layla",[ 2.8,-0.2,0],"moderate"),
            ASDChild("Omar", [-2.2,-1.0,0],"mild"),
        ]

        self.kid_idx = 0
        self.p_idx   = 0
        self.protocols=["ABA","DTT","TEACCH","TIE"]

        # Threads
        for fn in [self._sim_loop, self._children_loop,
                   self._walk_loop, self._arm_loop,
                   self._prompt_loop, self._cmd_loop]:
            threading.Thread(target=fn,daemon=True).start()

        p.resetDebugVisualizerCamera(7,45,-35,[0,0,.5])
        time.sleep(2)

    def _build_room(self):
        print("🏠 Building therapy room...")
        wc=[.85,.85,.9,1]
        for pos,ext in [
            ([0,-4,1.1],[5,.1,1.1]),([0,4,1.1],[5,.1,1.1]),
            ([5,0,1.1],[.1,4,1.1]),([-5,0,1.1],[.1,4,1.1])]:
            p.createMultiBody(0,-1,
                p.createVisualShape(
                    p.GEOM_BOX,halfExtents=ext,rgbaColor=wc),pos)
        p.createMultiBody(0,-1,
            p.createVisualShape(p.GEOM_BOX,
                halfExtents=[4.5,3.5,.02],
                rgbaColor=[.5,.4,.3,1]),[0,0,.01])
        for txt,pos in [
            ("ABA",[-4,3,1.8]),("DTT",[4,3,1.8]),
            ("TEACCH",[0,4,1.8]),("TIE",[-4,-3,1.8])]:
            p.addUserDebugText(
                txt,pos,[.3,.3,.9],textSize=1.3,lifeTime=0)
        print("✅ Room ready!")

    def _create_balloons(self):
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
                "id":bid,
                "x":random.uniform(-3,3),
                "y":random.uniform(-2,2),
                "z":random.uniform(.8,2.2),
                "spd":random.uniform(.01,.03)
            })

    # ===== SIMULATION LOOPS =====
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

    def _children_loop(self):
        while True:
            for c in self.children: c.update()
            time.sleep(.05)

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
                    self.pepper.setPosition([self.rx,self.ry,.8])
                except: pass
            time.sleep(.06)

    def _arm_loop(self):
        ph=0
        while True:
            try:
                if self.is_talking:
                    ph+=.07
                    L=.5+.3*math.sin(ph)
                    R=.5+.3*math.sin(ph+math.pi*.6)
                    self.pepper.setAngles("LShoulderPitch",L,.07)
                    self.pepper.setAngles("RShoulderPitch",R,.07)
                    self.pepper.setAngles("LElbowRoll",
                        -.3-.15*math.sin(ph*.7),.07)
                    self.pepper.setAngles("RElbowRoll",
                        .3+.15*math.sin(ph*.7),.07)
                else:
                    self.pepper.setAngles("LShoulderPitch",1.,.04)
                    self.pepper.setAngles("RShoulderPitch",1.,.04)
            except: pass
            time.sleep(.04)

    # ===== PROMPT LEVEL SYSTEM =====
    def _prompt_loop(self):
        """ABA Multi-level prompting"""
        time.sleep(5)
        no_face_count = 0
        while True:
            em  = STATE["emotion"]
            att = STATE["attention"]
            fd  = STATE["face_detected"]
            eng = STATE["engagement"]
            name= STATE.get("child_name","Friend")

            # Level 0: طفل منتبه ومبسوط
            if fd and em=="happy" and att>60:
                STATE["prompt_level"]=0
                no_face_count=0

            # Level 1: طفل مشتت (Verbal Prompt)
            elif not fd or att<40:
                no_face_count+=1
                if no_face_count==2:
                    STATE["prompt_level"]=1
                    self._speak(
                        f"Look at me {name}! "
                        "Let us play together!")
                    add_log("Prompt L1: Verbal","info","ABA")

            # Level 2: لا استجابة (Visual Prompt - wave/dance)
            elif no_face_count>=4:
                STATE["prompt_level"]=2
                add_log("Prompt L2: Visual","info","ABA")
                self._wave()
                no_face_count=0

            # Level 3: distressed (Modeling)
            if eng=="distressed" or em in ["angry","fear"]:
                STATE["prompt_level"]=3
                self._speak(
                    f"It is okay {name}. "
                    "Let us breathe. In... out...")
                add_log("Prompt L3: Modeling","info","TIE")
                no_face_count=0

            # Happy reward → balloon
            if em=="happy" and att>70:
                STATE["sim_cmd"]="balloon_reward"

            time.sleep(4)

    def _cmd_loop(self):
        """تنفيذ أوامر الداشبورد"""
        while True:
            cmd=STATE.get("sim_cmd")
            if cmd:
                STATE["sim_cmd"]=None
                name=STATE.get("child_name","Friend")
                if cmd in ["balloon","balloon_reward"]:
                    self._speak(
                        f"Great job {name}! "
                        "Balloon time! 🎈")
                    self.auto_walk=True
                elif cmd=="dance":
                    self._dance(name)
                elif cmd=="dtt":
                    c=self.children[self.kid_idx%len(self.children)]
                    threading.Thread(
                        target=self._run_dtt,
                        args=(c,),daemon=True).start()
                elif cmd=="teacch":
                    c=self.children[self.kid_idx%len(self.children)]
                    threading.Thread(
                        target=self._run_teacch,
                        args=(c,),daemon=True).start()
                elif cmd=="tie":
                    c=self.children[self.kid_idx%len(self.children)]
                    threading.Thread(
                        target=self._run_tie,
                        args=(c,),daemon=True).start()
                elif cmd=="stop":
                    self.auto_walk=False
                    self._speak("Stopping now.")
            time.sleep(.5)

    # ===== MOVEMENT =====
    def _move_to(self, child):
        self.auto_walk=False
        tx,ty=child.pos[0],child.pos[1]
        for _ in range(100):
            dx=tx-self.rx; dy=ty-self.ry
            dist=math.sqrt(dx**2+dy**2)
            if dist<.85: break
            step=min(.055,dist-.75)
            self.rx+=dx/dist*step
            self.ry+=dy/dist*step
            self.head_yaw=math.atan2(dy,dx)
            try:
                self.pepper.setPosition([self.rx,self.ry,.8])
                self.pepper.setAngles(
                    "HeadYaw",self.head_yaw*.5,.1)
                self.pepper.setAngles("HeadPitch",-.1,.08)
            except: pass
            time.sleep(.04)
        dx=tx-self.rx; dy=ty-self.ry
        self.head_yaw=math.atan2(dy,dx)
        try:
            self.pepper.setAngles(
                "HeadYaw",self.head_yaw*.5,.12)
        except: pass
        time.sleep(.4)

    def _speak(self, text):
        name=STATE.get("child_name","Friend")
        text=text.replace("{name}",name)
        self.is_talking=True
        try:
            pos=p.getBasePositionAndOrientation(
                self.pepper.body)[0]
            p.addUserDebugText(
                text[:55],[pos[0],pos[1],pos[2]+1.3],
                [0,0,0],textSize=.85,lifeTime=5)
        except: pass
        self.voice.say(text)
        self.is_talking=False

    def _wave(self):
        try:
            self.pepper.setAngles("RShoulderPitch",.2,.2)
            self.pepper.setAngles("RElbowRoll",.8,.2)
            time.sleep(.3)
            for _ in range(3):
                self.pepper.setAngles("RWristYaw",.5,.2)
                time.sleep(.2)
                self.pepper.setAngles("RWristYaw",-.5,.2)
                time.sleep(.2)
            self.pepper.setAngles("RShoulderPitch",1.,.15)
        except: pass

    def _dance(self, name="Friend"):
        self._speak(f"Let us dance {name}!")
        try:
            for _ in range(4):
                self.pepper.setAngles("LShoulderPitch",.2,.2)
                self.pepper.setAngles("RShoulderPitch",.9,.2)
                self.pepper.setAngles("HeadYaw",.3,.15)
                time.sleep(.25)
                self.pepper.setAngles("LShoulderPitch",.9,.2)
                self.pepper.setAngles("RShoulderPitch",.2,.2)
                self.pepper.setAngles("HeadYaw",-.3,.15)
                time.sleep(.25)
            self.pepper.setAngles("HeadYaw",0,.1)
        except: pass

    def _celebrate(self):
        try:
            for _ in range(2):
                self.pepper.setAngles("LShoulderPitch",.1,.2)
                self.pepper.setAngles("RShoulderPitch",.1,.2)
                time.sleep(.2)
                self.pepper.setAngles("LShoulderPitch",.9,.2)
                self.pepper.setAngles("RShoulderPitch",.9,.2)
                time.sleep(.2)
        except: pass

    def _adapt(self, child):
        em=STATE["emotion"]; eng=STATE["engagement"]
        name=STATE.get("child_name","Friend")
        if eng=="distressed" or em in ["angry","fear"]:
            self._speak(
                f"It is okay {name}. "
                "Let us take a break and breathe.")
            time.sleep(3)
            return "break"
        if STATE["attention"]<30:
            self._speak(f"Hey {name}! Look at me!")
            return "redirect"
        return "continue"

    # ===== ABA / DTT / TEACCH / TIE =====
    def _run_dtt(self, child):
        STATE["protocol"]="DTT"
        name=STATE.get("child_name","Friend")
        self._move_to(child)
        self._speak(f"DTT time {name}! Listen carefully!")
        add_log(f"DTT started with {child.name}","info","DTT")

        tasks={
            "mild":  [("Point to the ball","point"),
                      ("Show me happy face","emotion"),
                      ("Count to three","count")],
            "moderate":[("Clap your hands","clap"),
                        ("Touch your nose","nose"),
                        ("Wave hello","wave")],
            "severe":  [("Look at me","attention"),
                        ("Clap","clap"),
                        ("Touch nose","nose")],
        }

        for txt,typ in random.sample(
                tasks[child.sev],
                min(3,len(tasks[child.sev]))):
            if self._adapt(child)=="break": continue
            self._speak(f"{name}, {txt}!")
            time.sleep(1.5)
            ok=child.respond()
            if ok:
                r=random.choice(
                    ["Amazing!","Super star!",
                     "You did it!","Wonderful!"])
                self._speak(r)
                self._celebrate()
                add_log(f"DTT: {txt} → SUCCESS",
                    "success","DTT")
            else:
                self._speak(
                    f"Let us try again! {txt}")
                add_log(f"DTT: {txt} → retry",
                    "fail","DTT")
            time.sleep(2)
        self.auto_walk=True

    def _run_teacch(self, child):
        STATE["protocol"]="TEACCH"
        name=STATE.get("child_name","Friend")
        self._move_to(child)
        self._speak(
            f"Hello {name}! "
            "Let us check our schedule today!")
        schedule=[
            ("🌅 Greeting",
             f"Good morning {name}! How are you?"),
            ("😊 Emotion Check",
             f"{name}, show me a happy face!"),
            ("📚 Work Task",
             f"Let us sort these colors {name}!"),
            ("🎯 Sensory Break",
             "Take a deep breath with me. In... out..."),
            ("👀 Joint Attention",
             f"Look {name}! Look at the red ball!"),
            ("⭐ Closing",
             f"Great work {name}! Session done!"),
        ]
        for act,txt in schedule:
            if self._adapt(child)=="break": continue
            print(f"\n{act}")
            self._speak(txt)
            ok=child.respond()
            if ok:
                child.score+=15; STATE["total_score"]+=15
                self._speak("Excellent!")
            add_log(f"TEACCH: {act} → "
                f"{'✓' if ok else '✗'}",
                "success" if ok else "fail","TEACCH")
            time.sleep(2.5)
        self.auto_walk=True

    def _run_aba(self, child):
        STATE["protocol"]="ABA"
        name=STATE.get("child_name","Friend")
        self._move_to(child)
        self._speak(f"ABA therapy time {name}!")

        instrs={
            "mild":  ["Point to ball","Happy face?",
                      "What color?","Count to 3"],
            "moderate":["Clap hands","Touch nose",
                        "Wave","Stand up"],
            "severe":  ["Look at me","Touch nose","Clap"],
        }
        for instr in random.sample(
                instrs[child.sev],
                min(3,len(instrs[child.sev]))):
            if self._adapt(child)=="break": continue
            self._speak(f"{name}, {instr}!")
            time.sleep(1.5)
            ok=child.respond()
            if ok:
                self._speak(random.choice(
                    ["Amazing!","Super star!","You did it!"]))
                self._celebrate()
                add_log(f"ABA: {instr} → SUCCESS",
                    "success","ABA")
            else:
                self._speak(f"Try again! {instr}")
                add_log(f"ABA: {instr} → retry",
                    "fail","ABA")
            time.sleep(2)
        self.auto_walk=True

    def _run_tie(self, child):
        STATE["protocol"]="TIE"
        name=STATE.get("child_name","Friend")
        self._move_to(child)
        self._speak(
            f"Hello {name}. "
            "I am watching and adapting just for you!")

        for _ in range(6):
            em=STATE["emotion"]
            att=STATE["attention"]
            eng=STATE["engagement"]

            if eng=="distressed":
                self._speak(
                    "Let us calm down together.")
                time.sleep(3)
            elif att<35:
                self._speak(f"{name}! Look here at me!")
                self._wave()
            elif em=="happy" and att>65:
                self._speak(
                    "You are doing incredible! "
                    "Let us try something exciting!")
                ok=child.respond()
                if ok:
                    child.score+=20
                    STATE["total_score"]+=20
                    self._speak("Incredible! Champion!")
                    self._dance(name)
                    add_log("TIE: advance → SUCCESS",
                        "success","TIE")
            else:
                self._speak(
                    f"Keep going {name}! You can do it!")
                ok=child.respond()
                if ok:
                    child.score+=10
                    STATE["total_score"]+=10
                    self._celebrate()
                    add_log("TIE: maintain → SUCCESS",
                        "success","TIE")
            time.sleep(3)
        self.auto_walk=True

    def _handle_speech(self, text):
        """معالجة ما يقوله الطفل"""
        t   = text.lower()
        name= STATE.get("child_name","Friend")

        # How to / skill videos
        if "how" in t and (
                "to" in t or "do" in t or "i" in t):
            url = _open_skill_video(text)
            self._speak(
                f"Watch this video with me {name}! "
                "It will show you how!")
            return

        # أسئلة عامة
        if any(w in t for w in
               ["help","play","game","dance","balloon"]):
            self._speak(
                f"Of course {name}! Let us play!")
            STATE["sim_cmd"]="balloon"
            return

        if any(w in t for w in
               ["stop","no","bye","done"]):
            self._speak(
                f"Okay {name}. Good job today!")
            return

        # استجابة عامة
        responses=[
            f"Great {name}! Let us keep going!",
            f"You are amazing {name}!",
            f"I heard you {name}! What else?",
            f"Wonderful {name}! Keep it up!",
        ]
        self._speak(random.choice(responses))

    # ===== MAIN SESSION =====
    def start_session(self):
        """بداية الجلسة الحقيقية"""
        print("\n🏥 STARTING REAL THERAPY SESSION")

        # معرفة اسم الطفل
        name = self.listener.get_child_name()
        STATE["current_child"] = name
        add_log(
            f"Session started with {name}",
            "success","GREETING")

        # تحية
        time.sleep(1)
        self._speak(
            f"I am so happy to see you {name}! "
            "I am Pepper, your robot friend. "
            "Today we will learn and play together!")
        time.sleep(1)

        # استماع مستمر
        def on_speech(text):
            self._handle_speech(text)

        self.listener.listen_continuous(on_speech)

        # حلقة الثيرابي الرئيسية
        threading.Thread(
            target=self._therapy_loop,
            daemon=True).start()

    def _therapy_loop(self):
        time.sleep(3)
        while True:
            child   = self.children[
                self.kid_idx%len(self.children)]
            protocol= self.protocols[
                self.p_idx%len(self.protocols)]
            self.kid_idx+=1; self.p_idx+=1

            add_log(
                f"→ {child.name} | {protocol}","info")

            if protocol=="ABA":
                self._run_aba(child)
            elif protocol=="DTT":
                self._run_dtt(child)
            elif protocol=="TEACCH":
                self._run_teacch(child)
            elif protocol=="TIE":
                self._run_tie(child)

            print(f"\n[{child.name}] "
                  f"Rate:{child.rate()}% Score:{child.score}")
            self.auto_walk=True
            time.sleep(8)

    def run(self):
        print("\n"+"="*60)
        print("✅ PEPPER MASTER STATION READY")
        print("="*60)
        print("🌐 Dashboard: http://localhost:5009")
        print("📹 Camera: Real Zoom-style window")
        print("🎤 Voice: Real speech recognition")
        print("Commands: 'report' | 'name [child]' | 'exit'")
        print("="*60+"\n")

        self.start_session()

        while True:
            try:
                cmd=input("> ").strip()
                if not cmd: continue
                cl=cmd.lower()

                if cl=="report":
                    print("\n📊 REPORT")
                    print("-"*45)
                    for c in self.children:
                        bar="█"*int(c.rate()/10)+\
                            "░"*(10-int(c.rate()/10))
                        print(f"👦 {c.name:6} "
                              f"({c.sev:8}) "
                              f"[{bar}] {c.rate()}% "
                              f"Score:{c.score}")
                    print(f"Total: {STATE['total_score']}")
                    print(f"Emotion: {STATE['emotion']}")

                elif cl.startswith("name "):
                    n=cl[5:].strip().title()
                    STATE["child_name"]=n
                    STATE["child_known"]=True
                    self._speak(f"Hello {n}!")

                elif cl in ["exit","quit"]:
                    self.camera.stop()
                    self._speak("Goodbye! Great session!")
                    break

                elif cl:
                    # تمرير للـ speech handler
                    self._handle_speech(cmd)

            except KeyboardInterrupt:
                self.camera.stop()
                self._speak("Goodbye!")
                break

# ========== ENTRY POINT ==========
if __name__=="__main__":

    # Flask
    threading.Thread(target=run_flask,daemon=True).start()
    time.sleep(1)

    # تشغيل camera_yolo_emotion.py الموجود
    try:
        subprocess.Popen([
            "python3",
            "/home/lamya/pepper_duo/src/camera_yolo_emotion.py"
        ])
        print("✅ Camera emotion script launched!")
        time.sleep(2)
    except Exception as e:
        print(f"⚠️  {e}")

    # تشغيل النظام الكامل
    station = PepperMasterStation()
    station.run()
