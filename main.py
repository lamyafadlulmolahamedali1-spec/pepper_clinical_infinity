import time
import pybullet as p
import pybullet_data
import random
import cv2
import numpy as np
import os
import tempfile
import threading
import queue
import sounddevice as sd
import soundfile as sf
import numpy as np
import io
from qibullet import SimulationManager
from deepface import DeepFace
from ultralytics import YOLO
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
import pyttsx3
import speech_recognition as sr

class EinsteinCurieAIPepper:
    def __init__(self):
        print("🚀 بدء تشغيل Pepper AI مع Pepper واحد...")
        
        self.init_voice()
        self.init_speech_recognition()
        
        self.sim_manager = SimulationManager()
        self.client = self.sim_manager.launchSimulation(gui=True)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.loadURDF("plane.urdf")
        p.configureDebugVisualizer(p.COV_ENABLE_RENDERING, 0)
        p.configureDebugVisualizer(p.COV_ENABLE_SHADOWS, 0)
        p.configureDebugVisualizer(p.COV_ENABLE_GUI, 0)
        
        print("🧠 تحميل نماذج الذكاء الاصطناعي...")
        self.load_ai_models()
        
        print("📦 تحميل YOLO للتعرف على الأشياء...")
        self.yolo = YOLO('yolov8n.pt')
        
        print("🤖 تحميل Pepper واحد...")
        self.pepper = self.sim_manager.spawnPepper(
            self.client, translation=[-2, 0, 0], quaternion=[0, 0, 0, 1]
        )
        
        self.scientists = self.load_scientists_data()
        print("🎭 إنشاء تماثيل العلماء...")
        self.setup_scientist_statues()
        
        self.cap = cv2.VideoCapture(0)
        self.running = True
        self.questions_queue = queue.Queue()
        
        self.start_listener()
        
        print("✅ النظام جاهز! Pepper واحد يسمعك ويشوفك ويتحرك.\n")

    def init_voice(self):
        try:
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', 140)
            self.engine.setProperty('volume', 1.0)
            voices = self.engine.getProperty('voices')
            for voice in voices:
                if 'english' in voice.name.lower():
                    self.engine.setProperty('voice', voice.id)
                    break
            print("✅ نظام الصوت جاهز")
        except Exception as e:
            print(f"⚠️ خطأ في الصوت: {e}")
            self.engine = None

    def init_speech_recognition(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source)
        print("✅ نظام الاستماع جاهز")

    def speak(self, text):
        if self.engine:
            def speak_thread():
                self.engine.say(text)
                self.engine.runAndWait()
            threading.Thread(target=speak_thread, daemon=True).start()

    def listen_voice(self):
        try:
            with self.microphone as source:
                print("🎤 استماع...")
                audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=5)
            text = self.recognizer.recognize_google(audio)
            print(f"📝 سمعت: {text}")
            return text.lower()
        except sr.WaitTimeoutError:
            return None
        except sr.UnknownValueError:
            return None
        except Exception as e:
            print(f"⚠️ خطأ في الاستماع: {e}")
            return None

    def load_ai_models(self):
        try:
            self.tokenizer = AutoTokenizer.from_pretrained('microsoft/DialoGPT-small')
            self.model = AutoModelForCausalLM.from_pretrained('microsoft/DialoGPT-small')
            self.tokenizer.pad_token = self.tokenizer.eos_token
            print("✅ نماذج AI تم تحميلها")
        except Exception as e:
            print(f"⚠️ خطأ في تحميل النماذج: {e}")
            self.tokenizer = None
            self.model = None

    def load_scientists_data(self):
        return [
            {"name": "Albert Einstein", "field": "الفيزياء", "birth": "1879", "death": "1955",
             "pos": [3, -1.5, 0.1], "color": [0.9, 0.8, 0.7, 1], "image": "einstein.jpg",
             "facts": ["طور النظرية النسبية", "حصل على نوبل في الفيزياء", "قال: الخيال أهم من المعرفة"]},
            {"name": "Marie Curie", "field": "الكيمياء", "birth": "1867", "death": "1934",
             "pos": [3, 0, 0.1], "color": [0.8, 0.7, 0.9, 1], "image": "marie_curie.jpg",
             "facts": ["اكتشفت الراديوم", "أول من حصل على نوبل مرتين", "ماتت بسبب التعرض للإشعاع"]},
            {"name": "Isaac Newton", "field": "الفيزياء", "birth": "1643", "death": "1727",
             "pos": [3, 1.5, 0.1], "color": [0.7, 0.9, 0.8, 1], "image": "newton.jpg",
             "facts": ["قوانين الحركة الثلاثة", "قانون الجاذبية", "قال: ماذا لو كانت التفاحة هي التي تسقط؟"]},
        ]

    def setup_scientist_statues(self):
        for s in self.scientists:
            col_id = p.createCollisionShape(p.GEOM_BOX, halfExtents=[0.3, 0.3, 1.0])
            vis_id = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.3, 0.3, 1.0], rgbaColor=s["color"])
            p.createMultiBody(baseMass=1, baseCollisionShapeIndex=col_id,
                              baseVisualShapeIndex=vis_id, basePosition=s["pos"])
            head_pos = [s["pos"][0], s["pos"][1], s["pos"][2] + 1.0]
            head_vis = p.createVisualShape(p.GEOM_SPHERE, radius=0.2, rgbaColor=[1, 0.9, 0.8, 1])
            p.createMultiBody(baseMass=0, baseVisualShapeIndex=head_vis, basePosition=head_pos)
            text_pos = [s["pos"][0], s["pos"][1], s["pos"][2] + 1.5]
            p.addUserDebugText(s["name"], text_pos, [0, 0, 0], textSize=1.8, lifeTime=0)

    def move_hands(self, emotion="wave"):
        if emotion == "wave":
            self.pepper.setAngles(["RShoulderPitch", "RShoulderRoll", "RElbowRoll"],
                                  [-0.8, -0.3, 1.2], 0.2)
            self.pepper.setAngles(["LShoulderPitch"], [1.57], 0.1)
            time.sleep(0.4)
            self.pepper.setAngles(["RShoulderPitch"], [-0.3], 0.2)
            self.pepper.setAngles(["RShoulderRoll"], [0.2], 0.2)
            time.sleep(0.4)
        elif emotion == "both":
            self.pepper.setAngles(["RShoulderPitch", "LShoulderPitch"],
                                  [-0.5, -0.5], 0.2)
            self.pepper.setAngles(["RElbowRoll", "LElbowRoll"],
                                  [1.2, -1.2], 0.2)
            time.sleep(0.5)
            self.pepper.setAngles(["RShoulderPitch", "LShoulderPitch"],
                                  [0.5, 0.5], 0.2)

    def detect_objects_yolo(self, frame):
        results = self.yolo(frame)[0]
        detections = []
        for box in results.boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            conf = box.conf[0].item()
            cls = int(box.cls[0].item())
            label = self.yolo.names[cls]
            detections.append((label, conf, (int(x1), int(y1), int(x2), int(y2))))
        return detections

    def draw_detections(self, frame, detections):
        for label, conf, (x1, y1, x2, y2) in detections:
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, f"{label} {conf:.2f}", (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        return frame

    def generate_response(self, text):
        if not self.model or not self.tokenizer:
            return "That's interesting! Tell me more."
        try:
            inputs = self.tokenizer.encode(text + self.tokenizer.eos_token,
                                           return_tensors='pt', truncation=True, max_length=100)
            with torch.no_grad():
                outputs = self.model.generate(
                    inputs,
                    max_length=150,
                    pad_token_id=self.tokenizer.eos_token_id,
                    temperature=0.7,
                    do_sample=True
                )
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            return response
        except:
            return "I'm thinking..."

    def start_listener(self):
        def listen():
            while self.running:
                try:
                    text = self.listen_voice()
                    if text:
                        self.questions_queue.put(text)
                except:
                    pass
        threading.Thread(target=listen, daemon=True).start()

    def run(self):
        print("\n" + "="*60)
        print("🌟 Pepper AI - واحد فقط، يسمع ويشوف ويتحرك!")
        print("="*60 + "\n")
        self.speak("Hello! I am your single Pepper. I can hear you, see you, and move. Ask me anything!")
        
        current_target = 0
        try:
            while self.running:
                if self.cap.isOpened():
                    ret, frame = self.cap.read()
                    if ret:
                        detections = self.detect_objects_yolo(frame)
                        frame = self.draw_detections(frame, detections)
                        cv2.imshow("Pepper AI - YOLO Object Detection", frame)
                        if cv2.waitKey(1) & 0xFF == ord('q'):
                            break

                if current_target < len(self.scientists):
                    target = self.scientists[current_target]
                    pos = self.pepper.getPosition()
                    dx = target["pos"][0] - pos[0]
                    dy = target["pos"][1] - pos[1]

                    if abs(dx) > 0.5 or abs(dy) > 0.5:
                        self.pepper.move(0.1 * dx, 0, 0.05 * dy)
                    else:
                        print(f"\n🎯 Pepper وصل إلى {target['name']}")
                        self.move_hands("both")
                        fact = random.choice(target["facts"])
                        print(f"💬 Pepper: {target['name']} - {fact}")
                        self.speak(f"{target['name']} - {fact}")
                        current_target += 1
                        time.sleep(3)

                if not self.questions_queue.empty():
                    question = self.questions_queue.get()
                    print(f"\n📝 سؤالك الصوتي: {question}")

                    if "what do you see" in question or "what can you see" in question or "شايف" in question:
                        ret, frame = self.cap.read()
                        if ret:
                            detections = self.detect_objects_yolo(frame)
                            if detections:
                                items = list(set([d[0] for d in detections]))
                                response = f"I see: {', '.join(items)}"
                            else:
                                response = "I don't see anything special right now."
                            print(f"🤖 Pepper: {response}")
                            self.move_hands("wave")
                            self.speak(response)
                    else:
                        response = self.generate_response(question)
                        print(f"🤖 Pepper: {response}")
                        self.move_hands("wave")
                        self.speak(response)

                    time.sleep(2)

                time.sleep(0.5)

        except KeyboardInterrupt:
            print("\n\n👋 إيقاف المحاكاة...")
        finally:
            if self.cap:
                self.cap.release()
            cv2.destroyAllWindows()
            self.sim_manager.stopSimulation(self.client)

if __name__ == "__main__":
    sim = EinsteinCurieAIPepper()
    sim.run()
