import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role
from app.models.utilisateur import TypeUtilisateur, Utilisateur
from app.models.candidat import Candidat
from app.models.cv import CV
from app.schemas.cv import CVCreate, CVUpdate, CVRead, generate_code_cv

router = APIRouter(prefix="/cv", tags=["cv"])


def get_own_candidat(current_user: Utilisateur, db: Session) -> Candidat:
    candidat = db.query(Candidat).filter(Candidat.id_utilisateur == current_user.id_utilisateur).first()
    if not candidat:
        raise HTTPException(status_code=404, detail="Profil candidat introuvable")
    return candidat


@router.post("/", response_model=CVRead, status_code=status.HTTP_201_CREATED)
def create_cv(
    cv_in: CVCreate,
    current_user: Utilisateur = Depends(require_role(TypeUtilisateur.CANDIDAT)),
    db: Session = Depends(get_db),
):
    candidat = get_own_candidat(current_user, db)

    existing = db.query(CV).filter(CV.id_candidat == candidat.id_candidat).first()
    if existing:
        raise HTTPException(status_code=400, detail="Un CV existe deja pour ce candidat. Utilisez la modification.")

    # Genere un code_cv unique
    code = generate_code_cv()
    while db.query(CV).filter(CV.code_cv == code).first():
        code = generate_code_cv()

        cv = CV(
        id_candidat=candidat.id_candidat,
        resume_cv=cv_in.resume_cv,
        experience=cv_in.experience,
        education=cv_in.education,
        langues=cv_in.langues,
        domaine_etude=cv_in.domaine_etude,
        competences=cv_in.competences,
        certifications=cv_in.certifications,
        localisation=cv_in.localisation,
        type_poste_recherche=cv_in.type_poste_recherche,
        statut_cv="actif",
        code_cv=code,
    )
    db.add(cv)
    db.commit()
    db.refresh(cv)
    return cv


@router.get("/moi", response_model=CVRead)
def get_my_cv(
    current_user: Utilisateur = Depends(require_role(TypeUtilisateur.CANDIDAT)),
    db: Session = Depends(get_db),
):
    candidat = get_own_candidat(current_user, db)
    cv = db.query(CV).filter(CV.id_candidat == candidat.id_candidat).first()
    if not cv:
        raise HTTPException(status_code=404, detail="Aucun CV trouve pour ce candidat")
    return cv


@router.put("/moi", response_model=CVRead)
def update_my_cv(
    cv_in: CVUpdate,
    current_user: Utilisateur = Depends(require_role(TypeUtilisateur.CANDIDAT)),
    db: Session = Depends(get_db),
):
    candidat = get_own_candidat(current_user, db)
    cv = db.query(CV).filter(CV.id_candidat == candidat.id_candidat).first()
    if not cv:
        raise HTTPException(status_code=404, detail="Aucun CV trouve. Creez-en un d'abord.")

    for field, value in cv_in.model_dump(exclude_unset=True).items():
        setattr(cv, field, value)

    db.commit()
    db.refresh(cv)
    return cv


@router.delete("/moi", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_cv(
    current_user: Utilisateur = Depends(require_role(TypeUtilisateur.CANDIDAT)),
    db: Session = Depends(get_db),
):
    candidat = get_own_candidat(current_user, db)
    cv = db.query(CV).filter(CV.id_candidat == candidat.id_candidat).first()
    if not cv:
        raise HTTPException(status_code=404, detail="Aucun CV trouve")

    db.delete(cv)
    db.commit()