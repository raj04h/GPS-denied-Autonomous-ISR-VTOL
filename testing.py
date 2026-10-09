
from dataclasses import dataclass
from enum import Enum
from math import isfinite
from typing import Tuple


class TrackStatus(str, Enum):
    TENTATIVE = "tentative"
    CONFIRMED = "confirmed"
    LOST = "lost"
    ENDED = "ended"


@dataclass(frozen=True)
class Detection:
    """Normalized detection received from P1."""

    class_id: int
    class_name: str
    confidence: float
    x1: float
    y1: float
    x2: float
    y2: float

    def __post_init__(self):
        if self.class_id < 0:
            raise ValueError("class_id must be non-negative")

        if not self.class_name.strip():
            raise ValueError("class_name cannot be empty")

        if not isfinite(self.confidence) or not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")

        coordinates = (self.x1, self.y1, self.x2, self.y2)
        if not all(isfinite(value) for value in coordinates):
            raise ValueError("Bounding-box coordinates must be finite")

        if self.x2 <= self.x1 or self.y2 <= self.y1:
            raise ValueError("Bounding box must have positive width and height")


@dataclass(frozen=True)
class FrameDetections:
    """All normalized detections for one frame."""

    frame_id: int
    timestamp: float
    width: int
    height: int
    detections: Tuple[Detection, ...]

    def __post_init__(self):
        if self.frame_id < 0:
            raise ValueError("frame_id must be non-negative")

        if not isfinite(self.timestamp) or self.timestamp < 0:
            raise ValueError("timestamp must be finite and non-negative")

        if self.width <= 0 or self.height <= 0:
            raise ValueError("Frame dimensions must be positive")

        if not isinstance(self.detections, tuple):
            raise TypeError("detections must be a tuple")

        if not all(isinstance(detection, Detection) for detection in self.detections):
            raise TypeError("Every item must be a Detection")


@dataclass(frozen=True)
class TrackRecord:
    """Standardized tracking output for one object."""

    track_id: int
    class_id: int
    class_name: str
    confidence: float
    x1: float
    y1: float
    x2: float
    y2: float
    first_seen_timestamp: float
    last_seen_timestamp: float
    track_age: int
    status: TrackStatus

    def __post_init__(self):
        if self.track_id < 1:
            raise ValueError("track_id must be positive")

        if self.class_id < 0:
            raise ValueError("class_id must be non-negative")

        if not self.class_name.strip():
            raise ValueError("class_name cannot be empty")

        if not isfinite(self.confidence) or not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")

        coordinates = (self.x1, self.y1, self.x2, self.y2)
        if not all(isfinite(value) for value in coordinates):
            raise ValueError("Bounding-box coordinates must be finite")

        if self.x2 <= self.x1 or self.y2 <= self.y1:
            raise ValueError("Bounding box must have positive width and height")

        if (
            not isfinite(self.first_seen_timestamp)
            or not isfinite(self.last_seen_timestamp)
            or self.first_seen_timestamp < 0
            or self.last_seen_timestamp < self.first_seen_timestamp
        ):
            raise ValueError("Track timestamps are invalid")

        if self.track_age < 1:
            raise ValueError("track_age must be at least 1")

        if not isinstance(self.status, TrackStatus):
            raise TypeError("status must be a TrackStatus value")
