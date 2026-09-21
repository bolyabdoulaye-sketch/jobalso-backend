import enum
import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class IncidentCriticality(str, enum.Enum):
    FAIBLE = "faible"
    MOYEN = "moyen"
    ELEVE = "eleve"
    CRITIQUE = "critique"


class IncidentStatus(str, enum.Enum):
    OUVERT = "ouvert"
    EN_COURS = "en_cours"
    RESOLU = "resolu"
    FERME = "ferme"


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    titre: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    criticite: Mapped[IncidentCriticality] = mapped_column(Enum(IncidentCriticality), nullable=False)  # JA-102
    statut: Mapped[IncidentStatus] = mapped_column(Enum(IncidentStatus), default=IncidentStatus.OUVERT, nullable=False)

    signale_par: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("utilisateurs.id"), nullable=True)

    signale_le: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    resolu_le: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relations
    signaleur: Mapped["User | None"] = relationship()