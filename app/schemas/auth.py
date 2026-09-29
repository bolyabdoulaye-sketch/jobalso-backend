from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.utilisateur import valider_mot_de_passe


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    type_utilisateur: str
    persona: str | None = None


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=10, max_length=200)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=10, max_length=300)
    nouveau_mot_de_passe: str = Field(min_length=8)

    _mot_de_passe = field_validator("nouveau_mot_de_passe")(valider_mot_de_passe)


class ChangePasswordRequest(BaseModel):
    ancien_mot_de_passe: str
    nouveau_mot_de_passe: str = Field(min_length=8)

    _mot_de_passe = field_validator("nouveau_mot_de_passe")(valider_mot_de_passe)


class VerifyEmailRequest(BaseModel):
    token: str = Field(min_length=10, max_length=300)


class MessageResponse(BaseModel):
    message: str
