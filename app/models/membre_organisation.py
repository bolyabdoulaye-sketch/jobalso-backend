import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RoleOrganisation(str, enum.Enum):
    ADMIN = "ADMIN"
    MEMBRE = "MEMBRE"


class MembreOrganisation(Base):
    __tablename__ = "membre_organisation"

    id_organisation: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organisation.id_organisation", ondelete="CASCADE"),
        primary_key=True,
    )

    id_utilisateur: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("utilisateur.id_utilisateur", ondelete="CASCADE"),
        primary_key=True,
    )

    role: Mapped[RoleOrganisation] = mapped_column(
        Enum(RoleOrganisation),
        nullable=False,
    )

    date_ajout: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    organisation: Mapped["Organisation"] = relationship(
        back_populates="membres",
    )

    utilisateur: Mapped["Utilisateur"] = relationship()