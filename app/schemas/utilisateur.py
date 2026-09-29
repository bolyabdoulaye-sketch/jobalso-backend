import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.utilisateur import TypeUtilisateur, StatusUtilisateur


class UtilisateurCreate(BaseModel):
    email: EmailStr
    numero_telephone: str
    mot_de_passe: str = Field(min_length=8)
    nom_prenom: str
    type_utilisateur: TypeUtilisateur
    consentement_accepte: bool = Field(
        description=(
            "L'utilisateur doit accepter la politique "
            "de confidentialité."
        )
    )

    # Persona uniquement utilisé pour un compte recruteur.
    # Il est enregistré au moment de la création du compte.
    persona: str | None = None


class UtilisateurLogin(BaseModel):
    email: EmailStr
    mot_de_passe: str


class PersonaRecruteurRequest(BaseModel):
    persona: str = Field(min_length=1)


class UtilisateurRead(BaseModel):
    id_utilisateur: uuid.UUID
    email: EmailStr
    numero_telephone: str
    nom_prenom: str
    type_utilisateur: TypeUtilisateur
    status: StatusUtilisateur
    date_creation: datetime
    must_change_password: bool
    consentement_accepte: bool
    consentement_date: datetime | None
    consentement_version: str | None
    persona: str | None = None

    class Config:
        from_attributes = True