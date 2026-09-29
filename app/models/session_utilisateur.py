import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.dates import utcnow
from app.db.base import Base


class SessionUtilisateur(Base):
    """Session de connexion : un jeton de rafraîchissement, stocké haché.

    Chaque rafraîchissement révoque la session et en crée une nouvelle
    (rotation). Réutiliser un jeton déjà révoqué révoque toutes les sessions
    de l'utilisateur : c'est le signe d'un vol de jeton.
    """

    __tablename__ = "session_utilisateur"

    id_session: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    id_utilisateur: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("utilisateur.id_utilisateur", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    date_creation: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    date_expiration: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    date_revocation: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
