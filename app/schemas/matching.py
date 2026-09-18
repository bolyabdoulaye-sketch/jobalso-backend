import uuid
from datetime import datetime
from pydantic import BaseModel
from app.models.matching import MatchingClassification


class MatchingScoreRead(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    candidate_profile_id: uuid.UUID
    score: int
    classification: MatchingClassification
    model_version: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MatchingLogRead(BaseModel):
    id: uuid.UUID
    matching_score_id: uuid.UUID
    input_snapshot: dict
    output_score: int
    output_explanation: dict
    model_version: str
    created_at: datetime

    class Config:
        from_attributes = True