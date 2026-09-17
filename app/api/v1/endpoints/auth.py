from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from app.api.deps import get_db
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    generate_reset_token,
)
from app.models.user import User
from app.models.password_reset_token import PasswordResetToken
from app.schemas.user import UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email deja utilise")

    if not user_in.consent_accepted:
        raise HTTPException(status_code=400, detail="Consentement requis pour creer un compte")

    user = User(
        email=user_in.email,
        hashed_password=hash_password(user_in.password),
        role=user_in.role,
        persona=user_in.persona,
        consent_given_at=datetime.utcnow(),
        consent_policy_version="v1",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Compte desactive")

    access_token = create_access_token(subject=str(user.id))
    return {"access_token": access_token, "token_type": "bearer"}


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        # JA-004 : ne pas reveler si l email existe ou non
        return {"detail": "Si ce compte existe, un lien de reinitialisation a ete envoye"}

    token = generate_reset_token()
    reset_entry = PasswordResetToken(
        user_id=user.id,
        token=token,
        expires_at=datetime.utcnow() + timedelta(minutes=30),  # JA-004 : expire en 30 min
        used=False,
    )
    db.add(reset_entry)
    db.commit()

    # TODO : envoyer par email une fois le service SMTP configure
    return {
        "detail": "Si ce compte existe, un lien de reinitialisation a ete envoye",
        "reset_token": token,
    }


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    reset_entry = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == payload.token
    ).first()

    if not reset_entry:
        raise HTTPException(status_code=400, detail="Token invalide")

    if reset_entry.used:
        raise HTTPException(status_code=400, detail="Ce lien a deja ete utilise")

    if reset_entry.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Ce lien a expire")

    user = db.query(User).filter(User.id == reset_entry.user_id).first()
    if not user:
        raise HTTPException(status_code=400, detail="Token invalide")

    user.hashed_password = hash_password(payload.new_password)
    reset_entry.used = True  # JA-004 : usage unique

    db.commit()
    return {"detail": "Mot de passe reinitialise avec succes"}


from app.api.deps import get_current_user
from app.schemas.user import UserRead as _UserReadForMe


@router.get("/me", response_model=_UserReadForMe)
def read_current_user(current_user=Depends(get_current_user)):
    return current_user

