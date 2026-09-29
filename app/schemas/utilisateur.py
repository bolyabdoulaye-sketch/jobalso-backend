import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.utilisateur import TypeUtilisateur, StatusUtilisateur


def valider_mot_de_passe(valeur: str) -> str:
    # bcrypt ne prend en compte que les 72 premiers octets.
    if len(valeur.encode()) > 72:
        raise ValueError("Le mot de passe ne doit pas depasser 72 octets")
    return valeur


class UtilisateurCreate(BaseModel):
    email: EmailStr
    numero_telephone: str = Field(min_length=6, max_length=30)
    mot_de_passe: str = Field(min_length=8)
    nom_prenom: str = Field(min_length=2, max_length=255)
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

    # Compte recruteur : nom de l'organisation créée à l'inscription.
    # À défaut, « Organisation de <nom> ».
    nom_organisation: str | None = Field(default=None, max_length=255)

    _mot_de_passe = field_validator("mot_de_passe")(valider_mot_de_passe)

    @field_validator("email")
    @classmethod
    def _email_minuscule(cls, valeur: str) -> str:
        return valeur.strip().lower()


class PersonaRecruteurRequest(BaseModel):
    persona: str = Field(min_length=1)


class UtilisateurRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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
    id_organisation: uuid.UUID | None = None
    role_organisation: str | None = None
