import uuid
from datetime import datetime
from pydantic import BaseModel
from app.models.interview import InterviewStatus


class InterviewSimulationCreate(BaseModel):
    job_id: uuid.UUID
    consent_accepted: bool  # JA-078


class InterviewSimulationRead(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    candidate_profile_id: uuid.UUID
    status: InterviewStatus
    consent_given_at: datetime | None
    shared_with_recruiter: bool
    created_at: datetime

    class Config:
        from_attributes = True


class InterviewQuestionRead(BaseModel):
    id: uuid.UUID
    order: int
    question_text: str

    class Config:
        from_attributes = True


class InterviewAnswerCreate(BaseModel):
    question_id: uuid.UUID
    answer_text: str


class InterviewAnswerRead(BaseModel):
    id: uuid.UUID
    question_id: uuid.UUID
    answer_text: str
    follow_up_text: str | None
    answered_at: datetime

    class Config:
        from_attributes = True


class InterviewFeedbackRead(BaseModel):
    id: uuid.UUID
    simulation_id: uuid.UUID
    strengths: dict
    improvement_areas: dict
    created_at: datetime

    class Config:
        from_attributes = True