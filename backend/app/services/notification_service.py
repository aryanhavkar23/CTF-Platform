import logging
from typing import Any, Dict, Iterable, List, Optional, Tuple
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.base import utc_now
from app.models.notification import Notification, NotificationType

logger = logging.getLogger(__name__)


class NotificationService:
    """Authoritative service for creating, retrieving, and managing in-app user notifications."""

    # -------------------------------------------------------------------------
    # Core CRUD Operations
    # -------------------------------------------------------------------------

    @classmethod
    def create_notification(
        cls,
        db: Session,
        user_id: UUID,
        type: str,
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        event_key: Optional[str] = None,
    ) -> Optional[Notification]:
        """
        Creates an in-app notification for a user.
        If event_key is provided, deduplicates to prevent duplicate notification records.
        """
        if event_key:
            existing = (
                db.query(Notification)
                .filter(Notification.user_id == user_id, Notification.event_key == event_key)
                .first()
            )
            if existing:
                return existing

        notification = Notification(
            user_id=user_id,
            type=type,
            title=title.strip(),
            message=message.strip(),
            data=data,
            event_key=event_key,
            is_read=False,
        )
        try:
            db.add(notification)
            db.commit()
            db.refresh(notification)
            return notification
        except IntegrityError:
            db.rollback()
            return None
        except Exception as e:
            db.rollback()
            logger.warning(f"Failed to create notification for user {user_id}: {e}")
            return None

    @classmethod
    def create_batch_notifications(
        cls,
        db: Session,
        user_ids: Iterable[UUID],
        type: str,
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        event_key_prefix: Optional[str] = None,
    ) -> List[Notification]:
        """Creates notifications for multiple users with deduplication."""
        created: List[Notification] = []
        clean_title = title.strip()
        clean_msg = message.strip()

        for u_id in set(user_ids):
            ev_key = f"{event_key_prefix}:{u_id}" if event_key_prefix else None
            notif = cls.create_notification(
                db=db,
                user_id=u_id,
                type=type,
                title=clean_title,
                message=clean_msg,
                data=data,
                event_key=ev_key,
            )
            if notif:
                created.append(notif)
        return created

    @classmethod
    def get_user_notifications(
        cls,
        db: Session,
        user_id: UUID,
        page: int = 1,
        limit: int = 20,
        unread_only: bool = False,
    ) -> Tuple[List[Notification], int, int]:
        """
        Retrieves paginated notifications for a user, sorted newest first.
        Returns: (items, total_count, unread_count)
        """
        page = max(1, page)
        limit = min(max(1, limit), 100)

        query = db.query(Notification).filter(Notification.user_id == user_id)
        if unread_only:
            query = query.filter(Notification.is_read == False)

        total_count = query.count()
        unread_count = cls.count_unread_notifications(db, user_id)

        items = (
            query.order_by(Notification.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
            .all()
        )

        return items, total_count, unread_count

    @classmethod
    def count_unread_notifications(cls, db: Session, user_id: UUID) -> int:
        """Returns the total number of unread notifications for a user."""
        return (
            db.query(func.count(Notification.id))
            .filter(Notification.user_id == user_id, Notification.is_read == False)
            .scalar()
            or 0
        )

    @classmethod
    def mark_notification_as_read(
        cls,
        db: Session,
        notification_id: UUID,
        user_id: UUID,
    ) -> Notification:
        """
        Marks a specific notification as read.
        Validates ownership to prevent IDOR vulnerabilities.
        """
        notification = db.query(Notification).filter(Notification.id == notification_id).first()
        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found."
            )

        if notification.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to modify this notification."
            )

        if not notification.is_read:
            notification.is_read = True
            notification.read_at = utc_now()
            db.commit()
            db.refresh(notification)

        return notification

    @classmethod
    def mark_all_notifications_as_read(cls, db: Session, user_id: UUID) -> int:
        """Atomically marks all unread notifications for a user as read."""
        now = utc_now()
        marked = (
            db.query(Notification)
            .filter(Notification.user_id == user_id, Notification.is_read == False)
            .update(
                {Notification.is_read: True, Notification.read_at: now},
                synchronize_session=False,
            )
        )
        db.commit()
        return marked

    @classmethod
    def delete_notification(
        cls,
        db: Session,
        notification_id: UUID,
        user_id: UUID,
    ) -> bool:
        """
        Deletes a user's notification.
        Validates ownership to prevent IDOR attacks.
        """
        notification = db.query(Notification).filter(Notification.id == notification_id).first()
        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found."
            )

        if notification.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to delete this notification."
            )

        db.delete(notification)
        db.commit()
        return True

    # -------------------------------------------------------------------------
    # Automatic Trigger Integration Hooks
    # -------------------------------------------------------------------------

    @classmethod
    def notify_challenge_solved(
        cls,
        db: Session,
        user_id: UUID,
        challenge_title: str,
        challenge_id: UUID,
        points_awarded: int,
        event_id: Optional[UUID] = None,
    ) -> Optional[Notification]:
        """Triggered upon verified solve to notify user of solve and points awarded."""
        try:
            ev_key = f"challenge_solved:{user_id}:{challenge_id}"
            if event_id:
                ev_key = f"{ev_key}:{event_id}"

            return cls.create_notification(
                db=db,
                user_id=user_id,
                type=NotificationType.CHALLENGE_SOLVED.value,
                title="Challenge Solved",
                message=f"Congratulations! You solved {challenge_title} and earned {points_awarded} points.",
                data={
                    "challenge_id": str(challenge_id),
                    "points_awarded": points_awarded,
                    "event_id": str(event_id) if event_id else None,
                },
                event_key=ev_key,
            )
        except Exception as e:
            logger.warning(f"Error in notify_challenge_solved: {e}")
            return None

    @classmethod
    def notify_badge_awarded(
        cls,
        db: Session,
        user_id: UUID,
        badge_id: UUID,
        badge_name: str,
        badge_slug: str,
    ) -> Optional[Notification]:
        """Triggered upon badge award."""
        try:
            return cls.create_notification(
                db=db,
                user_id=user_id,
                type=NotificationType.BADGE_AWARDED.value,
                title="New Badge Unlocked",
                message=f"You earned the {badge_name} badge.",
                data={
                    "badge_id": str(badge_id),
                    "badge_name": badge_name,
                    "badge_slug": badge_slug,
                },
                event_key=f"badge_awarded:{user_id}:{badge_id}",
            )
        except Exception as e:
            logger.warning(f"Error in notify_badge_awarded: {e}")
            return None

    @classmethod
    def notify_team_member_added(
        cls,
        db: Session,
        team_id: UUID,
        team_name: str,
        target_user_id: UUID,
        added_by_username: str,
    ) -> Optional[Notification]:
        """Triggered when a member is added to a team by an owner/admin."""
        try:
            return cls.create_notification(
                db=db,
                user_id=target_user_id,
                type=NotificationType.TEAM_MEMBER_ADDED.value,
                title="Added to Team",
                message=f"You have been added to team '{team_name}' by {added_by_username}.",
                data={"team_id": str(team_id), "team_name": team_name, "added_by": added_by_username},
            )
        except Exception as e:
            logger.warning(f"Error in notify_team_member_added: {e}")
            return None

    @classmethod
    def notify_team_member_removed(
        cls,
        db: Session,
        team_id: UUID,
        team_name: str,
        target_user_id: UUID,
    ) -> Optional[Notification]:
        """Triggered when a member is removed from a team."""
        try:
            return cls.create_notification(
                db=db,
                user_id=target_user_id,
                type=NotificationType.TEAM_MEMBER_REMOVED.value,
                title="Removed from Team",
                message=f"You have been removed from team '{team_name}'.",
                data={"team_id": str(team_id), "team_name": team_name},
            )
        except Exception as e:
            logger.warning(f"Error in notify_team_member_removed: {e}")
            return None

    @classmethod
    def notify_team_owner_transferred(
        cls,
        db: Session,
        team_id: UUID,
        team_name: str,
        new_owner_id: UUID,
        old_owner_username: str,
    ) -> Optional[Notification]:
        """Triggered when team ownership is transferred."""
        try:
            return cls.create_notification(
                db=db,
                user_id=new_owner_id,
                type=NotificationType.TEAM_OWNER_TRANSFERRED.value,
                title="Team Ownership Transferred",
                message=f"You are now the owner of team '{team_name}' (transferred by {old_owner_username}).",
                data={"team_id": str(team_id), "team_name": team_name, "transferred_by": old_owner_username},
            )
        except Exception as e:
            logger.warning(f"Error in notify_team_owner_transferred: {e}")
            return None

    @classmethod
    def notify_event_registered(
        cls,
        db: Session,
        event_id: UUID,
        event_name: str,
        user_ids: List[UUID],
        is_team: bool = False,
        team_name: Optional[str] = None,
        team_id: Optional[UUID] = None,
    ) -> List[Notification]:
        """Triggered upon successful event registration."""
        created: List[Notification] = []
        try:
            for u_id in set(user_ids):
                if is_team and team_name:
                    title = "Team Event Registration Confirmed"
                    msg = f"Your team '{team_name}' successfully registered for {event_name}."
                    reg_data = {
                        "event_id": str(event_id),
                        "event_name": event_name,
                        "team_id": str(team_id),
                        "team_name": team_name,
                        "type": "team",
                    }
                else:
                    title = "Event Registration Confirmed"
                    msg = f"You successfully registered for {event_name}."
                    reg_data = {
                        "event_id": str(event_id),
                        "event_name": event_name,
                        "type": "individual",
                    }

                notif = cls.create_notification(
                    db=db,
                    user_id=u_id,
                    type=NotificationType.EVENT_REGISTERED.value,
                    title=title,
                    message=msg,
                    data=reg_data,
                    event_key=f"event_registered:{u_id}:{event_id}",
                )
                if notif:
                    created.append(notif)
        except Exception as e:
            logger.warning(f"Error in notify_event_registered: {e}")
        return created

    @classmethod
    def notify_event_lifecycle(
        cls,
        db: Session,
        event_id: UUID,
        event_name: str,
        participant_user_ids: List[UUID],
        lifecycle_type: NotificationType,
    ) -> List[Notification]:
        """Triggered when event lifecycle changes (started, ended, scoreboard frozen)."""
        titles = {
            NotificationType.EVENT_STARTED: "Event Started",
            NotificationType.EVENT_ENDED: "Event Ended",
            NotificationType.EVENT_SCOREBOARD_FROZEN: "Scoreboard Frozen",
        }
        messages = {
            NotificationType.EVENT_STARTED: f"The event '{event_name}' has officially started! Good luck.",
            NotificationType.EVENT_ENDED: f"The event '{event_name}' has ended. Thank you for participating!",
            NotificationType.EVENT_SCOREBOARD_FROZEN: f"The scoreboard for '{event_name}' has been frozen.",
        }

        title = titles.get(lifecycle_type, "Event Update")
        msg = messages.get(lifecycle_type, f"Event '{event_name}' status updated.")
        key_prefix = f"{lifecycle_type.value}:{event_id}"

        return cls.create_batch_notifications(
            db=db,
            user_ids=participant_user_ids,
            type=lifecycle_type.value,
            title=title,
            message=msg,
            data={"event_id": str(event_id), "event_name": event_name},
            event_key_prefix=key_prefix,
        )

    @classmethod
    def notify_discussion_reply(
        cls,
        db: Session,
        discussion_id: UUID,
        discussion_title: str,
        discussion_author_id: UUID,
        comment_id: UUID,
        replying_user_id: UUID,
        replying_username: str,
        challenge_id: UUID,
        parent_comment_id: Optional[UUID] = None,
        parent_author_id: Optional[UUID] = None,
    ) -> List[Notification]:
        """Triggered upon comment/reply creation, notifying discussion or comment author."""
        created: List[Notification] = []
        try:
            # 1. If replying to a specific comment and parent author is not replying user
            if parent_author_id and parent_author_id != replying_user_id:
                notif = cls.create_notification(
                    db=db,
                    user_id=parent_author_id,
                    type=NotificationType.DISCUSSION_REPLY.value,
                    title="New Reply to Your Comment",
                    message=f"{replying_username} replied to your comment on '{discussion_title}'.",
                    data={
                        "discussion_id": str(discussion_id),
                        "comment_id": str(comment_id),
                        "parent_comment_id": str(parent_comment_id),
                        "challenge_id": str(challenge_id),
                    },
                )
                if notif:
                    created.append(notif)

            # 2. Notify thread author if not the replying user and not already notified as parent author
            if (
                discussion_author_id != replying_user_id
                and discussion_author_id != parent_author_id
            ):
                notif = cls.create_notification(
                    db=db,
                    user_id=discussion_author_id,
                    type=NotificationType.DISCUSSION_REPLY.value,
                    title="New Reply to Your Discussion",
                    message=f"{replying_username} replied in your discussion '{discussion_title}'.",
                    data={
                        "discussion_id": str(discussion_id),
                        "comment_id": str(comment_id),
                        "challenge_id": str(challenge_id),
                    },
                )
                if notif:
                    created.append(notif)
        except Exception as e:
            logger.warning(f"Error in notify_discussion_reply: {e}")
        return created
