import uuid
from datetime import datetime
from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.models.user import RecruteurPersona


class JobTemplate(Base):
    __tablename__ = "modeles_poste"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    titre: Mapped[str] = mapped_column(String(255), nullable=False)  # JA-011
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    est_publie: Mapped[bool] = mapped_column(Boolean, default=True)  # JA-014 : publication immediate

    cree_par: Mapped[uuid.UUID] = mapped_column(ForeignKey("utilisateurs.id"), nullable=False)  # JA-014 : administrateur

    cree_le: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    modifie_le: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    createur: Mapped["User"] = relationship()
    criteres_modele: Mapped[list["JobTemplateCriterion"]] = relationship(
        back_populates="modele", cascade="all, delete-orphan"
    )
    personas: Mapped[list["JobTemplatePersona"]] = relationship(
        back_populates="modele", cascade="all, delete-orphan"
    )


class JobTemplateCriterion(Base):
    """Criteres pre-remplis du modele, modifiables ensuite par le recruteur (JA-011)."""
    __tablename__ = "criteres_modele_poste"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    modele_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("modeles_poste.id"), nullable=False)

    type_critere: Mapped[str] = mapped_column(String(50), nullable=False)
    valeur: Mapped[str] = mapped_column(String(255), nullable=False)
    niveau: Mapped[str] = mapped_column(String(50), nullable=False)

    # Relations
    modele: Mapped["JobTemplate"] = relationship(back_populates="criteres_modele")


class JobTemplatePersona(Base):
    """Table de liaison many-to-many : un modele peut viser plusieurs personas (JA-014)."""
    __tablename__ = "personas_modele_poste"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    modele_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("modeles_poste.id"), nullable=False)
    persona: Mapped[RecruteurPersona] = mapped_column(Enum(RecruteurPersona), nullable=False)

    # Relations
    modele: Mapped["JobTemplate"] = relationship(back_populates="personas")