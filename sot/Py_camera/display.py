import cv2

WINDOW_NAME = " Web camera"

def show(frame):
    cv2.imshow(
        WINDOW_NAME, frame)

def wait_key(delay=0):
    return cv2.waitKey(delay) & 0xFF

def close():
    cv2.destroyAllWindows()