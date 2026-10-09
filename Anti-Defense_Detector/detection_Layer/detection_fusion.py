from typing import List, Dict, Any

from bbox_detection import bbox_structure


class DetectionFusion:

    CANONICAL_CLASSES = {
        "PERSON",
        "VEHICLE",
        "HEAVY_VEHICLE",
        "MOTORCYCLE",
        "DRONE",
        "AIRCRAFT",
        "ANIMAL",
        "BOAT",
    }

    VEHICLE_FAMILY = {
        "VEHICLE",
        "HEAVY_VEHICLE",
    }

    AIR_FAMILY = {
        "DRONE",
        "AIRCRAFT",
    }

    def __init__(
        self,
        iou_threshold: float = 0.50,
        conflict_iou_threshold: float = 0.70,
        confidence_threshold: float = 0.25,
    ):

        if not 0.0 <= iou_threshold <= 1.0:
            raise ValueError(
                "iou_threshold must be between 0 and 1"
            )

        if not 0.0 <= conflict_iou_threshold <= 1.0:
            raise ValueError(
                "conflict_iou_threshold must be between 0 and 1"
            )

        if not 0.0 <= confidence_threshold <= 1.0:
            raise ValueError(
                "confidence_threshold must be between 0 and 1"
            )

        self.iou_threshold = iou_threshold
        self.conflict_iou_threshold = conflict_iou_threshold
        self.confidence_threshold = confidence_threshold

        self.last_conflicts: List[Dict[str, Any]] = []

    @staticmethod
    def _bbox(
        detection: bbox_structure,
    ):
        return (
            float(detection.x1),
            float(detection.y1),
            float(detection.x2),
            float(detection.y2),
        )

    @staticmethod
    def _iou(
        box_a,
        box_b,
    ) -> float:

        ax1, ay1, ax2, ay2 = box_a
        bx1, by1, bx2, by2 = box_b

        ix1 = max(ax1, bx1)
        iy1 = max(ay1, by1)
        ix2 = min(ax2, bx2)
        iy2 = min(ay2, by2)

        iw = max(
            0.0,
            ix2 - ix1,
        )

        ih = max(
            0.0,
            iy2 - iy1,
        )

        intersection = iw * ih

        area_a = max(
            0.0,
            ax2 - ax1,
        ) * max(
            0.0,
            ay2 - ay1,
        )

        area_b = max(
            0.0,
            bx2 - bx1,
        ) * max(
            0.0,
            by2 - by1,
        )

        union = (
            area_a
            + area_b
            - intersection
        )

        if union <= 0.0:
            return 0.0

        return intersection / union

    @classmethod
    def _class_name(
        cls,
        detection: bbox_structure,
    ) -> str:

        return str(
            detection.class_name
        ).strip().upper()

    @classmethod
    def _is_canonical(
        cls,
        detection: bbox_structure,
    ) -> bool:

        return (
            cls._class_name(detection)
            in cls.CANONICAL_CLASSES
        )

    def _is_valid(
        self,
        detection: bbox_structure,
    ) -> bool:

        try:

            confidence = float(
                detection.confidence
            )

            x1, y1, x2, y2 = self._bbox(
                detection
            )

        except (
            AttributeError,
            TypeError,
            ValueError,
        ):

            return False

        if confidence < self.confidence_threshold:
            return False

        if x2 <= x1 or y2 <= y1:
            return False

        class_name = self._class_name(
            detection
        )

        return bool(class_name)

    @classmethod
    def _same_class(
        cls,
        detection_a: bbox_structure,
        detection_b: bbox_structure,
    ) -> bool:

        return (
            cls._class_name(detection_a)
            == cls._class_name(detection_b)
        )

    @classmethod
    def _compatible_classes(
        cls,
        class_a: str,
        class_b: str,
    ) -> bool:

        if class_a == class_b:
            return True

        if (
            class_a in cls.VEHICLE_FAMILY
            and class_b in cls.VEHICLE_FAMILY
        ):
            return True

        return False

    @staticmethod
    def _confidence(
        detection: bbox_structure,
    ) -> float:

        return float(
            detection.confidence
        )

    def _select_strongest(
        self,
        detections: List[bbox_structure],
    ) -> bbox_structure:

        return max(
            detections,
            key=self._confidence,
        )

    def _record_conflict(
        self,
        detection_a: bbox_structure,
        detection_b: bbox_structure,
        iou: float,
    ):

        self.last_conflicts.append(
            {
                "class_a": self._class_name(
                    detection_a
                ),
                "confidence_a": self._confidence(
                    detection_a
                ),
                "source_a": detection_a.source_model,
                "class_b": self._class_name(
                    detection_b
                ),
                "confidence_b": self._confidence(
                    detection_b
                ),
                "source_b": detection_b.source_model,
                "iou": iou,
            }
        )

    def _suppress_same_class_duplicates(
        self,
        detections: List[bbox_structure],
    ) -> List[bbox_structure]:

        ordered = sorted(
            detections,
            key=self._confidence,
            reverse=True,
        )

        selected: List[bbox_structure] = []

        for detection in ordered:

            detection_box = self._bbox(
                detection
            )

            duplicate = False

            for existing in selected:

                if not self._same_class(
                    detection,
                    existing,
                ):
                    continue

                existing_box = self._bbox(
                    existing
                )

                iou = self._iou(
                    detection_box,
                    existing_box,
                )

                if iou >= self.iou_threshold:

                    duplicate = True
                    break

            if not duplicate:
                selected.append(
                    detection
                )

        return selected

    def _resolve_class_conflicts(
        self,
        detections: List[bbox_structure],
    ) -> List[bbox_structure]:

        ordered = sorted(
            detections,
            key=self._confidence,
            reverse=True,
        )

        selected: List[bbox_structure] = []

        for detection in ordered:

            detection_box = self._bbox(
                detection
            )

            remove_detection = False

            for existing in selected:

                existing_box = self._bbox(
                    existing
                )

                iou = self._iou(
                    detection_box,
                    existing_box,
                )

                if iou < self.conflict_iou_threshold:
                    continue

                if self._same_class(
                    detection,
                    existing,
                ):
                    continue

                class_a = self._class_name(
                    detection
                )

                class_b = self._class_name(
                    existing
                )

                if self._compatible_classes(
                    class_a,
                    class_b,
                ):
                    continue

                self._record_conflict(
                    existing,
                    detection,
                    iou,
                )

                remove_detection = True
                break

            if not remove_detection:
                selected.append(
                    detection
                )

        return selected

    def _handle_specialized(
        self,
        canonical: List[bbox_structure],
        specialized: List[bbox_structure],
    ) -> List[bbox_structure]:

        result = list(canonical)

        for detection in specialized:

            detection_box = self._bbox(
                detection
            )

            associated = False

            for canonical_detection in canonical:

                canonical_box = self._bbox(
                    canonical_detection
                )

                iou = self._iou(
                    detection_box,
                    canonical_box,
                )

                if iou >= self.iou_threshold:

                    associated = True
                    break

            if not associated:
                result.append(
                    detection
                )

        return result

    def fuse(
        self,
        detections: List[bbox_structure],
    ) -> List[bbox_structure]:

        self.last_conflicts = []

        if not detections:
            return []

        valid_detections = [
            detection
            for detection in detections
            if self._is_valid(detection)
        ]

        if not valid_detections:
            return []

        canonical = [
            detection
            for detection in valid_detections
            if self._is_canonical(detection)
        ]

        specialized = [
            detection
            for detection in valid_detections
            if not self._is_canonical(detection)
        ]

        canonical = (
            self._suppress_same_class_duplicates(
                canonical
            )
        )

        canonical = (
            self._resolve_class_conflicts(
                canonical
            )
        )

        fused = self._handle_specialized(
            canonical,
            specialized,
        )

        fused.sort(
            key=self._confidence,
            reverse=True,
        )

        return fused

    def get_conflicts(
        self,
    ) -> List[Dict[str, Any]]:

        return list(
            self.last_conflicts
        )