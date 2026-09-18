import uuid
from datetime import datetime
from pydantic import BaseModel


class ShortlistEntryCreate(BaseModel):
    job_id: uuid.UUID
    candidate_profile_id: uuid.UUID


class ShortlistEntryRead(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    candidate_profile_id: uuid.UUID
    is_selected_for_comparison: bool
    added_at: datetime

    class Config:
        from_attributes = True