import enum
import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
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
    __tablename__ = "utilisateurs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    mot_de_passe_hache: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False)

    persona: Mapped[RecruteurPersona | None] = mapped_column(Enum(RecruteurPersona), nullable=True)

    est_actif: Mapped[bool] = mapped_column(Boolean, default=True)
    email_verifie: Mapped[bool] = mapped_column(Boolean, default=False)

    consentement_donne_le: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    version_politique_consentement: Mapped[str | None] = mapped_column(String(20), nullable=True)

    cree_le: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    modifie_le: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    postes: Mapped[list["Job"]] = relationship(back_populates="recruteur")
    profil_candidat: Mapped["CandidateProfile | None"] = relationship(back_populates="utilisateur", uselist=False)
    jetons_reset: Mapped[list["PasswordResetToken"]] = relationship(back_populates="utilisateur")
    preferences_notification: Mapped["NotificationPreference | None"] = relationship(
        back_populates="utilisateur", uselist=False
    )
    notifications: Mapped[list["Notification"]] = relationship(back_populates="utilisateur")
    journaux_email: Mapped[list["EmailLog"]] = relationship(back_populates="utilisateur")