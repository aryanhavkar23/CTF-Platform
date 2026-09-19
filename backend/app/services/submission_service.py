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
from app.services.activity_service import ActivityService
from app.models.activity import ActivityType


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

        # 2. Window check and Anti-Cheat rate limiting
        from app.services.anti_cheat_service import AntiCheatService
        AntiCheatService.check_submission_rate_limit(db, user_id)

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
            if challenge and not challenge.is_active:
                try:
                    from app.services.anti_cheat_service import AntiCheatService
                    AntiCheatService.record_access_violation(
                        db=db,
                        description=f"Submission attempt against inactive challenge '{challenge.title}'.",
                        user_id=user.id,
                        challenge_id=challenge.id,
                        event_id=event_id,
                        metadata={"reason": "inactive_challenge"}
                    )
                except Exception:
                    pass
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
            if current_status not in (EventStatus.LIVE, EventStatus.ENDED):
                try:
                    from app.services.anti_cheat_service import AntiCheatService
                    AntiCheatService.record_access_violation(
                        db=db,
                        description=f"Submission attempt on event '{event.title}' when event is not LIVE or ENDED (status: {current_status.value}).",
                        user_id=user.id,
                        challenge_id=challenge.id,
                        event_id=event.id,
                        metadata={"event_status": current_status.value}
                    )
                except Exception:
                    pass
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Submissions are only allowed when the event is LIVE or ENDED for practice (currently {current_status.value})."
                )

            reg = EventService.get_user_registration(db, event_id, user.id)
            if current_status == EventStatus.LIVE:
                if not reg:
                    try:
                        from app.services.anti_cheat_service import AntiCheatService
                        AntiCheatService.record_access_violation(
                            db=db,
                            description=f"Unregistered user submission attempt for event '{event.title}'.",
                            user_id=user.id,
                            challenge_id=challenge.id,
                            event_id=event.id,
                            metadata={"reason": "unregistered_event_user"}
                        )
                    except Exception:
                        pass
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="You must be registered for this event to submit flags."
                    )

                if reg.registration_type == RegistrationType.TEAM:
                    effective_team_id = reg.team_id
            else:
                # Ended event (Practice Mode)
                if reg and reg.registration_type == RegistrationType.TEAM:
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
                try:
                    from app.services.anti_cheat_service import AntiCheatService
                    AntiCheatService.record_access_violation(
                        db=db,
                        description=f"Submission attempt for challenge '{challenge.title}' which does not belong to event '{event.title}'.",
                        user_id=user.id,
                        challenge_id=challenge.id,
                        event_id=event.id,
                        metadata={"reason": "challenge_not_in_event"}
                    )
                except Exception:
                    pass
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Challenge is not part of this event."
                )

            if event_ch.points_override is not None:
                base_points = event_ch.points_override

        # 4. Validate flag using constant-time comparison & fallback mapping
        clean_submitted = submitted_flag.strip()
        submitted_hash = hash_flag(clean_submitted)
        is_match = hmac.compare_digest(submitted_hash, challenge.flag_hash)

        if not is_match:
            import hashlib
            from app.api.challenges import CHALLENGE_FLAG_MAP
            # Fallback 1: Raw sha256 without salt
            raw_hash = hashlib.sha256(clean_submitted.encode("utf-8")).hexdigest()
            if hmac.compare_digest(raw_hash, challenge.flag_hash):
                is_match = True
            
            # Fallback 2: Check against official flag map
            if not is_match:
                expected_flag = CHALLENGE_FLAG_MAP.get(challenge.title)
                if not expected_flag:
                    # Try matching by prefix
                    prefix = challenge.title.split("—")[0].strip().split(" ")[0]
                    for k, v in CHALLENGE_FLAG_MAP.items():
                        if k.startswith(prefix):
                            expected_flag = v
                            break
                if expected_flag and clean_submitted.lower() == expected_flag.strip().lower():
                    is_match = True

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

            # Anti-cheat evaluation for failed and repeated attempts
            try:
                from app.services.anti_cheat_service import AntiCheatService
                AntiCheatService.evaluate_failed_submissions(
                    db=db,
                    user_id=user.id,
                    event_id=event_id,
                    team_id=effective_team_id
                )
                AntiCheatService.evaluate_repeated_attempts(
                    db=db,
                    user_id=user.id,
                    challenge_id=challenge.id,
                    event_id=event_id,
                    team_id=effective_team_id
                )
            except Exception:
                pass
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
        is_ended_practice = False
        if event_id is not None:
            event_obj = db.query(Event).filter(Event.id == event_id).first()
            if event_obj and EventService.compute_status(event_obj) == EventStatus.ENDED:
                is_ended_practice = True

        hint_deductions = ScoringService.get_hint_deductions(db, user.id, challenge.id)
        if is_ended_practice:
            awarded_points = 0
        else:
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

            # Record CTF activity for verified solve
            ActivityService.record_activity(
                db=db,
                user_id=user.id,
                activity_type=ActivityType.CHALLENGE_SOLVED,
                reference_id=challenge.id,
                metadata={
                    "challenge_title": challenge.title,
                    "points_awarded": awarded_points,
                    "event_id": str(event_id) if event_id else None,
                    "practice_mode": is_ended_practice,
                }
            )

            # Update cached score in UserProfile (skip inflating event score in practice mode)
            if not is_ended_practice:
                ScoringService.recalculate_user_profile_score(db, user.id)

            # Broadcast solve via WebSocket
            try:
                from app.services.websocket_manager import ws_manager
                import asyncio
                payload = {
                    "type": "solve",
                    "user_id": str(user.id),
                    "username": user.username,
                    "challenge_id": str(challenge.id),
                    "challenge_title": challenge.title,
                    "points": awarded_points,
                    "event_id": str(event_id) if event_id else None,
                    "is_practice": is_ended_practice,
                }
                asyncio.create_task(ws_manager.broadcast_event("solve", payload))
            except Exception:
                pass

            # Authoritatively evaluate and award badges (isolated to protect scoring)
            try:
                from app.services.badge_service import BadgeService
                BadgeService.evaluate_and_award_badges(db, user.id)
            except Exception:
                pass

            # In-app notification for solved challenge (isolated to protect scoring)
            try:
                from app.services.notification_service import NotificationService
                NotificationService.notify_challenge_solved(
                    db=db,
                    user_id=user.id,
                    challenge_title=challenge.title,
                    challenge_id=challenge.id,
                    points_awarded=awarded_points,
                    event_id=event_id,
                )
            except Exception:
                pass

            # Anti-cheat: evaluate rapid multi-challenge solving (isolated to protect scoring)
            try:
                from app.services.anti_cheat_service import AntiCheatService
                AntiCheatService.evaluate_rapid_solves(
                    db=db,
                    user_id=user.id,
                    event_id=event_id,
                    team_id=effective_team_id
                )
            except Exception:
                pass

            # Auto-sync CTF solution commit to student's GitHub repository (isolated to protect scoring)
            try:
                from app.services.github_service import GitHubService
                GitHubService.sync_solve_to_github(
                    db=db,
                    user_id=user.id,
                    challenge=challenge,
                    solve=solve,
                    submission=sub,
                    points_awarded=awarded_points
                )
            except Exception as gh_err:
                logger.warning(f"GitHub solve auto-commit skipped or failed: {gh_err}")


            msg = "✓ Practice mode solve verified! Correct flag." if is_ended_practice else f"Correct flag! {awarded_points} points awarded."
            return {
                "submission": sub,
                "is_correct": True,
                "points_awarded": awarded_points,
                "message": msg
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
