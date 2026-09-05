import uuid
from sqlalchemy import Column, String, Text, Boolean, ForeignKey, DateTime, Uuid, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import TimeStampedModel, utc_now


class TeamMember(TimeStampedModel):
    __tablename__ = "team_members"

    team_id = Column(Uuid, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    joined_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    role = Column(String(20), default="member", server_default="member", nullable=False)
    is_active = Column(Boolean, default=True, server_default="true", nullable=False)

    __table_args__ = (
        UniqueConstraint("team_id", "user_id", name="uq_team_members_team_user"),
    )

    team = relationship("Team", back_populates="memberships", overlaps="teams,members")
    user = relationship("User", back_populates="team_memberships", overlaps="teams,members")

    def __repr__(self) -> str:
        return f"<TeamMember team_id={self.team_id} user_id={self.user_id} role={self.role!r}>"


# Backwards compatibility alias for the underlying table
team_members = TeamMember.__table__


class Team(TimeStampedModel):
    __tablename__ = "teams"

    name = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    owner_id = Column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    captain_id = Column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=True, index=True)
    college = Column(String(150), nullable=True, index=True)
    is_active = Column(Boolean, default=True, server_default="true", nullable=False)
    invite_code = Column(String(64), unique=True, index=True, nullable=True, default=lambda: uuid.uuid4().hex[:16])

    def __init__(self, **kwargs):
        if "captain_id" in kwargs and "owner_id" not in kwargs:
            kwargs["owner_id"] = kwargs["captain_id"]
        elif "owner_id" in kwargs and "captain_id" not in kwargs:
            kwargs["captain_id"] = kwargs["owner_id"]
        super().__init__(**kwargs)

    # Relationships
    owner = relationship("User", foreign_keys=[owner_id], back_populates="owned_teams")
    captain = relationship("User", foreign_keys=[captain_id], back_populates="captained_teams", overlaps="owner")
    memberships = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan", overlaps="teams,members")
    members = relationship("User", secondary="team_members", back_populates="teams", overlaps="memberships,team,user,team_memberships")
    submissions = relationship("Submission", back_populates="team")

    def __repr__(self) -> str:
        return f"<Team name={self.name!r} owner_id={self.owner_id}>"
