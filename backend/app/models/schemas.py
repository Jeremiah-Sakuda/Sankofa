from typing import Literal, Optional
from pydantic import BaseModel, Field


# Max lengths to prevent abuse and ensure API stability
MAX_FIELD_LEN = 500
MAX_FREE_TEXT_LEN = 2000
MAX_FOLLOWUP_QUESTION_LEN = 2000
MAX_TTS_TEXT_LEN = 10000


class UserInput(BaseModel):
    family_name: str = Field(..., min_length=1, max_length=MAX_FIELD_LEN)
    region_of_origin: str = Field(..., min_length=1, max_length=MAX_FIELD_LEN)
    time_period: str = Field(..., min_length=1, max_length=MAX_FIELD_LEN)
    known_fragments: Optional[str] = Field(None, max_length=MAX_FREE_TEXT_LEN)
    language_or_ethnicity: Optional[str] = Field(None, max_length=MAX_FIELD_LEN)
    specific_interests: Optional[str] = Field(None, max_length=MAX_FREE_TEXT_LEN)


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
    question: str = Field(..., min_length=1, max_length=MAX_FOLLOWUP_QUESTION_LEN)


class AudioGenerateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=MAX_TTS_TEXT_LEN)
    voice: str = Field(default="Kore", max_length=100)


class NarrativeRequest(BaseModel):
    session_id: str
