"""Frame-level orchestration for the P2 tracking layer."""

from __future__ import annotations

from typing import Optional

import numpy as np

from tracking_layer.botsort_tracker import TrackerInterface
from tracking_layer.tracking_types import FrameDetections, TrackRecord


class TrackingPipeline:
    """Validate frame inputs and coordinate the tracker."""

    def __init__(self, tracker: TrackerInterface) -> None:
        if tracker is None:
            raise ValueError("tracker cannot be None")

        self._tracker = tracker
        self._last_frame_id: Optional[int] = None
        self._last_timestamp: Optional[float] = None
        self._last_tracks: list[TrackRecord] = []

    def process_frame(
        self,
        frame: FrameDetections,
        image: np.ndarray,
    ) -> list[TrackRecord]:
        """Process one frame and return tracks observed in that frame."""

        self._validate_frame(frame, image)

        if self._last_frame_id is not None:
            if frame.frame_id <= self._last_frame_id:
                raise ValueError(
                    f"Frame IDs must increase: received {frame.frame_id} "
                    f"after {self._last_frame_id}"
                )

            if frame.timestamp < self._last_timestamp:
                raise ValueError(
                    f"Frame timestamp moved backwards: {frame.timestamp} "
                    f"< {self._last_timestamp}"
                )

        # The tracker receives the frame metadata and image together.
        tracks = self._tracker.update(frame, image)

        if not isinstance(tracks, list):
            raise TypeError("Tracker.update() must return a list")

        if not all(isinstance(track, TrackRecord) for track in tracks):
            raise TypeError(
                "Tracker.update() must return only TrackRecord objects"
            )

        self._last_frame_id = frame.frame_id
        self._last_timestamp = frame.timestamp
        self._last_tracks = list(tracks)

        return list(self._last_tracks)

    @staticmethod
    def _validate_frame(
        frame: FrameDetections,
        image: np.ndarray,
    ) -> None:
        if not isinstance(frame, FrameDetections):
            raise TypeError("frame must be a FrameDetections instance")

        if not isinstance(image, np.ndarray):
            raise TypeError("image must be a NumPy array")

        if image.size == 0:
            raise ValueError("image cannot be empty")

        if image.ndim != 3 or image.shape[2] != 3:
            raise ValueError(
                "image must have shape (height, width, 3) in BGR format"
            )

        image_height, image_width = image.shape[:2]

        if image_width != frame.width or image_height != frame.height:
            raise ValueError(
                "Frame/image dimensions do not match: "
                f"metadata={frame.width}x{frame.height}, "
                f"image={image_width}x{image_height}"
            )

    @property
    def last_frame_id(self) -> Optional[int]:
        """Return the most recently processed frame ID."""
        return self._last_frame_id

    @property
    def last_tracks(self) -> list[TrackRecord]:
        """Return a copy of the tracks observed in the last processed frame."""
        return list(self._last_tracks)

    def reset(self) -> None:
        """Reset pipeline and tracker state."""
        self._tracker.reset()
        self._last_frame_id = None
        self._last_timestamp = None
        self._last_tracks.clear()