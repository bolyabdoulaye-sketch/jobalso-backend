from pydantic import BaseModel, ConfigDict, EmailStr
from uuid import UUID
from datetime import datetime
from typing import Optional
from app.models.database import MiniTypeUtilisateurEnum, MiniStatusUtilisateurEnum

# --- Inscription Utilisateur ---
class UtilisateurCreate(BaseModel):
    email: EmailStr
    numero_telephone: str
    mot_de_passe: str
    nom_prenom: str
    type_utilisateur: MiniTypeUtilisateurEnum

    nom_entreprise: Optional[str] = None
    pays: Optional[str] = None
    localisation_entreprise: Optional[str]=None

# --- Réponse Utilisateur (sans le mot de passe !) ---
class UtilisateurRead(BaseModel):
    id_utilisateur: UUID
    email: EmailStr
    numero_telephone: str
    nom_prenom: str
    type_utilisateur: MiniTypeUtilisateurEnum
    status: MiniStatusUtilisateurEnum
    date_creation: datetime

    model_config = ConfigDict(from_attributes=True)

# --- Connexion / Login ---
class LoginRequest(BaseModel):
    email: EmailStr
    mot_de_passe: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str
