import enum
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class HistoryAction(str, enum.Enum):
    AJOUT = "ajout"
    MODIFICATION = "modification"
    SUPPRESSION = "suppression"


class JobCriterionHistory(Base):
    __tablename__ = "historique_criteres_poste"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    poste_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("postes.id"), nullable=False)
    critere_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("criteres_poste.id"), nullable=True)

    action: Mapped[HistoryAction] = mapped_column(Enum(HistoryAction), nullable=False)

    # Snapshot de l'etat du critere au moment de l'action (JA-020)
    type_critere: Mapped[str] = mapped_column(String(50), nullable=False)
    valeur: Mapped[str] = mapped_column(String(255), nullable=False)
    niveau: Mapped[str] = mapped_column(String(50), nullable=False)

    modifie_par: Mapped[uuid.UUID] = mapped_column(ForeignKey("utilisateurs.id"), nullable=False)
    modifie_le: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relations
    poste: Mapped["Job"] = relationship()