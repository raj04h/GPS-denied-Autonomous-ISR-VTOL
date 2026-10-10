import cv2
from collections import deque
from datetime import datetime
from pathlib import Path

from camera import Camera
from selector import ROISelector, WINDOW_NAME
from tracking_ms import MOSSETracker
from display import show, wait_key, close

# Configuration
DEFAULT_VIDEO_PATH = (
    "/media/hraj/B3EA-9D8F/HRaj_WS/Autonomous-ISR-VTOL/"
    "Anti-Defense_Detector/asset/bw_vehicle.mp4"
)
WARMUP_FRAMES = 30  # Applied to webcam only; do not skip frames in prerecorded video.
OUTPUT_DIRECTORY = Path(
    "/media/hraj/B3EA-9D8F/HRaj_WS/Autonomous-ISR-VTOL/"
    "Anti-Defense_Detector/output"
)
TRAIL_LENGTH = 40  # Number of recent target-center positions to visualize.


def choose_source():
    """Return ('camera', None) or ('video', path)."""
    while True:
        print("\nSelect input source:")
        print("  1. Prerecorded video")
        print("  2. Web camera")
        choice = input("Enter 1 or 2: ").strip()

        if choice == "1":
            entered_path = input(
                f"Video path [press Enter for default: {DEFAULT_VIDEO_PATH}]: "
            ).strip().strip('"').strip("'")
            video_path = entered_path or DEFAULT_VIDEO_PATH

            import os
            if not os.path.isfile(video_path):
                print(f"ERROR: Video file not found: {video_path}")
                continue

            return "video", video_path

        if choice == "2":
            return "camera", None

        print("Invalid selection. Enter 1 or 2.")


def main():
    source_type, video_path = choose_source()

    camera = Camera() if source_type == "camera" else None
    video = None
    roi_selector = ROISelector()
    tracker = MOSSETracker()
    source_released = False
    output_writer = None
    output_path = None
    trajectory = deque(maxlen=TRAIL_LENGTH)

    def read_frame():
        if source_type == "camera":
            return camera.read()
        if video is None:
            return None
        ret, frame = video.read()
        return frame if ret else None

    def release_source():
        nonlocal source_released
        if source_released:
            return
        if camera is not None:
            camera.release()
        if video is not None:
            video.release()
        source_released = True

    try:
        if source_type == "camera":
            camera.open()
            width = camera.get_width()
            height = camera.get_height()
            fps = camera.get_fps()
            print("\nInput source: Web camera")
        else:
            video = cv2.VideoCapture(video_path)
            if not video.isOpened():
                raise RuntimeError(f"Unable to open video: {video_path}")
            width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = video.get(cv2.CAP_PROP_FPS)
            print(f"\nInput source: {video_path}")

        print(f"Resolution : {width} x {height}")
        print(f"Source FPS : {fps:.1f}")
        print("\nDrag a rectangle around the target. Press Q or Esc to cancel.")

        # Create a timestamped recording in the requested output directory.
        OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
        recording_fps = fps if fps and fps > 0 else 30.0
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = OUTPUT_DIRECTORY / f"mosse_tracking_{timestamp}.mp4"
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        output_writer = cv2.VideoWriter(
            str(output_path), fourcc, recording_fps, (width, height)
        )
        if not output_writer.isOpened():
            output_writer.release()
            output_writer = None
            raise RuntimeError(
                f"Could not create output video: {output_path}. "
                "Check that the output directory is writable and MP4 encoding is available."
            )
        print(f"Output recording: {output_path}")

        roi_selector.start()

        # For prerecorded video, freeze the first frame while the user
        # selects the ROI. This prevents the clip ending before selection.
        selected_frame = read_frame()
        if selected_frame is None:
            raise RuntimeError("Could not read the first frame from the input source.")

        if source_type == "video":
            print("Video paused on its first frame. Select the target ROI.")

        while not roi_selector.is_selected():
            display_frame = roi_selector.update(selected_frame)
            cv2.imshow(WINDOW_NAME, display_frame)

            key = cv2.waitKey(20) & 0xFF
            if key in (ord("q"), 27):
                print("Target selection cancelled.")
                return

        roi = roi_selector.get_roi()
        if roi is None:
            raise RuntimeError("Invalid ROI selected.")

        print("\nTARGET ROI")
        print(f"ROI    : {roi}")
        print(f"Center : {roi_selector.get_center()}")

        if selected_frame is None:
            raise RuntimeError("No valid frame available for tracker initialization.")

        tracker.initialize(selected_frame, roi)
        cv2.destroyWindow(WINDOW_NAME)

        # Warm-up only for a live camera. For a video, preserve every frame
        # after the selected ROI so short clips are not skipped.
        if source_type == "camera" and WARMUP_FRAMES > 0:
            print(f"\nWarming up for {WARMUP_FRAMES} frames...")
            for _ in range(WARMUP_FRAMES):
                frame = read_frame()
                if frame is None:
                    continue
                tracker.update(frame)
            print("Warm-up complete.")

        print("\nMOSSE tracking started. Press Q or Esc to stop.")

        while True:
            frame = read_frame()

            if frame is None:
                if source_type == "video":
                    print("End of prerecorded video reached.")
                    break
                continue

            success, bbox = tracker.update(frame)

            if success and bbox is not None:
                x, y, width, height = bbox
                center = tracker.get_center()

                # Bounding box and single-target label.
                cv2.rectangle(
                    frame, (x, y), (x + width, y + height), (0, 255, 0), 2
                )
                cv2.putText(
                    frame, "MOSSE | Target 1", (x, max(22, y - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2
                )

                if center is not None:
                    trajectory.append(center)
                    center_x, center_y = center
                    cv2.circle(frame, (center_x, center_y), 5, (0, 0, 255), -1)
                    cv2.putText(
                        frame,
                        f"Center: ({center_x}, {center_y})",
                        (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 255, 0),
                        2,
                    )

                # Draw recent motion path: blue connected trail and blue points.
                points = list(trajectory)
                for index in range(1, len(points)):
                    cv2.line(
                        frame, points[index - 1], points[index],
                        (255, 0, 0), 2, cv2.LINE_AA
                    )
                for point in points:
                    cv2.circle(frame, point, 3, (255, 0, 0), -1)

                status = "MOSSE: TRACKING"
                color = (0, 255, 0)
            else:
                status = "MOSSE: LOST"
                color = (0, 0, 255)

            cv2.putText(
                frame, status, (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2
            )

            # Record the same annotated frame shown on screen.
            if output_writer is not None:
                output_writer.write(frame)

            show(frame)

            # Pace prerecorded video at its source FPS (e.g. 25 FPS = 40 ms
            # per frame). Keep webcam display responsive with a short wait.
            if source_type == "video" and fps > 0:
                frame_delay_ms = max(1, int(round(1000.0 / fps)))
            else:
                frame_delay_ms = 1

            key = wait_key(frame_delay_ms)

            if key in (ord("q"), 27):
                print("Tracking stopped by user.")
                break

    except RuntimeError as error:
        print(f"ERROR: {error}")
    except Exception as error:
        print(f"UNEXPECTED ERROR: {error}")
    finally:
        release_source()
        if output_writer is not None:
            output_writer.release()
        close()
        if output_path is not None and output_path.exists():
            print(f"Recorded output video: {output_path}")
        print("Input source released.")


if __name__ == "__main__":
    main()




