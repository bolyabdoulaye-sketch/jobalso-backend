from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.core.config import settings
from app.core.security import hash_password, verify_password, create_access_token
from app.core.unsubscribe import read_unsubscribe_token
from app.core.password_reset import make_reset_token, read_reset_token, extract_user_id
from app.models.utilisateur import Utilisateur, TypeUtilisateur, StatusUtilisateur
from app.models.entreprise import Entreprise
from app.models.candidat import Candidat
from app.models.recruteur import Recruteur
from app.schemas.utilisateur import UtilisateurCreate, UtilisateurRead
from app.schemas.password_reset import ForgotPasswordRequest, ResetPasswordRequest, MessageResponse
from app.services.email import send_welcome_email
from app.services.email_password_reset import send_password_reset_email

router = APIRouter(prefix="/auth", tags=["auth"])

# Version courante de la politique de confidentialité (JA-009).
# Incrémenter cette valeur à chaque mise à jour substantielle de la politique.
POLITIQUE_CONFIDENTIALITE_VERSION = "1.0"

# Message volontairement identique que l'email existe ou non (ne pas reveler
# quels comptes existent).
MESSAGE_FORGOT_PASSWORD = (
    "Si un compte existe avec cet email, un lien de reinitialisation vient de lui etre envoye."
)


def _page_html(titre: str, message: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{titre} - Jobalso</title>
</head>
<body style="margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;
font-family:Arial,Helvetica,sans-serif;background:linear-gradient(135deg,#063F79,#0D5298 55%,#187ACD);">
<div style="background:#fff;border-radius:16px;padding:36px;max-width:440px;text-align:center;
box-shadow:0 24px 60px rgba(6,20,32,0.16);">
<h2 style="color:#10202E;margin-top:0">{titre}</h2>
<p style="color:#587B95;font-size:14px">{message}</p>
</div>
</body>
</html>"""


@router.post("/register", response_model=UtilisateurRead, status_code=status.HTTP_201_CREATED)
def register(
    user_in: UtilisateurCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    existing = db.query(Utilisateur).filter(Utilisateur.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email deja utilise")

    existing_phone = db.query(Utilisateur).filter(Utilisateur.numero_telephone == user_in.numero_telephone).first()
    if existing_phone:
        raise HTTPException(status_code=400, detail="Numero de telephone deja utilise")

    if not user_in.consentement_accepte:
        raise HTTPException(
            status_code=400,
            detail="Vous devez accepter la politique de confidentialite pour creer un compte",
        )

    if user_in.type_utilisateur == TypeUtilisateur.RECRUTEUR and not user_in.entreprise:
        raise HTTPException(status_code=400, detail="Les informations d'entreprise sont requises pour un recruteur")

    utilisateur = Utilisateur(
        email=user_in.email,
        numero_telephone=user_in.numero_telephone,
        mot_de_passe=hash_password(user_in.mot_de_passe),
        nom_prenom=user_in.nom_prenom,
        type_utilisateur=user_in.type_utilisateur,
        status=StatusUtilisateur.EN_ATTENTE,
        consentement_accepte=True,
        consentement_date=datetime.utcnow(),
        consentement_version=POLITIQUE_CONFIDENTIALITE_VERSION,
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

    # Email de bienvenue envoyé en arrière-plan (JA-080)
    background_tasks.add_task(send_welcome_email, utilisateur.email, utilisateur.nom_prenom)

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


# Désabonnement des notifications par email (JA-083, CASL).
# GET : clic sur le lien dans l'email. POST : "one-click unsubscribe" des clients mail.
@router.api_route("/desabonnement", methods=["GET", "POST"], response_class=HTMLResponse)
def desabonnement(token: str, db: Session = Depends(get_db)):
    user_id = read_unsubscribe_token(token)
    utilisateur = db.get(Utilisateur, user_id) if user_id else None
    if utilisateur is None:
        return HTMLResponse(
            _page_html("Lien invalide", "Ce lien de désabonnement est invalide ou incomplet."),
            status_code=400,
        )

    utilisateur.notifications_email = False
    db.commit()
    return HTMLResponse(
        _page_html(
            "Désabonnement confirmé",
            "Vous ne recevrez plus de notifications par email de Jobalso. "
            "Vous continuerez à recevoir les emails essentiels liés à votre compte.",
        )
    )


# Mot de passe oublie (JA-004)
@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(
    data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    utilisateur = db.query(Utilisateur).filter(Utilisateur.email == data.email).first()

    if utilisateur and utilisateur.status != StatusUtilisateur.SUPPRIME:
        token = make_reset_token(utilisateur)
        reset_url = f"{settings.FRONTEND_URL}/reinitialiser-mot-de-passe?token={token}"
        background_tasks.add_task(
            send_password_reset_email,
            utilisateur.email,
            utilisateur.nom_prenom,
            reset_url,
        )

    # Meme reponse dans tous les cas : on ne revele jamais si l'email existe.
    return MessageResponse(message=MESSAGE_FORGOT_PASSWORD)


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    user_id = extract_user_id(data.token)
    utilisateur = db.get(Utilisateur, user_id) if user_id else None

    if utilisateur is None or not read_reset_token(data.token, utilisateur):
        raise HTTPException(status_code=400, detail="Lien invalide ou expire")

    if utilisateur.status == StatusUtilisateur.SUPPRIME:
        raise HTTPException(status_code=400, detail="Lien invalide ou expire")

    utilisateur.mot_de_passe = hash_password(data.nouveau_mot_de_passe)
    utilisateur.must_change_password = False
    if utilisateur.status == StatusUtilisateur.EN_ATTENTE:
        utilisateur.status = StatusUtilisateur.ACTIF
    db.commit()

    return MessageResponse(message="Votre mot de passe a ete reinitialise avec succes.")
