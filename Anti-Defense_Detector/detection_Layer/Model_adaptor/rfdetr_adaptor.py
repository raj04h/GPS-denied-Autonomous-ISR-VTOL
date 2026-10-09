from typing import List

import numpy as np

from rfdetr import RFDETRMedium

from bbox_detection import bbox_structure
from detector_interface import DetectorInterface
from class_map import get_class_id


class RFDETRDetector(DetectorInterface):

    def __init__(
        self,
        confidence_threshold: float = 0.5,
    ):
        self.confidence_threshold = confidence_threshold
        self.model = RFDETRMedium()

    def predict(
        self,
        image: np.ndarray,
    ) -> List[bbox_structure]:

        detections = self.model.predict(
            image,
            threshold=self.confidence_threshold,
        )

        class_names = detections.data.get(
            "class_name"
        )

        if class_names is None:
            raise RuntimeError(
                "RF-DETR detection result does not contain "
                "'class_name' metadata."
            )

        results: List[bbox_structure] = []

        for index in range(
            len(detections.class_id)
        ):

            source_class_id = int(
                detections.class_id[index]
            )

            confidence = float(
                detections.confidence[index]
            )

            x1, y1, x2, y2 = map(
                float,
                detections.xyxy[index],
            )

            source_class_name = str(
                class_names[index]
            ).strip()

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

            center_x = (x1 + x2) / 2.0
            center_y = (y1 + y2) / 2.0

            width = x2 - x1
            height = y2 - y1

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

                source_model="RF-DETR-Medium",
                source_class_id=source_class_id,
                source_class_name=source_class_name,
            )

            results.append(detection)

        return results

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
            "person": "PERSON",

            "car": "VEHICLE",
            "bus": "VEHICLE",
            "truck": "VEHICLE",

            "motorcycle": "MOTORCYCLE",

            "airplane": "AIRCRAFT",

            "bird": "ANIMAL",
            "cat": "ANIMAL",
            "dog": "ANIMAL",
            "horse": "ANIMAL",
            "sheep": "ANIMAL",
            "cow": "ANIMAL",
            "elephant": "ANIMAL",
            "bear": "ANIMAL",
            "zebra": "ANIMAL",
            "giraffe": "ANIMAL",

            "boat": "BOAT",
        }

        return mapping.get(
            source_class_name,
            "UNKNOWN",
        )