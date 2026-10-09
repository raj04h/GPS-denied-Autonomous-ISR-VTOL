# Dependencies
import cv2


# Core Logic
class MOSSETracker:

    def __init__(self):

        self.tracker = None
        self.bbox = None
        self.initialized = False

    def initialize(self, frame, roi):

        if frame is None:

            raise ValueError("Cannot initialize tracker with empty frame.")

        if roi is None:

            raise ValueError("Cannot initialize tracker without ROI.")

        x, y, width, height = roi

        if width <= 0 or height <= 0:

            raise ValueError("ROI width and height must be greater than zero.")

        self.tracker = cv2.legacy.TrackerMOSSE_create()

        self.tracker.init(frame, (float(x), float(y), float(width), float(height)))

        self.bbox = (int(x), int(y), int(width), int(height))

        self.initialized = True

        return True

    def update(self, frame):

        if not self.initialized:

            raise RuntimeError("Tracker has not been initialized.")

        if frame is None:

            return False, None

        success, bbox = self.tracker.update(frame)

        if not success:
            return False, None

        x, y, width, height = bbox

        self.bbox = (int(x), int(y), int(width), int(height))

        return True, self.bbox

    def get_bbox(self):

        return self.bbox

    def get_center(self):

        if self.bbox is None:

            return None

        x, y, width, height = self.bbox

        center_x = x + width // 2
        center_y = y + height // 2

        return center_x, center_y

    def is_tracking(self):

        return self.initialized

    def reset(self):

        self.tracker = None
        self.bbox = None
        self.initialized = False
