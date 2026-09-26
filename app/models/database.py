from .base import Base

from sqlalchemy import UUID, JSON
from sqlalchemy.dialects.postgresql import JSONB
import enum
import uuid
from datetime import datetime, date, timezone
from typing import Optional, List, Any

from sqlalchemy import String, Text, Boolean, DateTime, Date, Float, Enum as SQLEnum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

#types enumeres

class MiniTypeUtilisateurEnum(str, enum.Enum):
    candidat = "candidat"
    recruteur = "recruteur"
    administrateur= "administrateur"

class MiniStatusUtilisateurEnum(str, enum.Enum):
    actif = "actif"
    inactif = "inactif"
    en_attente = "en_attente"
    supprime = "supprime"


class MiniEtapeCandidatureEnum(str, enum.Enum):
    candidature = "candidature"
    shortlist = "shortlist"
    entretien = "entrevue"
    decision = "decision"


#les tables de la base de donnees

class Utilisateur(Base):
    __tablename__= "utilisateur"

    id_utilisateur: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    numero_telephone: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    mot_de_passe: Mapped[str] = mapped_column(Text, nullable=False)
    nom_prenom: Mapped[str] = mapped_column(String, nullable=False)
    type_utilisateur: Mapped[MiniTypeUtilisateurEnum] = mapped_column(SQLEnum(MiniTypeUtilisateurEnum), nullable=False)
    status: Mapped[MiniStatusUtilisateurEnum] = mapped_column(SQLEnum(MiniStatusUtilisateurEnum), nullable=False)
    date_creation: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    date_modification: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, onupdate=datetime.utcnow)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


    candidat: Mapped[Optional["Candidat"]] = relationship("Candidat", back_populates="utilisateur", uselist=False)
    recruteur: Mapped[Optional["Recruteur"]] = relationship("Recruteur", back_populates="utilisateur", uselist=False)
    administrateur: Mapped[Optional["Administrateur"]] = relationship("Administrateur", back_populates="utilisateur", uselist=False)
    sessions: Mapped[List["SessionAuthentification"]] = relationship(
        "SessionAuthentification", back_populates="utilisateur", cascade="all, delete-orphan"
    )


class SessionAuthentification(Base):
    """Refresh tokens hachés, révocables et renouvelés à chaque usage."""
    __tablename__ = "session_authentification"

    id_session: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_utilisateur: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("utilisateur.id_utilisateur", ondelete="CASCADE"), nullable=False, index=True
    )
    refresh_token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expire_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoque_le: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    utilisateur: Mapped["Utilisateur"] = relationship("Utilisateur", back_populates="sessions")

class Administrateur(Base):

    __tablename__ = "administrateur"
    id_administrateur: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_utilisateur: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("utilisateur.id_utilisateur", ondelete="CASCADE"), nullable=False)

    __table_args__ = (UniqueConstraint("id_utilisateur"),)

    utilisateur: Mapped["Utilisateur"] = relationship("Utilisateur", back_populates="administrateur")

class Candidat(Base):
    __tablename__= "candidat"
    id_candidat: Mapped[uuid.UUID]= mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    id_utilisateur: Mapped[uuid.UUID]= mapped_column(UUID, ForeignKey("utilisateur.id_utilisateur", ondelete="CASCADE"), nullable=False)
    consentement_banque_profils: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (UniqueConstraint("id_utilisateur"),)

    utilisateur: Mapped["Utilisateur"] = relationship("Utilisateur", back_populates="candidat")
    cvs: Mapped[List["CV"]] = relationship("CV", back_populates="candidat")
    candidatures: Mapped[List["Candidature"]] = relationship("Candidature", back_populates="candidat")
class Recruteur(Base):
    __tablename__= "recruteur"
    id_recruteur: Mapped[uuid.UUID]= mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    id_utilisateur: Mapped[uuid.UUID]= mapped_column(UUID, ForeignKey("utilisateur.id_utilisateur", ondelete="CASCADE"), nullable=False)
    id_entreprise: Mapped[uuid.UUID]= mapped_column(UUID, ForeignKey("entreprise.id_entreprise"), nullable=False)

    __table_args__ = (UniqueConstraint("id_utilisateur"),)

    utilisateur: Mapped["Utilisateur"] = relationship("Utilisateur", back_populates="recruteur")
    entreprise: Mapped["Entreprise"] = relationship("Entreprise", back_populates="recruteurs")
    offres: Mapped[List["Offre"]] = relationship("Offre", back_populates="recruteur")


