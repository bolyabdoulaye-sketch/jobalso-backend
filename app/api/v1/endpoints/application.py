import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.api.deps import get_db, get_current_user, require_role
from app.models.user import User, UserRole
from app.models.job import Job
from app.models.candidate import CandidateProfile
from app.models.application import Application, PipelineEvent, PipelineStage
from app.schemas.application import ApplicationCreate, ApplicationRead, PipelineEventRead

router = APIRouter(prefix="/candidatures", tags=["candidatures"])


def get_own_candidate_profile(current_user: User, db: Session) -> CandidateProfile:
    profil = db.query(CandidateProfile).filter(
        CandidateProfile.utilisateur_id == current_user.id
    ).first()
    if not profil:
        raise HTTPException(status_code=404, detail="Profil candidat introuvable")
    return profil


@router.post("/", response_model=ApplicationRead, status_code=status.HTTP_201_CREATED)
def create_application(
    application_in: ApplicationCreate,
    current_user: User = Depends(require_role(UserRole.CANDIDAT)),
    db: Session = Depends(get_db),
):
    profil = get_own_candidate_profile(current_user, db)

    job = db.query(Job).filter(Job.id == application_in.poste_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Poste introuvable")

    application = Application(
        poste_id=application_in.poste_id,
        profil_candidat_id=profil.id,
    )
    db.add(application)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Vous avez deja postule a ce poste")

    db.flush()

    # JA-060 : premier evenement de l'historique
    event = PipelineEvent(
        candidature_id=application.id,
        etape_origine=None,
        etape_destination=PipelineStage.CANDIDATURE,
    )
    db.add(event)
    db.commit()
    db.refresh(application)
    return application


@router.get("/moi", response_model=list[ApplicationRead])
def list_my_applications(
    current_user: User = Depends(require_role(UserRole.CANDIDAT)),
    db: Session = Depends(get_db),
):
    profil = get_own_candidate_profile(current_user, db)
    # JA-059 : le candidat voit toutes ses candidatures
    return db.query(Application).filter(Application.profil_candidat_id == profil.id).all()


@router.get("/postes/{job_id}", response_model=list[ApplicationRead])
def list_applications_for_job(
    job_id: uuid.UUID,
    current_user: User = Depends(require_role(UserRole.RECRUTEUR, UserRole.ADMINISTRATEUR)),
    db: Session = Depends(get_db),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Poste introuvable")
    if job.recruteur_id != current_user.id:
        raise HTTPException(status_code=403, detail="Acces refuse")  # JA-007

    return db.query(Application).filter(Application.poste_id == job_id).all()


@router.get("/{application_id}/historique", response_model=list[PipelineEventRead])
def get_application_history(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Candidature introuvable")

    # JA-060 : le candidat voit son propre historique, le recruteur celui de son poste
    if current_user.role == UserRole.CANDIDAT:
        profil = get_own_candidate_profile(current_user, db)
        if application.profil_candidat_id != profil.id:
            raise HTTPException(status_code=403, detail="Acces refuse")
    elif current_user.role == UserRole.RECRUTEUR:
        job = db.query(Job).filter(Job.id == application.poste_id).first()
        if job.recruteur_id != current_user.id:
            raise HTTPException(status_code=403, detail="Acces refuse")

    return db.query(PipelineEvent).filter(
        PipelineEvent.candidature_id == application_id
    ).order_by(PipelineEvent.survenu_le).all()


@router.post("/{application_id}/changer-etape", response_model=ApplicationRead)
def change_application_stage(
    application_id: uuid.UUID,
    nouvelle_etape: PipelineStage,
    current_user: User = Depends(require_role(UserRole.RECRUTEUR, UserRole.ADMINISTRATEUR)),
    db: Session = Depends(get_db),
):
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Candidature introuvable")

    job = db.query(Job).filter(Job.id == application.poste_id).first()
    if job.recruteur_id != current_user.id:
        raise HTTPException(status_code=403, detail="Acces refuse")

    ancienne_etape = application.etape_actuelle
    application.etape_actuelle = nouvelle_etape  # JA-056

    event = PipelineEvent(
        candidature_id=application.id,
        etape_origine=ancienne_etape,
        etape_destination=nouvelle_etape,
    )
    db.add(event)
    db.commit()
    db.refresh(application)
    return application