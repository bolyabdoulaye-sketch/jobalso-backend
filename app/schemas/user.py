import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, model_validator
from app.models.user import UserRole, RecruteurPersona


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    role: UserRole
    persona: RecruteurPersona | None = None
    consent_accepted: bool

    @model_validator(mode="after")
    def check_persona_only_for_recruteur(self):
        if self.role != UserRole.RECRUTEUR and self.persona is not None:
            raise ValueError("Le persona ne peut etre defini que pour un compte recruteur")
        return self


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserRead(BaseModel):
    id: uuid.UUID
    email: EmailStr
    role: UserRole
    persona: RecruteurPersona | None
    is_active: bool
    is_email_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True
