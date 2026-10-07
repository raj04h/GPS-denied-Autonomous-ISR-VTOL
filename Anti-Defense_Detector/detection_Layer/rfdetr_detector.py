import json
import time
from pathlib import Path
from typing import List
import numpy as np
import cv2
import supervision as sv

from rfdetr import RFDETRMedium
from rfdetr.assets.coco_classes import COCO_CLASSES

from detection import Detection
from detector_interface import DetectorInterface



# ============================================================
# Configuration
# ============================================================

# Project root:
# Autonomous-ISR-VTOL/
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Input / output directories
INPUT_DIR = PROJECT_ROOT / "data" / "input"
OUTPUT_DIR = PROJECT_ROOT / "data" / "output"

# Files
INPUT_IMAGE = INPUT_DIR / "test.jpg"
OUTPUT_IMAGE = OUTPUT_DIR / "rfdetr_result.jpg"
OUTPUT_JSON = OUTPUT_DIR / "rfdetr_detections.json"

# Detection threshold
CONFIDENCE_THRESHOLD = 0.5


# ============================================================
# RF-DETR Detector
# ============================================================
class RFDETRDetector(DetectorInterface):

    def __init__(self, threshold: float = 0.5):

        self.threshold = threshold

        print("[INFO] Loading RF-DETR-Medium...")

        self.model = RFDETRMedium()

        print("[INFO] RF-DETR-Medium loaded.")


    def predict(self, image) -> List[Detection]:

        start_time = time.perf_counter()

        detections = self.model.predict(
            image,
            threshold=self.threshold
        )

        inference_time = time.perf_counter() - start_time

        print(
            f"[INFO] Inference time: "
            f"{inference_time * 1000:.2f} ms"
        )

        results = []

        for class_id, confidence, bbox in zip(
            detections.class_id,
            detections.confidence,
            detections.xyxy
        ):

            class_id = int(class_id)
            confidence = float(confidence)

            x1, y1, x2, y2 = map(float, bbox)

            width = x2 - x1
            height = y2 - y1

            center_x = x1 + width / 2.0
            center_y = y1 + height / 2.0

            class_name = COCO_CLASSES[class_id]

            detection = Detection(
                class_id=class_id,
                class_name=class_name,
                confidence=confidence,

                x1=x1,
                y1=y1,
                x2=x2,
                y2=y2,

                center_x=center_x,
                center_y=center_y,

                width=width,
                height=height,
            )

            results.append(detection)

        return results
# ============================================================
# Visualization
# ============================================================

def annotate_image(image, detections: List[Detection]):

    if not detections:
        return image

    xyxy = np.array(
        [
            [
                detection.x1,
                detection.y1,
                detection.x2,
                detection.y2,
            ]
            for detection in detections
        ],
        dtype=np.float32,
    )

    class_ids = np.array(
        [
            detection.class_id
            for detection in detections
        ],
        dtype=np.int32,
    )

    confidences = np.array(
        [
            detection.confidence
            for detection in detections
        ],
        dtype=np.float32,
    )

    sv_detections = sv.Detections(
        xyxy=xyxy,
        class_id=class_ids,
        confidence=confidences,
    )

    labels = [
        f"{detection.class_name} "
        f"{detection.confidence:.2f}"
        for detection in detections
    ]

    box_annotator = sv.BoxAnnotator()

    label_annotator = sv.LabelAnnotator()

    annotated = box_annotator.annotate(
        scene=image.copy(),
        detections=sv_detections,
    )

    annotated = label_annotator.annotate(
        scene=annotated,
        detections=sv_detections,
        labels=labels,
    )

    return annotated

# ============================================================
# JSON output
# ============================================================

def save_detections(
    detections: List[Detection],
    output_path: Path
):

    data = [
        detection.to_dict()
        for detection in detections
    ]

    with open(output_path, "w") as f:
        json.dump(
            data,
            f,
            indent=4
        )

    print(
        f"[INFO] Detection JSON saved: "
        f"{output_path}"
    )
# ============================================================
# Main
# ============================================================

def main():

    # --------------------------------------------------------
    # Validate input
    # --------------------------------------------------------

    if not INPUT_IMAGE.exists():

        raise FileNotFoundError(
            f"Input image not found: {INPUT_IMAGE}"
        )

    # --------------------------------------------------------
    # Create output directory
    # --------------------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # Load image
    # --------------------------------------------------------

    print(
        f"[INFO] Reading image: "
        f"{INPUT_IMAGE}"
    )

    image = cv2.imread(
        str(INPUT_IMAGE)
    )

    if image is None:

        raise RuntimeError(
            f"Unable to read image: "
            f"{INPUT_IMAGE}"
        )

    print(
        f"[INFO] Image size: "
        f"{image.shape[1]}x{image.shape[0]}"
    )

    # --------------------------------------------------------
    # Initialize detector
    # --------------------------------------------------------

    detector = RFDETRDetector(
        threshold=CONFIDENCE_THRESHOLD
    )

    # --------------------------------------------------------
    # Inference
    # --------------------------------------------------------

    detections = detector.predict(image)

    print(
        f"[INFO] Number of detections: "
        f"{len(detections)}"
    )

    # --------------------------------------------------------
    # Print detections
    # --------------------------------------------------------

    for index, detection in enumerate(
        detections,
        start=1
    ):

        print(
            f"[DETECTION {index}] "
            f"{detection.class_name} "
            f"confidence={detection.confidence:.3f} "
            f"bbox=("
            f"{detection.x1:.1f}, "
            f"{detection.y1:.1f}, "
            f"{detection.x2:.1f}, "
            f"{detection.y2:.1f}"
            f")"
        )

    # --------------------------------------------------------
    # Visualization
    # --------------------------------------------------------

    annotated = annotate_image(
        image,
        detections
    )

    # --------------------------------------------------------
    # Save annotated image
    # --------------------------------------------------------

    success = cv2.imwrite(
        str(OUTPUT_IMAGE),
        annotated
    )

    if not success:

        raise RuntimeError(
            f"Failed to save output image: "
            f"{OUTPUT_IMAGE}"
        )

    print(
        f"[INFO] Annotated image saved: "
        f"{OUTPUT_IMAGE}"
    )

    # --------------------------------------------------------
    # Save JSON
    # --------------------------------------------------------

    save_detections(
        detections,
        OUTPUT_JSON
    )


if __name__ == "__main__":
    main()