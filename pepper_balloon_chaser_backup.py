import pybullet as p
import pybullet_data
import time
import math
import requests
import pyttsx3
import threading
import sys

# إعداد محرك الصوت لجهاز ASUS TUF
engine = pyttsx3.init()
def speak(text):
    def _speak():
        engine.say(text)
        engine.runAndWait()
    threading.Thread(target=_speak).start()

def run_ballon_chaser():
    p.connect(p.GUI)
    p.setAdditionalSearchPath(pybullet_data.getDataPath())
    p.setGravity(0, 0, -9.8)
    p.loadURDF("plane.urdf")
    
    # تحميل الروبوت (Pepper/R2D2)
    robot_id = p.loadURDF("r2d2.urdf", [0, 0, 0.5])
    
    # إنشاء البالونة
    ballon_visual = p.createVisualShape(p.GEOM_SPHERE, radius=0.2, rgbaColor=[1, 0, 0, 1])
    ballon_id = p.createMultiBody(baseMass=0, baseVisualShapeIndex=ballon_visual, basePosition=[2, 2, 1])

    print("🎈 نظام مطاردة البالونات والذكاء الاصطناعي نشط!")
    speak("أهلاً بك، أنا بيبر. لنلعب معاً ونطارد البالونة!")

    t = 0
    last_check_time = time.time()

    try:
        while True:
            p.stepSimulation()
            
            # حركة البالونة الدائرية
            target_x = 2 * math.cos(t)
            target_y = 2 * math.sin(t)
            p.resetBasePositionAndOrientation(ballon_id, [target_x, target_y, 1], [0,0,0,1])
            
            # حركة الروبوت نحو الهدف
            pos, _ = p.getBasePositionAndOrientation(robot_id)
            p.resetBasePositionAndOrientation(robot_id, [pos[0]+(target_x-pos[0])*0.01, pos[1]+(target_y-pos[1])*0.01, 0.5], [0,0,0,1])

            # --- التفاعل الذكي (AI Integration) ---
            if time.time() - last_check_time > 3:  # فحص المشاعر كل 3 ثوانٍ
                try:
                    # جلب المشاعر من السيرفر (الذي تغذيه الكاميرا)
                    r = requests.get('http://localhost:5009/report', timeout=0.1).json()
                    if r['full_report']:
                        last_emo = r['full_report'][-1].lower()
                        if "happy" in last_emo:
                            speak("أنا أراك مبتسماً! هذا رائع، سأسرع أكثر!")
                        elif "sad" in last_emo:
                            speak("لا تحزن، أنا هنا لألعب معك. انظر للبالونة!")
                except:
                    pass
                last_check_time = time.time()

            t += 0.01
            time.sleep(1./240.)
    except KeyboardInterrupt:
        p.disconnect()

if __name__ == "__main__":
    run_ballon_chaser()
