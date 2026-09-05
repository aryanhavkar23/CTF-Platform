import enum
import uuid
from sqlalchemy import Column, String, Text, Integer, Boolean, ForeignKey, Enum as SQLEnum, CheckConstraint, Uuid, DateTime
from sqlalchemy.orm import relationship
from app.models.base import TimeStampedModel, utc_now
from app.database import Base


class ChallengeDifficulty(str, enum.Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    INSANE = "insane"


class ChallengeType(str, enum.Enum):
    STATIC = "static"
    LIVE = "live"


class WriteupVisibility(str, enum.Enum):
    HIDDEN = "hidden"
    AFTER_SOLVE = "after_solve"
    AFTER_EVENT = "after_event"
    PUBLIC = "public"


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
    is_live_instance = Column(Boolean, default=False, nullable=False)
    docker_image = Column(String(255), nullable=True)
    file_urls = Column(Text, nullable=True)

    # Constraints
    __table_args__ = (
        CheckConstraint("points >= 0", name="check_positive_points"),
    )

    # Relationships
    category = relationship("Category", back_populates="challenges")
    events = relationship("Event", secondary="event_challenges", back_populates="challenges")
    submissions = relationship("Submission", back_populates="challenge", cascade="all, delete-orphan")
    files = relationship("ChallengeFile", back_populates="challenge", cascade="all, delete-orphan")
    hints = relationship("ChallengeHint", back_populates="challenge", cascade="all, delete-orphan", order_by="ChallengeHint.order")
    writeup = relationship("ChallengeWriteup", back_populates="challenge", uselist=False, cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Challenge title={self.title!r} points={self.points} difficulty={self.difficulty.value!r}>"


class ChallengeFile(Base):
    __tablename__ = "challenge_files"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    challenge_id = Column(Uuid, ForeignKey("challenges.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    storage_path = Column(String(512), nullable=False)
    file_size = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    challenge = relationship("Challenge", back_populates="files")

    def __repr__(self) -> str:
        return f"<ChallengeFile filename={self.filename!r}>"


class ChallengeHint(TimeStampedModel):
    __tablename__ = "challenge_hints"

    challenge_id = Column(Uuid, ForeignKey("challenges.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(150), default="Hint", nullable=False)
    content = Column(Text, nullable=False)
    point_deduction = Column(Integer, default=0, nullable=False)
    order = Column(Integer, default=1, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    __table_args__ = (
        CheckConstraint("point_deduction >= 0", name="check_positive_hint_deduction"),
    )

    # Relationships
    challenge = relationship("Challenge", back_populates="hints")
    usages = relationship("HintUsage", back_populates="hint", cascade="all, delete-orphan")

    @property
    def points_deduction(self) -> int:
        return self.point_deduction

    @points_deduction.setter
    def points_deduction(self, val: int):
        self.point_deduction = val

    @property
    def display_order(self) -> int:
        return self.order

    @display_order.setter
    def display_order(self, val: int):
        self.order = val

    def __repr__(self) -> str:
        return f"<ChallengeHint title={self.title!r} order={self.order} deduction={self.point_deduction}>"


class ChallengeWriteup(TimeStampedModel):
    __tablename__ = "challenge_writeups"

    challenge_id = Column(Uuid, ForeignKey("challenges.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    title = Column(String(150), default="Official Writeup", nullable=False)
    content = Column(Text, nullable=False)
    visibility = Column(
        SQLEnum(WriteupVisibility, native_enum=False, length=20),
        default=WriteupVisibility.HIDDEN,
        nullable=False
    )

    # Relationships
    challenge = relationship("Challenge", back_populates="writeup")

    def __repr__(self) -> str:
        return f"<ChallengeWriteup title={self.title!r} visibility={self.visibility.value!r}>"
