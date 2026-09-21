import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.notification import Notification
from app.schemas.notification import NotificationRead

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/", response_model=list[NotificationRead])
def list_my_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # JA-082 : liste des notifications, plus recentes d'abord
    return db.query(Notification).filter(
        Notification.utilisateur_id == current_user.id
    ).order_by(Notification.cree_le.desc()).all()


@router.get("/compteur-non-lues")
def count_unread_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # JA-082 : icone avec compteur
    count = db.query(Notification).filter(
        Notification.utilisateur_id == current_user.id,
        Notification.lu == False,
    ).count()
    return {"non_lues": count}


@router.post("/{notification_id}/marquer-lu", response_model=NotificationRead)
def mark_as_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.utilisateur_id == current_user.id,
    ).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification introuvable")

    notification.lu = True  # JA-082 : marquage lu / non lu
    db.commit()
    db.refresh(notification)
    return notification


@router.post("/marquer-toutes-lues")
def mark_all_as_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db.query(Notification).filter(
        Notification.utilisateur_id == current_user.id,
        Notification.lu == False,
    ).update({"lu": True})
    db.commit()
    return {"detail": "Toutes les notifications ont ete marquees comme lues"}