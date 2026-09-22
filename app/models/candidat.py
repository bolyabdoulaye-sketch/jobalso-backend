import uuid
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Candidat(Base):
    __tablename__ = "candidat"

    id_candidat: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    id_utilisateur: Mapped[uuid.UUID] = mapped_column(ForeignKey("utilisateur.id_utilisateur"), unique=True, nullable=False)

    # Relations
    utilisateur: Mapped["Utilisateur"] = relationship(back_populates="candidat")
    cv: Mapped["CV | None"] = relationship(back_populates="candidat", uselist=False)