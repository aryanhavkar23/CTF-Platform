import hmac
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_
from fastapi import HTTPException, status

from app.config import settings
from app.models.challenge import Challenge
from app.models.submission import Submission
from app.models.solve import Solve
from app.models.user import User
from app.models.event import Event, EventStatus, event_challenges
from app.models.event_registration import EventRegistration, RegistrationType
from app.services.challenge_service import hash_flag
from app.services.scoring_service import ScoringService
from app.services.event_service import EventService


class SubmissionService:
    """Coordinates submission rate limiting, flag validation, and atomic solve recording."""

    @staticmethod
    def check_rate_limit(db: Session, user_id: UUID) -> None:
        """Enforces sliding window limit and cooldown period between attempts."""
        now = datetime.now(timezone.utc)

        # 1. Cooldown check (last submission too recent)
        last_sub = db.query(Submission)\
            .filter(Submission.user_id == user_id)\
            .order_by(Submission.created_at.desc())\
            .first()

        if last_sub and last_sub.created_at:
            last_time = last_sub.created_at
            if last_time.tzinfo is None:
                last_time = last_time.replace(tzinfo=timezone.utc)
            elapsed = (now - last_time).total_seconds()
            if elapsed < settings.SUBMISSION_COOLDOWN_SECONDS:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Submission cooldown active. Please wait {settings.SUBMISSION_COOLDOWN_SECONDS} seconds between attempts."
                )

        # 2. Window check (attempts in last 60 seconds)
        window_start = now - timedelta(minutes=1)
        recent_count = db.query(Submission)\
            .filter(Submission.user_id == user_id, Submission.created_at >= window_start)\
            .count()

        if recent_count >= settings.SUBMISSION_RATE_LIMIT_PER_MINUTE:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded ({settings.SUBMISSION_RATE_LIMIT_PER_MINUTE} submissions/min). Please slow down."
            )

    @staticmethod
    def process_submission(
        db: Session,
        user: User,
        challenge_id: UUID,
        submitted_flag: str,
        event_id: Optional[UUID] = None,
        skip_rate_limit: bool = False
    ) -> Dict[str, Any]:
        """Validates submitted flag, records attempt, and atomically awards points."""
        # 1. Check rate limit
        if not skip_rate_limit:
            SubmissionService.check_rate_limit(db, user.id)

        # 2. Validate challenge
        challenge = db.query(Challenge).filter(Challenge.id == challenge_id).first()
        if not challenge or not challenge.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Challenge not found or is currently inactive"
            )

        # 3. If event_id is specified, enforce event rules
        effective_team_id: Optional[UUID] = None
        base_points = challenge.points

        if event_id is not None:
            event = db.query(Event).filter(Event.id == event_id).first()
            if not event or not event.is_active:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Event not found or is currently inactive"
                )

            current_status = EventService.compute_status(event)
            if current_status != EventStatus.LIVE:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Submissions are only allowed when the event is LIVE (currently {current_status.value})."
                )

            reg = EventService.get_user_registration(db, event_id, user.id)
            if not reg:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You must be registered for this event to submit flags."
                )

            if reg.registration_type == RegistrationType.TEAM:
                effective_team_id = reg.team_id

            # Verify challenge is in event
            event_ch = db.execute(
                event_challenges.select().where(
                    and_(
                        event_challenges.c.event_id == event_id,
                        event_challenges.c.challenge_id == challenge_id,
                        event_challenges.c.is_active == True,
                    )
                )
            ).first()
            if not event_ch:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Challenge is not part of this event."
                )

            if event_ch.points_override is not None:
                base_points = event_ch.points_override

        # 4. Validate flag using constant-time comparison
        submitted_hash = hash_flag(submitted_flag)
        is_match = hmac.compare_digest(submitted_hash, challenge.flag_hash)

        # 5. Handle incorrect submission
        if not is_match:
            sub = Submission(
                user_id=user.id,
                challenge_id=challenge.id,
                event_id=event_id,
                team_id=effective_team_id,
                submitted_flag_hash=submitted_hash,
                is_correct=False,
                points_awarded=0
            )
            db.add(sub)
            db.commit()
            db.refresh(sub)
            return {
                "submission": sub,
                "is_correct": False,
                "points_awarded": 0,
                "message": "Incorrect flag."
            }

        # 6. Handle correct submission & duplicate checks
        already_solved = ScoringService.has_solved(
            db, user.id, challenge.id, event_id=event_id, team_id=effective_team_id
        )

        if already_solved:
            sub = Submission(
                user_id=user.id,
                challenge_id=challenge.id,
                event_id=event_id,
                team_id=effective_team_id,
                submitted_flag_hash=submitted_hash,
                is_correct=True,
                points_awarded=0
            )
            db.add(sub)
            db.commit()
            db.refresh(sub)
            msg = "Already solved for your team." if effective_team_id else "Already solved. No additional points awarded."
            return {
                "submission": sub,
                "is_correct": True,
                "points_awarded": 0,
                "message": msg
            }

        # 7. First solve: Atomically award points and register in solves ledger
        hint_deductions = ScoringService.get_hint_deductions(db, user.id, challenge.id)
        awarded_points = max(base_points - hint_deductions, 0)

        sub = Submission(
            user_id=user.id,
            challenge_id=challenge.id,
            event_id=event_id,
            team_id=effective_team_id,
            submitted_flag_hash=submitted_hash,
            is_correct=True,
            points_awarded=awarded_points
        )
        db.add(sub)
        db.flush()  # assign sub.id

        try:
            solve = Solve(
                user_id=user.id,
                challenge_id=challenge.id,
                event_id=event_id,
                team_id=effective_team_id,
                submission_id=sub.id,
                points_awarded=awarded_points
            )
            db.add(solve)
            db.commit()
            db.refresh(sub)
            return {
                "submission": sub,
                "is_correct": True,
                "points_awarded": awarded_points,
                "message": f"Correct flag! {awarded_points} points awarded."
            }
        except IntegrityError:
            # Race condition: another concurrent transaction solved it at the same moment
            db.rollback()
            sub_dup = Submission(
                user_id=user.id,
                challenge_id=challenge.id,
                event_id=event_id,
                team_id=effective_team_id,
                submitted_flag_hash=submitted_hash,
                is_correct=True,
                points_awarded=0
            )
            db.add(sub_dup)
            db.commit()
            db.refresh(sub_dup)
            return {
                "submission": sub_dup,
                "is_correct": True,
                "points_awarded": 0,
                "message": "Already solved. No additional points awarded."
            }

    @staticmethod
    def get_user_submissions(
        db: Session,
        user_id: UUID,
        event_id: Optional[UUID] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Retrieves caller's submission history with challenge and category metadata."""
        query = db.query(Submission).filter(Submission.user_id == user_id)
        if event_id is not None:
            query = query.filter(Submission.event_id == event_id)

        submissions = query.order_by(Submission.created_at.desc()).limit(limit).all()

        history = []
        for s in submissions:
            chall = s.challenge
            history.append({
                "id": s.id,
                "challenge_id": s.challenge_id,
                "challenge_title": chall.title if chall else "Deleted Challenge",
                "category_name": chall.category.name if chall and chall.category else None,
                "is_correct": s.is_correct,
                "points_awarded": s.points_awarded,
                "created_at": s.created_at,
                "event_id": s.event_id,
                "team_id": s.team_id,
            })
        return history