class Entreprise(Base):
    __tablename__ = "entreprise"

    id_entreprise: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nom_entreprise: Mapped[str] = mapped_column(Text, nullable=False)
    pays: Mapped[str] = mapped_column(Text, nullable=False)
    localisation_entreprise: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (UniqueConstraint("nom_entreprise", "pays", "localisation_entreprise"),)

    # Relations
    recruteurs: Mapped[List["Recruteur"]] = relationship("Recruteur", back_populates="entreprise")

class CV(Base):
    __tablename__ = "cv"

    id_cv: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_candidat: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("candidat.id_candidat", ondelete="CASCADE"), nullable=False)
    resume_cv: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    experience: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    education: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    langues: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    domaine_etude: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    competences: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    certifications: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    cv_vector: Mapped[Optional[list[float]]] = mapped_column(Vector(768), nullable=True)
    cv_hash: Mapped[Optional[str]] = mapped_column(String, unique=True, nullable=True)
    entretien: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    statut_cv: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    url_cv: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cv: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    date_creation: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    date_modification: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, onupdate=datetime.utcnow)
    interview: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    code_cv: Mapped[Optional[str]] = mapped_column(String, unique=True, nullable=True)
    commentaires_recruteurs: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)

    # Relations
    candidat: Mapped["Candidat"] = relationship("Candidat", back_populates="cvs")
    resultats: Mapped[List["Resultat"]] = relationship("Resultat", back_populates="cv")


class Offre(Base):
    __tablename__ = "offre"

    id_offre: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_recruteur: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("recruteur.id_recruteur", ondelete="CASCADE"), nullable=False)
    titre_offre: Mapped[str] = mapped_column(String, nullable=False)
    public_token: Mapped[Optional[str]] = mapped_column(String, unique=True, nullable=True, index=True)
    description: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    type_contrat: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    revenu: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    offre_vector: Mapped[Optional[list[float]]] = mapped_column(Vector(768), nullable=True)
    entretien: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    date_debut: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    date_fin: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    resume_offre: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    date_publication: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    date_modification: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, onupdate=datetime.utcnow)
    date_suppression: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relations
    recruteur: Mapped["Recruteur"] = relationship("Recruteur", back_populates="offres")
    resultats: Mapped[List["Resultat"]] = relationship("Resultat", back_populates="offre")
    candidatures: Mapped[List["Candidature"]] = relationship("Candidature", back_populates="offre")


class Resultat(Base):
    __tablename__ = "resultat"

    id_resultat: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_offre: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("offre.id_offre", ondelete="CASCADE"), nullable=False)
    id_cv: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("cv.id_cv", ondelete="SET NULL"), nullable=True)
    score_sim: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    statut_candidature: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    date_modification: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, onupdate=datetime.utcnow)

    # Relations
    offre: Mapped["Offre"] = relationship("Offre", back_populates="resultats")
    cv: Mapped[Optional["CV"]] = relationship("CV", back_populates="resultats")


class Candidature(Base):
    __tablename__ = "candidature"

    id_candidature: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_offre: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("offre.id_offre", ondelete="CASCADE"), nullable=False)
    id_candidat: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("candidat.id_candidat", ondelete="CASCADE"), nullable=True)
    id_cv: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("cv.id_cv", ondelete="SET NULL"), nullable=True)
    source_candidature: Mapped[str] = mapped_column(String(30), nullable=False, default="lien_public")
    etape_courante: Mapped[MiniEtapeCandidatureEnum] = mapped_column(
        SQLEnum(MiniEtapeCandidatureEnum), 
        nullable=False, 
        default=MiniEtapeCandidatureEnum.candidature
    )
    date_candidature: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    date_modification: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, onupdate=datetime.utcnow)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    url_cv: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Champs pour les candidats externes (non connectés)
    nom_prenom: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    telephone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Relations
    offre: Mapped["Offre"] = relationship("Offre", back_populates="candidatures")
    candidat: Mapped[Optional["Candidat"]] = relationship("Candidat", back_populates="candidatures")
    cv: Mapped[Optional["CV"]] = relationship("CV")
