from pathlib import Path
import json
import time
from typing import Optional, Union

import cv2

from .video_source import VideoSource
from .frame_processor import FrameProcessor
from detection_manager import DetectionManager, draw_detections


class EOPerceptionPipeline:
    def __init__(
        self,
        video_path: Optional[Union[str, int]],
        detection_manager: DetectionManager,
        output_video_path: Optional[Union[str, Path]],
        output_log_path: Optional[Union[str, Path]],
        max_frames: Optional[int] = None,
        display: bool = True,
        *,
        source_type: str = "video",
        camera_index: int = 0,
        rtsp_url: Optional[str] = None,
        reconnect_attempts: int = 0,
        reconnect_delay_sec: float = 1.0,
    ):
        self.video_path = video_path
        self.source_type = source_type
        self.camera_index = camera_index
        self.rtsp_url = rtsp_url
        self.reconnect_attempts = reconnect_attempts
        self.reconnect_delay_sec = reconnect_delay_sec

        self.detection_manager = detection_manager
        self.output_video_path = (
            Path(output_video_path) if output_video_path else None
        )
        self.output_log_path = Path(output_log_path) if output_log_path else None
        self.max_frames = max_frames
        self.display = display

        self.frame_processor = FrameProcessor()
        self.writer = None
        self._reset_statistics()

    def _create_source(self) -> VideoSource:
        return VideoSource(
            video_path=self.video_path,
            source_type=self.source_type,
            camera_index=self.camera_index,
            rtsp_url=self.rtsp_url,
            max_frames=self.max_frames,
            reconnect_attempts=self.reconnect_attempts,
            reconnect_delay_sec=self.reconnect_delay_sec,
        )

    def run(self) -> dict:
        self._reset_statistics()
        source = self._create_source()
        wall_start = time.perf_counter()
        stop_requested = False

        if self.output_video_path:
            self.output_video_path.parent.mkdir(parents=True, exist_ok=True)
        if self.output_log_path:
            self.output_log_path.parent.mkdir(parents=True, exist_ok=True)

        log_context = (
            self.output_log_path.open("w", encoding="utf-8")
            if self.output_log_path
            else None
        )

        try:
            source.open()

            while True:
                video_frame = source.read()
                if video_frame is None:
                    break

                self.total_frames += 1
                try:
                    processed_frame = self.frame_processor.process(video_frame)
                    inference_start = time.perf_counter()
                    fused_detections = self.detection_manager.predict(
                        processed_frame.image
                    )
                    inference_time = time.perf_counter() - inference_start
                    self._update_statistics(inference_time)

                    raw_detections = self.detection_manager.get_raw_detections()
                    conflicts = self.detection_manager.get_detection_conflicts()
                    self.total_detections += len(fused_detections)
                    self.total_conflicts += len(conflicts)

                    output_frame = draw_detections(
                        processed_frame.image.copy(), fused_detections
                    )
                    elapsed = time.perf_counter() - wall_start
                    effective_fps = (
                        self.processed_frames + 1
                    ) / elapsed if elapsed > 0 else 0.0

                    self._draw_frame_info(
                        output_frame,
                        processed_frame.frame_id,
                        processed_frame.timestamp,
                        len(fused_detections),
                        inference_time,
                        effective_fps,
                    )

                    if self.output_video_path and self.writer is None:
                        self._initialize_writer(source, output_frame)
                    if self.writer is not None:
                        self.writer.write(output_frame)

                    if log_context is not None:
                        self._write_log(
                            log_context,
                            processed_frame,
                            raw_detections,
                            fused_detections,
                            conflicts,
                            inference_time,
                        )

                    self.processed_frames += 1

                    if self.display:
                        cv2.imshow("EO Perception V1", output_frame)
                        key = cv2.waitKey(1) & 0xFF
                        if key in (ord("q"), 27):
                            stop_requested = True
                            break

                except Exception as error:
                    self.failed_frames += 1
                    print(
                        f"[EO Pipeline] Frame {video_frame.frame_id} failed: {error}"
                    )
                    if log_context is not None:
                        self._write_error(
                            log_context,
                            video_frame.frame_id,
                            video_frame.timestamp,
                            error,
                        )

        finally:
            source.release()
            self._release_writer()
            if log_context is not None:
                log_context.close()
            if self.display:
                cv2.destroyAllWindows()

        wall_time = time.perf_counter() - wall_start
        summary = self._build_summary(source, wall_time)
        if stop_requested:
            summary["stopped_by_user"] = True
        return summary

    def _initialize_writer(self, source: VideoSource, frame) -> None:
        height, width = frame.shape[:2]
        fps = source.get_fps()

        if width <= 0 or height <= 0:
            raise RuntimeError(f"Invalid frame resolution: {width}x{height}")
        if fps <= 0:
            fps = 30.0

        self.output_video_path.parent.mkdir(parents=True, exist_ok=True)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self.writer = cv2.VideoWriter(
            str(self.output_video_path), fourcc, fps, (width, height)
        )
        if not self.writer.isOpened():
            self.writer.release()
            self.writer = None
            raise RuntimeError(
                f"Could not create output video: {self.output_video_path}"
            )

    def _release_writer(self) -> None:
        if self.writer is not None:
            self.writer.release()
            self.writer = None

    @staticmethod
    def _draw_frame_info(
        frame,
        frame_id: int,
        timestamp: float,
        detection_count: int,
        inference_time: float,
        effective_fps: float,
    ) -> None:
        lines = [
            f"Frame: {frame_id}  Time: {timestamp:.2f}s",
            f"Detections: {detection_count}  Inference: {inference_time * 1000:.1f} ms",
            f"Processing FPS: {effective_fps:.2f}  Q/Esc: quit",
        ]
        y = 25
        for line in lines:
            cv2.putText(
                frame, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX,
                0.58, (255, 255, 255), 2, cv2.LINE_AA
            )
            y += 24

    @staticmethod
    def _serialize_detection(detection) -> dict:
        return {
            "class_id": int(detection.class_id),
            "class_name": str(detection.class_name),
            "confidence": float(detection.confidence),
            "x1": float(detection.x1),
            "y1": float(detection.y1),
            "x2": float(detection.x2),
            "y2": float(detection.y2),
            "center_x": float(detection.center_x),
            "center_y": float(detection.center_y),
            "width": float(detection.width),
            "height": float(detection.height),
            "source_model": str(getattr(detection, "source_model", "UNKNOWN")),
            "source_class_id": int(getattr(detection, "source_class_id", -1)),
            "source_class_name": str(getattr(detection, "source_class_name", "")),
        }

    def _write_log(
        self,
        log_file,
        processed_frame,
        raw_detections,
        fused_detections,
        conflicts,
        inference_time: float,
    ) -> None:
        record = {
            "frame_id": processed_frame.frame_id,
            "timestamp": processed_frame.timestamp,
            "width": processed_frame.width,
            "height": processed_frame.height,
            "inference_time_ms": inference_time * 1000.0,
            "raw_detections": [
                self._serialize_detection(item) for item in raw_detections
            ],
            "fused_detections": [
                self._serialize_detection(item) for item in fused_detections
            ],
            "conflicts": conflicts,
        }
        log_file.write(json.dumps(record, separators=(",", ":"), default=str) + "\n")
        log_file.flush()

    @staticmethod
    def _write_error(log_file, frame_id, timestamp, error) -> None:
        record = {
            "frame_id": frame_id,
            "timestamp": timestamp,
            "error": str(error),
        }
        log_file.write(json.dumps(record, separators=(",", ":")) + "\n")
        log_file.flush()

    def _update_statistics(self, inference_time: float) -> None:
        self.total_inference_time += inference_time
        if self.min_inference_time is None or inference_time < self.min_inference_time:
            self.min_inference_time = inference_time
        if self.max_inference_time is None or inference_time > self.max_inference_time:
            self.max_inference_time = inference_time

    def _reset_statistics(self) -> None:
        self.total_frames = 0
        self.processed_frames = 0
        self.failed_frames = 0
        self.total_inference_time = 0.0
        self.min_inference_time = None
        self.max_inference_time = None
        self.total_detections = 0
        self.total_conflicts = 0

    def _build_summary(self, source: VideoSource, wall_time: float) -> dict:
        average_inference_ms = (
            self.total_inference_time / self.processed_frames * 1000.0
            if self.processed_frames else 0.0
        )
        effective_fps = self.processed_frames / wall_time if wall_time > 0 else 0.0

        return {
            "source_type": self.source_type,
            "video_path": source.get_path(),
            "output_video": str(self.output_video_path) if self.output_video_path else None,
            "output_log": str(self.output_log_path) if self.output_log_path else None,
            "input_fps": source.get_fps(),
            "input_frame_count": source.get_frame_count(),
            "input_width": source.get_width(),
            "input_height": source.get_height(),
            "total_frames": self.total_frames,
            "processed_frames": self.processed_frames,
            "failed_frames": self.failed_frames,
            "total_detections": self.total_detections,
            "total_conflicts": self.total_conflicts,
            "wall_time_sec": wall_time,
            "average_inference_ms": average_inference_ms,
            "min_inference_ms": self.min_inference_time * 1000.0 if self.min_inference_time is not None else 0.0,
            "max_inference_ms": self.max_inference_time * 1000.0 if self.max_inference_time is not None else 0.0,
            "effective_fps": effective_fps,
        }