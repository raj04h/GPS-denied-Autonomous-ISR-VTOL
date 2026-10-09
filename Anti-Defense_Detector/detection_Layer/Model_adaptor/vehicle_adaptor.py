from pathlib import Path
from typing import List

import numpy as np
from ultralytics import YOLO

from bbox_detection import bbox_structure
from detector_interface import DetectorInterface
from class_map import get_class_id


class VEHICLEDETECTOR(DetectorInterface):

    def __init__(
        self,
        weights_path: str,
        confidence_threshold: float = 0.5,
    ):
        self.confidence_threshold = confidence_threshold

        self.weights_path = Path(
            weights_path
        )

        if not self.weights_path.exists():
            raise FileNotFoundError(
                f"YOLOv8m Defence weights not found:\n"
                f"{self.weights_path}"
            )

        self.model = YOLO(
            str(self.weights_path)
        )

    def predict(
        self,
        image: np.ndarray,
    ) -> List[bbox_structure]:

        results = self.model.predict(
            source=image,
            conf=self.confidence_threshold,
            verbose=False,
        )

        detections: List[bbox_structure] = []

        for result in results:

            if result.boxes is None:
                continue

            for box in result.boxes:

                source_class_id = int(
                    box.cls[0].item()
                )

                confidence = float(
                    box.conf[0].item()
                )

                source_class_name = str(
                    self.model.names.get(
                        source_class_id,
                        f"UNKNOWN_CLASS_{source_class_id}",
                    )
                ).strip()

                x1, y1, x2, y2 = (
                    box.xyxy[0]
                    .cpu()
                    .numpy()
                    .astype(float)
                )

                center_x = (
                    x1 + x2
                ) / 2.0

                center_y = (
                    y1 + y2
                ) / 2.0

                width = x2 - x1
                height = y2 - y1

                normalized_class_name = (
                    self._normalize_class(
                        source_class_name
                    )
                )

                if normalized_class_name == "UNKNOWN":
                    normalized_class_id = -1
                else:
                    normalized_class_id = get_class_id(
                        normalized_class_name
                    )

                detection = bbox_structure(
                    class_id=normalized_class_id,
                    class_name=normalized_class_name,

                    confidence=confidence,

                    x1=x1,
                    y1=y1,
                    x2=x2,
                    y2=y2,

                    center_x=center_x,
                    center_y=center_y,

                    width=width,
                    height=height,

                    source_model="YOLOv8m_Defence",
                    source_class_id=source_class_id,
                    source_class_name=source_class_name,
                )

                detections.append(
                    detection
                )

        return detections

    @staticmethod
    def _normalize_class(
        source_class_name: str,
    ) -> str:

        source_class_name = (
            source_class_name
            .strip()
            .lower()
        )

        mapping = {

            # Air
            "drone": "DRONE",

            "helicopter": "AIRCRAFT",
            "cargo aircraft": "AIRCRAFT",
            "commercial aircraft": "AIRCRAFT",
            "fighter jet": "AIRCRAFT",
            "fighter plane": "AIRCRAFT",
            "light aircraft": "AIRCRAFT",

            # Ground vehicles
            "truck": "VEHICLE",
            "car": "VEHICLE",
            "bus": "VEHICLE",
            "van": "VEHICLE",

            # Heavy vehicles
            "tank": "HEAVY_VEHICLE",

            # Maritime
            "cargo ship": "BOAT",
            "yacht": "BOAT",
            "cruise ship": "BOAT",
            "warship": "BOAT",
            "sailboat": "BOAT",
        }

        return mapping.get(
            source_class_name,
            "UNKNOWN",
        )