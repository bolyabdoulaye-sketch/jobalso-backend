import secrets

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import EmailStr
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.v1.endpoints.auth import POLITIQUE_CONFIDENTIALITE_VERSION
from app.core.dates import utcnow
from app.core.rate_limit import limiter
from app.core.security import hash_password
from app.core.storage import delete_file
from app.models.utilisateur import Utilisateur, TypeUtilisateur, StatusUtilisateur
from app.models.candidat import Candidat
from app.models.cv import CV
from app.models.offre import Offre
from app.schemas.cv import generate_code_cv
from app.schemas.public import PublicOffreRead, PostulerResponse
from app.services import comptes
from app.services.candidature import creer_candidature
from app.services.cv_upload import lire_fichier_borne, valider_et_stocker_cv
from app.services.email_candidature import send_application_receipt_email

router = APIRouter(prefix="/public", tags=["public"])

MESSAGE_SUCCES = "Votre candidature a bien ete recue. Un email de confirmation vous a ete envoye."


def offre_active(token: str, db: Session) -> Offre:
    offre = db.query(Offre).filter(Offre.lien_token == token, Offre.status.is_(True)).first()
    if not offre:
        raise HTTPException(status_code=404, detail="Offre introuvable ou fermee")
    return offre


@router.get("/offres/{token}", response_model=PublicOffreRead)
def get_public_offre(token: str, db: Session = Depends(get_db)):
    return offre_active(token, db)


# Candidature publique sans compte (JA-027) + accuse de reception (JA-081).
# Fonction synchrone : la lecture du CV ne bloque pas le serveur.
@router.post(
    "/offres/{token}/postuler",
    response_model=PostulerResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(limiter("postuler", 10, 3600))],
)
def postuler(
    token: str,
    background_tasks: BackgroundTasks,
    nom_prenom: str = Form(..., min_length=2, max_length=255),
    email: EmailStr = Form(...),
    numero_telephone: str = Form(..., min_length=6, max_length=30),
    consentement_accepte: bool = Form(...),
    fichier_cv: UploadFile = File(...),
    resume_cv: str | None = Form(None, max_length=5000),
    competences: list[str] = Form(default=[]),
    langues: list[str] = Form(default=[]),
    site_web: str | None = Form(None),
    db: Session = Depends(get_db),
):
    """Candidature publique avec dépôt réel du CV (JA-027).

    Réservée aux personnes sans compte : un compte existant doit se connecter
    et postuler depuis son espace, sinon n'importe qui connaissant son email
    pourrait remplacer son CV.
    """
    # Anti-spam : un robot remplit le champ cache, on fait semblant d'accepter sans rien enregistrer.
    if site_web:
        return PostulerResponse(message=MESSAGE_SUCCES)

    offre = offre_active(token, db)

    if not consentement_accepte:
        raise HTTPException(
            status_code=400,
            detail="Vous devez accepter la politique de confidentialite pour postuler",
        )

    email_normalise = str(email).strip().lower()
    if db.scalar(select(Utilisateur).where(func.lower(Utilisateur.email) == email_normalise)):
        raise HTTPException(
            status_code=409,
            detail=(
                "Un compte existe deja avec cet email. Connectez-vous pour postuler "
                "(mot de passe oublie : utilisez la reinitialisation)."
            ),
        )
    if db.scalar(select(Utilisateur).where(Utilisateur.numero_telephone == numero_telephone)):
        raise HTTPException(status_code=400, detail="Ce numero de telephone est deja utilise")

    # Fichier validé et stocké avant d'écrire en base ; retiré si la suite échoue.
    contenu = lire_fichier_borne(fichier_cv)
    donnees, object_name = valider_et_stocker_cv(contenu, fichier_cv.filename or "")

    try:
        utilisateur = Utilisateur(
            email=email_normalise,
            numero_telephone=numero_telephone,
            mot_de_passe=hash_password(secrets.token_urlsafe(32)),
            nom_prenom=nom_prenom.strip(),
            type_utilisateur=TypeUtilisateur.CANDIDAT,
            status=StatusUtilisateur.EN_ATTENTE,
            must_change_password=True,
            consentement_accepte=True,
            consentement_date=utcnow(),
            consentement_version=POLITIQUE_CONFIDENTIALITE_VERSION,
        )
        db.add(utilisateur)
        db.flush()
        candidat = Candidat(id_utilisateur=utilisateur.id_utilisateur)
        db.add(candidat)
        db.flush()

        code = generate_code_cv()
        while db.query(CV).filter(CV.code_cv == code).first():
            code = generate_code_cv()
        cv = CV(
            id_candidat=candidat.id_candidat,
            code_cv=code,
            resume_cv=donnees.get("resume_cv") or resume_cv,
            competences=donnees.get("competences") or [c.strip() for c in competences if c.strip()],
            langues=donnees.get("langues") or [lang.strip() for lang in langues if lang.strip()],
            url_cv=object_name,
            statut_cv="actif",
        )
        db.add(cv)
        db.flush()

        creer_candidature(db, offre, cv, utilisateur)
        db.commit()
    except IntegrityError:
        db.rollback()
        delete_file(object_name)
        raise HTTPException(status_code=409, detail="Une candidature est deja en cours de traitement, reessayez") from None
    except Exception:
        db.rollback()
        delete_file(object_name)
        raise

    background_tasks.add_task(
        send_application_receipt_email,
        utilisateur.email,
        utilisateur.nom_prenom,
        offre.titre_offre,
        cv.code_cv,
        comptes.url_front(
            "reinitialiser-mot-de-passe",
            comptes.jeton_reset(utilisateur, comptes.DUREE_ACTIVATION_SECONDES),
        ),
    )
    return PostulerResponse(message=MESSAGE_SUCCES)
