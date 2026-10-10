"""Bounded trajectory history for observed tracks."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from math import isfinite
from typing import Deque

from tracking_layer.tracking_types import TrackRecord


@dataclass(frozen=True)
class TrajectoryPoint:
    """One observed bounding box and its frame metadata."""

    timestamp: float
    frame_id: int
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float

    def __post_init__(self) -> None:
        if isinstance(self.frame_id, bool) or not isinstance(self.frame_id, int):
            raise TypeError("frame_id must be an integer")
        if self.frame_id < 0:
            raise ValueError("frame_id must be non-negative")

        values = (
            self.timestamp,
            self.x1,
            self.y1,
            self.x2,
            self.y2,
            self.confidence,
        )
        if not all(isfinite(value) for value in values):
            raise ValueError("Trajectory values must be finite")

        if self.timestamp < 0:
            raise ValueError("timestamp must be non-negative")
        if self.x2 <= self.x1 or self.y2 <= self.y1:
            raise ValueError("Bounding box must have positive dimensions")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")

    @property
    def center(self) -> tuple[float, float]:
        """Return the bounding-box center (x, y)."""
        return (
            (self.x1 + self.x2) / 2.0,
            (self.y1 + self.y2) / 2.0,
        )


class TrajectoryBuffer:
    """Store a bounded, frame-ordered history for each track ID."""

    def __init__(self, max_points: int = 100) -> None:
        if (
            isinstance(max_points, bool)
            or not isinstance(max_points, int)
            or max_points < 1
        ):
            raise ValueError("max_points must be a positive integer")

        self.max_points = max_points
        self._history: dict[int, Deque[TrajectoryPoint]] = {}

    def update(
        self,
        tracks: list[TrackRecord],
        frame_id: int,
    ) -> None:
        """Append observations returned for the current frame."""

        if isinstance(frame_id, bool) or not isinstance(frame_id, int):
            raise TypeError("frame_id must be an integer")
        if frame_id < 0:
            raise ValueError("frame_id must be non-negative")

        if not isinstance(tracks, list):
            raise TypeError("tracks must be a list")

        seen_ids: set[int] = set()

        for track in tracks:
            if not isinstance(track, TrackRecord):
                raise TypeError("Every item must be a TrackRecord")

            if track.track_id in seen_ids:
                raise ValueError(
                    f"Duplicate track ID {track.track_id} in frame {frame_id}"
                )
            seen_ids.add(track.track_id)

            history = self._history.get(track.track_id)

            if history:
                previous = history[-1]
                if frame_id <= previous.frame_id:
                    raise ValueError(
                        f"Frame IDs must increase for track {track.track_id}: "
                        f"{frame_id} <= {previous.frame_id}"
                    )
                if track.last_seen_timestamp < previous.timestamp:
                    raise ValueError(
                        f"Timestamp moved backwards for track {track.track_id}"
                    )

            point = TrajectoryPoint(
                timestamp=track.last_seen_timestamp,
                frame_id=frame_id,
                x1=track.x1,
                y1=track.y1,
                x2=track.x2,
                y2=track.y2,
                confidence=track.confidence,
            )

            if history is None:
                history = deque(maxlen=self.max_points)
                self._history[track.track_id] = history

            history.append(point)

    def get_history(self, track_id: int) -> list[TrajectoryPoint]:
        """Return a copy of one track's history."""
        history = self._history.get(track_id)
        return list(history) if history is not None else []

    def get_latest(self, track_id: int) -> TrajectoryPoint | None:
        """Return the latest observation, or None if unknown."""
        history = self._history.get(track_id)
        return history[-1] if history else None

    def get_all(self) -> dict[int, list[TrajectoryPoint]]:
        """Return a copy of all stored histories."""
        return {
            track_id: list(history)
            for track_id, history in self._history.items()
        }

    def remove(self, track_id: int) -> None:
        """Remove one track's stored history."""
        self._history.pop(track_id, None)

    def clear(self) -> None:
        """Remove all trajectory history."""
        self._history.clear()

    def __len__(self) -> int:
        """Return the number of track IDs with stored history."""
        return len(self._history)