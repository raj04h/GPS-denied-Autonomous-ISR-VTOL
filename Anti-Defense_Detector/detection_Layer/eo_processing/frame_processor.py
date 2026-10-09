from dataclasses import dataclass

import cv2
import numpy as np

from .video_source import VideoFrame


@dataclass
class ProcessedFrame:
    frame_id: int
    timestamp: float
    image: np.ndarray
    width: int
    height: int
    channels: int


class FrameProcessor:
    def __init__(
        self,
        expected_channels: int = 3,
        convert_gray_to_bgr: bool = True,
        ensure_contiguous: bool = True,
    ):
        if expected_channels not in (1, 3, 4):
            raise ValueError(
                "expected_channels must be 1, 3, or 4"
            )

        self.expected_channels = expected_channels
        self.convert_gray_to_bgr = convert_gray_to_bgr
        self.ensure_contiguous = ensure_contiguous

    def process(
        self,
        video_frame: VideoFrame,
    ) -> ProcessedFrame:
        if not isinstance(video_frame, VideoFrame):
            raise TypeError(
                "process() expects a VideoFrame"
            )

        image = video_frame.image

        if not isinstance(image, np.ndarray):
            raise TypeError(
                "VideoFrame.image must be a numpy array"
            )

        if image.size == 0:
            raise ValueError(
                "Video frame contains an empty image"
            )

        if image.ndim == 2:
            if not self.convert_gray_to_bgr:
                raise ValueError(
                    "Grayscale frame received but "
                    "convert_gray_to_bgr is disabled"
                )

            image = cv2.cvtColor(
                image,
                cv2.COLOR_GRAY2BGR,
            )

        elif image.ndim == 3:
            channels = image.shape[2]

            if channels == 1:
                if self.convert_gray_to_bgr:
                    image = cv2.cvtColor(
                        image,
                        cv2.COLOR_GRAY2BGR,
                    )
                else:
                    raise ValueError(
                        "Single-channel frame received"
                    )

            elif channels not in (3, 4):
                raise ValueError(
                    f"Unsupported channel count: {channels}"
                )

        else:
            raise ValueError(
                f"Unsupported frame dimensions: {image.ndim}"
            )

        if image.dtype != np.uint8:
            image = self._convert_to_uint8(image)

        if self.ensure_contiguous:
            image = np.ascontiguousarray(image)

        height, width = image.shape[:2]
        channels = (
            1
            if image.ndim == 2
            else image.shape[2]
        )

        return ProcessedFrame(
            frame_id=video_frame.frame_id,
            timestamp=video_frame.timestamp,
            image=image,
            width=width,
            height=height,
            channels=channels,
        )

    @staticmethod
    def _convert_to_uint8(
        image: np.ndarray,
    ) -> np.ndarray:
        if np.issubdtype(image.dtype, np.floating):
            image_min = float(np.min(image))
            image_max = float(np.max(image))

            if 0.0 <= image_min and image_max <= 1.0:
                image = image * 255.0

            image = np.clip(
                image,
                0.0,
                255.0,
            )

            return image.astype(
                np.uint8
            )

        if np.issubdtype(image.dtype, np.integer):
            return np.clip(
                image,
                0,
                255,
            ).astype(np.uint8)

        raise TypeError(
            f"Unsupported image dtype: {image.dtype}"
        )