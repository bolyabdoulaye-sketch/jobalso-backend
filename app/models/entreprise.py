import uuid
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Entreprise(Base):
    __tablename__ = "entreprise"

    id_entreprise: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    nom_entreprise: Mapped[str] = mapped_column(String(255), nullable=False)
    pays: Mapped[str] = mapped_column(String(100), nullable=False)
    localisation_entreprise: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relations
    recruteurs: Mapped[list["Recruteur"]] = relationship(back_populates="entreprise")