from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class GitHubAuthUrlResponse(BaseModel):
    """Returns the authorization URL to initiate GitHub OAuth."""
    auth_url: str


class GitHubCallbackRequest(BaseModel):
    """Payload for completing GitHub OAuth exchange."""
    code: Optional[str] = None
    state: Optional[str] = None
    mock_username: Optional[str] = None


class GitHubIntegrationStatusResponse(BaseModel):
    """Public safe representation of operative's GitHub connection status. Never exposes access tokens."""
    is_connected: bool
    github_username: Optional[str] = None
    github_profile_url: Optional[str] = None
    selected_repository: Optional[str] = None
    repository_url: Optional[str] = None
    last_sync_at: Optional[datetime] = None
    last_sync_status: Optional[str] = None
    last_sync_error: Optional[str] = None
    last_commit_sha: Optional[str] = None
    last_commit_url: Optional[str] = None
    synced_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class GitHubRepoItem(BaseModel):
    """Represents a GitHub repository available to the authenticated operative."""
    full_name: str
    name: str
    html_url: str
    private: bool = False
    description: Optional[str] = None
    has_push_access: bool = True


class GitHubRepoSelectRequest(BaseModel):
    """Request to select or configure target repository for CTF solution commits."""
    repository: str = Field(..., min_length=1, max_length=255, description="Repository full name or name e.g. 'username/repo' or 'repo'")
    auto_create: bool = Field(default=False, description="Whether to automatically create the repo if it does not exist")


class GitHubSyncResponse(BaseModel):
    """Result summary of syncing CTF solutions to GitHub."""
    success: bool
    message: str
    synced_count: int = 0
    details: List[Dict[str, Any]] = Field(default_factory=list)
