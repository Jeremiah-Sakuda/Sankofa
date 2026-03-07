from typing import Literal, Optional
from pydantic import BaseModel


class UserInput(BaseModel):
    family_name: str
    region_of_origin: str
    time_period: str
    known_fragments: Optional[str] = None
    language_or_ethnicity: Optional[str] = None
    specific_interests: Optional[str] = None


class NarrativeSegment(BaseModel):
    type: Literal["text", "image", "audio", "map"]
    content: Optional[str] = None
    media_data: Optional[str] = None
    media_type: Optional[str] = None
    trust_level: Literal["historical", "cultural", "reconstructed"]
    sequence: int
    act: Optional[int] = None
    is_hero: bool = False


class IntakeResponse(BaseModel):
    session_id: str
    message: str


class FollowUpRequest(BaseModel):
    question: str


class NarrativeRequest(BaseModel):
    session_id: str
