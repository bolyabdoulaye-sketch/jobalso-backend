import uuid
from datetime import datetime
from pydantic import BaseModel
from app.models.notification import NotificationType, EmailStatus


class NotificationRead(BaseModel):
    id: uuid.UUID
    utilisateur_id: uuid.UUID
    type: NotificationType
    message: str
    lu: bool
    cree_le: datetime

    class Config:
        from_attributes = True


class EmailLogRead(BaseModel):
    id: uuid.UUID
    utilisateur_id: uuid.UUID
    type_email: str
    statut: EmailStatus
    desabonne_le: datetime | None
    envoye_le: datetime

    class Config:
        from_attributes = True