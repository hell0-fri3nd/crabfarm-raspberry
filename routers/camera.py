from flask import (
    Blueprint,
    Response,
    jsonify,
    current_app
)

camera = Blueprint('camera', __name__, url_prefix="/camera")

@camera.route('/stream')
def stream():
    vs = current_app.config['get_camera']()
    
    if not vs:
        return "Camera not available", 503
    
    return Response(vs.streaming(), mimetype='multipart/x-mixed-replace; boundary=frame')

@camera.route('/status', methods=["GET"])
def status():    
    vs = current_app.config['get_camera']()
    
    if not vs:
        return jsonify({"error": "Camera not initialized", "camera_status": False}), 503
    
    return jsonify(vs.status()), 200

@camera.route('/start', methods=["PUT"])
def start():    
    vs = current_app.config['get_camera']()
    
    if not vs:
        return jsonify({"status": "Camera not available"}), 503
    
    result = vs.start()
    return jsonify({"status": "Camera started" if result else "Camera not started"}), 200 if result else 500

@camera.route('/stop', methods=["PUT"])
def stop():
    vs = current_app.config['get_camera']()
    
    if not vs:
        return jsonify({"status": "Camera not available"}), 503
    
    vs.stop()
    return jsonify({"status": "Camera stopped"}), 200
