import pybullet as p
import pybullet_data
import time
import math
import requests
import pyttsx3
import threading

# إعداد محرك الصوت
engine = pyttsx3.init()
def speak(text):
    def _speak():
        engine.say(text)
        engine.runAndWait()
    threading.Thread(target=_speak).start()

def run_ai_pepper():
    p.connect(p.GUI)
    p.setAdditionalSearchPath(pybullet_data.getDataPath())
    p.setGravity(0, 0, -9.8)
    p.loadURDF("plane.urdf")
    # تحميل بيبر (أو R2D2 كبديل)
    robot_id = p.loadURDF("r2d2.urdf", [0, 0, 0.5])
    
    # البالونة
    ballon_visual = p.createVisualShape(p.GEOM_SPHERE, radius=0.2, rgbaColor=[1, 0, 0, 1])
    ballon_id = p.createMultiBody(baseMass=0, baseVisualShapeIndex=ballon_visual, basePosition=[2, 2, 1])

    speak("مرحباً لميا، أنا بيبر. أنا أراكِ الآن وسأطارد البالونة معكِ!")

    t = 0
    last_voice_time = time.time()

    while True:
        p.stepSimulation()
        
        # حركة البالونة
        target_x, target_y = 2 * math.cos(t), 2 * math.sin(t)
        p.resetBasePositionAndOrientation(ballon_id, [target_x, target_y, 1], [0,0,0,1])
        
        # حركة الروبوت
        pos, _ = p.getBasePositionAndOrientation(robot_id)
        p.resetBasePositionAndOrientation(robot_id, [pos[0]+(target_x-pos[0])*0.01, pos[1]+(target_y-pos[1])*0.01, 0.5], [0,0,0,1])

        # الربط مع الكاميرا والسيرفر (الذكاء الاصطناعي)
        if time.time() - last_voice_time > 5:  # كل 5 ثوانٍ يحلل الحالة
            try:
                # جلب آخر شعور من السيرفر
                response = requests.get('http://localhost:5009/report', timeout=0.1).json()
                last_log = response['full_report'][-1] if response['full_report'] else ""
                
                if "happy" in last_log.lower():
                    speak("أنا سعيد لأنكِ سعيدة! انظري كيف أطارد البالونة!")
                elif "sad" in last_log.lower():
                    speak("لا تحزني يا بطلة، دعينا نلعب بالبالونة معاً.")
                
                last_voice_time = time.time()
            except: pass

        t += 0.01
        time.sleep(1./240.)

if __name__ == "__main__":
    run_ai_pepper()
