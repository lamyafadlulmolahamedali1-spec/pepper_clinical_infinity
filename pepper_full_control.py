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

class PepperFullControl:
    def __init__(self):
        print("🚀 تشغيل Pepper بالتحكم الكامل...")
        
        # الصوت
        self.init_voice()
        
        # محاكي
        self.sim_manager = SimulationManager()
        self.client = self.sim_manager.launchSimulation(gui=True)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.loadURDF("plane.urdf")
        
        # إعدادات
        p.configureDebugVisualizer(p.COV_ENABLE_GUI, 0)
        p.configureDebugVisualizer(p.COV_ENABLE_SHADOWS, 1)
        
        # Pepper
        print("🤖 تحميل Pepper...")
        self.pepper = self.sim_manager.spawnPepper(
            self.client,
            translation=[-3, 0, 0],
            quaternion=[0, 0, 0, 1]
        )
        
        # سرعات
        self.walk_speed = 0.2
        self.turn_speed = 0.3
        self.hand_speed = 0.4
        
        # حالة Pepper
        self.pos_x = -3.0
        self.pos_y = 0.0
        self.direction = 0  # 0 = أمام, 1 = يمين, 2 = خلف, 3 = يسار
        self.text_id = None
        self.hand_state = 0
        
        # تحميل العلماء
        self.scientists = self.load_scientists()
        
        # نافذة الصور
        self.create_image_window()
        
        self.current_index = 0
        self.last_update = time.time()
        self.last_hand_move = time.time()
        self.running = True
        self.speech_queue = queue.Queue()
        self.start_speech_worker()
        
        print(f"✅ تم تحميل {len(self.scientists)} عالم")
        self.speak("I am fully controlled! Watch me move!")

    def init_voice(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 170)
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
        
        IMG_WIDTH = 350
        IMG_HEIGHT = 450
        
        data = [
            {'name': 'Albert Einstein', 'key': 'einstein', 'facts': ['E=mc²', 'Relativity', 'Nobel Prize']},
            {'name': 'Marie Curie', 'key': 'marie_curie', 'facts': ['Radium', 'Two Nobels', 'Radioactivity']},
            {'name': 'Isaac Newton', 'key': 'newton', 'facts': ['Gravity', 'Laws of Motion', 'Calculus']},
            {'name': 'Nikola Tesla', 'key': 'tesla', 'facts': ['AC Current', 'Tesla Coil', 'Wireless']},
            {'name': 'Stephen Hawking', 'key': 'hawking', 'facts': ['Black Holes', 'Time', 'ALS']}
        ]
        
        for d in data:
            found = False
            for f in os.listdir(images_dir):
                if d['key'] in f.lower() and f.endswith(('.jpg', '.png')):
                    img = cv2.imread(os.path.join(images_dir, f))
                    if img is not None:
                        d['image'] = cv2.resize(img, (IMG_WIDTH, IMG_HEIGHT))
                        scientists.append(d)
                        found = True
                        break
            if not found:
                img = np.ones((IMG_HEIGHT, IMG_WIDTH, 3), dtype=np.uint8) * 200
                cv2.putText(img, d['name'], (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,0), 2)
                d['image'] = img
                scientists.append(d)
        
        return scientists

    def create_image_window(self):
        cv2.namedWindow("Scientists Gallery", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Scientists Gallery", 1900, 600)
        cv2.moveWindow("Scientists Gallery", 50, 50)
        self.img_width = 350
        self.img_height = 450
        self.gallery = np.ones((self.img_height + 100, 1900, 3), dtype=np.uint8) * 255

    def update_gallery(self):
        self.gallery[:] = 255
        x_pos = 30
        
        for i, s in enumerate(self.scientists):
            img = s['image'].copy()
            h, w = img.shape[:2]
            
            if i == self.current_index:
                cv2.rectangle(img, (5, 5), (w-5, h-5), (0, 255, 0), 8)
                cv2.putText(img, f"★ {s['name']} ★", (20, 50), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            else:
                cv2.rectangle(img, (5, 5), (w-5, h-5), (100, 100, 100), 2)
                cv2.putText(img, s['name'], (20, 50), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (100, 100, 100), 2)
            
            self.gallery[20:20+h, x_pos:x_pos+w] = img
            x_pos += w + 30
        
        cv2.imshow("Scientists Gallery", self.gallery)
        cv2.waitKey(1)

    def show_text_over_pepper(self, text):
        pos = self.pepper.getPosition()
        if self.text_id is not None:
            p.removeUserDebugItem(self.text_id)
        self.text_id = p.addUserDebugText(
            text,
            [pos[0], pos[1], pos[2] + 2.0],
            [0, 0, 0],
            textSize=1.8,
            lifeTime=3
        )

    def move_forward(self):
        """يمشي أمام"""
        self.pepper.move(self.walk_speed, 0, 0)
        self.pos_x += self.walk_speed * math.cos(self.direction)
        self.pos_y += self.walk_speed * math.sin(self.direction)

    def move_backward(self):
        """يمشي خلف"""
        self.pepper.move(-self.walk_speed, 0, 0)
        self.pos_x -= self.walk_speed * math.cos(self.direction)
        self.pos_y -= self.walk_speed * math.sin(self.direction)

    def turn_left(self):
        """يلتفت يسار"""
        self.pepper.move(0, 0, self.turn_speed)
        self.direction += self.turn_speed

    def turn_right(self):
        """يلتفت يمين"""
        self.pepper.move(0, 0, -self.turn_speed)
        self.direction -= self.turn_speed

    def move_hands(self):
        """حركة اليدين المستمرة"""
        if self.hand_state == 0:
            # رفع اليد اليمنى
            self.pepper.setAngles(["RShoulderPitch", "RElbowRoll"], 
                                 [-0.5, 1.2], self.hand_speed)
            self.hand_state = 1
        elif self.hand_state == 1:
            # رفع اليد اليسرى
            self.pepper.setAngles(["LShoulderPitch", "LElbowRoll"], 
                                 [1.0, -1.2], self.hand_speed)
            self.hand_state = 2
        elif self.hand_state == 2:
            # كلتا اليدين
            self.pepper.setAngles(["RShoulderPitch", "LShoulderPitch"], 
                                 [-0.3, 1.2], self.hand_speed)
            self.hand_state = 3
        else:
            # عودة طبيعية
            self.pepper.setAngles(["RShoulderPitch", "LShoulderPitch"], 
                                 [0.2, 1.57], self.hand_speed)
            self.pepper.setAngles(["RElbowRoll", "LElbowRoll"], 
                                 [1.2, -1.2], self.hand_speed)
            self.hand_state = 0

    def look_at_screen(self):
        """ينظر ناحية الشاشة (اليمين)"""
        self.pepper.setAngles(["HeadYaw", "HeadPitch"], 
                             [-0.5, 0.2], self.hand_speed)

    def look_around(self):
        """يدير رأسه"""
        self.pepper.setAngles(["HeadYaw"], [0.5], self.hand_speed)
        time.sleep(0.3)
        self.pepper.setAngles(["HeadYaw"], [-0.5], self.hand_speed)
        time.sleep(0.3)
        self.pepper.setAngles(["HeadYaw"], [0.0], self.hand_speed)

    def run(self):
        print("\n" + "="*70)
        print("🌟 Pepper بالتحكم الكامل - يمين يسار أمام خلف")
        print("="*70 + "\n")
        print("🔹 سيتحرك Pepper في اتجاهات مختلفة")
        print("🔹 انظري للشاشة لترى الصور")
        print("🔹 سيغير اتجاهه كل ثانيتين\n")
        
        self.speak("Watch me move in all directions!")
        
        move_cycle = 0
        target_x = 2.0  # ناحية الشاشة
        
        try:
            while self.running:
                # التحكم في الاتجاه
                if self.pos_x < target_x:
                    self.move_forward()
                else:
                    # وصل للشاشة
                    self.look_at_screen()
                
                # حركة دائرية
                if move_cycle % 20 == 0:
                    self.turn_right()
                elif move_cycle % 20 == 10:
                    self.turn_left()
                
                # حركة اليدين
                if time.time() - self.last_hand_move > 1:
                    self.move_hands()
                    self.last_hand_move = time.time()
                
                # تحديث المعرض
                self.update_gallery()
                
                # كل ثانيتين نتحدث عن عالم
                if time.time() - self.last_update > 2:
                    s = self.scientists[self.current_index]
                    fact = random.choice(s['facts'])
                    
                    self.show_text_over_pepper(f"{s['name']}: {fact}")
                    print(f"⚡ {s['name']}: {fact}")
                    self.speak(f"{s['name']} {fact}")
                    
                    # حركة يدين إضافية
                    self.move_hands()
                    self.look_around()
                    
                    self.current_index += 1
                    if self.current_index >= len(self.scientists):
                        self.current_index = 0
                        print("\n🔥 New round!")
                        # يرجع للخلف
                        target_x = -3.0
                    else:
                        target_x = 2.0
                    
                    self.last_update = time.time()
                
                move_cycle += 1
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
        finally:
            cv2.destroyAllWindows()
            self.sim_manager.stopSimulation(self.client)

if __name__ == "__main__":
    app = PepperFullControl()
    app.run()
