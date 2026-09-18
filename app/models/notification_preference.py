import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class NotificationPreference(Base):
    __tablename__ = "preferences_notification"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    utilisateur_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("utilisateurs.id"), unique=True, nullable=False)

    notifier_nouvelle_recommandation: Mapped[bool] = mapped_column(Boolean, default=True)
    notifier_candidature_recue: Mapped[bool] = mapped_column(Boolean, default=True)
    notifier_changement_etape: Mapped[bool] = mapped_column(Boolean, default=True)
    notifier_entrevue_proposee: Mapped[bool] = mapped_column(Boolean, default=True)
    notifier_candidature_refusee: Mapped[bool] = mapped_column(Boolean, default=True)
    notifier_recapitulatif_hebdo: Mapped[bool] = mapped_column(Boolean, default=False)
    notifier_rappel_profil: Mapped[bool] = mapped_column(Boolean, default=True)

    modifie_le: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RecommendationDismissal(Base):
    __tablename__ = "recommandations_rejetees"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    profil_candidat_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("profils_candidats.id"), nullable=False)
    poste_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("postes.id"), nullable=False)

    rejete_le: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)