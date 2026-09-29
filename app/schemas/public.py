import uuid

from pydantic import BaseModel, EmailStr, Field


class PublicOffreRead(BaseModel):
    id_offre: uuid.UUID
    titre_offre: str
    type_contrat: str | None = None
    resume_offre: str | None = None

    class Config:
        from_attributes = True


class PostulerPublic(BaseModel):
    nom_prenom: str = Field(min_length=2, max_length=255)
    email: EmailStr
    numero_telephone: str = Field(min_length=6, max_length=30)
    resume_cv: str | None = Field(default=None, max_length=5000)
    competences: list[str] = Field(default_factory=list, max_length=50)
    langues: list[str] = Field(default_factory=list, max_length=20)
    consentement_accepte: bool

    # Champ piege anti-spam : invisible pour un humain, rempli par les robots
    site_web: str | None = Field(default=None, examples=[""])


class PostulerResponse(BaseModel):
    message: str
