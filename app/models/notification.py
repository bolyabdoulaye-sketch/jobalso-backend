import enum
import uuid
from datetime import datetime
from sqlalchemy import String, Text, Boolean, DateTime, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
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
    utilisateur_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("utilisateurs.id"), nullable=False)

    type: Mapped[NotificationType] = mapped_column(Enum(NotificationType), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    lu: Mapped[bool] = mapped_column(Boolean, default=False)

    cree_le: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relations
    utilisateur: Mapped["User"] = relationship(back_populates="notifications")


class EmailStatus(str, enum.Enum):
    ENVOYE = "envoye"
    ECHEC = "echec"
    REPRIS = "repris"


class EmailLog(Base):
    __tablename__ = "journaux_email"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    utilisateur_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("utilisateurs.id"), nullable=False)

    type_email: Mapped[str] = mapped_column(String(100), nullable=False)
    statut: Mapped[EmailStatus] = mapped_column(Enum(EmailStatus), default=EmailStatus.ENVOYE, nullable=False)

    desabonne_le: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    envoye_le: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relations
    utilisateur: Mapped["User"] = relationship(back_populates="journaux_email")