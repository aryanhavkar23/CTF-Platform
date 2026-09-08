import html
import re
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, func
from fastapi import HTTPException, status

from app.models.discussion import Discussion, DiscussionComment
from app.models.challenge import Challenge
from app.models.user import User, UserRole
from app.models.event import Event, EventStatus, event_challenges
from app.schemas.discussion import (
    DiscussionCreate,
    DiscussionUpdate,
    CommentCreate,
    CommentUpdate,
    DiscussionResponse,
    CommentResponse,
    DiscussionListResponse,
    CommentListResponse,
)
from app.services.challenge_service import ChallengeService, hash_flag
from app.services.event_service import EventService


def sanitize_content(text: str) -> str:
    """Sanitizes user input to prevent stored XSS while keeping safe formatting."""
    if not text:
        return ""
    # Strip dangerous HTML elements
    cleaned = re.sub(r"<\s*(script|iframe|object|embed|applet|meta|link)[^>]*>.*?<\s*/\s*\1\s*>", "", text, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"<\s*(script|iframe|object|embed|applet|meta|link)[^>]*>", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"javascript\s*:", "blocked:", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bon\w+\s*=", "data-blocked=", cleaned, flags=re.IGNORECASE)
    # Neutralize HTML tags
    return html.escape(cleaned)


class DiscussionService:
    """Authoritative business logic for challenge discussions, threaded comments, and moderation."""

    @staticmethod
    def _check_flag_leak(text: str, challenge: Challenge) -> None:
        """Ensures exact challenge solution flags are never leaked directly in content."""
        if not text or not challenge:
            return
        tokens = re.findall(r"[^\s]+", text)
        for token in tokens:
            clean_token = token.strip(".,;:!?\"'()")
            if clean_token and hash_flag(clean_token) == challenge.flag_hash:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Posting exact challenge solution flags in discussions is prohibited."
                )

    @classmethod
    def check_challenge_access(cls, db: Session, challenge: Challenge, user: Optional[User]) -> None:
        """Enforces challenge status and event isolation rules for discussions."""
        is_admin_or_mod = user is not None and user.role in (UserRole.ADMIN, UserRole.MODERATOR)
        if is_admin_or_mod:
            return

        if not challenge.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Challenge not found or is currently inactive"
            )

        # Check if challenge is linked to any active events
        active_event_links = (
            db.query(event_challenges.c.event_id)
            .filter(
                event_challenges.c.challenge_id == challenge.id,
                event_challenges.c.is_active == True,
            )
            .all()
        )

        for (event_id,) in active_event_links:
            event = db.query(Event).filter(Event.id == event_id).first()
            if not event or not event.is_active:
                continue

            event_status = EventService.compute_status(event)
            if event_status == EventStatus.UPCOMING:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Challenge is part of upcoming event '{event.name}' and discussion is not yet open."
                )

            if event_status == EventStatus.LIVE:
                if not user:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Authentication is required to participate in live event discussions."
                    )
                reg = EventService.get_user_registration(db, event.id, user.id)
                if not reg:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"You must be registered for event '{event.name}' to access its discussions."
                    )

    @classmethod
    def format_discussion_response(cls, discussion: Discussion, caller: Optional[User]) -> Dict[str, Any]:
        """Formats discussion dict masking deleted content for standard participants."""
        is_admin_or_mod = caller is not None and caller.role in (UserRole.ADMIN, UserRole.MODERATOR)
        is_deleted = discussion.is_deleted

        title = discussion.title
        content = discussion.content
        if is_deleted and not is_admin_or_mod:
            title = "[Deleted]"
            content = "[This discussion has been deleted by author or moderator]"

        author = None
        if discussion.user:
            author = {
                "id": discussion.user.id,
                "username": discussion.user.username if (not is_deleted or is_admin_or_mod) else "[deleted]",
                "role": discussion.user.role.value if hasattr(discussion.user.role, "value") else str(discussion.user.role),
                "avatar_url": discussion.user.avatar_url if (not is_deleted or is_admin_or_mod) else None,
                "college": discussion.user.college if (not is_deleted or is_admin_or_mod) else None,
            }

        comments_count = len(discussion.comments) if discussion.comments else 0

        return {
            "id": discussion.id,
            "challenge_id": discussion.challenge_id,
            "user": author,
            "title": title,
            "content": content,
            "is_pinned": discussion.is_pinned,
            "is_locked": discussion.is_locked,
            "is_deleted": is_deleted,
            "contains_spoiler": discussion.contains_spoiler,
            "comments_count": comments_count,
            "created_at": discussion.created_at,
            "updated_at": discussion.updated_at,
        }

    @classmethod
    def format_comment_response(cls, comment: DiscussionComment, caller: Optional[User]) -> Dict[str, Any]:
        """Formats comment dict masking deleted content for standard participants."""
        is_admin_or_mod = caller is not None and caller.role in (UserRole.ADMIN, UserRole.MODERATOR)
        is_deleted = comment.is_deleted

        content = comment.content
        if is_deleted and not is_admin_or_mod:
            content = "[This comment has been deleted]"

        author = None
        if comment.user:
            author = {
                "id": comment.user.id,
                "username": comment.user.username if (not is_deleted or is_admin_or_mod) else "[deleted]",
                "role": comment.user.role.value if hasattr(comment.user.role, "value") else str(comment.user.role),
                "avatar_url": comment.user.avatar_url if (not is_deleted or is_admin_or_mod) else None,
                "college": comment.user.college if (not is_deleted or is_admin_or_mod) else None,
            }

        replies_count = len(comment.replies) if comment.replies else 0

        return {
            "id": comment.id,
            "discussion_id": comment.discussion_id,
            "user": author,
            "parent_comment_id": comment.parent_comment_id,
            "content": content,
            "is_deleted": is_deleted,
            "contains_spoiler": comment.contains_spoiler,
            "created_at": comment.created_at,
            "updated_at": comment.updated_at,
            "replies_count": replies_count,
        }

    # -------------------------------------------------------------------------
    # Discussion Management
    # -------------------------------------------------------------------------

    @classmethod
    def create_discussion(
        cls,
        db: Session,
        challenge_id: UUID,
        user: User,
        data: DiscussionCreate
    ) -> Dict[str, Any]:
        """Creates a new discussion for a challenge after checking permissions and inputs."""
        is_admin_or_mod = user.role in (UserRole.ADMIN, UserRole.MODERATOR)
        challenge = ChallengeService.get_challenge(db, challenge_id, is_admin_or_mod=is_admin_or_mod)
        cls.check_challenge_access(db, challenge, user)

        title = data.title.strip()
        if len(title) < 3:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Title must be at least 3 characters.")

        content = data.content.strip()
        if len(content) < 1:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Content cannot be empty.")

        cls._check_flag_leak(content, challenge)
        cls._check_flag_leak(title, challenge)

        clean_title = sanitize_content(title)
        clean_content = sanitize_content(content)

        discussion = Discussion(
            challenge_id=challenge.id,
            user_id=user.id,
            title=clean_title,
            content=clean_content,
            contains_spoiler=data.contains_spoiler,
            is_pinned=False,
            is_locked=False,
            is_deleted=False,
        )
        db.add(discussion)
        db.commit()
        db.refresh(discussion)
        return cls.format_discussion_response(discussion, user)

    @classmethod
    def list_discussions(
        cls,
        db: Session,
        challenge_id: UUID,
        user: Optional[User] = None,
        page: int = 1,
        limit: int = 20,
        sort: str = "newest",
    ) -> DiscussionListResponse:
        """Lists discussions for a challenge with pagination and sorting, pinned items prioritized."""
        is_admin_or_mod = user is not None and user.role in (UserRole.ADMIN, UserRole.MODERATOR)
        challenge = ChallengeService.get_challenge(db, challenge_id, is_admin_or_mod=is_admin_or_mod)
        cls.check_challenge_access(db, challenge, user)

        query = db.query(Discussion).filter(Discussion.challenge_id == challenge_id)
        if not is_admin_or_mod:
            # Show active discussions (including soft-deleted placeholder ones to preserve history)
            pass

        total = query.count()

        # Sorting: always pinned first, then requested order
        if sort == "oldest":
            query = query.order_by(desc(Discussion.is_pinned), asc(Discussion.created_at))
        elif sort == "pinned":
            query = query.order_by(desc(Discussion.is_pinned), desc(Discussion.created_at))
        else:  # newest
            query = query.order_by(desc(Discussion.is_pinned), desc(Discussion.created_at))

        offset = (page - 1) * limit
        items = query.offset(offset).limit(limit).all()

        formatted_items = [
            DiscussionResponse(**cls.format_discussion_response(d, user))
            for d in items
        ]

        return DiscussionListResponse(
            items=formatted_items,
            total=total,
            page=page,
            limit=limit,
        )

    @classmethod
    def get_discussion(cls, db: Session, discussion_id: UUID, user: Optional[User] = None) -> Dict[str, Any]:
        """Retrieves single discussion details enforcing access rules."""
        discussion = db.query(Discussion).filter(Discussion.id == discussion_id).first()
        if not discussion:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discussion not found.")

        cls.check_challenge_access(db, discussion.challenge, user)
        return cls.format_discussion_response(discussion, user)

    @classmethod
    def update_discussion(
        cls,
        db: Session,
        discussion_id: UUID,
        user: User,
        data: DiscussionUpdate
    ) -> Dict[str, Any]:
        """Updates a discussion enforcing ownership, lock state, and content validation."""
        discussion = db.query(Discussion).filter(Discussion.id == discussion_id).first()
        if not discussion:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discussion not found.")

        is_admin_or_mod = user.role in (UserRole.ADMIN, UserRole.MODERATOR)
        if discussion.user_id != user.id and not is_admin_or_mod:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to modify this discussion."
            )

        if discussion.is_locked and not is_admin_or_mod:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Discussion is locked and cannot be modified."
            )

        if discussion.is_deleted and not is_admin_or_mod:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Deleted discussions cannot be modified."
            )

        if data.title is not None:
            title = data.title.strip()
            if len(title) < 3:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Title must be at least 3 characters.")
            cls._check_flag_leak(title, discussion.challenge)
            discussion.title = sanitize_content(title)

        if data.content is not None:
            content = data.content.strip()
            if len(content) < 1:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Content cannot be empty.")
            cls._check_flag_leak(content, discussion.challenge)
            discussion.content = sanitize_content(content)

        if data.contains_spoiler is not None:
            discussion.contains_spoiler = data.contains_spoiler

        db.commit()
        db.refresh(discussion)
        return cls.format_discussion_response(discussion, user)

    @classmethod
    def delete_discussion(cls, db: Session, discussion_id: UUID, user: User) -> Dict[str, Any]:
        """Soft-deletes discussion enforcing author ownership or moderator privilege."""
        discussion = db.query(Discussion).filter(Discussion.id == discussion_id).first()
        if not discussion:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discussion not found.")

        is_admin_or_mod = user.role in (UserRole.ADMIN, UserRole.MODERATOR)
        if discussion.user_id != user.id and not is_admin_or_mod:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to delete this discussion."
            )

        discussion.is_deleted = True
        db.commit()
        return {
            "message": "Discussion deleted successfully.",
            "discussion_id": str(discussion_id),
            "is_deleted": True,
        }

    # -------------------------------------------------------------------------
    # Moderation Actions: Lock / Unlock & Pin / Unpin
    # -------------------------------------------------------------------------

    @classmethod
    def lock_discussion(cls, db: Session, discussion_id: UUID, user: User) -> Dict[str, Any]:
        if user.role not in (UserRole.ADMIN, UserRole.MODERATOR):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only administrators and moderators can lock discussions.")
        discussion = db.query(Discussion).filter(Discussion.id == discussion_id).first()
        if not discussion:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discussion not found.")
        discussion.is_locked = True
        db.commit()
        db.refresh(discussion)
        return cls.format_discussion_response(discussion, user)

    @classmethod
    def unlock_discussion(cls, db: Session, discussion_id: UUID, user: User) -> Dict[str, Any]:
        if user.role not in (UserRole.ADMIN, UserRole.MODERATOR):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only administrators and moderators can unlock discussions.")
        discussion = db.query(Discussion).filter(Discussion.id == discussion_id).first()
        if not discussion:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discussion not found.")
        discussion.is_locked = False
        db.commit()
        db.refresh(discussion)
        return cls.format_discussion_response(discussion, user)

    @classmethod
    def pin_discussion(cls, db: Session, discussion_id: UUID, user: User) -> Dict[str, Any]:
        if user.role not in (UserRole.ADMIN, UserRole.MODERATOR):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only administrators and moderators can pin discussions.")
        discussion = db.query(Discussion).filter(Discussion.id == discussion_id).first()
        if not discussion:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discussion not found.")
        discussion.is_pinned = True
        db.commit()
        db.refresh(discussion)
        return cls.format_discussion_response(discussion, user)

    @classmethod
    def unpin_discussion(cls, db: Session, discussion_id: UUID, user: User) -> Dict[str, Any]:
        if user.role not in (UserRole.ADMIN, UserRole.MODERATOR):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only administrators and moderators can unpin discussions.")
        discussion = db.query(Discussion).filter(Discussion.id == discussion_id).first()
        if not discussion:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discussion not found.")
        discussion.is_pinned = False
        db.commit()
        db.refresh(discussion)
        return cls.format_discussion_response(discussion, user)

    # -------------------------------------------------------------------------
    # Comment & Reply Management
    # -------------------------------------------------------------------------

    @classmethod
    def create_comment(
        cls,
        db: Session,
        discussion_id: UUID,
        user: User,
        data: CommentCreate
    ) -> Dict[str, Any]:
        """Adds a comment or reply to a discussion, verifying discussion lock and anti-IDOR parent relation."""
        discussion = db.query(Discussion).filter(Discussion.id == discussion_id).first()
        if not discussion or discussion.is_deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discussion not found.")

        cls.check_challenge_access(db, discussion.challenge, user)

        if discussion.is_locked:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Discussion is locked. New comments and replies are disabled."
            )

        if data.parent_comment_id:
            parent = db.query(DiscussionComment).filter(DiscussionComment.id == data.parent_comment_id).first()
            if not parent:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent comment not found.")

            # Critical Anti-IDOR check: Parent comment must belong to this exact discussion
            if parent.discussion_id != discussion.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Parent comment does not belong to this discussion."
                )

            if parent.is_deleted:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot reply to a deleted comment."
                )

        content = data.content.strip()
        if len(content) < 1:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Comment content cannot be empty.")

        cls._check_flag_leak(content, discussion.challenge)
        clean_content = sanitize_content(content)

        comment = DiscussionComment(
            discussion_id=discussion.id,
            user_id=user.id,
            parent_comment_id=data.parent_comment_id,
            content=clean_content,
            contains_spoiler=data.contains_spoiler,
            is_deleted=False,
        )
        db.add(comment)
        db.commit()
        db.refresh(comment)

        # In-app notification for discussion reply / comment
        try:
            from app.services.notification_service import NotificationService
            parent_uid = parent.user_id if data.parent_comment_id and 'parent' in locals() and parent else None
            NotificationService.notify_discussion_reply(
                db=db,
                discussion_id=discussion.id,
                discussion_title=discussion.title,
                discussion_author_id=discussion.user_id,
                comment_id=comment.id,
                replying_user_id=user.id,
                replying_username=user.username,
                challenge_id=discussion.challenge_id,
                parent_comment_id=data.parent_comment_id,
                parent_author_id=parent_uid,
            )
        except Exception:
            pass

        return cls.format_comment_response(comment, user)

    @classmethod
    def list_comments(
        cls,
        db: Session,
        discussion_id: UUID,
        user: Optional[User] = None,
        page: int = 1,
        limit: int = 20,
    ) -> CommentListResponse:
        """Retrieves paginated comments for a discussion with chronological order."""
        discussion = db.query(Discussion).filter(Discussion.id == discussion_id).first()
        if not discussion:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discussion not found.")

        cls.check_challenge_access(db, discussion.challenge, user)

        query = db.query(DiscussionComment).filter(DiscussionComment.discussion_id == discussion_id)
        total = query.count()

        offset = (page - 1) * limit
        items = query.order_by(asc(DiscussionComment.created_at)).offset(offset).limit(limit).all()

        formatted_items = [
            CommentResponse(**cls.format_comment_response(c, user))
            for c in items
        ]

        return CommentListResponse(
            items=formatted_items,
            total=total,
            page=page,
            limit=limit,
        )

    @classmethod
    def update_comment(
        cls,
        db: Session,
        comment_id: UUID,
        user: User,
        data: CommentUpdate
    ) -> Dict[str, Any]:
        """Updates a comment, enforcing ownership and lock constraints."""
        comment = db.query(DiscussionComment).filter(DiscussionComment.id == comment_id).first()
        if not comment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found.")

        is_admin_or_mod = user.role in (UserRole.ADMIN, UserRole.MODERATOR)
        if comment.user_id != user.id and not is_admin_or_mod:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to modify this comment."
            )

        if comment.discussion.is_locked and not is_admin_or_mod:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Discussion is locked and comments cannot be modified."
            )

        if comment.is_deleted and not is_admin_or_mod:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Deleted comments cannot be modified."
            )

        if data.content is not None:
            content = data.content.strip()
            if len(content) < 1:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Comment content cannot be empty.")
            cls._check_flag_leak(content, comment.discussion.challenge)
            comment.content = sanitize_content(content)

        if data.contains_spoiler is not None:
            comment.contains_spoiler = data.contains_spoiler

        db.commit()
        db.refresh(comment)
        return cls.format_comment_response(comment, user)

    @classmethod
    def delete_comment(cls, db: Session, comment_id: UUID, user: User) -> Dict[str, Any]:
        """Soft-deletes a comment preserving child thread structures."""
        comment = db.query(DiscussionComment).filter(DiscussionComment.id == comment_id).first()
        if not comment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found.")

        is_admin_or_mod = user.role in (UserRole.ADMIN, UserRole.MODERATOR)
        if comment.user_id != user.id and not is_admin_or_mod:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to delete this comment."
            )

        comment.is_deleted = True
        db.commit()
        return {
            "message": "Comment deleted successfully.",
            "comment_id": str(comment_id),
            "is_deleted": True,
        }
