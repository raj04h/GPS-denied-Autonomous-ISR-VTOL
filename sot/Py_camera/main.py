import cv2

from camera import Camera
from selector import ROISelector, WINDOW_NAME
from tracking_ms import MOSSETracker

from display import (
    show,
    wait_key,
    close,
)

# Configuration
WARMUP_FRAMES = 30

# Core Logic
def main():

    camera = Camera()
    roi_selector = ROISelector()
    tracker = MOSSETracker()

    try:
        camera.open()
        print()

        print(f"Resolution : " f"{camera.get_width()} x " f"{camera.get_height()}")
        print(f"Camera FPS : " f"{camera.get_fps():.1f}")

        print()

        roi_selector.start()
        print()

        selected_frame = None
        
        while not roi_selector.is_selected():
            frame = camera.read()
            if frame is None:
                continue

            selected_frame = frame.copy()

            # Update selector
            display_frame = roi_selector.update(frame)

            cv2.imshow(WINDOW_NAME, display_frame)
   
            key = cv2.waitKey(1) & 0xFF

            if key == ord("q") or key == 27:

                print()
                print("Target selection cancelled.")
                return

        # Get ROI
        roi = roi_selector.get_roi()

        if roi is None:
            print()
            print("ERROR: Invalid ROI.")
            return

        print()
        print("TARGET ROI")
        print(f"ROI    : {roi}")
        print(f"Center : " f"{roi_selector.get_center()}")
        print()

        # Initialize MOSSE

        if selected_frame is None:
            print("ERROR: No valid frame available.")
            return

        tracker.initialize(selected_frame, roi)
        print()

        # Close selection window

        cv2.destroyWindow(WINDOW_NAME)

        # Warm-up

        print(f"Warming up for " f"{WARMUP_FRAMES} frames...")

        for _ in range(WARMUP_FRAMES):

            frame = camera.read()

            if frame is None:

                continue

            tracker.update(frame)

        print("Warm-up complete.")
        print()

        # Continuous tracking loop

        while True:

            # Capture live frame

            frame = camera.read()

            if frame is None:

                continue

            # Update MOSSE

            success, bbox = tracker.update(frame)

            # Tracking successful

            if success:

                x, y, width, height = bbox

                # Bounding box

                cv2.rectangle(frame, (x, y), (x + width, y + height), (0, 255, 0), 2)

                # Target center

                center = tracker.get_center()

                if center is not None:

                    center_x, center_y = center

                    cv2.circle(frame, (center_x, center_y), 5, (0, 0, 255), -1)

                    cv2.putText(
                        frame,
                        f"Center: " f"({center_x}, {center_y})",
                        (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 255, 0),
                        2,
                    )

                # Tracking status

                cv2.putText(
                    frame,
                    "MOSSE: TRACKING",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2,
                )

            # Tracking failed

            else:

                cv2.putText(
                    frame,
                    "MOSSE: LOST",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 0, 255),
                    2,
                )

            # Display

            show(frame)

            # Keyboard

            key = wait_key(1)

            if key == ord("q") or key == 27:

                print()
                print("Tracking stopped by user.")

                break

    except RuntimeError as error:

        print(f"ERROR: {error}")

    except Exception as error:

        print(f"UNEXPECTED ERROR: {error}")

    finally:

        camera.release()

        close()

        print("Camera released.")


# Execution
if __name__ == "__main__":

    main()
