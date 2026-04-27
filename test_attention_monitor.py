#!/usr/bin/env python3
"""اختبار Attention Monitoring - مراقبة الانتباه"""
import cv2
import mediapipe as mp

print("🔬 Testing Attention Monitoring System")
print("="*50)

mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(static_image_mode=False, max_num_faces=1, refine_landmarks=True)

cap = cv2.VideoCapture(0)
print("🎥 Camera opened. Look at the camera to test attention tracking!")

attention_history = []
gaze_direction = "center"

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb)
    
    if results.multi_face_landmarks:
        face = results.multi_face_landmarks[0]
        left_eye = face.landmark[159]
        right_eye = face.landmark[386]
        gaze_x = (left_eye.x + right_eye.x) / 2
        
        if gaze_x < 0.4:
            gaze_direction = "LEFT"
            attention = 40
        elif gaze_x > 0.6:
            gaze_direction = "RIGHT"
            attention = 40
        else:
            gaze_direction = "CENTER"
            attention = 80
        
        attention_history.append(attention)
        avg_attention = sum(attention_history[-30:]) / min(30, len(attention_history))
        
        cv2.putText(frame, f"Gaze: {gaze_direction}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, f"Attention: {attention}%", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, f"Avg Attention: {avg_attention:.0f}%", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        if attention < 50:
            cv2.putText(frame, "⚠️ Low attention - redirecting focus", (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
    else:
        cv2.putText(frame, "No face detected", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    
    cv2.imshow("Attention Monitor", frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
print(f"✅ Test complete! Average attention: {sum(attention_history)/len(attention_history):.0f}%")
