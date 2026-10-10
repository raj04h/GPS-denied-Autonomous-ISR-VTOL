"""BoT-SORT tracker adapter for the P2 tracking layer."""

from abc import ABC, abstractmethod
from typing import Any

import numpy as np

from .tracking_types import (
    FrameDetections,
    TrackRecord,
    TrackStatus,
)


class TrackerInterface(ABC):
    """Common interface for tracking backends."""

    @abstractmethod
    def update(
        self,
        frame: FrameDetections,
        image: np.ndarray,
    ) -> list[TrackRecord]:
        """Update tracker state and return current tracks."""
        raise NotImplementedError

    @abstractmethod
    def reset(self) -> None:
        """Reset all internal tracking state."""
        raise NotImplementedError


class BoTSORTTracker(TrackerInterface):
    """BoT-SORT implementation using the BoxMOT package."""

    def __init__(
        self,
        tracker_config: dict[str, Any] | None = None,
        fps: float = 30.0,
    ) -> None:
        if isinstance(fps, bool) or not isinstance(fps, (int, float)):
            raise TypeError("fps must be numeric")

        if not np.isfinite(fps) or fps <= 0:
            raise ValueError("fps must be finite and greater than zero")

        try:
            from boxmot import BotSort
        except ImportError as exc:
            raise ImportError(
                "BoxMOT is required. Install boxmot in your active "
                "Python environment."
            ) from exc

        self._backend_class = BotSort
        self._config = dict(tracker_config or {})
        self._fps = float(fps)

        self._tracker = self._create_backend()

        # Metadata is keyed by the backend's track ID.
        self._metadata: dict[int, dict[str, Any]] = {}
        self._class_names: dict[int, str] = {}

        self._last_frame_id: int | None = None
        self._last_timestamp: float | None = None

    def _create_backend(self) -> Any:
        """Create a BoT-SORT backend instance."""
        return self._backend_class(
            **self._config,
            frame_rate=int(round(self._fps)),
        )

    def update(
        self,
        frame: FrameDetections,
        image: np.ndarray,
    ) -> list[TrackRecord]:
        """Process one frame and return currently reported tracks."""

        if not isinstance(frame, FrameDetections):
            raise TypeError("frame must be a FrameDetections instance")

        if not isinstance(image, np.ndarray) or image.ndim != 3:
            raise ValueError(
                "image must be a color image with shape (H, W, C)"
            )

        if image.shape[:2] != (frame.height, frame.width):
            raise ValueError(
                "Image dimensions do not match FrameDetections"
            )

        if self._last_frame_id is not None:
            if frame.frame_id <= self._last_frame_id:
                raise ValueError("frame_id must increase between updates")

            if (
                self._last_timestamp is not None
                and frame.timestamp < self._last_timestamp
            ):
                raise ValueError("timestamp cannot move backwards")

        for detection in frame.detections:
            self._class_names[detection.class_id] = detection.class_name

        # BoxMOT input format:
        # [x1, y1, x2, y2, confidence, class_id]
        detections = np.asarray(
            [
                [
                    det.x1,
                    det.y1,
                    det.x2,
                    det.y2,
                    det.confidence,
                    det.class_id,
                ]
                for det in frame.detections
            ],
            dtype=np.float32,
        ).reshape(-1, 6)

        # Update the backend even if the frame has no detections.
        raw_tracks = self._tracker.update(detections, image)
        tracks = self._convert_tracks(raw_tracks, frame)

        self._last_frame_id = frame.frame_id
        self._last_timestamp = frame.timestamp

        return tracks

    def _convert_tracks(
        self,
        raw_tracks: Any,
        frame: FrameDetections,
    ) -> list[TrackRecord]:
        """Convert BoxMOT rows into the P2 TrackRecord contract.

        Expected columns:
        x1, y1, x2, y2, track_id, confidence, class_id.

        Only tracks actually returned by the backend are emitted here.
        """

        if raw_tracks is None:
            return []

        rows = np.asarray(raw_tracks)

        if rows.size == 0:
            return []

        if rows.ndim != 2 or rows.shape[1] < 7:
            raise ValueError(
                "Unexpected BoT-SORT output format; expected "
                "at least 7 columns"
            )

        results: list[TrackRecord] = []
        seen_track_ids: set[int] = set()

        for row in rows:
            x1, y1, x2, y2 = map(float, row[:4])
            track_id = int(row[4])
            confidence = float(row[5])
            class_id = int(row[6])

            if track_id <= 0 or class_id < 0:
                continue

            if not np.isfinite(
                [x1, y1, x2, y2, confidence]
            ).all():
                continue

            if x2 <= x1 or y2 <= y1:
                continue

            if not 0.0 <= confidence <= 1.0:
                continue

            class_name = self._class_names.get(
                class_id,
                f"class_{class_id}",
            )

            previous = self._metadata.get(track_id)

            if previous is None:
                first_seen = frame.timestamp
                observation_count = 1
            else:
                first_seen = previous["first_seen_timestamp"]
                observation_count = previous["observation_count"] + 1

            # Metadata is updated only when this ID is returned by BoT-SORT.
            self._metadata[track_id] = {
                "first_seen_timestamp": first_seen,
                "last_seen_timestamp": frame.timestamp,
                "last_seen_frame_id": frame.frame_id,
                "observation_count": observation_count,
                "class_id": class_id,
                "class_name": class_name,
            }

            seen_track_ids.add(track_id)

            results.append(
                TrackRecord(
                    track_id=track_id,
                    class_id=class_id,
                    class_name=class_name,
                    confidence=confidence,
                    x1=x1,
                    y1=y1,
                    x2=x2,
                    y2=y2,
                    first_seen_timestamp=first_seen,
                    last_seen_timestamp=frame.timestamp,
                    track_age=observation_count,
                    status=TrackStatus.CONFIRMED,
                )
            )

        return results

    def get_track_metadata(self) -> dict[int, dict[str, Any]]:
        """Return a snapshot of metadata for IDs observed by the backend.

        This includes last-seen information. It does not assert that a
        track absent from the current output is still active.
        """
        return {
            track_id: metadata.copy()
            for track_id, metadata in self._metadata.items()
        }

    def reset(self) -> None:
        """Reset BoT-SORT and clear stored metadata."""
        self._tracker = self._create_backend()
        self._metadata.clear()
        self._class_names.clear()
        self._last_frame_id = None
        self._last_timestamp = None