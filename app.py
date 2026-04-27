"""
app.py  –  ASD Companion Robot  |  Parental Dashboard
══════════════════════════════════════════════════════
Flask + Flask-SocketIO backend.

Routes:
  GET  /                 → main dashboard SPA
  GET  /health           → health check (Docker)
  GET  /api/profiles     → list child profiles
  POST /api/profiles     → create child profile
  PUT  /api/profiles/<id>→ update profile
  GET  /api/schedule/<id>→ get TEACCH schedule for profile
  PUT  /api/schedule/<id>→ update TEACCH schedule
  GET  /api/sessions/<id>→ get session logs for profile
  POST /api/sessions     → receive session log from ROS bridge

WebSocket events (SocketIO):
  child_state  → real-time child state from ROS
  session_log  → real-time trial events
"""

import os, json, datetime
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from flask_sqlalchemy import SQLAlchemy

# ── App setup ────────────────────────────────────────────────
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "asd_dev_secret")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", "sqlite:///asd_dashboard.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

CORS(app)
db      = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")


# ── Database Models ──────────────────────────────────────────
class ChildProfile(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(100), nullable=False)
    age         = db.Column(db.Integer)
    asd_level   = db.Column(db.Integer, default=1)      # DSM-5 levels 1–3
    notes       = db.Column(db.Text, default="")
    created_at  = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    sessions    = db.relationship("SessionLog", backref="profile", lazy=True)
    schedule    = db.relationship("TherapySchedule", backref="profile",
                                  uselist=False, lazy=True)

    def to_dict(self):
        return {
            "id": self.id, "name": self.name, "age": self.age,
            "asd_level": self.asd_level, "notes": self.notes,
            "created_at": self.created_at.isoformat(),
        }


class TherapySchedule(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    profile_id = db.Column(db.Integer, db.ForeignKey("child_profile.id"),
                            nullable=False)
    tasks_json = db.Column(db.Text, default="[]")
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow,
                            onupdate=datetime.datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id, "profile_id": self.profile_id,
            "tasks": json.loads(self.tasks_json),
            "updated_at": self.updated_at.isoformat(),
        }


class SessionLog(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    profile_id  = db.Column(db.Integer, db.ForeignKey("child_profile.id"),
                             nullable=False)
    date        = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    total_trials= db.Column(db.Integer, default=0)
    correct     = db.Column(db.Integer, default=0)
    log_json    = db.Column(db.Text, default="[]")

    def to_dict(self):
        return {
            "id": self.id, "profile_id": self.profile_id,
            "date": self.date.isoformat(),
            "total_trials": self.total_trials,
            "correct": self.correct,
            "accuracy": round(self.correct / max(self.total_trials, 1) * 100, 1),
            "log": json.loads(self.log_json),
        }


# ── Init DB ──────────────────────────────────────────────────
with app.app_context():
    db.create_all()
    # Seed default profile
    if ChildProfile.query.count() == 0:
        default = ChildProfile(
            name="Default Child", age=6, asd_level=1,
            notes="Default profile for testing")
        db.session.add(default)
        db.session.commit()
        sched = TherapySchedule(profile_id=default.id, tasks_json=json.dumps([
            {"name": "color_matching", "prompt": "Can you match the colors?",
             "duration_s": 120, "reinforcement": "verbal+led"},
            {"name": "shape_sorting",  "prompt": "Let's sort the shapes!",
             "duration_s": 120, "reinforcement": "verbal+sound"},
            {"name": "name_recognition","prompt": "Point to the picture of a cat!",
             "duration_s": 90,  "reinforcement": "verbal"},
        ]))
        db.session.add(sched)
        db.session.commit()


# ── Health ───────────────────────────────────────────────────
@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "asd_dashboard"})


# ── Child Profiles ───────────────────────────────────────────
@app.route("/api/profiles", methods=["GET"])
def list_profiles():
    return jsonify([p.to_dict() for p in ChildProfile.query.all()])


