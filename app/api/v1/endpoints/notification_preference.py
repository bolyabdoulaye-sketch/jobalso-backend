import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role
from app.models.user import User, UserRole
from app.models.candidate import CandidateProfile
from app.models.notification_preference import NotificationPreference, RecommendationDismissal
from app.schemas.notification_preference import (
    NotificationPreferenceRead,
    NotificationPreferenceUpdate,
    RecommendationDismissalCreate,
)

router = APIRouter(prefix="/preferences-notification", tags=["preferences-notification"])


def get_or_create_preferences(current_user: User, db: Session) -> NotificationPreference:
    prefs = db.query(NotificationPreference).filter(
        NotificationPreference.utilisateur_id == current_user.id
    ).first()
    if not prefs:
        prefs = NotificationPreference(utilisateur_id=current_user.id)
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
    return prefs


@router.get("/moi", response_model=NotificationPreferenceRead)
def get_my_preferences(
    current_user: User = Depends(require_role(UserRole.CANDIDAT)),
    db: Session = Depends(get_db),
):
    return get_or_create_preferences(current_user, db)  # JA-071


@router.put("/moi", response_model=NotificationPreferenceRead)
def update_my_preferences(
    prefs_in: NotificationPreferenceUpdate,
    current_user: User = Depends(require_role(UserRole.CANDIDAT)),
    db: Session = Depends(get_db),
):
    prefs = get_or_create_preferences(current_user, db)

    for field, value in prefs_in.model_dump(exclude_unset=True).items():
        setattr(prefs, field, value)  # JA-071 : prise en compte immediate

    db.commit()
    db.refresh(prefs)
    return prefs


@router.post("/moi/recommandations-rejetees", status_code=status.HTTP_201_CREATED)
def dismiss_recommendation(
    dismissal_in: RecommendationDismissalCreate,
    current_user: User = Depends(require_role(UserRole.CANDIDAT)),
    db: Session = Depends(get_db),
):
    profil = db.query(CandidateProfile).filter(
        CandidateProfile.utilisateur_id == current_user.id
    ).first()
    if not profil:
        raise HTTPException(status_code=404, detail="Profil candidat introuvable")

    dismissal = RecommendationDismissal(
        profil_candidat_id=profil.id,
        poste_id=dismissal_in.poste_id,
    )
    db.add(dismissal)
    db.commit()  # JA-070 : retrait immediat de la liste (le front filtrera avec cette table)
    return {"detail": "Recommandation retiree"}


@router.get("/moi/recommandations-rejetees", response_model=list[uuid.UUID])
def list_dismissed_job_ids(
    current_user: User = Depends(require_role(UserRole.CANDIDAT)),
    db: Session = Depends(get_db),
):
    profil = db.query(CandidateProfile).filter(
        CandidateProfile.utilisateur_id == current_user.id
    ).first()
    if not profil:
        raise HTTPException(status_code=404, detail="Profil candidat introuvable")

    dismissals = db.query(RecommendationDismissal).filter(
        RecommendationDismissal.profil_candidat_id == profil.id
    ).all()
    return [d.poste_id for d in dismissals]