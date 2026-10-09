from pathlib import Path
from typing import List

import numpy as np
from ultralytics import YOLO

from bbox_detection import bbox_structure
from detector_interface import DetectorInterface


class WEAPONDETECTOR(DetectorInterface):

    def __init__(
        self,
        weights_path: str,
        confidence_threshold: float = 0.35,
        image_size: int = 1024,
    ):
        self.confidence_threshold = confidence_threshold
        self.image_size = image_size

        self.weights_path = Path(
            weights_path
        )

        if not self.weights_path.exists():
            raise FileNotFoundError(
                f"YOLO26x weapon model not found:\n"
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
            imgsz=self.image_size,
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

                x1, y1, x2, y2 = map(
                    float,
                    box.xyxy[0].cpu().numpy(),
                )

                source_class_name = str(
                    self.model.names[
                        source_class_id
                    ]
                ).strip()

                center_x = (
                    x1 + x2
                ) / 2.0

                center_y = (
                    y1 + y2
                ) / 2.0

                width = x2 - x1
                height = y2 - y1

                detection = bbox_structure(
                    class_id=-1,
                    class_name="UNKNOWN",

                    confidence=confidence,

                    x1=x1,
                    y1=y1,
                    x2=x2,
                    y2=y2,

                    center_x=center_x,
                    center_y=center_y,

                    width=width,
                    height=height,

                    source_model="YOLO26x-Weapon",
                    source_class_id=source_class_id,
                    source_class_name=source_class_name,
                )

                detections.append(
                    detection
                )

        return detections