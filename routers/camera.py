from flask import (
    Blueprint,
    Response,
    jsonify
)

import cv2

camera = Blueprint('camera', __name__, url_prefix="/camera/")
camera.config["CAMERA_STATUS"] = "LOADING"

def camera_stream(camera=None):
    while True:
        ret, frame = camera.read()
        if not ret:
            camera.config["CAMERA_STATUS"] = "UNABLE TO LOAD THE CAMERA"
            break
        
        camera.config["CAMERA_STATUS"] = "ONLINE"
        
        frame = cv2.flip(frame,1)
        
        _, frame_encoded  = cv2.imencode('.png', frame)
        yield (b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + frame_encoded.tobytes() + b'\r\n')
                
@camera.route('/stream')
def stream():

    camera = cv2.VideoCapture(0)
    camera.config["CAMERA_STATUS"] = "LOADING"
    return Response(camera_stream(camera=camera), mimetype='multipart/x-mixed-replace; boundary=frame')


@camera.route('/status', methods=["GET"])
def status():    
    return jsonify({"status": camera.config["CAMERA_STATUS"]}), 200