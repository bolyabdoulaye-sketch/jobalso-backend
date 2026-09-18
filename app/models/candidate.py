import enum
import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Enum, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)

    location: Mapped[str | None] = mapped_column(String(255), nullable=True)  # JA-036
    desired_job_type: Mapped[str | None] = mapped_column(String(255), nullable=True)  # JA-036

    completeness_rate: Mapped[int] = mapped_column(Integer, default=0)  # JA-035

    talent_pool_consent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # anticipe JA-066

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CVAnalysisStatus(str, enum.Enum):
    EN_ATTENTE = "en_attente"
    TRAITE = "traite"
    ECHEC = "echec"


class CV(Base):
    __tablename__ = "cvs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("candidate_profiles.id"), nullable=False)

    file_path: Mapped[str] = mapped_column(String(500), nullable=False)  # JA-030
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)  # pdf ou docx

    analysis_status: Mapped[CVAnalysisStatus] = mapped_column(
        Enum(CVAnalysisStatus), default=CVAnalysisStatus.EN_ATTENTE, nullable=False
    )  # JA-031

    is_current: Mapped[bool] = mapped_column(Boolean, default=True)  # JA-032

    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SkillType(str, enum.Enum):
    COMPETENCE = "competence"
    LANGUE = "langue"
    DOMAINE_EXPERIENCE = "domaine_experience"
    TYPE_POSTE_COMPATIBLE = "type_poste_compatible"


class SkillSource(str, enum.Enum):
    EXTRAIT = "extrait"
    CORRIGE = "corrige"  # JA-034 : prime sur l'extraction automatique


class CandidateSkill(Base):
    __tablename__ = "candidate_skills"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("candidate_profiles.id"), nullable=False)

    skill_type: Mapped[SkillType] = mapped_column(Enum(SkillType), nullable=False)
    value: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[SkillSource] = mapped_column(Enum(SkillSource), default=SkillSource.EXTRAIT, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)