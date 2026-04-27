#!/usr/bin/env python3
"""
Camera + AI Chat
- Camera with YOLO + Emotion
- AI Chat in terminal
"""

import cv2
import time
import threading
import requests
from ultralytics import YOLO
from deepface import DeepFace

# ========== AI Chat ==========
CHAT_API = "https://text.pollinations.ai/v1/chat/completions"

def get_ai_response(message):
    data = {"model": "openai", "messages": [{"role": "system", "content": "You are Pepper, a friendly robot. Respond in short, simple English."}, {"role": "user", "content": message}]}
    try:
        r = requests.post(CHAT_API, json=data, timeout=10)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
    except:
        pass
    return "That's interesting! Tell me more! 😊"

# ========== Camera Detection ==========
class CameraDetection:
    def __init__(self):
        print("📷 Loading YOLO...")
        self.model = YOLO('yolov8n.pt')
        self.cap = cv2.VideoCapture(1)
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(0)
        self.emotion = "neutral"
        self.running = True
        cv2.namedWindow("Camera", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Camera", 640, 480)
        threading.Thread(target=self.run, daemon=True).start()
    
    def detect_emotion(self, face):
        try:
            result = DeepFace.analyze(face, actions=['emotion'], enforce_detection=False)
            return result[0]['dominant_emotion']
        except:
            return "neutral"
    
    def run(self):
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                continue
            frame = cv2.resize(frame, (640, 480))
            results = self.model(frame, verbose=False)
            for r in results:
                if r.boxes:
                    for box in r.boxes:
                        if self.model.names[int(box.cls[0])] == 'person':
                            x1, y1, x2, y2 = map(int, box.xyxy[0])
                            face = frame[y1:y2, x1:x2]
                            if face.size > 0:
                                self.emotion = self.detect_emotion(face)
                            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 3)
                            cv2.putText(frame, f"Lamia: {self.emotion.upper()}", (x1, y1-10),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            cv2.putText(frame, f"Emotion: {self.emotion.upper()}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.imshow("Camera", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                self.running = False
                break
        self.cap.release()
        cv2.destroyAllWindows()
    
    def get_emotion(self):
        return self.emotion
    
    def stop(self):
        self.running = False

# ========== Main ==========
def main():
    print("\n" + "="*50)
    print("📷 CAMERA + AI CHAT")
    print("="*50)
    print("✅ Camera with YOLO + Emotion")
    print("✅ AI Chat in terminal")
    print("💬 Type your message, press Enter")
    print("👋 Type 'exit' to quit")
    print("="*50 + "\n")
    
    camera = CameraDetection()
    time.sleep(1)
    
    print("🤖 Pepper: Hello! I see you! Your current emotion is", camera.get_emotion().upper())
    
    while True:
        try:
            user = input("\n👶 You: ").strip()
            if user.lower() in ['exit', 'quit', 'bye']:
                print("🤖 Pepper: Goodbye!")
                break
            if not user:
                continue
            
            # Add emotion context
            emotion = camera.get_emotion()
            if emotion != "neutral":
                print(f"📷 (Detected emotion: {emotion.upper()})")
            
            response = get_ai_response(user)
            print(f"🤖 Pepper: {response}")
            
        except KeyboardInterrupt:
            print("\n🤖 Pepper: Goodbye!")
            break
    
    camera.stop()

if __name__ == "__main__":
    main()
