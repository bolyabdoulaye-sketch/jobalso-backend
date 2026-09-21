import uuid
import secrets
from datetime import datetime
from pydantic import BaseModel


class CVCreate(BaseModel):
    resume_cv: str | None = None
    experience: dict | list | None = None
    education: dict | list | None = None
    langues: dict | list | None = None
    domaine_etude: dict | list | None = None
    competences: dict | list | None = None
    certifications: dict | list | None = None


class CVUpdate(BaseModel):
    resume_cv: str | None = None
    experience: dict | list | None = None
    education: dict | list | None = None
    langues: dict | list | None = None
    domaine_etude: dict | list | None = None
    competences: dict | list | None = None
    certifications: dict | list | None = None


class CVRead(BaseModel):
    id_cv: uuid.UUID
    id_candidat: uuid.UUID
    resume_cv: str | None
    experience: dict | list | None
    education: dict | list | None
    langues: dict | list | None
    domaine_etude: dict | list | None
    competences: dict | list | None
    certifications: dict | list | None
    statut_cv: str | None
    code_cv: str
    date_creation: datetime
    date_modification: datetime | None

    class Config:
        from_attributes = True


def generate_code_cv() -> str:
    # Code court, lisible, a partager au recruteur
    return secrets.token_hex(4).upper()