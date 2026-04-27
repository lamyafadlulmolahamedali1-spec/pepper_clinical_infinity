import os, sys, threading, time, json, random
from datetime import datetime
import cv2
import numpy as np
import google.generativeai as genai
from flask import Flask, request, jsonify, render_template_string

# --- CONFIG ---
GEMINI_KEY = "AIzaSyDEdleVKiQ5E00wMcjMbji0G9JcYT2TvE8"
genai.configure(api_key=GEMINI_KEY)
app = Flask(__name__)

S = {"name": "Child", "emotion": "neutral", "stars": 0, "logs": []}

def log(msg):
    t = datetime.now().strftime("%H:%M:%S")
    S["logs"].append(f"[{t}] {msg}")
    if len(S["logs"]) > 10: S["logs"].pop(0)
    print(f"[{t}] {msg}")

# --- HTML UI ---
UI = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { background: #0f172a; color: white; text-align: center; font-family: sans-serif; }
        .card { background: #1e293b; border-radius: 15px; padding: 20px; margin: 10px; }
        .btn { display: block; background: #3b82f6; color: white; padding: 15px; margin: 10px; border-radius: 10px; text-decoration: none; }
    </style>
</head>
<body>
    <div class="card">
        <h1>🤖 محطة بيبر</h1>
        <h2>المشاعر: {{ s.emotion }}</h2>
        <h3>⭐ النجوم: {{ s.stars }}</h3>
    </div>
    <div class="card">
        <a href="http://{{ ip }}:5001" class="btn">الرئيسية</a>
        <a href="http://{{ ip }}:5007" class="btn">الذكاء الاصطناعي</a>
        <a href="http://{{ ip }}:5009" class="btn">الألعاب</a>
    </div>
    <script>setInterval(()=>location.reload(), 3000);</script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(UI, s=S, ip=request.host.split(':')[0])

def run_flask(port):
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    log("System Initializing...")
    # تشغيل المنافذ الثلاثة فوراً
    for p in [5001, 5007, 5009]:
        threading.Thread(target=run_flask, args=(p,), daemon=True).start()
    
    log("All Ports (5001, 5007, 5009) are LIVE!")
    try:
        while True: time.sleep(1)
    except: pass
