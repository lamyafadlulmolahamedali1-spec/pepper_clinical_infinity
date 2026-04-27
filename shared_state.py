import json, os, time, threading
from pathlib import Path

STATE_DIR = Path.home() / ".pepper_therapy_state"
STATE_DIR.mkdir(exist_ok=True)

EMOTION_FILE = STATE_DIR / "emotion.json"
SESSION_FILE = STATE_DIR / "session.json"

DEFAULT_EMOTION = {"emotion": "neutral", "confidence": 0.5, "scores": {}, "timestamp": 0.0}
DEFAULT_SESSION = {"active": True, "start_time": time.time(), "score": 0}

_locks = {}

def _get_lock(path):
    k = str(path)
    if k not in _locks: _locks[k] = threading.Lock()
    return _locks[k]

def write_state(path, data):
    with _get_lock(path):
        try:
            tmp = str(path) + ".tmp"
            with open(tmp, "w") as f:
                json.dump(data, f)
            os.replace(tmp, path)
        except: pass

def read_state(path, default):
    try:
        with open(path) as f:
            d = json.load(f)
            res = default.copy()
            res.update(d)
            return res
    except: return default.copy()

def set_emotion(emotion, confidence, scores=None):
    write_state(EMOTION_FILE, {
        "emotion": emotion,
        "confidence": confidence,
        "scores": scores or {},
        "timestamp": time.time(),
    })

def get_emotion(): return read_state(EMOTION_FILE, DEFAULT_EMOTION)
