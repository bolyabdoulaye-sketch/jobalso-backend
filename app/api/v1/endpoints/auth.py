from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
    status,
)
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.core.config import settings
from app.core.dates import utcnow
from app.core.rate_limit import check_rate_limit, limiter, record_hit
from app.core.security import (
    hash_password,
    verify_password,
)
from app.models.utilisateur import (
    Utilisateur,
    TypeUtilisateur,
    StatusUtilisateur,
)
from app.models.candidat import Candidat
from app.models.recruteur import Recruteur
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    MessageResponse,
    RefreshRequest,
    ResetPasswordRequest,
    TokenResponse,
    VerifyEmailRequest,
)
from app.schemas.utilisateur import (
    UtilisateurCreate,
    UtilisateurRead,
    PersonaRecruteurRequest,
)
from app.services import comptes
from app.services.email_compte import send_verification_email
from app.services.email_password_reset import send_password_reset_email


router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)


# Version courante de la politique de confidentialité.
POLITIQUE_CONFIDENTIALITE_VERSION = "1.0"


PERSONAS_RECRUTEUR_AUTORISEES = {
    "pme",
    "entrepreneur",
    "rh",
    "recruteur",
    "gestionnaire",
}

MESSAGE_EMAIL_ENVOYE = "Si un compte correspond a cet email, un message vient d'y etre envoye."


def trouver_par_email(db: Session, email: str) -> Utilisateur | None:
    return db.scalar(
        select(Utilisateur).where(func.lower(Utilisateur.email) == email.strip().lower())
    )


def _persona(db: Session, utilisateur: Utilisateur) -> str | None:
    if utilisateur.type_utilisateur != TypeUtilisateur.RECRUTEUR:
        return None
    recruteur = db.scalar(select(Recruteur).where(Recruteur.id_utilisateur == utilisateur.id_utilisateur))
    return recruteur.persona if recruteur else None


def _reponse_jetons(db: Session, utilisateur: Utilisateur) -> TokenResponse:
    access_token, refresh_token = comptes.ouvrir_session(db, utilisateur)
    db.commit()
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_MINUTES * 60,
        type_utilisateur=utilisateur.type_utilisateur.value,
        persona=_persona(db, utilisateur),
    )


def _verifier_statut_connexion(utilisateur: Utilisateur) -> None:
    if utilisateur.status == StatusUtilisateur.SUPPRIME:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Compte supprime")
    if utilisateur.status == StatusUtilisateur.INACTIF:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Compte inactif")


