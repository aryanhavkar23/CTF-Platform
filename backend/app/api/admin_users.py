from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.deps import require_role
from app.models.user import User, UserRole
from app.schemas.admin_user import (
    AdminUserResponse,
    AdminUserListResponse,
    AdminUserDetailResponse,
    AdminUserUpdate,
)
from app.services.user_management_service import UserManagementService

router = APIRouter(prefix="/api/admin/users", tags=["Admin Users"])


@router.get("", response_model=AdminUserListResponse, status_code=status.HTTP_200_OK)
def list_users(
    search: Optional[str] = Query(None, description="Search across username, email, name, college"),
    role: Optional[UserRole] = Query(None, description="Filter by user role"),
    is_banned: Optional[bool] = Query(None, description="Filter by banned status"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    is_muted: Optional[bool] = Query(None, description="Filter by muted status"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.MODERATOR, UserRole.ADMIN)),
):
    """Lists users with search, filtering, and computed scoring stats. Restricted to moderators and admins."""
    items, total, total_pages = UserManagementService.list_users(
        db=db,
        search=search,
        role=role,
        is_banned=is_banned,
        is_active=is_active,
        is_muted=is_muted,
        page=page,
        limit=limit,
    )
    return AdminUserListResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages,
    )


@router.get("/{user_id}", response_model=AdminUserDetailResponse, status_code=status.HTTP_200_OK)
def get_user_details(
    user_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.MODERATOR, UserRole.ADMIN)),
):
    """Retrieves full user audit info with recent submissions. Restricted to moderators and admins."""
    return UserManagementService.get_user_details(db, user_id)


@router.patch("/{user_id}", response_model=AdminUserResponse, status_code=status.HTTP_200_OK)
def update_user(
    user_id: UUID,
    data: AdminUserUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_role(UserRole.ADMIN)),
):
    """Updates user role, ban status, or mute status. Restricted to administrators."""
    return UserManagementService.update_user(
        db=db,
        user_id=user_id,
        current_admin=current_admin,
        data=data,
    )
