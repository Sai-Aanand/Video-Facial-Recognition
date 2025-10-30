from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(slots=True)
class Person:
    id: str
    name: str
    encodings: List[List[float]] = field(default_factory=list)
    metadata: Optional[dict] = None
