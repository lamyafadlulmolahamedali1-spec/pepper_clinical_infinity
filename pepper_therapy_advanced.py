import time
import random
import math
import pybullet as p
import pyttsx3
from qibullet import SimulationManager

# إعداد المحرك الصوتي بنبرة هادئة وواضحة
engine = pyttsx3.init()
engine.setProperty('rate', 135) 

class AutismTherapyBot:
    def __init__(self):
        self.sim_manager = SimulationManager()
        self.client = self.sim_manager.launchSimulation(gui=True)
        self.pepper = self.sim_manager.spawnPepper(self.client, spawn_ground_plane=True)
        
        # بيانات الأطفال مع ربط الألوان بالحالات (TEACCH Visual Cues)
        self.kids_data = [
            {"name": "Happy", "color": [1, 1, 0, 1], "pos": [2.5, 2.0, 0.6], "trait": "happy"},
            {"name": "Sad", "color": [0, 0, 1, 1], "pos": [2.5, -2.0, 0.6], "trait": "sad"},
            {"name": "Crying", "color": [0.5, 0, 0.5, 1], "pos": [4.0, 0.5, 0.6], "trait": "crying"},
            {"name": "Excited", "color": [1, 0, 0, 1], "pos": [1.0, 3.5, 0.6], "trait": "excited"},
            {"name": "Quiet", "color": [0, 1, 0, 1], "pos": [-1.5, 2.5, 0.6], "trait": "calm"},
            {"name": "Talkative", "color": [1, 0.5, 0, 1], "pos": [0.5, -3.0, 0.6], "trait": "talkative"}
        ]
        self.kids_ids = []
        self.setup_environment()

    def setup_environment(self):
        for kid in self.kids_data:
            # 1. إنشاء مجسم الطفل (Capsule)
            v_id = p.createVisualShape(p.GEOM_CAPSULE, radius=0.25, length=1.0, rgbaColor=kid['color'])
            k_id = p.createMultiBody(baseVisualShapeIndex=v_id, basePosition=kid['pos'])
            
            # 2. إضافة "محطة عمل" (Visual Workstation) أمام كل طفل (مبدأ TEACCH)
            # وضع مكعب صغير على الأرض أمام الطفل لتحديد "منطقة التفاعل"
            p.createMultiBody(
                baseVisualShapeIndex=p.createVisualShape(p.GEOM_BOX, halfExtents=[0.2, 0.2, 0.01], rgbaColor=kid['color']),
                basePosition=[kid['pos'][0]-0.6, kid['pos'][1], 0.01]
            )
            self.kids_ids.append((k_id, kid))
        
        self.pepper.setAngles(["LShoulderPitch", "RShoulderPitch", "HeadPitch"], [1.5, 1.5, 0.1], 0.1)

    def execute_aba_protocol(self, trait):
        """تنفيذ بروتوكول ABA/DTT: تعليمات واضحة -> استجابة -> تعزيز"""
        responses = {
            "happy": ("You are smiling! Let's share the joy.", ["RShoulderRoll"], [-0.5]),
            "sad": ("It's okay to be sad. I am sitting with you.", ["HeadPitch"], [0.4]),
            "crying": ("Softly now. Let's look at the lights. Shhh.", ["LShoulderPitch", "RShoulderPitch"], [1.8, 1.8]),
            "excited": ("High energy! Hands down for a moment. Good waiting.", ["LShoulderRoll", "RShoulderRoll"], [0.1, -0.1]),
            "calm": ("Excellent sitting! You win a golden star for being quiet.", ["HeadYaw"], [0.4]),
            "talkative": ("I hear you. Now, it is time for listening. Look at me.", ["HeadPitch"], [-0.2])
        }
        
        text, joints, angles = responses.get(trait, ("Hello friend.", ["HeadPitch"], [0.1]))
        
        print(f"🔊 Pepper: {text}")
        engine.say(text)
        engine.runAndWait()
        
        # تنفيذ الحركة السلوكية
        self.pepper.setAngles(joints, angles, 0.1)
        time.sleep(2)

    def run_session(self):
        print("🎯 Autism Therapy Session in Progress...")
        try:
            while True:
                # ترتيب عشوائي لضمان عدم التكرار الممل (Generalization)
                random.shuffle(self.kids_ids)
                
                for k_id, data in self.kids_ids:
                    k_pos, _ = p.getBasePositionAndOrientation(k_id)
                    p_pos = self.pepper.getPosition()
                    dx, dy = k_pos[0] - p_pos[0], k_pos[1] - p_pos[1]
                    
                    # الاقتراب ببطء (Predictable Movement)
                    angle = math.atan2(dy, dx)
                    self.pepper.moveTo(0, 0, angle, _async=False)
                    self.pepper.moveTo(max(0, math.sqrt(dx**2 + dy**2) - 0.85), 0, 0, _async=False)
                    
                    # التفاعل
                    self.execute_aba_protocol(data['trait'])
                    
                    # تعزيز نهائي (Social Reinforcement)
                    time.sleep(3)
                    self.pepper.moveTo(-0.5, 0, 0, _async=False)

        except KeyboardInterrupt:
            self.sim_manager.stopSimulation(self.client)

if __name__ == "__main__":
    bot = AutismTherapyBot()
    bot.run_session()
