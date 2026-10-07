# lib import
import cv2

# configuration
from config import CAMERA_DEVICE, FRAME_HEIGHT, FRAME_WIDTH, CAMERA_FPS, PIXEL_FORMAT

# core logic
class Camera:
    def __init__(self):
        self.cap=None

    # Open cam
    def open(self):
        self.cap=cv2.VideoCapture(
            CAMERA_DEVICE, cv2.CAP_V4L2
            )


        if not self.cap.isOpened():
            raise RuntimeError(f"Unable to Open camera {CAMERA_DEVICE}")

        self.cap.set(
            cv2.CAP_PROP_FOURCC,
            cv2.VideoWriter_fourcc(*PIXEL_FORMAT)
        )

        self.cap.set(
            cv2.CAP_PROP_FRAME_HEIGHT,
            FRAME_HEIGHT
        )
        self.cap.set(
            cv2.CAP_PROP_FRAME_WIDTH,
            FRAME_WIDTH
        )

        self.cap.set(
            cv2.CAP_PROP_FPS,
            CAMERA_FPS
        )

    # Read frame
    def read(self):
        if self.cap is None:
            raise RuntimeError("Camera is not open")


        ret, frame = self.cap.read()  # return status, frame- actual image

        if not ret:
            return None

        return frame


    # Dimension of frame
    def get_width(self):
        return int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))

    def get_height(self):
        return int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    def get_fps(self):
        return int(self.cap.get(cv2.CAP_PROP_FPS))

    # Release
    def release(self):
        if self.cap is not None:
            self.cap.release()
            self.cap=None
