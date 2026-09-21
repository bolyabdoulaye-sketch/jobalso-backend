import uuid
from datetime import datetime
from pydantic import BaseModel
from app.models.candidate import CVAnalysisStatus, SkillType, SkillSource


class CandidateProfileRead(BaseModel):
    id: uuid.UUID
    utilisateur_id: uuid.UUID
    localisation: str | None
    type_poste_recherche: str | None
    taux_completude: int
    consentement_banque_profils_le: datetime | None
    cree_le: datetime

    class Config:
        from_attributes = True


class CandidateProfileUpdate(BaseModel):
    localisation: str | None = None
    type_poste_recherche: str | None = None


class CVRead(BaseModel):
    id: uuid.UUID
    profil_candidat_id: uuid.UUID
    chemin_fichier: str
    type_fichier: str
    statut_analyse: CVAnalysisStatus
    est_actuel: bool
    depose_le: datetime

    class Config:
        from_attributes = True


class CandidateSkillCreate(BaseModel):
    type_competence: SkillType
    valeur: str
    source: SkillSource = SkillSource.EXTRAIT


class CandidateSkillRead(BaseModel):
    id: uuid.UUID
    type_competence: SkillType
    valeur: str
    source: SkillSource

    class Config:
        from_attributes = True