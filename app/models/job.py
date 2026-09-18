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
    __tablename__ = "postes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    recruteur_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("utilisateurs.id"), nullable=False)

    titre: Mapped[str | None] = mapped_column(String(255), nullable=True)

    description_brute: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_generee: Mapped[str | None] = mapped_column(Text, nullable=True)

    statut: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.BROUILLON, nullable=False)
    mode_creation: Mapped[JobCreationMode] = mapped_column(Enum(JobCreationMode), nullable=False)

    jeton_lien_candidature: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, default=lambda: secrets.token_urlsafe(24)
    )

    publie_le: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cree_le: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    modifie_le: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


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
    __tablename__ = "criteres_poste"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    poste_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("postes.id"), nullable=False)

    type_critere: Mapped[CriterionType] = mapped_column(Enum(CriterionType), nullable=False)
    valeur: Mapped[str] = mapped_column(String(255), nullable=False)
    niveau: Mapped[CriterionLevel] = mapped_column(Enum(CriterionLevel), nullable=False)

    cree_le: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    modifie_le: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)