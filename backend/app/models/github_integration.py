import uuid
from sqlalchemy import Column, String, Text, Boolean, Integer, ForeignKey, Uuid, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import TimeStampedModel, utc_now


class GitHubIntegration(TimeStampedModel):
    """Stores GitHub OAuth connection, encrypted access token, and repository configuration for an operative."""
    __tablename__ = "github_integrations"

    user_id = Column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    github_user_id = Column(String(100), nullable=True)
    github_username = Column(String(100), nullable=False, index=True)
    github_profile_url = Column(String(255), nullable=True)
    encrypted_access_token = Column(Text, nullable=False)
    token_type = Column(String(50), default="bearer", nullable=False)
    scope = Column(String(255), default="repo,read:user", nullable=False)

    selected_repository = Column(String(255), nullable=True)  # e.g. "octocat/ctf-solutions"
    repository_url = Column(String(512), nullable=True)
    is_connected = Column(Boolean, default=True, nullable=False, index=True)

    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    last_sync_status = Column(String(50), nullable=True)  # "success", "error", "pending"
    last_sync_error = Column(Text, nullable=True)
    last_commit_sha = Column(String(100), nullable=True)
    last_commit_url = Column(String(512), nullable=True)

    # Relationships
    user = relationship("User", back_populates="github_integration")

    def __repr__(self) -> str:
        return f"<GitHubIntegration user_id={self.user_id} github_username={self.github_username!r} repo={self.selected_repository!r}>"


class GitHubSubmissionSync(Base):
    """Tracks individual challenge solve commits sent to GitHub to prevent duplicate commits."""
    __tablename__ = "github_submission_syncs"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    challenge_id = Column(
        Uuid,
        ForeignKey("challenges.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    submission_id = Column(
        Uuid,
        ForeignKey("submissions.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    solve_id = Column(
        Uuid,
        ForeignKey("solves.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    file_path = Column(String(255), nullable=False)  # e.g. "ctf-solutions/web-sqli/README.md"
    commit_sha = Column(String(100), nullable=True)
    commit_url = Column(String(512), nullable=True)
    status = Column(String(50), default="synced", nullable=False)  # "synced", "failed"
    error_message = Column(Text, nullable=True)
    synced_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "challenge_id", name="uq_github_user_challenge_sync"),
    )

    # Relationships
    user = relationship("User")
    challenge = relationship("Challenge")

    def __repr__(self) -> str:
        return f"<GitHubSubmissionSync user_id={self.user_id} challenge_id={self.challenge_id} sha={self.commit_sha!r}>"
