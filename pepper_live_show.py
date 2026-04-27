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

class PepperLiveShow:
    def __init__(self):
        print("🚀 تشغيل Pepper Live Show - صور متحركة وحركة طبيعية...")
        
        # الصوت
        self.init_voice()
        
        # محاكي
        self.sim_manager = SimulationManager()
        self.client = self.sim_manager.launchSimulation(gui=True)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.loadURDF("plane.urdf")
        
        # إعدادات النافذة
        p.configureDebugVisualizer(p.COV_ENABLE_GUI, 1)
        p.configureDebugVisualizer(p.COV_ENABLE_SHADOWS, 1)
        p.resetDebugVisualizerCamera(4.0, 60, -30, [0, 0, 1])
        
        # Pepper
        print("🤖 تحميل Pepper...")
        self.pepper = self.sim_manager.spawnPepper(
            self.client,
            translation=[-1, 0, 0],
            quaternion=[0, 0, 0, 1]
        )
        
        # وضع اليدين الطبيعي
        self.reset_arms()
        
        # تحميل العلماء
        self.scientists = []
        self.load_scientists()
        
        # نافذة OpenCV للصور
        cv2.namedWindow("Scientist Gallery", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Scientist Gallery", 600, 800)
        cv2.moveWindow("Scientist Gallery", 1000, 50)
        
        self.current_index = 0
        self.running = True
        self.is_speaking = False
        
        print(f"✅ تم تحميل {len(self.scientists)} عالم")
        self.speak("Welcome to the scientist gallery! I will introduce each one.")

    def init_voice(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 150)
        self.engine.setProperty('volume', 1.0)
        voices = self.engine.getProperty('voices')
        for voice in voices:
            if 'english' in voice.name.lower():
                self.engine.setProperty('voice', voice.id)
                break
        print("✅ الصوت جاهز")

    def speak(self, text):
        self.is_speaking = True
        def t():
            self.engine.say(text)
            self.engine.runAndWait()
            self.is_speaking = False
        threading.Thread(target=t, daemon=True).start()

    def reset_arms(self):
        """وضع اليدين الطبيعي (منخفض)"""
        self.pepper.setAngles(["LShoulderPitch"], [1.57], 0.1)
        self.pepper.setAngles(["RShoulderPitch"], [0.2], 0.1)
        self.pepper.setAngles(["LElbowRoll"], [-1.2], 0.1)
        self.pepper.setAngles(["RElbowRoll"], [1.2], 0.1)

    def wave_hand(self):
        """يلوح بيده"""
        self.pepper.setAngles(["RShoulderPitch"], [-0.8], 0.2)
        time.sleep(0.2)
        self.pepper.setAngles(["RShoulderPitch"], [0.2], 0.2)
        time.sleep(0.2)
        self.pepper.setAngles(["RShoulderPitch"], [-0.5], 0.2)
        time.sleep(0.2)
        self.pepper.setAngles(["RShoulderPitch"], [0.2], 0.2)
        self.reset_arms()

    def move_arms_naturally(self):
        """حركة يدين طبيعية أثناء الكلام"""
        if random.random() > 0.5:
            self.pepper.setAngles(["LShoulderPitch"], [1.2], 0.1)
            time.sleep(0.3)
            self.pepper.setAngles(["LShoulderPitch"], [1.57], 0.1)
        else:
            self.pepper.setAngles(["RShoulderPitch"], [-0.3], 0.1)
            time.sleep(0.3)
            self.pepper.setAngles(["RShoulderPitch"], [0.2], 0.1)

    def walk_in_place(self):
        """حركة مشي في المكان"""
        self.pepper.move(0.1, 0, 0.05)
        time.sleep(0.5)
        self.pepper.move(-0.05, 0, -0.03)
        time.sleep(0.5)

    def turn_head(self):
        """يدير رأسه"""
        self.pepper.setAngles(["HeadYaw"], [0.5], 0.1)
        time.sleep(0.3)
        self.pepper.setAngles(["HeadYaw"], [-0.5], 0.1)
        time.sleep(0.3)
        self.pepper.setAngles(["HeadYaw"], [0.0], 0.1)

    def load_scientists(self):
        """تحميل صور العلماء مع معلوماتهم"""
        images_dir = os.path.expanduser("~/pepper_duo/data/known_faces/")
        
        scientist_info = {
            'einstein': {
                'name': 'Albert Einstein',
                'facts': [
                    'developed the theory of relativity',
                    'won the Nobel Prize in Physics in 1921',
                    'his famous equation is E = mc²',
                    'said: Imagination is more important than knowledge',
                    'escaped Nazi Germany and came to USA'
                ]
            },
            'marie_curie': {
                'name': 'Marie Curie',
                'facts': [
                    'discovered radium and polonium',
                    'first person to win two Nobel Prizes',
                    'died from radiation exposure',
                    'was the first female professor at Sorbonne',
                    'her notebooks are still radioactive'
                ]
            },
            'newton': {
                'name': 'Isaac Newton',
                'facts': [
                    'formulated the laws of motion',
                    'discovered gravity when an apple fell',
                    'invented calculus',
                    'was president of the Royal Society',
                    'built the first reflecting telescope'
                ]
            },
            'tesla': {
                'name': 'Nikola Tesla',
                'facts': [
                    'invented alternating current',
                    'developed the Tesla coil',
                    'had over 300 patents',
                    'dreamed of wireless electricity',
                    'spoke 8 languages'
                ]
            },
            'hawking': {
                'name': 'Stephen Hawking',
                'facts': [
                    'studied black holes and cosmology',
                    'wrote A Brief History of Time',
                    'had ALS and used a speech synthesizer',
                    'believed aliens might exist',
                    'said: Intelligence is the ability to adapt'
                ]
            }
        }
        
        for filename in os.listdir(images_dir):
            if filename.endswith(('.jpg', '.png', '.jpeg')):
                filepath = os.path.join(images_dir, filename)
                base_name = os.path.splitext(filename)[0].lower()
                
                # قراءة الصورة
                img = cv2.imread(filepath)
                if img is not None:
                    img = cv2.resize(img, (400, 500))
                    
                    # البحث عن المعلومات
                    for key, info in scientist_info.items():
                        if key in base_name:
                            self.scientists.append({
                                'name': info['name'],
                                'facts': info['facts'],
                                'image': img,
                                'key': key
                            })
                            print(f"✅ Added: {info['name']}")
                            break

    def display_current_scientist(self):
        """عرض العالم الحالي في نافذة OpenCV"""
        if self.current_index < len(self.scientists):
            s = self.scientists[self.current_index]
            
            # نسخ الصورة
            img = s['image'].copy()
            h, w = img.shape[:2]
            
            # رسم إطار أخضر
            cv2.rectangle(img, (5, 5), (w-5, h-5), (0, 255, 0), 5)
            
            # كتابة الاسم في أعلى الصورة
            cv2.putText(img, s['name'], (30, 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
            
            cv2.imshow("Scientist Gallery", img)
            cv2.waitKey(1)
            
            return s
        return None

    def show_text_over_pepper(self, text, duration=3):
        """عرض نص فوق Pepper"""
        pos = self.pepper.getPosition()
        p.addUserDebugText(
            text,
            [pos[0], pos[1], pos[2] + 1.8],
            [0, 0, 0],  # أسود
            textSize=1.5,
            lifeTime=duration
        )

    def introduce_scientist(self, scientist):
        """تقديم العالم - كلام وحركة"""
        print(f"\n🌟 Introducing: {scientist['name']}")
        
        # 1. يدير رأسه ناحية الصورة (وهمي)
        self.turn_head()
        
        # 2. يتقدم للأمام
        self.pepper.move(0.3, 0, 0)
        time.sleep(1)
        
        # 3. يقول الاسم
        name_text = f"This is {scientist['name']}!"
        print(f"💬 {name_text}")
        self.speak(name_text)
        self.show_text_over_pepper(name_text, 3)
        
        # 4. يلوح بيده
        self.wave_hand()
        time.sleep(1)
        
        # 5. يقول حقيقة
        fact = random.choice(scientist['facts'])
        fact_text = f"He {fact}"
        print(f"💬 {fact_text}")
        self.speak(fact_text)
        self.show_text_over_pepper(fact_text, 4)
        
        # 6. حركة يدين أثناء الكلام
        self.move_arms_naturally()
        time.sleep(2)
        
        # 7. يعود للخلف قليلاً
        self.pepper.move(-0.2, 0, 0)
        self.reset_arms()

    def run(self):
        print("\n" + "="*70)
        print("🌟 Pepper Live Show - معرض العلماء المتحرك")
        print("="*70 + "\n")
        
        self.speak("Let me show you the scientists gallery!")
        time.sleep(2)
        
        try:
            while self.running and self.current_index < len(self.scientists):
                # 1. عرض العالم الحالي
                scientist = self.display_current_scientist()
                
                if scientist:
                    # 2. تقديم العالم (كلام وحركة)
                    self.introduce_scientist(scientist)
                    
                    # 3. الانتظار قليلاً
                    time.sleep(2)
                    
                    # 4. الانتقال للعالم التالي
                    self.current_index += 1
                    
                    # 5. حركة انتقالية
                    self.walk_in_place()
                    self.turn_head()
                    
                    print(f"\n🔄 Moving to next scientist... ({self.current_index+1}/{len(self.scientists)})")
                else:
                    break
                
                # 6. الخروج إذا انتهت الصور
                if self.current_index >= len(self.scientists):
                    print("\n🎉 End of gallery!")
                    self.speak("That's all! Hope you enjoyed learning about these great scientists!")
                    
                    # رقصة صغيرة فرحانة
                    for i in range(3):
                        self.wave_hand()
                        time.sleep(0.5)
                    
                    break
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            
            # انتظار حتى يخلص الكلام
            while self.is_speaking:
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            print("\n\n👋 إيقاف Pepper...")
        finally:
            cv2.destroyAllWindows()
            self.sim_manager.stopSimulation(self.client)

if __name__ == "__main__":
    app = PepperLiveShow()
    app.run()
