import enum
import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Enum, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class CandidateProfile(Base):
    __tablename__ = "profils_candidats"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    utilisateur_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("utilisateurs.id"), unique=True, nullable=False)

    localisation: Mapped[str | None] = mapped_column(String(255), nullable=True)
    type_poste_recherche: Mapped[str | None] = mapped_column(String(255), nullable=True)

    taux_completude: Mapped[int] = mapped_column(Integer, default=0)

    consentement_banque_profils_le: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    cree_le: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    modifie_le: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    utilisateur: Mapped["User"] = relationship(back_populates="profil_candidat")
    cvs: Mapped[list["CV"]] = relationship(back_populates="profil_candidat", cascade="all, delete-orphan")
    competences: Mapped[list["CandidateSkill"]] = relationship(
        back_populates="profil_candidat", cascade="all, delete-orphan"
    )
    candidatures: Mapped[list["Application"]] = relationship(back_populates="profil_candidat")
    entrees_shortlist: Mapped[list["ShortlistEntry"]] = relationship(back_populates="profil_candidat")
    scores_matching: Mapped[list["MatchingScore"]] = relationship(back_populates="profil_candidat")
    simulations_entrevue: Mapped[list["InterviewSimulation"]] = relationship(back_populates="profil_candidat")


class CVAnalysisStatus(str, enum.Enum):
    EN_ATTENTE = "en_attente"
    TRAITE = "traite"
    ECHEC = "echec"


class CV(Base):
    __tablename__ = "cvs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    profil_candidat_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("profils_candidats.id"), nullable=False)

    chemin_fichier: Mapped[str] = mapped_column(String(500), nullable=False)
    type_fichier: Mapped[str] = mapped_column(String(10), nullable=False)

    statut_analyse: Mapped[CVAnalysisStatus] = mapped_column(
        Enum(CVAnalysisStatus), default=CVAnalysisStatus.EN_ATTENTE, nullable=False
    )

    est_actuel: Mapped[bool] = mapped_column(Boolean, default=True)

    depose_le: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relations
    profil_candidat: Mapped["CandidateProfile"] = relationship(back_populates="cvs")


class SkillType(str, enum.Enum):
    COMPETENCE = "competence"
    LANGUE = "langue"
    DOMAINE_EXPERIENCE = "domaine_experience"
    TYPE_POSTE_COMPATIBLE = "type_poste_compatible"


class SkillSource(str, enum.Enum):
    EXTRAIT = "extrait"
    CORRIGE = "corrige"


class CandidateSkill(Base):
    __tablename__ = "competences_candidat"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    profil_candidat_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("profils_candidats.id"), nullable=False)

    type_competence: Mapped[SkillType] = mapped_column(Enum(SkillType), nullable=False)
    valeur: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[SkillSource] = mapped_column(Enum(SkillSource), default=SkillSource.EXTRAIT, nullable=False)

    cree_le: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relations
    profil_candidat: Mapped["CandidateProfile"] = relationship(back_populates="competences")