#!/usr/bin/env python3
"""اختبار SPARK - Early Autism Detection"""
import cv2
import mediapipe as mp

print("🔬 Testing SPARK Early Detection System")
print("="*50)

mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(static_image_mode=False, max_num_faces=1, refine_landmarks=True)

cap = cv2.VideoCapture(0)
eye_contact_count = 0
social_smile_count = 0

print("🎥 Camera opened. Look at the camera for eye contact detection...")

for _ in range(100):
    ret, frame = cap.read()
    if not ret:
        continue
    
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb)
    
    if results.multi_face_landmarks:
        face = results.multi_face_landmarks[0]
        # Check eye contact
        left_eye = face.landmark[159]
        right_eye = face.landmark[386]
        gaze_x = (left_eye.x + right_eye.x) / 2
        if 0.4 < gaze_x < 0.6:
            eye_contact_count += 1
            cv2.putText(frame, "✅ Eye Contact!", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        else:
            cv2.putText(frame, "⚠️ Looking away", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        # Check smile (mouth landmarks)
        mouth_top = face.landmark[13].y
        mouth_bottom = face.landmark[14].y
        if mouth_bottom - mouth_top > 0.03:
            social_smile_count += 1
            cv2.putText(frame, "😊 Smile detected!", (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    
    cv2.putText(frame, f"Eye Contact: {eye_contact_count}", (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    cv2.imshow("SPARK Detection Test", frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
print(f"✅ Test complete! Eye contact: {eye_contact_count}, Smiles: {social_smile_count}")
if eye_contact_count < 30:
    print("⚠️ Low eye contact detected - consider monitoring")
else:
    print("✅ Normal eye contact pattern")
