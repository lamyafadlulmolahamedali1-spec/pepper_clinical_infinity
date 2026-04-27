#!/usr/bin/env python3
"""اختبار MediaPipe - Face and Pose Detection"""
import cv2
import mediapipe as mp

print("🔬 Testing MediaPipe Detection")
print("="*50)

mp_face_mesh = mp.solutions.face_mesh
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

face_mesh = mp_face_mesh.FaceMesh(static_image_mode=False, max_num_faces=1, refine_landmarks=True)
pose = mp_pose.Pose()

cap = cv2.VideoCapture(0)
print("🎥 Camera opened. Detecting face landmarks and pose...")

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # Face detection
    face_results = face_mesh.process(rgb)
    if face_results.multi_face_landmarks:
        for landmarks in face_results.multi_face_landmarks:
            mp_drawing.draw_landmarks(frame, landmarks, mp_face_mesh.FACEMESH_CONTOURS)
            cv2.putText(frame, "Face Landmarks Detected", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    
    # Pose detection
    pose_results = pose.process(rgb)
    if pose_results.pose_landmarks:
        mp_drawing.draw_landmarks(frame, pose_results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
        cv2.putText(frame, "Pose Detected", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    
    cv2.imshow("MediaPipe Detection", frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
print("✅ Test complete!")
