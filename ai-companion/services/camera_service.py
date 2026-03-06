import cv2
import time

class CameraService:
    def __init__(self, camera_index=0):
        self.camera_index = camera_index
        self.cap = None

    def start(self):
        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            print(f"Error: Could not open camera {self.camera_index}")
            return False
        return True

    def get_frame(self):
        if not self.cap:
            return None
        ret, frame = self.cap.read()
        if not ret:
            print("Error: Could not read frame")
            return None
        return frame

    def stop(self):
        if self.cap:
            self.cap.release()
            print("Camera released.")

if __name__ == "__main__":
    cam = CameraService()
    if cam.start():
        print("Camera started. Capturing 1 frame...")
        frame = cam.get_frame()
        if frame is not None:
            cv2.imwrite("data/test_capture.jpg", frame)
            print("Captured data/test_capture.jpg")
        cam.stop()
