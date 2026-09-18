import enum
import uuid
from datetime import datetime
from sqlalchemy import String, Text, Boolean, DateTime, Enum, ForeignKey, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class InterviewStatus(str, enum.Enum):
    EN_COURS = "en_cours"
    TERMINEE = "terminee"
    INTERROMPUE = "interrompue"


class InterviewSimulation(Base):
    __tablename__ = "interview_simulations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id"), nullable=False)
    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("candidate_profiles.id"), nullable=False)

    status: Mapped[InterviewStatus] = mapped_column(
        Enum(InterviewStatus), default=InterviewStatus.EN_COURS, nullable=False
    )  # JA-076

    consent_given_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # JA-078
    shared_with_recruiter: Mapped[bool] = mapped_column(Boolean, default=False)  # JA-079

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class InterviewQuestion(Base):
    __tablename__ = "interview_questions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    simulation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("interview_simulations.id"), nullable=False)

    order: Mapped[int] = mapped_column(Integer, nullable=False)  # JA-075
    question_text: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class InterviewAnswer(Base):
    __tablename__ = "interview_answers"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    question_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("interview_questions.id"), nullable=False)

    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    follow_up_text: Mapped[str | None] = mapped_column(Text, nullable=True)  # JA-076 : relance

    answered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class InterviewFeedback(Base):
    __tablename__ = "interview_feedbacks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    simulation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("interview_simulations.id"), unique=True, nullable=False)

    strengths: Mapped[dict] = mapped_column(JSON, nullable=False)  # JA-077
    improvement_areas: Mapped[dict] = mapped_column(JSON, nullable=False)  # JA-077

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)