import cv2

from camera import Camera


def main():

    camera = Camera()

    while True:

        frame = camera.read()

        if frame is None:
            break

        cv2.imshow("Drone Video", frame)

        key = cv2.waitKey(30) & 0xFF

        if key == ord("q"):
            break

    camera.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()