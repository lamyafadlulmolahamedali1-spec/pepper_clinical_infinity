"""
EmotionEngine v3 — works with mediapipe 0.10+ (Tasks API)
No tensorflow, no deepface, no downloads needed.

Architecture:
  Layer 1 — OpenCV multi-cascade (face + smile + eyes → structural cues)
  Layer 2 — Geometric AU ratios from OpenCV face ROI (brow, mouth, eye shape)
  Layer 3 — Temporal Kalman-style smoothing per emotion class
  
9 emotions: happy, sad, angry, fear, surprise, disgust, contempt, confused, neutral
"""

import cv2
import numpy as np
from collections import deque
import time

EMO_COLORS = {
    "happy":    (0,  220,  80),
    "sad":      (100,100, 220),
    "angry":    (0,    0, 220),
    "fear":     (0,  180, 220),
    "surprise": (200, 50, 220),
    "disgust":  (0,  180, 100),
    "neutral":  (180,180, 180),
    "contempt": (150, 80, 200),
    "confused": (200,150,   0),
}

EMOTIONS = list(EMO_COLORS.keys())

class KalmanEmotion:
    """Per-emotion 1D Kalman filter to smooth confidence scores."""
    def __init__(self, process_noise=0.02, measure_noise=0.15):
        self.x  = 0.0   # estimate
        self.p  = 1.0   # error covariance
        self.q  = process_noise
        self.r  = measure_noise

    def update(self, z):
        # predict
        p_pred = self.p + self.q
        # update
        k      = p_pred / (p_pred + self.r)
        self.x = self.x + k * (z - self.x)
        self.p = (1 - k) * p_pred
        return self.x


