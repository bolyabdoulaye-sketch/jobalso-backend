import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class ShortlistEntry(Base):
    __tablename__ = "entrees_shortlist"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    poste_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("postes.id"), nullable=False)
    profil_candidat_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("profils_candidats.id"), nullable=False)

    selectionne_pour_comparaison: Mapped[bool] = mapped_column(Boolean, default=False)

    ajoute_le: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)