import enum
import uuid
from datetime import datetime
from sqlalchemy import DateTime, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class PipelineStage(str, enum.Enum):
    CANDIDATURE = "candidature"
    SHORTLIST = "shortlist"
    ENTREVUE = "entrevue"
    DECISION = "decision"


class Application(Base):
    __tablename__ = "candidatures"
    __table_args__ = (UniqueConstraint("poste_id", "profil_candidat_id", name="uq_candidature_poste_candidat"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    poste_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("postes.id"), nullable=False)
    profil_candidat_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("profils_candidats.id"), nullable=False)

    etape_actuelle: Mapped[PipelineStage] = mapped_column(
        Enum(PipelineStage), default=PipelineStage.CANDIDATURE, nullable=False
    )

    postule_le: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relations
    poste: Mapped["Job"] = relationship(back_populates="candidatures")
    profil_candidat: Mapped["CandidateProfile"] = relationship(back_populates="candidatures")
    evenements: Mapped[list["PipelineEvent"]] = relationship(back_populates="candidature", cascade="all, delete-orphan")


class PipelineEvent(Base):
    __tablename__ = "evenements_pipeline"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    candidature_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("candidatures.id"), nullable=False)

    etape_origine: Mapped[PipelineStage | None] = mapped_column(Enum(PipelineStage), nullable=True)
    etape_destination: Mapped[PipelineStage] = mapped_column(Enum(PipelineStage), nullable=False)

    survenu_le: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relations
    candidature: Mapped["Application"] = relationship(back_populates="evenements")