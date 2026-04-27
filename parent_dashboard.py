"""
Parental Dashboard - Flask Web App
View session reports, configure therapy goals, monitor child progress
"""

from flask import Flask, render_template_string, request, jsonify
import json
import os
import glob
from datetime import datetime

app = Flask(__name__)

# ========== Config Storage ==========
CONFIG_FILE = "therapy_config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {
        "child_name": "My Child",
        "severity": "moderate",
        "primary_goal": "joint_attention",
        "reinforcer_type": "verbal_praise",
        "session_duration": 30,
        "prompt_level": "gestural",
        "schedule_type": "morning",
        "daily_goals": ["eye_contact", "greet_robot", "complete_DTT"],
        "notes": ""
    }

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

def load_sessions():
    sessions = []
    for f in sorted(glob.glob("session_*.json"), reverse=True)[:10]:
        try:
            with open(f) as fp:
                sessions.append(json.load(fp))
        except:
            pass
    return sessions

# ========== HTML Template ==========
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🤖 ASD Therapy Dashboard</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Segoe UI', sans-serif; background: #f0f4f8; color: #333; }

  .header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white; padding: 20px 30px;
    display: flex; align-items: center; gap: 15px;
  }
  .header h1 { font-size: 1.6em; }
  .header p { font-size: 0.9em; opacity: 0.85; }

  .container { max-width: 1100px; margin: 0 auto; padding: 25px 20px; }

  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
  .grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 15px; }

  .card {
    background: white; border-radius: 12px;
    padding: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.08);
  }
  .card h2 { font-size: 1.1em; color: #555; margin-bottom: 15px;
             border-bottom: 2px solid #667eea; padding-bottom: 8px; }

  .stat-box {
    background: linear-gradient(135deg, #667eea, #764ba2);
    color: white; border-radius: 10px; padding: 18px;
    text-align: center;
  }
  .stat-box .number { font-size: 2.2em; font-weight: bold; }
  .stat-box .label { font-size: 0.85em; opacity: 0.9; margin-top: 4px; }

  .severity-badge {
    display: inline-block; padding: 4px 12px; border-radius: 20px;
    font-size: 0.85em; font-weight: bold; color: white;
  }
  .mild { background: #27ae60; }
  .moderate { background: #e67e22; }
  .severe { background: #e74c3c; }

  form label { display: block; margin: 12px 0 4px; font-weight: 600; font-size: 0.9em; color: #555; }
  form input, form select, form textarea {
    width: 100%; padding: 9px 12px; border: 1.5px solid #ddd;
    border-radius: 8px; font-size: 0.9em;
    transition: border-color 0.2s;
  }
  form input:focus, form select:focus { border-color: #667eea; outline: none; }

  .btn {
    background: linear-gradient(135deg, #667eea, #764ba2);
    color: white; border: none; padding: 11px 25px;
    border-radius: 8px; cursor: pointer; font-size: 0.95em;
    margin-top: 15px; width: 100%; font-weight: 600;
    transition: opacity 0.2s;
  }
  .btn:hover { opacity: 0.9; }

  .session-item {
    border-left: 4px solid #667eea; padding: 12px 15px;
    margin: 10px 0; background: #f8f9ff; border-radius: 0 8px 8px 0;
  }
  .session-item .date { font-size: 0.8em; color: #888; }
  .session-item .rates { display: flex; gap: 15px; margin-top: 6px; }
  .session-item .rate { font-size: 0.85em; }
  .rate.good { color: #27ae60; }
  .rate.mid { color: #e67e22; }
  .rate.bad { color: #e74c3c; }

  .progress-bar { background: #eee; border-radius: 10px; height: 10px; margin: 6px 0; }
  .progress-fill { height: 10px; border-radius: 10px;
                   background: linear-gradient(90deg, #667eea, #764ba2); }

  .schedule-item {
    display: flex; align-items: center; gap: 12px;
    padding: 8px 0; border-bottom: 1px solid #f0f0f0;
  }
  .schedule-item .emoji { font-size: 1.3em; }
  .schedule-item .info { flex: 1; }
  .schedule-item .time { font-size: 0.8em; color: #888; }
  .schedule-item .act { font-weight: 600; font-size: 0.9em; }

  .alert {
    padding: 12px 15px; border-radius: 8px;
    margin: 10px 0; font-size: 0.9em;
  }
  .alert-success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
  .alert-info { background: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }

  @media (max-width: 700px) { .grid, .grid-3 { grid-template-columns: 1fr; } }
</style>
</head>
<body>

<div class="header">
  <div style="font-size:2.5em">🤖</div>
  <div>
    <h1>ASD Therapy Robot Dashboard</h1>
    <p>AI-Driven Companion Robot | Omdurman Islamic University</p>
  </div>
</div>

<div class="container">

  {% if saved %}
  <div class="alert alert-success">✅ Configuration saved successfully!</div>
  {% endif %}

  <!-- Stats Row -->
  <div class="grid-3" style="margin-bottom:20px">
    <div class="stat-box">
      <div class="number">{{ total_sessions }}</div>
      <div class="label">Total Sessions</div>
    </div>
    <div class="stat-box">
      <div class="number">{{ avg_dtt }}%</div>
      <div class="label">Avg DTT Success</div>
    </div>
    <div class="stat-box">
      <div class="number">{{ avg_ja }}%</div>
      <div class="label">Joint Attention Rate</div>
    </div>
  </div>

  <div class="grid">

    <!-- LEFT: Config Form -->
    <div>
      <div class="card">
        <h2>⚙️ Therapy Configuration</h2>
        <form method="POST" action="/save_config">
          <label>Child Name</label>
          <input type="text" name="child_name" value="{{ config.child_name }}">

          <label>ASD Severity Level</label>
          <select name="severity">
            <option value="mild"     {% if config.severity=='mild'     %}selected{% endif %}>🟢 Mild</option>
            <option value="moderate" {% if config.severity=='moderate' %}selected{% endif %}>🟠 Moderate</option>
            <option value="severe"   {% if config.severity=='severe'   %}selected{% endif %}>🔴 Severe</option>
          </select>

          <label>Primary Therapy Goal</label>
          <select name="primary_goal">
            <option value="joint_attention"     {% if config.primary_goal=='joint_attention'     %}selected{% endif %}>👀 Joint Attention</option>
            <option value="emotion_recognition" {% if config.primary_goal=='emotion_recognition' %}selected{% endif %}>🎭 Emotion Recognition</option>
            <option value="DTT"                 {% if config.primary_goal=='DTT'                 %}selected{% endif %}>📚 DTT Training</option>
            <option value="communication"       {% if config.primary_goal=='communication'       %}selected{% endif %}>💬 Communication</option>
          </select>

          <label>Prompt Level</label>
          <select name="prompt_level">
            <option value="verbal"   {% if config.prompt_level=='verbal'   %}selected{% endif %}>🗣️ Verbal</option>
            <option value="gestural" {% if config.prompt_level=='gestural' %}selected{% endif %}>👋 Gestural</option>
            <option value="physical" {% if config.prompt_level=='physical' %}selected{% endif %}>🤝 Physical</option>
            <option value="visual"   {% if config.prompt_level=='visual'   %}selected{% endif %}>🖼️ Visual</option>
          </select>

          <label>Reinforcer Type</label>
          <select name="reinforcer_type">
            <option value="verbal_praise" {% if config.reinforcer_type=='verbal_praise' %}selected{% endif %}>🗣️ Verbal Praise</option>
            <option value="token_economy" {% if config.reinforcer_type=='token_economy' %}selected{% endif %}>🏆 Token Economy</option>
            <option value="preferred_item"{% if config.reinforcer_type=='preferred_item'%}selected{% endif %}>⭐ Preferred Item</option>
          </select>

          <label>Session Duration (minutes)</label>
          <input type="number" name="session_duration" value="{{ config.session_duration }}" min="10" max="90">

          <label>Notes for Therapist</label>
          <textarea name="notes" rows="3" style="resize:vertical">{{ config.notes }}</textarea>

          <button type="submit" class="btn">💾 Save Configuration</button>
        </form>
      </div>
    </div>

    <!-- RIGHT: Sessions + Schedule -->
    <div>

      <!-- Current Child Status -->
      <div class="card" style="margin-bottom:20px">
        <h2>👦 Child Profile</h2>
        <p><strong>Name:</strong> {{ config.child_name }}</p>
        <p style="margin-top:8px"><strong>Severity:</strong>
          <span class="severity-badge {{ config.severity }}">{{ config.severity.upper() }}</span>
        </p>
        <p style="margin-top:8px"><strong>Goal:</strong> {{ config.primary_goal.replace('_',' ').title() }}</p>
        <p style="margin-top:8px"><strong>Prompt Level:</strong> {{ config.prompt_level.title() }}</p>
      </div>

      <!-- TEACCH Visual Schedule -->
      <div class="card" style="margin-bottom:20px">
        <h2>📅 Today's Visual Schedule (TEACCH)</h2>
        {% for item in schedule %}
        <div class="schedule-item">
          <div class="emoji">{{ item.visual }}</div>
          <div class="info">
            <div class="act">{{ item.activity.replace('_',' ').title() }}</div>
            <div class="time">{{ item.time }} | {{ item.duration }} min</div>
          </div>
        </div>
        {% endfor %}
      </div>

      <!-- Recent Sessions -->
      <div class="card">
        <h2>📊 Recent Sessions</h2>
        {% if sessions %}
          {% for s in sessions %}
          <div class="session-item">
            <div class="date">📅 {{ s.session_date }} {{ s.session_time }} | {{ s.duration_minutes }} min</div>
            <div class="rates">
              {% set dtt = s.therapy_results.DTT.success_rate %}
              {% set ja = s.therapy_results.joint_attention.success_rate %}
              {% set er = s.therapy_results.emotion_recognition.success_rate %}
              <span class="rate {% if dtt >= 70 %}good{% elif dtt >= 40 %}mid{% else %}bad{% endif %}">
                DTT: {{ dtt }}%
              </span>
              <span class="rate {% if ja >= 70 %}good{% elif ja >= 40 %}mid{% else %}bad{% endif %}">
                JA: {{ ja }}%
              </span>
              <span class="rate {% if er >= 70 %}good{% elif er >= 40 %}mid{% else %}bad{% endif %}">
                ER: {{ er }}%
              </span>
            </div>
            <div style="margin-top:8px">
              <div style="font-size:0.8em;color:#888">Overall Progress</div>
              <div class="progress-bar">
                <div class="progress-fill" style="width:{{ s.child_report.success_rate }}%"></div>
              </div>
              <div style="font-size:0.8em;color:#667eea">{{ s.child_report.success_rate }}% success rate</div>
            </div>
          </div>
          {% endfor %}
        {% else %}
          <div class="alert alert-info">ℹ️ No sessions yet. Run the simulation to generate session data!</div>
        {% endif %}
      </div>

    </div>
  </div>
</div>

</body>
</html>
"""

# ========== Routes ==========

@app.route("/")
def dashboard():
    config = load_config()
    sessions = load_sessions()

    # Calculate averages
    avg_dtt = avg_ja = 0
    if sessions:
        avg_dtt = round(sum(s["therapy_results"]["DTT"]["success_rate"] for s in sessions) / len(sessions), 1)
        avg_ja  = round(sum(s["therapy_results"]["joint_attention"]["success_rate"] for s in sessions) / len(sessions), 1)

    schedule = [
        {"time": "09:00", "activity": "greeting_circle",     "duration": 5,  "visual": "🌅"},
        {"time": "09:05", "activity": "emotion_check_in",    "duration": 3,  "visual": "😊"},
        {"time": "09:08", "activity": "DTT_session",         "duration": 10, "visual": "📚"},
        {"time": "09:18", "activity": "sensory_break",       "duration": 5,  "visual": "🎯"},
        {"time": "09:23", "activity": "joint_attention",     "duration": 8,  "visual": "👀"},
        {"time": "09:31", "activity": "free_play",           "duration": 5,  "visual": "🎮"},
        {"time": "09:36", "activity": "emotion_recognition", "duration": 7,  "visual": "🎭"},
        {"time": "09:43", "activity": "closing_circle",      "duration": 5,  "visual": "⭐"},
    ]

    return render_template_string(
        DASHBOARD_HTML,
        config=config,
        sessions=sessions,
        total_sessions=len(sessions),
        avg_dtt=avg_dtt,
        avg_ja=avg_ja,
        schedule=schedule,
        saved=False
    )

@app.route("/save_config", methods=["POST"])
def save_config_route():
    config = {
        "child_name":       request.form.get("child_name", "My Child"),
        "severity":         request.form.get("severity", "moderate"),
        "primary_goal":     request.form.get("primary_goal", "joint_attention"),
        "prompt_level":     request.form.get("prompt_level", "gestural"),
        "reinforcer_type":  request.form.get("reinforcer_type", "verbal_praise"),
        "session_duration": int(request.form.get("session_duration", 30)),
        "notes":            request.form.get("notes", ""),
        "schedule_type":    "morning"
    }
    save_config(config)

    config_data = load_config()
    sessions = load_sessions()
    avg_dtt = avg_ja = 0
    if sessions:
        avg_dtt = round(sum(s["therapy_results"]["DTT"]["success_rate"] for s in sessions) / len(sessions), 1)
        avg_ja  = round(sum(s["therapy_results"]["joint_attention"]["success_rate"] for s in sessions) / len(sessions), 1)

    schedule = [
        {"time": "09:00", "activity": "greeting_circle",     "duration": 5,  "visual": "🌅"},
        {"time": "09:05", "activity": "emotion_check_in",    "duration": 3,  "visual": "😊"},
        {"time": "09:08", "activity": "DTT_session",         "duration": 10, "visual": "📚"},
        {"time": "09:18", "activity": "sensory_break",       "duration": 5,  "visual": "🎯"},
        {"time": "09:23", "activity": "joint_attention",     "duration": 8,  "visual": "👀"},
        {"time": "09:31", "activity": "free_play",           "duration": 5,  "visual": "🎮"},
        {"time": "09:36", "activity": "emotion_recognition", "duration": 7,  "visual": "🎭"},
        {"time": "09:43", "activity": "closing_circle",      "duration": 5,  "visual": "⭐"},
    ]

    return render_template_string(
        DASHBOARD_HTML,
        config=config_data,
        sessions=sessions,
        total_sessions=len(sessions),
        avg_dtt=avg_dtt,
        avg_ja=avg_ja,
        schedule=schedule,
        saved=True
    )

@app.route("/api/sessions")
def api_sessions():
    return jsonify(load_sessions())

@app.route("/api/config")
def api_config():
    return jsonify(load_config())

if __name__ == "__main__":
    print("\n" + "="*50)
    print("🤖 ASD Therapy Dashboard")
    print("="*50)
    print("Open browser: http://localhost:5000")
    print("="*50 + "\n")
    app.run(debug=True, port=5000)

