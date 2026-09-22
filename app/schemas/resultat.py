import uuid
from datetime import datetime
from pydantic import BaseModel


class MatchingRequest(BaseModel):
    code_cv: str
    id_offre: uuid.UUID


class ResultatRead(BaseModel):
    id_resultat: uuid.UUID
    id_offre: uuid.UUID
    id_cv: uuid.UUID
    score_sim: float
    statut_candidature: str | None
    date_modification: datetime | None

    class Config:
        from_attributes = True