from typing import Optional, List, Tuple
from uuid import UUID
import math
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, desc

from app.models.user import User, UserRole
from app.models.submission import Submission
from app.models.challenge import Challenge
from app.schemas.admin_user import (
    AdminUserResponse,
    AdminUserUpdate,
    AdminUserSubmissionItem,
    AdminUserDetailResponse,
)
from app.services.scoring_service import ScoringService


class UserManagementService:
    """Administrative service for managing users, roles, and moderation actions."""

    @staticmethod
    def list_users(
        db: Session,
        search: Optional[str] = None,
        role: Optional[UserRole] = None,
        is_banned: Optional[bool] = None,
        is_active: Optional[bool] = None,
        is_muted: Optional[bool] = None,
        page: int = 1,
        limit: int = 20,
    ) -> Tuple[List[AdminUserResponse], int, int]:
        """Returns paginated user list with filters, search, and calculated score/solve metrics."""
        query = db.query(User)

        if search:
            pattern = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    User.username.ilike(pattern),
                    User.email.ilike(pattern),
                    User.name.ilike(pattern),
                    User.college.ilike(pattern),
                )
            )

        if role is not None:
            query = query.filter(User.role == role)
        if is_banned is not None:
            query = query.filter(User.is_banned == is_banned)
        if is_active is not None:
            query = query.filter(User.is_active == is_active)
        if is_muted is not None:
            query = query.filter(User.is_muted == is_muted)

        total = query.count()
        total_pages = max(1, math.ceil(total / limit)) if total > 0 else 1
        offset = (page - 1) * limit

        users = query.order_by(desc(User.created_at)).offset(offset).limit(limit).all()

        user_responses = []
        for u in users:
            points = ScoringService.get_user_score(db, u.id)
            solves_count = ScoringService.get_user_solve_count(db, u.id)
            sub_count = db.query(func.count(Submission.id)).filter(Submission.user_id == u.id).scalar() or 0

            resp = AdminUserResponse(
                id=u.id,
                username=u.username,
                email=u.email,
                role=u.role,
                name=u.name,
                bio=u.bio,
                college=u.college,
                avatar_url=u.avatar_url,
                is_active=u.is_active,
                is_verified=u.is_verified,
                is_banned=u.is_banned,
                is_muted=u.is_muted,
                points=points,
                solves_count=solves_count,
                submissions_count=sub_count,
                created_at=u.created_at,
                updated_at=u.updated_at,
            )
            user_responses.append(resp)

        return user_responses, total, total_pages

    @staticmethod
    def get_user_details(db: Session, user_id: UUID) -> AdminUserDetailResponse:
        """Retrieves comprehensive user audit info including recent submissions."""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        points = ScoringService.get_user_score(db, user.id)
        solves_count = ScoringService.get_user_solve_count(db, user.id)
        sub_count = db.query(func.count(Submission.id)).filter(Submission.user_id == user.id).scalar() or 0

        # Query recent submissions
        recent_subs_query = (
            db.query(Submission, Challenge.title)
            .join(Challenge, Submission.challenge_id == Challenge.id)
            .filter(Submission.user_id == user.id)
            .order_by(desc(Submission.created_at))
            .limit(25)
            .all()
        )

        sub_items = [
            AdminUserSubmissionItem(
                id=sub.id,
                challenge_id=sub.challenge_id,
                challenge_title=title,
                is_correct=sub.is_correct,
                points_awarded=sub.points_awarded or 0,
                created_at=sub.created_at,
            )
            for sub, title in recent_subs_query
        ]

        return AdminUserDetailResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            role=user.role,
            name=user.name,
            bio=user.bio,
            college=user.college,
            avatar_url=user.avatar_url,
            is_active=user.is_active,
            is_verified=user.is_verified,
            is_banned=user.is_banned,
            is_muted=user.is_muted,
            points=points,
            solves_count=solves_count,
            submissions_count=sub_count,
            created_at=user.created_at,
            updated_at=user.updated_at,
            recent_submissions=sub_items,
        )

    @staticmethod
    def update_user(
        db: Session,
        user_id: UUID,
        current_admin: User,
        data: AdminUserUpdate,
    ) -> AdminUserResponse:
        """Updates user moderation status and role with self-demotion/self-ban protection."""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        # Protection: Prevent admin self-demotion or self-ban
        if user.id == current_admin.id:
            if data.role is not None and data.role != UserRole.ADMIN:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Administrators cannot demote themselves.",
                )
            if data.is_banned is True:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Administrators cannot ban themselves.",
                )
            if data.is_active is False:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Administrators cannot deactivate their own account.",
                )

        if data.role is not None:
            user.role = data.role
        if data.is_active is not None:
            user.is_active = data.is_active
        if data.is_banned is not None:
            user.is_banned = data.is_banned
            if data.is_banned:
                # Banning also deactivates active flag
                user.is_active = False
        if data.is_muted is not None:
            user.is_muted = data.is_muted

        db.commit()
        db.refresh(user)

        points = ScoringService.get_user_score(db, user.id)
        solves_count = ScoringService.get_user_solve_count(db, user.id)
        sub_count = db.query(func.count(Submission.id)).filter(Submission.user_id == user.id).scalar() or 0

        return AdminUserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            role=user.role,
            name=user.name,
            bio=user.bio,
            college=user.college,
            avatar_url=user.avatar_url,
            is_active=user.is_active,
            is_verified=user.is_verified,
            is_banned=user.is_banned,
            is_muted=user.is_muted,
            points=points,
            solves_count=solves_count,
            submissions_count=sub_count,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
