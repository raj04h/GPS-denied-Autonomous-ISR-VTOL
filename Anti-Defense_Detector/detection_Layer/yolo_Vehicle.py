from pathlib import Path
from typing import List

import cv2
import numpy as np

from ultralytics import YOLO

from bbox_detection import bbox_structure
from detector_interface import DetectorInterface


# Native classes from spencercdz/YOLOv8m_defence
DEFENCE_CLASSES = {
    0: "Cargo Aircraft",
    1: "Commercial Aircraft",
    2: "Drone",
    3: "Fighter Jet",
    4: "Fighter Plane",
    5: "Helicopter",
    6: "Light Aircraft",
    7: "Missile",
    8: "Truck",
    9: "Car",
    10: "Tank",
    11: "Bus",
    12: "Van",
    13: "Cargo Ship",
    14: "Yacht",
    15: "Cruise Ship",
    16: "Warship",
    17: "Sailboat",
}


class YOLOv8DefenceDetector(DetectorInterface):

    def __init__(
        self,
        weights_path: str,
        confidence_threshold: float = 0.5,
    ):
        self.confidence_threshold = confidence_threshold
        self.weights_path = weights_path

        self.model = YOLO(weights_path)

    def predict(self, image: np.ndarray) -> List[bbox_structure]:
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

                class_id = int(box.cls[0].item())
                confidence = float(box.conf[0].item())

                x1, y1, x2, y2 = (
                    box.xyxy[0]
                    .cpu()
                    .numpy()
                    .astype(float)
                )

                source_class_name = DEFENCE_CLASSES.get(
                    class_id,
                    f"UNKNOWN_CLASS_{class_id}",
                )

                center_x = (x1 + x2) / 2.0
                center_y = (y1 + y2) / 2.0

                width = x2 - x1
                height = y2 - y1

                normalized_class_id, normalized_class_name = (
                    self._temporary_normalize(
                        source_class_name
                    )
                )

                detections.append(
                    bbox_structure(
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
                        source_class_id=class_id,
                        source_class_name=source_class_name,
                    )
                )

        return detections

    @staticmethod
    def _temporary_normalize(source_class_name: str):
        mapping = {

            # Air
            "Drone": (4, "DRONE"),

            "Helicopter": (5, "AIRCRAFT"),
            "Cargo Aircraft": (5, "AIRCRAFT"),
            "Commercial Aircraft": (5, "AIRCRAFT"),
            "Fighter Jet": (5, "AIRCRAFT"),
            "Fighter Plane": (5, "AIRCRAFT"),
            "Light Aircraft": (5, "AIRCRAFT"),

            # Ground vehicles
            "Truck": (1, "VEHICLE"),
            "Car": (1, "VEHICLE"),
            "Bus": (1, "VEHICLE"),
            "Van": (1, "VEHICLE"),

            # Maritime
            "Cargo Ship": (7, "BOAT"),
            "Yacht": (7, "BOAT"),
            "Cruise Ship": (7, "BOAT"),
            "Warship": (7, "BOAT"),
            "Sailboat": (7, "BOAT"),
        }

        return mapping.get(
            source_class_name,
            (-1, "UNKNOWN"),
        )


if __name__ == "__main__":

    PROJECT_ROOT = Path(__file__).resolve().parents[2]

    weights_path = (
        PROJECT_ROOT
        / "models"
        / "yolov8m_defence"
        / "yolov8m_defence.pt"
    )

    input_image = (
        PROJECT_ROOT
        / "data"
        / "input"
        / "test.jpg"
    )

    if not weights_path.exists():
        raise FileNotFoundError(
            f"YOLOv8m Defence weights not found:\n"
            f"{weights_path}"
        )

    image = cv2.imread(str(input_image))

    if image is None:
        raise FileNotFoundError(
            f"Could not load input image:\n"
            f"{input_image}"
        )

    detector = YOLOv8DefenceDetector(
        weights_path=str(weights_path),
        confidence_threshold=0.5,
    )

    detections = detector.predict(image)

    print(f"Detections: {len(detections)}")

    for detection in detections:
        print(detection.to_dict())