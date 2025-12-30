import cv2
import threading
import cv2

from ultralytics import YOLO
from pyzbar.pyzbar import decode


class VideoStream:
    def __init__(self):
        self.camera = cv2.VideoCapture(0)
        if not self.camera.isOpened():
            raise RuntimeError("Camera not accessible")
        
        self.model = YOLO("models/yolov8n.pt")
        
        self.latest_frame    = None
        self.processed_frame = None
        self.stopped         = True
        self.lock            = threading.Lock()
        
        self.real_width      = 0
        self.real_height     = 0
        self.extracted_data  = ""
    
    def __box_area(self,frame,data,box, rgb):
        x, y, w, h = box
        cv2.rectangle(frame, (x, y), (w,h),rgb, 2)
        label = f"{data}"
        cv2.putText(
            frame,                    # image
            label,                    # text
            (int(x), int(y) - 10),    # position (slightly above box)
            cv2.FONT_HERSHEY_SIMPLEX, # font
            0.5,                      # font scale
            rgb,                      # color (green)
            2                         # thickness
        )
        
        self.latest_frame = frame
        
    def __run_detections(self):
        
        while not self.stopped:
            
            if self.latest_frame is None:
                continue
            
            results = self.model.predict(self.latest_frame, imgsz=320, conf=0.4, verbose=False)
            cm_per_pixel = 1 / 37.795275591 
            decoded_objects = decode(self.latest_frame)
            
            for box in results[0].boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                width  = x2 - x1
                height = y2 - y1

                self.real_width  = width * cm_per_pixel
                self.real_height = height * cm_per_pixel

                self.__box_area(self.latest_frame, "", (int(x1), int(y1), int(x2), int(y2)), (0, 255, 0))
            
                for obj in decoded_objects:
                    if (obj.data.decode('utf-8') is not None):
                        (x, y, w, h) = obj.rect
                        self.__box_area(self.latest_frame, obj.data.decode('utf-8'), (x, y, x+ w, y + h), (255, 0, 0))
                        self.stopped  = True
                        self.processed_frame = self.latest_frame
                        
                        self.extracted_data = obj.data.decode('utf-8')
                    
    def __capture_frames(self):
        while not self.stopped:
            ret, frame = self.camera.read()
            if ret:
                frame = cv2.flip(frame, 1)
                with self.lock:
                    self.latest_frame = frame     
    
    def start(self):
        
        try:
            if not self.camera.isOpened():
                self.camera = cv2.VideoCapture(0)

            if self.stopped:
                self.stopped = False
                threading.Thread(target=self.__capture_frames, daemon=True).start()
                threading.Thread(target=self.__run_detections, daemon=True).start()
            
            return self.camera.isOpened()
        except:
            return False

          
    def status(self):
        data = {
            "camera_status":  self.camera.isOpened(),
            "width_cm":       self.real_width,
            "height_cm":      self.real_height,
            "extracted_data": self.extracted_data
        }

        return data
    
    def streaming(self):
        while not self.stopped:
            if self.latest_frame is None:
                continue
            with self.lock:
                frame = self.latest_frame.copy()
                
            ret, buffer = cv2.imencode('.png', frame)
                
            if not ret:
                continue
            
            yield (b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        
        self.camera.release() 
        frame = self.processed_frame.copy()
        ret, buffer = cv2.imencode('.png', frame)
        if ret:
            yield (b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            
