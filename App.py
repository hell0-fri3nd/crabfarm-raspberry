from flask import ( Flask )
from flask_cors import CORS
from routers.camera import camera  # Import the blueprint directly
import os
import atexit

app = Flask(__name__)

# Configure CORS
CORS(app,
    supports_credentials=True,
    origins=[
        "http://localhost:7987",
        "http://192.168.100.11:7987",
        "http://192.168.100.11:4572/",
        "http://0.0.0.0:4572/"
    ]
)

# Global camera instance
camera_instance = None

def get_camera():
    """Get or create camera instance"""
    global camera_instance
    if camera_instance is None:
        try:
            from view import VideoStream
            print("[INFO] Initializing camera...")
            camera_instance = VideoStream()
            if camera_instance.start():
                print("[INFO] Camera started successfully")
            else:
                print("[ERROR] Failed to start camera")
                camera_instance = None
        except Exception as e:
            print(f"[ERROR] Camera initialization failed: {e}")
            camera_instance = None
    return camera_instance

# Make camera available to routes
app.config['get_camera'] = get_camera

# Register blueprint - just 'camera' not 'camera.camera'
app.register_blueprint(camera)

# Cleanup on exit
@atexit.register
def cleanup():
    global camera_instance
    if camera_instance:
        print("[INFO] Cleaning up camera...")
        camera_instance.stop()
        camera_instance = None

@app.route('/')
def index():
    return "Camera Server Running - Access /camera/stream for stream"

if __name__ == '__main__':
    print("=" * 50)
    print("RASPBERRY PI CAMERA SERVER")
    print("=" * 50)
    print("[INFO] Starting Flask server...")
    print("[INFO] Camera will initialize on first request")
    print(f"[INFO] Access the stream at: http://192.168.100.196:4573/camera/stream")
    print(f"[INFO] Check status at: http://192.168.100.196:4573/camera/status")
    print("=" * 50)
    
    # IMPORTANT: debug=False to prevent double processes
    app.run(
        host='0.0.0.0',        
        debug=True,           # Changed from True to False
        threaded=True,
        port=4573
    )
