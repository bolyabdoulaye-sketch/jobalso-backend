import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RoleInvitationOrganisation(str, enum.Enum):
    ADMIN = "ADMIN"
    MEMBRE = "MEMBRE"


class InvitationOrganisation(Base):
    __tablename__ = "invitation_organisation"

    __table_args__ = (
        UniqueConstraint(
            "token",
            name="invitation_organisation_token_key",
        ),
    )

    id_invitation: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    id_organisation: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "organisation.id_organisation",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    role: Mapped[RoleInvitationOrganisation] = mapped_column(
        Enum(RoleInvitationOrganisation),
        nullable=False,
        default=RoleInvitationOrganisation.MEMBRE,
    )

    token: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    date_creation: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    date_expiration: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    date_utilisation: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    organisation: Mapped["Organisation"] = relationship(
        back_populates="invitations",
    )