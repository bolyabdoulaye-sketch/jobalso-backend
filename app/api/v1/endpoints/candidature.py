from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role
from app.models.utilisateur import TypeUtilisateur, Utilisateur
from app.models.candidat import Candidat
from app.models.cv import CV
from app.models.offre import Offre
from app.models.resultat import Resultat
from app.models.statut_candidature import libelle_statut
from app.schemas.candidature import CandidatureRead

router = APIRouter(prefix="/candidatures", tags=["candidatures"])


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
    return [
        CandidatureRead(
            id_resultat=resultat.id_resultat,
            id_offre=offre.id_offre,
            titre_offre=offre.titre_offre,
            statut_candidature=resultat.statut_candidature,
            libelle_statut=libelle_statut(resultat.statut_candidature),
            date_modification=resultat.date_modification,
        )
        for resultat, offre in rows
    ]
