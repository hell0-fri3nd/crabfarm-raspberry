from flask import (
    Blueprint,
    Response,
    jsonify
)
from ultralytics import YOLO
import cv2


# 20 cm distance from the object to the camera
camera = Blueprint('camera', __name__, url_prefix="/camera/")

model = YOLO("models/yolov8s.pt")

def camera_stream(camera=None):
    while True:
        ret, frame = camera.read()
        if not ret:
            break
        
        frame = cv2.flip(frame,1)
        results = model(frame, imgsz=320, conf=0.4)
        
        annotated = frame.copy()
        cm_per_pixel = 1 / 37.795275591 
        for box in results[0].boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            width = x2 - x1
            height = y2 - y1

            real_width = width * cm_per_pixel
            real_height = height * cm_per_pixel

            cv2.rectangle(annotated, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)

            label = f"W:{real_width:.2f}cm H:{real_height:.2f}cm"
            cv2.putText(
                annotated,                # image
                label,                    # text
                (int(x1), int(y1) - 10),  # position (slightly above box)
                cv2.FONT_HERSHEY_SIMPLEX, # font
                0.5,                      # font scale
                (0, 255, 0),              # color (green)
                2                         # thickness
            )

        _, frame_encoded  = cv2.imencode('.png', annotated)
        yield (b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + frame_encoded.tobytes() + b'\r\n')
                
@camera.route('/stream')
def stream():
    camera = cv2.VideoCapture(0)
    return Response(camera_stream(camera=camera), mimetype='multipart/x-mixed-replace; boundary=frame')


@camera.route('/status', methods=["GET"])
def status():    
    return jsonify({"status": camera.config["CAMERA_STATUS"]}), 200