import uuid
from datetime import datetime
from pydantic import BaseModel


class NotificationPreferenceRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    notify_new_recommendation: bool
    notify_application_received: bool
    notify_pipeline_stage_change: bool
    notify_interview_proposed: bool
    notify_application_rejected: bool
    notify_weekly_summary: bool
    notify_profile_reminder: bool
    updated_at: datetime

    class Config:
        from_attributes = True


class NotificationPreferenceUpdate(BaseModel):
    notify_new_recommendation: bool | None = None
    notify_application_received: bool | None = None
    notify_pipeline_stage_change: bool | None = None
    notify_interview_proposed: bool | None = None
    notify_application_rejected: bool | None = None
    notify_weekly_summary: bool | None = None
    notify_profile_reminder: bool | None = None


class RecommendationDismissalCreate(BaseModel):
    job_id: uuid.UUID