class EmotionEngine:
    """
    High-accuracy emotion detection using only packages available in pepper_stable.
    No downloads, no tensorflow, no deepface.
    """

    def __init__(self, size=300):
        self.size = size

        # Cascades
        self.face_cascade  = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.smile_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_smile.xml')
        self.eye_cascade   = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_eye.xml')
        self.eye_l_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_lefteye_2splits.xml')
        self.eye_r_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_righteye_2splits.xml')

        # Kalman smoothers per emotion
        self.kalman = {e: KalmanEmotion() for e in EMOTIONS}

        # History for momentum
        self.history = deque(maxlen=8)

        # State
        self.last_emotion    = "neutral"
        self.last_confidence = 0.5
        self.last_scores     = {e: 0.0 for e in EMOTIONS}
        self.frames_no_face  = 0
        self._last_face_box  = None

        print(f"✅ EmotionEngine v3 ready (cascade+geometry+Kalman, {size}x{size})")
        print(f"   Emotions: {EMOTIONS}")

    # ── Core geometry analyser ───────────────────────────────────────────
    def _analyse_roi(self, gray_face, color_face, fw, fh):
        """
        Extract AU-style features from face ROI.
        Returns raw score dict.
        """
        scores = {e: 0.0 for e in EMOTIONS}

        # ── Smile detection (AU12/13) ─────────────────────────────────
        mouth_roi  = gray_face[int(fh*0.55):fh, :]
        smiles     = self.smile_cascade.detectMultiScale(
            mouth_roi, scaleFactor=1.7, minNeighbors=22,
            minSize=(int(fw*0.25), int(fh*0.08)))
        smile_strength = 0.0
        if len(smiles):
            # more neighbors = stronger smile
            smile_strength = min(1.0, len(smiles) * 0.35 + 0.3)

        # ── Eye detection & openness ──────────────────────────────────
        brow_roi   = gray_face[0:int(fh*0.45), :]
        eyes       = self.eye_cascade.detectMultiScale(
            brow_roi, scaleFactor=1.1, minNeighbors=5,
            minSize=(int(fw*0.15), int(fh*0.08)))
        n_eyes     = len(eyes)
        eye_open   = min(1.0, n_eyes * 0.5)

        # Eye area relative size (wider open = more pixels)
        eye_area_ratio = 0.0
        if n_eyes > 0:
            total_eye_area = sum(w*h for (x,y,w,h) in eyes)
            eye_area_ratio = min(1.0, total_eye_area / (fw * fh * 0.15))

        # ── Asymmetric eye check (contempt/confused) ──────────────────
        eye_asymmetry = 0.0
        if n_eyes == 2:
            areas = [(w*h) for (x,y,w,h) in eyes]
            ratio = min(areas) / (max(areas) + 1e-6)
            eye_asymmetry = 1.0 - ratio   # 0=symmetric, 1=very asymmetric

        # ── Brightness gradient (brow furrow → angry/fear) ────────────
        brow_strip = gray_face[int(fh*0.05):int(fh*0.30), int(fw*0.20):int(fw*0.80)]
        if brow_strip.size > 0:
            # Vertical Sobel → detects furrowed brows
            sobel_y    = cv2.Sobel(brow_strip, cv2.CV_64F, 0, 1, ksize=3)
            brow_furrow = min(1.0, np.mean(np.abs(sobel_y)) / 12.0)
        else:
            brow_furrow = 0.0

        # ── Mouth height/width ratio from lower face luminance ─────────
        lower_face = gray_face[int(fh*0.55):fh, int(fw*0.20):int(fw*0.80)]
        mouth_open = 0.0
        if lower_face.size > 0:
            _, thresh  = cv2.threshold(lower_face, 60, 255, cv2.THRESH_BINARY_INV)
            dark_ratio = np.sum(thresh > 0) / thresh.size
            mouth_open = min(1.0, dark_ratio * 3.5)

        # ── Overall face brightness (pallor → fear) ────────────────────
        face_bright  = np.mean(gray_face) / 255.0

        # ── Score mapping ─────────────────────────────────────────────
        scores["happy"]    = min(1.0, smile_strength * 0.75 + eye_open * 0.20 + smile_strength * eye_open * 0.30)
        scores["surprise"] = min(1.0, mouth_open * 0.60 + eye_area_ratio * 0.40 + (1-smile_strength) * 0.20)
        scores["fear"]     = min(1.0, eye_area_ratio * 0.40 + brow_furrow * 0.30 + (1-face_bright) * 0.15 + mouth_open * 0.20)
        scores["angry"]    = min(1.0, brow_furrow * 0.60 + (1-smile_strength) * 0.25 + (1-eye_open) * 0.20)
        scores["sad"]      = min(1.0, (1-smile_strength) * 0.40 + (1-eye_open) * 0.30 + (1-face_bright) * 0.20)
        scores["disgust"]  = min(1.0, brow_furrow * 0.40 + (1-smile_strength) * 0.30 + mouth_open * 0.20)
        scores["contempt"] = min(1.0, eye_asymmetry * 0.55 + (1-smile_strength) * 0.25)
        scores["confused"] = min(1.0, eye_asymmetry * 0.45 + brow_furrow * 0.30 + (1-smile_strength) * 0.20)
        scores["neutral"]  = max(0.0, 0.55
                                     - scores["happy"]    * 0.6
                                     - scores["angry"]    * 0.5
                                     - scores["sad"]      * 0.4
                                     - scores["surprise"] * 0.5)
        return scores

    # ── Main analysis ───────────────────────────────────────────────────
    def analyse(self, frame):
        """
        Input:  BGR frame (any size)
        Output: (emotion_str, confidence_0_to_1, annotated_300x300_frame)
        """
        small  = cv2.resize(frame, (self.size, self.size))
        gray   = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        gray   = cv2.equalizeHist(gray)   # normalise illumination
        output = small.copy()

        faces  = self.face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5,
            minSize=(60, 60), flags=cv2.CASCADE_SCALE_IMAGE)

        if len(faces) == 0:
            self.frames_no_face += 1
            # Decay all scores slowly toward neutral
            for e in EMOTIONS:
                target = 0.6 if e == "neutral" else 0.05
                self.last_scores[e] = self.kalman[e].update(target)

            cv2.putText(output, "searching...",
                        (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                        (120,120,120), 1, cv2.LINE_AA)
            self._draw_bars(output, self.last_scores)
            return self.last_emotion, self.last_confidence, output

        self.frames_no_face = 0

        # Use largest face
        fx, fy, fw, fh = max(faces, key=lambda r: r[2]*r[3])
        self._last_face_box = (fx, fy, fw, fh)

        face_gray  = gray[fy:fy+fh, fx:fx+fw]
        face_color = small[fy:fy+fh, fx:fx+fw]

        raw_scores = self._analyse_roi(face_gray, face_color, fw, fh)

        # Kalman smooth every score
        smoothed = {}
        for e in EMOTIONS:
            smoothed[e] = self.kalman[e].update(raw_scores[e])

        # Momentum: blend with history
        self.history.append(smoothed.copy())
        if len(self.history) >= 3:
            for e in EMOTIONS:
                smoothed[e] = np.mean([h[e] for h in self.history])

        # Normalise so they sum to 1
        total = sum(smoothed.values()) + 1e-6
        for e in EMOTIONS:
            smoothed[e] = smoothed[e] / total

        best       = max(smoothed, key=smoothed.get)
        confidence = min(1.0, smoothed[best] * 2.2)  # rescale for display

        self.last_emotion    = best
        self.last_confidence = confidence
        self.last_scores     = smoothed

        # ── Draw face box ──────────────────────────────────────────
        color = EMO_COLORS.get(best, (180,180,180))
        cv2.rectangle(output, (fx,fy), (fx+fw,fy+fh), color, 2)
        cv2.putText(output, f"{best}  {confidence:.0%}",
                    (fx, fy-8), cv2.FONT_HERSHEY_SIMPLEX, 0.60,
                    color, 2, cv2.LINE_AA)

        # Eye boxes
        eye_roi  = face_gray[0:int(fh*0.45), :]
        eyes     = self.eye_cascade.detectMultiScale(eye_roi, 1.1, 5,
                       minSize=(int(fw*0.15), int(fh*0.08)))
        for (ex,ey,ew,eh) in eyes:
            cv2.rectangle(output, (fx+ex, fy+ey), (fx+ex+ew, fy+ey+eh),
                          (200,200,0), 1)

        # Smile box
        mouth_y0 = fy + int(fh*0.55)
        mouth_roi = face_gray[int(fh*0.55):fh, :]
        smiles    = self.smile_cascade.detectMultiScale(mouth_roi, 1.7, 22,
                        minSize=(int(fw*0.25), int(fh*0.08)))
        for (sx,sy,sw,sh) in smiles:
            cv2.rectangle(output, (fx+sx, mouth_y0+sy),
                          (fx+sx+sw, mouth_y0+sy+sh), (0,220,80), 1)

        # ── Bars ──────────────────────────────────────────────────
        self._draw_bars(output, smoothed)
        return best, confidence, output

    def _draw_bars(self, img, scores):
        """Draw emotion bar chart bottom of window."""
        top4 = sorted(scores.items(), key=lambda x: -x[1])[:5]
        bar_x = 6
        for i, (emo, sc) in enumerate(top4):
            bar_w = int(sc * (self.size - 12) * 0.85)
            bar_w = max(bar_w, 2)
            y     = self.size - 105 + i * 20
            color = EMO_COLORS.get(emo, (150,150,150))
            cv2.rectangle(img, (bar_x, y), (bar_x + bar_w, y+15), color, -1)
            cv2.putText(img, f"{emo[:7]} {sc:.0%}",
                        (bar_x+3, y+11),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.36,
                        (255,255,255), 1, cv2.LINE_AA)


# ── Standalone test ──────────────────────────────────────────────────────
if __name__ == "__main__":
    engine = EmotionEngine(size=300)
    print("\nOpening camera for live test (press Q to quit)...")

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)

    if not cap.isOpened():
        cap = cv2.VideoCapture(1)

    cv2.namedWindow("Emotion Test", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Emotion Test", 300, 300)
    cv2.moveWindow("Emotion Test", 100, 100)

    fps_t = time.time()
    frames = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Camera read failed")
            break

        emotion, conf, vis = engine.analyse(frame)
        frames += 1
        elapsed = time.time() - fps_t
        if elapsed > 0:
            fps = frames / elapsed
            cv2.putText(vis, f"FPS:{fps:.0f}", (vis.shape[1]-60, 18),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200,200,200), 1)

        cv2.imshow("Emotion Test", vis)
        print(f"\r[{emotion:10s}] {conf:.0%}  ", end="", flush=True)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("\nDone.")
