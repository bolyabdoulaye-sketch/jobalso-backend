import uuid
from datetime import datetime, date
from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector
from app.db.base import Base


class CV(Base):
    __tablename__ = "cv"

    id_cv: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    id_candidat: Mapped[uuid.UUID] = mapped_column(ForeignKey("candidat.id_candidat"), unique=True, nullable=False)

    resume_cv: Mapped[str | None] = mapped_column(Text, nullable=True)
    experience: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    education: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    langues: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    domaine_etude: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    competences: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    certifications: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    cv_vector: Mapped[list[float] | None] = mapped_column(Vector(768), nullable=True)
    cv_hash: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)

    entretien: Mapped[str | None] = mapped_column(Text, nullable=True)
    statut_cv: Mapped[str | None] = mapped_column(String(50), nullable=True)
    url_cv: Mapped[str | None] = mapped_column(Text, nullable=True)
    cv: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    date_creation: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    date_modification: Mapped[datetime | None] = mapped_column(DateTime, onupdate=datetime.utcnow, nullable=True)
    interview: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    code_cv: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    commentaires_recruteurs: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Relations
    candidat: Mapped["Candidat"] = relationship(back_populates="cv")
    resultats: Mapped[list["Resultat"]] = relationship(back_populates="cv")