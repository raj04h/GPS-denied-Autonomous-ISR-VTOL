"""Data models and lifecycle contract for the P2 tracking layer."""

from dataclasses import dataclass
from enum import Enum
from math import isfinite


class TrackStatus(str, Enum):
    """Lifecycle states exposed by the tracking layer."""

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

    def __post_init__(self) -> None:
        if isinstance(self.class_id, bool) or not isinstance(self.class_id, int):
            raise TypeError("class_id must be an integer")

        if self.class_id < 0:
            raise ValueError("class_id must be non-negative")

        if not isinstance(self.class_name, str) or not self.class_name.strip():
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
    detections: tuple[Detection, ...]

    def __post_init__(self) -> None:
        if isinstance(self.frame_id, bool) or not isinstance(self.frame_id, int):
            raise TypeError("frame_id must be an integer")

        if self.frame_id < 0:
            raise ValueError("frame_id must be non-negative")

        if not isfinite(self.timestamp) or self.timestamp < 0:
            raise ValueError("timestamp must be finite and non-negative")

        if (
            isinstance(self.width, bool)
            or not isinstance(self.width, int)
            or self.width <= 0
        ):
            raise ValueError("width must be a positive integer")

        if (
            isinstance(self.height, bool)
            or not isinstance(self.height, int)
            or self.height <= 0
        ):
            raise ValueError("height must be a positive integer")

        if not isinstance(self.detections, tuple):
            raise TypeError("detections must be a tuple")

        if not all(isinstance(d, Detection) for d in self.detections):
            raise TypeError("Every item must be a Detection")


@dataclass(frozen=True)
class TrackRecord:
    """Standardized output for a track observed in a frame.

    TrackRecord represents a track observation, not a complete registry
    of active, lost, or ended tracks.
    """

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

    def __post_init__(self) -> None:
        if isinstance(self.track_id, bool) or not isinstance(self.track_id, int):
            raise TypeError("track_id must be an integer")

        if self.track_id < 1:
            raise ValueError("track_id must be positive")

        if isinstance(self.class_id, bool) or not isinstance(self.class_id, int):
            raise TypeError("class_id must be an integer")

        if self.class_id < 0:
            raise ValueError("class_id must be non-negative")

        if not isinstance(self.class_name, str) or not self.class_name.strip():
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

        if (
            isinstance(self.track_age, bool)
            or not isinstance(self.track_age, int)
            or self.track_age < 1
        ):
            raise ValueError("track_age must be a positive integer")

        if not isinstance(self.status, TrackStatus):
            raise TypeError("status must be a TrackStatus value")