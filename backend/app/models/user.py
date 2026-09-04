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
    college = Column(String(150), nullable=True)
    avatar_url = Column(String(512), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    # Relationships
    teams = relationship("Team", secondary="team_members", back_populates="members")
    captained_teams = relationship("Team", back_populates="captain")
    submissions = relationship("Submission", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User username={self.username!r} role={self.role.value!r}>"
