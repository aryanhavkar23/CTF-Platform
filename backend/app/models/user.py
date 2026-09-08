import enum
from sqlalchemy import Column, String, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.models.base import TimeStampedModel


class UserRole(str, enum.Enum):
    STUDENT = "student"
    MODERATOR = "moderator"
    ADMIN = "admin"


class User(TimeStampedModel):
    __tablename__ = "users"

    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(
        SQLEnum(UserRole, native_enum=False, length=20),
        default=UserRole.STUDENT,
        nullable=False,
        index=True
    )
    name = Column(String(100), nullable=True)
    bio = Column(String(500), nullable=True)
    college = Column(String(150), nullable=True, index=True)
    avatar_url = Column(String(512), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    # Relationships
    teams = relationship("Team", secondary="team_members", back_populates="members", overlaps="team_memberships")
    team_memberships = relationship("TeamMember", back_populates="user", cascade="all, delete-orphan")
    owned_teams = relationship("Team", foreign_keys="Team.owner_id", back_populates="owner")
    captained_teams = relationship("Team", foreign_keys="Team.captain_id", back_populates="captain", overlaps="owned_teams,owner")
    submissions = relationship("Submission", back_populates="user", cascade="all, delete-orphan")
    activities = relationship("UserActivity", back_populates="user", cascade="all, delete-orphan")
    badges = relationship("UserBadge", back_populates="user", cascade="all, delete-orphan")
    discussions = relationship("Discussion", back_populates="user", cascade="all, delete-orphan")
    discussion_comments = relationship("DiscussionComment", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User username={self.username!r} role={self.role.value!r}>"
