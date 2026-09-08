import uuid
from sqlalchemy import Column, String, Text, Boolean, ForeignKey, Uuid, DateTime
from sqlalchemy.orm import relationship

from app.models.base import TimeStampedModel, utc_now


class Discussion(TimeStampedModel):
    """Represents a discussion thread associated with a specific challenge."""
    __tablename__ = "discussions"

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
    is_pinned = Column(Boolean, default=False, nullable=False, index=True)
    is_locked = Column(Boolean, default=False, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    contains_spoiler = Column(Boolean, default=False, nullable=False)

    # Relationships
    challenge = relationship("Challenge", back_populates="discussions")
    user = relationship("User", back_populates="discussions")
    comments = relationship(
        "DiscussionComment",
        back_populates="discussion",
        cascade="all, delete-orphan",
        order_by="DiscussionComment.created_at.asc()"
    )

    def __repr__(self) -> str:
        return f"<Discussion id={self.id} title={self.title!r} pinned={self.is_pinned} locked={self.is_locked}>"


class DiscussionComment(TimeStampedModel):
    """Represents a top-level or threaded reply comment within a discussion."""
    __tablename__ = "discussion_comments"

    discussion_id = Column(
        Uuid,
        ForeignKey("discussions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id = Column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    parent_comment_id = Column(
        Uuid,
        ForeignKey("discussion_comments.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    content = Column(Text, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    contains_spoiler = Column(Boolean, default=False, nullable=False)

    # Relationships
    discussion = relationship("Discussion", back_populates="comments")
    user = relationship("User", back_populates="discussion_comments")
    parent = relationship("DiscussionComment", remote_side="DiscussionComment.id", back_populates="replies")
    replies = relationship(
        "DiscussionComment",
        back_populates="parent",
        cascade="all, delete-orphan",
        order_by="DiscussionComment.created_at.asc()"
    )

    def __repr__(self) -> str:
        return f"<DiscussionComment id={self.id} discussion_id={self.discussion_id} parent_id={self.parent_comment_id}>"
