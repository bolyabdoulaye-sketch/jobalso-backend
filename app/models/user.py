import enum
import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class UserRole(str, enum.Enum):
    CANDIDAT = "candidat"
    RECRUTEUR = "recruteur"
    ADMINISTRATEUR = "administrateur"


class RecruteurPersona(str, enum.Enum):
    PME = "pme"
    ENTREPRENEUR = "entrepreneur"
    RESPONSABLE_RH = "responsable_rh"
    RECRUTEUR = "recruteur"
    GESTIONNAIRE_SANS_RH = "gestionnaire_sans_equipe_rh"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False)

    persona: Mapped[RecruteurPersona | None] = mapped_column(Enum(RecruteurPersona), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_email_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    consent_given_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    consent_policy_version: Mapped[str | None] = mapped_column(String(20), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
