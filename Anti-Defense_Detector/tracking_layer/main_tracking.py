"""Main entry point for tracking-layer tests and visualization."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import traceback
from pathlib import Path
from typing import Optional

import cv2
import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tracking_layer.botsort_tracker import BoTSORTTracker
from tracking_layer.detection_adapter import parse_frame_packet
from tracking_layer.jsonl_replay import JSONLReplay
from tracking_layer.output_writer import TrackingOutputWriter
from tracking_layer.tracking_pipeline import TrackingPipeline
from tracking_layer.tracking_types import (
    Detection,
    FrameDetections,
    TrackRecord,
    TrackStatus,
)
from tracking_layer.trajectory_buffer import TrajectoryBuffer

def make_test_frame(
    frame_id: int = 0,
    timestamp: float = 1.0,
    with_detection: bool = True,
) -> FrameDetections:
    """Create a synthetic frame for smoke testing."""

    detections = ()

    if with_detection:
        detections = (
            Detection(
                class_id=0,
                class_name="test_object",
                confidence=0.95,
                x1=10.0,
                y1=20.0,
                x2=50.0,
                y2=80.0,
            ),
        )

    return FrameDetections(
        frame_id=frame_id,
        timestamp=timestamp,
        width=640,
        height=480,
        detections=detections,
    )


def make_test_track(
    frame: FrameDetections,
    track_id: int = 1,
) -> TrackRecord:
    """Create a synthetic track record."""

    return TrackRecord(
        track_id=track_id,
        class_id=0,
        class_name="test_object",
        confidence=0.95,
        x1=10.0,
        y1=20.0,
        x2=50.0,
        y2=80.0,
        first_seen_timestamp=frame.timestamp,
        last_seen_timestamp=frame.timestamp,
        track_age=1,
        status=TrackStatus.CONFIRMED,
    )


class FakeTracker:
    """Minimal tracker used to test the pipeline without BoT-SORT."""

    def __init__(self) -> None:
        self.calls = 0
        self.last_frame: Optional[FrameDetections] = None

    def update(
        self,
        frame: FrameDetections,
        image: np.ndarray,
    ) -> list[TrackRecord]:
        self.calls += 1
        self.last_frame = frame

        if frame.detections:
            return [make_test_track(frame)]

        return []

    def reset(self) -> None:
        self.calls = 0
        self.last_frame = None

def test_detection_adapter() -> None:
    """Test normal, empty, and invalid P1 records."""

    packet = {
        "frame_id": 0,
        "timestamp": 1.0,
        "width": 640,
        "height": 480,
        "fused_detections": [
            {
                "class_id": 0,
                "class_name": "test_object",
                "confidence": 0.95,
                "x1": 10.0,
                "y1": 20.0,
                "x2": 50.0,
                "y2": 80.0,
            }
        ],
    }

    frame = parse_frame_packet(packet)
    assert frame.frame_id == 0
    assert len(frame.detections) == 1

    empty_packet = {
        **packet,
        "frame_id": 1,
        "fused_detections": [],
    }
    assert len(parse_frame_packet(empty_packet).detections) == 0

    try:
        parse_frame_packet({"frame_id": 2, "error": "test error"})
    except ValueError:
        pass
    else:
        raise AssertionError("P1 error record should be rejected")


def test_lifecycle_model() -> None:
    """Check lifecycle enum values."""

    assert TrackStatus.TENTATIVE.value == "tentative"
    assert TrackStatus.CONFIRMED.value == "confirmed"
    assert TrackStatus.LOST.value == "lost"
    assert TrackStatus.ENDED.value == "ended"


def test_trajectory_buffer() -> None:
    """Test trajectory storage and bounded history."""

    buffer = TrajectoryBuffer(max_points=3)

    for frame_id in range(3):
        frame = make_test_frame(
            frame_id=frame_id,
            timestamp=float(frame_id + 1),
        )
        buffer.update([make_test_track(frame)], frame_id)

    history = buffer.get_history(1)

    assert len(history) == 3
    assert history[-1].frame_id == 2
    assert buffer.get_latest(1) is not None
    assert len(buffer) == 1

    frame = make_test_frame(frame_id=3, timestamp=4.0)
    buffer.update([make_test_track(frame)], 3)

    history = buffer.get_history(1)

    assert len(history) == 3
    assert history[0].frame_id == 1
    assert history[-1].frame_id == 3

    assert buffer.get_history(999) == []
    assert buffer.get_latest(999) is None


def test_pipeline() -> None:
    """Test pipeline processing, frame validation, and reset."""

    fake_tracker = FakeTracker()
    pipeline = TrackingPipeline(fake_tracker)

    image = np.zeros((480, 640, 3), dtype=np.uint8)

    frame0 = make_test_frame(frame_id=0, timestamp=1.0)
    tracks0 = pipeline.process_frame(frame0, image)

    assert len(tracks0) == 1
    assert tracks0[0].track_id == 1
    assert fake_tracker.calls == 1
    assert pipeline.last_frame_id == 0
    assert len(pipeline.last_tracks) == 1

    frame1 = make_test_frame(
        frame_id=1,
        timestamp=2.0,
        with_detection=False,
    )
    tracks1 = pipeline.process_frame(frame1, image)

    assert tracks1 == []
    assert fake_tracker.calls == 2
    assert pipeline.last_frame_id == 1

    # A repeated frame must be rejected.
    try:
        pipeline.process_frame(frame1, image)
    except ValueError:
        pass
    else:
        raise AssertionError("Repeated frame ID should be rejected")

    # Incorrect image dimensions must be rejected.
    wrong_image = np.zeros((240, 320, 3), dtype=np.uint8)
    frame2 = make_test_frame(frame_id=2, timestamp=3.0)

    try:
        pipeline.process_frame(frame2, wrong_image)
    except ValueError:
        pass
    else:
        raise AssertionError("Image dimension mismatch should be rejected")

    assert fake_tracker.calls == 2
    assert pipeline.last_frame_id == 1

    pipeline.reset()

    assert pipeline.last_frame_id is None
    assert pipeline.last_tracks == []
    assert fake_tracker.calls == 0


def test_jsonl_replay_and_output() -> None:
    """Test JSONL replay and output schema."""

    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        input_path = root / "input.jsonl"
        output_path = root / "output.jsonl"

        packets = [
            {
                "frame_id": 0,
                "timestamp": 1.0,
                "width": 640,
                "height": 480,
                "fused_detections": [
                    {
                        "class_id": 0,
                        "class_name": "test_object",
                        "confidence": 0.95,
                        "x1": 10.0,
                        "y1": 20.0,
                        "x2": 50.0,
                        "y2": 80.0,
                    }
                ],
            },
            {
                "frame_id": 1,
                "timestamp": 2.0,
                "width": 640,
                "height": 480,
                "fused_detections": [],
            },
        ]

        with input_path.open("w", encoding="utf-8") as file:
            for packet in packets:
                file.write(json.dumps(packet) + "\n")

        frames = JSONLReplay(input_path).read_all()

        assert len(frames) == 2
        assert len(frames[0].detections) == 1
        assert len(frames[1].detections) == 0

        with TrackingOutputWriter(output_path) as writer:
            writer.write_frame(
                frames[0],
                [make_test_track(frames[0])],
            )
            writer.write_frame(frames[1], [])

        with output_path.open("r", encoding="utf-8") as file:
            records = [
                json.loads(line)
                for line in file
                if line.strip()
            ]

        assert len(records) == 2
        assert records[0]["track_count"] == 1
        assert records[1]["track_count"] == 0
        assert records[1]["tracks"] == []


def run_smoke_tests() -> bool:
    """Run checks that do not require a video or BoT-SORT backend."""

    tests = [
        ("Detection adapter", test_detection_adapter),
        ("Track lifecycle model", test_lifecycle_model),
        ("Trajectory buffer", test_trajectory_buffer),
        ("Tracking pipeline", test_pipeline),
        ("JSONL replay and output", test_jsonl_replay_and_output),
    ]

    passed = 0
    failed = 0

    print("\nTracking Layer Smoke Tests")
    print("=" * 40)

    for name, function in tests:
        try:
            function()
            print(f"[PASS] {name}")
            passed += 1
        except Exception:
            print(f"[FAIL] {name}")
            traceback.print_exc()
            failed += 1

    print("=" * 40)
    print(f"Passed: {passed} | Failed: {failed}")

    return failed == 0


def draw_track_trajectories(
    image: np.ndarray,
    trajectory_buffer: TrajectoryBuffer,
    tracks: list[TrackRecord],
    frame_id: int,
    color: tuple[int, int, int] = (255, 0, 0),
    thickness: int = 2,
    min_points: int = 2,
) -> None:
    """Draw historical center points for currently observed tracks."""

    for track in tracks:
        points = trajectory_buffer.get_history(track.track_id)

        if len(points) < min_points:
            continue

        centers = [
            (int(point.center[0]), int(point.center[1]))
            for point in points
        ]

        for index in range(1, len(centers)):
            cv2.line(
                image,
                centers[index - 1],
                centers[index],
                color,
                thickness,
                cv2.LINE_AA,
            )

        for center in centers:
            cv2.circle(
                image,
                center,
                2,
                color,
                -1,
                cv2.LINE_AA,
            )


def run_visualization(
    video_path: str,
    detections_path: str,
    output_path: str | None = None,
    output_video_path: str | None = None,
) -> None:
    """Run tracking, display annotated frames, and save JSONL/video outputs.

    Assumption: P1 frame_id matches the video's zero-based frame index.
    """

    video_file = Path(video_path)
    detections_file = Path(detections_path)

    if not video_file.is_file():
        raise FileNotFoundError(f"Video not found: {video_file}")

    if not detections_file.is_file():
        raise FileNotFoundError(
            f"Detection JSONL not found: {detections_file}"
        )

    cap = cv2.VideoCapture(str(video_file))

    if not cap.isOpened():
        cap.release()
        raise RuntimeError(f"Cannot open video: {video_file}")

    writer = None
    video_writer = None
    output_video_file = Path(output_video_path) if output_video_path else None
    if output_video_file is not None:
        output_video_file.parent.mkdir(parents=True, exist_ok=True)

    frame_count = 0
    last_frame_id = -1

    try:
        fps = cap.get(cv2.CAP_PROP_FPS)
        if not np.isfinite(fps) or fps <= 0:
            fps = 30.0

        tracker = BoTSORTTracker(fps=fps)
        pipeline = TrackingPipeline(tracker)
        trajectory_buffer = TrajectoryBuffer(max_points=100)

        if output_path:
            writer = TrackingOutputWriter(output_path)

        with detections_file.open("r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, start=1):
                if not line.strip():
                    continue

                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"Invalid JSON at line {line_number}: {exc}"
                    ) from exc

                if not isinstance(record, dict):
                    raise ValueError(
                        f"Expected a JSON object at line {line_number}"
                    )

                if "error" in record:
                    print(
                        f"\nSkipping P1 error at line {line_number}: "
                        f"{record['error']}"
                    )
                    continue

                frame = parse_frame_packet(record)

                if frame.frame_id <= last_frame_id:
                    raise ValueError(
                        f"Frame IDs must increase; invalid ID "
                        f"{frame.frame_id} at line {line_number}"
                    )

                # Seek to the corresponding zero-based video frame.
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame.frame_id)
                success, image = cap.read()

                if not success:
                    print(
                        f"\nCould not read video frame {frame.frame_id}; "
                        "stopping replay."
                    )
                    break

                image_height, image_width = image.shape[:2]

                if (
                    image_width != frame.width
                    or image_height != frame.height
                ):
                    raise ValueError(
                        f"Frame {frame.frame_id}: video is "
                        f"{image_width}x{image_height}, but P1 reports "
                        f"{frame.width}x{frame.height}"
                    )

                # Initialize the video writer only after the actual frame size is known.
                if output_video_file is not None and video_writer is None:
                    height, width = image.shape[:2]
                    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                    video_writer = cv2.VideoWriter(
                        str(output_video_file), fourcc, fps, (width, height)
                    )
                    if not video_writer.isOpened():
                        video_writer.release()
                        video_writer = None
                        raise RuntimeError(
                            f"Could not create output video: {output_video_file}. "
                            "Check the output directory and OpenCV video codec support."
                        )
                    print(f"Saving annotated video to: {output_video_file}")

                tracks = pipeline.process_frame(frame, image)

                trajectory_buffer.update(tracks, frame.frame_id)

                draw_track_trajectories(
                    image=image,
                    trajectory_buffer=trajectory_buffer,
                    tracks=tracks,
                    frame_id=frame.frame_id,
                )

                for track in tracks:
                    x1 = max(0, int(track.x1))
                    y1 = max(0, int(track.y1))
                    x2 = min(image_width - 1, int(track.x2))
                    y2 = min(image_height - 1, int(track.y2))

                    if x2 <= x1 or y2 <= y1:
                        continue

                    label = (
                        f"ID {track.track_id} | "
                        f"{track.class_name} | "
                        f"{track.confidence:.2f}"
                    )

                    cv2.rectangle(
                        image,
                        (x1, y1),
                        (x2, y2),
                        (0, 255, 0),
                        2,
                    )

                    cv2.putText(
                        image,
                        label,
                        (x1, max(20, y1 - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.55,
                        (0, 255, 0),
                        2,
                        cv2.LINE_AA,
                    )

                cv2.putText(
                    image,
                    f"Frame: {frame.frame_id} | Tracks: {len(tracks)}",
                    (15, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 255, 255),
                    2,
                    cv2.LINE_AA,
                )

                if writer is not None:
                    writer.write_frame(frame, tracks)

                # Save the same annotated frame shown in the live preview.
                if video_writer is not None:
                    video_writer.write(image)

                cv2.imshow("P2 BoT-SORT Tracking", image)

                frame_count += 1
                last_frame_id = frame.frame_id

                print(
                    f"\rProcessed frames: {frame_count} | "
                    f"Current tracks: {len(tracks)}",
                    end="",
                    flush=True,
                )

                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

        print(f"\nVisualization finished. Frames processed: {frame_count}")

    finally:
        cap.release()
        cv2.destroyAllWindows()

        if writer is not None:
            writer.close()

        if video_writer is not None:
            video_writer.release()
            print(f"Annotated video saved: {output_video_file}")


def main() -> None:
    """Launch default visualization or run smoke tests."""

    parser = argparse.ArgumentParser(
        description="Tracking layer visualization and smoke tests."
    )

    parser.add_argument(
        "--check",
        action="store_true",
        help="Run smoke tests instead of video tracking.",
    )
    parser.add_argument(
        "--video",
        type=str,
        default=None,
        help="Optional source video path.",
    )
    parser.add_argument(
        "--detections",
        type=str,
        default=None,
        help="Optional P1 detection JSONL path.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Optional tracking output JSONL path.",
    )
    parser.add_argument(
        "--output-video",
        type=str,
        default=None,
        help="Optional path for the annotated output video (MP4).",
    )

    args = parser.parse_args()

    if args.check:
        if not run_smoke_tests():
            raise SystemExit(1)
        return

    # Default paths are anchored to this file's project directory,
    # so VS Code's working directory does not affect them.
    video_path = args.video or str(
        PROJECT_ROOT / "asset" / "drone_testing.mp4"
    )
    detections_path = args.detections or str(
        PROJECT_ROOT / "data" / "output" / "eo_perception_v1.jsonl"
    )
    output_dir = PROJECT_ROOT / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = args.output or str(
        PROJECT_ROOT / "tracking_output.jsonl"
    )
    output_video_path = args.output_video or str(
        output_dir / "tracking_output.mp4"
    )

    print(f"Input video:       {video_path}")
    print(f"P1 detections:     {detections_path}")
    print(f"Tracking JSONL:    {output_path}")
    print(f"Annotated video:   {output_video_path}")

    run_visualization(
        video_path=video_path,
        detections_path=detections_path,
        output_path=output_path,
        output_video_path=output_video_path,
    )


if __name__ == "__main__":
    main()