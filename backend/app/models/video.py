from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional


@dataclass(slots=True)
class ProcessedVideo:
    id: str
    filename: str
    original_path: str
    annotated_path: Optional[str]
    report_path: Optional[str]
    created_at: datetime
    processing_time_seconds: Optional[float]
    processing_progress: Optional[float]
    summary: Dict[str, List[Dict[str, str]]]
