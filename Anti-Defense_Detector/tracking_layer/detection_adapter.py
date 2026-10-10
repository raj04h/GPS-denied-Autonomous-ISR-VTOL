import math
from typing import Any, Mapping

from .tracking_types import Detection, FrameDetections


def parse_frame_packet(record: Mapping[str, Any]) -> FrameDetections:
    """Convert one P1 JSONL frame record into the P2 data contract."""

    if not isinstance(record, Mapping):
        raise TypeError("Frame record must be a mapping")

    if "error" in record:
        raise ValueError(f"P1 frame contains an error: {record['error']}")

    required = (
        "frame_id",
        "timestamp",
        "width",
        "height",
        "fused_detections",
    )

    missing = [key for key in required if key not in record]
    if missing:
        raise ValueError(f"Missing required frame fields: {missing}")

    frame_id = record["frame_id"]
    timestamp = record["timestamp"]
    width = record["width"]
    height = record["height"]
    raw_detections = record["fused_detections"]

    if isinstance(frame_id, bool) or not isinstance(frame_id, int):
        raise ValueError("frame_id must be an integer")

    if isinstance(width, bool) or not isinstance(width, int):
        raise ValueError("width must be an integer")

    if isinstance(height, bool) or not isinstance(height, int):
        raise ValueError("height must be an integer")

    if isinstance(timestamp, bool) or not isinstance(timestamp, (int, float)):
        raise ValueError("timestamp must be numeric")

    if not math.isfinite(timestamp) or timestamp < 0:
        raise ValueError("timestamp must be finite and non-negative")

    if width <= 0 or height <= 0:
        raise ValueError("Frame dimensions must be positive")

    if not isinstance(raw_detections, list):
        raise ValueError("fused_detections must be a list")

    detections = []

    required_detection_fields = (
        "class_id",
        "class_name",
        "confidence",
        "x1",
        "y1",
        "x2",
        "y2",
    )

    for index, item in enumerate(raw_detections):
        if not isinstance(item, Mapping):
            raise ValueError(
                f"Detection at index {index} must be an object"
            )

        missing_fields = [
            key for key in required_detection_fields if key not in item
        ]

        if missing_fields:
            raise ValueError(
                f"Detection {index} missing fields: {missing_fields}"
            )

        class_id = item["class_id"]

        if (
            isinstance(class_id, bool)
            or not isinstance(class_id, int)
            or class_id < 0
        ):
            print(
                f"WARNING: Skipping invalid detection at frame {frame_id}, "
                f"detection index {index}: class_id={class_id!r}"
            )
            continue

        try:
            detection = Detection(
                class_id=class_id,
                class_name=item["class_name"],
                confidence=item["confidence"],
                x1=item["x1"],
                y1=item["y1"],
                x2=item["x2"],
                y2=item["y2"],
            )
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Invalid detection at index {index}: {exc}"
            ) from exc

        detections.append(detection)

    return FrameDetections(
        frame_id=frame_id,
        timestamp=float(timestamp),
        width=width,
        height=height,
        detections=tuple(detections),
    )