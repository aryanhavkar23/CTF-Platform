from typing import List, Optional, Any, Dict
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from app.config import settings
from app.models.team import Team, TeamMember
from app.models.user import User, UserRole
from app.models.base import utc_now
from app.models.event import Event, EventStatus
from app.models.event_registration import EventRegistration, RegistrationType
from app.models.solve import Solve
from app.models.challenge import Challenge
from app.schemas.team import (
    TeamCreate,
    TeamUpdate,
    TeamResponse,
    TeamDetailResponse,
    TeamMemberResponse,
    UserTeamDetailResponse,
    TeamHistoryResponse,
    TeamEventHistoryItem,
    TeamEventSolveItem,
)
from app.models.activity import ActivityType
from app.services.activity_service import ActivityService
from app.services.scoring_service import ScoringService


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
            .filter(TeamMember.team_id == team.id, TeamMember.is_active == True, TeamMember.role != "requested")
            .scalar()
            or 0
        )
        total_pts = (
            db.query(func.coalesce(func.sum(Solve.points_awarded), 0))
            .filter(Solve.team_id == team.id)
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
            invite_code=getattr(team, "invite_code", None),
            join_code=getattr(team, "invite_code", None),
            total_points=int(total_pts),
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
    def get_my_team(cls, db: Session, current_user: User) -> Optional[TeamDetailResponse]:
        membership = (
            db.query(TeamMember)
            .join(Team, Team.id == TeamMember.team_id)
            .filter(
                TeamMember.user_id == current_user.id,
                TeamMember.is_active == True,
                Team.is_active == True,
                TeamMember.role != "requested",
            )
            .first()
        )
        if not membership or not membership.team:
            return None
        return cls._to_team_detail_response(db, membership.team)

    @classmethod
    def get_my_teams(cls, db: Session, current_user: User) -> List[UserTeamDetailResponse]:
        """Retrieve all active squads where current operative is owner, captain, or active roster member."""
        # Find all active team memberships
        memberships = (
            db.query(TeamMember)
            .join(Team, Team.id == TeamMember.team_id)
            .filter(
                TeamMember.user_id == current_user.id,
                TeamMember.is_active == True,
                Team.is_active == True,
                TeamMember.role != "requested",
            )
            .all()
        )

        # Also find any teams owned or captained by the user
        owned_teams = (
            db.query(Team)
            .filter(
                or_(Team.owner_id == current_user.id, Team.captain_id == current_user.id),
                Team.is_active == True,
            )
            .all()
        )

        seen_team_ids = set()
        user_teams: List[UserTeamDetailResponse] = []

        # 1. First add owned / captained teams
        for team in owned_teams:
            if team.id in seen_team_ids:
                continue
            seen_team_ids.add(team.id)
            base = cls._to_team_detail_response(db, team)
            events_count = (
                db.query(func.count(func.distinct(EventRegistration.event_id)))
                .filter(EventRegistration.team_id == team.id, EventRegistration.is_active == True)
                .scalar() or 0
            )
            role = "owner" if team.owner_id == current_user.id else "captain"
            user_teams.append(UserTeamDetailResponse(
                **base.model_dump(),
                my_role=role,
                events_participated_count=int(events_count),
            ))

        # 2. Then add member teams
        for m in memberships:
            team = m.team
            if not team or team.id in seen_team_ids:
                continue
            seen_team_ids.add(team.id)
            base = cls._to_team_detail_response(db, team)
            events_count = (
                db.query(func.count(func.distinct(EventRegistration.event_id)))
                .filter(EventRegistration.team_id == team.id, EventRegistration.is_active == True)
                .scalar() or 0
            )
            role = "owner" if team.owner_id == current_user.id else ("captain" if team.captain_id == current_user.id else (m.role or "member"))
            user_teams.append(UserTeamDetailResponse(
                **base.model_dump(),
                my_role=role,
                events_participated_count=int(events_count),
            ))

        return user_teams

    @classmethod
    def get_team_history(cls, db: Session, team_id: UUID) -> TeamHistoryResponse:
        """Retrieve complete event engagement record, scores, and rankings for a team."""
        team = db.query(Team).filter(Team.id == team_id).first()
        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Team with ID '{team_id}' not found."
            )

        # Active roster members
        active_memberships = (
            db.query(TeamMember)
            .filter(TeamMember.team_id == team.id, TeamMember.is_active == True, TeamMember.role != "requested")
            .order_by(TeamMember.joined_at.asc())
            .all()
        )
        members = [cls._to_member_response(m) for m in active_memberships]

        # Registrations and solves
        registrations = (
            db.query(EventRegistration)
            .filter(EventRegistration.team_id == team.id, EventRegistration.is_active == True)
            .all()
        )
        team_solves = (
            db.query(Solve)
            .filter(Solve.team_id == team.id)
            .order_by(Solve.created_at.desc())
            .all()
        )

        event_ids = set()
        reg_by_event: Dict[UUID, EventRegistration] = {}
        for r in registrations:
            if r.event_id:
                event_ids.add(r.event_id)
                reg_by_event[r.event_id] = r
        for s in team_solves:
            if s.event_id:
                event_ids.add(s.event_id)

        events_list: List[TeamEventHistoryItem] = []

        for eid in event_ids:
            event = db.query(Event).filter(Event.id == eid).first()
            if not event:
                continue

            reg = reg_by_event.get(eid)
            e_solves = [s for s in team_solves if s.event_id == eid]
            e_score = sum(s.points_awarded for s in e_solves)

            solve_items: List[TeamEventSolveItem] = []
            for s in e_solves:
                ch = db.query(Challenge).filter(Challenge.id == s.challenge_id).first()
                u = db.query(User).filter(User.id == s.user_id).first()
                cat_name = ch.category.name if (ch and getattr(ch, "category", None) and hasattr(ch.category, "name")) else "General"
                solve_items.append(TeamEventSolveItem(
                    challenge_id=s.challenge_id,
                    challenge_title=ch.title if ch else "Classified Challenge",
                    category=cat_name,
                    points_awarded=s.points_awarded,
                    solver_username=u.username if u else "Operative",
                    solved_at=s.created_at,
                ))

            # Determine rank in this event among teams
            event_team_regs = (
                db.query(EventRegistration)
                .filter(
                    EventRegistration.event_id == eid,
                    EventRegistration.registration_type == RegistrationType.TEAM,
                    EventRegistration.is_active == True
                )
                .all()
            )
            event_team_solves = db.query(Solve).filter(Solve.event_id == eid, Solve.team_id.isnot(None)).all()
            participating_team_ids = set([r.team_id for r in event_team_regs if r.team_id] + [s.team_id for s in event_team_solves if s.team_id])
            if team.id not in participating_team_ids:
                participating_team_ids.add(team.id)

            team_scoreboard = []
            for tid in participating_team_ids:
                t_solves = [s for s in event_team_solves if s.team_id == tid]
                pts = sum(s.points_awarded for s in t_solves)
                last_time = max([s.created_at for s in t_solves]) if t_solves else None
                team_scoreboard.append({
                    "team_id": tid,
                    "points": pts,
                    "last_time": last_time or event.end_at,
                })

            team_scoreboard.sort(key=lambda x: (-x["points"], x["last_time"]))

            rank = None
            for idx, entry in enumerate(team_scoreboard):
                if entry["team_id"] == team.id:
                    rank = idx + 1
                    break

            status_val = event.status.value if hasattr(event.status, "value") else str(event.status)

            events_list.append(TeamEventHistoryItem(
                event_id=event.id,
                event_name=event.name,
                event_slug=event.slug,
                status=status_val,
                start_at=event.start_at,
                end_at=event.end_at,
                score=e_score,
                solves_count=len(e_solves),
                rank=rank,
                total_teams=len(team_scoreboard),
                registered_at=reg.registered_at if reg else None,
                solves=solve_items,
            ))

        # Sort events by start date descending
        events_list.sort(key=lambda e: e.start_at, reverse=True)

        total_pts = (
            db.query(func.coalesce(func.sum(Solve.points_awarded), 0))
            .filter(Solve.team_id == team.id)
            .scalar()
            or 0
        )

        return TeamHistoryResponse(
            team_id=team.id,
            team_name=team.name,
            college=team.college,
            description=team.description,
            owner_username=team.owner.username if team.owner else None,
            member_count=len(members),
            members=members,
            events_participated_count=len(events_list),
            total_score=int(total_pts),
            total_solves=len(team_solves),
            events=events_list,
        )

    @classmethod
    def get_my_invitations(cls, db: Session, current_user: User) -> List[Dict[str, Any]]:
        """Retrieve pending squad invitations sent to the current user."""
        memberships = (
            db.query(TeamMember)
            .join(Team, Team.id == TeamMember.team_id)
            .filter(
                TeamMember.user_id == current_user.id,
                TeamMember.is_active == True,
                TeamMember.role == "requested",
                Team.is_active == True,
            )
            .all()
        )
        results = []
        for m in memberships:
            t = m.team
            results.append({
                "membership_id": str(m.id),
                "team_id": str(t.id),
                "team_name": t.name,
                "college": t.college,
                "owner_id": str(t.owner_id),
                "owner_username": t.owner.username if t.owner else None,
                "invited_at": m.joined_at,
            })
        return results

    @classmethod
    def search_operatives(
        cls,
        db: Session,
        current_user: User,
        query: Optional[str] = None,
        college: Optional[str] = None,
        strict_college: bool = False,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        q = db.query(User).filter(User.is_active == True)
        pref_college = (college or current_user.college or "").strip()

        if strict_college and pref_college:
            q = q.filter(
                or_(
                    func.lower(User.college) == func.lower(pref_college),
                    User.college.ilike(f"%{pref_college}%")
                )
            )

        if query and query.strip():
            term = f"%{query.strip()}%"
            q = q.filter(
                or_(
                    User.username.ilike(term),
                    User.name.ilike(term),
                    User.college.ilike(term),
                    User.email.ilike(term),
                )
            )
        q = q.filter(User.id != current_user.id)
        users = q.all()

        # Prioritize operatives from the same college on top ("upside")
        def sort_key(u: User):
            is_same = False
            if pref_college and u.college:
                p_col = pref_college.lower()
                u_col = u.college.lower()
                is_same = (p_col in u_col) or (u_col in p_col)
            # 0 for same college (top), 1 for other colleges
            return (0 if is_same else 1, -(ScoringService.get_user_score(db, u.id) or 0), (u.username or "").lower())

        users.sort(key=sort_key)
        users = users[:limit]

        return [
            {
                "id": str(u.id),
                "username": u.username,
                "name": u.name or u.username,
                "college": u.college or "Registered Operative",
                "is_same_college": bool(
                    pref_college and u.college and (
                        pref_college.lower() in u.college.lower() or u.college.lower() in pref_college.lower()
                    )
                ),
                "role": u.role.value if hasattr(u.role, "value") else str(u.role),
                "points": ScoringService.get_user_score(db, u.id),
                "avatar_url": u.avatar_url,
            }
            for u in users
        ]

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
        role: str = "member",
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
            if role == "requested" and existing.role == "requested":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Squad request already sent to this operative (Pending Acceptance)."
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already an active member of this team."
            )

        # Check maximum team size (confirmed active members)
        active_count = (
            db.query(func.count(TeamMember.id))
            .filter(TeamMember.team_id == team.id, TeamMember.is_active == True, TeamMember.role != "requested")
            .scalar()
            or 0
        )
        if active_count >= settings.MAX_TEAM_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Squad has reached the maximum size of {settings.MAX_TEAM_SIZE} members."
            )

        if existing:
            existing.is_active = True
            existing.role = role
            existing.joined_at = utc_now()
            db.commit()
            db.refresh(existing)

            # In-app notification for requested member
            if role == "requested" and target_user.id != current_user.id:
                try:
                    from app.services.notification_service import NotificationService
                    NotificationService.notify_team_invite_request(
                        db=db,
                        team_id=team.id,
                        team_name=team.name,
                        target_user_id=target_user.id,
                        invited_by_username=current_user.username,
                        college=team.college,
                    )
                except Exception:
                    pass

            return cls._to_member_response(existing)
        else:
            new_member = TeamMember(
                team_id=team.id,
                user_id=target_user.id,
                role=role,
                is_active=True,
            )
            db.add(new_member)
            db.commit()
            db.refresh(new_member)

            # In-app notification for requested member
            if role == "requested" and target_user.id != current_user.id:
                try:
                    from app.services.notification_service import NotificationService
                    NotificationService.notify_team_invite_request(
                        db=db,
                        team_id=team.id,
                        team_name=team.name,
                        target_user_id=target_user.id,
                        invited_by_username=current_user.username,
                        college=team.college,
                    )
                except Exception:
                    pass

            return cls._to_member_response(new_member)

    @classmethod
    def accept_team_request(
        cls,
        db: Session,
        current_user: User,
        team_id: UUID,
        target_user_id: Optional[UUID] = None,
    ) -> TeamMemberResponse:
        """Accept a squad invitation/request so operative becomes full active member."""
        team = db.query(Team).filter(Team.id == team_id).first()
        if not team:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found.")

        user_id_to_accept = target_user_id if (target_user_id and (team.owner_id == current_user.id or current_user.role == UserRole.ADMIN)) else current_user.id

        membership = (
            db.query(TeamMember)
            .filter(TeamMember.team_id == team.id, TeamMember.user_id == user_id_to_accept, TeamMember.is_active == True)
            .first()
        )
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pending squad request not found."
            )

        active_count = (
            db.query(func.count(TeamMember.id))
            .filter(TeamMember.team_id == team.id, TeamMember.is_active == True, TeamMember.role != "requested")
            .scalar()
            or 0
        )
        if active_count >= settings.MAX_TEAM_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Squad has already reached max capacity of {settings.MAX_TEAM_SIZE} members."
            )

        membership.role = "member"
        membership.joined_at = utc_now()
        db.commit()
        db.refresh(membership)

        ActivityService.record_activity(
            db=db,
            user_id=user_id_to_accept,
            activity_type=ActivityType.TEAM_JOINED,
            reference_id=team.id,
            metadata={"team_id": str(team.id), "team_name": team.name, "accepted": True}
        )

        # Notify team owner that the invited user accepted
        if team.owner_id != current_user.id:
            try:
                from app.services.notification_service import NotificationService
                NotificationService.notify_team_invite_accepted(
                    db=db,
                    team_id=team.id,
                    team_name=team.name,
                    owner_id=team.owner_id,
                    accepted_by_username=current_user.username,
                )
            except Exception:
                pass

        return cls._to_member_response(membership)

    @classmethod
    def decline_team_request(
        cls,
        db: Session,
        current_user: User,
        team_id: UUID,
    ) -> dict:
        """Invited user declines a pending squad request."""
        team = db.query(Team).filter(Team.id == team_id).first()
        if not team:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found.")

        membership = (
            db.query(TeamMember)
            .filter(TeamMember.team_id == team.id, TeamMember.user_id == current_user.id, TeamMember.is_active == True)
            .first()
        )
        if not membership:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pending squad request not found.")

        db.delete(membership)
        db.commit()

        # Notify owner that the invite was declined
        try:
            from app.services.notification_service import NotificationService
            NotificationService.notify_team_invite_declined(
                db=db,
                team_id=team.id,
                team_name=team.name,
                owner_id=team.owner_id,
                declined_by_username=current_user.username,
            )
        except Exception:
            pass

        return {"message": f"Declined invitation to join {team.name}."}

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
                detail="Team owner cannot leave without transferring ownership first. Disband or delete the squad to delete it directly."
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
        team_memberships = db.query(TeamMember).filter(TeamMember.team_id == team.id).all()
        for m in team_memberships:
            m.is_active = False
        db.commit()

        ActivityService.record_activity(
            db=db,
            user_id=current_user.id,
            activity_type=ActivityType.TEAM_LEFT,
            reference_id=team.id,
            metadata={"team_id": str(team.id), "team_name": team.name, "action": "deleted"}
        )

        return {"message": f"Squad '{team.name}' deleted successfully."}
