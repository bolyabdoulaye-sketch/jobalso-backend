import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MatchingRequest(BaseModel):
    code_cv: str = Field(min_length=4, max_length=20)
    id_offre: uuid.UUID


class CritereExplication(BaseModel):
    libelle: str
    niveau: str


class CandidatApercu(BaseModel):
    """Ce que le recruteur voit du candidat dans la shortlist."""

    nom_prenom: str
    localisation: str | None = None
    type_poste_recherche: str | None = None
    competences: list | dict | None = None
    langues: list | dict | None = None
    code_cv: str


class ResultatRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_resultat: uuid.UUID
    id_offre: uuid.UUID
    id_cv: uuid.UUID
    score_sim: float
    statut_candidature: str | None
    date_modification: datetime | None
    recommendation: str | None = None
    # Clé de catégorie alignée sur le front : rec, good, review, low
    categorie: str | None = None
    criteres_valides: list[CritereExplication] = Field(default_factory=list)
    ecarts: list[CritereExplication] = Field(default_factory=list)
    candidat: CandidatApercu | None = None


class HistoriqueStatutRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ancien_statut: str | None
    nouveau_statut: str
    date_changement: datetime
    id_utilisateur: uuid.UUID
