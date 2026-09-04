import uuid
from sqlalchemy import Column, String, ForeignKey, Table, DateTime, Uuid, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import TimeStampedModel, utc_now


team_members = Table(
    "team_members",
    Base.metadata,
    Column("team_id", Uuid, ForeignKey("teams.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, unique=True),
    Column("joined_at", DateTime(timezone=True), default=utc_now, nullable=False),
)


class Team(TimeStampedModel):
    __tablename__ = "teams"

    name = Column(String(100), unique=True, index=True, nullable=False)
    captain_id = Column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    invite_code = Column(String(64), unique=True, index=True, nullable=False, default=lambda: uuid.uuid4().hex[:16])

    # Relationships
    captain = relationship("User", foreign_keys=[captain_id], back_populates="captained_teams")
    members = relationship("User", secondary=team_members, back_populates="teams")
    submissions = relationship("Submission", back_populates="team")

    def __repr__(self) -> str:
        return f"<Team name={self.name!r}>"
