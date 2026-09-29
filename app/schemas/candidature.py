import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.statut_candidature import StatutCandidature


class StatutUpdate(BaseModel):
    statut: StatutCandidature


class CandidatureRead(BaseModel):
    id_resultat: uuid.UUID
    id_offre: uuid.UUID
    titre_offre: str
    statut_candidature: str | None
    libelle_statut: str
    date_modification: datetime | None
