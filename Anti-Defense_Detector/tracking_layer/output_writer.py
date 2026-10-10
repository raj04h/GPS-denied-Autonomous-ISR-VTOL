# Tracking results to JSONL
"""Write tracking results to a JSONL file."""

import json
import math
from pathlib import Path
from typing import Any

from .tracking_types import FrameDetections, TrackRecord


class TrackingOutputWriter:
    """Serialize tracking results as one JSON object per frame."""

    def __init__(self, output_path: str | Path) -> None:
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        self._file = self.output_path.open(
            "w",
            encoding="utf-8",
        )
        self._closed = False

    def write_frame(
        self,
        frame: FrameDetections,
        tracks: list[TrackRecord],
    ) -> None:
        """Write one frame and its tracks."""

        if self._closed:
            raise ValueError("Cannot write to a closed output file")

        if not isinstance(frame, FrameDetections):
            raise TypeError("frame must be a FrameDetections instance")

        if not isinstance(tracks, list):
            raise TypeError("tracks must be a list")

        if not all(isinstance(track, TrackRecord) for track in tracks):
            raise TypeError("Every item in tracks must be a TrackRecord")

        record: dict[str, Any] = {
            "frame_id": frame.frame_id,
            "timestamp": frame.timestamp,
            "width": frame.width,
            "height": frame.height,
            "track_count": len(tracks),
            "tracks": [
                {
                    "track_id": track.track_id,
                    "class_id": track.class_id,
                    "class_name": track.class_name,
                    "confidence": track.confidence,
                    "bbox": {
                        "x1": track.x1,
                        "y1": track.y1,
                        "x2": track.x2,
                        "y2": track.y2,
                    },
                    "first_seen_timestamp": track.first_seen_timestamp,
                    "last_seen_timestamp": track.last_seen_timestamp,
                    "track_age": track.track_age,
                    "status": track.status.value,
                }
                for track in tracks
            ],
        }

        # Reject NaN and Infinity so the output remains valid JSON.
        line = json.dumps(
            record,
            ensure_ascii=False,
            allow_nan=False,
        )

        self._file.write(line + "\n")
        self._file.flush()

    def close(self) -> None:
        """Close the output file safely."""
        if not self._closed:
            self._file.close()
            self._closed = True

    def __enter__(self) -> "TrackingOutputWriter":
        if self._closed:
            raise ValueError("Cannot reopen a closed writer")
        return self

    def __exit__(
        self,
        exc_type: Any,
        exc_value: Any,
        traceback: Any,
    ) -> None:
        self.close()