@app.route("/api/profiles", methods=["POST"])
def create_profile():
    data = request.get_json()
    p = ChildProfile(
        name=data["name"], age=data.get("age", 6),
        asd_level=data.get("asd_level", 1), notes=data.get("notes", ""))
    db.session.add(p)
    db.session.commit()
    # create empty schedule
    sched = TherapySchedule(profile_id=p.id)
    db.session.add(sched)
    db.session.commit()
    return jsonify(p.to_dict()), 201


@app.route("/api/profiles/<int:pid>", methods=["PUT"])
def update_profile(pid):
    p    = ChildProfile.query.get_or_404(pid)
    data = request.get_json()
    for field in ("name", "age", "asd_level", "notes"):
        if field in data:
            setattr(p, field, data[field])
    db.session.commit()
    return jsonify(p.to_dict())


# ── TEACCH Schedule ──────────────────────────────────────────
@app.route("/api/schedule/<int:pid>", methods=["GET"])
def get_schedule(pid):
    sched = TherapySchedule.query.filter_by(profile_id=pid).first_or_404()
    return jsonify(sched.to_dict())


@app.route("/api/schedule/<int:pid>", methods=["PUT"])
def update_schedule(pid):
    sched = TherapySchedule.query.filter_by(profile_id=pid).first_or_404()
    data  = request.get_json()
    sched.tasks_json  = json.dumps(data.get("tasks", []))
    sched.updated_at  = datetime.datetime.utcnow()
    db.session.commit()

    # Push updated schedule to ROS via SocketIO
    socketio.emit("schedule_update", {
        "profile_id": pid,
        "tasks": data.get("tasks", [])
    })
    return jsonify(sched.to_dict())


# ── Session Logs ─────────────────────────────────────────────
@app.route("/api/sessions/<int:pid>", methods=["GET"])
def get_sessions(pid):
    sessions = (SessionLog.query
                .filter_by(profile_id=pid)
                .order_by(SessionLog.date.desc())
                .limit(50).all())
    return jsonify([s.to_dict() for s in sessions])


@app.route("/api/sessions", methods=["POST"])
def receive_session():
    """Called by the ROS dashboard_bridge_node to save session logs."""
    data    = request.get_json()
    log_entries = data.get("log", [])
    correct = sum(1 for e in log_entries if e.get("event") == "trial_correct")

    session = SessionLog(
        profile_id   = data.get("profile_id", 1),
        total_trials = data.get("total_trials", 0),
        correct      = correct,
        log_json     = json.dumps(log_entries),
    )
    db.session.add(session)
    db.session.commit()

    # Broadcast to connected dashboard clients
    socketio.emit("session_complete", session.to_dict())
    return jsonify(session.to_dict()), 201


# ── SocketIO: real-time child state relay ────────────────────
@socketio.on("child_state")
def relay_child_state(data):
    """ROS bridge sends child_state; we broadcast to all dashboard clients."""
    emit("child_state", data, broadcast=True)


@socketio.on("session_log")
def relay_session_log(data):
    emit("session_log", data, broadcast=True)


