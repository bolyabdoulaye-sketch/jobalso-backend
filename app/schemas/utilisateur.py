import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
from app.models.utilisateur import TypeUtilisateur, StatusUtilisateur


class EntrepriseCreate(BaseModel):
    nom_entreprise: str
    pays: str
    localisation_entreprise: str | None = None


class UtilisateurCreate(BaseModel):
    email: EmailStr
    numero_telephone: str
    mot_de_passe: str = Field(min_length=8)
    nom_prenom: str
    type_utilisateur: TypeUtilisateur

    # Requis uniquement si type_utilisateur == RECRUTEUR
    entreprise: EntrepriseCreate | None = None


class UtilisateurLogin(BaseModel):
    email: EmailStr
    mot_de_passe: str


class UtilisateurRead(BaseModel):
    id_utilisateur: uuid.UUID
    email: EmailStr
    numero_telephone: str
    nom_prenom: str
    type_utilisateur: TypeUtilisateur
    status: StatusUtilisateur
    date_creation: datetime
    must_change_password: bool

    class Config:
        from_attributes = True