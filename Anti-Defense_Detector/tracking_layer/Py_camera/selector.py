import cv2

# Configuration

WINDOW_NAME = "VAero - Select Target"


# Core Logic

class ROISelector:

    def __init__(self):

        self.roi = None

        self.selecting = False
        self.selected = False

        self.start_point = None
        self.current_point = None

    def start(self):


        self.roi = None
        self.selecting = False
        self.selected = False

        self.start_point = None
        self.current_point = None

        cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)

        cv2.setMouseCallback(WINDOW_NAME, self.mouse_callback)

    def mouse_callback(self, event, x, y, flags, param):

        if event == cv2.EVENT_LBUTTONDOWN:

            self.selecting = True
            self.selected = False

            self.start_point = (x, y)

            self.current_point = (x, y)

        elif event == cv2.EVENT_MOUSEMOVE:

            if self.selecting:

                self.current_point = (x, y)

        elif event == cv2.EVENT_LBUTTONUP:

            if self.selecting:

                self.current_point = (x, y)

                self.selecting = False

                self.create_roi()

    def create_roi(self):

        if self.start_point is None:
            return

        if self.current_point is None:
            return

        x1, y1 = self.start_point
        x2, y2 = self.current_point

        x = min(x1, x2)
        y = min(y1, y2)

        width = abs(x2 - x1)
        height = abs(y2 - y1)

        if width <= 0 or height <= 0:

            self.roi = None
            self.selected = False

            return

        self.roi = (int(x), int(y), int(width), int(height))

        self.selected = True

    def update(self, frame):

        display_frame = frame.copy()

        if (
            self.selecting
            and self.start_point is not None
            and self.current_point is not None
        ):

            x1, y1 = self.start_point
            x2, y2 = self.current_point

            cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

        if self.selected and self.roi is not None:

            x, y, width, height = self.roi

            cv2.rectangle(
                display_frame, (x, y), (x + width, y + height), (0, 255, 0), 2
            )

            center_x = x + width // 2

            center_y = y + height // 2

            cv2.circle(display_frame, (center_x, center_y), 5, (0, 0, 255), -1)

            cv2.putText(
                display_frame,
                "TARGET SELECTED",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2,
            )

        else:

            cv2.putText(
                display_frame,
                "DRAG TO SELECT TARGET",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 255),
                2,
            )

        return display_frame

    def get_roi(self):

        return self.roi

    def get_center(self):

        if self.roi is None:

            return None

        x, y, width, height = self.roi

        center_x = x + width // 2

        center_y = y + height // 2

        return (center_x, center_y)

    def is_selected(self):

        return self.selected

    def reset(self):

        self.roi = None

        self.selecting = False
        self.selected = False

        self.start_point = None
        self.current_point = None

    def close(self):

        cv2.destroyWindow(WINDOW_NAME)
