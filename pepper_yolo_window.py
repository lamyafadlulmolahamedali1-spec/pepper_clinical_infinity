import time
import pybullet as p
import pybullet_data
import threading
import random
import cv2
import numpy as np
import os
import math
from qibullet import SimulationManager
import pyttsx3
import queue
from ultralytics import YOLO

class PepperYoloWindow:
    def __init__(self):
        print("🚀 تشغيل Pepper مع نافذة YOLO بحجم 4×4...")
        
        # YOLO
        self.yolo = YOLO('yolov8n.pt')
        
        # صوت
        self.init_voice()
        
        # محاكي
        self.sim_manager = SimulationManager()
        self.client = self.sim_manager.launchSimulation(gui=True)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.loadURDF("plane.urdf")
        
        p.configureDebugVisualizer(p.COV_ENABLE_GUI, 0)
        p.resetDebugVisualizerCamera(5.0, 60, -30, [0, 0, 1])
        
        # Pepper
        print("🤖 تحميل Pepper...")
        self.pepper = self.sim_manager.spawnPepper(
            self.client,
            translation=[-2, 0, 0],
            quaternion=[0, 0, 0, 1]
        )
        
        # وضع اليدين
        self.reset_hands()
        
        # منطقة المشي (دائرة)
        self.center_x = 0.0
        self.center_y = 0.0
        self.radius = 1.5
        self.angle = 0.0
        self.angle_speed = 0.15
        
        # سرعات
        self.walk_speed = 0.3
        self.hand_speed = 0.6
        
        # تحميل الصور
        self.scientists = []
        self.movies = []
        self.books = []
        self.load_all_images()
        self.all_images = self.scientists + self.movies + self.books
        self.current_index = 0
        
        # نافذة YOLO بحجم محدد (600×600 بكسل ≈ 4×4 سم)
        cv2.namedWindow("YOLO Detection", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("YOLO Detection", 600, 600)
        cv2.moveWindow("YOLO Detection", 1000, 100)
        
        self.last_update = time.time()
        self.last_hand_move = time.time()
        self.hand_state = 0
        self.text_id = None
        self.running = True
        self.speech_queue = queue.Queue()
        self.start_speech_worker()
        
        print(f"✅ {len(self.scientists)} عالم, {len(self.movies)} فيلم, {len(self.books)} كتاب")
        print("📏 نافذة YOLO بحجم 600×600 بكسل (≈ 4×4 سم)")
        self.speak("I will walk in a circle and show you YOLO detection in a small window!")

    def init_voice(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 190)
        self.engine.setProperty('volume', 1.0)
        voices = self.engine.getProperty('voices')
        for voice in voices:
            if 'english' in voice.name.lower():
                self.engine.setProperty('voice', voice.id)
                break

    def speak(self, text):
        self.speech_queue.put(text)

    def start_speech_worker(self):
        def worker():
            while self.running:
                try:
                    text = self.speech_queue.get(timeout=0.3)
                    self.engine.say(text)
                    self.engine.runAndWait()
                except queue.Empty:
                    continue
        threading.Thread(target=worker, daemon=True).start()

    def reset_hands(self):
        self.pepper.setAngles(["LShoulderPitch", "RShoulderPitch"], 
                             [1.57, 0.3], 0.3)
        self.pepper.setAngles(["LElbowRoll", "RElbowRoll"], 
                             [-1.2, 1.2], 0.3)

    def move_hands_naturally(self):
        current_time = time.time()
        if current_time - self.last_hand_move > 0.6:
            if self.hand_state == 0:
                self.pepper.setAngles(["RShoulderPitch"], [0.6], self.hand_speed)
                self.hand_state = 1
            elif self.hand_state == 1:
                self.pepper.setAngles(["LShoulderPitch"], [1.3], self.hand_speed)
                self.hand_state = 2
            elif self.hand_state == 2:
                self.pepper.setAngles(["RShoulderPitch", "LShoulderPitch"], 
                                     [0.3, 1.4], self.hand_speed)
                self.hand_state = 3
            else:
                self.reset_hands()
                self.hand_state = 0
            self.last_hand_move = current_time

    def move_in_circle(self):
        self.angle += self.angle_speed
        target_x = self.center_x + self.radius * math.cos(self.angle)
        target_y = self.center_y + self.radius * math.sin(self.angle)
        
        current_pos = self.pepper.getPosition()
        dx = target_x - current_pos[0]
        dy = target_y - current_pos[1]
        
        if abs(dx) > 0.1 or abs(dy) > 0.1:
            self.pepper.move(dx * 0.5, dy * 0.5, 0)
        
        self.move_hands_naturally()

    def load_all_images(self):
        """تحميل الصور"""
        images_dir = os.path.expanduser("~/pepper_duo/data/known_faces/")
        
        # علماء
        scientists_data = {
            'einstein': ('Albert Einstein', [
                "He developed the theory of relativity when he was only 26!",
                "His famous equation E = mc² changed physics forever!",
                "He won the Nobel Prize in 1921!",
                "He escaped Nazi Germany and came to America!",
                "He said: Imagination is more important than knowledge!"
            ]),
            'marie_curie': ('Marie Curie', [
                "She discovered radium and polonium!",
                "She won TWO Nobel Prizes!",
                "She was the first woman professor in Paris!",
                "Her notebooks are still radioactive today!",
                "She died from radiation exposure!"
            ]),
            'newton': ('Isaac Newton', [
                "He discovered gravity when an apple fell!",
                "He formulated the three laws of motion!",
                "He invented calculus!",
                "He built the first reflecting telescope!",
                "He was president of the Royal Society!"
            ]),
            'tesla': ('Nikola Tesla', [
                "He invented alternating current (AC)!",
                "He developed the Tesla coil!",
                "He had over 300 patents!",
                "He dreamed of wireless electricity!",
                "He spoke 8 languages!"
            ]),
            'hawking': ('Stephen Hawking', [
                "He studied black holes!",
                "He wrote 'A Brief History of Time'!",
                "He had ALS and used a speech synthesizer!",
                "He appeared on The Simpsons!",
                "He said: Intelligence is the ability to adapt!"
            ])
        }
        
        for filename in os.listdir(images_dir):
            if filename.endswith(('.jpg', '.png')):
                for key, (name, facts) in scientists_data.items():
                    if key in filename.lower():
                        img = cv2.imread(os.path.join(images_dir, filename))
                        if img is not None:
                            img = cv2.resize(img, (400, 500))
                            self.scientists.append({
                                'type': 'scientist',
                                'name': name,
                                'facts': facts,
                                'image': img
                            })
                            print(f"✅ عالم: {name}")
                        break
        
        # أفلام
        movies = [
            ('Interstellar', 'Christopher Nolan'),
            ('Inception', 'Christopher Nolan'),
            ('The Matrix', 'The Wachowskis'),
            ('Avatar', 'James Cameron'),
            ('Titanic', 'James Cameron')
        ]
        for title, director in movies:
            img = np.ones((500, 400, 3), dtype=np.uint8) * 30
            cv2.putText(img, f"🎬 {title}", (30, 150), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255,215,0), 3)
            cv2.putText(img, f"Director: {director}", (30, 250), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255,255,255), 2)
            self.movies.append({'type': 'movie', 'name': title, 'director': director, 'image': img})
        
        # كتب
        books = [
            ('1984', 'George Orwell'),
            ('To Kill a Mockingbird', 'Harper Lee'),
            ('The Great Gatsby', 'Fitzgerald')
        ]
        for title, author in books:
            img = np.ones((500, 400, 3), dtype=np.uint8) * 20
            cv2.putText(img, f"📚 {title}", (30, 150), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255,255,255), 3)
            cv2.putText(img, f"Author: {author}", (30, 250), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (200,200,200), 2)
            self.books.append({'type': 'book', 'name': title, 'author': author, 'image': img})
        
        random.shuffle(self.movies)
        random.shuffle(self.books)

    def detect_with_yolo(self, img):
        results = self.yolo(img, verbose=False)[0]
        detections = []
        img_copy = img.copy()
        
        for box in results.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            label = self.yolo.names[int(box.cls[0].item())]
            detections.append(label)
            cv2.rectangle(img_copy, (x1, y1), (x2, y2), (0,255,0), 2)
            cv2.putText(img_copy, f"{label}", (x1, y1-10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)
        
        return img_copy, detections

    def show_text_above_pepper(self, lines):
        pos = self.pepper.getPosition()
        for i, line in enumerate(lines[:2]):
            self.text_id = p.addUserDebugText(
                line,
                [pos[0], pos[1], pos[2] + 1.8 - i*0.2],
                [0, 0, 0],
                textSize=1.3,
                lifeTime=4
            )

    def run(self):
        print("\n" + "="*70)
        print("🌟 Pepper مع نافذة YOLO بحجم 4×4 سم")
        print("="*70 + "\n")
        
        self.speak("Look at the small YOLO window while I walk!")
        
        try:
            while self.running:
                # المشي في دائرة
                self.move_in_circle()
                
                # كل 4 ثواني نغير الصورة
                if time.time() - self.last_update > 4:
                    img_data = self.all_images[self.current_index]
                    detected, detections = self.detect_with_yolo(img_data['image'].copy())
                    
                    cv2.putText(detected, f"★ {img_data['name']} ★", (20, 50),
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)
                    
                    # عرض في النافذة الصغيرة
                    cv2.imshow("YOLO Detection", detected)
                    cv2.waitKey(1)
                    
                    # كلام
                    if img_data['type'] == 'scientist':
                        fact = random.choice(img_data['facts'])
                        speech = f"This is {img_data['name']}! {fact}"
                        lines = [f"🔬 {img_data['name']}", fact[:40]]
                    else:
                        speech = f"This is {img_data['name']}"
                        lines = [img_data['name'], ""]
                    
                    print(f"🎯 {speech}")
                    self.speak(speech)
                    self.show_text_above_pepper(lines)
                    
                    self.current_index += 1
                    if self.current_index >= len(self.all_images):
                        self.current_index = 0
                        random.shuffle(self.all_images)
                        print("\n🔄 Starting new tour!")
                        self.speak("Let's see more!")
                    
                    self.last_update = time.time()
                
                time.sleep(0.05)
                
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            self.speak("Thanks for watching! Bye bye!")
        finally:
            cv2.destroyAllWindows()
            self.sim_manager.stopSimulation(self.client)

if __name__ == "__main__":
    app = PepperYoloWindow()
    app.run()
