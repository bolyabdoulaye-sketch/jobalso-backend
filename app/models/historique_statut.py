import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class HistoriqueStatutCandidature(Base):
    __tablename__ = "historique_statut_candidature"

    id_historique: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    id_resultat: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("resultat.id_resultat"), nullable=False, index=True
    )
    ancien_statut: Mapped[str | None] = mapped_column(String(50), nullable=True)
    nouveau_statut: Mapped[str] = mapped_column(String(50), nullable=False)
    id_utilisateur: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("utilisateur.id_utilisateur"), nullable=False
    )
    date_changement: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
