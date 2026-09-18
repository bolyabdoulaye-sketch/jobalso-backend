import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class ShortlistEntry(Base):
    __tablename__ = "shortlist_entries"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id"), nullable=False)
    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("candidate_profiles.id"), nullable=False)

    is_selected_for_comparison: Mapped[bool] = mapped_column(Boolean, default=False)  # JA-051

    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)  # JA-049