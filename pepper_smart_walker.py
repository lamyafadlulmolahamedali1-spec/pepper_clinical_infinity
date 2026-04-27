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

class PepperSmartWalker:
    def __init__(self):
        print("🚀 تشغيل Pepper مع مشي ذكي وكلام طويل...")
        
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
        self.angle_speed = 0.15  # سرعة الدوران
        
        # سرعات
        self.walk_speed = 0.3
        self.turn_speed = 0.4
        self.hand_speed = 0.6
        
        # تحميل الصور
        self.scientists = []
        self.movies = []
        self.books = []
        self.load_all_images()
        self.all_images = self.scientists + self.movies + self.books
        self.current_index = 0
        
        # نافذة YOLO
        cv2.namedWindow("Smart Walker", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Smart Walker", 1000, 700)
        cv2.moveWindow("Smart Walker", 900, 50)
        
        self.last_update = time.time()
        self.last_hand_move = time.time()
        self.hand_state = 0
        self.text_id = None
        self.running = True
        self.speech_queue = queue.Queue()
        self.start_speech_worker()
        
        print(f"✅ {len(self.scientists)} عالم, {len(self.movies)} فيلم, {len(self.books)} كتاب")
        self.speak("I will walk in a circle and tell you everything about scientists!")

    def init_voice(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 190)  # كلام أسرع
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
        if current_time - self.last_hand_move > 0.6:  # أسرع
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
        """المشي في دائرة"""
        self.angle += self.angle_speed
        target_x = self.center_x + self.radius * math.cos(self.angle)
        target_y = self.center_y + self.radius * math.sin(self.angle)
        
        current_pos = self.pepper.getPosition()
        dx = target_x - current_pos[0]
        dy = target_y - current_pos[1]
        
        # المشي نحو الهدف
        if abs(dx) > 0.1 or abs(dy) > 0.1:
            self.pepper.move(dx * 0.5, dy * 0.5, 0)
        
        self.move_hands_naturally()

    def load_all_images(self):
        """تحميل الصور"""
        images_dir = os.path.expanduser("~/pepper_duo/data/known_faces/")
        
        # علماء مع معلومات مفصلة
        scientists_data = {
            'einstein': ('Albert Einstein', [
                "He was born in Germany in 1879!",
                "He developed the theory of relativity when he was only 26 years old!",
                "His famous equation E = mc² changed physics forever!",
                "He won the Nobel Prize in 1921 for discovering the photoelectric effect!",
                "He escaped Nazi Germany and came to America in 1933!",
                "He worked on the Manhattan Project but later regretted it!",
                "He had a famous photo with his tongue out!",
                "He said: Imagination is more important than knowledge!",
                "He died in 1955 at age 76!",
                "His brain was preserved for scientific research!"
            ]),
            'marie_curie': ('Marie Curie', [
                "She was born in Poland in 1867!",
                "She discovered two elements: radium and polonium!",
                "She is the only person to win Nobel Prizes in two different sciences!",
                "She won Physics in 1903 and Chemistry in 1911!",
                "She was the first woman professor at the University of Paris!",
                "She died from radiation exposure because she carried radium in her pockets!",
                "Her notebooks are still radioactive today and kept in lead boxes!",
                "She named polonium after her home country Poland!",
                "She founded the Curie Institutes in Paris and Warsaw!",
                "During WWI, she created mobile X-ray units to help wounded soldiers!"
            ]),
            'newton': ('Isaac Newton', [
                "He was born in England in 1643!",
                "He discovered gravity when an apple fell on his head!",
                "He formulated the three laws of motion that are still used today!",
                "He invented calculus, which is essential for modern mathematics!",
                "He built the first reflecting telescope!",
                "He was president of the Royal Society for over 20 years!",
                "He was knighted by Queen Anne in 1705!",
                "He studied alchemy and wrote more about religion than science!",
                "He never married and was known to be quite eccentric!",
                "He died in 1727 and was buried in Westminster Abbey!"
            ]),
            'tesla': ('Nikola Tesla', [
                "He was born in Serbia in 1856!",
                "He invented alternating current (AC) which powers our homes today!",
                "He worked for Thomas Edison but they had a famous rivalry!",
                "He developed the Tesla coil which creates high-voltage electricity!",
                "He had over 300 patents worldwide!",
                "He dreamed of wireless electricity and built a tower to test it!",
                "He spoke 8 languages fluently!",
                "He had a photographic memory and could visualize inventions perfectly!",
                "He was obsessed with the number 3 and would do everything in threes!",
                "He died alone and poor in a New York hotel room in 1943!"
            ]),
            'hawking': ('Stephen Hawking', [
                "He was born in England in 1942, exactly 300 years after Galileo died!",
                "He was diagnosed with ALS at age 21 and given only 2 years to live!",
                "He lived for 55 more years and became one of history's greatest scientists!",
                "He studied black holes and discovered they emit radiation, now called Hawking radiation!",
                "He wrote 'A Brief History of Time' which sold over 10 million copies!",
                "He used a speech synthesizer to communicate after losing his voice!",
                "He was married twice and had three children!",
                "He appeared in Star Trek, The Simpsons, and The Big Bang Theory!",
                "He believed that aliens probably exist and we should be careful contacting them!",
                "He said: Intelligence is the ability to adapt to change!"
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
        
        # أفلام وكتب (مختصرة)
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
        print("🌟 Pepper يمشي في دائرة ويتكلم كثيراً عن العلماء")
        print("="*70 + "\n")
        
        self.speak("I will walk in a circle and tell you everything I know about scientists!")
        
        try:
            while self.running:
                # المشي في دائرة
                self.move_in_circle()
                
                # كل 5 ثواني نغير الصورة (وقت أطول للكلام)
                if time.time() - self.last_update > 5:
                    img_data = self.all_images[self.current_index]
                    detected, detections = self.detect_with_yolo(img_data['image'].copy())
                    
                    cv2.putText(detected, f"★ {img_data['name']} ★", (20, 50),
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)
                    
                    cv2.imshow("Smart Walker", detected)
                    cv2.waitKey(1)
                    
                    # كلام طويل للعلماء
                    if img_data['type'] == 'scientist':
                        # اختيار 3 حقائق عشوائية
                        facts = random.sample(img_data['facts'], 3)
                        speech = f"Let me tell you about {img_data['name']}! " + " ".join(facts)
                        lines = [f"🔬 {img_data['name']}", facts[0][:40]]
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
                        self.speak("That was fascinating! Let's learn more!")
                    
                    self.last_update = time.time()
                
                time.sleep(0.05)
                
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            self.speak("Thanks for learning with me! Bye bye!")
        finally:
            cv2.destroyAllWindows()
            self.sim_manager.stopSimulation(self.client)

if __name__ == "__main__":
    app = PepperSmartWalker()
    app.run()
