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

class PepperSuperMuseum:
    def __init__(self):
        print("🚀 تشغيل Pepper السريع في المتحف الكبير...")
        
        # YOLO
        print("📦 تحميل YOLO...")
        self.yolo = YOLO('yolov8n.pt')
        
        # الصوت
        self.init_voice()
        
        # محاكي
        self.sim_manager = SimulationManager()
        self.client = self.sim_manager.launchSimulation(gui=True)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.loadURDF("plane.urdf")
        
        p.configureDebugVisualizer(p.COV_ENABLE_GUI, 0)
        p.configureDebugVisualizer(p.COV_ENABLE_SHADOWS, 1)
        p.resetDebugVisualizerCamera(4.5, 50, -30, [0, 0, 1])
        
        # Pepper سريع
        print("🤖 تحميل Pepper السريع...")
        self.pepper = self.sim_manager.spawnPepper(
            self.client,
            translation=[-3, 0, 0],
            quaternion=[0, 0, 0, 1]
        )
        
        # سرعة عالية
        self.speed = 0.7
        self.walk_speed = 0.3
        
        # تحميل العلماء
        self.images = self.load_scientists()
        
        # إضافة صور إضافية (أفلام، كتب)
        self.extra_images = self.load_extra_images()
        self.all_images = self.images + self.extra_images
        
        # نافذة YOLO
        cv2.namedWindow("YOLO Super Detection", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("YOLO Super Detection", 1000, 700)
        cv2.moveWindow("YOLO Super Detection", 900, 50)
        
        self.current_index = 0
        self.last_update = time.time()
        self.text_id = None
        self.running = True
        self.speech_queue = queue.Queue()
        self.start_speech_worker()
        
        print(f"✅ تم تحميل {len(self.all_images)} صورة (علماء + أفلام + كتب)")
        self.speak("Super fast museum tour!")

    def init_voice(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 180)  # أسرع
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
                    text = self.speech_queue.get(timeout=0.5)
                    self.engine.say(text)
                    self.engine.runAndWait()
                except queue.Empty:
                    continue
        threading.Thread(target=worker, daemon=True).start()

    def load_scientists(self):
        """تحميل العلماء"""
        scientists = []
        images_dir = os.path.expanduser("~/pepper_duo/data/known_faces/")
        
        scientist_info = {
            'einstein': ('Albert Einstein', 'physicist who developed relativity', ['E=mc²', 'Nobel Prize', 'German']),
            'marie_curie': ('Marie Curie', 'discovered radium and polonium', ['Two Nobels', 'Radioactivity', 'Polish']),
            'newton': ('Isaac Newton', 'formulated laws of motion and gravity', ['Calculus', 'English', 'Apple story']),
            'tesla': ('Nikola Tesla', 'invented alternating current', ['Tesla coil', 'Wireless', 'Serbian']),
            'hawking': ('Stephen Hawking', 'studied black holes', ['Brief History of Time', 'ALS', 'British']),
            'galileo': ('Galileo Galilei', 'father of modern astronomy', ['Telescope', 'Jupiter moons', 'Italian']),
            'ada': ('Ada Lovelace', 'first computer programmer', ['Algorithm', 'Babbage', 'English']),
            'turing': ('Alan Turing', 'father of computer science', ['Enigma', 'AI', 'British']),
            'curie': ('Pierre Curie', 'radioactivity research', ['Nobel Prize', 'French', 'Physics']),
            'darwin': ('Charles Darwin', 'theory of evolution', ['Natural selection', 'Beagle', 'English'])
        }
        
        IMG_SIZE = (400, 500)
        
        for filename in os.listdir(images_dir):
            if filename.endswith(('.jpg', '.png', '.jpeg')):
                for key, (name, desc, facts) in scientist_info.items():
                    if key in filename.lower():
                        img = cv2.imread(os.path.join(images_dir, filename))
                        if img is not None:
                            img = cv2.resize(img, IMG_SIZE)
                            scientists.append({
                                'name': name,
                                'desc': desc,
                                'facts': facts,
                                'type': 'scientist',
                                'image': img
                            })
                            print(f"✅ عالم: {name}")
                        break
        
        return scientists

    def load_extra_images(self):
        """إنشاء صور إضافية (أفلام، كتب)"""
        extras = []
        
        # أفلام
        movies = [
            ('Interstellar', 'Space exploration movie', ['space', 'wormhole', 'sci-fi']),
            ('Inception', 'Dream within a dream', ['DiCaprio', 'mind', 'oscar']),
            ('The Matrix', 'Virtual reality world', ['Neo', 'AI', 'simulation']),
            ('Avatar', 'Blue aliens on Pandora', ['3D', 'Cameron', 'billion dollar']),
            ('Titanic', 'Ship disaster romance', ['DiCaprio', 'Winslet', 'oscar']),
            ('The Godfather', 'Mafia family saga', ['Brando', 'Pacino', 'classic']),
            ('Pulp Fiction', 'Tarantino masterpiece', ['Travolta', 'Uma', 'cult']),
            ('Star Wars', 'Space opera saga', ['Jedi', 'Vader', 'Lucas']),
            ('The Dark Knight', 'Batman vs Joker', ['Ledger', 'Nolan', 'comic']),
            ('Forrest Gump', 'Life is like a box', ['Hanks', 'history', 'oscar'])
        ]
        
        # كتب
        books = [
            ('1984', 'Dystopian novel by Orwell', ['Big Brother', 'totalitarian', 'classic']),
            ('To Kill a Mockingbird', 'Racism in American south', ['Harper Lee', 'justice', 'Pulitzer']),
            ('The Great Gatsby', 'Jazz age tragedy', ['Fitzgerald', 'wealth', 'American']),
            ('Moby Dick', 'Whale hunting obsession', ['Melville', 'sea', 'classic']),
            ('War and Peace', 'Russian epic novel', ['Tolstoy', 'Napoleon', 'long']),
            ('Pride and Prejudice', 'Romance and manners', ['Austen', 'Darcy', 'English']),
            ('The Hobbit', 'Fantasy adventure', ['Tolkien', 'Bilbo', 'ring']),
            ('Crime and Punishment', 'Psychological drama', ['Dostoevsky', 'murder', 'Russian']),
            ('The Catcher in the Rye', 'Teenage rebellion', ['Salinger', 'Holden', 'American']),
            ('Brave New World', 'Future society', ['Huxley', 'dystopia', 'science'])
        ]
        
        # إنشاء صور وهمية
        for i, (title, desc, facts) in enumerate(movies):
            img = np.ones((500, 400, 3), dtype=np.uint8) * 30
            cv2.putText(img, f"🎬 {title}", (30, 150), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255,255,0), 2)
            cv2.putText(img, desc[:30], (30, 250), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200,200,200), 1)
            extras.append({
                'name': title,
                'desc': desc,
                'facts': facts,
                'type': 'movie',
                'image': img
            })
        
        for i, (title, desc, facts) in enumerate(books):
            img = np.ones((500, 400, 3), dtype=np.uint8) * 20
            cv2.putText(img, f"📚 {title}", (30, 150), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255,255,255), 2)
            cv2.putText(img, desc[:30], (30, 250), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200,200,200), 1)
            extras.append({
                'name': title,
                'desc': desc,
                'facts': facts,
                'type': 'book',
                'image': img
            })
        
        random.shuffle(extras)
        return extras[:10]  # 10 صور إضافية

    def detect_with_yolo(self, img):
        """كشف YOLO"""
        results = self.yolo(img)[0]
        detections = []
        img_copy = img.copy()
        
        for box in results.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = box.conf[0].item()
            cls = int(box.cls[0].item())
            label = self.yolo.names[cls]
            detections.append(label)
            
            color = (0,255,0) if conf > 0.7 else (0,255,255)
            cv2.rectangle(img_copy, (x1, y1), (x2, y2), color, 3)
            cv2.putText(img_copy, f"{label} {conf:.2f}", (x1, y1-10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        return img_copy, detections

    def show_text_below_pepper(self, lines):
        """نص متعدد الأسطر تحت Pepper"""
        pos = self.pepper.getPosition()
        y_offset = -0.5
        for i, line in enumerate(lines):
            self.text_id = p.addUserDebugText(
                line,
                [pos[0], pos[1], pos[2] + y_offset - i*0.3],
                [0, 0, 0],
                textSize=1.2,
                lifeTime=3
            )

    def move_pepper_fast(self):
        """حركة سريعة جداً"""
        self.pepper.move(self.walk_speed, 0, 0.2)
        self.pepper.setAngles(["RShoulderPitch", "LShoulderPitch"], 
                             [-0.5, 1.0], self.speed)
        self.pepper.setAngles(["RElbowRoll", "LElbowRoll"], 
                             [1.3, -1.3], self.speed)

    def run(self):
        print("\n" + "="*70)
        print("🌟 Pepper السريع - علماء + أفلام + كتب + كائنات")
        print("="*70 + "\n")
        
        self.speak("Super fast tour with movies and books!")
        
        try:
            while self.running:
                # حركة سريعة
                self.move_pepper_fast()
                
                # عرض الصورة الحالية
                if self.current_index < len(self.all_images):
                    img_data = self.all_images[self.current_index]
                    detected_img, detections = self.detect_with_yolo(img_data['image'].copy())
                    
                    # إضافة معلومات
                    cv2.putText(detected_img, f"★ {img_data['name']} ★", 
                               (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)
                    cv2.putText(detected_img, img_data['desc'], 
                               (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
                    
                    # عرض الكائنات
                    y_pos = 150
                    for det in detections[:5]:
                        cv2.putText(detected_img, f"• {det}", (20, y_pos),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,0), 1)
                        y_pos += 25
                    
                    cv2.imshow("YOLO Super Detection", detected_img)
                    cv2.waitKey(1)
                    
                    # كل 3 ثواني نتكلم
                    if time.time() - self.last_update > 3:
                        # نص تحت Pepper
                        lines = [
                            f"{img_data['name']}",
                            f"{img_data['desc']}",
                            f"Objects: {', '.join(detections[:3])}"
                        ]
                        self.show_text_below_pepper(lines)
                        
                        # كلام
                        if img_data['type'] == 'scientist':
                            fact = random.choice(img_data['facts'])
                            speech = f"{img_data['name']} was a {img_data['desc']}. {fact}"
                        else:
                            speech = f"This is {img_data['name']}. {img_data['desc']}"
                        
                        print(f"🔍 {speech}")
                        self.speak(speech)
                        
                        self.current_index += 1
                        if self.current_index >= len(self.all_images):
                            self.current_index = 0
                            random.shuffle(self.all_images)
                            print("\n🔥 Super fast new round!")
                        
                        self.last_update = time.time()
                
                time.sleep(0.05)  # تحديث سريع
                
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
        finally:
            cv2.destroyAllWindows()
            self.sim_manager.stopSimulation(self.client)

if __name__ == "__main__":
    app = PepperSuperMuseum()
    app.run()
