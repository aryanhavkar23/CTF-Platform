import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.config import settings
from app.models.user import User, UserRole
from app.models.team import Team
from app.models.challenge import Challenge
from app.models.event import Event
from app.models.submission import Submission
from app.models.solve import Solve
from app.models.security_event import (
    SecurityEvent,
    SecurityEventReview,
    SecurityEventType,
    SecurityEventSeverity,
    SecurityEventStatus,
)
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

# Weight mapping for suspicion scoring
EVENT_TYPE_WEIGHTS = {
    SecurityEventType.SUBMISSION_RATE_EXCEEDED.value: 20,
    SecurityEventType.EXCESSIVE_FAILED_SUBMISSIONS.value: 15,
    SecurityEventType.RAPID_MULTI_CHALLENGE_SOLVING.value: 20,
    SecurityEventType.REPEATED_CHALLENGE_ATTEMPTS.value: 10,
    SecurityEventType.CHALLENGE_ACCESS_VIOLATION.value: 30,
    SecurityEventType.SUSPICIOUS_EVENT_ACTIVITY.value: 15,
}


class AntiCheatService:
    """Service providing rule-based submission abuse protection and security observability."""

    # -------------------------------------------------------------------------
    # Core Event Logging & Cooldown Deduplication
    # -------------------------------------------------------------------------

    @classmethod
    def record_security_event(
        cls,
        db: Session,
        event_type: SecurityEventType,
        severity: SecurityEventSeverity,
        description: str,
        user_id: Optional[UUID] = None,
        team_id: Optional[UUID] = None,
        event_id: Optional[UUID] = None,
        challenge_id: Optional[UUID] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
    ) -> SecurityEvent:
        """Records a security observation with cooldown deduplication to prevent flood storms."""
        now = datetime.now(timezone.utc)
        cooldown_threshold = now - timedelta(seconds=settings.SECURITY_EVENT_COOLDOWN_SECONDS)

        # Check for duplicate open security event within cooldown window
        dup_query = db.query(SecurityEvent).filter(
            SecurityEvent.event_type == event_type.value,
            SecurityEvent.created_at >= cooldown_threshold,
            SecurityEvent.status == SecurityEventStatus.OPEN.value,
        )
        if user_id:
            dup_query = dup_query.filter(SecurityEvent.user_id == user_id)
        if challenge_id:
            dup_query = dup_query.filter(SecurityEvent.challenge_id == challenge_id)

        existing_event = dup_query.first()
        if existing_event:
            return existing_event

        # Sanitize metadata (strictly prevent flags/hashes/passwords from ever persisting)
        safe_metadata = {}
        if metadata:
            for k, v in metadata.items():
                if any(secret_term in k.lower() for secret_term in ["flag", "password", "token", "hash", "secret"]):
                    continue
                safe_metadata[k] = v

        event = SecurityEvent(
            user_id=user_id,
            team_id=team_id,
            event_id=event_id,
            challenge_id=challenge_id,
            event_type=event_type.value,
            severity=severity.value,
            description=description,
            metadata_json=json.dumps(safe_metadata) if safe_metadata else None,
            ip_address=ip_address,
            status=SecurityEventStatus.OPEN.value,
        )
        try:
            db.add(event)
            db.commit()
            db.refresh(event)
        except Exception as e:
            logger.error(f"Failed to record security event: {e}")
            db.rollback()
            return event

        # Notify administrators and moderators if severity is HIGH or CRITICAL
        if severity in (SecurityEventSeverity.HIGH, SecurityEventSeverity.CRITICAL):
            try:
                cls._notify_admins(db, event)
            except Exception as e:
                logger.error(f"Failed to dispatch security alert notification: {e}")

        return event

    @classmethod
    def _notify_admins(cls, db: Session, event: SecurityEvent) -> None:
        """Sends an in-app notification to all admins and moderators for high/critical incidents."""
        admin_and_mods = db.query(User).filter(
            User.role.in_([UserRole.ADMIN, UserRole.MODERATOR]),
            User.is_active == True,
        ).all()

        for admin in admin_and_mods:
            NotificationService.create_notification(
                db=db,
                user_id=admin.id,
                type="security_alert",
                title=f"[{event.severity.upper()}] Anti-Cheat: {event.event_type}",
                message=event.description,
                data={
                    "security_event_id": str(event.id),
                    "event_type": event.event_type,
                    "severity": event.severity,
                    "user_id": str(event.user_id) if event.user_id else None,
                },
                event_key=f"sec_alert:{event.id}:{admin.id}",
            )

    # -------------------------------------------------------------------------
    # Rule-Based Abuse Evaluators
    # -------------------------------------------------------------------------

    @classmethod
    def check_submission_rate_limit(
        cls,
        db: Session,
        user_id: UUID,
        ip_address: Optional[str] = None
    ) -> None:
        """Database-backed sliding window submission rate limiting."""
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(seconds=settings.SUBMISSION_RATE_WINDOW_SECONDS)

        recent_submissions = db.query(func.count(Submission.id)).filter(
            Submission.user_id == user_id,
            Submission.created_at >= window_start,
        ).scalar() or 0

        if recent_submissions >= settings.SUBMISSION_RATE_LIMIT:
            # Record security event for rate limit violation
            cls.record_security_event(
                db=db,
                event_type=SecurityEventType.SUBMISSION_RATE_EXCEEDED,
                severity=SecurityEventSeverity.LOW,
                description=(
                    f"User exceeded submission rate limit: {recent_submissions} submissions "
                    f"in {settings.SUBMISSION_RATE_WINDOW_SECONDS}s (limit: {settings.SUBMISSION_RATE_LIMIT})"
                ),
                user_id=user_id,
                metadata={
                    "submissions_in_window": recent_submissions,
                    "window_seconds": settings.SUBMISSION_RATE_WINDOW_SECONDS,
                    "rate_limit": settings.SUBMISSION_RATE_LIMIT,
                },
                ip_address=ip_address,
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many submission attempts. Please try again later."
            )

    @classmethod
    def evaluate_failed_submissions(
        cls,
        db: Session,
        user_id: UUID,
        challenge_id: Optional[UUID] = None,
        event_id: Optional[UUID] = None,
        team_id: Optional[UUID] = None,
        ip_address: Optional[str] = None
    ) -> None:
        """Detects excessive failed submissions within the configured time window."""
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(seconds=settings.FAILED_SUBMISSION_WINDOW_SECONDS)

        failed_count = db.query(func.count(Submission.id)).filter(
            Submission.user_id == user_id,
            Submission.is_correct == False,
            Submission.created_at >= window_start,
        ).scalar() or 0

        if failed_count >= settings.FAILED_SUBMISSION_THRESHOLD:
            cls.record_security_event(
                db=db,
                event_type=SecurityEventType.EXCESSIVE_FAILED_SUBMISSIONS,
                severity=SecurityEventSeverity.HIGH,
                description=(
                    f"Excessive failed submissions detected: {failed_count} incorrect flags "
                    f"within {settings.FAILED_SUBMISSION_WINDOW_SECONDS}s window (threshold: {settings.FAILED_SUBMISSION_THRESHOLD})"
                ),
                user_id=user_id,
                team_id=team_id,
                event_id=event_id,
                challenge_id=challenge_id,
                metadata={
                    "failed_count": failed_count,
                    "window_seconds": settings.FAILED_SUBMISSION_WINDOW_SECONDS,
                    "threshold": settings.FAILED_SUBMISSION_THRESHOLD,
                },
                ip_address=ip_address,
            )

    @classmethod
    def evaluate_repeated_attempts(
        cls,
        db: Session,
        user_id: UUID,
        challenge_id: UUID,
        event_id: Optional[UUID] = None,
        team_id: Optional[UUID] = None,
        ip_address: Optional[str] = None
    ) -> None:
        """Detects rapid repeated incorrect attempts targeting a single challenge."""
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(seconds=settings.REPEATED_CHALLENGE_ATTEMPT_WINDOW_SECONDS)

        failed_challenge_attempts = db.query(func.count(Submission.id)).filter(
            Submission.user_id == user_id,
            Submission.challenge_id == challenge_id,
            Submission.is_correct == False,
            Submission.created_at >= window_start,
        ).scalar() or 0

        if failed_challenge_attempts >= settings.REPEATED_CHALLENGE_ATTEMPT_THRESHOLD:
            cls.record_security_event(
                db=db,
                event_type=SecurityEventType.REPEATED_CHALLENGE_ATTEMPTS,
                severity=SecurityEventSeverity.MEDIUM,
                description=(
                    f"Repeated attempts on single challenge: {failed_challenge_attempts} failed submissions "
                    f"within {settings.REPEATED_CHALLENGE_ATTEMPT_WINDOW_SECONDS}s (threshold: {settings.REPEATED_CHALLENGE_ATTEMPT_THRESHOLD})"
                ),
                user_id=user_id,
                team_id=team_id,
                event_id=event_id,
                challenge_id=challenge_id,
                metadata={
                    "challenge_id": str(challenge_id),
                    "attempt_count": failed_challenge_attempts,
                    "window_seconds": settings.REPEATED_CHALLENGE_ATTEMPT_WINDOW_SECONDS,
                    "threshold": settings.REPEATED_CHALLENGE_ATTEMPT_THRESHOLD,
                },
                ip_address=ip_address,
            )

    @classmethod
    def evaluate_rapid_solves(
        cls,
        db: Session,
        user_id: UUID,
        event_id: Optional[UUID] = None,
        team_id: Optional[UUID] = None,
        ip_address: Optional[str] = None
    ) -> None:
        """Detects unusually rapid multi-challenge solving patterns."""
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(seconds=settings.RAPID_SOLVE_WINDOW_SECONDS)

        solve_count = db.query(func.count(Solve.id)).filter(
            Solve.user_id == user_id,
            Solve.created_at >= window_start,
        ).scalar() or 0

        if solve_count >= settings.RAPID_SOLVE_COUNT:
            cls.record_security_event(
                db=db,
                event_type=SecurityEventType.RAPID_MULTI_CHALLENGE_SOLVING,
                severity=SecurityEventSeverity.HIGH,
                description=(
                    f"Unusually rapid solving pattern: {solve_count} distinct challenges solved "
                    f"within {settings.RAPID_SOLVE_WINDOW_SECONDS}s (threshold: {settings.RAPID_SOLVE_COUNT})"
                ),
                user_id=user_id,
                team_id=team_id,
                event_id=event_id,
                metadata={
                    "rapid_solves_count": solve_count,
                    "window_seconds": settings.RAPID_SOLVE_WINDOW_SECONDS,
                    "threshold": settings.RAPID_SOLVE_COUNT,
                },
                ip_address=ip_address,
            )

    @classmethod
    def record_access_violation(
        cls,
        db: Session,
        user_id: UUID,
        challenge_id: Optional[UUID] = None,
        event_id: Optional[UUID] = None,
        reason: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        team_id: Optional[UUID] = None,
        ip_address: Optional[str] = None
    ) -> None:
        """Records unauthorized attempts to access or submit flags for restricted challenges."""
        desc = description or f"Challenge access violation: {reason or 'unauthorized attempt'}"
        meta = metadata if metadata is not None else ({"reason": reason} if reason else {})
        cls.record_security_event(
            db=db,
            event_type=SecurityEventType.CHALLENGE_ACCESS_VIOLATION,
            severity=SecurityEventSeverity.HIGH,
            description=desc,
            user_id=user_id,
            team_id=team_id,
            event_id=event_id,
            challenge_id=challenge_id,
            metadata=meta,
            ip_address=ip_address,
        )

    # -------------------------------------------------------------------------
    # Suspicion Scoring & Administrative Reviews
    # -------------------------------------------------------------------------

    @classmethod
    def calculate_suspicion_score(cls, db: Session, user_id: UUID) -> Tuple[int, str]:
        """
        Calculates an explainable weighted suspicion score and threat level.
        Only considers non-dismissed security events.
        """
        events = db.query(SecurityEvent).filter(
            SecurityEvent.user_id == user_id,
            SecurityEvent.status != SecurityEventStatus.DISMISSED.value,
        ).all()

        total_score = sum(EVENT_TYPE_WEIGHTS.get(ev.event_type, 10) for ev in events)

        if total_score >= 80:
            level = "Critical"
        elif total_score >= 60:
            level = "High"
        elif total_score >= 40:
            level = "Medium"
        elif total_score >= 20:
            level = "Low"
        else:
            level = "Normal"

        return total_score, level

    @classmethod
    def list_security_events(
        cls,
        db: Session,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        event_type: Optional[str] = None,
        user_id: Optional[UUID] = None,
        event_id: Optional[UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """Returns paginated security events with relational context and filters."""
        query = db.query(
            SecurityEvent,
            User.username,
            Team.name,
            Event.name,
            Challenge.title
        ).outerjoin(User, SecurityEvent.user_id == User.id)\
         .outerjoin(Team, SecurityEvent.team_id == Team.id)\
         .outerjoin(Event, SecurityEvent.event_id == Event.id)\
         .outerjoin(Challenge, SecurityEvent.challenge_id == Challenge.id)

        if status and status != "all":
            query = query.filter(SecurityEvent.status == status)
        if severity and severity != "all":
            query = query.filter(SecurityEvent.severity == severity)
        if event_type and event_type != "all":
            query = query.filter(SecurityEvent.event_type == event_type)
        if user_id:
            query = query.filter(SecurityEvent.user_id == user_id)
        if event_id:
            query = query.filter(SecurityEvent.event_id == event_id)
        if start_date:
            query = query.filter(SecurityEvent.created_at >= start_date)
        if end_date:
            query = query.filter(SecurityEvent.created_at <= end_date)

        total = query.count()
        rows = query.order_by(desc(SecurityEvent.created_at))\
                    .offset((page - 1) * page_size)\
                    .limit(page_size)\
                    .all()

        items = []
        for ev, uname, tname, evname, ch_title in rows:
            items.append({
                "id": ev.id,
                "user_id": ev.user_id,
                "username": uname,
                "team_id": ev.team_id,
                "team_name": tname,
                "event_id": ev.event_id,
                "event_name": evname,
                "challenge_id": ev.challenge_id,
                "challenge_title": ch_title,
                "event_type": ev.event_type,
                "severity": ev.severity,
                "description": ev.description,
                "metadata_json": ev.metadata_json,
                "ip_address": ev.ip_address,
                "status": ev.status,
                "created_at": ev.created_at,
                "updated_at": ev.updated_at,
            })

        total_pages = max(1, (total + page_size - 1) // page_size)
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    @classmethod
    def get_security_event_detail(cls, db: Session, event_id: UUID) -> Optional[Dict[str, Any]]:
        """Returns details for a single security incident."""
        row = db.query(
            SecurityEvent,
            User.username,
            Team.name,
            Event.name,
            Challenge.title
        ).outerjoin(User, SecurityEvent.user_id == User.id)\
         .outerjoin(Team, SecurityEvent.team_id == Team.id)\
         .outerjoin(Event, SecurityEvent.event_id == Event.id)\
         .outerjoin(Challenge, SecurityEvent.challenge_id == Challenge.id)\
         .filter(SecurityEvent.id == event_id)\
         .first()

        if not row:
            return None

        ev, uname, tname, evname, ch_title = row

        reviews_rows = db.query(SecurityEventReview, User.username)\
            .outerjoin(User, SecurityEventReview.reviewer_id == User.id)\
            .filter(SecurityEventReview.security_event_id == ev.id)\
            .order_by(SecurityEventReview.created_at.desc())\
            .all()

        reviews = [
            {
                "id": rev.id,
                "security_event_id": rev.security_event_id,
                "reviewer_id": rev.reviewer_id,
                "reviewer_username": r_uname,
                "previous_status": rev.previous_status,
                "new_status": rev.new_status,
                "note": rev.note,
                "created_at": rev.created_at,
            }
            for rev, r_uname in reviews_rows
        ]

        return {
            "id": ev.id,
            "user_id": ev.user_id,
            "username": uname,
            "team_id": ev.team_id,
            "team_name": tname,
            "event_id": ev.event_id,
            "event_name": evname,
            "challenge_id": ev.challenge_id,
            "challenge_title": ch_title,
            "event_type": ev.event_type,
            "severity": ev.severity,
            "description": ev.description,
            "metadata_json": ev.metadata_json,
            "ip_address": ev.ip_address,
            "status": ev.status,
            "created_at": ev.created_at,
            "updated_at": ev.updated_at,
            "reviews": reviews,
        }

    @classmethod
    def review_security_event(
        cls,
        db: Session,
        event_id: UUID,
        reviewer_id: UUID,
        new_status: SecurityEventStatus,
        note: Optional[str] = None
    ) -> Dict[str, Any]:
        """Transitions event status with an immutable audit trail entry."""
        event = db.query(SecurityEvent).filter(SecurityEvent.id == event_id).first()
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Security event not found")

        prev_status = event.status
        event.status = new_status.value
        event.updated_at = datetime.now(timezone.utc)

        review = SecurityEventReview(
            security_event_id=event.id,
            reviewer_id=reviewer_id,
            previous_status=prev_status,
            new_status=new_status.value,
            note=note.strip() if note else None,
        )
        db.add(review)
        db.commit()

        detail = cls.get_security_event_detail(db, event.id)
        return detail

    @classmethod
    def get_user_security_summary(cls, db: Session, user_id: UUID) -> Dict[str, Any]:
        """Provides an administrator with an aggregate risk breakdown for a user."""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        total_events = db.query(func.count(SecurityEvent.id)).filter(SecurityEvent.user_id == user_id).scalar() or 0
        open_events = db.query(func.count(SecurityEvent.id)).filter(
            SecurityEvent.user_id == user_id,
            SecurityEvent.status == SecurityEventStatus.OPEN.value,
        ).scalar() or 0
        high_critical = db.query(func.count(SecurityEvent.id)).filter(
            SecurityEvent.user_id == user_id,
            SecurityEvent.severity.in_([SecurityEventSeverity.HIGH.value, SecurityEventSeverity.CRITICAL.value]),
            SecurityEvent.status != SecurityEventStatus.DISMISSED.value,
        ).scalar() or 0

        score, level = cls.calculate_suspicion_score(db, user_id)

        # Recent 10 events
        recent = cls.list_security_events(db, user_id=user_id, page=1, page_size=10)["items"]

        return {
            "user_id": user.id,
            "username": user.username,
            "total_security_events": total_events,
            "open_events": open_events,
            "high_critical_events": high_critical,
            "suspicion_score": score,
            "suspicion_level": level,
            "recent_events": recent,
        }
