import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import utc_now, TimeStampedModel


class CriteriaType(str, enum.Enum):
    """Supported authoritative criteria types for unlocking badges."""
    FIRST_SOLVE = "first_solve"
    SOLVE_COUNT = "solve_count"
    POINTS_REACHED = "points_reached"
    CATEGORY_SOLVES = "category_solves"
    EVENT_PARTICIPATION = "event_participation"
    STREAK_DAYS = "streak_days"


class Badge(TimeStampedModel):
    """Badge definition entity stored in the database."""
    __tablename__ = "badges"

    name = Column(String(100), nullable=False)
    slug = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(String(500), nullable=False)
    icon = Column(String(255), nullable=False)  # Safe identifier/icon key/URL
    criteria_type = Column(String(50), index=True, nullable=False)
    criteria_value = Column(Integer, default=1, nullable=False)
    is_active = Column(Boolean, default=True, index=True, nullable=False)

    # Relationships
    user_badges = relationship(
        "UserBadge",
        back_populates="badge",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Badge {self.slug} (criteria: {self.criteria_type} >= {self.criteria_value})>"


class UserBadge(Base):
    """Relational join table tracking awarded badges per user."""
    __tablename__ = "user_badges"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    badge_id = Column(
        Uuid,
        ForeignKey("badges.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    awarded_at = Column(
        DateTime(timezone=True),
        default=utc_now,
        index=True,
        nullable=False,
    )

    # Relationships
    user = relationship("User", back_populates="badges")
    badge = relationship("Badge", back_populates="user_badges")

    __table_args__ = (
        UniqueConstraint("user_id", "badge_id", name="uq_user_badge"),
    )

    def __repr__(self) -> str:
        return f"<UserBadge user_id={self.user_id} badge_id={self.badge_id} awarded_at={self.awarded_at}>"
