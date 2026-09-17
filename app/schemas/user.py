import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
from app.models.user import UserRole, RecruteurPersona


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    role: UserRole
    persona: RecruteurPersona | None = None
    consent_accepted: bool


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
