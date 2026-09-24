import enum
import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class TypeUtilisateur(str, enum.Enum):
    CANDIDAT = "CANDIDAT"
    RECRUTEUR = "RECRUTEUR"


class StatusUtilisateur(str, enum.Enum):
    ACTIF = "ACTIF"
    INACTIF = "INACTIF"
    EN_ATTENTE = "EN_ATTENTE"
    SUPPRIME = "SUPPRIME"


class Utilisateur(Base):
    __tablename__ = "utilisateur"

    id_utilisateur: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    numero_telephone: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    mot_de_passe: Mapped[str] = mapped_column(String(255), nullable=False)
    nom_prenom: Mapped[str] = mapped_column(String(255), nullable=False)

    type_utilisateur: Mapped[TypeUtilisateur] = mapped_column(Enum(TypeUtilisateur), nullable=False)
    status: Mapped[StatusUtilisateur] = mapped_column(
        Enum(StatusUtilisateur), default=StatusUtilisateur.EN_ATTENTE, nullable=False
    )

    date_creation: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    date_modification: Mapped[datetime | None] = mapped_column(DateTime, onupdate=datetime.utcnow, nullable=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Consentement Loi 25 / RGPD (JA-009)
    consentement_accepte: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    consentement_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    consentement_version: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Relations
    candidat: Mapped["Candidat | None"] = relationship(back_populates="utilisateur", uselist=False)
    recruteur: Mapped["Recruteur | None"] = relationship(back_populates="utilisateur", uselist=False)
