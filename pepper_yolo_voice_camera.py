#!/usr/bin/env python3
"""
Pepper مع YOLO + كاميرا + صوت + فيديو
"""

import cv2
import numpy as np
import time
import threading
import random
import queue
import pybullet as p
import pybullet_data
from qibullet import SimulationManager
import pyttsx3
import speech_recognition as sr
from ultralytics import YOLO

class PepperYoloVoice:
    def __init__(self):
        print("🚀 تشغيل Pepper مع YOLO والكاميرا والصوت...")
        
        # YOLO
        self.yolo = YOLO('yolov8n.pt')
        
        # الصوت
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 170)
        
        # الميكروفون
        self.recognizer = sr.Recognizer()
        try:
            self.mic = sr.Microphone()
            with self.mic as source:
                print("🔄 معايرة الميكروفون...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
        except:
            self.mic = None
            print("⚠️ ميكروفون غير متوفر")
        
        # الكاميرا + تسجيل الفيديو
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            print("⚠️ الكاميرا مش شغالة - بنستخدم كاميرا افتراضية")
            self.cap = cv2.VideoCapture(0)  # افتراضي
        
        # تسجيل الفيديو
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        self.out = cv2.VideoWriter('pepper_recording.avi', fourcc, 20.0, (640, 480))
        
        # محاكي Pepper
        self.sim_manager = SimulationManager()
        self.client = self.sim_manager.launchSimulation(gui=True)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.loadURDF("plane.urdf")
        p.resetDebugVisualizerCamera(4.5, 50, -30, [0, 0, 1])
        
        # Pepper
        self.pepper = self.sim_manager.spawnPepper(
            self.client, translation=[-2, 0, 0], quaternion=[0, 0, 0, 1]
        )
        
        self.text_id = None
        self.running = True
        self.speech_queue = queue.Queue()
        
        # بدء الاستماع
        self.start_listener()
        
        print("✅ Pepper جاهز!")
        self.speak("Hello! I'm ready. You can ask me what I see.")

    def speak(self, text):
        def t():
            self.engine.say(text)
            self.engine.runAndWait()
        threading.Thread(target=t, daemon=True).start()

    def start_listener(self):
        def listen_loop():
            if not self.mic:
                return
            while self.running:
                try:
                    with self.mic as source:
                        print("\n🎤 استماع...")
                        audio = self.recognizer.listen(source, timeout=2, phrase_time_limit=5)
                    text = self.recognizer.recognize_google(audio)
                    print(f"📝 أنت: {text}")
                    self.speech_queue.put(text)
                except sr.WaitTimeoutError:
                    pass
                except:
                    pass
        threading.Thread(target=listen_loop, daemon=True).start()

    def detect_objects(self, frame):
        results = self.yolo(frame)[0]
        detections = []
        for box in results.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            label = self.yolo.names[int(box.cls[0].item())]
            conf = box.conf[0].item()
            detections.append((label, conf, (x1, y1, x2, y2)))
        return detections

    def draw_detections(self, frame, detections):
        for label, conf, (x1, y1, x2, y2) in detections:
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, f"{label} {conf:.2f}", (x1, y1-10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)
        return frame

    def wave(self):
        for i in range(2):
            self.pepper.setAngles(["RShoulderPitch"], [-0.7], 0.5)
            time.sleep(0.2)
            self.pepper.setAngles(["RShoulderPitch"], [0.3], 0.5)
            time.sleep(0.2)

    def show_text(self, text):
        pos = self.pepper.getPosition()
        if self.text_id:
            p.removeUserDebugItem(self.text_id)
        self.text_id = p.addUserDebugText(
            text, [pos[0], pos[1], pos[2] + 2.0], [0,0,0], textSize=1.2, lifeTime=3
        )

    def process_speech(self, text):
        text_lower = text.lower()
        
        if "what do you see" in text_lower or "what can you see" in text_lower:
            if hasattr(self, 'last_detections') and self.last_detections:
                items = list(set([d[0] for d in self.last_detections[:5]]))
                response = f"I see: {', '.join(items)}"
            else:
                response = "I don't see anything right now"
            print(f"🤖 Pepper: {response}")
            self.speak(response)
            self.show_text(response)
            self.wave()
            return
        
        if "hello" in text_lower or "hi" in text_lower:
            response = "Hello! Nice to see you!"
            print(f"🤖 Pepper: {response}")
            self.speak(response)
            self.show_text(response)
            self.wave()
            return
        
        if "how are you" in text_lower:
            response = "I'm great! Thanks for asking!"
            print(f"🤖 Pepper: {response}")
            self.speak(response)
            return
        
        # ردود عامة
        responses = [
            "That's interesting!", "Tell me more!", "Really?", 
            "Wow!", "I understand.", "Go on..."
        ]
        response = random.choice(responses)
        print(f"🤖 Pepper: {response}")
        self.speak(response)

    def run(self):
        print("\n" + "="*70)
        print("🌟 PEPPER مع YOLO + كاميرا + صوت")
        print("="*70 + "\n")
        print("🎤 تحدث الآن - سيرد Pepper ذكياً")
        print("📸 الكاميرا شغالة - هيكشف الأشياء")
        print("💾 الفيديو بيتسجل في pepper_recording.avi\n")
        
        self.speak("I can hear you and see you!")
        
        last_detection_time = time.time()
        
        try:
            while self.running:
                # صورة من الكاميرا
                ret, frame = self.cap.read()
                if ret:
                    # كشف YOLO
                    detections = self.detect_objects(frame)
                    self.last_detections = detections
                    frame = self.draw_detections(frame, detections)
                    
                    # عرض + تسجيل
                    cv2.imshow("Pepper YOLO Vision", frame)
                    self.out.write(frame)
                    
                    # كل 5 ثواني يقول إيه شايف
                    if detections and time.time() - last_detection_time > 5:
                        items = list(set([d[0] for d in detections[:3]]))
                        if items:
                            response = f"I see {', '.join(items)}"
                            print(f"🤖 Pepper: {response}")
                            self.speak(response)
                            self.show_text(response)
                            last_detection_time = time.time()
                
                # معالجة الصوت
                if not self.speech_queue.empty():
                    text = self.speech_queue.get()
                    self.process_speech(text)
                
                # حركة Pepper
                self.pepper.move(0.05, 0, 0.02)
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                
                time.sleep(0.05)
                
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
        finally:
            self.cap.release()
            self.out.release()
            cv2.destroyAllWindows()
            self.sim_manager.stopSimulation(self.client)

if __name__ == "__main__":
    pepper = PepperYoloVoice()
    pepper.run()
