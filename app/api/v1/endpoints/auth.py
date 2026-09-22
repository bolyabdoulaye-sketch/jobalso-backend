from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.core.security import hash_password, verify_password, create_access_token
from app.models.utilisateur import Utilisateur, TypeUtilisateur, StatusUtilisateur
from app.models.entreprise import Entreprise
from app.models.candidat import Candidat
from app.models.recruteur import Recruteur
from app.schemas.utilisateur import UtilisateurCreate, UtilisateurRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UtilisateurRead, status_code=status.HTTP_201_CREATED)
def register(user_in: UtilisateurCreate, db: Session = Depends(get_db)):
    existing = db.query(Utilisateur).filter(Utilisateur.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email deja utilise")

    if user_in.type_utilisateur == TypeUtilisateur.RECRUTEUR and not user_in.entreprise:
        raise HTTPException(status_code=400, detail="Les informations d'entreprise sont requises pour un recruteur")

    utilisateur = Utilisateur(
        email=user_in.email,
        numero_telephone=user_in.numero_telephone,
        mot_de_passe=hash_password(user_in.mot_de_passe),
        nom_prenom=user_in.nom_prenom,
        type_utilisateur=user_in.type_utilisateur,
        status=StatusUtilisateur.EN_ATTENTE,
    )
    db.add(utilisateur)
    db.flush()

    if user_in.type_utilisateur == TypeUtilisateur.CANDIDAT:
        candidat = Candidat(id_utilisateur=utilisateur.id_utilisateur)
        db.add(candidat)
    else:
        entreprise = Entreprise(
            nom_entreprise=user_in.entreprise.nom_entreprise,
            pays=user_in.entreprise.pays,
            localisation_entreprise=user_in.entreprise.localisation_entreprise,
        )
        db.add(entreprise)
        db.flush()

        recruteur = Recruteur(
            id_utilisateur=utilisateur.id_utilisateur,
            id_entreprise=entreprise.id_entreprise,
        )
        db.add(recruteur)

    db.commit()
    db.refresh(utilisateur)
    return utilisateur


@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    utilisateur = db.query(Utilisateur).filter(Utilisateur.email == form_data.username).first()
    if not utilisateur or not verify_password(form_data.password, utilisateur.mot_de_passe):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
        )
    if utilisateur.status == StatusUtilisateur.SUPPRIME:
        raise HTTPException(status_code=403, detail="Compte supprime")
    if utilisateur.status == StatusUtilisateur.INACTIF:
        raise HTTPException(status_code=403, detail="Compte inactif")

    access_token = create_access_token(subject=str(utilisateur.id_utilisateur))
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UtilisateurRead)
def read_current_user(current_user: Utilisateur = Depends(get_current_user)):
    return current_user