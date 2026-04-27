import os
# Force Keras compatibility and suppress noise
os.environ['TF_USE_LEGACY_KERAS'] = '1'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['CUDA_VISIBLE_DEVICES'] = '' # Run on CPU for stability first

from deepface import DeepFace
import cv2
import time

def analyze_face():
    # Use index 2 as index 0 failed on your system
    CAMERA_INDEX = 1
    cap = cv2.VideoCapture(CAMERA_INDEX)
    
    if not cap.isOpened():
        print(f"❌ Still cannot open camera at index {CAMERA_INDEX}")
        return

    print(f"📸 Camera {CAMERA_INDEX} active! Taking picture in 2s...")
    time.sleep(2)
    
    ret, frame = cap.read()
    cap.release()

    if ret:
        try:
            print("🧠 DeepFace is thinking...")
            # Using 'opencv' backend for the first quick test
            results = DeepFace.analyze(frame, 
                                       actions=['emotion'], 
                                       enforce_detection=False,
                                       detector_backend='opencv')
            
            emotion_data = results[0]['emotion']
            dominant = results[0]['dominant_emotion']
            
            print(f"\n✅ SUCCESS!")
            print(f"Main Emotion: {dominant.upper()}")
            print("📊 Full Spectrum:")
            for emo, score in emotion_data.items():
                print(f"  - {emo}: {score:.2f}%")
                
        except Exception as e:
            print(f"❌ Analysis Error: {e}")
    else:
        print("❌ Failed to capture frame from camera.")

if __name__ == "__main__":
    analyze_face()
