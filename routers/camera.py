from flask import (
    Blueprint,
    Response,
    jsonify
)
from view import VideoStream
from services import JWTManager

# 20 cm distance from the object to the camera
camera = Blueprint('camera', __name__, url_prefix="/camera/")
vs = VideoStream()
jwt_manager = JWTManager()

@camera.route('/stream')
def stream():
    return Response(vs.streaming(), mimetype='multipart/x-mixed-replace; boundary=frame')

@camera.route('/status', methods=["GET"])
@jwt_manager.requires_access
def status():    
    return jsonify(vs.status()), 200

@camera.route('/start', methods=["PUT"])
@jwt_manager.requires_access
def start():    
    result = vs.start()
    return jsonify({"status": "Camera started" if result else "Camera not started"}), 200 if result else 500