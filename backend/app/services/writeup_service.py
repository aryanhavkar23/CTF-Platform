from typing import Optional, List
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.models.challenge import Challenge, ChallengeWriteup, WriteupVisibility
from app.schemas.writeup import WriteupCreate, WriteupUpdate
from app.services.scoring_service import ScoringService


class WriteupService:
    """Service managing challenge writeups and enforcing visibility access rules."""

    @staticmethod
    def create_or_update_writeup(
        db: Session,
        challenge_id: UUID,
        request: WriteupCreate
    ) -> ChallengeWriteup:
        """Creates or updates a writeup for a challenge."""
        challenge = db.query(Challenge).filter(Challenge.id == challenge_id).first()
        if not challenge:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Challenge not found"
            )

        writeup = db.query(ChallengeWriteup).filter(ChallengeWriteup.challenge_id == challenge_id).first()
        if writeup:
            writeup.title = request.title
            writeup.content = request.content
            writeup.visibility = request.visibility
        else:
            writeup = ChallengeWriteup(
                challenge_id=challenge_id,
                title=request.title,
                content=request.content,
                visibility=request.visibility
            )
            db.add(writeup)

        db.commit()
        db.refresh(writeup)
        return writeup

    @staticmethod
    def get_writeups_for_challenge(
        db: Session,
        challenge_id: UUID,
        user: Optional[User] = None
    ) -> List[ChallengeWriteup]:
        """Returns writeups for a challenge, enforcing visibility rules."""
        challenge = db.query(Challenge).filter(Challenge.id == challenge_id).first()
        if not challenge:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Challenge not found"
            )

        writeup = db.query(ChallengeWriteup).filter(ChallengeWriteup.challenge_id == challenge_id).first()
        if not writeup:
            return []

        # Check visibility
        is_admin_or_mod = user is not None and user.role in [UserRole.MODERATOR, UserRole.ADMIN]
        if is_admin_or_mod or writeup.visibility == WriteupVisibility.PUBLIC:
            return [writeup]

        if writeup.visibility == WriteupVisibility.AFTER_SOLVE:
            if user and ScoringService.has_solved(db, user.id, challenge_id):
                return [writeup]

        # In hidden or after_event, return empty list for public list query
        return []

    @staticmethod
    def get_writeup(
        db: Session,
        challenge_id: UUID,
        user: Optional[User] = None,
        writeup_id: Optional[UUID] = None
    ) -> ChallengeWriteup:
        """Retrieves writeup detail, enforcing visibility or raising 403 Forbidden."""
        challenge = db.query(Challenge).filter(Challenge.id == challenge_id).first()
        if not challenge:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Challenge not found"
            )

        query = db.query(ChallengeWriteup).filter(ChallengeWriteup.challenge_id == challenge_id)
        if writeup_id:
            query = query.filter(ChallengeWriteup.id == writeup_id)

        writeup = query.first()
        if not writeup:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Writeup not found"
            )

        is_admin_or_mod = user is not None and user.role in [UserRole.MODERATOR, UserRole.ADMIN]
        if is_admin_or_mod or writeup.visibility == WriteupVisibility.PUBLIC:
            return writeup

        if writeup.visibility == WriteupVisibility.AFTER_SOLVE:
            if not user or not ScoringService.has_solved(db, user.id, challenge_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Writeup is locked: solving the challenge is required"
                )
            return writeup

        if writeup.visibility == WriteupVisibility.AFTER_EVENT:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Writeup is locked: event has not concluded"
            )

        # HIDDEN
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Writeup is locked according to visibility rules"
        )

    @staticmethod
    def update_writeup(
        db: Session,
        challenge_id: UUID,
        writeup_id: UUID,
        request: WriteupUpdate
    ) -> ChallengeWriteup:
        """Updates a challenge writeup. Restricted to moderators and administrators."""
        writeup = db.query(ChallengeWriteup).filter(
            ChallengeWriteup.id == writeup_id,
            ChallengeWriteup.challenge_id == challenge_id
        ).first()
        if not writeup:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Writeup not found for this challenge"
            )

        if request.title is not None:
            writeup.title = request.title
        if request.content is not None:
            writeup.content = request.content
        if request.visibility is not None:
            writeup.visibility = request.visibility

        db.commit()
        db.refresh(writeup)
        return writeup

    @staticmethod
    def delete_writeup(
        db: Session,
        challenge_id: UUID,
        writeup_id: Optional[UUID] = None
    ) -> bool:
        """Deletes a challenge writeup. Restricted to moderators and administrators."""
        query = db.query(ChallengeWriteup).filter(ChallengeWriteup.challenge_id == challenge_id)
        if writeup_id:
            query = query.filter(ChallengeWriteup.id == writeup_id)

        writeup = query.first()
        if not writeup:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Writeup not found"
            )

        db.delete(writeup)
        db.commit()
        return True
