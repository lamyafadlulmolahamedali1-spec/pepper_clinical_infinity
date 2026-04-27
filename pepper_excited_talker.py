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

class PepperExcitedTalker:
    def __init__(self):
        print("🚀 تشغيل Pepper المتحمس المتكلم...")
        
        # YOLO
        self.yolo = YOLO('yolov8n.pt')
        
        # صوت متحمس
        self.init_voice()
        
        # محاكي
        self.sim_manager = SimulationManager()
        self.client = self.sim_manager.launchSimulation(gui=True)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.loadURDF("plane.urdf")
        
        p.configureDebugVisualizer(p.COV_ENABLE_GUI, 0)
        p.resetDebugVisualizerCamera(5.0, 60, -30, [0, 0, 1])
        
        # Pepper
        print("🤖 تحميل Pepper المتحمس...")
        self.pepper = self.sim_manager.spawnPepper(
            self.client,
            translation=[-3, 0, 0],
            quaternion=[0, 0, 0, 1]
        )
        
        # وضع اليدين الطبيعي (منخفض)
        self.reset_hands()
        
        # سرعات
        self.walk_speed = 0.3
        self.turn_speed = 0.4
        self.hand_speed = 0.5
        
        # تحميل كل الصور
        self.all_images = self.load_all_images()
        
        # نافذة YOLO
        cv2.namedWindow("Excited Pepper Detection", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Excited Pepper Detection", 1000, 700)
        cv2.moveWindow("Excited Pepper Detection", 900, 50)
        
        self.current_index = 0
        self.last_update = time.time()
        self.last_hand_move = time.time()
        self.hand_state = 0
        self.text_id = None
        self.running = True
        self.speech_queue = queue.Queue()
        self.start_speech_worker()
        
        print(f"✅ {len(self.all_images)} صورة جاهزة")
        self.speak("OH WOW! I'm so excited to show you all these amazing things!")

    def init_voice(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 190)  # سريع متحمس
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
        """وضع اليدين الطبيعي (منخفض)"""
        self.pepper.setAngles(["LShoulderPitch", "RShoulderPitch"], 
                             [1.57, 0.3], 0.3)
        self.pepper.setAngles(["LElbowRoll", "RElbowRoll"], 
                             [-1.2, 1.2], 0.3)

    def move_hands_naturally(self):
        """حركة يدين طبيعية أثناء الكلام"""
        current_time = time.time()
        if current_time - self.last_hand_move > 0.8:  # كل 0.8 ثانية حركة
            if self.hand_state == 0:
                # اليد اليمنى تتحرك قليلاً
                self.pepper.setAngles(["RShoulderPitch"], [0.5], self.hand_speed)
                self.hand_state = 1
            elif self.hand_state == 1:
                # اليد اليسرى تتحرك
                self.pepper.setAngles(["LShoulderPitch"], [1.2], self.hand_speed)
                self.hand_state = 2
            elif self.hand_state == 2:
                # كلتا اليدين
                self.pepper.setAngles(["RShoulderPitch", "LShoulderPitch"], 
                                     [0.2, 1.4], self.hand_speed)
                self.hand_state = 3
            else:
                # العودة للوضع الطبيعي
                self.reset_hands()
                self.hand_state = 0
            
            self.last_hand_move = current_time

    def load_all_images(self):
        """تحميل كل الصور"""
        images = []
        images_dir = os.path.expanduser("~/pepper_duo/data/known_faces/")
        
        # علماء حقيقيين
        scientists = {
            'einstein': {
                'name': 'Albert Einstein',
                'desc': 'the genius who changed physics forever!',
                'details': [
                    'He developed the theory of relativity!',
                    'E = mc² is his famous equation!',
                    'He won the Nobel Prize in 1921!',
                    'He said: Imagination is more important than knowledge!',
                    'He escaped Nazi Germany and came to America!'
                ]
            },
            'marie_curie': {
                'name': 'Marie Curie',
                'desc': 'the incredible scientist who discovered radioactivity!',
                'details': [
                    'She discovered radium and polonium!',
                    'She won TWO Nobel Prizes! Can you believe it?',
                    'She was the first woman professor in Paris!',
                    'Her notebooks are still radioactive today!',
                    'She died from radiation exposure because she was so dedicated!'
                ]
            },
            'newton': {
                'name': 'Isaac Newton',
                'desc': 'the father of classical physics!',
                'details': [
                    'He discovered gravity when an apple fell on his head!',
                    'He formulated the three laws of motion!',
                    'He invented calculus!',
                    'He built the first reflecting telescope!',
                    'He was president of the Royal Society!'
                ]
            },
            'tesla': {
                'name': 'Nikola Tesla',
                'desc': 'the electrical wizard!',
                'details': [
                    'He invented alternating current (AC)!',
                    'He developed the Tesla coil!',
                    'He had over 300 patents! Amazing!',
                    'He dreamed of wireless electricity!',
                    'He spoke 8 languages!'
                ]
            },
            'hawking': {
                'name': 'Stephen Hawking',
                'desc': 'the brilliant cosmologist who studied black holes!',
                'details': [
                    'He wrote "A Brief History of Time"!',
                    'He discovered that black holes emit radiation!',
                    'He had ALS and communicated with a speech synthesizer!',
                    'He believed aliens might exist!',
                    'He said: Intelligence is the ability to adapt!'
                ]
            }
        }
        
        # صور حقيقية
        for filename in os.listdir(images_dir):
            if filename.endswith(('.jpg', '.png')):
                for key, data in scientists.items():
                    if key in filename.lower():
                        img = cv2.imread(os.path.join(images_dir, filename))
                        if img is not None:
                            img = cv2.resize(img, (400, 500))
                            images.append({
                                'type': 'scientist',
                                'name': data['name'],
                                'desc': data['desc'],
                                'details': data['details'],
                                'image': img
                            })
                            print(f"✅ عالم: {data['name']}")
                        break
        
        # أفلام
        movies = [
            ('Interstellar', 'Christopher Nolan', 'sci-fi masterpiece!', 
             ['A team travels through a wormhole!', 
              'Matthew McConaughey is amazing!',
              'The ending will blow your mind!',
              'Hans Zimmer composed the epic music!']),
            ('Inception', 'Christopher Nolan', 'dream within a dream!',
             ['Leo DiCaprio steals dreams!',
              'The spinning top at the end!',
              'Visual effects are incredible!',
              'One of the best sci-fi movies ever!']),
            ('The Matrix', 'The Wachowskis', 'what is reality?',
             ['Keanu Reeves is Neo!',
              'Bullet time scenes are iconic!',
              'Red pill or blue pill?',
              'Changed action movies forever!']),
            ('Avatar', 'James Cameron', 'the highest grossing film!',
             ['Blue aliens on Pandora!',
              '3D technology revolutionized!',
              'Environmental message!',
              'Sequels are coming!']),
            ('Titanic', 'James Cameron', 'the ship of dreams!',
             ['Leo and Kate Winslet!',
              'My heart will go on!',
              'Historical tragedy!',
              'Won 11 Oscars!']),
            ('Pulp Fiction', 'Quentin Tarantino', 'cult classic!',
             ['John Travolta dances!',
              'Uma Thurman overdoses!',
              'Non-linear storytelling!',
              'Samuel L Jackson quotes!']),
            ('Star Wars', 'George Lucas', 'the force awakens!',
             ['I am your father!',
              'Lightsabers are cool!',
              'Han Solo shoots first!',
              'May the force be with you!']),
            ('The Dark Knight', 'Christopher Nolan', 'the best Batman movie!',
             ['Heath Ledger as Joker!',
              'Why so serious?',
              'Christian Bale is Batman!',
              'Moral dilemmas!']),
            ('Forrest Gump', 'Robert Zemeckis', 'life is like a box of chocolates!',
             ['Tom Hanks is amazing!',
              'Run Forrest run!',
              'Historical moments!',
              'Won 6 Oscars!']),
            ('The Godfather', 'Francis Ford Coppola', 'the mafia masterpiece!',
             ['Marlon Brando!',
              'Al Pacino!',
              'I will make him an offer!',
              'Best movie ever made!'])
        ]
        
        for title, director, tag, details in movies:
            img = np.ones((500, 400, 3), dtype=np.uint8) * 30
            cv2.putText(img, f"🎬 {title}", (30, 150), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255,215,0), 2)
            cv2.putText(img, f"Director: {director}", (30, 250), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (200,200,200), 2)
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
              'Doublethink!',
              'Still relevant today!']),
            ('To Kill a Mockingbird', 'Harper Lee', 'American literature masterpiece!',
             ['Atticus Finch!',
              'Racial injustice!',
              'Scout and Jem!',
              'Pulitzer Prize winner!']),
            ('The Great Gatsby', 'F. Scott Fitzgerald', 'the jazz age!',
             ['The green light!',
              'Tragic love story!',
              'Rich and poor!',
              'American dream!']),
            ('Moby Dick', 'Herman Melville', 'the white whale!',
             ['Call me Ishmael!',
              'Captain Ahab obsessed!',
              'Epic adventure!',
              'Classic literature!']),
            ('War and Peace', 'Leo Tolstoy', 'Russian epic!',
             ['Over 1000 pages!',
              'Napoleon invasion!',
              'Many characters!',
              'Philosophical themes!'])
        ]
        
        for title, author, tag, details in books:
            img = np.ones((500, 400, 3), dtype=np.uint8) * 20
            cv2.putText(img, f"📚 {title}", (30, 150), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255,255,255), 2)
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

    def show_text_above_pepper(self, lines):
        """نص طويل فوق Pepper"""
        pos = self.pepper.getPosition()
        y_offset = 1.8
        for i, line in enumerate(lines[:3]):  # 3 أسطر بس
            self.text_id = p.addUserDebugText(
                line,
                [pos[0], pos[1], pos[2] + y_offset - i*0.3],
                [0, 0, 0],
                textSize=1.2,
                lifeTime=3
            )

    def move_excited(self):
        """حركة متحمسة"""
        # مشي مع دوران
        self.pepper.move(self.walk_speed, 0, self.turn_speed * random.choice([-1, 1]))
        self.move_hands_naturally()

    def run(self):
        print("\n" + "="*70)
        print("🌟 Pepper المتحمس - نصوص طويلة وحركة طبيعية")
        print("="*70 + "\n")
        
        self.speak("OH MY GOD! I'm so excited to show you all these amazing things!")
        
        try:
            while self.running:
                # حركة متحمسة
                self.move_excited()
                
                # كل 3 ثواني نغير الصورة
                if time.time() - self.last_update > 3:
                    img_data = self.all_images[self.current_index]
                    detected, detections = self.detect_with_yolo(img_data['image'].copy())
                    
                    # إضافة اسم على الصورة
                    cv2.putText(detected, f"★ {img_data['name']} ★", (20, 50),
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)
                    
                    cv2.imshow("Excited Pepper Detection", detected)
                    cv2.waitKey(1)
                    
                    # تحضير النص الطويل
                    if img_data['type'] == 'scientist':
                        detail = random.choice(img_data['details'])
                        speech = f"OH! This is {img_data['name']}! {img_data['desc']} {detail}"
                        lines = [img_data['name'], img_data['desc'], detail]
                    elif img_data['type'] == 'movie':
                        detail = random.choice(img_data['details'])
                        speech = f"WOW! {img_data['name']} by {img_data['director']}! {img_data['desc']} {detail}"
                        lines = [f"Movie: {img_data['name']}", f"Director: {img_data['director']}", detail]
                    else:  # book
                        detail = random.choice(img_data['details'])
                        speech = f"AMAZING! The book {img_data['name']} by {img_data['author']}! {img_data['desc']} {detail}"
                        lines = [f"Book: {img_data['name']}", f"Author: {img_data['author']}", detail]
                    
                    # كلام متحمس
                    print(f"🔥 {speech}")
                    self.speak(speech)
                    
                    # نص فوق Pepper
                    self.show_text_above_pepper(lines)
                    
                    self.current_index += 1
                    if self.current_index >= len(self.all_images):
                        self.current_index = 0
                        random.shuffle(self.all_images)
                        print("\n🔥 WOW! New round! Let's do it again!")
                        self.speak("That was fantastic! Let's see more amazing things!")
                    
                    self.last_update = time.time()
                
                time.sleep(0.05)
                
        except KeyboardInterrupt:
            print("\n\n👋 Bye! Thanks for watching!")
            self.speak("Goodbye! It was so much fun!")
        finally:
            cv2.destroyAllWindows()
            self.sim_manager.stopSimulation(self.client)

if __name__ == "__main__":
    app = PepperExcitedTalker()
    app.run()
