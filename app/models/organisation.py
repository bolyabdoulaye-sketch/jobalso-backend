import uuid
from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.dates import utcnow
from app.db.base import Base


class Organisation(Base):
    __tablename__ = "organisation"

    id_organisation: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    nom: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    date_creation: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
        nullable=False,
    )

    date_modification: Mapped[datetime | None] = mapped_column(
        DateTime,
        onupdate=utcnow,
        nullable=True,
    )

    membres: Mapped[list["MembreOrganisation"]] = relationship(
        back_populates="organisation",
        cascade="all, delete-orphan",
    )

    offres: Mapped[list["Offre"]] = relationship(
        back_populates="organisation",
    )

    invitations: Mapped[list["InvitationOrganisation"]] = relationship(
        back_populates="organisation",
        cascade="all, delete-orphan",
    )
