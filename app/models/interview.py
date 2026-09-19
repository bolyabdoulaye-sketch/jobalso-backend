import enum
import uuid
from datetime import datetime
from sqlalchemy import Text, Boolean, DateTime, Enum, ForeignKey, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class InterviewStatus(str, enum.Enum):
    EN_COURS = "en_cours"
    TERMINEE = "terminee"
    INTERROMPUE = "interrompue"


class InterviewSimulation(Base):
    __tablename__ = "simulations_entrevue"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    poste_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("postes.id"), nullable=False)
    profil_candidat_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("profils_candidats.id"), nullable=False)

    statut: Mapped[InterviewStatus] = mapped_column(
        Enum(InterviewStatus), default=InterviewStatus.EN_COURS, nullable=False
    )

    consentement_donne_le: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    partage_avec_recruteur: Mapped[bool] = mapped_column(Boolean, default=False)

    cree_le: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    modifie_le: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    poste: Mapped["Job"] = relationship(back_populates="simulations_entrevue")
    profil_candidat: Mapped["CandidateProfile"] = relationship(back_populates="simulations_entrevue")
    questions: Mapped[list["InterviewQuestion"]] = relationship(
        back_populates="simulation", cascade="all, delete-orphan"
    )
    retour: Mapped["InterviewFeedback | None"] = relationship(back_populates="simulation", uselist=False)


class InterviewQuestion(Base):
    __tablename__ = "questions_entrevue"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    simulation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("simulations_entrevue.id"), nullable=False)

    ordre: Mapped[int] = mapped_column(Integer, nullable=False)
    texte_question: Mapped[str] = mapped_column(Text, nullable=False)

    cree_le: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relations
    simulation: Mapped["InterviewSimulation"] = relationship(back_populates="questions")
    reponses: Mapped[list["InterviewAnswer"]] = relationship(back_populates="question", cascade="all, delete-orphan")


class InterviewAnswer(Base):
    __tablename__ = "reponses_entrevue"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    question_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("questions_entrevue.id"), nullable=False)

    texte_reponse: Mapped[str] = mapped_column(Text, nullable=False)
    texte_relance: Mapped[str | None] = mapped_column(Text, nullable=True)

    repondu_le: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relations
    question: Mapped["InterviewQuestion"] = relationship(back_populates="reponses")


class InterviewFeedback(Base):
    __tablename__ = "retours_entrevue"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    simulation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("simulations_entrevue.id"), unique=True, nullable=False)

    points_forts: Mapped[dict] = mapped_column(JSON, nullable=False)
    axes_amelioration: Mapped[dict] = mapped_column(JSON, nullable=False)

    cree_le: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relations
    simulation: Mapped["InterviewSimulation"] = relationship(back_populates="retour")