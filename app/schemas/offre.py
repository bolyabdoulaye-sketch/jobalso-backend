import uuid
from datetime import datetime, date

from pydantic import BaseModel, ConfigDict, Field

from app.models.critere_offre import NiveauCritere


class CritereCreate(BaseModel):
    libelle: str = Field(min_length=1, max_length=255)
    niveau: NiveauCritere = NiveauCritere.IMPORTANT


class CritereRead(BaseModel):
    id_critere: uuid.UUID
    libelle: str
    niveau: NiveauCritere

    model_config = ConfigDict(from_attributes=True)


class OffreCreate(BaseModel):
    titre_offre: str = Field(min_length=2, max_length=255)
    description: dict | list | None = None
    type_contrat: str | None = None
    revenu: float | None = None
    date_debut: date | None = None
    date_fin: date | None = None
    resume_offre: str | None = None
    # False = brouillon : l'offre n'est pas visible par son lien public.
    status: bool = True
    # Hierarchisation des criteres (JA-018/019) : optionnelle, mais permet
    # un score de matching reel au lieu du placeholder a 0.0.
    criteres: list[CritereCreate] = Field(default_factory=list, max_length=30)


class OffreUpdate(BaseModel):
    titre_offre: str | None = Field(default=None, min_length=2, max_length=255)
    description: dict | list | None = None
    type_contrat: str | None = None
    revenu: float | None = None
    date_debut: date | None = None
    date_fin: date | None = None
    resume_offre: str | None = None
    status: bool | None = None
    criteres: list[CritereCreate] | None = Field(default=None, max_length=30)


class OffreRead(BaseModel):
    id_offre: uuid.UUID
    id_recruteur: uuid.UUID
    id_organisation: uuid.UUID
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

    model_config = ConfigDict(from_attributes=True)


class CategoriesCount(BaseModel):
    rec: int = 0
    good: int = 0
    review: int = 0
    low: int = 0


class OffreSynthese(BaseModel):
    """Ligne du tableau de bord recruteur : une offre et ses candidatures."""

    id_offre: uuid.UUID
    titre_offre: str
    status: bool
    date_publication: datetime
    nb_candidatures: int
    categories: CategoriesCount
    par_statut: dict[str, int]
