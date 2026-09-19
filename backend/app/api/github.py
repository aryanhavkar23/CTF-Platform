import base64
import json
import logging
import urllib.parse
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.database import get_db
from app.models.user import User
from app.schemas.github import (
    GitHubAuthUrlResponse,
    GitHubCallbackRequest,
    GitHubIntegrationStatusResponse,
    GitHubRepoItem,
    GitHubRepoSelectRequest,
    GitHubSyncResponse,
)
from app.services.github_service import GitHubService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/github", tags=["GitHub Integration"])


@router.get("/oauth/url", response_model=GitHubAuthUrlResponse, status_code=status.HTTP_200_OK)
def get_github_oauth_url(
    current_user: User = Depends(get_current_active_user)
):
    """Generates a secure GitHub OAuth 2.0 authorization URL with minimal repository scope."""
    url = GitHubService.get_auth_url(current_user.id)
    return GitHubAuthUrlResponse(auth_url=url)


@router.get("/oauth/callback")
def github_oauth_callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    mock: Optional[bool] = Query(False),
    db: Session = Depends(get_db)
):
    """Handles browser redirect from GitHub OAuth and redirects to the operative's profile page."""
    user: Optional[User] = None
    if state:
        try:
            raw_state = base64.urlsafe_b64decode(state.encode("utf-8")).decode("utf-8")
            state_data = json.loads(raw_state)
            user_id = UUID(state_data.get("user_id"))
            user = db.query(User).filter(User.id == user_id).first()
        except Exception as e:
            logger.warning(f"Unable to parse state in GitHub callback: {e}")

    if user:
        try:
            GitHubService.exchange_oauth_code(db, user, code=code, mock_username=user.github_username if mock else None)
            return RedirectResponse(url="/#profile?github=connected")
        except Exception as e:
            logger.error(f"GitHub OAuth callback exchange error: {e}")
            return RedirectResponse(url=f"/#profile?github=error&message={urllib.parse.quote(str(e))}")

    return RedirectResponse(url="/#profile?github=connected")


@router.post("/oauth/exchange", response_model=GitHubIntegrationStatusResponse, status_code=status.HTTP_200_OK)
def exchange_github_oauth(
    request: GitHubCallbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Exchanges GitHub OAuth code or executes simulated dev connection for single-page application."""
    GitHubService.exchange_oauth_code(
        db=db,
        user=current_user,
        code=request.code,
        mock_username=request.mock_username
    )
    return GitHubService.get_status(db, current_user.id)


@router.get("/status", response_model=GitHubIntegrationStatusResponse, status_code=status.HTTP_200_OK)
def get_github_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Returns current operative's GitHub connection status, repository configuration, and sync telemetry."""
    return GitHubService.get_status(db, current_user.id)


@router.get("/repositories", response_model=List[GitHubRepoItem], status_code=status.HTTP_200_OK)
def get_user_repositories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Retrieves list of GitHub repositories available to the authenticated operative."""
    return GitHubService.list_user_repositories(db, current_user.id)


@router.post("/repository", response_model=GitHubIntegrationStatusResponse, status_code=status.HTTP_200_OK)
def configure_repository(
    request: GitHubRepoSelectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Selects and verifies write access to the operative's target CTF solutions repository."""
    GitHubService.configure_repository(
        db=db,
        user_id=current_user.id,
        repository_name=request.repository,
        auto_create=request.auto_create
    )
    return GitHubService.get_status(db, current_user.id)


@router.post("/sync", response_model=GitHubSyncResponse, status_code=status.HTTP_200_OK)
def sync_all_solves(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Manually triggers synchronization of all historical uncommitted solves to the configured repository."""
    return GitHubService.sync_all_uncommitted_solves(db, current_user.id)


@router.post("/disconnect", status_code=status.HTTP_200_OK)
def disconnect_github(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Revokes and clears GitHub OAuth credentials for the authenticated operative."""
    GitHubService.disconnect(db, current_user.id)
    return {"message": "GitHub integration disconnected successfully."}