# ── Minimal SPA ──────────────────────────────────────────────
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ASD Companion Robot – Dashboard</title>
<style>
  body { font-family: Arial,sans-serif; margin:0; background:#f0f4f8; color:#222; }
  header { background:#1F3864; color:#fff; padding:1rem 2rem;
            display:flex; align-items:center; gap:1rem; }
  header h1 { margin:0; font-size:1.3rem; }
  .badge { background:#2E75B6; border-radius:4px; padding:2px 8px; font-size:.8rem; }
  main { max-width:1100px; margin:2rem auto; padding:0 1rem; }
  .grid { display:grid; grid-template-columns:1fr 1fr; gap:1.5rem; }
  .card { background:#fff; border-radius:8px; padding:1.5rem;
          box-shadow:0 2px 8px rgba(0,0,0,.08); }
  .card h2 { margin-top:0; color:#1F3864; font-size:1rem; }
  .state-box { background:#e8f5e9; border-radius:6px; padding:1rem;
               font-family:monospace; font-size:.85rem; min-height:80px; }
  .emotion { display:inline-block; padding:3px 10px; border-radius:12px;
             font-weight:bold; font-size:.9rem; }
  .happy    { background:#c8e6c9; color:#2e7d32; }
  .neutral  { background:#e3f2fd; color:#1565c0; }
  .sad      { background:#e1bee7; color:#6a1b9a; }
  .angry    { background:#ffcdd2; color:#b71c1c; }
  .fear     { background:#fff3e0; color:#e65100; }
  table { width:100%; border-collapse:collapse; font-size:.85rem; }
  th { background:#1F3864; color:#fff; padding:6px 10px; text-align:left; }
  td { padding:6px 10px; border-bottom:1px solid #eee; }
  tr:hover td { background:#f5f9ff; }
  .dot { width:10px; height:10px; border-radius:50%; display:inline-block; }
  .dot.green { background:#4caf50; }  .dot.red { background:#f44336; }
  button { background:#2E75B6; color:#fff; border:none; border-radius:4px;
           padding:6px 14px; cursor:pointer; font-size:.85rem; }
  button:hover { background:#1F3864; }
</style>
</head>
<body>
<header>
  <h1>🤖 ASD Companion Robot — Parental Dashboard</h1>
  <span class="badge">Omdurman Islamic University</span>
  <span id="conn_status" class="badge" style="background:#f44336">Disconnected</span>
</header>
<main>
  <div class="grid">
    <div class="card">
      <h2>📡 Live Child State</h2>
      <div class="state-box" id="state_box">Waiting for simulation data…</div>
    </div>
    <div class="card">
      <h2>🔄 Current TIE Phase</h2>
      <div class="state-box" id="phase_box">—</div>
    </div>
    <div class="card" style="grid-column:1/-1">
      <h2>📋 Recent Session Events</h2>
      <table>
        <thead><tr><th>Time</th><th>Event</th><th>Details</th></tr></thead>
        <tbody id="log_table"><tr><td colspan="3">No events yet.</td></tr></tbody>
      </table>
    </div>
  </div>
  <p style="color:#888;font-size:.8rem;margin-top:2rem;text-align:center">
    REST API: <code>GET /api/profiles</code> · <code>GET/PUT /api/schedule/&lt;id&gt;</code>
    · <code>GET /api/sessions/&lt;id&gt;</code> · Real-time via SocketIO ws://localhost:5000
  </p>
</main>
<script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.2/socket.io.min.js"></script>
<script>
const socket = io();
const stateBox = document.getElementById('state_box');
const phaseBox = document.getElementById('phase_box');
const logTable = document.getElementById('log_table');
const connBadge = document.getElementById('conn_status');

socket.on('connect', () => {
  connBadge.textContent = 'Connected';
  connBadge.style.background = '#4caf50';
});
socket.on('disconnect', () => {
  connBadge.textContent = 'Disconnected';
  connBadge.style.background = '#f44336';
});
socket.on('child_state', (d) => {
  stateBox.innerHTML =
    `<b>Emotion:</b> <span class="emotion ${d.emotion}">${d.emotion}</span>
     (conf: ${(d.emotion_conf*100).toFixed(0)}%)<br>
     <b>Activity:</b> ${d.activity}<br>
     <b>Child present:</b> ${d.child_present ? '✅' : '❌'}<br>
     <b>Timestamp:</b> ${new Date(d.timestamp*1000).toLocaleTimeString()}`;
});
socket.on('session_log', (d) => {
  if (logTable.rows[0].cells.length === 1) logTable.innerHTML = '';
  const tr = logTable.insertRow(0);
  const t = new Date(d.timestamp*1000).toLocaleTimeString();
  tr.innerHTML = `<td>${t}</td><td>${d.event}</td>
    <td><code>${JSON.stringify(d.data||{})}</code></td>`;
  if (logTable.rows.length > 50) logTable.deleteRow(-1);
});
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(DASHBOARD_HTML)


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
