import cv2

class CameraHandler:
    def __init__(self, use_real_camera=True, camera_id=0):
        self.use_real = use_real_camera
        if self.use_real:
            self.cap = cv2.VideoCapture(camera_id)
            # التحقق من أن الكاميرا تعمل
            if not self.cap.isOpened():
                print("⚠️ Warning: Could not open camera, using dummy mode")
                self.use_real = False
                self.cap = None
        else:
            self.cap = None

    def get_frame(self):
        if self.use_real and self.cap:
            ret, frame = self.cap.read()
            if ret:
                return frame
            else:
                print("⚠️ Failed to capture frame")
                return None
        else:
            # إنشاء صورة افتراضية للاختبار
            dummy_frame = cv2.imread('/app/src/vision/dummy.jpg')
            if dummy_frame is not None:
                return dummy_frame
            else:
                # إنشاء صورة سوداء كبديل
                return cv2.imread('/app/src/vision/dummy.jpg')
                # إنشاء صورة سوداء كبديل
                return np.zeros((480, 640, 3), dtype=np.uint8)
