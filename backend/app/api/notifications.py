import math
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.api.deps import get_current_active_user
from app.schemas.notification import (
    NotificationResponse,
    NotificationListResponse,
    UnreadCountResponse,
    MarkAllReadResponse,
)
from app.services.notification_service import NotificationService

router = APIRouter(tags=["Notifications"])


@router.get(
    "/api/notifications",
    response_model=NotificationListResponse,
    summary="Get user notifications",
)
def get_notifications(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    unread_only: bool = Query(False, description="Filter to only unread notifications"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Retrieve paginated notifications for the authenticated user, newest first."""
    items, total, unread_count = NotificationService.get_user_notifications(
        db=db,
        user_id=current_user.id,
        page=page,
        limit=limit,
        unread_only=unread_only,
    )
    total_pages = max(1, math.ceil(total / limit)) if total > 0 else 1

    return NotificationListResponse(
        items=[NotificationResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages,
        unread_count=unread_count,
    )


@router.get(
    "/api/notifications/unread-count",
    response_model=UnreadCountResponse,
    summary="Get unread notification count",
)
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Returns the total number of unread notifications for the authenticated user."""
    count = NotificationService.count_unread_notifications(db=db, user_id=current_user.id)
    return UnreadCountResponse(unread_count=count)


@router.post(
    "/api/notifications/{notification_id}/read",
    response_model=NotificationResponse,
    summary="Mark single notification as read",
)
def mark_notification_as_read(
    notification_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Marks a notification as read. Validates ownership to prevent IDOR vulnerabilities."""
    notification = NotificationService.mark_notification_as_read(
        db=db,
        notification_id=notification_id,
        user_id=current_user.id,
    )
    return NotificationResponse.model_validate(notification)


@router.post(
    "/api/notifications/read-all",
    response_model=MarkAllReadResponse,
    summary="Mark all notifications as read",
)
def mark_all_notifications_as_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Marks all unread notifications for the authenticated user as read."""
    marked = NotificationService.mark_all_notifications_as_read(
        db=db,
        user_id=current_user.id,
    )
    return MarkAllReadResponse(
        message="All notifications marked as read",
        marked_count=marked,
    )


@router.delete(
    "/api/notifications/{notification_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete notification",
)
def delete_notification(
    notification_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Deletes a notification belonging to the authenticated user. Prevents IDOR."""
    NotificationService.delete_notification(
        db=db,
        notification_id=notification_id,
        user_id=current_user.id,
    )
    return {"message": "Notification deleted successfully"}
