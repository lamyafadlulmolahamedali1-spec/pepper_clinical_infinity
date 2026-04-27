from ultralytics import YOLO
import cv2

class YOLODetector:
    def __init__(self, model_path='yolov8n.pt'):
        self.model = YOLO(model_path)
        self.class_names = self.model.names

    def detect(self, image):
        results = self.model(image)[0]
        detections = []
        for box in results.boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            conf = box.conf[0].item()
            cls = int(box.cls[0].item())
            label = self.class_names[cls]
            detections.append((label, conf, (int(x1), int(y1), int(x2), int(y2))))
        return detections

    def draw_boxes(self, image, detections):
        for label, conf, (x1, y1, x2, y2) in detections:
            cv2.rectangle(image, (x1, y1), (x2, y2), (0,255,0), 2)
            cv2.putText(image, f"{label} {conf:.2f}", (x1, y1-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 2)
