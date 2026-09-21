from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from app.api.deps import get_db, get_current_user
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    generate_reset_token,
)
from app.models.user import User, UserRole
from app.models.candidate import CandidateProfile
from app.models.password_reset_token import PasswordResetToken
from app.schemas.user import UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email deja utilise")

    if not user_in.consentement_accepte:
        raise HTTPException(status_code=400, detail="Consentement requis pour creer un compte")

    user = User(
        email=user_in.email,
        mot_de_passe_hache=hash_password(user_in.mot_de_passe),
        role=user_in.role,
        persona=user_in.persona,
        consentement_donne_le=datetime.utcnow(),
        version_politique_consentement="v1",
    )
    db.add(user)
    db.flush()  # pour obtenir user.id avant de creer le profil

    if user.role == UserRole.CANDIDAT:
        profil = CandidateProfile(utilisateur_id=user.id)
        db.add(profil)

    db.commit()
    db.refresh(user)
    return user


@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.mot_de_passe_hache):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
        )
    if not user.est_actif:
        raise HTTPException(status_code=403, detail="Compte desactive")

    access_token = create_access_token(subject=str(user.id))
    return {"access_token": access_token, "token_type": "bearer"}


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    jeton: str
    nouveau_mot_de_passe: str


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        return {"detail": "Si ce compte existe, un lien de reinitialisation a ete envoye"}

    jeton = generate_reset_token()
    reset_entry = PasswordResetToken(
        utilisateur_id=user.id,
        jeton=jeton,
        expire_le=datetime.utcnow() + timedelta(minutes=30),
        utilise=False,
    )
    db.add(reset_entry)
    db.commit()

    return {
        "detail": "Si ce compte existe, un lien de reinitialisation a ete envoye",
        "reset_token": jeton,
    }


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    reset_entry = db.query(PasswordResetToken).filter(
        PasswordResetToken.jeton == payload.jeton
    ).first()

    if not reset_entry:
        raise HTTPException(status_code=400, detail="Token invalide")

    if reset_entry.utilise:
        raise HTTPException(status_code=400, detail="Ce lien a deja ete utilise")

    if reset_entry.expire_le < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Ce lien a expire")

    user = db.query(User).filter(User.id == reset_entry.utilisateur_id).first()
    if not user:
        raise HTTPException(status_code=400, detail="Token invalide")

    user.mot_de_passe_hache = hash_password(payload.nouveau_mot_de_passe)
    reset_entry.utilise = True

    db.commit()
    return {"detail": "Mot de passe reinitialise avec succes"}


@router.get("/me", response_model=UserRead)
def read_current_user(current_user=Depends(get_current_user)):
    return current_user