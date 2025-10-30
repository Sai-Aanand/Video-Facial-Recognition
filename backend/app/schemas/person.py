from typing import List, Optional

from pydantic import BaseModel, Field


class PersonCreate(BaseModel):
    name: str = Field(..., example="Jane Doe")
    encodings: List[List[float]]
    metadata: Optional[dict] = None


class PersonResponse(BaseModel):
    person_id: str
    name: str
    metadata: Optional[dict] = None
