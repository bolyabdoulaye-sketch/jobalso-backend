import enum
import uuid
import secrets
from datetime import datetime
from sqlalchemy import String, Text, DateTime, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class JobStatus(str, enum.Enum):
    BROUILLON = "brouillon"
    PUBLIEE = "publiee"
    DEPUBLIEE = "depubliee"


class JobCreationMode(str, enum.Enum):
    CHAT = "chat"
    FORMULAIRE = "formulaire"


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    recruiter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)

    title: Mapped[str | None] = mapped_column(String(255), nullable=True)

    description_raw: Mapped[str | None] = mapped_column(Text, nullable=True)  # JA-015 saisie libre
    description_generated: Mapped[str | None] = mapped_column(Text, nullable=True)  # JA-023 texte genere

    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.BROUILLON, nullable=False)
    creation_mode: Mapped[JobCreationMode] = mapped_column(Enum(JobCreationMode), nullable=False)

    application_link_token: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, default=lambda: secrets.token_urlsafe(24)
    )  # JA-026

    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CriterionLevel(str, enum.Enum):
    OBLIGATOIRE = "obligatoire"
    IMPORTANT = "important"
    SOUHAITABLE = "souhaitable"


class CriterionType(str, enum.Enum):
    INTITULE = "intitule"
    LIEU = "lieu"
    LANGUE = "langue"
    EXPERIENCE = "experience"
    COMPETENCE = "competence"


class JobCriterion(Base):
    __tablename__ = "job_criteria"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id"), nullable=False)

    criterion_type: Mapped[CriterionType] = mapped_column(Enum(CriterionType), nullable=False)
    value: Mapped[str] = mapped_column(String(255), nullable=False)
    level: Mapped[CriterionLevel] = mapped_column(Enum(CriterionLevel), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
