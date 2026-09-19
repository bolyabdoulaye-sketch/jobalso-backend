import enum
import uuid
from datetime import datetime
from sqlalchemy import String, Float, Text, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class BiasCategory(str, enum.Enum):
    GENRE = "genre"
    AGE = "age"
    ORIGINE_NOM = "origine_nom"
    ETABLISSEMENT = "etablissement"


class BiasTestResult(Base):
    __tablename__ = "resultats_tests_biais"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    categorie_biais: Mapped[BiasCategory] = mapped_column(Enum(BiasCategory), nullable=False)  # JA-046
    description_test: Mapped[str] = mapped_column(Text, nullable=False)

    ecart_score: Mapped[float] = mapped_column(Float, nullable=False)  # ecart mesure sur profils apparies

    version_modele: Mapped[str] = mapped_column(String(50), nullable=False)

    execute_le: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)