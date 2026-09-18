import uuid
from datetime import datetime
from pydantic import BaseModel
from app.models.candidate import CVAnalysisStatus, SkillType, SkillSource


class CandidateProfileRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    location: str | None
    desired_job_type: str | None
    completeness_rate: int
    talent_pool_consent_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class CandidateProfileUpdate(BaseModel):
    location: str | None = None
    desired_job_type: str | None = None


class CVRead(BaseModel):
    id: uuid.UUID
    candidate_profile_id: uuid.UUID
    file_path: str
    file_type: str
    analysis_status: CVAnalysisStatus
    is_current: bool
    uploaded_at: datetime

    class Config:
        from_attributes = True


class CandidateSkillCreate(BaseModel):
    skill_type: SkillType
    value: str
    source: SkillSource = SkillSource.EXTRAIT


class CandidateSkillRead(BaseModel):
    id: uuid.UUID
    skill_type: SkillType
    value: str
    source: SkillSource

    class Config:
        from_attributes = True