import cv2
import threading
from ultralytics import YOLO
from pyzbar.pyzbar import decode
import cv2
from time import sleep
class VideoStream:
    def __init__(self):
        self.camera = cv2.VideoCapture(0)
        if not self.camera.isOpened():
            raise RuntimeError("Camera not accessible"    )
        
        self.model = YOLO("models/yolov8n.pt")
        
        self.latest_frame    = None
        self.processed_frame = None
        self.stopped         = False
        self.lock            = threading.Lock()
        
        threading.Thread(target=self.__capture_frames, daemon=True).start()
        threading.Thread(target=self.__run_detections, daemon=True).start()
    
    def __box_area(self,frame,data,box, rgb):
        x, y, w, h = box
        cv2.rectangle(frame, (x, y), (w,h),rgb, 2)
        label = f"Data: {data}"
        cv2.putText(
            frame,                    # image
            label,                    # text
            (int(x), int(y) - 10),  # position (slightly above box)
            cv2.FONT_HERSHEY_SIMPLEX, # font
            0.5,                      # font scale
            rgb,            # color (green)
            2                         # thickness
        )
        
        self.latest_frame = frame
        
    def __run_detections(self):
        
        while not self.stopped:
      
            results = self.model.predict(self.latest_frame, imgsz=320, conf=0.4, verbose=False)
            cm_per_pixel = 1 / 37.795275591 
            decoded_objects = decode(self.latest_frame)
            
            for box in results[0].boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                width = x2 - x1
                height = y2 - y1

                real_width = width * cm_per_pixel
                real_height = height * cm_per_pixel

                self.__box_area(self.latest_frame, f"W:{real_width:.2f}cm H:{real_height:.2f}cm", (int(x1), int(y1), int(x2), int(y2)), (0, 255, 0))
            
            for obj in decoded_objects:
                (x, y, w, h) = obj.rect
                self.__box_area(self.latest_frame, obj.data.decode('utf-8'), (x, y, x+ w, y + h), (255, 0, 0))
                
                if (obj.data.decode('utf-8') is not None):
                    print(f"Decoded Data: {obj.data.decode('utf-8')}")
                    self.stopped  = True
                    self.processed_frame = self.latest_frame
                    
            
            # return annotated
    
    def __capture_frames(self):
        while not self.stopped:
            ret, frame = self.camera.read()
            if ret:
                frame = cv2.flip(frame, 1)
                with self.lock:
                    self.latest_frame = frame
                
    def streaming(self):
        while True:
            if self.latest_frame is None:
                continue
            with self.lock:
                frame = self.latest_frame.copy()
                
            ret, buffer = cv2.imencode('.png', frame)
            
            if self.stopped:
                frame = self.processed_frame
                self.camera.release()
                yield (b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                break
                
            if not ret:
                continue
            
            yield (b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

            
