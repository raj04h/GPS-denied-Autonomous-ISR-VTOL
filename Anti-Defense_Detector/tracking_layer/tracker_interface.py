
from abc import ABC, abstractmethod

from .track_types import FrameDetections, TrackRecord


class TrackerInterface(ABC):
    """Common interface for the tracking backend."""

    @abstractmethod
    def update(self, frame: FrameDetections) -> list[TrackRecord]:
        """Update tracks using detections from one frame."""
        raise NotImplementedError

    @abstractmethod
    def reset(self) -> None:
        """Reset tracker state before starting a new sequence."""
        raise NotImplementedError
