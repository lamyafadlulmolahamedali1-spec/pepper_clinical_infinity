#!/usr/bin/env python3
"""
ZOOM-STYLE PEPPER THERAPY
- Camera window (like Zoom)
- Real emotion detection
- Voice AI chat
- ABA/TEACCH/DTT/TIE protocols
- PyBullet simulation
- Flask dashboard port 5009
Run: python3 zoom_therapy.py
"""

import sys, os, time, math, random, threading, json, queue
import pybullet as p
import pybullet_data
import pyttsx3
import requests
import webbrowser
import urllib.parse
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string

sys.path.insert(0, '/home/lamya/pepper_duo/src')
from qibullet import SimulationManager

# ========== SHARED STATE ==========
state = {
    "emotion":      "neutral",
    "attention":    70,
    "engagement":   "moderate",
    "face_detected": True,
    "session_logs": [],
    "current_child": "Ahmed",
    "current_protocol": "ABA",
    "total_score":  0,
    "simulation_cmd": None,   # balloon / dance / stop
}

# ========== FLASK DASHBOARD ==========
app_flask = Flask(__name__)

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>🤖 Pepper Therapy Dashboard</title>
<meta http-equiv="refresh" content="2">
<style>
* { box-sizing:border-box; margin:0; padding:0; }
body { font-family:'Segoe UI',sans-serif; background:#0f1117; color:#eee; }
.header {
    background:linear-gradient(135deg,#667eea,#764ba2);
    padding:18px 30px; display:flex;
    align-items:center; gap:15px;
}
.header h1 { font-size:1.4em; }
.header .live {
    background:#e74c3c; color:white;
    padding:3px 10px; border-radius:20px;
    font-size:0.8em; animation:pulse 1s infinite;
}
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.5} }
.container { max-width:1100px; margin:0 auto; padding:20px; }
.grid3 { display:grid; grid-template-columns:1fr 1fr 1fr; gap:15px; margin-bottom:20px; }
.grid2 { display:grid; grid-template-columns:1fr 1fr; gap:15px; margin-bottom:20px; }
.card {
    background:#1a1d27; border-radius:12px;
    padding:18px; border:1px solid #2a2d3a;
}
.card h2 {
    font-size:0.95em; color:#aaa;
    margin-bottom:12px; border-bottom:1px solid #2a2d3a;
    padding-bottom:8px;
}
.stat {
    background:linear-gradient(135deg,#667eea22,#764ba222);
    border:1px solid #667eea44;
    border-radius:10px; padding:15px; text-align:center;
}
.stat .num { font-size:2.2em; font-weight:bold; color:#667eea; }
.stat .lbl { font-size:0.8em; color:#888; margin-top:4px; }

/* Emotion badge */
.emotion-badge {
    display:inline-block; padding:6px 16px;
    border-radius:20px; font-weight:bold;
    font-size:1.1em; margin:5px 0;
}
.happy    { background:#27ae6033; color:#27ae60; border:1px solid #27ae60; }
.sad      { background:#3498db33; color:#3498db; border:1px solid #3498db; }
.angry    { background:#e74c3c33; color:#e74c3c; border:1px solid #e74c3c; }
.neutral  { background:#95a5a633; color:#95a5a6; border:1px solid #95a5a6; }
.fear     { background:#e67e2233; color:#e67e22; border:1px solid #e67e22; }
.surprise { background:#9b59b633; color:#9b59b6; border:1px solid #9b59b6; }
.disgust  { background:#1abc9c33; color:#1abc9c; border:1px solid #1abc9c; }

/* Attention bar */
.bar-bg { background:#2a2d3a; border-radius:10px; height:12px; margin:8px 0; }
.bar-fill { height:12px; border-radius:10px;
            background:linear-gradient(90deg,#667eea,#764ba2); }

/* Buttons */
.btn {
    background:linear-gradient(135deg,#667eea,#764ba2);
    color:white; border:none; padding:10px 18px;
    border-radius:8px; cursor:pointer; font-size:0.9em;
    margin:4px; transition:opacity 0.2s;
}
.btn:hover { opacity:0.85; }
.btn-red { background:linear-gradient(135deg,#e74c3c,#c0392b); }
.btn-green { background:linear-gradient(135deg,#27ae60,#2ecc71); }
.btn-orange { background:linear-gradient(135deg,#e67e22,#f39c12); }

/* Log */
.log-item {
    padding:8px 12px; margin:4px 0;
    border-radius:6px; font-size:0.82em;
    border-left:3px solid #667eea;
    background:#12151f;
}
.log-item.success { border-color:#27ae60; }
.log-item.fail    { border-color:#e74c3c; }
.log-item.info    { border-color:#3498db; }

/* Protocol badge */
.protocol {
    display:inline-block; padding:3px 10px;
    border-radius:12px; font-size:0.8em;
    font-weight:bold;
}
.ABA    { background:#667eea33; color:#667eea; }
.TEACCH { background:#27ae6033; color:#27ae60; }
.DTT    { background:#e67e2233; color:#e67e22; }
.TIE    { background:#9b59b633; color:#9b59b6; }

@media(max-width:700px){
    .grid3,.grid2{ grid-template-columns:1fr; }
}
</style>
</head>
<body>
<div class="header">
    <div style="font-size:2em">🤖</div>
    <div>
        <h1>Pepper ASD Therapy - Live Dashboard</h1>
        <p style="font-size:0.85em;opacity:0.8">
            Zoom-Style Therapy Session |
            Child: <b>{{state.current_child}}</b> |
            Protocol: <span class="protocol {{state.current_protocol}}">
                {{state.current_protocol}}</span>
        </p>
    </div>
    <span class="live">● LIVE</span>
</div>

<div class="container">

    <!-- Stats -->
    <div class="grid3">
        <div class="stat">
            <div class="num">{{state.total_score}}</div>
            <div class="lbl">Session Score</div>
        </div>
        <div class="stat">
            <div class="num">{{state.attention}}%</div>
            <div class="lbl">Child Attention</div>
        </div>
        <div class="stat">
            <div class="num">{{state.session_logs|length}}</div>
            <div class="lbl">Interactions</div>
        </div>
    </div>

    <div class="grid2">

        <!-- LEFT: Emotion + Camera -->
        <div>
            <div class="card" style="margin-bottom:15px">
                <h2>😊 Live Emotion Stream</h2>
                <div style="text-align:center; padding:10px">
                    <div class="emotion-badge {{state.emotion}}">
                        {{emotion_emoji}} {{state.emotion.upper()}}
                    </div>
                    <div style="margin-top:12px">
                        <div style="font-size:0.85em;color:#888;margin-bottom:4px">
                            Attention Level</div>
                        <div class="bar-bg">
                            <div class="bar-fill"
                                style="width:{{state.attention}}%"></div>
                        </div>
                        <div style="font-size:0.8em;color:#667eea">
                            {{state.attention}}%</div>
                    </div>
                    <div style="margin-top:10px;font-size:0.85em;color:#888">
                        Engagement:
                        <b style="color:#fff">{{state.engagement}}</b>
                    </div>
                    <div style="margin-top:6px;font-size:0.8em;
                                color:{{'#27ae60' if state.face_detected else '#e74c3c'}}">
                        {{'✓ Face Detected' if state.face_detected else '✗ No Face'}}
                    </div>
                </div>
            </div>

            <!-- Game Center -->
            <div class="card">
                <h2>🎮 Game Center</h2>
                <p style="font-size:0.82em;color:#888;margin-bottom:10px">
                    Control Pepper simulation</p>
                <form method="POST" action="/trigger">
                    <button class="btn btn-green"
                        name="cmd" value="balloon">
                        🎈 Balloon Chase
                    </button>
                    <button class="btn btn-orange"
                        name="cmd" value="dance">
                        💃 Dance Mode
                    </button>
                    <button class="btn"
                        name="cmd" value="dtt">
                        📚 DTT Session
                    </button>
                    <button class="btn"
                        name="cmd" value="teacch">
                        📅 TEACCH Schedule
                    </button>
                    <button class="btn btn-red"
                        name="cmd" value="stop">
                        ⏹ Stop
                    </button>
                </form>
            </div>
        </div>

        <!-- RIGHT: Logs -->
        <div class="card">
            <h2>📋 Therapy Session Log</h2>
            <div style="max-height:420px;overflow-y:auto">
                {% for log in state.session_logs[-20:]|reverse %}
                <div class="log-item {{log.type}}">
                    <span style="color:#667eea">{{log.time}}</span>
                    <span class="protocol {{log.protocol}}">
                        {{log.protocol}}</span>
                    {{log.message}}
                    {% if log.emotion %}
                    <span style="color:#888;font-size:0.85em">
                        | 😊{{log.emotion}}</span>
                    {% endif %}
                </div>
                {% endfor %}
            </div>
            <div style="margin-top:12px;text-align:right">
                <a href="/export" style="color:#667eea;font-size:0.85em">
                    📄 Export Report
                </a>
            </div>
        </div>
    </div>

    <!-- YouTube / How-to -->
    <div class="card">
        <h2>📺 Educational Resources</h2>
        <p style="font-size:0.82em;color:#888;margin-bottom:10px">
            Search educational videos for autism therapy</p>
        <form method="POST" action="/search_video"
              style="display:flex;gap:10px">
            <input name="query" placeholder="e.g. wash hands, brush teeth..."
                style="flex:1;padding:8px 12px;border-radius:8px;
                       border:1px solid #2a2d3a;background:#12151f;
                       color:#eee;font-size:0.9em">
            <button class="btn" type="submit">🔍 Find Video</button>
        </form>
    </div>

</div>
</body>
</html>
"""

EMOTION_EMOJIS = {
    "happy":"😊","sad":"😢","angry":"😠",
    "neutral":"😐","fear":"😨","surprise":"😲",
    "disgust":"🤢"
}

@app_flask.route("/")
def dashboard():
    emoji = EMOTION_EMOJIS.get(state["emotion"], "😐")
    return render_template_string(
        DASHBOARD_HTML, state=state, emotion_emoji=emoji)

@app_flask.route("/update_context", methods=["POST"])
def update_context():
    """يستقبل المشاعر من camera_yolo_emotion.py"""
    data = request.json or {}
    em   = data.get("emotion", "neutral")
    state["emotion"]      = em
    state["face_detected"]= True
    state["attention"]    = data.get("attention", state["attention"])

    # تحديث engagement
    if em == "happy":
        state["engagement"] = "high"
    elif em in ["sad","angry","fear"]:
        state["engagement"] = "distressed"
    else:
        state["engagement"] = "moderate"

    # إضافة للـ log
    _add_log(f"Camera detected: {em}", "info")
    return jsonify({"status":"ok","emotion":em})

@app_flask.route("/trigger", methods=["POST"])
def trigger():
    """أوامر من الداشبورد للـ simulation"""
    cmd = request.form.get("cmd","")
    state["simulation_cmd"] = cmd
    _add_log(f"Dashboard triggered: {cmd}", "info")
    return dashboard()

@app_flask.route("/search_video", methods=["POST"])
def search_video():
    query = request.form.get("query","")
    if query:
        search = f"{query} autism children educational therapy"
        url = "https://www.youtube.com/results?search_query=" + \
              urllib.parse.quote(search)
        webbrowser.open(url)
        _add_log(f"Opened YouTube: {query}", "info")
    return dashboard()

@app_flask.route("/api/state")
def api_state():
    return jsonify(state)

@app_flask.route("/export")
def export_report():
    """تصدير تقرير نصي"""
    report = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "child": state["current_child"],
        "protocol": state["current_protocol"],
        "total_score": state["total_score"],
        "final_emotion": state["emotion"],
        "logs": state["session_logs"]
    }
    fn = f"report_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(fn,"w") as f:
        json.dump(report, f, indent=2)
    _add_log(f"Report exported: {fn}", "success")
    return jsonify({"saved": fn, "data": report})

def _add_log(msg, log_type="info", protocol=None):
    state["session_logs"].append({
        "time":     datetime.now().strftime("%H:%M:%S"),
        "message":  msg,
        "type":     log_type,
        "protocol": protocol or state["current_protocol"],
        "emotion":  state["emotion"]
    })

def run_flask():
    print("🌐 Dashboard: http://localhost:5009")
    app_flask.run(port=5009, debug=False, use_reloader=False)

# ========== VOICE ==========
class Voice:
    def __init__(self):
        try:
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', 140)
            self.engine.setProperty('volume', 1.0)
            for v in self.engine.getProperty('voices'):
                if any(x in v.name.lower()
                       for x in ['female','zira','hazel']):
                    self.engine.setProperty('voice', v.id)
                    break
            self.ok = True
        except:
            self.ok = False

    def say(self, text):
        print(f"🔊 Pepper: {text}")
        _add_log(f"Pepper said: {text[:60]}", "info")
        if not self.ok: return
        try:
            self.engine.say(text)
            self.engine.runAndWait()
        except: pass

# ========== CAMERA + EMOTION ==========
class ZoomCamera:
    """نافذة الكاميرا مثل Zoom"""
    def __init__(self):
        self.running    = False
        self.deepface_ok= False
        self.yolo_ok    = False
        self.cap        = None
        self.frame      = None

        try:
            import cv2
            self.cv2 = cv2
        except:
            print("⚠️  OpenCV not found")
            return

        # DeepFace
        try:
            from deepface import DeepFace
            self.DeepFace = DeepFace
            self.deepface_ok = True
            print("✅ DeepFace ready!")
        except:
            print("⚠️  DeepFace not available")

        # YOLO
        try:
            from ultralytics import YOLO
            self.yolo = YOLO('yolov8n.pt')
            self.yolo_ok = True
            print("✅ YOLOv8 ready!")
        except:
            print("⚠️  YOLO not available")

        # كاميرا
        self.cap = cv2.VideoCapture(0)
        if self.cap.isOpened():
            self.running = True
            threading.Thread(
                target=self._run, daemon=True).start()
            print("✅ Camera (Zoom-style) ready!")
        else:
            print("⚠️  No camera - using simulation")
            threading.Thread(
                target=self._simulate, daemon=True).start()

    def _run(self):
        fc = 0
        while self.running:
            ret, frame = self.cap.read()
            if not ret: continue
            fc += 1
            self.frame = frame.copy()

            # YOLO detection
            if self.yolo_ok and fc % 5 == 0:
                results = self.yolo(frame, verbose=False)
                for r in results:
                    for box in r.boxes:
                        if self.yolo.names[int(box.cls[0])]=="person":
                            x1,y1,x2,y2 = map(int, box.xyxy[0])
                            self.cv2.rectangle(
                                frame,(x1,y1),(x2,y2),(0,255,0),2)
                            self.cv2.putText(
                                frame,"Child Detected",
                                (x1,y1-10),
                                self.cv2.FONT_HERSHEY_SIMPLEX,
                                0.6,(0,255,0),2)

            # DeepFace emotion
            if self.deepface_ok and fc % 20 == 0:
                threading.Thread(
                    target=self._emotion,
                    args=(frame.copy(),),
                    daemon=True).start()

            # رسم overlay
            self._draw(frame)

            # عرض نافذة Zoom-style
            self.cv2.imshow(
                "🤖 Pepper Therapy - Zoom Session", frame)
            if self.cv2.waitKey(1) & 0xFF == ord('q'):
                break
            time.sleep(0.025)

    def _emotion(self, frame):
        try:
            res = self.DeepFace.analyze(
                frame, actions=['emotion'],
                enforce_detection=False, silent=True)
            if res:
                em = res[0]['dominant_emotion']
                state["emotion"] = em
                state["face_detected"] = True

                # إرسال للسيرفر
                try:
                    requests.post(
                        'http://localhost:5009/update_context',
                        json={"emotion": em}, timeout=0.5)
                except: pass

                # تحديث engagement
                scores = res[0]['emotion']
                pos = scores.get('happy',0)+scores.get('surprise',0)
                neg = scores.get('sad',0)+scores.get('angry',0)+\
                      scores.get('fear',0)
                if pos > 40:   state["engagement"] = "high"
                elif neg > 50: state["engagement"] = "distressed"
                else:          state["engagement"] = "moderate"
        except: pass

    def _draw(self, frame):
        """overlay مثل Zoom"""
        h, w = frame.shape[:2]
        em  = state["emotion"]
        att = state["attention"]

        colors = {
            "happy":(0,255,100),"sad":(255,100,100),
            "angry":(0,0,255),"neutral":(200,200,200),
            "fear":(0,165,255),"surprise":(255,0,255)
        }
        col = colors.get(em,(255,255,255))

        # شريط معلومات أسفل
        overlay = frame.copy()
        self.cv2.rectangle(
            overlay,(0,h-70),(w,h),(0,0,0),-1)
        frame[:] = self.cv2.addWeighted(
            overlay,0.7,frame,0.3,0)

        self.cv2.putText(
            frame, f"😊 {em.upper()}",
            (10, h-45),
            self.cv2.FONT_HERSHEY_SIMPLEX,0.7,col,2)
        self.cv2.putText(
            frame, f"Attention: {att}%",
            (10, h-18),
            self.cv2.FONT_HERSHEY_SIMPLEX,0.55,
            (255,255,100),1)
        self.cv2.putText(
            frame, f"Protocol: {state['current_protocol']}",
            (w-200, h-18),
            self.cv2.FONT_HERSHEY_SIMPLEX,0.55,
            (100,200,255),1)

        # نقطة تسجيل حمراء
        self.cv2.circle(frame,(w-20,20),8,(0,0,255),-1)
        self.cv2.putText(
            frame,"REC",(w-60,28),
            self.cv2.FONT_HERSHEY_SIMPLEX,
            0.5,(0,0,255),1)

    def _simulate(self):
        pool = ["happy","happy","neutral","neutral","sad","surprise"]
        while True:
            state["emotion"]      = random.choice(pool)
            state["face_detected"]= random.random() > 0.1
            state["attention"]    = random.randint(50,90)
            time.sleep(4)

    def stop(self):
        self.running = False
        if self.cap: self.cap.release()
        try:
            self.cv2.destroyAllWindows()
        except: pass

# ========== ASD CHILD ==========
class ASDChild:
    PARAMS = {
        "mild":     {"r":0.75,"a":12,"m":0.05,"rep":0.20},
        "moderate": {"r":0.45,"a":7, "m":0.15,"rep":0.45},
        "severe":   {"r":0.15,"a":3, "m":0.35,"rep":0.75},
    }
    BEHAVIORS = {
        "mild":    ["wandering","smiling","pointing","eye_contact"],
        "moderate":["hand_flapping","rocking","ignoring","fixating"],
        "severe":  ["spinning","covering_ears","running","stimming"],
    }
    COLORS = {
        "mild":[0.2,0.85,0.2,1],
        "moderate":[1.0,0.6,0.0,1],
        "severe":[0.9,0.15,0.15,1],
    }

    def __init__(self, name, pos, severity):
        self.name=name; self.base=list(pos)
        self.pos=list(pos); self.severity=severity
        self.pr=self.PARAMS[severity]
        self.behavior="wandering"; self.emotion="calm"
        self.meltdown=False; self.melt_t=0
        self.last_t=time.time()
        self.vel=[random.uniform(-0.005,0.005),
                  random.uniform(-0.005,0.005)]
        self.off=[0.0,0.0]
        self.interactions=0; self.successes=0; self.score=0
        self.tid=None; self.hid=None
        self._build()

    def _build(self):
        col=self.COLORS[self.severity]
        vs=p.createVisualShape(
            p.GEOM_BOX,halfExtents=[0.13,0.09,0.21],rgbaColor=col)
        cs=p.createCollisionShape(
            p.GEOM_BOX,halfExtents=[0.13,0.09,0.21])
        self.tid=p.createMultiBody(
            0,cs,vs,[self.pos[0],self.pos[1],0.41])
        vs2=p.createVisualShape(
            p.GEOM_SPHERE,radius=0.11,rgbaColor=[1,0.82,0.65,1])
        cs2=p.createCollisionShape(p.GEOM_SPHERE,radius=0.11)
        self.hid=p.createMultiBody(
            0,cs2,vs2,[self.pos[0],self.pos[1],0.74])
        em={"mild":"🟢","moderate":"🟠","severe":"🔴"}
        p.addUserDebugText(
            f"{self.name} {em[self.severity]}",
            [self.pos[0],self.pos[1],1.05],
            [0,0,0],textSize=0.9,lifeTime=0)

    def update(self):
        now=time.time()
        if now-self.last_t > self.pr["a"]:
            self.last_t=now
            if not self.meltdown and random.random()<self.pr["m"]:
                self.meltdown=True; self.melt_t=now
                self.emotion="overwhelmed"
                self.behavior=random.choice(
                    self.BEHAVIORS[self.severity])
                print(f"[{self.name}] ⚠️  MELTDOWN!")
            elif self.meltdown and now-self.melt_t>10:
                self.meltdown=False
                self.emotion="calm"; self.behavior="wandering"
            else:
                pool=self.BEHAVIORS[self.severity] \
                    if random.random()<self.pr["rep"] \
                    else ["wandering"]
                self.behavior=random.choice(pool)
                self.emotion=random.choice(
                    ["calm","happy","anxious","sad"])

        spd=0.005 if not self.meltdown else 0.009
        self.vel[0]+=random.uniform(-0.001,0.001)
        self.vel[1]+=random.uniform(-0.001,0.001)
        self.vel[0]=max(-spd,min(spd,self.vel[0]))
        self.vel[1]=max(-spd,min(spd,self.vel[1]))
        self.off[0]+=self.vel[0]
        self.off[1]+=self.vel[1]
        if abs(self.off[0])>0.4: self.vel[0]*=-1
        if abs(self.off[1])>0.4: self.vel[1]*=-1
        self.pos[0]=self.base[0]+self.off[0]
        self.pos[1]=self.base[1]+self.off[1]
        try:
            p.resetBasePositionAndOrientation(
                self.tid,[self.pos[0],self.pos[1],0.41],[0,0,0,1])
            p.resetBasePositionAndOrientation(
                self.hid,[self.pos[0],self.pos[1],0.74],[0,0,0,1])
        except: pass

    def respond(self):
        self.interactions+=1
        if self.meltdown: return False
        base=self.pr["r"]
        if state["emotion"]=="happy":      base+=0.15
        if state["attention"]>70:          base+=0.10
        if state["engagement"]=="high":    base+=0.10
        if state["engagement"]=="distressed": base-=0.20
        ok=random.random()<max(0.05,min(0.95,base))
        if ok:
            self.successes+=1; self.score+=10
            state["total_score"]+=10
        return ok

    def rate(self):
        if not self.interactions: return 0
        return round(self.successes/self.interactions*100,1)

# ========== MAIN SIM ==========
class ZoomTherapySim:
    def __init__(self):
        self.voice  = Voice()
        self.camera = ZoomCamera()

        # PyBullet
        self.sim=SimulationManager()
        self.client=self.sim.launchSimulation(gui=True)
        p.setRealTimeSimulation(1)
        p.setGravity(0,0,-9.81)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.loadURDF("plane.urdf")
        self._build_room()

        # Pepper
        print("🤖 Spawning Pepper...")
        self.pepper=self.sim.spawnPepper(self.client)
        self.pepper.goToPosture("Stand",0.5)
        self.rx=0.0; self.ry=0.0
        self.head_yaw=0.0
        self.auto_walk=True
        self.is_talking=False

        # أطفال
        self.children=[
            ASDChild("Ahmed",[ 1.5,-1.2,0],"mild"),
            ASDChild("Sara", [-1.2, 1.3,0],"moderate"),
            ASDChild("Yusuf",[ 0.5,-2.0,0],"severe"),
            ASDChild("Layla",[ 2.8,-0.2,0],"moderate"),
            ASDChild("Omar", [-2.2,-1.0,0],"mild"),
        ]

        self.balloons=[]
        self._create_balloons()

        self.kid_idx=0
        self.protocols=["ABA","TEACCH","DTT","TIE"]
        self.p_idx=0

        # Threads
        threading.Thread(target=self._sim_loop,      daemon=True).start()
        threading.Thread(target=self._children_loop, daemon=True).start()
        threading.Thread(target=self._walk_loop,     daemon=True).start()
        threading.Thread(target=self._arm_loop,      daemon=True).start()
        threading.Thread(target=self._cmd_loop,      daemon=True).start()

        p.resetDebugVisualizerCamera(7,45,-35,[0,0,0.5])
        time.sleep(2)

        self._speak("Hello! I am Pepper. Starting therapy session!")
        threading.Thread(
            target=self._therapy_loop,daemon=True).start()

    def _build_room(self):
        print("🏠 Building room...")
        wc=[0.85,0.85,0.9,1]
        for pos,ext in [
            ([0,-4,1.1],[5,0.1,1.1]),([0,4,1.1],[5,0.1,1.1]),
            ([5,0,1.1],[0.1,4,1.1]),([-5,0,1.1],[0.1,4,1.1])]:
            p.createMultiBody(0,-1,
                p.createVisualShape(
                    p.GEOM_BOX,halfExtents=ext,rgbaColor=wc),pos)
        p.createMultiBody(0,-1,
            p.createVisualShape(p.GEOM_BOX,
                halfExtents=[4.5,3.5,0.02],
                rgbaColor=[0.5,0.4,0.3,1]),[0,0,0.01])
        # Protocol labels
        for txt,pos in [
            ("ABA ROOM",    [-4, 3,1.8]),
            ("TEACCH ROOM", [ 0, 4,1.8]),
            ("DTT ROOM",    [ 4, 3,1.8]),
            ("TIE ROOM",    [-4,-3,1.8]),
        ]:
            p.addUserDebugText(
                txt,pos,[0.3,0.3,0.9],textSize=1.2,lifeTime=0)
        print("✅ Room ready!")

    def _create_balloons(self):
        cols=[[1,0.2,0.2,1],[0.2,1,0.2,1],[0.2,0.2,1,1],
              [1,1,0.2,1],[1,0.5,0.2,1],[0.8,0.2,0.8,1]]
        for i in range(8):
            vs=p.createVisualShape(
                p.GEOM_SPHERE,radius=0.15,
                rgbaColor=cols[i%len(cols)])
            bid=p.createMultiBody(0,-1,vs,
                [random.uniform(-3,3),
                 random.uniform(-2,2),
                 random.uniform(0.8,2.2)])
            self.balloons.append({
                "id":bid,
                "x":random.uniform(-3,3),
                "y":random.uniform(-2,2),
                "z":random.uniform(0.8,2.2),
                "spd":random.uniform(0.01,0.03)
            })

    def _sim_loop(self):
        while True:
            p.stepSimulation()
            # تحريك البالونات
            for b in self.balloons:
                b["z"]+=b["spd"]
                if b["z"]>2.8:
                    b["z"]=0.6
                    b["x"]=random.uniform(-3,3)
                    b["y"]=random.uniform(-2,2)
                try:
                    p.resetBasePositionAndOrientation(
                        b["id"],
                        [b["x"],b["y"],b["z"]],
                        [0,0,0,1])
                except: pass
            time.sleep(1/240.)

    def _children_loop(self):
        while True:
            for c in self.children: c.update()
            time.sleep(0.05)

    def _walk_loop(self):
        t=0
        while True:
            if self.auto_walk:
                t+=0.015
                self.rx+=0.018*math.cos(t*0.4)
                self.ry+=0.018*math.sin(t*0.5)
                self.rx=max(-3.5,min(3.5,self.rx))
                self.ry=max(-2.8,min(2.8,self.ry))
                try:
                    self.pepper.setPosition([self.rx,self.ry,0.8])
                except: pass
            time.sleep(0.06)

    def _arm_loop(self):
        phase=0
        while True:
            try:
                if self.is_talking:
                    phase+=0.07
                    L=0.5+0.3*math.sin(phase)
                    R=0.5+0.3*math.sin(phase+math.pi*0.6)
                    self.pepper.setAngles("LShoulderPitch",L,0.07)
                    self.pepper.setAngles("RShoulderPitch",R,0.07)
                    self.pepper.setAngles(
                        "LElbowRoll",
                        -0.3-0.15*math.sin(phase*0.7),0.07)
                    self.pepper.setAngles(
                        "RElbowRoll",
                        0.3+0.15*math.sin(phase*0.7),0.07)
                else:
                    self.pepper.setAngles("LShoulderPitch",1.0,0.04)
                    self.pepper.setAngles("RShoulderPitch",1.0,0.04)
            except: pass
            time.sleep(0.04)

    def _cmd_loop(self):
        """تنفيذ أوامر الداشبورد"""
        while True:
            cmd=state.get("simulation_cmd")
            if cmd:
                state["simulation_cmd"]=None
                if cmd=="balloon":
                    self.auto_walk=True
                    self._speak("Balloon chase time!")
                elif cmd=="dance":
                    self._dance()
                elif cmd=="dtt":
                    child=self.children[self.kid_idx%len(self.children)]
                    self._run_protocol("DTT",child)
                elif cmd=="teacch":
                    child=self.children[self.kid_idx%len(self.children)]
                    self._run_protocol("TEACCH",child)
                elif cmd=="stop":
                    self.auto_walk=False
                    self._speak("Stopping.")
            time.sleep(0.5)

    def _move_to(self, child):
        self.auto_walk=False
        state["current_child"]=child.name
        tx,ty=child.pos[0],child.pos[1]
        for _ in range(100):
            dx=tx-self.rx; dy=ty-self.ry
            dist=math.sqrt(dx**2+dy**2)
            if dist<0.85: break
            step=min(0.055,dist-0.75)
            self.rx+=dx/dist*step
            self.ry+=dy/dist*step
            self.head_yaw=math.atan2(dy,dx)
            try:
                self.pepper.setPosition([self.rx,self.ry,0.8])
                self.pepper.setAngles(
                    "HeadYaw",self.head_yaw*0.5,0.1)
                self.pepper.setAngles("HeadPitch",-0.1,0.08)
            except: pass
            time.sleep(0.04)
        # اتجه للطفل
        dx=tx-self.rx; dy=ty-self.ry
        self.head_yaw=math.atan2(dy,dx)
        try:
            self.pepper.setAngles(
                "HeadYaw",self.head_yaw*0.5,0.12)
        except: pass
        time.sleep(0.4)

    def _speak(self, text, child=None):
        self.is_talking=True
        try:
            pos=p.getBasePositionAndOrientation(
                self.pepper.body)[0]
            p.addUserDebugText(
                text[:55],[pos[0],pos[1],pos[2]+1.3],
                [0,0,0],textSize=0.85,lifeTime=5)
        except: pass
        _add_log(f"Pepper: {text[:60]}",
            "info",state["current_protocol"])
        self.voice.say(text)
        self.is_talking=False

    def _dance(self):
        self._speak("Let us dance together!")
        try:
            for _ in range(4):
                self.pepper.setAngles("LShoulderPitch",0.2,0.2)
                self.pepper.setAngles("RShoulderPitch",0.9,0.2)
                self.pepper.setAngles("HeadYaw",0.3,0.15)
                time.sleep(0.25)
                self.pepper.setAngles("LShoulderPitch",0.9,0.2)
                self.pepper.setAngles("RShoulderPitch",0.2,0.2)
                self.pepper.setAngles("HeadYaw",-0.3,0.15)
                time.sleep(0.25)
            self.pepper.setAngles("HeadYaw",0,0.1)
        except: pass

    def _celebrate(self, child_name):
        try:
            for _ in range(2):
                self.pepper.setAngles("LShoulderPitch",0.1,0.2)
                self.pepper.setAngles("RShoulderPitch",0.1,0.2)
                time.sleep(0.2)
                self.pepper.setAngles("LShoulderPitch",0.9,0.2)
                self.pepper.setAngles("RShoulderPitch",0.9,0.2)
                time.sleep(0.2)
        except: pass

    def _adapt(self, child):
        """تكيّف مع المشاعر"""
        em=state["emotion"]
        eng=state["engagement"]
        if eng=="distressed" or em in ["angry","fear"]:
            self._speak(
                f"It is okay {child.name}. Breathe with me.")
            _add_log(f"Meltdown/distress - sensory break",
                "fail")
            time.sleep(3)
            return "break"
        if state["attention"]<30:
            self._speak(f"Hey {child.name}! Look at me!")
            return "redirect"
        return "continue"

    def _run_protocol(self, protocol, child):
        state["current_protocol"]=protocol
        _add_log(
            f"Starting {protocol} with {child.name}","info")

        if protocol=="ABA":
            self._speak(
                f"Hello {child.name}! ABA time!")
            instrs={
                "mild":  ["Point to ball","Show happy face",
                          "Count to 3","What color is this?"],
                "moderate":["Clap hands","Touch nose",
                            "Wave hello","Stand up"],
                "severe":  ["Look at me","Touch nose","Clap"],
            }
            for instr in random.sample(
                    instrs[child.severity],
                    min(3,len(instrs[child.severity]))):
                if self._adapt(child)=="break": continue
                self._speak(f"{child.name}, {instr}!")
                time.sleep(1.5)
                ok=child.respond()
                if ok:
                    self._speak(
                        random.choice(["Amazing!","Super star!",
                                       "You did it!"]))
                    self._celebrate(child.name)
                    _add_log(f"ABA: {instr} → SUCCESS","success")
                else:
                    self._speak(f"Let us try again! {instr}")
                    _add_log(f"ABA: {instr} → retry","fail")
                time.sleep(2)

        elif protocol=="TEACCH":
            self._speak(
                f"Let us check our schedule {child.name}!")
            schedule=[
                ("Greeting",  f"Good morning {child.name}!"),
                ("Emotion",   f"Show me happy face {child.name}!"),
                ("Work Task", f"Let us sort colors {child.name}!"),
                ("Break",     "Breathe with me. In... out..."),
                ("Joint Att", f"Look {child.name}! Red ball!"),
                ("Closing",   f"Great job {child.name}! Done!"),
            ]
            for act, txt in schedule:
                if self._adapt(child)=="break": continue
                self._speak(txt)
                ok=child.respond()
                if ok: child.score+=15; state["total_score"]+=15
                _add_log(
                    f"TEACCH: {act} → {'✓' if ok else '✗'}",
                    "success" if ok else "fail")
                time.sleep(2)

        elif protocol=="DTT":
            self._speak(f"DTT time {child.name}!")
            tasks=[("Clap hands","clap"),
                   ("Touch nose","nose"),
                   ("Wave hello","wave"),
                   ("Stand up","stand")]
            for txt,_ in random.sample(tasks,min(3,len(tasks))):
                if self._adapt(child)=="break": continue
                self._speak(f"{child.name}, {txt}!")
                time.sleep(1.5)
                ok=child.respond()
                if ok:
                    child.score+=12; state["total_score"]+=12
                    self._speak("Amazing!")
                    _add_log(f"DTT: {txt} → CORRECT","success")
                else:
                    self._speak(f"Error correction: {txt}")
                    _add_log(f"DTT: {txt} → ERROR","fail")
                time.sleep(2)

        elif protocol=="TIE":
            self._speak(
                f"Hello {child.name}. "
                "I am adapting just for you!")
            for _ in range(5):
                em=state["emotion"]
                att=state["attention"]
                eng=state["engagement"]

                if eng=="distressed":
                    self._speak("Let us calm down together.")
                    time.sleep(3)
                elif att<35:
                    self._speak(f"{child.name}! Look here!")
                elif em=="happy" and att>65:
                    self._speak(
                        "You are doing great! "
                        "Let us try something harder!")
                    ok=child.respond()
                    if ok:
                        child.score+=20
                        state["total_score"]+=20
                        self._speak("Incredible!")
                        _add_log("TIE: advance → SUCCESS",
                            "success")
                else:
                    self._speak(
                        f"Keep going {child.name}!")
                    ok=child.respond()
                    if ok:
                        child.score+=10
                        state["total_score"]+=10
                        _add_log("TIE: maintain → SUCCESS",
                            "success")
                time.sleep(2.5)

    def _therapy_loop(self):
        print("\n🏥 THERAPY LOOP STARTED!\n")
        time.sleep(2)
        while True:
            child=self.children[self.kid_idx%len(self.children)]
            proto=self.protocols[self.p_idx%len(self.protocols)]
            self.kid_idx+=1; self.p_idx+=1

            print(f"\n[THERAPY] → {child.name} | {proto}")
            _add_log(f"Moving to {child.name}","info",proto)

            self._move_to(child)
            self._run_protocol(proto,child)

            print(f"[{child.name}] "
                  f"Rate:{child.rate()}% Score:{child.score}")

            self.auto_walk=True
            time.sleep(8)

    def run(self):
        print("\n" + "="*55)
        print("✅ ZOOM THERAPY SESSION ACTIVE")
        print("="*55)
        print("🌐 Dashboard: http://localhost:5009")
        print("📹 Camera: Zoom-style window")
        print("Commands: 'report' | 'exit'")
        print("="*55 + "\n")

        while True:
            try:
                cmd=input("> ").strip().lower()
                if cmd=="report":
                    print("\n📊 SESSION REPORT")
                    print("="*45)
                    for c in self.children:
                        bar="█"*int(c.rate()/10)+\
                            "░"*(10-int(c.rate()/10))
                        print(f"👦 {c.name:6} "
                              f"({c.severity:8}) "
                              f"[{bar}] {c.rate()}% "
                              f"Score:{c.score}")
                    print(f"\n😊 Emotion: {state['emotion']}")
                    print(f"📈 Total Score: {state['total_score']}")
                    print("="*45)
                elif cmd in ["exit","quit"]:
                    self.camera.stop()
                    break
            except KeyboardInterrupt:
                self.camera.stop()
                break

# ========== RUN ALL ==========
if __name__ == "__main__":
    # Flask في thread منفصل
    threading.Thread(target=run_flask, daemon=True).start()
    time.sleep(1)

    # تشغيل الكاميرا الموجودة
    try:
        import subprocess
        subprocess.Popen([
            "python3",
            "/home/lamya/pepper_duo/src/camera_yolo_emotion.py"
        ])
        print("✅ camera_yolo_emotion.py launched!")
    except Exception as e:
        print(f"⚠️  Camera script: {e}")

    time.sleep(1)
    sim = ZoomTherapySim()
    sim.run()
