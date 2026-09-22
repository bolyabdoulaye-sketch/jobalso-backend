import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, require_role
from app.models.utilisateur import TypeUtilisateur, Utilisateur
from app.models.recruteur import Recruteur
from app.models.offre import Offre
from app.models.cv import CV
from app.models.resultat import Resultat
from app.schemas.offre import OffreCreate, OffreUpdate, OffreRead
from app.schemas.resultat import MatchingRequest, ResultatRead

router = APIRouter(prefix="/offres", tags=["offres"])


def get_own_recruteur(current_user: Utilisateur, db: Session) -> Recruteur:
    recruteur = db.query(Recruteur).filter(Recruteur.id_utilisateur == current_user.id_utilisateur).first()
    if not recruteur:
        raise HTTPException(status_code=404, detail="Profil recruteur introuvable")
    return recruteur


@router.post("/", response_model=OffreRead, status_code=status.HTTP_201_CREATED)
def create_offre(
    offre_in: OffreCreate,
    current_user: Utilisateur = Depends(require_role(TypeUtilisateur.RECRUTEUR)),
    db: Session = Depends(get_db),
):
    recruteur = get_own_recruteur(current_user, db)

    offre = Offre(
        id_recruteur=recruteur.id_recruteur,
        titre_offre=offre_in.titre_offre,
        description=offre_in.description,
        type_contrat=offre_in.type_contrat,
        revenu=offre_in.revenu,
        date_debut=offre_in.date_debut,
        date_fin=offre_in.date_fin,
        resume_offre=offre_in.resume_offre,
        status=True,
    )
    db.add(offre)
    db.commit()
    db.refresh(offre)
    return offre


@router.get("/", response_model=list[OffreRead])
def list_my_offres(
    current_user: Utilisateur = Depends(require_role(TypeUtilisateur.RECRUTEUR)),
    db: Session = Depends(get_db),
):
    recruteur = get_own_recruteur(current_user, db)
    return db.query(Offre).filter(Offre.id_recruteur == recruteur.id_recruteur).all()


@router.get("/{offre_id}", response_model=OffreRead)
def get_offre(
    offre_id: uuid.UUID,
    current_user: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    offre = db.query(Offre).filter(Offre.id_offre == offre_id).first()
    if not offre:
        raise HTTPException(status_code=404, detail="Offre introuvable")
    return offre


@router.put("/{offre_id}", response_model=OffreRead)
def update_offre(
    offre_id: uuid.UUID,
    offre_in: OffreUpdate,
    current_user: Utilisateur = Depends(require_role(TypeUtilisateur.RECRUTEUR)),
    db: Session = Depends(get_db),
):
    recruteur = get_own_recruteur(current_user, db)
    offre = db.query(Offre).filter(Offre.id_offre == offre_id).first()
    if not offre:
        raise HTTPException(status_code=404, detail="Offre introuvable")
    if offre.id_recruteur != recruteur.id_recruteur:
        raise HTTPException(status_code=403, detail="Acces refuse")

    for field, value in offre_in.model_dump(exclude_unset=True).items():
        setattr(offre, field, value)

    db.commit()
    db.refresh(offre)
    return offre


@router.delete("/{offre_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_offre(
    offre_id: uuid.UUID,
    current_user: Utilisateur = Depends(require_role(TypeUtilisateur.RECRUTEUR)),
    db: Session = Depends(get_db),
):
    recruteur = get_own_recruteur(current_user, db)
    offre = db.query(Offre).filter(Offre.id_offre == offre_id).first()
    if not offre:
        raise HTTPException(status_code=404, detail="Offre introuvable")
    if offre.id_recruteur != recruteur.id_recruteur:
        raise HTTPException(status_code=403, detail="Acces refuse")

    db.delete(offre)
    db.commit()


@router.post("/matching", response_model=ResultatRead, status_code=status.HTTP_201_CREATED)
def match_cv_to_offre(
    matching_in: MatchingRequest,
    current_user: Utilisateur = Depends(require_role(TypeUtilisateur.RECRUTEUR)),
    db: Session = Depends(get_db),
):
    recruteur = get_own_recruteur(current_user, db)

    offre = db.query(Offre).filter(Offre.id_offre == matching_in.id_offre).first()
    if not offre:
        raise HTTPException(status_code=404, detail="Offre introuvable")
    if offre.id_recruteur != recruteur.id_recruteur:
        raise HTTPException(status_code=403, detail="Acces refuse")

    cv = db.query(CV).filter(CV.code_cv == matching_in.code_cv.upper()).first()
    if not cv:
        raise HTTPException(status_code=404, detail="Aucun CV trouve avec ce code")

    existing = db.query(Resultat).filter(
        Resultat.id_offre == offre.id_offre, Resultat.id_cv == cv.id_cv
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Ce CV a deja ete evalue pour cette offre")

    # TODO : remplacer par un vrai calcul de similarite cosinus entre cv_vector et offre_vector
    # une fois l'integration UjuzAI disponible. En attendant, score provisoire.
    score_provisoire = 0.0

    resultat = Resultat(
        id_offre=offre.id_offre,
        id_cv=cv.id_cv,
        score_sim=score_provisoire,
        statut_candidature="en_attente",
    )
    db.add(resultat)
    db.commit()
    db.refresh(resultat)
    return resultat


@router.get("/{offre_id}/resultats", response_model=list[ResultatRead])
def list_matching_results(
    offre_id: uuid.UUID,
    current_user: Utilisateur = Depends(require_role(TypeUtilisateur.RECRUTEUR)),
    db: Session = Depends(get_db),
):
    recruteur = get_own_recruteur(current_user, db)
    offre = db.query(Offre).filter(Offre.id_offre == offre_id).first()
    if not offre:
        raise HTTPException(status_code=404, detail="Offre introuvable")
    if offre.id_recruteur != recruteur.id_recruteur:
        raise HTTPException(status_code=403, detail="Acces refuse")

    return db.query(Resultat).filter(Resultat.id_offre == offre_id).order_by(
        Resultat.score_sim.desc()
    ).all()