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
    __tablename__ = "matching_scores"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id"), nullable=False)
    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("candidate_profiles.id"), nullable=False)

    score: Mapped[int] = mapped_column(Integer, nullable=False)  # JA-039 : 0-100
    classification: Mapped[MatchingClassification] = mapped_column(
        Enum(MatchingClassification), nullable=False
    )  # JA-042

    model_version: Mapped[str] = mapped_column(String(50), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # JA-044


class MatchingLog(Base):
    __tablename__ = "matching_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    matching_score_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("matching_scores.id"), nullable=False)

    # JA-045 : snapshot immuable des entrees et du resultat pour tracabilite ISO 42001
    input_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    output_score: Mapped[int] = mapped_column(Integer, nullable=False)
    output_explanation: Mapped[dict] = mapped_column(JSON, nullable=False)  # JA-041 : criteres remplis/ecarts
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)