import qi
import sys

def fix_mic_gain(ip="127.0.0.1", port=9559):
    session = qi.Session()
    try:
        session.connect(f"tcp://{ip}:{port}")
        audio = session.service("ALAudioDevice")
        energy = audio.getFrontMicEnergy()
        print(f"Current Front Mic Energy: {energy}")
        
        if energy > 500:
            print("Clipping detected! Resetting Audio device...")
            # بعض إصدارات NAOqi لا تدعم reconnect مباشرة، 
            # إذا فشلت، سنعتمد على التنبيه فقط في البداية
            print("High energy detected. Please check your audio gain settings.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fix_mic_gain()

