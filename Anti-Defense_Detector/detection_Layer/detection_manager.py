from typing import Dict, List, Optional
import time

import numpy as np
import cv2

from bbox_detection import bbox_structure
from detector_interface import DetectorInterface
from detection_fusion import DetectionFusion


class DetectionManager:

    def __init__(
        self,
        detectors: Dict[str, DetectorInterface],
        fusion: Optional[DetectionFusion] = None,
    ):
        if not detectors:
            raise ValueError("DetectionManager requires at least one detector.")

        self.detectors = detectors

        self.fusion = (
            fusion
            if fusion is not None
            else DetectionFusion(
                iou_threshold=0.50,
                confidence_threshold=0.25,
            )
        )

        self.last_raw_detections: List[bbox_structure] = []
        self.last_fused_detections: List[bbox_structure] = []

    def predict(self, image: np.ndarray) -> List[bbox_structure]:
        """Run all configured detectors and fuse their detections."""

        self._validate_image(image)

        all_detections: List[bbox_structure] = []

        for detector_name, detector in self.detectors.items():
            start_time = time.perf_counter()

            try:
                detections = detector.predict(image)

                if detections is None:
                    detections = []

                if not isinstance(detections, list):
                    detections = list(detections)

                elapsed_ms = (time.perf_counter() - start_time) * 1000.0

                print(
                    f"[DetectionManager] "
                    f"{detector_name:<18} "
                    f"{elapsed_ms:8.2f} ms | "
                    f"detections={len(detections)}"
                )

                all_detections.extend(detections)

            except Exception as error:
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0

                print(
                    f"[DetectionManager] "
                    f"{detector_name:<18} "
                    f"FAILED after {elapsed_ms:.2f} ms"
                )
                print(f"Error: {error}")

        self.last_raw_detections = all_detections

        fused_detections = self.fusion.fuse(all_detections)
        self.last_fused_detections = fused_detections

        conflicts = self.fusion.get_conflicts()

        if conflicts:
            print("\n[DetectionManager] Detection conflicts:")
            for conflict in conflicts:
                print(
                    f"  {conflict['class_a']} "
                    f"{conflict['confidence_a']:.2f} "
                    f"({conflict['source_a']}) <-> "
                    f"{conflict['class_b']} "
                    f"{conflict['confidence_b']:.2f} "
                    f"({conflict['source_b']}) | "
                    f"IoU={conflict['iou']:.2f}"
                )

        print(
            f"[DetectionManager] "
            f"raw={len(all_detections)} | "
            f"fused={len(fused_detections)}"
        )

        return fused_detections

    @staticmethod
    def _validate_image(image: np.ndarray) -> None:
        if image is None:
            raise ValueError("Input image is None.")

        if not isinstance(image, np.ndarray):
            raise TypeError("Input image must be a numpy.ndarray.")

        if image.size == 0:
            raise ValueError("Input image is empty.")

        if image.ndim not in (2, 3):
            raise ValueError(
                f"Input image must have 2 or 3 dimensions, got {image.ndim}."
            )

    def get_detection_conflicts(self):
        return self.fusion.get_conflicts()

    def get_raw_detections(self) -> List[bbox_structure]:
        return self.last_raw_detections

    def get_fused_detections(self) -> List[bbox_structure]:
        return self.last_fused_detections

    def get_detector_names(self) -> List[str]:
        return list(self.detectors.keys())


def draw_detections(
    image: np.ndarray,
    detections: List[bbox_structure],
) -> np.ndarray:
    """Draw fused detections for V1 EO/RGB validation output."""

    if image is None:
        raise ValueError("Input image is None.")

    output = image.copy()

    for detection in detections:
        x1 = int(detection.x1)
        y1 = int(detection.y1)
        x2 = int(detection.x2)
        y2 = int(detection.y2)

        if detection.class_name and detection.class_name != "UNKNOWN":
            class_name = detection.class_name
        elif (
            detection.source_class_name
            and detection.source_class_name != "UNKNOWN"
        ):
            class_name = detection.source_class_name
        else:
            class_name = "UNKNOWN"

        label = f"{class_name} {detection.confidence:.2f}"

        cv2.rectangle(
            output,
            (x1, y1),
            (x2, y2),
            (0, 255, 0),
            2,
        )

        text_y = max(y1 - 10, 20)

        cv2.putText(
            output,
            label,
            (x1, text_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 0),
            2,
        )

    return output