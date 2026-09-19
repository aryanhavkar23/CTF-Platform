from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.follow import FollowStatusResponse, FollowUserItem
from app.services.follow_service import FollowService
from app.api.deps import get_current_active_user, get_current_user_optional

router = APIRouter(prefix="/api/users", tags=["Social Network & Follows"])


@router.post("/{user_id}/follow", response_model=FollowStatusResponse, status_code=status.HTTP_200_OK)
def follow_or_toggle_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FollowStatusResponse:
    """Toggles follow status for target user (LeetCode style)."""
    res = FollowService.toggle_follow(db, current_user.id, user_id)
    return FollowStatusResponse(**res)


@router.delete("/{user_id}/follow", response_model=FollowStatusResponse, status_code=status.HTTP_200_OK)
def unfollow_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FollowStatusResponse:
    """Explicitly unfollows target user."""
    res = FollowService.unfollow_user(db, current_user.id, user_id)
    return FollowStatusResponse(**res)


@router.get("/{user_id}/followers", response_model=List[FollowUserItem], status_code=status.HTTP_200_OK)
def get_user_followers(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> List[FollowUserItem]:
    """Retrieves list of operatives following target user."""
    followers = FollowService.get_followers(db, user_id, current_user.id if current_user else None)
    return [FollowUserItem(**f) for f in followers]


@router.get("/{user_id}/following", response_model=List[FollowUserItem], status_code=status.HTTP_200_OK)
def get_user_following(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> List[FollowUserItem]:
    """Retrieves list of operatives whom target user is following."""
    following = FollowService.get_following(db, user_id, current_user.id if current_user else None)
    return [FollowUserItem(**f) for f in following]
