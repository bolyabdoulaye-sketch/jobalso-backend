import uuid
from datetime import datetime
from pydantic import BaseModel
from app.models.interview import InterviewStatus


class InterviewSimulationCreate(BaseModel):
    poste_id: uuid.UUID
    consentement_accepte: bool


class InterviewSimulationRead(BaseModel):
    id: uuid.UUID
    poste_id: uuid.UUID
    profil_candidat_id: uuid.UUID
    statut: InterviewStatus
    consentement_donne_le: datetime | None
    partage_avec_recruteur: bool
    cree_le: datetime

    class Config:
        from_attributes = True


class InterviewQuestionRead(BaseModel):
    id: uuid.UUID
    ordre: int
    texte_question: str

    class Config:
        from_attributes = True


class InterviewAnswerCreate(BaseModel):
    question_id: uuid.UUID
    texte_reponse: str


class InterviewAnswerRead(BaseModel):
    id: uuid.UUID
    question_id: uuid.UUID
    texte_reponse: str
    texte_relance: str | None
    repondu_le: datetime

    class Config:
        from_attributes = True


class InterviewFeedbackRead(BaseModel):
    id: uuid.UUID
    simulation_id: uuid.UUID
    points_forts: dict
    axes_amelioration: dict
    cree_le: datetime

    class Config:
        from_attributes = True