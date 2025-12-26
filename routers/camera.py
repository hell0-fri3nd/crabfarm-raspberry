from flask import (
    Blueprint,
    Response,
    jsonify
)
from ultralytics import YOLO
from pyzbar.pyzbar import decode
import cv2


# 20 cm distance from the object to the camera
camera = Blueprint('camera', __name__, url_prefix="/camera/")

model = YOLO("models/yolov8n.pt")

def __box_area(cv2,frame,data,box, rgb):
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

def __camera_stream(camera=None):
    while True:
        ret, frame = camera.read()
        if not ret:
            break
        
        frame = cv2.flip(frame,1)
        annotated = frame.copy()
        
        results = model(frame, imgsz=320, conf=0.4)
        cm_per_pixel = 1 / 37.795275591 
        decoded_objects = decode(annotated)
        
        for box in results[0].boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            width = x2 - x1
            height = y2 - y1

            real_width = width * cm_per_pixel
            real_height = height * cm_per_pixel

            __box_area(cv2, annotated, f"W:{real_width:.2f}cm H:{real_height:.2f}cm", (int(x1), int(y1), int(x2), int(y2)), (0, 255, 0))
        
        for obj in decoded_objects:
            (x, y, w, h) = obj.rect
            __box_area(cv2, annotated, obj.data.decode('utf-8'), (x, y, x+ w, y + h), (255, 0, 0))
            
        

        _, frame_encoded  = cv2.imencode('.png', annotated)
        yield (b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + frame_encoded.tobytes() + b'\r\n')
                
@camera.route('/stream')
def stream():
    camera_stream = cv2.VideoCapture(0)
    return Response(__camera_stream(camera=camera_stream), mimetype='multipart/x-mixed-replace; boundary=frame')


@camera.route('/status', methods=["GET"])
def status():    
    return jsonify({"status": camera.config["CAMERA_STATUS"]}), 200