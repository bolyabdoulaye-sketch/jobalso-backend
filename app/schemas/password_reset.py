from pydantic import BaseModel, EmailStr, Field


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    nouveau_mot_de_passe: str = Field(min_length=8)


class MessageResponse(BaseModel):
    message: str
