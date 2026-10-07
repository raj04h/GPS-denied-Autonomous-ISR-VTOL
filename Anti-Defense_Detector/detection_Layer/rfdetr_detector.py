from pathlib import Path
from typing import List

import cv2
import numpy as np

from rfdetr import RFDETRMedium

from bbox_detection import bbox_structure
from detector_interface import DetectorInterface


COCO_CLASSES = [
    "person",
    "bicycle",
    "car",
    "motorcycle",
    "airplane",
    "bus",
    "train",
    "truck",
    "boat",
    "traffic light",
    "fire hydrant",
    "stop sign",
    "parking meter",
    "bench",
    "bird",
    "cat",
    "dog",
    "horse",
    "sheep",
    "cow",
    "elephant",
    "bear",
    "zebra",
    "giraffe",
    "backpack",
    "umbrella",
    "handbag",
    "tie",
    "suitcase",
    "frisbee",
    "skis",
    "snowboard",
    "sports ball",
    "kite",
    "baseball bat",
    "baseball glove",
    "skateboard",
    "surfboard",
    "tennis racket",
    "bottle",
    "wine glass",
    "cup",
    "fork",
    "knife",
    "spoon",
    "bowl",
    "banana",
    "apple",
    "sandwich",
    "orange",
    "broccoli",
    "carrot",
    "hot dog",
    "pizza",
    "donut",
    "cake",
    "chair",
    "couch",
    "potted plant",
    "bed",
    "dining table",
    "toilet",
    "tv",
    "laptop",
    "mouse",
    "remote",
    "keyboard",
    "cell phone",
    "microwave",
    "oven",
    "toaster",
    "sink",
    "refrigerator",
    "book",
    "clock",
    "vase",
    "scissors",
    "teddy bear",
    "hair drier",
    "toothbrush",
]


class RFDETRDetector(DetectorInterface):
    """
    RF-DETR detector adapter.

    Converts native RF-DETR output into the common Detection format.
    """

    def __init__(self, confidence_threshold: float = 0.5):
        self.confidence_threshold = confidence_threshold
        self.model = RFDETRMedium()

    def predict(self, image: np.ndarray) -> List[bbox_structure]:
        """
        Run RF-DETR inference.

        Args:
            image: Input image as a NumPy array.

        Returns:
            List of normalized Detection objects.
        """

        detections = self.model.predict(
            image,
            threshold=self.confidence_threshold,
        )

        results: List[bbox_structure] = []

        for class_id, confidence, bbox in zip(
            detections.class_id,
            detections.confidence,
            detections.xyxy,
        ):
            class_id = int(class_id)
            confidence = float(confidence)

            x1, y1, x2, y2 = map(float, bbox)

            if 0 <= class_id < len(COCO_CLASSES):
                source_class_name = COCO_CLASSES[class_id]
            else:
                source_class_name = f"UNKNOWN_COCO_CLASS_{class_id}"

            normalized_class_id, normalized_class_name = (
                self._normalize_class(source_class_name)
            )

            center_x = (x1 + x2) / 2.0
            center_y = (y1 + y2) / 2.0

            width = x2 - x1
            height = y2 - y1

            results.append(
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

                    source_model="RF-DETR-Medium",
                    source_class_id=class_id,
                    source_class_name=source_class_name,
                )
            )

        return results

    @staticmethod
    def _normalize_class(source_class_name: str):
        """
        Temporary RF-DETR/COCO → ISR taxonomy mapping.

        The final multi-model normalization layer will be
        implemented later in Step 6.
        """

        mapping = {
            "person": (0, "PERSON"),

            "car": (1, "VEHICLE"),
            "bus": (1, "VEHICLE"),
            "truck": (1, "VEHICLE"),

            "motorcycle": (3, "MOTORCYCLE"),

            "airplane": (5, "AIRCRAFT"),

            "bird": (6, "ANIMAL"),
            "cat": (6, "ANIMAL"),
            "dog": (6, "ANIMAL"),
            "horse": (6, "ANIMAL"),
            "sheep": (6, "ANIMAL"),
            "cow": (6, "ANIMAL"),
            "elephant": (6, "ANIMAL"),
            "bear": (6, "ANIMAL"),
            "zebra": (6, "ANIMAL"),
            "giraffe": (6, "ANIMAL"),

            "boat": (7, "BOAT"),
        }

        return mapping.get(
            source_class_name,
            (-1, "UNKNOWN"),
        )


if __name__ == "__main__":
    PROJECT_ROOT = Path(__file__).resolve().parents[2]

    input_image = PROJECT_ROOT / "data" / "input" / "test.jpg"

    image = cv2.imread(str(input_image))

    if image is None:
        raise FileNotFoundError(
            f"Could not load input image: {input_image}"
        )

    detector = RFDETRDetector(
        confidence_threshold=0.5
    )

    detections = detector.predict(image)

    print(f"Detections: {len(detections)}")

    for detection in detections:
        print(detection.to_dict())