from typing import List, Optional
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.config import settings
from app.models.team import Team, TeamMember
from app.models.user import User, UserRole
from app.models.base import utc_now
from app.schemas.team import (
    TeamCreate,
    TeamUpdate,
    TeamResponse,
    TeamDetailResponse,
    TeamMemberResponse,
)
from app.models.activity import ActivityType
from app.services.activity_service import ActivityService


class TeamService:
    @staticmethod
    def _to_member_response(member: TeamMember) -> TeamMemberResponse:
        return TeamMemberResponse(
            id=member.id,
            team_id=member.team_id,
            user_id=member.user_id,
            username=member.user.username if member.user else "Unknown",
            college=member.user.college if member.user else None,
            role=member.role,
            is_active=member.is_active,
            joined_at=member.joined_at,
        )

    @staticmethod
    def _to_team_response(db: Session, team: Team) -> TeamResponse:
        active_count = (
            db.query(func.count(TeamMember.id))
            .filter(TeamMember.team_id == team.id, TeamMember.is_active == True)
            .scalar()
            or 0
        )
        return TeamResponse(
            id=team.id,
            name=team.name,
            description=team.description,
            college=team.college,
            owner_id=team.owner_id,
            owner_username=team.owner.username if team.owner else None,
            member_count=active_count,
            max_team_size=settings.MAX_TEAM_SIZE,
            is_active=team.is_active,
            created_at=team.created_at,
            updated_at=team.updated_at,
        )

    @classmethod
    def _to_team_detail_response(cls, db: Session, team: Team) -> TeamDetailResponse:
        base = cls._to_team_response(db, team)
        active_memberships = (
            db.query(TeamMember)
            .filter(TeamMember.team_id == team.id, TeamMember.is_active == True)
            .order_by(TeamMember.joined_at.asc())
            .all()
        )
        members = [cls._to_member_response(m) for m in active_memberships]
        return TeamDetailResponse(
            **base.model_dump(),
            members=members,
        )

    @classmethod
    def create_team(cls, db: Session, current_user: User, data: TeamCreate) -> TeamResponse:
        """Create a new team and automatically make the authenticated user the owner."""
        clean_name = data.name.strip()
        if not clean_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Team name cannot be blank."
            )

        # Name uniqueness check
        existing = db.query(Team).filter(func.lower(Team.name) == func.lower(clean_name)).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Team name '{clean_name}' is already taken."
            )

        college = data.college.strip() if data.college else current_user.college
        team = Team(
            name=clean_name,
            description=data.description.strip() if data.description else None,
            college=college,
            owner_id=current_user.id,
            captain_id=current_user.id,
            is_active=True,
        )
        db.add(team)
        db.flush()

        # Automatically make creator the owner member
        owner_member = TeamMember(
            team_id=team.id,
            user_id=current_user.id,
            role="owner",
            is_active=True,
        )
        db.add(owner_member)
        db.commit()
        db.refresh(team)

        ActivityService.record_activity(
            db=db,
            user_id=current_user.id,
            activity_type=ActivityType.TEAM_CREATED,
            reference_id=team.id,
            metadata={"team_id": str(team.id), "team_name": team.name}
        )

        return cls._to_team_response(db, team)

    @classmethod
    def get_teams(
        cls,
        db: Session,
        college: Optional[str] = None,
        search: Optional[str] = None,
        is_active: Optional[bool] = True,
        skip: int = 0,
        limit: int = 50,
    ) -> List[TeamResponse]:
        query = db.query(Team)
        if is_active is not None:
            query = query.filter(Team.is_active == is_active)
        if college:
            query = query.filter(func.lower(Team.college) == func.lower(college.strip()))
        if search:
            pattern = f"%{search.strip()}%"
            query = query.filter(Team.name.ilike(pattern))

        teams = query.order_by(Team.created_at.desc()).offset(skip).limit(limit).all()
        return [cls._to_team_response(db, t) for t in teams]

    @classmethod
    def get_team_by_id(cls, db: Session, team_id: UUID) -> TeamDetailResponse:
        team = db.query(Team).filter(Team.id == team_id).first()
        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Team not found."
            )
        return cls._to_team_detail_response(db, team)

    @classmethod
    def get_team_members(cls, db: Session, team_id: UUID) -> List[TeamMemberResponse]:
        team = db.query(Team).filter(Team.id == team_id).first()
        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Team not found."
            )
        memberships = (
            db.query(TeamMember)
            .filter(TeamMember.team_id == team.id, TeamMember.is_active == True)
            .order_by(TeamMember.joined_at.asc())
            .all()
        )
        return [cls._to_member_response(m) for m in memberships]

    @classmethod
    def add_team_member(
        cls,
        db: Session,
        current_user: User,
        team_id: UUID,
        target_user_id: Optional[UUID] = None,
        target_username: Optional[str] = None,
    ) -> TeamMemberResponse:
        """Add a member to the team with row-level locking to prevent exceeding MAX_TEAM_SIZE."""
        # Lock team row to prevent concurrent race condition additions
        # with_for_update() handles PostgreSQL; falls back gracefully in SQLite
        query = db.query(Team).filter(Team.id == team_id)
        if db.bind and db.bind.dialect.name != "sqlite":
            query = query.with_for_update()
        team = query.first()

        if not team:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found.")

        if not team.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot add members to an inactive team."
            )

        # Authorization: Only owner or admin can add members
        if team.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the team owner or an administrator can add members."
            )

        # Resolve target user
        target_user = None
        if target_user_id:
            target_user = db.query(User).filter(User.id == target_user_id).first()
        elif target_username:
            target_user = db.query(User).filter(func.lower(User.username) == func.lower(target_username.strip())).first()

        if not target_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target user not found.")

        if not target_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot add an inactive user to a team."
            )

        # Check if already an active member of this team
        existing = (
            db.query(TeamMember)
            .filter(TeamMember.team_id == team.id, TeamMember.user_id == target_user.id)
            .first()
        )
        if existing and existing.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already an active member of this team."
            )

        # Check maximum team size
        active_count = (
            db.query(func.count(TeamMember.id))
            .filter(TeamMember.team_id == team.id, TeamMember.is_active == True)
            .scalar()
            or 0
        )
        if active_count >= settings.MAX_TEAM_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Team has reached the maximum size of {settings.MAX_TEAM_SIZE} members."
            )

        if existing:
            existing.is_active = True
            existing.role = "member"
            existing.joined_at = utc_now()
            db.commit()
            db.refresh(existing)

            ActivityService.record_activity(
                db=db,
                user_id=target_user.id,
                activity_type=ActivityType.TEAM_JOINED,
                reference_id=team.id,
                metadata={"team_id": str(team.id), "team_name": team.name}
            )

            # In-app notification for added member
            if target_user.id != current_user.id:
                try:
                    from app.services.notification_service import NotificationService
                    NotificationService.notify_team_member_added(
                        db=db,
                        team_id=team.id,
                        team_name=team.name,
                        target_user_id=target_user.id,
                        added_by_username=current_user.username,
                    )
                except Exception:
                    pass

            return cls._to_member_response(existing)
        else:
            new_member = TeamMember(
                team_id=team.id,
                user_id=target_user.id,
                role="member",
                is_active=True,
            )
            db.add(new_member)
            db.commit()
            db.refresh(new_member)

            ActivityService.record_activity(
                db=db,
                user_id=target_user.id,
                activity_type=ActivityType.TEAM_JOINED,
                reference_id=team.id,
                metadata={"team_id": str(team.id), "team_name": team.name}
            )

            # In-app notification for added member
            if target_user.id != current_user.id:
                try:
                    from app.services.notification_service import NotificationService
                    NotificationService.notify_team_member_added(
                        db=db,
                        team_id=team.id,
                        team_name=team.name,
                        target_user_id=target_user.id,
                        added_by_username=current_user.username,
                    )
                except Exception:
                    pass

            return cls._to_member_response(new_member)

    @classmethod
    def remove_team_member(
        cls,
        db: Session,
        current_user: User,
        team_id: UUID,
        target_user_id: UUID,
    ) -> dict:
        """Owner or admin removes a member from the team."""
        team = db.query(Team).filter(Team.id == team_id).first()
        if not team:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found.")

        # Authorization
        if team.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the team owner or an administrator can remove team members."
            )

        # Owner cannot remove themselves (must transfer ownership first or leave)
        if target_user_id == current_user.id and current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Team owner cannot remove themselves. Transfer ownership before leaving."
            )

        if target_user_id == team.owner_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove the team owner."
            )

        membership = (
            db.query(TeamMember)
            .filter(TeamMember.team_id == team.id, TeamMember.user_id == target_user_id, TeamMember.is_active == True)
            .first()
        )
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User is not an active member of this team."
            )

        db.delete(membership)
        db.commit()

        ActivityService.record_activity(
            db=db,
            user_id=target_user_id,
            activity_type=ActivityType.TEAM_LEFT,
            reference_id=team.id,
            metadata={"team_id": str(team.id), "team_name": team.name}
        )

        # In-app notification for removed member
        if target_user_id != current_user.id:
            try:
                from app.services.notification_service import NotificationService
                NotificationService.notify_team_member_removed(
                    db=db,
                    team_id=team.id,
                    team_name=team.name,
                    target_user_id=target_user_id,
                )
            except Exception:
                pass

        return {"message": "Member successfully removed from the team."}

    @classmethod
    def leave_team(cls, db: Session, current_user: User, team_id: UUID) -> dict:
        """A normal member leaves the team. Owner must transfer ownership first."""
        team = db.query(Team).filter(Team.id == team_id).first()
        if not team:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found.")

        if current_user.id == team.owner_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Team owner cannot leave without transferring ownership first."
            )

        membership = (
            db.query(TeamMember)
            .filter(TeamMember.team_id == team.id, TeamMember.user_id == current_user.id, TeamMember.is_active == True)
            .first()
        )
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You are not an active member of this team."
            )

        db.delete(membership)
        db.commit()

        ActivityService.record_activity(
            db=db,
            user_id=current_user.id,
            activity_type=ActivityType.TEAM_LEFT,
            reference_id=team.id,
            metadata={"team_id": str(team.id), "team_name": team.name}
        )

        return {"message": "You have left the team."}

    @classmethod
    def transfer_ownership(
        cls,
        db: Session,
        current_user: User,
        team_id: UUID,
        new_owner_id: UUID,
    ) -> TeamDetailResponse:
        """Transfer team ownership atomically to another active team member."""
        team = db.query(Team).filter(Team.id == team_id).first()
        if not team:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found.")

        # Authorization: strictly the current owner can transfer ownership
        if current_user.id != team.owner_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the current team owner can transfer ownership."
            )

        if new_owner_id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You are already the owner of this team."
            )

        # Verify new owner exists and is an active member
        new_owner_member = (
            db.query(TeamMember)
            .filter(TeamMember.team_id == team.id, TeamMember.user_id == new_owner_id, TeamMember.is_active == True)
            .first()
        )
        if not new_owner_member:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New owner must be an active member of the team."
            )

        # Atomic role swapping
        old_owner_member = (
            db.query(TeamMember)
            .filter(TeamMember.team_id == team.id, TeamMember.user_id == current_user.id, TeamMember.is_active == True)
            .first()
        )
        if old_owner_member:
            old_owner_member.role = "member"

        new_owner_member.role = "owner"
        team.owner_id = new_owner_id
        team.captain_id = new_owner_id
        db.commit()
        db.refresh(team)

        # In-app notification for new owner
        try:
            from app.services.notification_service import NotificationService
            NotificationService.notify_team_owner_transferred(
                db=db,
                team_id=team.id,
                team_name=team.name,
                new_owner_id=new_owner_id,
                old_owner_username=current_user.username,
            )
        except Exception:
            pass

        return cls._to_team_detail_response(db, team)

    @classmethod
    def update_team(
        cls,
        db: Session,
        current_user: User,
        team_id: UUID,
        data: TeamUpdate,
    ) -> TeamResponse:
        team = db.query(Team).filter(Team.id == team_id).first()
        if not team:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found.")

        if team.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the team owner or an administrator can update team details."
            )

        if data.name is not None:
            clean_name = data.name.strip()
            if not clean_name:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Team name cannot be blank."
                )
            if clean_name.lower() != team.name.lower():
                existing = db.query(Team).filter(func.lower(Team.name) == func.lower(clean_name)).first()
                if existing:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Team name '{clean_name}' is already taken."
                    )
            team.name = clean_name

        if data.description is not None:
            team.description = data.description.strip() if data.description else None

        if data.college is not None:
            team.college = data.college.strip() if data.college else None

        if data.is_active is not None:
            team.is_active = data.is_active

        db.commit()
        db.refresh(team)
        return cls._to_team_response(db, team)

    @classmethod
    def deactivate_team(cls, db: Session, current_user: User, team_id: UUID) -> dict:
        """Soft-deactivate a team."""
        team = db.query(Team).filter(Team.id == team_id).first()
        if not team:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found.")

        if team.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the team owner or an administrator can deactivate the team."
            )

        team.is_active = False
        db.commit()
        return {"message": "Team deactivated successfully."}
