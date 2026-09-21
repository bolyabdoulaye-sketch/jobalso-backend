import uuid
from datetime import datetime
from pydantic import BaseModel
from app.models.matching import MatchingClassification


class MatchingScoreRead(BaseModel):
    id: uuid.UUID
    poste_id: uuid.UUID
    profil_candidat_id: uuid.UUID
    score: int
    classification: MatchingClassification
    version_modele: str
    cree_le: datetime
    modifie_le: datetime

    class Config:
        from_attributes = True


class MatchingLogRead(BaseModel):
    id: uuid.UUID
    score_matching_id: uuid.UUID
    instantane_entrees: dict
    score_resultat: int
    explication_resultat: dict
    version_modele: str
    cree_le: datetime

    class Config:
        from_attributes = True