import uuid
from sqlalchemy import Column, ForeignKey, Uuid, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship, backref

from app.database import Base
from app.models.base import utc_now


class UserFollow(Base):
    """Represents a follow relationship where follower_id follows following_id (LeetCode style)."""
    __tablename__ = "user_follows"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    follower_id = Column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    following_id = Column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("follower_id", "following_id", name="uq_user_follows"),
    )

    # Relationships
    follower = relationship("User", foreign_keys=[follower_id], backref=backref("following_relations", cascade="all, delete-orphan"))
    following = relationship("User", foreign_keys=[following_id], backref=backref("follower_relations", cascade="all, delete-orphan"))

    def __repr__(self) -> str:
        return f"<UserFollow follower={self.follower_id} following={self.following_id}>"
