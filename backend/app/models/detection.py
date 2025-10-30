from dataclasses import dataclass
from typing import List


@dataclass(slots=True)
class DetectionEvent:
    video_id: str
    person_id: str
    person_name: str
    timestamp: float
    frame_index: int
    bounding_box: List[int]
