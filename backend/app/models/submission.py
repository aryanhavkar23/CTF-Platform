from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, Uuid, Index
from sqlalchemy.orm import relationship
from app.models.base import TimeStampedModel


class Submission(TimeStampedModel):
    __tablename__ = "submissions"

    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    team_id = Column(Uuid, ForeignKey("teams.id", ondelete="SET NULL"), nullable=True, index=True)
    challenge_id = Column(Uuid, ForeignKey("challenges.id", ondelete="CASCADE"), nullable=False, index=True)
    event_id = Column(Uuid, ForeignKey("events.id", ondelete="CASCADE"), nullable=True, index=True)
    submitted_flag_hash = Column(String(255), nullable=False)
    is_correct = Column(Boolean, default=False, nullable=False, index=True)
    points_awarded = Column(Integer, default=0, nullable=False)

    # Relationships
    user = relationship("User", back_populates="submissions")
    team = relationship("Team", back_populates="submissions")
    challenge = relationship("Challenge", back_populates="submissions")
    event = relationship("Event", back_populates="submissions")

    # Indexes
    __table_args__ = (
        Index("idx_submission_user_challenge_correct", "user_id", "challenge_id", "is_correct"),
        Index("idx_submission_team_challenge_correct", "team_id", "challenge_id", "is_correct"),
    )

    def __repr__(self) -> str:
        return f"<Submission user={self.user_id} challenge={self.challenge_id} correct={self.is_correct}>"
