import uuid
from datetime import datetime, date

from pydantic import BaseModel, Field

from app.models.critere_offre import NiveauCritere


class CritereCreate(BaseModel):
    libelle: str = Field(min_length=1, max_length=255)
    niveau: NiveauCritere = NiveauCritere.IMPORTANT


class CritereRead(BaseModel):
    id_critere: uuid.UUID
    libelle: str
    niveau: NiveauCritere

    class Config:
        from_attributes = True


class OffreCreate(BaseModel):
    titre_offre: str
    description: dict | list | None = None
    type_contrat: str | None = None
    revenu: float | None = None
    date_debut: date | None = None
    date_fin: date | None = None
    resume_offre: str | None = None
    # Hierarchisation des criteres (JA-018/019) : optionnelle, mais permet
    # un score de matching reel au lieu du placeholder a 0.0.
    criteres: list[CritereCreate] = Field(default_factory=list, max_length=30)


class OffreUpdate(BaseModel):
    titre_offre: str | None = None
    description: dict | list | None = None
    type_contrat: str | None = None
    revenu: float | None = None
    date_debut: date | None = None
    date_fin: date | None = None
    resume_offre: str | None = None
    status: bool | None = None


class OffreRead(BaseModel):
    id_offre: uuid.UUID
    id_recruteur: uuid.UUID
    titre_offre: str
    description: dict | list | None
    type_contrat: str | None
    revenu: float | None
    date_debut: date | None
    date_fin: date | None
    status: bool
    resume_offre: str | None
    lien_token: str
    date_publication: datetime
    date_modification: datetime | None
    criteres: list[CritereRead] = Field(default_factory=list)

    class Config:
        from_attributes = True
