import time
import pybullet as p
import pybullet_data
import threading
import random
import queue
import numpy as np
import cv2
from qibullet import SimulationManager
import pyttsx3
import speech_recognition as sr
from ultralytics import YOLO

class PepperRoomWithKids:
    def __init__(self):
        print("🚀 بناء غرفة Pepper مع الأطفال...")
        
        # الصوت
        self.init_voice()
        
        # التعرف على الصوت
        self.init_speech()
        
        # محاكي
        self.sim_manager = SimulationManager()
        self.client = self.sim_manager.launchSimulation(gui=True)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.loadURDF("plane.urdf")
        
        # بناء الغرفة
        self.build_room()
        
        # إضافة Pepper
        self.add_pepper()
        
        # إضافة الأطفال
        self.kids = []
        self.add_kids()
        
        # YOLO (لما يراه Pepper)
        self.yolo = YOLO('yolov8n.pt')
        
        # متغيرات التشغيل
        self.running = True
        self.speech_queue = queue.Queue()
        self.text_id = None
        
        # بدء مستمع الصوت
        self.start_listener()
        
        print("✅ Pepper جاهز في الغرفة مع الأطفال!")
        self.speak("Hello everyone! I'm Pepper. Let's play together!")

    def init_voice(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 170)
        self.engine.setProperty('volume', 1.0)
        voices = self.engine.getProperty('voices')
        for voice in voices:
            if 'english' in voice.name.lower():
                self.engine.setProperty('voice', voice.id)
                break

    def init_speech(self):
        self.recognizer = sr.Recognizer()
        try:
            self.microphone = sr.Microphone()
            with self.microphone as source:
                print("🔄 معايرة الميكروفون...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
            print("✅ الميكروفون جاهز")
        except Exception as e:
            print(f"⚠️ مشكلة في الميكروفون: {e}")
            self.microphone = None

    def start_listener(self):
        def listen_loop():
            if not self.microphone:
                return
            while self.running:
                try:
                    with self.microphone as source:
                        print("\n🎤 استماع... (تحدث الآن)")
                        audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=5)
                    text = self.recognizer.recognize_google(audio)
                    print(f"📝 أنت: {text}")
                    self.speech_queue.put(text)
                except sr.WaitTimeoutError:
                    pass
                except sr.UnknownValueError:
                    pass
                except Exception as e:
                    print(f"⚠️ خطأ: {e}")
                time.sleep(0.1)
        
        threading.Thread(target=listen_loop, daemon=True).start()

    def speak(self, text):
        def speak_thread():
            self.engine.say(text)
            self.engine.runAndWait()
        threading.Thread(target=speak_thread, daemon=True).start()

    def build_room(self):
        """بناء الغرفة"""
        # أرضية
        p.loadURDF("plane.urdf")
        
        # جدران
        wall_color = [0.8, 0.8, 0.9, 0.5]
        
        # جدار خلفي
        wall_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[6, 0.2, 3], rgbaColor=wall_color)
        p.createMultiBody(baseVisualShapeIndex=wall_vis, basePosition=[0, -6, 1.5])
        
        # جدار أمامي
        p.createMultiBody(baseVisualShapeIndex=wall_vis, basePosition=[0, 6, 1.5])
        
        # جدار أيمن
        wall_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.2, 6, 3], rgbaColor=wall_color)
        p.createMultiBody(baseVisualShapeIndex=wall_vis, basePosition=[6, 0, 1.5])
        
        # جدار أيسر
        p.createMultiBody(baseVisualShapeIndex=wall_vis, basePosition=[-6, 0, 1.5])
        
        # سجادة
        carpet_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[5, 5, 0.05], rgbaColor=[0.6, 0.4, 0.2, 1])
        p.createMultiBody(baseVisualShapeIndex=carpet_vis, basePosition=[0, 0, 0.05])
        
        # طاولة
        self.add_table([2, 2, 0])
        
        # كراسي
        self.add_chair([2.5, 2.5, 0])
        self.add_chair([1.5, 1.5, 0])
        self.add_chair([-2, -2, 0])
        
        # ألعاب
        self.add_toy([1, 0, 0.2], [1, 0, 0])    # كرة حمراء
        self.add_toy([-1, 1, 0.2], [0, 1, 0])   # كرة خضراء
        self.add_toy([0, -1, 0.2], [0, 0, 1])   # كرة زرقاء

    def add_table(self, pos):
        """إضافة طاولة"""
        # سطح
        col_id = p.createCollisionShape(p.GEOM_BOX, halfExtents=[0.8, 0.5, 0.1])
        vis_id = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.8, 0.5, 0.1], rgbaColor=[0.5, 0.3, 0.1, 1])
        p.createMultiBody(baseMass=10, baseCollisionShapeIndex=col_id, 
                         baseVisualShapeIndex=vis_id, basePosition=[pos[0], pos[1], pos[2] + 0.8])
        
        # أرجل
        for dx, dy in [(-0.6, -0.3), (0.6, -0.3), (-0.6, 0.3), (0.6, 0.3)]:
            leg_col = p.createCollisionShape(p.GEOM_CYLINDER, radius=0.1, height=0.8)
            leg_vis = p.createVisualShape(p.GEOM_CYLINDER, radius=0.1, length=0.8, rgbaColor=[0.4, 0.2, 0.1, 1])
            p.createMultiBody(baseMass=5, baseCollisionShapeIndex=leg_col,
                            baseVisualShapeIndex=leg_vis,
                            basePosition=[pos[0] + dx, pos[1] + dy, pos[2] + 0.4])

    def add_chair(self, pos):
        """إضافة كرسي"""
        col_id = p.createCollisionShape(p.GEOM_BOX, halfExtents=[0.4, 0.4, 0.4])
        vis_id = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.4, 0.4, 0.4], rgbaColor=[0.3, 0.2, 0.1, 1])
        p.createMultiBody(baseMass=5, baseCollisionShapeIndex=col_id,
                         baseVisualShapeIndex=vis_id, basePosition=[pos[0], pos[1], pos[2] + 0.2])

    def add_toy(self, pos, color):
        """إضافة لعبة"""
        col_id = p.createCollisionShape(p.GEOM_SPHERE, radius=0.15)
        vis_id = p.createVisualShape(p.GEOM_SPHERE, radius=0.15, rgbaColor=color + [1])
        p.createMultiBody(baseMass=0.5, baseCollisionShapeIndex=col_id,
                         baseVisualShapeIndex=vis_id, basePosition=pos)

    def add_pepper(self):
        """إضافة Pepper"""
        self.pepper = self.sim_manager.spawnPepper(
            self.client, translation=[-3, 0, 0.2], quaternion=[0, 0, 0, 1]
        )
        
        # كاميرا Pepper (افتراضية)
        self.camera_pos = [-3, 0, 1.2]

    def add_kids(self):
        """إضافة أطفال"""
        kid_names = ["Lina", "Omar", "Nour", "Ali", "Hala"]
        kid_colors = [
            [1, 0.8, 0.8, 1],  # وردي
            [0.8, 1, 0.8, 1],  # أخضر فاتح
            [0.8, 0.8, 1, 1],  # أزرق فاتح
            [1, 1, 0.8, 1],    # أصفر
            [1, 0.8, 1, 1]     # بنفسجي
        ]
        
        positions = [
            [1, 2, 0.2],
            [2, -1, 0.2],
            [-1, -2, 0.2],
            [-2, 1, 0.2],
            [3, 3, 0.2]
        ]
        
        for i, (pos, color, name) in enumerate(zip(positions, kid_colors, kid_names)):
            # جسم الطفل
            col_id = p.createCollisionShape(p.GEOM_CYLINDER, radius=0.2, height=0.8)
            vis_id = p.createVisualShape(p.GEOM_CYLINDER, radius=0.2, length=0.8, rgbaColor=color)
            body = p.createMultiBody(baseMass=3, baseCollisionShapeIndex=col_id,
                                    baseVisualShapeIndex=vis_id, basePosition=pos)
            
            # رأس الطفل
            head_pos = [pos[0], pos[1], pos[2] + 0.4]
            head_vis = p.createVisualShape(p.GEOM_SPHERE, radius=0.15, rgbaColor=[1, 0.9, 0.8, 1])
            head = p.createMultiBody(baseMass=0, baseVisualShapeIndex=head_vis,
                                    basePosition=head_pos)
            
            # اسم الطفل
            p.addUserDebugText(name, [pos[0], pos[1], pos[2] + 0.8], [0, 0, 0], textSize=1)
            
            self.kids.append({
                'name': name,
                'body': body,
                'head': head,
                'pos': pos,
                'age': random.randint(4, 8)
            })

    def get_pepper_view(self):
        """ما يراه Pepper (محاكاة)"""
        # نافذة منفصلة لعرض رؤية Pepper
        view_img = np.ones((400, 600, 3), dtype=np.uint8) * 200
        
        # رسم الأطفال كما يراهم Pepper
        y_offset = 50
        for kid in self.kids:
            # حساب المسافة
            dist = np.sqrt((kid['pos'][0] - self.camera_pos[0])**2 + 
                          (kid['pos'][1] - self.camera_pos[1])**2)
            
            if dist < 5:  # إذا كان الطفل قريب
                color = (0, 255, 0) if dist < 2 else (0, 255, 255)
                cv2.putText(view_img, f"👤 {kid['name']}", (50, y_offset), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                y_offset += 30
        
        cv2.putText(view_img, "Pepper's View", (250, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,0), 2)
        
        cv2.imshow("What Pepper Sees", view_img)
        cv2.waitKey(1)

    def move_to_kid(self, kid_idx):
        """Pepper يتحرك نحو طفل"""
        if kid_idx >= len(self.kids):
            return
        
        target = self.kids[kid_idx]['pos']
        current = self.pepper.getPosition()
        
        dx = target[0] - current[0]
        dy = target[1] - current[1]
        
        if abs(dx) > 0.2 or abs(dy) > 0.2:
            self.pepper.move(0.1 * dx, 0, 0.05 * dy)
            return False
        
        # وصل للطفل
        self.camera_pos = [current[0], current[1], current[2] + 1.0]
        return True

    def wave(self):
        """يلوح"""
        for i in range(3):
            try:
                self.pepper.setAngles(["RShoulderPitch"], [-0.7], 0.5)
                time.sleep(0.2)
                self.pepper.setAngles(["RShoulderPitch"], [0.3], 0.5)
                time.sleep(0.2)
            except:
                pass

    def show_text(self, text):
        """نص فوق Pepper"""
        pos = self.pepper.getPosition()
        if self.text_id:
            p.removeUserDebugItem(self.text_id)
        self.text_id = p.addUserDebugText(
            text, [pos[0], pos[1], pos[2] + 2.0], [0,0,0], textSize=1.5, lifeTime=3
        )

    def process_speech(self, text):
        """معالجة الكلام"""
        text_lower = text.lower()
        
        if "hello" in text_lower or "hi" in text_lower:
            response = f"Hello! I'm playing with {len(self.kids)} kids!"
            print(f"🤖 Pepper: {response}")
            self.speak(response)
            self.wave()
            return
        
        if "who" in text_lower or "name" in text_lower:
            kids_list = ", ".join([k['name'] for k in self.kids[:3]])
            response = f"I'm with {kids_list} and others"
            print(f"🤖 Pepper: {response}")
            self.speak(response)
            return
        
        if "play" in text_lower or "game" in text_lower:
            response = "Let's play together! I love playing with children."
            print(f"🤖 Pepper: {response}")
            self.speak(response)
            return
        
        # ردود عامة
        responses = [
            "That's nice! Tell me more.",
            "I understand. Go on...",
            "Really? How interesting!",
            "The children are having fun!",
            "I love talking with you!"
        ]
        response = random.choice(responses)
        print(f"🤖 Pepper: {response}")
        self.speak(response)

    def run(self):
        """تشغيل المحاكاة"""
        print("\n" + "="*70)
        print("🌟 Pepper في الغرفة مع الأطفال")
        print("="*70 + "\n")
        
        self.speak("Welcome to the kids room! I'm Pepper.")
        
        current_kid = 0
        last_action = time.time()
        
        try:
            while self.running:
                # 1. Pepper يتجول بين الأطفال
                if time.time() - last_action > 5:
                    current_kid = (current_kid + 1) % len(self.kids)
                    kid_name = self.kids[current_kid]['name']
                    self.speak(f"Hello {kid_name}! How are you?")
                    self.show_text(f"Talking to {kid_name}")
                    last_action = time.time()
                
                self.move_to_kid(current_kid)
                
                # 2. عرض رؤية Pepper
                self.get_pepper_view()
                
                # 3. معالجة الصوت
                if not self.speech_queue.empty():
                    text = self.speech_queue.get()
                    self.process_speech(text)
                
                # 4. حركات عشوائية
                if random.random() < 0.01:
                    self.wave()
                
                time.sleep(0.05)
                
        except KeyboardInterrupt:
            print("\n\n👋 Bye!")
        finally:
            cv2.destroyAllWindows()
            self.sim_manager.stopSimulation(self.client)

if __name__ == "__main__":
    app = PepperRoomWithKids()
    app.run()
