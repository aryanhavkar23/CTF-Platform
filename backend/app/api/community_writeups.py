from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.community_writeup import (
    UserWriteupCreate,
    UserWriteupUpdate,
    UserWriteupResponse,
    WriteupUpvoteResponse,
)
from app.services.community_writeup_service import CommunityWriteupService
from app.api.deps import get_current_active_user, get_current_user_optional

router = APIRouter(prefix="/api/challenges", tags=["Community Writeups"])


@router.get("/{challenge_id}/solutions", response_model=List[UserWriteupResponse], status_code=status.HTTP_200_OK)
@router.get("/{challenge_id}/community-writeups", response_model=List[UserWriteupResponse], status_code=status.HTTP_200_OK)
def list_community_writeups(
    challenge_id: UUID,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> List[UserWriteupResponse]:
    """Retrieves all published community solutions and writeups for a challenge."""
    writeups = CommunityWriteupService.list_writeups(db, challenge_id, current_user)
    return [UserWriteupResponse(**w) for w in writeups]


@router.post("/{challenge_id}/solutions", response_model=UserWriteupResponse, status_code=status.HTTP_201_CREATED)
@router.post("/{challenge_id}/community-writeups", response_model=UserWriteupResponse, status_code=status.HTTP_201_CREATED)
def publish_community_writeup(
    challenge_id: UUID,
    payload: UserWriteupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> UserWriteupResponse:
    """Publishes a new community solution/writeup for a challenge."""
    writeup = CommunityWriteupService.create_writeup(db, challenge_id, current_user.id, payload)
    return UserWriteupResponse(**writeup)


@router.put("/{challenge_id}/solutions/{writeup_id}", response_model=UserWriteupResponse, status_code=status.HTTP_200_OK)
@router.put("/{challenge_id}/community-writeups/{writeup_id}", response_model=UserWriteupResponse, status_code=status.HTTP_200_OK)
def update_community_writeup(
    challenge_id: UUID,
    writeup_id: UUID,
    payload: UserWriteupUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> UserWriteupResponse:
    """Updates a previously published community writeup."""
    writeup = CommunityWriteupService.update_writeup(db, writeup_id, current_user, payload)
    return UserWriteupResponse(**writeup)


@router.delete("/{challenge_id}/solutions/{writeup_id}", status_code=status.HTTP_200_OK)
@router.delete("/{challenge_id}/community-writeups/{writeup_id}", status_code=status.HTTP_200_OK)
def delete_community_writeup(
    challenge_id: UUID,
    writeup_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Deletes a community writeup (Author or Admin)."""
    CommunityWriteupService.delete_writeup(db, writeup_id, current_user)
    return {"status": "deleted", "message": "Writeup successfully removed."}


@router.post("/{challenge_id}/solutions/{writeup_id}/upvote", response_model=WriteupUpvoteResponse, status_code=status.HTTP_200_OK)
@router.post("/{challenge_id}/community-writeups/{writeup_id}/upvote", response_model=WriteupUpvoteResponse, status_code=status.HTTP_200_OK)
def toggle_upvote_writeup(
    challenge_id: UUID,
    writeup_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> WriteupUpvoteResponse:
    """Toggles upvote for a community writeup."""
    count, is_upvoted = CommunityWriteupService.toggle_upvote(db, writeup_id, current_user)
    return WriteupUpvoteResponse(writeup_id=writeup_id, upvotes_count=count, is_upvoted=is_upvoted)
