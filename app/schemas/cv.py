import uuid
import secrets
from datetime import datetime
from pydantic import BaseModel, computed_field


class CVCreate(BaseModel):
    resume_cv: str | None = None
    experience: dict | list | None = None
    education: dict | list | None = None
    langues: dict | list | None = None
    domaine_etude: dict | list | None = None
    competences: dict | list | None = None
    certifications: dict | list | None = None
    localisation: str | None = None
    type_poste_recherche: str | None = None


class CVUpdate(BaseModel):
    resume_cv: str | None = None
    experience: dict | list | None = None
    education: dict | list | None = None
    langues: dict | list | None = None
    domaine_etude: dict | list | None = None
    competences: dict | list | None = None
    certifications: dict | list | None = None
    localisation: str | None = None
    type_poste_recherche: str | None = None


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
    localisation: str | None
    type_poste_recherche: str | None
    statut_cv: str | None
    code_cv: str
    date_creation: datetime
    date_modification: datetime | None

    class Config:
        from_attributes = True

    @computed_field
    @property
    def taux_completude(self) -> int:
        # JA-035 : proportion de champs remplis parmi les champs pertinents du profil
        champs = [
            self.resume_cv,
            self.experience,
            self.education,
            self.langues,
            self.domaine_etude,
            self.competences,
            self.certifications,
            self.localisation,
            self.type_poste_recherche,
        ]
        remplis = sum(1 for c in champs if c not in (None, "", [], {}))
        return round(remplis / len(champs) * 100)


def generate_code_cv() -> str:
    return secrets.token_hex(4).upper()