@router.post(
    "/register",
    response_model=UtilisateurRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(limiter("register", 10, 3600))],
)
def register(
    user_in: UtilisateurCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    if trouver_par_email(db, user_in.email):
        raise HTTPException(
            status_code=400,
            detail="Email deja utilise",
        )

    existing_phone = db.scalar(
        select(Utilisateur).where(Utilisateur.numero_telephone == user_in.numero_telephone)
    )
    if existing_phone:
        raise HTTPException(
            status_code=400,
            detail="Numero de telephone deja utilise",
        )

    if not user_in.consentement_accepte:
        raise HTTPException(
            status_code=400,
            detail=(
                "Vous devez accepter la politique de "
                "confidentialite pour creer un compte"
            ),
        )

    if user_in.type_utilisateur == TypeUtilisateur.CANDIDAT and (
        user_in.persona is not None or user_in.nom_organisation is not None
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Un compte candidat ne peut pas definir "
                "de persona ni d'organisation."
            ),
        )

    persona = user_in.persona.strip().lower() if user_in.persona else None
    if (
        user_in.type_utilisateur == TypeUtilisateur.RECRUTEUR
        and persona is not None
        and persona not in PERSONAS_RECRUTEUR_AUTORISEES
    ):
        raise HTTPException(
            status_code=400,
            detail="Persona recruteur invalide.",
        )

    utilisateur = Utilisateur(
        email=user_in.email,
        numero_telephone=user_in.numero_telephone,
        mot_de_passe=hash_password(user_in.mot_de_passe),
        nom_prenom=user_in.nom_prenom.strip(),
        type_utilisateur=user_in.type_utilisateur,
        status=StatusUtilisateur.EN_ATTENTE,
        consentement_accepte=True,
        consentement_date=utcnow(),
        consentement_version=POLITIQUE_CONFIDENTIALITE_VERSION,
    )

    db.add(utilisateur)
    db.flush()

    if user_in.type_utilisateur == TypeUtilisateur.CANDIDAT:
        db.add(Candidat(id_utilisateur=utilisateur.id_utilisateur))
    else:
        db.add(Recruteur(id_utilisateur=utilisateur.id_utilisateur, persona=persona))
        # JA-008 : sans organisation, un recruteur ne peut créer aucune offre.
        comptes.creer_organisation(db, utilisateur, user_in.nom_organisation)

    db.commit()
    db.refresh(utilisateur)

    background_tasks.add_task(
        send_verification_email,
        utilisateur.email,
        utilisateur.nom_prenom,
        comptes.url_front("verifier-email", comptes.jeton_verification(utilisateur)),
    )

    return _lire_utilisateur(db, utilisateur)


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(limiter("login", 20, 60))],
)
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Connexion centrale Jobalso.

    L'utilisateur fournit :
    - email
    - mot de passe

    Le type de compte est déterminé automatiquement
    à partir du compte trouvé en base.

    Le champ OAuth2 "scope" reste accepté lorsqu'il est
    fourni depuis un parcours contextualisé, afin de
    conserver l'isolation stricte candidat/recruteur.

    Réponse : jeton d'accès (court) + jeton de rafraîchissement
    à échanger sur /auth/refresh.
    """
    # En plus de la limite par IP : 10 échecs par compte et par IP en 15 min.
    # Seuls les échecs comptent, et la clé inclut l'IP pour qu'un tiers ne
    # puisse pas bloquer le compte de quelqu'un d'autre depuis sa machine.
    ip = request.client.host if request.client else "inconnu"
    cle_echecs = f"login-echecs:{form_data.username.strip().lower()}:{ip}"
    check_rate_limit(cle_echecs, 10, 900, enregistrer=False)

    utilisateur = trouver_par_email(db, form_data.username)

    if not utilisateur or not verify_password(
        form_data.password,
        utilisateur.mot_de_passe,
    ):
        record_hit(cle_echecs)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
        )

    _verifier_statut_connexion(utilisateur)

    role_compte = (
        "candidat"
        if utilisateur.type_utilisateur == TypeUtilisateur.CANDIDAT
        else "recruteur"
    )

    scopes = form_data.scopes or []

    if len(scopes) > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Espace de connexion invalide.",
        )

    if len(scopes) == 1:
        role_demande = scopes[0].strip().lower()

        if role_demande not in {"candidat", "recruteur"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Espace de connexion invalide.",
            )

        if role_demande != role_compte:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Ces identifiants ne correspondent "
                    "pas a cet espace."
                ),
            )

    return _reponse_jetons(db, utilisateur)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    dependencies=[Depends(limiter("refresh", 60, 60))],
)
def refresh(data: RefreshRequest, db: Session = Depends(get_db)):
    """Échange un jeton de rafraîchissement contre une nouvelle paire (rotation)."""
    invalide = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session invalide ou expiree")

    session = comptes.trouver_session(db, data.refresh_token)
    if session is None:
        raise invalide

    if session.date_revocation is not None:
        # Jeton déjà utilisé : il a probablement été volé. On coupe tout.
        comptes.revoquer_sessions(db, session.id_utilisateur)
        db.commit()
        raise invalide

    if session.date_expiration <= utcnow():
        raise invalide

    utilisateur = db.get(Utilisateur, session.id_utilisateur)
    if utilisateur is None:
        raise invalide
    _verifier_statut_connexion(utilisateur)

    session.date_revocation = utcnow()
    return _reponse_jetons(db, utilisateur)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(data: RefreshRequest, db: Session = Depends(get_db)):
    """Révoque la session. Idempotent : un jeton inconnu ne renvoie pas d'erreur."""
    session = comptes.trouver_session(db, data.refresh_token)
    if session is not None and session.date_revocation is None:
        session.date_revocation = utcnow()
        db.commit()


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    dependencies=[Depends(limiter("forgot", 5, 900))],
)
def forgot_password(
    data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Envoie un lien de réinitialisation (JA-004). Même réponse que le compte existe ou non."""
    utilisateur = trouver_par_email(db, data.email)
    if utilisateur and utilisateur.status not in (StatusUtilisateur.SUPPRIME, StatusUtilisateur.INACTIF):
        background_tasks.add_task(
            send_password_reset_email,
            utilisateur.email,
            utilisateur.nom_prenom,
            comptes.url_front("reinitialiser-mot-de-passe", comptes.jeton_reset(utilisateur)),
        )
    return MessageResponse(message=MESSAGE_EMAIL_ENVOYE)


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    dependencies=[Depends(limiter("reset", 10, 900))],
)
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Définit un nouveau mot de passe à partir du lien reçu par email.

    Sert aussi à activer les comptes créés par une candidature publique.
    """
    utilisateur = comptes.utilisateur_du_jeton_reset(db, data.token)
    if utilisateur is None or utilisateur.status in (StatusUtilisateur.SUPPRIME, StatusUtilisateur.INACTIF):
        raise HTTPException(status_code=400, detail="Lien invalide ou expire")

    utilisateur.mot_de_passe = hash_password(data.nouveau_mot_de_passe)
    utilisateur.must_change_password = False
    # Le lien est arrivé dans sa boîte : l'adresse email est prouvée.
    if utilisateur.status == StatusUtilisateur.EN_ATTENTE:
        utilisateur.status = StatusUtilisateur.ACTIF
    comptes.revoquer_sessions(db, utilisateur.id_utilisateur)
    db.commit()
    return MessageResponse(message="Mot de passe mis a jour. Vous pouvez vous connecter.")


@router.post("/change-password", response_model=TokenResponse)
def change_password(
    data: ChangePasswordRequest,
    current_user: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change le mot de passe, ferme les autres sessions et en ouvre une nouvelle."""
    check_rate_limit(f"change-password:{current_user.id_utilisateur}", 5, 900)
    if not verify_password(data.ancien_mot_de_passe, current_user.mot_de_passe):
        raise HTTPException(status_code=400, detail="Mot de passe actuel incorrect")

    current_user.mot_de_passe = hash_password(data.nouveau_mot_de_passe)
    current_user.must_change_password = False
    comptes.revoquer_sessions(db, current_user.id_utilisateur)
    return _reponse_jetons(db, current_user)


@router.post("/verify-email", response_model=MessageResponse)
def verify_email(data: VerifyEmailRequest, db: Session = Depends(get_db)):
    utilisateur = comptes.utilisateur_du_jeton_verification(db, data.token)
    if utilisateur is None or utilisateur.status != StatusUtilisateur.EN_ATTENTE:
        raise HTTPException(status_code=400, detail="Lien invalide ou expire")
    utilisateur.status = StatusUtilisateur.ACTIF
    db.commit()
    return MessageResponse(message="Adresse email confirmee.")


@router.post("/resend-verification", response_model=MessageResponse)
def resend_verification(
    background_tasks: BackgroundTasks,
    current_user: Utilisateur = Depends(get_current_user),
):
    check_rate_limit(f"resend-verification:{current_user.id_utilisateur}", 3, 3600)
    if current_user.status != StatusUtilisateur.EN_ATTENTE:
        return MessageResponse(message="Adresse email deja confirmee.")
    background_tasks.add_task(
        send_verification_email,
        current_user.email,
        current_user.nom_prenom,
        comptes.url_front("verifier-email", comptes.jeton_verification(current_user)),
    )
    return MessageResponse(message="Email de confirmation renvoye.")


@router.post("/persona")
def save_recruiter_persona(
    data: PersonaRecruteurRequest,
    current_user: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.type_utilisateur != TypeUtilisateur.RECRUTEUR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Seul un recruteur peut définir "
                "un persona recruteur."
            ),
        )

    persona = data.persona.strip().lower()

    if persona not in PERSONAS_RECRUTEUR_AUTORISEES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Persona recruteur invalide.",
        )

    recruteur = db.scalar(select(Recruteur).where(Recruteur.id_utilisateur == current_user.id_utilisateur))

    if recruteur is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profil recruteur introuvable.",
        )

    recruteur.persona = persona

    db.commit()
    db.refresh(recruteur)

    return {"persona": recruteur.persona}


def _lire_utilisateur(db: Session, utilisateur: Utilisateur) -> UtilisateurRead:
    result = UtilisateurRead.model_validate(utilisateur)
    result.persona = _persona(db, utilisateur)
    if utilisateur.type_utilisateur == TypeUtilisateur.RECRUTEUR:
        membre = comptes.adhesion(db, utilisateur)
        if membre is not None:
            result.id_organisation = membre.id_organisation
            result.role_organisation = membre.role.value
    return result


@router.get(
    "/me",
    response_model=UtilisateurRead,
)
def read_current_user(
    current_user: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _lire_utilisateur(db, current_user)
