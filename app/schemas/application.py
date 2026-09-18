import uuid
from datetime import datetime
from pydantic import BaseModel
from app.models.application import PipelineStage


class ApplicationCreate(BaseModel):
    job_id: uuid.UUID
    candidate_profile_id: uuid.UUID


class ApplicationRead(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    candidate_profile_id: uuid.UUID
    current_stage: PipelineStage
    applied_at: datetime

    class Config:
        from_attributes = True


class PipelineEventRead(BaseModel):
    id: uuid.UUID
    application_id: uuid.UUID
    from_stage: PipelineStage | None
    to_stage: PipelineStage
    occurred_at: datetime

    class Config:
        from_attributes = True