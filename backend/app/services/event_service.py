import re
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, and_, or_, desc, asc
from sqlalchemy.orm import Session

from app.models.base import utc_now
from app.models.event import Event, EventStatus, event_challenges
from app.models.event_registration import EventRegistration, RegistrationType
from app.models.challenge import Challenge
from app.models.solve import Solve
from app.models.user import User, UserRole
from app.models.team import Team, TeamMember
from app.models.activity import ActivityType
from app.services.activity_service import ActivityService
from app.schemas.event import (
    EventCreate,
    EventUpdate,
    EventChallengeAdd,
    EventChallengeResponse,
    EventRegistrationRequest,
    EventRegistrationResponse,
    EventParticipantResponse,
    EventResponse,
    EventLeaderboardEntry,
    EventLeaderboardResponse,
)


class EventService:
    """Manages CTF events, challenge associations, registration windows, and isolated leaderboards."""

    @staticmethod
    def _normalize_tz(dt: Optional[datetime]) -> Optional[datetime]:
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    @classmethod
    def compute_status(cls, event: Event) -> EventStatus:
        """Determines event status based on UTC server clock unless explicitly DRAFT or CANCELLED."""
        if event.status in (EventStatus.DRAFT, EventStatus.CANCELLED):
            return event.status

        now = utc_now()
        start_at = cls._normalize_tz(event.start_at)
        end_at = cls._normalize_tz(event.end_at)

        if start_at and now < start_at:
            return EventStatus.UPCOMING
        elif start_at and end_at and start_at <= now < end_at:
            return EventStatus.LIVE
        elif end_at and now >= end_at:
            return EventStatus.ENDED
        return EventStatus.UPCOMING

    @classmethod
    def is_registration_open(cls, event: Event) -> bool:
        """Checks if current UTC time falls within the event's registration window."""
        if event.status == EventStatus.CANCELLED:
            return False

        now = utc_now()
        reg_start = cls._normalize_tz(event.registration_start_at)
        reg_end = cls._normalize_tz(event.registration_end_at)
        start_at = cls._normalize_tz(event.start_at)

        if reg_start and reg_end:
            return reg_start <= now < reg_end
        elif start_at:
            return now < start_at
        return True

    @classmethod
    def to_event_response(cls, event: Event) -> EventResponse:
        current_status = cls.compute_status(event)
        reg_open = cls.is_registration_open(event)
        return EventResponse(
            id=event.id,
            name=event.name,
            description=event.description,
            slug=event.slug,
            start_at=event.start_at,
            end_at=event.end_at,
            registration_start_at=event.registration_start_at,
            registration_end_at=event.registration_end_at,
            status=event.status.value if hasattr(event.status, "value") else str(event.status),
            computed_status=current_status.value,
            is_registration_open=reg_open,
            is_active=event.is_active,
            is_scoreboard_frozen=event.is_scoreboard_frozen,
            scoreboard_frozen_at=event.scoreboard_frozen_at,
            challenge_count=len(event.challenges) if event.challenges else 0,
            participant_count=len([r for r in event.registrations if r.is_active]) if event.registrations else 0,
            created_at=event.created_at or utc_now(),
            updated_at=event.updated_at or event.created_at or utc_now(),
        )

    # -------------------------------------------------------------------------
    # Event CRUD
    # -------------------------------------------------------------------------

    @classmethod
    def create_event(cls, db: Session, request: EventCreate, creator_id: Optional[UUID] = None) -> Event:
        # Check name uniqueness
        existing_name = db.query(Event).filter(func.lower(Event.name) == request.name.lower()).first()
        if existing_name:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An event with this name already exists."
            )

        slug = request.slug
        if not slug:
            cleaned = re.sub(r"[^a-zA-Z0-9\s-]", "", request.name).strip().lower()
            slug = re.sub(r"[\s-]+", "-", cleaned) or "ctf-event"

        # Ensure slug uniqueness
        existing_slug = db.query(Event).filter(Event.slug == slug).first()
        if existing_slug:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"An event with slug '{slug}' already exists."
            )

        # Status validation
        try:
            status_enum = EventStatus(request.status) if request.status else EventStatus.UPCOMING
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid event status '{request.status}'"
            )

        event = Event(
            name=request.name,
            description=request.description,
            slug=slug,
            start_at=request.start_at,
            end_at=request.end_at,
            registration_start_at=request.registration_start_at,
            registration_end_at=request.registration_end_at,
            status=status_enum,
            is_active=request.is_active if request.is_active is not None else True,
            created_by=creator_id,
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return event

    @classmethod
    def get_events(
        cls,
        db: Session,
        include_inactive: bool = False,
        user: Optional[User] = None
    ) -> List[Event]:
        query = db.query(Event)
        is_admin_or_mod = user and user.role in (UserRole.ADMIN, UserRole.MODERATOR)
        if not (include_inactive and is_admin_or_mod):
            query = query.filter(Event.is_active == True)
        return query.order_by(Event.start_at.desc()).all()

    @classmethod
    def get_event_by_id(cls, db: Session, event_id: UUID, user: Optional[User] = None) -> Event:
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found.")
        is_admin_or_mod = user and user.role in (UserRole.ADMIN, UserRole.MODERATOR)
        if not event.is_active and not is_admin_or_mod:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found.")
        return event

    @classmethod
    def get_event_by_slug(cls, db: Session, slug: str, user: Optional[User] = None) -> Event:
        event = db.query(Event).filter(Event.slug == slug).first()
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found.")
        is_admin_or_mod = user and user.role in (UserRole.ADMIN, UserRole.MODERATOR)
        if not event.is_active and not is_admin_or_mod:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found.")
        return event

    @classmethod
    def update_event(cls, db: Session, event_id: UUID, request: EventUpdate) -> Event:
        event = cls.get_event_by_id(db, event_id)

        # Merge candidate dates for validation
        candidate_start = cls._normalize_tz(request.start_at if request.start_at is not None else event.start_at)
        candidate_end = cls._normalize_tz(request.end_at if request.end_at is not None else event.end_at)
        candidate_reg_start = cls._normalize_tz(request.registration_start_at if request.registration_start_at is not None else event.registration_start_at)
        candidate_reg_end = cls._normalize_tz(request.registration_end_at if request.registration_end_at is not None else event.registration_end_at)

        if candidate_end <= candidate_start:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Event end_at must be strictly after start_at."
            )

        if candidate_reg_start and candidate_reg_end:
            if candidate_reg_end <= candidate_reg_start:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="registration_end_at must be after registration_start_at."
                )
            if candidate_reg_end > candidate_start:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="registration_end_at must be less than or equal to event start_at."
                )

        if request.name is not None and request.name != event.name:
            existing = db.query(Event).filter(func.lower(Event.name) == request.name.lower(), Event.id != event_id).first()
            if existing:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An event with this name already exists.")
            event.name = request.name

        if request.slug is not None and request.slug != event.slug:
            existing_slug = db.query(Event).filter(Event.slug == request.slug, Event.id != event_id).first()
            if existing_slug:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug already in use.")
            event.slug = request.slug

        if request.description is not None:
            event.description = request.description
        if request.start_at is not None:
            event.start_at = request.start_at
            event.start_time = request.start_at
        if request.end_at is not None:
            event.end_at = request.end_at
            event.end_time = request.end_at
        if request.registration_start_at is not None:
            event.registration_start_at = request.registration_start_at
        if request.registration_end_at is not None:
            event.registration_end_at = request.registration_end_at
        if request.status is not None:
            try:
                event.status = EventStatus(request.status)
            except ValueError:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Invalid event status '{request.status}'")
        if request.is_active is not None:
            event.is_active = request.is_active

        db.commit()
        db.refresh(event)
        return event

    @classmethod
    def delete_event(cls, db: Session, event_id: UUID) -> None:
        event = cls.get_event_by_id(db, event_id)
        db.delete(event)
        db.commit()

    # -------------------------------------------------------------------------
    # Event Challenges
    # -------------------------------------------------------------------------

    @classmethod
    def add_challenge_to_event(cls, db: Session, event_id: UUID, req: EventChallengeAdd) -> Dict[str, Any]:
        event = cls.get_event_by_id(db, event_id)
        challenge = db.query(Challenge).filter(Challenge.id == req.challenge_id).first()
        if not challenge:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Challenge not found.")

        # Check if already linked
        existing = db.execute(
            event_challenges.select().where(
                and_(
                    event_challenges.c.event_id == event_id,
                    event_challenges.c.challenge_id == req.challenge_id
                )
            )
        ).first()

        if existing:
            # Update attributes
            db.execute(
                event_challenges.update().where(
                    and_(
                        event_challenges.c.event_id == event_id,
                        event_challenges.c.challenge_id == req.challenge_id
                    )
                ).values(
                    display_order=req.display_order if req.display_order else 1,
                    points_override=req.points_override,
                    is_active=True,
                )
            )
        else:
            db.execute(
                event_challenges.insert().values(
                    event_id=event_id,
                    challenge_id=req.challenge_id,
                    display_order=req.display_order if req.display_order else 1,
                    points_override=req.points_override,
                    is_active=True,
                    added_at=utc_now(),
                )
            )
        db.commit()
        return {"event_id": event_id, "challenge_id": req.challenge_id, "display_order": req.display_order}

    @classmethod
    def remove_challenge_from_event(cls, db: Session, event_id: UUID, challenge_id: UUID) -> None:
        cls.get_event_by_id(db, event_id)
        result = db.execute(
            event_challenges.delete().where(
                and_(
                    event_challenges.c.event_id == event_id,
                    event_challenges.c.challenge_id == challenge_id
                )
            )
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Challenge is not associated with this event.")
        db.commit()

    @classmethod
    def get_event_challenges(
        cls,
        db: Session,
        event_id: UUID,
        user: Optional[User] = None
    ) -> List[EventChallengeResponse]:
        event = cls.get_event_by_id(db, event_id, user)
        is_admin_or_mod = user and user.role in (UserRole.ADMIN, UserRole.MODERATOR)

        if not is_admin_or_mod:
            # 1. Verify event is LIVE
            current_status = cls.compute_status(event)
            if current_status != EventStatus.LIVE:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Event challenges are only accessible when the event is LIVE (currently {current_status.value})."
                )
            # 2. Verify user is registered
            if not user or not cls.get_user_registration(db, event_id, user.id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You must be registered for this event to access its challenges."
                )

        query = (
            db.query(
                Challenge,
                event_challenges.c.display_order,
                event_challenges.c.points_override,
                event_challenges.c.is_active.label("event_ch_active"),
            )
            .join(event_challenges, Challenge.id == event_challenges.c.challenge_id)
            .filter(event_challenges.c.event_id == event_id)
        )

        if not is_admin_or_mod:
            query = query.filter(event_challenges.c.is_active == True, Challenge.is_active == True)

        records = query.order_by(event_challenges.c.display_order.asc(), Challenge.title.asc()).all()

        results = []
        for ch, display_order, points_override, is_active in records:
            effective_points = points_override if points_override is not None else ch.points
            results.append(
                EventChallengeResponse(
                    id=ch.id,
                    title=ch.title,
                    description=ch.description,
                    category_id=ch.category_id,
                    category_name=ch.category.name if ch.category else None,
                    difficulty=ch.difficulty.value if hasattr(ch.difficulty, "value") else str(ch.difficulty),
                    points=effective_points,
                    display_order=display_order,
                    is_active=is_active and ch.is_active,
                )
            )
        return results

    # -------------------------------------------------------------------------
    # Registration
    # -------------------------------------------------------------------------

    @classmethod
    def get_user_registration(
        cls,
        db: Session,
        event_id: UUID,
        user_id: UUID
    ) -> Optional[EventRegistration]:
        """Finds active registration for this user directly or via an active team."""
        # 1. Direct individual registration
        reg = db.query(EventRegistration).filter(
            EventRegistration.event_id == event_id,
            EventRegistration.user_id == user_id,
            EventRegistration.is_active == True,
        ).first()
        if reg:
            return reg

        # 2. Team registration
        user_teams = [
            t[0] for t in db.query(TeamMember.team_id).filter(
                TeamMember.user_id == user_id,
                TeamMember.is_active == True,
            ).all()
        ]
        if user_teams:
            team_reg = db.query(EventRegistration).filter(
                EventRegistration.event_id == event_id,
                EventRegistration.team_id.in_(user_teams),
                EventRegistration.is_active == True,
            ).first()
            if team_reg:
                return team_reg
        return None

    @classmethod
    def register_for_event(
        cls,
        db: Session,
        event_id: UUID,
        user: User,
        request: EventRegistrationRequest
    ) -> EventRegistrationResponse:
        event = cls.get_event_by_id(db, event_id)

        # Verify registration window
        if not cls.is_registration_open(event):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration for this event is currently closed."
            )

        if request.registration_type == "individual":
            # Check individual duplicate
            existing_ind = db.query(EventRegistration).filter(
                EventRegistration.event_id == event_id,
                EventRegistration.user_id == user.id,
                EventRegistration.is_active == True,
            ).first()
            if existing_ind:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="You are already registered for this event."
                )

            # Check if user is already registered via any of their teams
            user_teams = [
                t[0] for t in db.query(TeamMember.team_id).filter(
                    TeamMember.user_id == user.id,
                    TeamMember.is_active == True,
                ).all()
            ]
            if user_teams:
                existing_team = db.query(EventRegistration).filter(
                    EventRegistration.event_id == event_id,
                    EventRegistration.team_id.in_(user_teams),
                    EventRegistration.is_active == True,
                ).first()
                if existing_team:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="You are already participating in this event as part of a registered team."
                    )

            registration = EventRegistration(
                event_id=event_id,
                user_id=user.id,
                registration_type=RegistrationType.INDIVIDUAL,
                is_active=True,
            )
            db.add(registration)
            db.commit()
            db.refresh(registration)

            ActivityService.record_activity(
                db=db,
                user_id=user.id,
                activity_type=ActivityType.EVENT_REGISTERED,
                reference_id=event.id,
                metadata={
                    "event_id": str(event.id),
                    "event_name": event.name,
                    "type": "individual",
                }
            )

            # Evaluate badges safely
            try:
                from app.services.badge_service import BadgeService
                BadgeService.evaluate_and_award_badges(db, user.id)
            except Exception:
                pass

            # In-app notification for event registration
            try:
                from app.services.notification_service import NotificationService
                NotificationService.notify_event_registered(
                    db=db,
                    event_id=event.id,
                    event_name=event.name,
                    user_ids=[user.id],
                    is_team=False,
                )
            except Exception:
                pass

            return EventRegistrationResponse(
                id=registration.id,
                event_id=registration.event_id,
                user_id=registration.user_id,
                participant_name=user.username,
                registration_type="individual",
                registered_at=registration.registered_at,
                is_active=registration.is_active,
            )

        else:  # team registration
            team = db.query(Team).filter(Team.id == request.team_id, Team.is_active == True).first()
            if not team:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found.")

            # Team registration restricted to team owner
            if team.owner_id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only the team owner/captain may register the team for an event."
                )

            # Check if team is already registered
            existing_team_reg = db.query(EventRegistration).filter(
                EventRegistration.event_id == event_id,
                EventRegistration.team_id == team.id,
                EventRegistration.is_active == True,
            ).first()
            if existing_team_reg:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Team is already registered for this event."
                )

            # Check if any active member of the team is registered individually or under another team
            team_member_ids = [
                m.user_id for m in team.memberships if m.is_active
            ]
            if not team_member_ids:
                team_member_ids = [team.owner_id]

            conflicting_ind = db.query(EventRegistration).filter(
                EventRegistration.event_id == event_id,
                EventRegistration.user_id.in_(team_member_ids),
                EventRegistration.is_active == True,
            ).first()
            if conflicting_ind:
                conflicting_user = db.query(User).filter(User.id == conflicting_ind.user_id).first()
                u_name = conflicting_user.username if conflicting_user else "A member"
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"{u_name} is already registered individually for this event."
                )

            registration = EventRegistration(
                event_id=event_id,
                team_id=team.id,
                registration_type=RegistrationType.TEAM,
                is_active=True,
            )
            db.add(registration)
            db.commit()
            db.refresh(registration)

            ActivityService.record_activity(
                db=db,
                user_id=user.id,
                activity_type=ActivityType.EVENT_REGISTERED,
                reference_id=event.id,
                metadata={
                    "event_id": str(event.id),
                    "event_name": event.name,
                    "team_id": str(team.id),
                    "team_name": team.name,
                    "type": "team",
                }
            )

            # Evaluate badges safely for team members
            try:
                from app.services.badge_service import BadgeService
                for m_id in team_member_ids:
                    BadgeService.evaluate_and_award_badges(db, m_id)
            except Exception:
                pass

            # In-app notification for team event registration
            try:
                from app.services.notification_service import NotificationService
                NotificationService.notify_event_registered(
                    db=db,
                    event_id=event.id,
                    event_name=event.name,
                    user_ids=team_member_ids,
                    is_team=True,
                    team_name=team.name,
                    team_id=team.id,
                )
            except Exception:
                pass

            return EventRegistrationResponse(
                id=registration.id,
                event_id=registration.event_id,
                team_id=registration.team_id,
                participant_name=team.name,
                registration_type="team",
                registered_at=registration.registered_at,
                is_active=registration.is_active,
            )

    @classmethod
    def unregister_from_event(cls, db: Session, event_id: UUID, user: User) -> Dict[str, str]:
        event = cls.get_event_by_id(db, event_id)
        current_status = cls.compute_status(event)
        if current_status == EventStatus.ENDED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot unregister from an event that has already ended."
            )

        # Check individual registration
        reg = db.query(EventRegistration).filter(
            EventRegistration.event_id == event_id,
            EventRegistration.user_id == user.id,
            EventRegistration.is_active == True,
        ).first()

        if reg:
            db.delete(reg)
            db.commit()
            return {"message": "Successfully unregistered from event."}

        # Check team registration where user is owner
        owned_teams = [
            t[0] for t in db.query(Team.id).filter(Team.owner_id == user.id, Team.is_active == True).all()
        ]
        if owned_teams:
            team_reg = db.query(EventRegistration).filter(
                EventRegistration.event_id == event_id,
                EventRegistration.team_id.in_(owned_teams),
                EventRegistration.is_active == True,
            ).first()

            if team_reg:
                db.delete(team_reg)
                db.commit()
                return {"message": "Team successfully unregistered from event."}

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active registration found for this user/team in the event."
        )

    @classmethod
    def get_participants(cls, db: Session, event_id: UUID) -> List[EventParticipantResponse]:
        cls.get_event_by_id(db, event_id)
        registrations = (
            db.query(EventRegistration)
            .filter(EventRegistration.event_id == event_id, EventRegistration.is_active == True)
            .order_by(EventRegistration.registered_at.asc())
            .all()
        )

        participants = []
        for r in registrations:
            if r.registration_type == RegistrationType.INDIVIDUAL and r.user:
                participants.append(
                    EventParticipantResponse(
                        id=r.id,
                        registration_type="individual",
                        participant_id=r.user.id,
                        participant_name=r.user.username,
                        college=r.user.college,
                        registered_at=r.registered_at,
                    )
                )
            elif r.registration_type == RegistrationType.TEAM and r.team:
                participants.append(
                    EventParticipantResponse(
                        id=r.id,
                        registration_type="team",
                        participant_id=r.team.id,
                        participant_name=r.team.name,
                        college=r.team.college,
                        registered_at=r.registered_at,
                    )
                )
        return participants

    # -------------------------------------------------------------------------
    # Leaderboard & Scoreboard Freeze
    # -------------------------------------------------------------------------

    @classmethod
    def freeze_scoreboard(cls, db: Session, event_id: UUID) -> Event:
        event = cls.get_event_by_id(db, event_id)
        event.is_scoreboard_frozen = True
        event.scoreboard_frozen_at = utc_now()
        db.commit()
        db.refresh(event)
        return event

    @classmethod
    def unfreeze_scoreboard(cls, db: Session, event_id: UUID) -> Event:
        event = cls.get_event_by_id(db, event_id)
        event.is_scoreboard_frozen = False
        event.scoreboard_frozen_at = None
        db.commit()
        db.refresh(event)
        return event

    @classmethod
    def get_event_leaderboard(
        cls,
        db: Session,
        event_id: UUID,
        user: Optional[User] = None
    ) -> EventLeaderboardResponse:
        event = cls.get_event_by_id(db, event_id, user)
        is_admin_or_mod = user and user.role in (UserRole.ADMIN, UserRole.MODERATOR)

        # Determine if public view is frozen
        is_frozen = event.is_scoreboard_frozen
        cutoff_time: Optional[datetime] = None
        if is_frozen and not is_admin_or_mod:
            cutoff_time = event.scoreboard_frozen_at

        # Fetch active registrations
        registrations = (
            db.query(EventRegistration)
            .filter(EventRegistration.event_id == event_id, EventRegistration.is_active == True)
            .all()
        )

        # Build solves query for this event
        solve_query = db.query(Solve).filter(Solve.event_id == event_id)
        if cutoff_time:
            solve_query = solve_query.filter(Solve.created_at <= cutoff_time)
        solves = solve_query.all()

        # Map solves by user_id and team_id
        user_solves: Dict[UUID, List[Solve]] = {}
        team_solves: Dict[UUID, List[Solve]] = {}
        for s in solves:
            if s.team_id:
                team_solves.setdefault(s.team_id, []).append(s)
            elif s.user_id:
                user_solves.setdefault(s.user_id, []).append(s)

        entries = []
        for reg in registrations:
            if reg.registration_type == RegistrationType.INDIVIDUAL and reg.user:
                p_solves = user_solves.get(reg.user.id, [])
                total_points = sum(s.points_awarded for s in p_solves)
                solve_count = len(p_solves)
                last_solve = max([s.created_at for s in p_solves]) if p_solves else None
                entries.append({
                    "participant_id": reg.user.id,
                    "participant_name": reg.user.username,
                    "participant_type": "individual",
                    "college": reg.user.college,
                    "total_points": total_points,
                    "solved_count": solve_count,
                    "last_solve_time": last_solve,
                })
            elif reg.registration_type == RegistrationType.TEAM and reg.team:
                p_solves = team_solves.get(reg.team.id, [])
                total_points = sum(s.points_awarded for s in p_solves)
                solve_count = len(p_solves)
                last_solve = max([s.created_at for s in p_solves]) if p_solves else None
                entries.append({
                    "participant_id": reg.team.id,
                    "participant_name": reg.team.name,
                    "participant_type": "team",
                    "college": reg.team.college,
                    "total_points": total_points,
                    "solved_count": solve_count,
                    "last_solve_time": last_solve,
                })

        # Sort entries:
        # 1. total_points desc
        # 2. last_solve_time asc (None goes to the end)
        # 3. participant_name asc
        distant_future = datetime(9999, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        entries.sort(
            key=lambda x: (
                -x["total_points"],
                cls._normalize_tz(x["last_solve_time"]) if x["last_solve_time"] else distant_future,
                x["participant_name"].lower(),
            )
        )

        leaderboard_items = []
        for idx, item in enumerate(entries, start=1):
            leaderboard_items.append(
                EventLeaderboardEntry(
                    rank=idx,
                    participant_id=item["participant_id"],
                    participant_name=item["participant_name"],
                    participant_type=item["participant_type"],
                    college=item["college"],
                    total_points=item["total_points"],
                    solved_count=item["solved_count"],
                    last_solve_time=item["last_solve_time"],
                )
            )

        return EventLeaderboardResponse(
            event_id=event.id,
            event_name=event.name,
            is_scoreboard_frozen=is_frozen,
            scoreboard_frozen_at=event.scoreboard_frozen_at if is_frozen else None,
            total_participants=len(leaderboard_items),
            items=leaderboard_items,
        )
