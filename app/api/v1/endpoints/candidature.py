from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role
from app.api.v1.endpoints.public import offre_active
from app.models.utilisateur import TypeUtilisateur, Utilisateur
from app.models.candidat import Candidat
from app.models.cv import CV
from app.models.offre import Offre
from app.models.resultat import Resultat
from app.models.statut_candidature import libelle_statut
from app.schemas.candidature import CandidatureRead
from app.services.candidature import creer_candidature
from app.services.email_candidature import send_application_receipt_email

router = APIRouter(prefix="/candidatures", tags=["candidatures"])


def _lire(resultat: Resultat, offre: Offre) -> CandidatureRead:
    return CandidatureRead(
        id_resultat=resultat.id_resultat,
        id_offre=offre.id_offre,
        titre_offre=offre.titre_offre,
        statut_candidature=resultat.statut_candidature,
        libelle_statut=libelle_statut(resultat.statut_candidature),
        date_modification=resultat.date_modification,
    )


@router.get("/mes-candidatures", response_model=list[CandidatureRead])
def mes_candidatures(
    current_user: Utilisateur = Depends(require_role(TypeUtilisateur.CANDIDAT)),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(Resultat, Offre)
        .join(Offre, Offre.id_offre == Resultat.id_offre)
        .join(CV, CV.id_cv == Resultat.id_cv)
        .join(Candidat, Candidat.id_candidat == CV.id_candidat)
        .filter(Candidat.id_utilisateur == current_user.id_utilisateur)
        .order_by(Resultat.date_modification.desc())
        .all()
    )
    return [_lire(resultat, offre) for resultat, offre in rows]


@router.post(
    "/offres/{token}",
    response_model=CandidatureRead,
    status_code=status.HTTP_201_CREATED,
)
def postuler_connecte(
    token: str,
    background_tasks: BackgroundTasks,
    current_user: Utilisateur = Depends(require_role(TypeUtilisateur.CANDIDAT)),
    db: Session = Depends(get_db),
):
    """Candidature depuis l'espace candidat, avec le CV déjà déposé."""
    offre = offre_active(token, db)

    cv = db.scalar(
        select(CV)
        .join(Candidat, Candidat.id_candidat == CV.id_candidat)
        .where(Candidat.id_utilisateur == current_user.id_utilisateur)
    )
    if cv is None:
        raise HTTPException(status_code=400, detail="Deposez d'abord votre CV")

    if db.scalar(select(Resultat).where(Resultat.id_offre == offre.id_offre, Resultat.id_cv == cv.id_cv)):
        raise HTTPException(status_code=400, detail="Vous avez deja postule a cette offre")

    resultat = creer_candidature(db, offre, cv, current_user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Vous avez deja postule a cette offre") from None
    db.refresh(resultat)

    background_tasks.add_task(
        send_application_receipt_email,
        current_user.email,
        current_user.nom_prenom,
        offre.titre_offre,
        cv.code_cv,
    )
    return _lire(resultat, offre)
