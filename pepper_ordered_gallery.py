import time
import pybullet as p
import pybullet_data
import threading
import random
import cv2
import numpy as np
import os
from qibullet import SimulationManager
import pyttsx3
import queue
from ultralytics import YOLO

class PepperOrderedGallery:
    def __init__(self):
        print("🚀 تشغيل Pepper مع معرض مرتب...")
        
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
        
        # سرعات
        self.walk_speed = 0.2
        self.direction = 1
        self.max_x = 2.0
        self.min_x = -2.0
        
        # تحميل الصور مرتبة
        self.scientists = []
        self.movies = []
        self.books = []
        self.load_all_images()
        
        # دمج الكل مع ترتيب: علماء → أفلام → كتب
        self.all_images = self.scientists + self.movies + self.books
        
        # نافذة YOLO
        cv2.namedWindow("Ordered Gallery", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Ordered Gallery", 1000, 700)
        cv2.moveWindow("Ordered Gallery", 900, 50)
        
        self.current_index = 0
        self.last_update = time.time()
        self.last_hand_move = time.time()
        self.hand_state = 0
        self.text_id = None
        self.running = True
        self.speech_queue = queue.Queue()
        self.start_speech_worker()
        
        print(f"✅ {len(self.scientists)} عالم, {len(self.movies)} فيلم, {len(self.books)} كتاب")
        self.speak("First I'll show you scientists, then movies, then books!")

    def init_voice(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 180)
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
        if current_time - self.last_hand_move > 0.8:
            if self.hand_state == 0:
                self.pepper.setAngles(["RShoulderPitch"], [0.5], 0.5)
                self.hand_state = 1
            elif self.hand_state == 1:
                self.pepper.setAngles(["LShoulderPitch"], [1.2], 0.5)
                self.hand_state = 2
            elif self.hand_state == 2:
                self.pepper.setAngles(["RShoulderPitch", "LShoulderPitch"], 
                                     [0.2, 1.4], 0.5)
                self.hand_state = 3
            else:
                self.reset_hands()
                self.hand_state = 0
            self.last_hand_move = current_time

    def move_horizontal(self):
        pos = self.pepper.getPosition()
        if pos[0] > self.max_x:
            self.direction = -1
        elif pos[0] < self.min_x:
            self.direction = 1
        self.pepper.move(self.walk_speed * self.direction, 0, 0)
        self.move_hands_naturally()

    def load_all_images(self):
        """تحميل الصور مرتبة"""
        images_dir = os.path.expanduser("~/pepper_duo/data/known_faces/")
        
        # 1. علماء
        scientists_data = {
            'einstein': ('Albert Einstein', 'the genius who changed physics!', [
                'He developed the theory of relativity!',
                'E = mc² is his famous equation!',
                'He won the Nobel Prize in 1921!'
            ]),
            'marie_curie': ('Marie Curie', 'the incredible scientist!', [
                'She discovered radium and polonium!',
                'She won TWO Nobel Prizes!',
                'She was the first woman professor!'
            ]),
            'newton': ('Isaac Newton', 'the father of physics!', [
                'He discovered gravity!',
                'He formulated the laws of motion!',
                'He invented calculus!'
            ]),
            'tesla': ('Nikola Tesla', 'the electrical wizard!', [
                'He invented alternating current (AC)!',
                'He developed the Tesla coil!',
                'He had over 300 patents!'
            ]),
            'hawking': ('Stephen Hawking', 'the cosmologist!', [
                'He studied black holes!',
                'He wrote "A Brief History of Time"!',
                'He had ALS!'
            ])
        }
        
        for filename in os.listdir(images_dir):
            if filename.endswith(('.jpg', '.png')):
                for key, (name, desc, facts) in scientists_data.items():
                    if key in filename.lower():
                        img = cv2.imread(os.path.join(images_dir, filename))
                        if img is not None:
                            img = cv2.resize(img, (400, 500))
                            self.scientists.append({
                                'type': 'scientist',
                                'name': name,
                                'desc': desc,
                                'facts': facts,
                                'image': img
                            })
                            print(f"✅ عالم: {name}")
                        break
        
        # 2. أفلام
        movies_data = [
            ('Interstellar', 'Christopher Nolan', 'sci-fi masterpiece!', 
             ['A team travels through a wormhole!', 
              'Matthew McConaughey is amazing!',
              'The ending will blow your mind!']),
            ('Inception', 'Christopher Nolan', 'dream within a dream!',
             ['Leo DiCaprio steals dreams!',
              'The spinning top at the end!',
              'One of the best sci-fi movies ever!']),
            ('The Matrix', 'The Wachowskis', 'what is reality?',
             ['Keanu Reeves is Neo!',
              'Bullet time scenes are iconic!',
              'Red pill or blue pill?']),
            ('Avatar', 'James Cameron', 'the highest grossing film!',
             ['Blue aliens on Pandora!',
              '3D technology revolutionized!',
              'Environmental message!']),
            ('Titanic', 'James Cameron', 'the ship of dreams!',
             ['Leo and Kate Winslet!',
              'My heart will go on!',
              'Historical tragedy!']),
            ('Pulp Fiction', 'Quentin Tarantino', 'cult classic!',
             ['John Travolta dances!',
              'Uma Thurman overdoses!',
              'Non-linear storytelling!']),
            ('Star Wars', 'George Lucas', 'the force awakens!',
             ['I am your father!',
              'Lightsabers are cool!',
              'May the force be with you!']),
            ('The Dark Knight', 'Christopher Nolan', 'the best Batman movie!',
             ['Heath Ledger as Joker!',
              'Why so serious?',
              'Christian Bale is Batman!']),
            ('Forrest Gump', 'Robert Zemeckis', 'life is like a box of chocolates!',
             ['Tom Hanks is amazing!',
              'Run Forrest run!',
              'Historical moments!']),
            ('The Godfather', 'Francis Ford Coppola', 'the mafia masterpiece!',
             ['Marlon Brando!',
              'Al Pacino!',
              'I will make him an offer!'])
        ]
        
        for title, director, tag, details in movies_data:
            img = np.ones((500, 400, 3), dtype=np.uint8) * 30
            color = (random.randint(100,255), random.randint(100,255), random.randint(100,255))
            cv2.putText(img, f"🎬 {title}", (30, 150), cv2.FONT_HERSHEY_SIMPLEX, 1.2, color, 3)
            cv2.putText(img, f"Director: {director}", (30, 250), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255,255,255), 2)
            self.movies.append({
                'type': 'movie',
                'name': title,
                'desc': tag,
                'director': director,
                'details': details,
                'image': img
            })
        
        # 3. كتب
        books_data = [
            ('1984', 'George Orwell', 'dystopian classic!',
             ['Big Brother is watching you!',
              'Thought police!',
              'Doublethink!']),
            ('To Kill a Mockingbird', 'Harper Lee', 'American masterpiece!',
             ['Atticus Finch!',
              'Racial injustice!',
              'Scout and Jem!']),
            ('The Great Gatsby', 'F. Scott Fitzgerald', 'the jazz age!',
             ['The green light!',
              'Tragic love story!',
              'American dream!']),
            ('Moby Dick', 'Herman Melville', 'the white whale!',
             ['Call me Ishmael!',
              'Captain Ahab obsessed!',
              'Epic adventure!']),
            ('War and Peace', 'Leo Tolstoy', 'Russian epic!',
             ['Over 1000 pages!',
              'Napoleon invasion!',
              'Many characters!'])
        ]
        
        for title, author, tag, details in books_data:
            img = np.ones((500, 400, 3), dtype=np.uint8) * 20
            cv2.putText(img, f"📚 {title}", (30, 150), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255,255,255), 3)
            cv2.putText(img, f"Author: {author}", (30, 250), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (200,200,200), 2)
            self.books.append({
                'type': 'book',
                'name': title,
                'desc': tag,
                'author': author,
                'details': details,
                'image': img
            })
        
        # خلط الكتب والأفلام عشوائياً
        random.shuffle(self.movies)
        random.shuffle(self.books)

    def detect_with_yolo(self, img):
        results = self.yolo(img, verbose=False)[0]
        detections = []
        img_copy = img.copy()
        
        for box in results.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = box.conf[0].item()
            label = self.yolo.names[int(box.cls[0].item())]
            detections.append(label)
            cv2.rectangle(img_copy, (x1, y1), (x2, y2), (0,255,0), 2)
            cv2.putText(img_copy, f"{label}", (x1, y1-10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)
        
        return img_copy, detections

    def show_text_above_pepper(self, lines):
        """نص فوق Pepper"""
        pos = self.pepper.getPosition()
        y_offset = 1.8
        for i, line in enumerate(lines[:2]):
            self.text_id = p.addUserDebugText(
                line,
                [pos[0], pos[1], pos[2] + y_offset - i*0.2],
                [0, 0, 0],
                textSize=1.3,
                lifeTime=3
            )

    def run(self):
        print("\n" + "="*70)
        print("🌟 Pepper مع معرض مرتب - علماء → أفلام → كتب")
        print("="*70 + "\n")
        
        self.speak("Let's start with famous scientists!")
        
        section = "scientists"
        section_index = 0
        
        try:
            while self.running:
                # حركة أفقية
                self.move_horizontal()
                
                # كل 3 ثواني نغير الصورة
                if time.time() - self.last_update > 3:
                    img_data = self.all_images[self.current_index]
                    detected, detections = self.detect_with_yolo(img_data['image'].copy())
                    
                    # إضافة اسم على الصورة
                    cv2.putText(detected, f"★ {img_data['name']} ★", (20, 50),
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)
                    
                    cv2.imshow("Ordered Gallery", detected)
                    cv2.waitKey(1)
                    
                    # تحضير النص
                    if img_data['type'] == 'scientist':
                        fact = random.choice(img_data['facts'])
                        speech = f"This is {img_data['name']}! {img_data['desc']} {fact}"
                        lines = [f"🔬 {img_data['name']}", fact[:40]]
                    elif img_data['type'] == 'movie':
                        detail = random.choice(img_data['details'])
                        speech = f"Movie: {img_data['name']} by {img_data['director']}! {detail}"
                        lines = [f"🎬 {img_data['name']}", detail[:40]]
                    else:
                        detail = random.choice(img_data['details'])
                        speech = f"Book: {img_data['name']} by {img_data['author']}! {detail}"
                        lines = [f"📚 {img_data['name']}", detail[:40]]
                    
                    print(f"🎯 {speech}")
                    self.speak(speech)
                    
                    # نص فوق Pepper
                    self.show_text_above_pepper(lines)
                    
                    self.current_index += 1
                    if self.current_index >= len(self.all_images):
                        self.current_index = 0
                        print("\n🔄 Complete tour finished! Starting over!")
                        self.speak("That was all! Let's start again with scientists!")
                    
                    self.last_update = time.time()
                
                time.sleep(0.05)
                
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            self.speak("Thanks for watching! Bye bye!")
        finally:
            cv2.destroyAllWindows()
            self.sim_manager.stopSimulation(self.client)

if __name__ == "__main__":
    app = PepperOrderedGallery()
    app.run()
