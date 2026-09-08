from typing import Optional, List
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.user import User, UserRole
from app.models.challenge import Challenge, ChallengeHint
from app.models.hint_usage import HintUsage
from app.schemas.hint import HintCreate, HintUpdate, HintResponse, HintUsageResponse
from app.services.scoring_service import ScoringService
from app.services.activity_service import ActivityService
from app.models.activity import ActivityType


class HintService:
    """Service handling hint authoring, safe student visibility, and hint unlocking."""

    @staticmethod
    def create_hint(db: Session, challenge_id: UUID, request: HintCreate) -> ChallengeHint:
        """Creates a new hint for a challenge. Validates challenge existence."""
        challenge = db.query(Challenge).filter(Challenge.id == challenge_id).first()
        if not challenge:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Challenge not found"
            )

        hint = ChallengeHint(
            challenge_id=challenge_id,
            title=request.title,
            content=request.content,
            point_deduction=request.points_deduction,
            order=request.display_order,
            is_active=request.is_active,
        )
        db.add(hint)
        db.commit()
        db.refresh(hint)
        return hint

    @staticmethod
    def get_hints_for_challenge(
        db: Session,
        challenge_id: UUID,
        user: Optional[User] = None
    ) -> List[HintResponse]:
        """Lists hints for a challenge.
        
        Moderators and administrators see full content for all hints.
        Students only see active hints, and content is strictly omitted (None)
        until the student unlocks the hint via /use.
        """
        challenge = db.query(Challenge).filter(Challenge.id == challenge_id).first()
        if not challenge:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Challenge not found"
            )

        is_admin_or_mod = user is not None and user.role in [UserRole.MODERATOR, UserRole.ADMIN]

        query = db.query(ChallengeHint).filter(ChallengeHint.challenge_id == challenge_id)
        if not is_admin_or_mod:
            query = query.filter(ChallengeHint.is_active == True)

        hints = query.order_by(ChallengeHint.order.asc()).all()

        results = []
        for h in hints:
            used = False
            content = None

            if is_admin_or_mod:
                content = h.content
            elif user:
                used = ScoringService.has_used_hint(db, user.id, h.id)
                if used:
                    content = h.content

            results.append(
                HintResponse(
                    id=h.id,
                    challenge_id=h.challenge_id,
                    title=h.title,
                    content=content,
                    points_deduction=h.point_deduction,
                    point_deduction=h.point_deduction,
                    display_order=h.order,
                    order=h.order,
                    is_active=h.is_active,
                    used=used,
                    created_at=h.created_at,
                    updated_at=h.updated_at,
                )
            )

        return results

    @staticmethod
    def get_hint(
        db: Session,
        challenge_id: UUID,
        hint_id: UUID,
        user: Optional[User] = None
    ) -> HintResponse:
        """Retrieves a single hint with content protection for unrevealed students."""
        hint = db.query(ChallengeHint).filter(
            ChallengeHint.id == hint_id,
            ChallengeHint.challenge_id == challenge_id
        ).first()
        if not hint:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Hint not found for this challenge"
            )

        is_admin_or_mod = user is not None and user.role in [UserRole.MODERATOR, UserRole.ADMIN]

        if not is_admin_or_mod and not hint.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Hint not found"
            )

        used = False
        content = None
        if is_admin_or_mod:
            content = hint.content
        elif user:
            used = ScoringService.has_used_hint(db, user.id, hint.id)
            if used:
                content = hint.content

        return HintResponse(
            id=hint.id,
            challenge_id=hint.challenge_id,
            title=hint.title,
            content=content,
            points_deduction=hint.point_deduction,
            point_deduction=hint.point_deduction,
            display_order=hint.order,
            order=hint.order,
            is_active=hint.is_active,
            used=used,
            created_at=hint.created_at,
            updated_at=hint.updated_at,
        )

    @staticmethod
    def update_hint(
        db: Session,
        challenge_id: UUID,
        hint_id: UUID,
        request: HintUpdate
    ) -> ChallengeHint:
        """Updates hint attributes. Restricted to moderators and administrators."""
        hint = db.query(ChallengeHint).filter(
            ChallengeHint.id == hint_id,
            ChallengeHint.challenge_id == challenge_id
        ).first()
        if not hint:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Hint not found for this challenge"
            )

        if request.title is not None:
            hint.title = request.title
        if request.content is not None:
            hint.content = request.content
        if request.points_deduction is not None:
            hint.point_deduction = request.points_deduction
        if request.display_order is not None:
            hint.order = request.display_order
        if request.is_active is not None:
            hint.is_active = request.is_active

        db.commit()
        db.refresh(hint)
        return hint

    @staticmethod
    def delete_hint(db: Session, challenge_id: UUID, hint_id: UUID) -> bool:
        """Deletes a hint. Restricted to moderators and administrators."""
        hint = db.query(ChallengeHint).filter(
            ChallengeHint.id == hint_id,
            ChallengeHint.challenge_id == challenge_id
        ).first()
        if not hint:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Hint not found for this challenge"
            )
        db.delete(hint)
        db.commit()
        return True

    @staticmethod
    def use_hint(
        db: Session,
        challenge_id: UUID,
        hint_id: UUID,
        user: User
    ) -> HintUsageResponse:
        """Allows an authenticated student to unlock a hint, recording the deduction."""
        # 1. Challenge must exist and be active
        challenge = db.query(Challenge).filter(Challenge.id == challenge_id).first()
        if not challenge or not challenge.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Challenge not found or is inactive"
            )

        # 2. Hint must exist, belong to challenge, and be active
        hint = db.query(ChallengeHint).filter(
            ChallengeHint.id == hint_id,
            ChallengeHint.challenge_id == challenge_id
        ).first()
        if not hint or not hint.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Hint is inactive or does not belong to this challenge"
            )

        # 3. Cannot use hint after solving challenge
        if ScoringService.has_solved(db, user.id, challenge_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot use hints after already solving the challenge"
            )

        # 4. Cannot use hint twice
        if ScoringService.has_used_hint(db, user.id, hint_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Hint has already been unlocked by this user"
            )

        # 5. Record usage atomically
        usage = HintUsage(
            user_id=user.id,
            hint_id=hint.id,
            challenge_id=challenge_id,
            points_deducted=hint.point_deduction,
        )
        db.add(usage)
        try:
            db.commit()
            db.refresh(usage)
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Hint has already been unlocked by this user"
            )

        # Record CTF activity for hint usage
        ActivityService.record_activity(
            db=db,
            user_id=user.id,
            activity_type=ActivityType.HINT_USED,
            reference_id=hint.id,
            metadata={
                "challenge_id": str(challenge_id),
                "hint_title": hint.title,
                "points_deducted": usage.points_deducted,
            }
        )

        return HintUsageResponse(
            hint_id=hint.id,
            challenge_id=challenge_id,
            title=hint.title,
            content=hint.content,
            points_deducted=usage.points_deducted,
            used_at=usage.used_at,
        )
