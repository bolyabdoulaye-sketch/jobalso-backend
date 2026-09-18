import enum
import uuid
from datetime import datetime
from sqlalchemy import String, Text, Boolean, DateTime, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class NotificationType(str, enum.Enum):
    NOUVELLE_RECOMMANDATION = "nouvelle_recommandation"
    CANDIDATURE_RECUE = "candidature_recue"
    CHANGEMENT_ETAPE = "changement_etape"
    ENTREVUE_PROPOSEE = "entrevue_proposee"
    CANDIDATURE_REFUSEE = "candidature_refusee"


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)

    type: Mapped[NotificationType] = mapped_column(Enum(NotificationType), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)  # JA-082

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class EmailStatus(str, enum.Enum):
    ENVOYE = "envoye"
    ECHEC = "echec"
    REPRIS = "repris"


class EmailLog(Base):
    __tablename__ = "email_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)

    email_type: Mapped[str] = mapped_column(String(100), nullable=False)  # JA-081 : accuse_reception, etc.
    status: Mapped[EmailStatus] = mapped_column(Enum(EmailStatus), default=EmailStatus.ENVOYE, nullable=False)

    unsubscribed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # JA-083

    sent_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)