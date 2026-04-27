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

class PepperHorizontalMuseum:
    def __init__(self):
        print("🚀 تشغيل Pepper مع حركة أفقية وبوسترات واضحة...")
        
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
        
        # وضع اليدين الطبيعي
        self.reset_hands()
        
        # سرعات
        self.walk_speed = 0.2
        self.turn_speed = 0.3
        self.hand_speed = 0.5
        self.direction = 1  # 1 = يمين, -1 = يسار
        self.max_x = 2.0
        self.min_x = -2.0
        
        # تحميل كل الصور
        self.all_images = self.load_all_images()
        
        # نافذة YOLO
        cv2.namedWindow("Horizontal Museum", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Horizontal Museum", 1000, 700)
        cv2.moveWindow("Horizontal Museum", 900, 50)
        
        self.current_index = 0
        self.last_update = time.time()
        self.last_hand_move = time.time()
        self.hand_state = 0
        self.text_id = None
        self.running = True
        self.speech_queue = queue.Queue()
        self.start_speech_worker()
        
        print(f"✅ {len(self.all_images)} صورة جاهزة")
        self.speak("Welcome! I'll walk side to side and show you amazing posters!")

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
        """وضع اليدين الطبيعي"""
        self.pepper.setAngles(["LShoulderPitch", "RShoulderPitch"], 
                             [1.57, 0.3], 0.3)
        self.pepper.setAngles(["LElbowRoll", "RElbowRoll"], 
                             [-1.2, 1.2], 0.3)

    def move_hands_naturally(self):
        """حركة يدين طبيعية"""
        current_time = time.time()
        if current_time - self.last_hand_move > 0.8:
            if self.hand_state == 0:
                self.pepper.setAngles(["RShoulderPitch"], [0.5], self.hand_speed)
                self.hand_state = 1
            elif self.hand_state == 1:
                self.pepper.setAngles(["LShoulderPitch"], [1.2], self.hand_speed)
                self.hand_state = 2
            elif self.hand_state == 2:
                self.pepper.setAngles(["RShoulderPitch", "LShoulderPitch"], 
                                     [0.2, 1.4], self.hand_speed)
                self.hand_state = 3
            else:
                self.reset_hands()
                self.hand_state = 0
            self.last_hand_move = current_time

    def move_horizontal(self):
        """حركة أفقية (يمين - يسار)"""
        pos = self.pepper.getPosition()
        
        # تغيير الاتجاه عند الوصول للحدود
        if pos[0] > self.max_x:
            self.direction = -1
        elif pos[0] < self.min_x:
            self.direction = 1
        
        # حركة أفقية
        self.pepper.move(self.walk_speed * self.direction, 0, 0)
        self.move_hands_naturally()

    def load_all_images(self):
        """تحميل كل الصور"""
        images = []
        images_dir = os.path.expanduser("~/pepper_duo/data/known_faces/")
        
        # علماء حقيقيين
        scientists = {
            'einstein': ('Albert Einstein', 'the genius who changed physics forever!', [
                'He developed the theory of relativity!',
                'E = mc² is his famous equation!',
                'He won the Nobel Prize in 1921!'
            ]),
            'marie_curie': ('Marie Curie', 'the incredible scientist who discovered radioactivity!', [
                'She discovered radium and polonium!',
                'She won TWO Nobel Prizes!',
                'She was the first woman professor in Paris!'
            ]),
            'newton': ('Isaac Newton', 'the father of classical physics!', [
                'He discovered gravity!',
                'He formulated the laws of motion!',
                'He invented calculus!'
            ]),
            'tesla': ('Nikola Tesla', 'the electrical wizard!', [
                'He invented alternating current (AC)!',
                'He developed the Tesla coil!',
                'He had over 300 patents!'
            ]),
            'hawking': ('Stephen Hawking', 'the brilliant cosmologist!', [
                'He studied black holes!',
                'He wrote "A Brief History of Time"!',
                'He had ALS!'
            ])
        }
        
        # صور حقيقية
        for filename in os.listdir(images_dir):
            if filename.endswith(('.jpg', '.png')):
                for key, (name, desc, facts) in scientists.items():
                    if key in filename.lower():
                        img = cv2.imread(os.path.join(images_dir, filename))
                        if img is not None:
                            img = cv2.resize(img, (400, 500))
                            images.append({
                                'type': 'scientist',
                                'name': name,
                                'desc': desc,
                                'facts': facts,
                                'image': img
                            })
                            print(f"✅ عالم: {name}")
                        break
        
        # بوسترات أفلام ملونة
        movies = [
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
        
        for title, director, tag, details in movies:
            # إنشاء بوستر ملون
            img = np.ones((500, 400, 3), dtype=np.uint8) * random.randint(20, 50)
            # ألوان زاهية
            color1 = (random.randint(100,255), random.randint(100,255), random.randint(100,255))
            color2 = (random.randint(100,255), random.randint(100,255), random.randint(100,255))
            
            cv2.putText(img, f"🎬 {title}", (30, 150), cv2.FONT_HERSHEY_SIMPLEX, 1.2, color1, 3)
            cv2.putText(img, f"Director: {director}", (30, 250), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color2, 2)
            cv2.putText(img, tag, (30, 350), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2)
            
            images.append({
                'type': 'movie',
                'name': title,
                'desc': tag,
                'director': director,
                'details': details,
                'image': img
            })
        
        # كتب
        books = [
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
        
        for title, author, tag, details in books:
            img = np.ones((500, 400, 3), dtype=np.uint8) * random.randint(10, 30)
            color = (random.randint(150,255), random.randint(150,255), random.randint(150,255))
            cv2.putText(img, f"📚 {title}", (30, 150), cv2.FONT_HERSHEY_SIMPLEX, 1.2, color, 3)
            cv2.putText(img, f"Author: {author}", (30, 250), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (200,200,200), 2)
            
            images.append({
                'type': 'book',
                'name': title,
                'desc': tag,
                'author': author,
                'details': details,
                'image': img
            })
        
        random.shuffle(images)
        return images

    def detect_with_yolo(self, img):
        """YOLO detection"""
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

    def show_text_below_pepper(self, lines):
        """نص تحت Pepper"""
        pos = self.pepper.getPosition()
        for i, line in enumerate(lines[:2]):
            self.text_id = p.addUserDebugText(
                line,
                [pos[0], pos[1], pos[2] - 0.3 - i*0.2],
                [0, 0, 0],
                textSize=1.2,
                lifeTime=3
            )

    def run(self):
        print("\n" + "="*70)
        print("🌟 Pepper مع حركة أفقية وبوسترات واضحة")
        print("="*70 + "\n")
        
        self.speak("Look at me walking side to side while showing amazing posters!")
        
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
                    
                    cv2.imshow("Horizontal Museum", detected)
                    cv2.waitKey(1)
                    
                    # تحضير النص
                    if img_data['type'] == 'scientist':
                        fact = random.choice(img_data['facts'])
                        speech = f"This is {img_data['name']}! {img_data['desc']} {fact}"
                        lines = [img_data['name'], fact[:40]]
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
                    
                    # نص تحت Pepper
                    self.show_text_below_pepper(lines)
                    
                    self.current_index += 1
                    if self.current_index >= len(self.all_images):
                        self.current_index = 0
                        random.shuffle(self.all_images)
                        print("\n🔄 New round!")
                        self.speak("Let's see more amazing things!")
                    
                    self.last_update = time.time()
                
                time.sleep(0.05)
                
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            self.speak("Thanks for watching! Bye bye!")
        finally:
            cv2.destroyAllWindows()
            self.sim_manager.stopSimulation(self.client)

if __name__ == "__main__":
    app = PepperHorizontalMuseum()
    app.run()
