import enum
import uuid
from datetime import datetime
from sqlalchemy import DateTime, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class PipelineStage(str, enum.Enum):
    CANDIDATURE = "candidature"
    SHORTLIST = "shortlist"
    ENTREVUE = "entrevue"
    DECISION = "decision"


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id"), nullable=False)
    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("candidate_profiles.id"), nullable=False)

    current_stage: Mapped[PipelineStage] = mapped_column(
        Enum(PipelineStage), default=PipelineStage.CANDIDATURE, nullable=False
    )  # JA-056

    applied_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PipelineEvent(Base):
    __tablename__ = "pipeline_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("applications.id"), nullable=False)

    from_stage: Mapped[PipelineStage | None] = mapped_column(Enum(PipelineStage), nullable=True)
    to_stage: Mapped[PipelineStage] = mapped_column(Enum(PipelineStage), nullable=False)

    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)  # JA-060