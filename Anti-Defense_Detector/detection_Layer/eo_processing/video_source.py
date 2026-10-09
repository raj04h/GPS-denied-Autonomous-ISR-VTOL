
from dataclasses import dataclass
from pathlib import Path
from time import monotonic, sleep
from typing import Iterator, Optional, Union

import cv2
import numpy as np


@dataclass
class VideoFrame:
    frame_id: int
    timestamp: float
    image: np.ndarray
    width: int
    height: int


class VideoSource:
    VALID_SOURCE_TYPES = {"video", "camera", "rtsp"}

    def __init__(
        self,
        video_path: Optional[Union[str, int]] = None,
        loop: bool = False,
        start_frame: int = 0,
        max_frames: Optional[int] = None,
        *,
        source_type: str = "video",
        camera_index: int = 0,
        rtsp_url: Optional[str] = None,
        api_preference: int = cv2.CAP_ANY,
        open_timeout_ms: int = 10000,
        read_timeout_ms: int = 10000,
        reconnect_attempts: int = 0,
        reconnect_delay_sec: float = 1.0,
    ):
        source_type = source_type.lower().strip()

        if source_type not in self.VALID_SOURCE_TYPES:
            raise ValueError(
                f"Unsupported source_type: {source_type}. "
                f"Choose from {sorted(self.VALID_SOURCE_TYPES)}."
            )

        if max_frames is not None and int(max_frames) < 0:
            raise ValueError("max_frames must be >= 0 or None")

        self.source_type = source_type
        self.loop = bool(loop)
        self.start_frame = max(0, int(start_frame))
        self.max_frames = max_frames

        self.api_preference = api_preference
        self.open_timeout_ms = max(0, int(open_timeout_ms))
        self.read_timeout_ms = max(0, int(read_timeout_ms))
        self.reconnect_attempts = max(0, int(reconnect_attempts))
        self.reconnect_delay_sec = max(
            0.0, float(reconnect_delay_sec)
        )

        self.capture: Optional[cv2.VideoCapture] = None
        self._opened = False

        self._frame_id = 0
        self._frames_read = 0
        self._stream_started_at: Optional[float] = None
        self._last_timestamp = 0.0

        self._fps = 0.0
        self._frame_count = 0
        self._width = 0
        self._height = 0
        self._duration = 0.0

        self.video_path: Optional[Path] = None

        if source_type == "video":
            if video_path is None:
                raise ValueError(
                    "video_path is required for video mode"
                )

            self.video_path = Path(str(video_path))
            self.source = str(self.video_path)

            if not self.video_path.exists():
                raise FileNotFoundError(
                    f"Video file not found: {self.video_path}"
                )

            if not self.video_path.is_file():
                raise ValueError(
                    f"Video path is not a file: {self.video_path}"
                )

        elif source_type == "camera":
            if isinstance(video_path, int):
                camera_index = video_path

            if int(camera_index) < 0:
                raise ValueError("camera_index must be >= 0")

            self.camera_index = int(camera_index)
            self.source = self.camera_index

            if self.loop or self.start_frame > 0:
                raise ValueError(
                    "loop and start_frame are only supported "
                    "for recorded video"
                )

        else:
            candidate = (
                rtsp_url if rtsp_url is not None else video_path
            )

            if not isinstance(candidate, str) or not candidate.strip():
                raise ValueError(
                    "Provide rtsp_url for RTSP mode"
                )

            self.rtsp_url = candidate.strip()
            self.source = self.rtsp_url

            if self.loop or self.start_frame > 0:
                raise ValueError(
                    "loop and start_frame are only supported "
                    "for recorded video"
                )

    def _open_capture(self) -> cv2.VideoCapture:
        """Open the selected source, applying backend timeouts if supported."""

        params = []

        if self.open_timeout_ms > 0:
            params.extend([
                cv2.CAP_PROP_OPEN_TIMEOUT_MSEC,
                self.open_timeout_ms,
            ])

        if self.read_timeout_ms > 0:
            params.extend([
                cv2.CAP_PROP_READ_TIMEOUT_MSEC,
                self.read_timeout_ms,
            ])

        try:
            if params:
                capture = cv2.VideoCapture(
                    self.source,
                    self.api_preference,
                    params,
                )
            else:
                capture = cv2.VideoCapture(
                    self.source,
                    self.api_preference,
                )
        except (TypeError, cv2.error):
            # Some OpenCV backends do not accept timeout parameters.
            capture = cv2.VideoCapture(
                self.source,
                self.api_preference,
            )

        if not capture.isOpened():
            capture.release()
            raise RuntimeError(
                f"Unable to open {self.source_type} source: "
                f"{self.source}"
            )

        return capture

    def open(self) -> None:
        if self._opened:
            return

        self.capture = self._open_capture()

        self._fps = float(
            self.capture.get(cv2.CAP_PROP_FPS) or 0.0
        )
        self._frame_count = int(
            self.capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0
        )
        self._width = int(
            self.capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0
        )
        self._height = int(
            self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0
        )

        if not np.isfinite(self._fps) or self._fps < 0:
            self._fps = 0.0

        if self.source_type != "video":
            # Live-stream frame counts and duration are generally unknown.
            self._frame_count = 0
            self._duration = 0.0
        elif self._fps > 0 and self._frame_count > 0:
            self._duration = self._frame_count / self._fps

        if self.source_type == "video" and self.start_frame > 0:
            if (
                self._frame_count > 0
                and self.start_frame >= self._frame_count
            ):
                self.release()
                raise ValueError(
                    f"start_frame {self.start_frame} is beyond "
                    f"the video length ({self._frame_count} frames)"
                )

            success = self.capture.set(
                cv2.CAP_PROP_POS_FRAMES,
                self.start_frame,
            )

            if not success:
                self.release()
                raise RuntimeError(
                    f"Unable to seek to frame {self.start_frame}"
                )

            self._frame_id = self.start_frame
        else:
            self._frame_id = 0

        self._frames_read = 0
        self._last_timestamp = 0.0
        self._stream_started_at = monotonic()
        self._opened = True

    def read(self) -> Optional[VideoFrame]:
        if not self._opened:
            self.open()

        if self.capture is None:
            raise RuntimeError(
                "Video capture is not initialized"
            )

        if (
            self.max_frames is not None
            and self._frames_read >= self.max_frames
        ):
            return None

        success, frame = self.capture.read()

        if not success or frame is None:
            if self.source_type == "video" and self.loop:
                self._restart()
                success, frame = self.capture.read()

                if not success or frame is None:
                    return None

            elif (
                self.source_type in {"camera", "rtsp"}
                and self.reconnect_attempts > 0
            ):
                if not self._reconnect():
                    return None

                if self.capture is None:
                    return None

                success, frame = self.capture.read()

                if not success or frame is None:
                    return None

            else:
                return None

        frame_id = self._frame_id

        if self.source_type == "video":
            if self._fps > 0:
                timestamp = frame_id / self._fps
            else:
                timestamp = float(
                    self.capture.get(cv2.CAP_PROP_POS_MSEC) or 0.0
                ) / 1000.0
        else:
            timestamp = monotonic() - (
                self._stream_started_at or monotonic()
            )
            timestamp = max(timestamp, self._last_timestamp)

        height, width = frame.shape[:2]

        result = VideoFrame(
            frame_id=frame_id,
            timestamp=float(timestamp),
            image=frame,
            width=width,
            height=height,
        )

        self._frame_id += 1
        self._frames_read += 1
        self._last_timestamp = float(timestamp)
        self._width = width
        self._height = height

        return result

    def _reconnect(self) -> bool:
        """Retry opening a live source after a failed frame read."""

        for _ in range(self.reconnect_attempts):
            self.release()

            if self.reconnect_delay_sec > 0:
                sleep(self.reconnect_delay_sec)

            try:
                self.capture = self._open_capture()
                self._opened = True

                # Keep the live timestamp non-decreasing across reconnects.
                self._stream_started_at = (
                    monotonic() - self._last_timestamp
                )

                return True

            except RuntimeError:
                continue

        return False

    def frames(self) -> Iterator[VideoFrame]:
        while True:
            video_frame = self.read()

            if video_frame is None:
                break

            yield video_frame

    def _restart(self) -> None:
        if self.capture is None:
            raise RuntimeError(
                "Video capture is not initialized"
            )

        success = self.capture.set(
            cv2.CAP_PROP_POS_FRAMES,
            0,
        )

        if not success:
            raise RuntimeError(
                f"Unable to restart video: {self.video_path}"
            )

        self._frame_id = 0

    def release(self) -> None:
        if self.capture is not None:
            self.capture.release()

        self.capture = None
        self._opened = False

    def is_opened(self) -> bool:
        return self._opened

    def get_fps(self) -> float:
        return self._fps

    def get_frame_count(self) -> int:
        return self._frame_count

    def get_width(self) -> int:
        return self._width

    def get_height(self) -> int:
        return self._height

    def get_duration(self) -> float:
        return self._duration

    def get_path(self) -> str:
        """Return the configured source identifier."""
        return str(self.source)

    def __iter__(self) -> Iterator[VideoFrame]:
        return self.frames()

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.release()
