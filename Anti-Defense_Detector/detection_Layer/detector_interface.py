from abc import ABC, abstractmethod
from typing import List

from bbox_detection import bbox_structure


class DetectorInterface(ABC):
    @abstractmethod
    def predict(self, image) -> List[bbox_structure]:
        raise NotImplementedError