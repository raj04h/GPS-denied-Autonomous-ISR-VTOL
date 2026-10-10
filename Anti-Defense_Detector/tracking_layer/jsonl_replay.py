
"""Read and replay P1 detection records from a JSONL file."""

import json
from pathlib import Path
from typing import Iterator

from .detection_adapter import parse_frame_packet
from .tracking_types import FrameDetections


class JSONLReplay:
    """Replay valid detection frames from a P1 JSONL file."""

    def __init__(self, file_path: str | Path) -> None:
        self.file_path = Path(file_path)

        if not self.file_path.is_file():
            raise FileNotFoundError(
                f"Detection JSONL file not found: {self.file_path}"
            )

    def __iter__(self) -> Iterator[FrameDetections]:
        """Yield valid frames in file order."""

        with self.file_path.open("r", encoding="utf-8") as file:
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

                try:
                    frame = parse_frame_packet(record)
                except (TypeError, ValueError) as exc:
                    raise ValueError(
                        f"Invalid detection record at line "
                        f"{line_number}: {exc}"
                    ) from exc

                yield frame

    def read_all(self) -> list[FrameDetections]:
        """Load all valid frames into memory."""
        return list(iter(self))
