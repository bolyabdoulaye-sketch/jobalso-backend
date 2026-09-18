import uuid
from datetime import datetime
from pydantic import BaseModel


class ShortlistEntryCreate(BaseModel):
    poste_id: uuid.UUID
    profil_candidat_id: uuid.UUID


class ShortlistEntryRead(BaseModel):
    id: uuid.UUID
    poste_id: uuid.UUID
    profil_candidat_id: uuid.UUID
    selectionne_pour_comparaison: bool
    ajoute_le: datetime

    class Config:
        from_attributes = True