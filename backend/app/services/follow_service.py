import logging
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.follow import UserFollow
from app.models.user import User
from app.services.scoring_service import ScoringService

logger = logging.getLogger(__name__)


class FollowService:
    """Business logic for LeetCode-style following and followers network."""

    @classmethod
    def get_follow_counts(cls, db: Session, user_id: UUID) -> Tuple[int, int]:
        """Returns (followers_count, following_count) for a user."""
        followers_count = db.query(func.count(UserFollow.id)).filter(
            UserFollow.following_id == user_id
        ).scalar() or 0

        following_count = db.query(func.count(UserFollow.id)).filter(
            UserFollow.follower_id == user_id
        ).scalar() or 0

        return int(followers_count), int(following_count)

    @classmethod
    def is_following(cls, db: Session, follower_id: UUID, following_id: UUID) -> bool:
        """Returns True if follower_id follows following_id."""
        if follower_id == following_id:
            return False
        return db.query(UserFollow).filter(
            UserFollow.follower_id == follower_id,
            UserFollow.following_id == following_id
        ).first() is not None

    @classmethod
    def toggle_follow(
        cls,
        db: Session,
        follower_id: UUID,
        following_id: UUID
    ) -> Dict[str, Any]:
        """Toggles follow status between two operatives (like LeetCode)."""
        if follower_id == following_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Operatives cannot follow themselves."
            )

        target_user = db.query(User).filter(User.id == following_id).first()
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Operative profile not found."
            )

        follower_user = db.query(User).filter(User.id == follower_id).first()
        if not follower_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Authenticated user not found."
            )

        existing = db.query(UserFollow).filter(
            UserFollow.follower_id == follower_id,
            UserFollow.following_id == following_id
        ).first()

        if existing:
            # Unfollow
            db.delete(existing)
            db.commit()
            is_following = False
        else:
            # Follow
            new_follow = UserFollow(follower_id=follower_id, following_id=following_id)
            db.add(new_follow)
            db.commit()
            is_following = True

            # In-app notification to target user
            try:
                from app.services.notification_service import NotificationService
                NotificationService.create_notification(
                    db=db,
                    user_id=following_id,
                    type="user_follow",
                    title="New Operative Follower",
                    message=f"@{follower_user.username} started following your tactical research and solves.",
                    data={"follower_id": str(follower_id), "username": follower_user.username},
                    event_key=f"user_follow_{follower_id}_{following_id}"
                )
            except Exception:
                pass

        followers_cnt, following_cnt = cls.get_follow_counts(db, following_id)
        return {
            "user_id": following_id,
            "is_following": is_following,
            "followers_count": followers_cnt,
            "following_count": following_cnt,
        }

    @classmethod
    def unfollow_user(cls, db: Session, follower_id: UUID, following_id: UUID) -> Dict[str, Any]:
        """Explicitly unfollow a user."""
        existing = db.query(UserFollow).filter(
            UserFollow.follower_id == follower_id,
            UserFollow.following_id == following_id
        ).first()
        if existing:
            db.delete(existing)
            db.commit()

        followers_cnt, following_cnt = cls.get_follow_counts(db, following_id)
        return {
            "user_id": following_id,
            "is_following": False,
            "followers_count": followers_cnt,
            "following_count": following_cnt,
        }

    @classmethod
    def get_followers(
        cls,
        db: Session,
        target_user_id: UUID,
        current_user_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """Lists users who follow target_user_id."""
        rows = (
            db.query(UserFollow, User)
            .join(User, User.id == UserFollow.follower_id)
            .filter(UserFollow.following_id == target_user_id)
            .order_by(UserFollow.created_at.desc())
            .all()
        )

        my_following_set = set()
        if current_user_id:
            my_following_tuples = db.query(UserFollow.following_id).filter(
                UserFollow.follower_id == current_user_id
            ).all()
            my_following_set = {t[0] for t in my_following_tuples}

        results = []
        for uf, u in rows:
            score = ScoringService.get_user_score(db, u.id)
            solves = ScoringService.get_user_solve_count(db, u.id)
            results.append({
                "id": u.id,
                "username": u.username,
                "name": u.name or u.username,
                "college": u.college,
                "avatar_url": u.avatar_url,
                "total_points": score,
                "solves_count": solves,
                "is_following": u.id in my_following_set,
                "followed_at": uf.created_at,
            })
        return results

    @classmethod
    def get_following(
        cls,
        db: Session,
        target_user_id: UUID,
        current_user_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """Lists users whom target_user_id is following."""
        rows = (
            db.query(UserFollow, User)
            .join(User, User.id == UserFollow.following_id)
            .filter(UserFollow.follower_id == target_user_id)
            .order_by(UserFollow.created_at.desc())
            .all()
        )

        my_following_set = set()
        if current_user_id:
            my_following_tuples = db.query(UserFollow.following_id).filter(
                UserFollow.follower_id == current_user_id
            ).all()
            my_following_set = {t[0] for t in my_following_tuples}

        results = []
        for uf, u in rows:
            score = ScoringService.get_user_score(db, u.id)
            solves = ScoringService.get_user_solve_count(db, u.id)
            results.append({
                "id": u.id,
                "username": u.username,
                "name": u.name or u.username,
                "college": u.college,
                "avatar_url": u.avatar_url,
                "total_points": score,
                "solves_count": solves,
                "is_following": u.id in my_following_set,
                "followed_at": uf.created_at,
            })
        return results
