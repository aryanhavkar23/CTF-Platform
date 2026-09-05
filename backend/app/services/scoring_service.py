from typing import Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.solve import Solve
from app.models.submission import Submission
from app.models.hint_usage import HintUsage


class ScoringService:
    """Authoritative scoring calculations derived from verified solves."""

    @staticmethod
    def get_hint_deductions(db: Session, user_id: UUID, challenge_id: UUID) -> int:
        """Calculates total point deductions from hints unlocked by the user for a challenge."""
        deductions = db.query(func.coalesce(func.sum(HintUsage.points_deducted), 0))\
            .filter(
                HintUsage.user_id == user_id,
                HintUsage.challenge_id == challenge_id
            ).scalar()
        return int(deductions or 0)

    @staticmethod
    def has_used_hint(db: Session, user_id: UUID, hint_id: UUID) -> bool:
        """Checks whether the user has unlocked this specific hint."""
        return db.query(HintUsage).filter(
            HintUsage.user_id == user_id,
            HintUsage.hint_id == hint_id
        ).first() is not None


    @staticmethod
    def get_user_score(db: Session, user_id: UUID) -> int:
        """Calculates user's total score from their verified solves in practice mode.
        
        Guaranteed to avoid double-counting via the solves ledger.
        """
        score = db.query(func.coalesce(func.sum(Solve.points_awarded), 0))\
            .filter(Solve.user_id == user_id, Solve.event_id == None)\
            .scalar()
        return int(score or 0)

    @staticmethod
    def get_user_solve_count(db: Session, user_id: UUID) -> int:
        """Returns the total number of distinct challenges solved by the user in practice mode."""
        count = db.query(func.count(Solve.id))\
            .filter(Solve.user_id == user_id, Solve.event_id == None)\
            .scalar()
        return int(count or 0)

    @staticmethod
    def has_solved(
        db: Session,
        user_id: UUID,
        challenge_id: UUID,
        event_id: Optional[UUID] = None,
        team_id: Optional[UUID] = None,
    ) -> bool:
        """Checks whether the user (or team) has already solved this challenge."""
        query = db.query(Solve).filter(Solve.challenge_id == challenge_id)
        if event_id is not None:
            query = query.filter(Solve.event_id == event_id)
            if team_id is not None:
                query = query.filter(Solve.team_id == team_id)
            else:
                query = query.filter(Solve.user_id == user_id)
        else:
            query = query.filter(Solve.user_id == user_id, Solve.event_id == None)
        return query.first() is not None

    @staticmethod
    def get_challenge_status(db: Session, user_id: UUID, challenge_id: UUID) -> Dict[str, Any]:
        """Determines solve and attempt status for a user and challenge."""
        solve = db.query(Solve).filter(
            Solve.user_id == user_id,
            Solve.challenge_id == challenge_id
        ).first()

        if solve:
            return {
                "challenge_id": challenge_id,
                "status": "solved",
                "points_earned": solve.points_awarded,
                "solved_at": solve.created_at
            }

        attempt = db.query(Submission).filter(
            Submission.user_id == user_id,
            Submission.challenge_id == challenge_id
        ).first()

        if attempt:
            return {
                "challenge_id": challenge_id,
                "status": "attempted",
                "points_earned": 0,
                "solved_at": None
            }

        return {
            "challenge_id": challenge_id,
            "status": "not_attempted",
            "points_earned": 0,
            "solved_at": None
        }
