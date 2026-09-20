import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, require_role
from app.models.user import User, UserRole
from app.models.job import Job, JobCriterion, JobStatus
from app.models.job_criterion_history import JobCriterionHistory, HistoryAction
from app.schemas.job import JobCreate, JobRead, JobCriterionCreate, JobCriterionRead

router = APIRouter(prefix="/postes", tags=["postes"])


@router.post("/", response_model=JobRead, status_code=status.HTTP_201_CREATED)
def create_job(
    job_in: JobCreate,
    current_user: User = Depends(require_role(UserRole.RECRUTEUR, UserRole.ADMINISTRATEUR)),
    db: Session = Depends(get_db),
):
    job = Job(
        recruteur_id=current_user.id,
        titre=job_in.titre,
        description_brute=job_in.description_brute,
        mode_creation=job_in.mode_creation,
        statut=JobStatus.BROUILLON,  # JA-021 : brouillon par defaut
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("/", response_model=list[JobRead])
def list_jobs(
    current_user: User = Depends(require_role(UserRole.RECRUTEUR, UserRole.ADMINISTRATEUR)),
    db: Session = Depends(get_db),
):
    # JA-007 : un recruteur ne voit que ses postes
    return db.query(Job).filter(Job.recruteur_id == current_user.id).all()


@router.get("/{job_id}", response_model=JobRead)
def get_job(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Poste introuvable")

    if current_user.role == UserRole.RECRUTEUR and job.recruteur_id != current_user.id:
        raise HTTPException(status_code=403, detail="Acces refuse")

    return job


@router.put("/{job_id}", response_model=JobRead)
def update_job(
    job_id: uuid.UUID,
    job_in: JobCreate,
    current_user: User = Depends(require_role(UserRole.RECRUTEUR, UserRole.ADMINISTRATEUR)),
    db: Session = Depends(get_db),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Poste introuvable")
    if job.recruteur_id != current_user.id:
        raise HTTPException(status_code=403, detail="Acces refuse")

    job.titre = job_in.titre
    job.description_brute = job_in.description_brute
    db.commit()
    db.refresh(job)
    return job


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(
    job_id: uuid.UUID,
    current_user: User = Depends(require_role(UserRole.RECRUTEUR, UserRole.ADMINISTRATEUR)),
    db: Session = Depends(get_db),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Poste introuvable")
    if job.recruteur_id != current_user.id:
        raise HTTPException(status_code=403, detail="Acces refuse")

    db.delete(job)
    db.commit()


@router.post("/{job_id}/publier", response_model=JobRead)
def publish_job(
    job_id: uuid.UUID,
    current_user: User = Depends(require_role(UserRole.RECRUTEUR, UserRole.ADMINISTRATEUR)),
    db: Session = Depends(get_db),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Poste introuvable")
    if job.recruteur_id != current_user.id:
        raise HTTPException(status_code=403, detail="Acces refuse")

    job.statut = JobStatus.PUBLIEE  # JA-025
    job.publie_le = datetime.utcnow()
    db.commit()
    db.refresh(job)
    return job


@router.post("/{job_id}/depublier", response_model=JobRead)
def unpublish_job(
    job_id: uuid.UUID,
    current_user: User = Depends(require_role(UserRole.RECRUTEUR, UserRole.ADMINISTRATEUR)),
    db: Session = Depends(get_db),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Poste introuvable")
    if job.recruteur_id != current_user.id:
        raise HTTPException(status_code=403, detail="Acces refuse")

    job.statut = JobStatus.DEPUBLIEE  # JA-025
    db.commit()
    db.refresh(job)
    return job


@router.post("/{job_id}/criteres", response_model=JobCriterionRead, status_code=status.HTTP_201_CREATED)
def add_criterion(
    job_id: uuid.UUID,
    criterion_in: JobCriterionCreate,
    current_user: User = Depends(require_role(UserRole.RECRUTEUR, UserRole.ADMINISTRATEUR)),
    db: Session = Depends(get_db),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Poste introuvable")
    if job.recruteur_id != current_user.id:
        raise HTTPException(status_code=403, detail="Acces refuse")

    criterion = JobCriterion(
        poste_id=job_id,
        type_critere=criterion_in.type_critere,
        valeur=criterion_in.valeur,
        niveau=criterion_in.niveau,
    )
    db.add(criterion)
    db.flush()  # pour obtenir criterion.id avant le commit

    # JA-020 : historique de creation
    history = JobCriterionHistory(
        poste_id=job_id,
        critere_id=criterion.id,
        action=HistoryAction.AJOUT,
        type_critere=criterion.type_critere.value,
        valeur=criterion.valeur,
        niveau=criterion.niveau.value,
        modifie_par=current_user.id,
    )
    db.add(history)
    db.commit()
    db.refresh(criterion)
    return criterion


@router.get("/{job_id}/criteres", response_model=list[JobCriterionRead])
def list_criteria(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Poste introuvable")

    return db.query(JobCriterion).filter(JobCriterion.poste_id == job_id).all()


@router.delete("/criteres/{criterion_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_criterion(
    criterion_id: uuid.UUID,
    current_user: User = Depends(require_role(UserRole.RECRUTEUR, UserRole.ADMINISTRATEUR)),
    db: Session = Depends(get_db),
):
    criterion = db.query(JobCriterion).filter(JobCriterion.id == criterion_id).first()
    if not criterion:
        raise HTTPException(status_code=404, detail="Critere introuvable")

    job = db.query(Job).filter(Job.id == criterion.poste_id).first()
    if job.recruteur_id != current_user.id:
        raise HTTPException(status_code=403, detail="Acces refuse")

    # JA-020 : historique de suppression avant de supprimer reellement
    history = JobCriterionHistory(
        poste_id=criterion.poste_id,
        critere_id=None,  # le critere n'existera plus
        action=HistoryAction.SUPPRESSION,
        type_critere=criterion.type_critere.value,
        valeur=criterion.valeur,
        niveau=criterion.niveau.value,
        modifie_par=current_user.id,
    )
    db.add(history)
    db.delete(criterion)
    db.commit()                                                                                                                 