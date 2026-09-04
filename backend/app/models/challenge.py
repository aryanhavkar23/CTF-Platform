import enum
from sqlalchemy import Column, String, Text, Integer, Boolean, ForeignKey, Enum as SQLEnum, CheckConstraint, Uuid
from sqlalchemy.orm import relationship
from app.models.base import TimeStampedModel


class ChallengeDifficulty(str, enum.Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    INSANE = "insane"


class ChallengeType(str, enum.Enum):
    STATIC = "static"
    LIVE = "live"


class Challenge(TimeStampedModel):
    __tablename__ = "challenges"

    title = Column(String(200), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=False)
    category_id = Column(Uuid, ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False, index=True)
    difficulty = Column(
        SQLEnum(ChallengeDifficulty, native_enum=False, length=20),
        default=ChallengeDifficulty.EASY,
        nullable=False,
        index=True
    )
    points = Column(Integer, nullable=False)
    flag_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    challenge_type = Column(
        SQLEnum(ChallengeType, native_enum=False, length=20),
        default=ChallengeType.STATIC,
        nullable=False
    )
    file_urls = Column(Text, nullable=True)  # JSON or delimited file storage URLs

    # Constraints
    __table_args__ = (
        CheckConstraint("points >= 0", name="check_positive_points"),
    )

    # Relationships
    category = relationship("Category", back_populates="challenges")
    events = relationship("Event", secondary="event_challenges", back_populates="challenges")
    submissions = relationship("Submission", back_populates="challenge", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Challenge title={self.title!r} points={self.points} difficulty={self.difficulty.value!r}>"
