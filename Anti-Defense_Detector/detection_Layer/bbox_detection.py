from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional

@dataclass
class bbox_structure:
    # txt_box
    class_id: int
    class_name: str
    confidence:float

    # size_box
    x1:float
    y1:float
    x2: float
    y2:float

    center_x: float
    center_y: float
    width: float
    height: float


    # original detector info
    source_model: Optional[str] = None
    source_class_id: Optional[int] = None
    source_class_name: Optional[str] = None


    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
