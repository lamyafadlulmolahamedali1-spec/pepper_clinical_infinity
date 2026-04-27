import os
import cv2
import shared_state
from deepface import DeepFace

os.environ['TF_USE_LEGACY_KERAS'] = '1'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['CUDA_VISIBLE_DEVICES'] = ''

def find_working_camera():
    for i in [1, 0, 2]: # Try 1 first, then 0, then 2
        print(f"🔍 Testing Camera Index {i}...")
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            ret, _ = cap.read()
            if ret:
                print(f"✅ Success! Using Camera {i}")
                return cap
            cap.release()
    return None

def vision_loop():
    cap = find_working_camera()
    if not cap:
        print("❌ CRITICAL: No working camera found at index 0, 1, or 2.")
        return

    while True:
        ret, frame = cap.read()
        if not ret: break
        
        try:
            results = DeepFace.analyze(frame, actions=['emotion'], enforce_detection=False, detector_backend='opencv', silent=True)
            if results:
                raw = results[0]['emotion']
                # Calculate the 9th emotions (Anxiety/Confusion)
                raw['confusion'] = (raw['neutral'] * 0.4) + (raw['surprise'] * 0.6)
                raw['anxiety'] = (raw['fear'] * 0.7) + (raw['sad'] * 0.3)
                dom = max(raw, key=raw.get)
                
                shared_state.set_emotion(dom, raw[dom]/100, raw)
                cv2.putText(frame, f"9-EMO: {dom}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        except: pass

        cv2.imshow("DeepFace 9-Emotion Vision", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    vision_loop()
