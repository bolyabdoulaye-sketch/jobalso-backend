import uuid
from datetime import datetime
from pydantic import BaseModel
from app.models.notification import NotificationType, EmailStatus


class NotificationRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    type: NotificationType
    message: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


class EmailLogRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    email_type: str
    status: EmailStatus
    unsubscribed_at: datetime | None
    sent_at: datetime

    class Config:
        from_attributes = True