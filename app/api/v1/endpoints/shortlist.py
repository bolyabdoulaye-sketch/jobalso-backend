import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.api.deps import get_db, require_role
from app.models.user import User, UserRole
from app.models.job import Job
from app.models.candidate import CandidateProfile
from app.models.shortlist import ShortlistEntry
from app.schemas.shortlist import ShortlistEntryCreate, ShortlistEntryRead

router = APIRouter(prefix="/shortlist", tags=["shortlist"])


def check_job_ownership(job_id: uuid.UUID, current_user: User, db: Session) -> Job:
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Poste introuvable")
    if job.recruteur_id != current_user.id:
        raise HTTPException(status_code=403, detail="Acces refuse")
    return job


@router.post("/", response_model=ShortlistEntryRead, status_code=status.HTTP_201_CREATED)
def add_to_shortlist(
    entry_in: ShortlistEntryCreate,
    current_user: User = Depends(require_role(UserRole.RECRUTEUR, UserRole.ADMINISTRATEUR)),
    db: Session = Depends(get_db),
):
    check_job_ownership(entry_in.poste_id, current_user, db)  # JA-007

    candidat = db.query(CandidateProfile).filter(
        CandidateProfile.id == entry_in.profil_candidat_id
    ).first()
    if not candidat:
        raise HTTPException(status_code=404, detail="Profil candidat introuvable")

    entry = ShortlistEntry(
        poste_id=entry_in.poste_id,
        profil_candidat_id=entry_in.profil_candidat_id,
    )
    db.add(entry)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Ce candidat est deja dans la shortlist de ce poste")

    db.refresh(entry)
    return entry


@router.get("/postes/{job_id}", response_model=list[ShortlistEntryRead])
def list_shortlist_for_job(
    job_id: uuid.UUID,
    current_user: User = Depends(require_role(UserRole.RECRUTEUR, UserRole.ADMINISTRATEUR)),
    db: Session = Depends(get_db),
):
    check_job_ownership(job_id, current_user, db)  # JA-048

    return db.query(ShortlistEntry).filter(ShortlistEntry.poste_id == job_id).all()


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_from_shortlist(
    entry_id: uuid.UUID,
    current_user: User = Depends(require_role(UserRole.RECRUTEUR, UserRole.ADMINISTRATEUR)),
    db: Session = Depends(get_db),
):
    entry = db.query(ShortlistEntry).filter(ShortlistEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entree shortlist introuvable")

    check_job_ownership(entry.poste_id, current_user, db)  # JA-049 : reversible

    db.delete(entry)
    db.commit()


@router.post("/{entry_id}/selectionner-comparaison", response_model=ShortlistEntryRead)
def toggle_comparison_selection(
    entry_id: uuid.UUID,
    current_user: User = Depends(require_role(UserRole.RECRUTEUR, UserRole.ADMINISTRATEUR)),
    db: Session = Depends(get_db),
):
    entry = db.query(ShortlistEntry).filter(ShortlistEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entree shortlist introuvable")

    check_job_ownership(entry.poste_id, current_user, db)

    if not entry.selectionne_pour_comparaison:
        # JA-051 : max 3 candidats selectionnes pour comparaison, par poste
        nb_selected = db.query(ShortlistEntry).filter(
            ShortlistEntry.poste_id == entry.poste_id,
            ShortlistEntry.selectionne_pour_comparaison == True,
        ).count()
        if nb_selected >= 3:
            raise HTTPException(status_code=400, detail="Maximum 3 candidats pour la comparaison")

    entry.selectionne_pour_comparaison = not entry.selectionne_pour_comparaison
    db.commit()
    db.refresh(entry)
    return entry