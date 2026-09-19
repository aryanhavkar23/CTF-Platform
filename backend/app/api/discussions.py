from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.api.deps import get_current_active_user, get_current_user_optional, require_role
from app.schemas.discussion import (
    DiscussionCreate,
    DiscussionUpdate,
    DiscussionResponse,
    DiscussionListResponse,
    CommentCreate,
    CommentUpdate,
    CommentResponse,
    CommentListResponse,
)
from app.services.discussion_service import DiscussionService

router = APIRouter(tags=["Discussions"])


# -----------------------------------------------------------------------------
# Challenge Discussion Endpoints
# -----------------------------------------------------------------------------

@router.post(
    "/api/challenges/{challenge_id}/discussions",
    response_model=DiscussionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create challenge discussion"
)
def create_discussion(
    challenge_id: UUID,
    payload: DiscussionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Authenticated user creates a new discussion for an accessible challenge."""
    if getattr(current_user, "is_muted", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been muted by an administrator."
        )
    return DiscussionService.create_discussion(
        db=db,
        challenge_id=challenge_id,
        user=current_user,
        data=payload
    )


@router.get(
    "/api/challenges/{challenge_id}/discussions",
    response_model=DiscussionListResponse,
    status_code=status.HTTP_200_OK,
    summary="List discussions for a challenge"
)
def list_discussions(
    challenge_id: UUID,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    sort: str = Query("newest", regex="^(newest|oldest|pinned)$", description="Sort order: newest, oldest, pinned"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Lists discussions for a challenge. Pinned discussions are prioritized."""
    return DiscussionService.list_discussions(
        db=db,
        challenge_id=challenge_id,
        user=current_user,
        page=page,
        limit=limit,
        sort=sort
    )


# -----------------------------------------------------------------------------
# Individual Discussion Endpoints
# -----------------------------------------------------------------------------

@router.get(
    "/api/discussions/{discussion_id}",
    response_model=DiscussionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get discussion detail"
)
def get_discussion(
    discussion_id: UUID,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Retrieves single discussion details. Deleted content is masked for non-moderators."""
    return DiscussionService.get_discussion(db=db, discussion_id=discussion_id, user=current_user)


@router.put(
    "/api/discussions/{discussion_id}",
    response_model=DiscussionResponse,
    status_code=status.HTTP_200_OK,
    summary="Update discussion"
)
def update_discussion(
    discussion_id: UUID,
    payload: DiscussionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Author or moderator updates a discussion title/content/spoiler status."""
    return DiscussionService.update_discussion(
        db=db,
        discussion_id=discussion_id,
        user=current_user,
        data=payload
    )


@router.delete(
    "/api/discussions/{discussion_id}",
    status_code=status.HTTP_200_OK,
    summary="Soft-delete discussion"
)
def delete_discussion(
    discussion_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Author or moderator soft-deletes a discussion."""
    return DiscussionService.delete_discussion(
        db=db,
        discussion_id=discussion_id,
        user=current_user
    )


# -----------------------------------------------------------------------------
# Moderation: Lock / Unlock & Pin / Unpin
# -----------------------------------------------------------------------------

@router.post(
    "/api/discussions/{discussion_id}/lock",
    response_model=DiscussionResponse,
    status_code=status.HTTP_200_OK,
    summary="Lock discussion"
)
def lock_discussion(
    discussion_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """Moderator/admin locks discussion to prevent new comments/replies."""
    return DiscussionService.lock_discussion(db=db, discussion_id=discussion_id, user=current_user)


@router.post(
    "/api/discussions/{discussion_id}/unlock",
    response_model=DiscussionResponse,
    status_code=status.HTTP_200_OK,
    summary="Unlock discussion"
)
def unlock_discussion(
    discussion_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """Moderator/admin unlocks discussion to restore commenting."""
    return DiscussionService.unlock_discussion(db=db, discussion_id=discussion_id, user=current_user)


@router.post(
    "/api/discussions/{discussion_id}/pin",
    response_model=DiscussionResponse,
    status_code=status.HTTP_200_OK,
    summary="Pin discussion"
)
def pin_discussion(
    discussion_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """Moderator/admin pins discussion to top of challenge discussions."""
    return DiscussionService.pin_discussion(db=db, discussion_id=discussion_id, user=current_user)


@router.post(
    "/api/discussions/{discussion_id}/unpin",
    response_model=DiscussionResponse,
    status_code=status.HTTP_200_OK,
    summary="Unpin discussion"
)
def unpin_discussion(
    discussion_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """Moderator/admin unpins discussion."""
    return DiscussionService.unpin_discussion(db=db, discussion_id=discussion_id, user=current_user)


# -----------------------------------------------------------------------------
# Comments & Threaded Replies
# -----------------------------------------------------------------------------

@router.post(
    "/api/discussions/{discussion_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create comment or reply"
)
def create_comment(
    discussion_id: UUID,
    payload: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Authenticated user posts a comment or reply to an unlocked discussion."""
    if getattr(current_user, "is_muted", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been muted by an administrator."
        )
    return DiscussionService.create_comment(
        db=db,
        discussion_id=discussion_id,
        user=current_user,
        data=payload
    )


@router.get(
    "/api/discussions/{discussion_id}/comments",
    response_model=CommentListResponse,
    status_code=status.HTTP_200_OK,
    summary="List comments for discussion"
)
def list_comments(
    discussion_id: UUID,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Lists chronological comments for a discussion with reply counts."""
    return DiscussionService.list_comments(
        db=db,
        discussion_id=discussion_id,
        user=current_user,
        page=page,
        limit=limit
    )


@router.put(
    "/api/comments/{comment_id}",
    response_model=CommentResponse,
    status_code=status.HTTP_200_OK,
    summary="Update comment"
)
def update_comment(
    comment_id: UUID,
    payload: CommentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Author or moderator updates a comment."""
    return DiscussionService.update_comment(
        db=db,
        comment_id=comment_id,
        user=current_user,
        data=payload
    )


@router.delete(
    "/api/comments/{comment_id}",
    status_code=status.HTTP_200_OK,
    summary="Soft-delete comment"
)
def delete_comment(
    comment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Author or moderator soft-deletes a comment."""
    return DiscussionService.delete_comment(
        db=db,
        comment_id=comment_id,
        user=current_user
    )
