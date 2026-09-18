import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)

    # JA-071 : 7 declencheurs independants
    notify_new_recommendation: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_application_received: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_pipeline_stage_change: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_interview_proposed: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_application_rejected: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_weekly_summary: Mapped[bool] = mapped_column(Boolean, default=False)
    notify_profile_reminder: Mapped[bool] = mapped_column(Boolean, default=True)

    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RecommendationDismissal(Base):
    __tablename__ = "recommendation_dismissals"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("candidate_profiles.id"), nullable=False)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id"), nullable=False)

    dismissed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)  # JA-070