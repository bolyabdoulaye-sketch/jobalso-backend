import uuid
from datetime import datetime
from pydantic import BaseModel
from app.models.job import JobStatus, JobCreationMode, CriterionLevel, CriterionType


class JobCriterionCreate(BaseModel):
    criterion_type: CriterionType
    value: str
    level: CriterionLevel


class JobCriterionRead(BaseModel):
    id: uuid.UUID
    criterion_type: CriterionType
    value: str
    level: CriterionLevel

    class Config:
        from_attributes = True


class JobCreate(BaseModel):
    creation_mode: JobCreationMode
    title: str | None = None
    description_raw: str | None = None


class JobRead(BaseModel):
    id: uuid.UUID
    recruiter_id: uuid.UUID
    title: str | None
    description_raw: str | None
    description_generated: str | None
    status: JobStatus
    creation_mode: JobCreationMode
    application_link_token: str
    published_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True