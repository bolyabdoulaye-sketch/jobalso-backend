import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class MatchingRequest(BaseModel):
    code_cv: str
    id_offre: uuid.UUID


class CritereExplication(BaseModel):
    libelle: str
    niveau: str


class ResultatRead(BaseModel):
    id_resultat: uuid.UUID
    id_offre: uuid.UUID
    id_cv: uuid.UUID
    score_sim: float
    statut_candidature: str | None
    date_modification: datetime | None
    recommendation: str | None = None
    criteres_valides: list[CritereExplication] = Field(default_factory=list)
    ecarts: list[CritereExplication] = Field(default_factory=list)

    class Config:
        from_attributes = True
