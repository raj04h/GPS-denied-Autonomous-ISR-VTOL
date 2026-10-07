from typing import List
from abc import ABC, abstractmethod
from bbox_detection import bbox_structure

class DetectorInterface(ABC):

    @abstractmethod
    def predict(self, image) -> List[bbox_structure]:
        raise NotImplemented
