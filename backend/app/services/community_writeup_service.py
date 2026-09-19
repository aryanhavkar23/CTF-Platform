import logging
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.solution import UserWriteup, WriteupUpvote
from app.models.challenge import Challenge
from app.models.user import User, UserRole
from app.models.solve import Solve
from app.schemas.community_writeup import UserWriteupCreate, UserWriteupUpdate

logger = logging.getLogger(__name__)


class CommunityWriteupService:
    """Business logic for community-submitted challenge writeups and upvotes."""

    @classmethod
    def list_writeups(
        cls,
        db: Session,
        challenge_id: UUID,
        current_user: Optional[User] = None
    ) -> List[Dict[str, Any]]:
        """Lists published community writeups for a specific challenge."""
        # Verify challenge exists
        chall = db.query(Challenge).filter(Challenge.id == challenge_id).first()
        if not chall:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Challenge not found.")

        # Query writeups
        query = db.query(UserWriteup).filter(
            UserWriteup.challenge_id == challenge_id,
            UserWriteup.is_published == True
        )
        writeups = query.order_by(UserWriteup.upvotes_count.desc(), UserWriteup.created_at.desc()).all()

        # Gather author solved map
        author_ids = [w.user_id for w in writeups]
        solved_author_ids = set()
        if author_ids:
            solved_rows = (
                db.query(Solve.user_id)
                .filter(Solve.challenge_id == challenge_id, Solve.user_id.in_(author_ids))
                .all()
            )
            solved_author_ids = {r[0] for r in solved_rows}

        # Gather upvotes by current_user
        upvoted_writeup_ids = set()
        if current_user and writeups:
            wu_ids = [w.id for w in writeups]
            upvoted_rows = (
                db.query(WriteupUpvote.writeup_id)
                .filter(WriteupUpvote.user_id == current_user.id, WriteupUpvote.writeup_id.in_(wu_ids))
                .all()
            )
            upvoted_writeup_ids = {r[0] for r in upvoted_rows}

        chall_title = chall.title if chall else None
        chall_cat = chall.category.name if (chall and chall.category) else None
        chall_pts = chall.points if chall else 0

        results = []
        for w in writeups:
            author = w.user
            results.append({
                "id": w.id,
                "challenge_id": w.challenge_id,
                "user_id": w.user_id,
                "title": w.title,
                "content": w.content,
                "tags": w.tags,
                "upvotes_count": w.upvotes_count,
                "is_published": w.is_published,
                "created_at": w.created_at,
                "updated_at": w.updated_at,
                "author_username": author.username if author else "operative",
                "author_name": (author.name or author.username) if author else "operative",
                "author_college": author.college if author else None,
                "author_avatar_url": author.avatar_url if author else None,
                "author_has_solved": w.user_id in solved_author_ids,
                "is_upvoted_by_me": w.id in upvoted_writeup_ids,
                "is_author": bool(current_user and current_user.id == w.user_id),
                "challenge_title": chall_title,
                "challenge_category": chall_cat,
                "challenge_points": chall_pts,
            })

        return results

    @classmethod
    def create_writeup(
        cls,
        db: Session,
        challenge_id: UUID,
        user_id: UUID,
        data: UserWriteupCreate
    ) -> Dict[str, Any]:
        """Operative publishes their own solution/writeup for a challenge."""
        chall = db.query(Challenge).filter(Challenge.id == challenge_id).first()
        if not chall:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Challenge not found.")

        author = db.query(User).filter(User.id == user_id).first()
        if not author:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

        writeup = UserWriteup(
            challenge_id=challenge_id,
            user_id=user_id,
            title=data.title.strip(),
            content=data.content.strip(),
            tags=data.tags.strip() if data.tags else None,
            upvotes_count=0,
            is_published=True,
        )
        db.add(writeup)
        db.commit()
        db.refresh(writeup)

        has_solved = db.query(Solve).filter(Solve.challenge_id == challenge_id, Solve.user_id == user_id).first() is not None

        return {
            "id": writeup.id,
            "challenge_id": writeup.challenge_id,
            "user_id": writeup.user_id,
            "title": writeup.title,
            "content": writeup.content,
            "tags": writeup.tags,
            "upvotes_count": writeup.upvotes_count,
            "is_published": writeup.is_published,
            "created_at": writeup.created_at,
            "updated_at": writeup.updated_at,
            "author_username": author.username,
            "author_name": author.name or author.username,
            "author_college": author.college,
            "author_avatar_url": author.avatar_url,
            "author_has_solved": has_solved,
            "is_upvoted_by_me": False,
            "is_author": True,
            "challenge_title": chall.title,
            "challenge_category": chall.category.name if chall.category else None,
            "challenge_points": chall.points,
        }

    @classmethod
    def update_writeup(
        cls,
        db: Session,
        writeup_id: UUID,
        current_user: User,
        data: UserWriteupUpdate
    ) -> Dict[str, Any]:
        """Author or Administrator updates their writeup."""
        writeup = db.query(UserWriteup).filter(UserWriteup.id == writeup_id).first()
        if not writeup:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Writeup not found.")

        is_admin = current_user.role in [UserRole.ADMIN, UserRole.MODERATOR]
        if writeup.user_id != current_user.id and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to modify this writeup."
            )

        if data.title is not None:
            writeup.title = data.title.strip()
        if data.content is not None:
            writeup.content = data.content.strip()
        if data.tags is not None:
            writeup.tags = data.tags.strip() if data.tags else None
        if data.is_published is not None:
            writeup.is_published = data.is_published

        db.commit()
        db.refresh(writeup)

        chall = db.query(Challenge).filter(Challenge.id == writeup.challenge_id).first()
        author = writeup.user
        has_solved = db.query(Solve).filter(Solve.challenge_id == writeup.challenge_id, Solve.user_id == writeup.user_id).first() is not None
        is_upvoted = db.query(WriteupUpvote).filter(WriteupUpvote.writeup_id == writeup.id, WriteupUpvote.user_id == current_user.id).first() is not None

        return {
            "id": writeup.id,
            "challenge_id": writeup.challenge_id,
            "user_id": writeup.user_id,
            "title": writeup.title,
            "content": writeup.content,
            "tags": writeup.tags,
            "upvotes_count": writeup.upvotes_count,
            "is_published": writeup.is_published,
            "created_at": writeup.created_at,
            "updated_at": writeup.updated_at,
            "author_username": author.username if author else "operative",
            "author_name": (author.name or author.username) if author else "operative",
            "author_college": author.college if author else None,
            "author_avatar_url": author.avatar_url if author else None,
            "author_has_solved": has_solved,
            "is_upvoted_by_me": is_upvoted,
            "is_author": bool(current_user.id == writeup.user_id),
            "challenge_title": chall.title if chall else None,
            "challenge_category": chall.category.name if (chall and chall.category) else None,
            "challenge_points": chall.points if chall else 0,
        }

    @classmethod
    def delete_writeup(cls, db: Session, writeup_id: UUID, current_user: User) -> bool:
        """Author or Administrator deletes a community writeup."""
        writeup = db.query(UserWriteup).filter(UserWriteup.id == writeup_id).first()
        if not writeup:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Writeup not found.")

        is_admin = current_user.role in [UserRole.ADMIN, UserRole.MODERATOR]
        if writeup.user_id != current_user.id and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to delete this writeup."
            )

        db.delete(writeup)
        db.commit()
        return True

    @classmethod
    def toggle_upvote(cls, db: Session, writeup_id: UUID, current_user: User) -> Tuple[int, bool]:
        """Toggles upvote for an operative writeup (1 per user). Returns (upvotes_count, is_upvoted)."""
        writeup = db.query(UserWriteup).filter(UserWriteup.id == writeup_id).first()
        if not writeup:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Writeup not found.")

        existing = db.query(WriteupUpvote).filter(
            WriteupUpvote.writeup_id == writeup_id,
            WriteupUpvote.user_id == current_user.id
        ).first()

        if existing:
            # Remove upvote
            db.delete(existing)
            writeup.upvotes_count = max(0, writeup.upvotes_count - 1)
            db.commit()
            db.refresh(writeup)
            return writeup.upvotes_count, False
        else:
            # Add upvote
            new_upvote = WriteupUpvote(writeup_id=writeup_id, user_id=current_user.id)
            db.add(new_upvote)
            writeup.upvotes_count += 1
            db.commit()
            db.refresh(writeup)

            # In-app notification to author if author is different user
            if writeup.user_id != current_user.id:
                try:
                    from app.services.notification_service import NotificationService
                    NotificationService.create_notification(
                        db=db,
                        user_id=writeup.user_id,
                        type="writeup_upvote",
                        title="Solution Applauded",
                        message=f"{current_user.username} applauded your solution '{writeup.title[:40]}'.",
                        data={"writeup_id": str(writeup.id), "challenge_id": str(writeup.challenge_id)},
                        event_key=f"writeup_upvote_{writeup.id}_{current_user.id}"
                    )
                except Exception:
                    pass

            return writeup.upvotes_count, True
