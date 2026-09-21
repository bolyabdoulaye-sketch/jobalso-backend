import uuid
from datetime import datetime
from pydantic import BaseModel
from app.models.job import JobStatus, JobCreationMode, CriterionLevel, CriterionType


class JobCriterionCreate(BaseModel):
    type_critere: CriterionType
    valeur: str
    niveau: CriterionLevel


class JobCriterionRead(BaseModel):
    id: uuid.UUID
    type_critere: CriterionType
    valeur: str
    niveau: CriterionLevel

    class Config:
        from_attributes = True


class JobCreate(BaseModel):
    mode_creation: JobCreationMode
    titre: str | None = None
    description_brute: str | None = None


class JobRead(BaseModel):
    id: uuid.UUID
    recruteur_id: uuid.UUID
    titre: str | None
    description_brute: str | None
    description_generee: str | None
    statut: JobStatus
    mode_creation: JobCreationMode
    jeton_lien_candidature: str
    publie_le: datetime | None
    cree_le: datetime

    class Config:
        from_attributes = True