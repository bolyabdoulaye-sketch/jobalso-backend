import secrets
import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
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
from app.schemas.public import PublicOffreRead, PostulerPublic, PostulerResponse
from app.services.email_candidature import send_application_receipt_email

router = APIRouter(prefix="/public", tags=["public"])

MESSAGE_SUCCES = "Votre candidature a bien été reçue. Un email de confirmation vous a été envoyé."


def _offre_active(offre_id: uuid.UUID, db: Session) -> Offre:
    offre = db.query(Offre).filter(Offre.id_offre == offre_id, Offre.status.is_(True)).first()
    if not offre:
        raise HTTPException(status_code=404, detail="Offre introuvable ou fermee")
    return offre


@router.get("/offres/{offre_id}", response_model=PublicOffreRead)
def get_public_offre(offre_id: uuid.UUID, db: Session = Depends(get_db)):
    return _offre_active(offre_id, db)


# Candidature publique sans compte (JA-027) + accuse de reception (JA-081)
@router.post(
    "/offres/{offre_id}/postuler",
    response_model=PostulerResponse,
    status_code=status.HTTP_201_CREATED,
)
def postuler(
    offre_id: uuid.UUID,
    data: PostulerPublic,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    # Anti-spam : un robot remplit le champ cache, on fait semblant d'accepter sans rien enregistrer
    if data.site_web:
        return PostulerResponse(message=MESSAGE_SUCCES)

    offre = _offre_active(offre_id, db)

    if not data.consentement_accepte:
        raise HTTPException(
            status_code=400,
            detail="Vous devez accepter la politique de confidentialite pour postuler",
        )

    utilisateur = db.query(Utilisateur).filter(Utilisateur.email == data.email).first()

    if utilisateur:
        if utilisateur.type_utilisateur != TypeUtilisateur.CANDIDAT:
            raise HTTPException(status_code=400, detail="Impossible de candidater avec cet email")
        if utilisateur.status in (StatusUtilisateur.SUPPRIME, StatusUtilisateur.INACTIF):
            raise HTTPException(status_code=400, detail="Impossible de candidater avec cet email")
        candidat = db.query(Candidat).filter(Candidat.id_utilisateur == utilisateur.id_utilisateur).first()
    else:
        if db.query(Utilisateur).filter(Utilisateur.numero_telephone == data.numero_telephone).first():
            raise HTTPException(status_code=400, detail="Ce numero de telephone est deja utilise")

        # Compte leger : mot de passe aleatoire inutilisable, en attente d'activation
        utilisateur = Utilisateur(
            email=data.email,
            numero_telephone=data.numero_telephone,
            mot_de_passe=hash_password(secrets.token_urlsafe(32)),
            nom_prenom=data.nom_prenom,
            type_utilisateur=TypeUtilisateur.CANDIDAT,
            status=StatusUtilisateur.EN_ATTENTE,
            must_change_password=True,
            consentement_accepte=True,
            consentement_date=datetime.utcnow(),
            consentement_version=POLITIQUE_CONFIDENTIALITE_VERSION,
        )
        db.add(utilisateur)
        db.flush()
        candidat = None

    if candidat is None:
        candidat = Candidat(id_utilisateur=utilisateur.id_utilisateur)
        db.add(candidat)
        db.flush()

    # On ne modifie JAMAIS un CV existant depuis un formulaire public :
    # sinon n'importe qui connaissant un email pourrait alterer le CV d'un autre.
    cv = db.query(CV).filter(CV.id_candidat == candidat.id_candidat).first()
    if cv is None:
        code = generate_code_cv()
        while db.query(CV).filter(CV.code_cv == code).first():
            code = generate_code_cv()
        cv = CV(
            id_candidat=candidat.id_candidat,
            resume_cv=data.resume_cv,
            competences=[c.strip() for c in data.competences if c.strip()],
            langues=[l.strip() for l in data.langues if l.strip()],
            statut_cv="actif",
            code_cv=code,
        )
        db.add(cv)
        db.flush()

    deja = db.query(Resultat).filter(
        Resultat.id_offre == offre.id_offre, Resultat.id_cv == cv.id_cv
    ).first()
    if deja:
        db.rollback()
        raise HTTPException(status_code=400, detail="Vous avez deja postule a cette offre")

    resultat = Resultat(
        id_offre=offre.id_offre,
        id_cv=cv.id_cv,
        score_sim=0.0,  # provisoire, comme pour le matching recruteur
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

    background_tasks.add_task(
        send_application_receipt_email,
        utilisateur.email,
        utilisateur.nom_prenom,
        offre.titre_offre,
        cv.code_cv,
    )
    return PostulerResponse(message=MESSAGE_SUCCES)
