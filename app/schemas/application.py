import uuid
from datetime import datetime
from pydantic import BaseModel
from app.models.application import PipelineStage


class ApplicationCreate(BaseModel):
    poste_id: uuid.UUID
    profil_candidat_id: uuid.UUID


class ApplicationRead(BaseModel):
    id: uuid.UUID
    poste_id: uuid.UUID
    profil_candidat_id: uuid.UUID
    etape_actuelle: PipelineStage
    postule_le: datetime

    class Config:
        from_attributes = True


class PipelineEventRead(BaseModel):
    id: uuid.UUID
    candidature_id: uuid.UUID
    etape_origine: PipelineStage | None
    etape_destination: PipelineStage
    survenu_le: datetime

    class Config:
        from_attributes = True