import enum
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Enum, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class MatchingClassification(str, enum.Enum):
    FORTEMENT_RECOMMANDE = "fortement_recommande"
    BON_MATCH = "bon_match"
    A_EXAMINER = "a_examiner"


class MatchingScore(Base):
    __tablename__ = "scores_matching"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    poste_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("postes.id"), nullable=False)
    profil_candidat_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("profils_candidats.id"), nullable=False)

    score: Mapped[int] = mapped_column(Integer, nullable=False)
    classification: Mapped[MatchingClassification] = mapped_column(Enum(MatchingClassification), nullable=False)

    version_modele: Mapped[str] = mapped_column(String(50), nullable=False)

    cree_le: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    modifie_le: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MatchingLog(Base):
    __tablename__ = "journaux_matching"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    score_matching_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("scores_matching.id"), nullable=False)

    instantane_entrees: Mapped[dict] = mapped_column(JSON, nullable=False)
    score_resultat: Mapped[int] = mapped_column(Integer, nullable=False)
    explication_resultat: Mapped[dict] = mapped_column(JSON, nullable=False)
    version_modele: Mapped[str] = mapped_column(String(50), nullable=False)

    cree_le: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)