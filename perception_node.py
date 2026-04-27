#!/usr/bin/env python3

import rospy
from std_msgs.msg import String
import cv2
from ultralytics import YOLO
from deepface import DeepFace
import time

class PerceptionNode:
    def __init__(self):
        rospy.init_node('perception_node', anonymous=True)
        
        self.emotion_pub = rospy.Publisher('/child/emotion', String, queue_size=10)
        self.objects_pub = rospy.Publisher('/child/objects', String, queue_size=10)
        self.face_pub = rospy.Publisher('/child/face_detected', String, queue_size=10)
        
        self.cap = None
        for camera_id in [0, 1, 2]:
            self.cap = cv2.VideoCapture(camera_id)
            if self.cap.isOpened():
                rospy.loginfo(f"✅ تم فتح الكاميرا رقم {camera_id}")
                break
        
        if not self.cap or not self.cap.isOpened():
            rospy.logerr("❌ فشل في فتح أي كاميرا")
            return
        
        rospy.loginfo("📥 جاري تحميل نموذج YOLO...")
        self.yolo_model = YOLO('yolov8n.pt')
        rospy.loginfo("✅ تم تحميل YOLO بنجاح")
        
        self.rate = rospy.Rate(2)
        rospy.loginfo("🚀 Perception Node جاهز للعمل")
    
    def detect_emotion(self, face_img):
        try:
            temp_path = '/tmp/temp_face.jpg'
            cv2.imwrite(temp_path, face_img)
            
            result = DeepFace.analyze(
                img_path=temp_path,
                actions=['emotion'],
                enforce_detection=False,
                silent=True
            )
            
            if result and len(result) > 0:
                return result[0]['dominant_emotion']
        except Exception as e:
            rospy.logdebug(f"خطأ في كشف المشاعر: {e}")
        return None
    
    def run(self):
        while not rospy.is_shutdown():
            ret, frame = self.cap.read()
            if not ret:
                rospy.logwarn("⚠️ لم أستطع قراءة الصورة من الكاميرا")
                continue
            
            results = self.yolo_model(frame)
            
            detected_objects = []
            face_detected = False
            
            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes:
                        x1, y1, x2, y2 = box.xyxy[0].tolist()
                        conf = float(box.conf[0])
                        cls = int(box.cls[0])
                        label = self.yolo_model.names[cls]
                        
                        if conf > 0.5:
                            detected_objects.append(label)
                            
                            if label == 'person':
                                face_detected = True
                                
                                face_img = frame[int(y1):int(y2), int(x1):int(x2)]
                                if face_img.size > 0:
                                    emotion = self.detect_emotion(face_img)
                                    if emotion:
                                        rospy.loginfo(f"😊 المشاعر المكتشفة: {emotion}")
                                        self.emotion_pub.publish(String(emotion))
                            
                            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                            cv2.putText(frame, f"{label} {conf:.2f}", (int(x1), int(y1)-10),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            if detected_objects:
                objects_str = ','.join(list(set(detected_objects)))
                self.objects_pub.publish(String(objects_str))
                rospy.loginfo(f"📦 الأشياء المكتشفة: {objects_str}")
            
            if face_detected:
                self.face_pub.publish(String("yes"))
            
            cv2.imshow('NAO Robot Camera', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            
            self.rate.sleep()
        
        self.cap.release()
        cv2.destroyAllWindows()

if __name__ == '__main__':
    try:
        node = PerceptionNode()
        node.run()
    except rospy.ROSInterruptException:
        pass
    except Exception as e:
        rospy.logerr(f"❌ خطأ غير متوقع: {e}")
