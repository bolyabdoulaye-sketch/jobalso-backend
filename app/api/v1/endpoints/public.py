import secrets
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import EmailStr
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.v1.endpoints.auth import POLITIQUE_CONFIDENTIALITE_VERSION
from app.core.security import hash_password
from app.models.utilisateur import Utilisateur, TypeUtilisateur, StatusUtilisateur
from app.models.candidat import Candidat
from app.models.cv import CV
from app.models.offre import Offre
from app.models.resultat import Resultat
from app.models.historique_statut import HistoriqueStatutCandidature
from app.models.statut_candidature import StatutCandidature
from app.schemas.cv import generate_code_cv
from app.schemas.public import PublicOffreRead, PostulerResponse
from app.services.email_candidature import send_application_receipt_email
from app.services.matching import calculer_score
from app.services.cv_upload import valider_et_stocker_cv

router = APIRouter(prefix="/public", tags=["public"])

MESSAGE_SUCCES = "Votre candidature a bien ete recue. Un email de confirmation vous a ete envoye."


def _offre_active(token: str, db: Session) -> Offre:
    offre = db.query(Offre).filter(Offre.lien_token == token, Offre.status.is_(True)).first()
    if not offre:
        raise HTTPException(status_code=404, detail="Offre introuvable ou fermee")
    return offre


@router.get("/offres/{token}", response_model=PublicOffreRead)
def get_public_offre(token: str, db: Session = Depends(get_db)):
    return _offre_active(token, db)


# Candidature publique sans compte (JA-027) + accuse de reception (JA-081)
@router.post(
    "/offres/{token}/postuler",
    response_model=PostulerResponse,
    status_code=status.HTTP_201_CREATED,
)
async def postuler(
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
    """Candidature publique avec dépôt réel du CV (JA-027)."""
    # Anti-spam : un robot remplit le champ cache, on fait semblant d'accepter sans rien enregistrer.
    if site_web:
        return PostulerResponse(message=MESSAGE_SUCCES)

    offre = _offre_active(token, db)

    if not consentement_accepte:
        raise HTTPException(
            status_code=400,
            detail="Vous devez accepter la politique de confidentialite pour postuler",
        )

    utilisateur = db.query(Utilisateur).filter(Utilisateur.email == str(email)).first()

    if utilisateur:
        if utilisateur.type_utilisateur != TypeUtilisateur.CANDIDAT:
            raise HTTPException(status_code=400, detail="Impossible de candidater avec cet email")
        if utilisateur.status in (StatusUtilisateur.SUPPRIME, StatusUtilisateur.INACTIF):
            raise HTTPException(status_code=400, detail="Impossible de candidater avec cet email")
        candidat = db.query(Candidat).filter(Candidat.id_utilisateur == utilisateur.id_utilisateur).first()
        if candidat is None:
            candidat = Candidat(id_utilisateur=utilisateur.id_utilisateur)
            db.add(candidat)
            db.flush()
    else:
        if db.query(Utilisateur).filter(Utilisateur.numero_telephone == numero_telephone).first():
            raise HTTPException(status_code=400, detail="Ce numero de telephone est deja utilise")

        utilisateur = Utilisateur(
            email=str(email),
            numero_telephone=numero_telephone,
            mot_de_passe=hash_password(secrets.token_urlsafe(32)),
            nom_prenom=nom_prenom,
            type_utilisateur=TypeUtilisateur.CANDIDAT,
            status=StatusUtilisateur.EN_ATTENTE,
            must_change_password=True,
            consentement_accepte=True,
            consentement_date=datetime.utcnow(),
            consentement_version=POLITIQUE_CONFIDENTIALITE_VERSION,
        )
        db.add(utilisateur)
        db.flush()
        candidat = Candidat(id_utilisateur=utilisateur.id_utilisateur)
        db.add(candidat)
        db.flush()

    cv = db.query(CV).filter(CV.id_candidat == candidat.id_candidat).first()

    if cv is None:
        code = generate_code_cv()
        while db.query(CV).filter(CV.code_cv == code).first():
            code = generate_code_cv()
        cv = CV(id_candidat=candidat.id_candidat, code_cv=code)
        db.add(cv)
    else:
        # Une candidature publique ne doit pas permettre de modifier le CV d'un compte
        # existant avec le seul email. Le dépôt est donc autorisé uniquement lorsque
        # les coordonnées fournies correspondent au compte existant.
        if (utilisateur.numero_telephone or "") != numero_telephone or (utilisateur.nom_prenom or "").strip().casefold() != nom_prenom.strip().casefold():
            raise HTTPException(
                status_code=409,
                detail="Un CV existe deja pour ce compte. Utilisez votre espace candidat pour le remplacer.",
            )


    contenu = await fichier_cv.read()
    donnees, object_name = valider_et_stocker_cv(contenu, fichier_cv.filename or "")

    cv.resume_cv = donnees.get("resume_cv") or resume_cv
    cv.competences = donnees.get("competences") or [c.strip() for c in competences if c.strip()]
    cv.langues = donnees.get("langues") or [l.strip() for l in langues if l.strip()]
    cv.experience = donnees.get("experience")
    cv.education = donnees.get("education")
    cv.domaine_etude = donnees.get("domaine_etude")
    cv.certifications = donnees.get("certifications")
    cv.localisation = donnees.get("localisation")
    cv.type_poste_recherche = donnees.get("type_poste_recherche")
    cv.url_cv = object_name
    cv.statut_cv = "actif"
    db.flush()

    deja = db.query(Resultat).filter(
        Resultat.id_offre == offre.id_offre, Resultat.id_cv == cv.id_cv
    ).first()
    if deja:
        db.rollback()
        raise HTTPException(status_code=400, detail="Vous avez deja postule a cette offre")

    score = calculer_score(cv, offre.criteres)
    resultat = Resultat(
        id_offre=offre.id_offre,
        id_cv=cv.id_cv,
        score_sim=score,
        statut_candidature=StatutCandidature.RECUE.value,
    )
    db.add(resultat)
    db.flush()
    db.add(
        HistoriqueStatutCandidature(
            id_resultat=resultat.id_resultat,
            ancien_statut=None,
            nouveau_statut=StatutCandidature.RECUE.value,
            id_utilisateur=utilisateur.id_utilisateur,
        )
    )

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Une candidature est deja en cours de traitement, reessayez")

    if background_tasks is not None:
        background_tasks.add_task(
            send_application_receipt_email,
            utilisateur.email,
            utilisateur.nom_prenom,
            offre.titre_offre,
            cv.code_cv,
        )
    return PostulerResponse(message=MESSAGE_SUCCES)

