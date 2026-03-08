import cv2
import threading
import time
from ultralytics import YOLO
from pyzbar.pyzbar import decode

class VideoStream:
    def __init__(self):
        # Find the camera first
        self.camera_loc = self.find_camera()
        print(f"[INFO] Using camera at index: {self.camera_loc}")
        
        # Force V4L2 backend for better compatibility on Pi
        self.camera = cv2.VideoCapture(self.camera_loc, cv2.CAP_V4L2)
        
        # Give camera time to initialize
        time.sleep(1)
        
        # Set to 1080p
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        self.camera.set(cv2.CAP_PROP_FPS, 30)
        self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        # Try MJPEG format for better performance
        self.camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
        
        # Verify resolution
        time.sleep(0.5)
        actual_width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
        print(f"[INFO] Camera resolution: {actual_width}x{actual_height}")
        
        if not self.camera.isOpened() or actual_width == 0:
            print("[WARN] Failed with V4L2 backend, trying default...")
            self.camera.release()
            time.sleep(1)
            self.camera = cv2.VideoCapture(self.camera_loc)
            time.sleep(1)
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
            actual_width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
            print(f"[INFO] Camera resolution: {actual_width}x{actual_height}")
        
        if not self.camera.isOpened():
            raise RuntimeError("Camera not accessible")
        
        # Load YOLO model
        self.model = YOLO("models/yolov8s.pt")
        
        self.latest_frame = None
        self.processed_frame = None
        self.stopped = True
        self.lock = threading.Lock()
        
        self.real_width = 0
        self.real_height = 0
        self.extracted_data = ""
        
        # Performance optimization
        self.frame_count = 0
        self.process_every_n = 3  # Process every 3rd frame at 1080p
        self.last_fps_print = time.time()
        self.detection_size = 320  # YOLO input size
    
    def find_camera(self):
        """Find the first working camera"""
        # First try standard indices
        for i in range(5):
            cap = cv2.VideoCapture(i, cv2.CAP_V4L2)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None and frame.size > 0:
                    print(f"[INFO] Found working camera at index {i}")
                    cap.release()
                    return i
            cap.release()
        
        # Try without V4L2 backend
        for i in range(5):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None and frame.size > 0:
                    print(f"[INFO] Found working camera at index {i} (default backend)")
                    cap.release()
                    return i
            cap.release()
        
        # Default to 0 if nothing found
        print("[WARN] No camera found, defaulting to 0")
        return 0
    
    def __box_area(self, frame, data, box, rgb):
        """Draw bounding box and label on frame"""
        x, y, w, h = box
        cv2.rectangle(frame, (x, y), (w, h), rgb, 2)
        
        # Adjust font size based on resolution
        font_scale = 0.7 if frame.shape[1] > 1280 else 0.5
        
        cv2.putText(
            frame,
            str(data),
            (int(x), int(y) - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            rgb,
            2
        )
        return frame
        
    def __run_detections(self):
        """Main detection loop - optimized for 1080p on Pi"""
        print("[INFO] Detection thread started")
        
        while not self.stopped:
            # Get a frame to process
            with self.lock:
                if self.latest_frame is None:
                    time.sleep(0.01)
                    continue
                frame_to_process = self.latest_frame.copy()
            
            # Frame skipping for performance
            self.frame_count += 1
            if self.frame_count % self.process_every_n != 0:
                # Skip processing this frame, just pass through
                with self.lock:
                    self.processed_frame = frame_to_process.copy()
                continue
            
            # Process frame with YOLO
            try:
                results = self.model.predict(
                    frame_to_process, 
                    imgsz=self.detection_size,
                    conf=0.4, 
                    verbose=False,
                    device='cpu'  # Explicitly use CPU
                )
            except Exception as e:
                print(f"[ERROR] YOLO prediction failed: {e}")
                time.sleep(0.1)
                continue
            
            cm_per_pixel = 1 / 37.795275591 
            
            # Decode QR codes/barcodes
            try:
                decoded_objects = decode(frame_to_process)
            except Exception as e:
                print(f"[ERROR] QR decode failed: {e}")
                decoded_objects = []
            
            # Process YOLO detections
            for box in results[0].boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                width = x2 - x1
                height = y2 - y1

                self.real_width = width * cm_per_pixel
                self.real_height = height * cm_per_pixel

                frame_to_process = self.__box_area(
                    frame_to_process, 
                    "", 
                    (int(x1), int(y1), int(x2), int(y2)), 
                    (0, 255, 0)
                )
            
            # Process QR codes
            for obj in decoded_objects:
                if obj.data and obj.data.decode('utf-8') is not None:
                    (x, y, w, h) = obj.rect
                    frame_to_process = self.__box_area(
                        frame_to_process, 
                        obj.data.decode('utf-8'), 
                        (x, y, x + w, y + h), 
                        (255, 0, 0)
                    )
                    
                    # Save QR code data
                    self.extracted_data = obj.data.decode('utf-8')
                    print(f"[INFO] QR Code detected: {self.extracted_data}")
                    
                    # Save the frame with QR code
                    self.processed_frame = frame_to_process.copy()
            
            # Update the processed frame for display
            with self.lock:
                self.processed_frame = frame_to_process.copy()
            
            # Print FPS occasionally
            if self.frame_count % 30 == 0:
                fps = 30 / (time.time() - self.last_fps_print)
                print(f"[INFO] Processing at {fps:.1f} fps")
                self.last_fps_print = time.time()
    
    def __capture_frames(self):
        """Frame capture thread with error recovery"""
        print("[INFO] Capture thread started")
        failures = 0
        max_failures = 5
        
        while not self.stopped:
            try:
                ret, frame = self.camera.read()
                if ret:
                    failures = 0
                    frame = cv2.flip(frame, 1)
                    with self.lock:
                        self.latest_frame = frame
                else:
                    failures += 1
                    print(f"[WARNING] Frame capture failed ({failures}/{max_failures})")
                    if failures >= max_failures:
                        print("[ERROR] Camera disconnected, attempting to reconnect...")
                        self.camera.release()
                        time.sleep(1)
                        self.camera = cv2.VideoCapture(self.camera_loc)
                        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
                        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
                        failures = 0
                    time.sleep(0.1)
            except Exception as e:
                print(f"[ERROR] Capture exception: {e}")
                time.sleep(0.1)
    
    def start(self):
        """Start the video stream"""
        try:
            if not self.camera.isOpened():
                print("[INFO] Re-opening camera...")
                self.camera = cv2.VideoCapture(self.camera_loc)
                self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
                self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

            if self.stopped:
                self.stopped = False
                print("[INFO] Starting capture thread...")
                threading.Thread(target=self.__capture_frames, daemon=True).start()
                print("[INFO] Starting detection thread...")
                threading.Thread(target=self.__run_detections, daemon=True).start()
                print("[INFO] Camera started successfully at 1080p")
            
            return self.camera.isOpened()
        except Exception as e:
            print(f"[ERROR] Start failed: {e}")
            return False

    def status(self):
        """Get current status"""
        with self.lock:
            data = {
                "camera_status": self.camera.isOpened(),
                "width_cm": self.real_width,
                "height_cm": self.real_height,
                "extracted_data": self.extracted_data,
                "is_running": not self.stopped,
                "resolution": f"{int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))}"
            }
        return data
    
    def streaming(self):
        """Generate streaming frames for Flask"""
        while not self.stopped:
            # Get the latest frame
            with self.lock:
                if self.processed_frame is not None:
                    frame = self.processed_frame.copy()
                elif self.latest_frame is not None:
                    frame = self.latest_frame.copy()
                else:
                    time.sleep(0.01)
                    continue
            
            # Use JPEG compression for faster streaming
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                
            if not ret:
                continue
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        
        print("[INFO] Streaming ended, releasing camera...")
        self.camera.release()
        
        # Send final frame if available
        if self.processed_frame is not None:
            ret, buffer = cv2.imencode('.jpg', self.processed_frame, 
                                     [cv2.IMWRITE_JPEG_QUALITY, 80])
            if ret:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
    
    def stop(self):
        """Gracefully stop the camera"""
        print("[INFO] Stopping camera...")
        self.stopped = True
        time.sleep(0.5)  # Give threads time to stop
        if self.camera.isOpened():
            self.camera.release()
        print("[INFO] Camera stopped")


# Test the class if run directly
if __name__ == "__main__":
    print("=" * 50)
    print("RASPBERRY PI CAMERA TEST (1080p MODE)")
    print("=" * 50)
    
    # Create and start camera
    camera = VideoStream()
    
    if camera.start():
        print("\n Camera started! Running for 15 seconds...\n")
        
        try:
            start_time = time.time()
            while time.time() - start_time < 15:
                status = camera.status()
                print(f"Status: {status}")
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n Stopped by user")
        finally:
            camera.stop()
            print("\n Test complete")
    else:
        print("âŒ Failed to start camera!")
