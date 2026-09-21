import uuid
from datetime import datetime
from pydantic import BaseModel
from app.models.user import RecruteurPersona


class JobTemplateCriterionCreate(BaseModel):
    type_critere: str
    valeur: str
    niveau: str


class JobTemplateCreate(BaseModel):
    titre: str
    description: str | None = None
    personas: list[RecruteurPersona]
    criteres: list[JobTemplateCriterionCreate]


class JobTemplateRead(BaseModel):
    id: uuid.UUID
    titre: str
    description: str | None
    est_publie: bool
    cree_par: uuid.UUID
    cree_le: datetime

    class Config:
        from_attributes = True