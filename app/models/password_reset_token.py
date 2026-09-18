import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class PasswordResetToken(Base):
    __tablename__ = "jetons_reinitialisation_mot_de_passe"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    utilisateur_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("utilisateurs.id"), nullable=False)
    jeton: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)

    expire_le: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    utilise: Mapped[bool] = mapped_column(Boolean, default=False)

    cree_le: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)