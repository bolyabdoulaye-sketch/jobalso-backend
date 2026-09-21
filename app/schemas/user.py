import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, model_validator
from app.models.user import UserRole, RecruteurPersona


class UserCreate(BaseModel):
    email: EmailStr
    mot_de_passe: str = Field(min_length=8)
    role: UserRole
    persona: RecruteurPersona | None = None
    consentement_accepte: bool

    @model_validator(mode="after")
    def check_persona_only_for_recruteur(self):
        if self.role != UserRole.RECRUTEUR and self.persona is not None:
            raise ValueError("Le persona ne peut etre defini que pour un compte recruteur")
        return self


class UserLogin(BaseModel):
    email: EmailStr
    mot_de_passe: str


class UserRead(BaseModel):
    id: uuid.UUID
    email: EmailStr
    role: UserRole
    persona: RecruteurPersona | None
    est_actif: bool
    email_verifie: bool
    cree_le: datetime

    class Config:
        from_attributes = True