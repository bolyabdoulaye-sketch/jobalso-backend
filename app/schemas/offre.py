import uuid
from datetime import datetime, date
from pydantic import BaseModel


class OffreCreate(BaseModel):
    titre_offre: str
    description: dict | list | None = None
    type_contrat: str | None = None
    revenu: float | None = None
    date_fin: date | None = None
    resume_offre: str | None = None


class OffreUpdate(BaseModel):
    titre_offre: str | None = None
    description: dict | list | None = None
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

    class Config:
        from_attributes = True
