import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Uuid
from app.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TimeStampedModel(Base):
    """Abstract base model with primary UUID key and UTC timestamps."""
    __abstract__ = True

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
