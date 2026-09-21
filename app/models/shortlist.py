import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class ShortlistEntry(Base):
    __tablename__ = "entrees_shortlist"
    __table_args__ = (UniqueConstraint("poste_id", "profil_candidat_id", name="uq_shortlist_poste_candidat"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    poste_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("postes.id"), nullable=False)
    profil_candidat_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("profils_candidats.id"), nullable=False)

    selectionne_pour_comparaison: Mapped[bool] = mapped_column(Boolean, default=False)

    ajoute_le: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relations
    poste: Mapped["Job"] = relationship(back_populates="entrees_shortlist")
    profil_candidat: Mapped["CandidateProfile"] = relationship(back_populates="entrees_shortlist")