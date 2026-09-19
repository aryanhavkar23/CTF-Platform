import uuid
from sqlalchemy import Column, String, Text, Boolean, Integer, ForeignKey, Uuid, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship, backref

from app.database import Base
from app.models.base import TimeStampedModel, utc_now


class UserWriteup(TimeStampedModel):
    """Represents a community solution/writeup published by an operative for a challenge."""
    __tablename__ = "user_writeups"

    challenge_id = Column(
        Uuid,
        ForeignKey("challenges.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id = Column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    tags = Column(String(255), nullable=True)  # Comma-separated or label tags
    upvotes_count = Column(Integer, default=0, nullable=False)
    is_published = Column(Boolean, default=True, nullable=False, index=True)

    # Relationships
    challenge = relationship("Challenge", backref=backref("user_writeups", cascade="all, delete-orphan"))
    user = relationship("User", backref=backref("user_writeups", cascade="all, delete-orphan"))
    upvotes = relationship("WriteupUpvote", back_populates="writeup", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<UserWriteup id={self.id} title={self.title!r} user_id={self.user_id} challenge_id={self.challenge_id}>"


class WriteupUpvote(Base):
    """Tracks upvotes given to user writeups to enforce 1 vote per user."""
    __tablename__ = "writeup_upvotes"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    writeup_id = Column(
        Uuid,
        ForeignKey("user_writeups.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id = Column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("writeup_id", "user_id", name="uq_writeup_user_upvote"),
    )

    # Relationships
    writeup = relationship("UserWriteup", back_populates="upvotes")
    user = relationship("User")

    def __repr__(self) -> str:
        return f"<WriteupUpvote writeup_id={self.writeup_id} user_id={self.user_id}>"
