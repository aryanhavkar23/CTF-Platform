import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple, Union
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status

from app.models.badge import Badge, UserBadge, CriteriaType
from app.models.user import User
from app.models.solve import Solve
from app.models.challenge import Challenge
from app.models.team import TeamMember
from app.models.event_registration import EventRegistration
from app.models.base import utc_now
from app.schemas.badge import BadgeCreate, BadgeUpdate
from app.services.scoring_service import ScoringService
from app.services.streak_service import StreakService

logger = logging.getLogger("ctf.badge_service")


class BadgeService:
    """Authoritative business logic for badge definitions, evaluation, and user achievements."""

    # -------------------------------------------------------------------------
    # Admin Badge Management
    # -------------------------------------------------------------------------

    @classmethod
    def create_badge(cls, db: Session, data: BadgeCreate) -> Badge:
        """Admin creates a new badge definition."""
        existing = db.query(Badge).filter(Badge.slug == data.slug).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Badge with slug '{data.slug}' already exists."
            )

        badge = Badge(
            name=data.name.strip(),
            slug=data.slug.strip().lower(),
            description=data.description.strip(),
            icon=data.icon.strip(),
            criteria_type=data.criteria_type.strip().lower(),
            criteria_value=data.criteria_value,
            is_active=data.is_active,
        )
        db.add(badge)
        db.commit()
        db.refresh(badge)
        return badge

    @classmethod
    def update_badge(cls, db: Session, badge_id: UUID, data: BadgeUpdate) -> Badge:
        """Admin updates an existing badge definition."""
        badge = db.query(Badge).filter(Badge.id == badge_id).first()
        if not badge:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Badge not found."
            )

        if data.slug is not None and data.slug.strip().lower() != badge.slug:
            new_slug = data.slug.strip().lower()
            conflict = db.query(Badge).filter(Badge.slug == new_slug, Badge.id != badge.id).first()
            if conflict:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Badge with slug '{new_slug}' already exists."
                )
            badge.slug = new_slug

        if data.name is not None:
            badge.name = data.name.strip()
        if data.description is not None:
            badge.description = data.description.strip()
        if data.icon is not None:
            badge.icon = data.icon.strip()
        if data.criteria_type is not None:
            badge.criteria_type = data.criteria_type.strip().lower()
        if data.criteria_value is not None:
            badge.criteria_value = data.criteria_value
        if data.is_active is not None:
            badge.is_active = data.is_active

        db.commit()
        db.refresh(badge)
        return badge

    @classmethod
    def delete_or_deactivate_badge(cls, db: Session, badge_id: UUID) -> Tuple[bool, str]:
        """
        Deactivates badge if users have already earned it to preserve history;
        hard deletes if never awarded.
        """
        badge = db.query(Badge).filter(Badge.id == badge_id).first()
        if not badge:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Badge not found."
            )

        awarded_count = db.query(UserBadge).filter(UserBadge.badge_id == badge.id).count()
        if awarded_count > 0:
            badge.is_active = False
            db.commit()
            return False, "Badge has already been earned by users; deactivated instead of deleted to protect user history."
        else:
            db.delete(badge)
            db.commit()
            return True, "Badge successfully deleted."

    @classmethod
    def get_badge(cls, db: Session, badge_id_or_slug: Union[UUID, str]) -> Badge:
        """Retrieves badge by UUID or slug."""
        if isinstance(badge_id_or_slug, UUID):
            badge = db.query(Badge).filter(Badge.id == badge_id_or_slug).first()
        else:
            # Try UUID parsing first
            try:
                parsed_uuid = UUID(str(badge_id_or_slug))
                badge = db.query(Badge).filter(Badge.id == parsed_uuid).first()
            except ValueError:
                badge = db.query(Badge).filter(Badge.slug == str(badge_id_or_slug).lower()).first()

        if not badge:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Badge not found."
            )
        return badge

    @classmethod
    def list_badges(cls, db: Session, include_inactive: bool = False) -> List[Badge]:
        """Lists badges, optionally including inactive definitions for admins."""
        query = db.query(Badge)
        if not include_inactive:
            query = query.filter(Badge.is_active == True)
        return query.order_by(Badge.criteria_type.asc(), Badge.criteria_value.asc()).all()

    @classmethod
    def get_badge_users(cls, db: Session, badge_id: UUID) -> List[Dict[str, Any]]:
        """Lists users who have earned this badge without leaking private fields."""
        badge = cls.get_badge(db, badge_id)
        rows = (
            db.query(UserBadge, User)
            .join(User, User.id == UserBadge.user_id)
            .filter(UserBadge.badge_id == badge.id)
            .order_by(UserBadge.awarded_at.desc())
            .all()
        )
        return [
            {
                "user_id": user.id,
                "username": user.username,
                "name": user.name or user.username,
                "college": user.college,
                "avatar_url": user.avatar_url,
                "awarded_at": ub.awarded_at,
            }
            for ub, user in rows
        ]

    @classmethod
    def get_badge_stats(cls, db: Session, badge_id: UUID) -> Dict[str, Any]:
        """Returns award count statistics for a badge."""
        badge = cls.get_badge(db, badge_id)
        total_awarded = db.query(func.count(UserBadge.id)).filter(UserBadge.badge_id == badge.id).scalar() or 0
        return {
            "badge_id": badge.id,
            "name": badge.name,
            "slug": badge.slug,
            "total_users_awarded": int(total_awarded),
        }

    # -------------------------------------------------------------------------
    # Authoritative Evaluation & Auto-Award Engine
    # -------------------------------------------------------------------------

    @classmethod
    def evaluate_and_award_badges(cls, db: Session, user_id: UUID) -> List[Badge]:
        """
        Evaluates all active badges for a given user against authoritative metrics.
        Idempotently inserts newly qualified badges.
        Returns the list of newly awarded badges.
        """
        # 1. Fetch active badges
        active_badges = db.query(Badge).filter(Badge.is_active == True).all()
        if not active_badges:
            return []

        # 2. Fetch badges already earned by user
        earned_badge_ids = {
            row[0]
            for row in db.query(UserBadge.badge_id).filter(UserBadge.user_id == user_id).all()
        }

        unearned_badges = [b for b in active_badges if b.id not in earned_badge_ids]
        if not unearned_badges:
            return []

        # 3. Gather authoritative metrics from Phase 1-9 services
        solves_count = ScoringService.get_user_solve_count(db, user_id)
        total_points = ScoringService.get_user_score(db, user_id)
        streak_info = StreakService.get_user_streak(db, user_id)
        max_streak = max(streak_info.get("current_streak", 0), streak_info.get("longest_streak", 0))

        # Distinct categories solved
        distinct_categories_count = (
            db.query(func.count(func.distinct(Challenge.category_id)))
            .join(Solve, Solve.challenge_id == Challenge.id)
            .filter(Solve.user_id == user_id)
            .scalar()
            or 0
        )

        # Events participated (individual or team)
        team_ids_tuples = (
            db.query(TeamMember.team_id)
            .filter(TeamMember.user_id == user_id, TeamMember.is_active == True)
            .all()
        )
        team_ids = [t[0] for t in team_ids_tuples]

        event_reg_query = db.query(func.count(func.distinct(EventRegistration.event_id))).filter(
            EventRegistration.is_active == True
        )
        if team_ids:
            event_reg_query = event_reg_query.filter(
                or_(
                    EventRegistration.user_id == user_id,
                    EventRegistration.team_id.in_(team_ids)
                )
            )
        else:
            event_reg_query = event_reg_query.filter(EventRegistration.user_id == user_id)
        events_participated = int(event_reg_query.scalar() or 0)

        newly_awarded: List[Badge] = []
        now_utc = utc_now()

        # 4. Check eligibility for each unearned badge
        for badge in unearned_badges:
            c_type = badge.criteria_type
            c_val = badge.criteria_value
            is_qualified = False

            if c_type == CriteriaType.FIRST_SOLVE.value:
                is_qualified = (solves_count >= 1)
            elif c_type == CriteriaType.SOLVE_COUNT.value:
                is_qualified = (solves_count >= c_val)
            elif c_type == CriteriaType.POINTS_REACHED.value:
                is_qualified = (total_points >= c_val)
            elif c_type == CriteriaType.STREAK_DAYS.value:
                is_qualified = (max_streak >= c_val)
            elif c_type == CriteriaType.CATEGORY_SOLVES.value:
                is_qualified = (distinct_categories_count >= c_val)
            elif c_type == CriteriaType.EVENT_PARTICIPATION.value:
                is_qualified = (events_participated >= c_val)

            if is_qualified:
                user_badge = UserBadge(
                    user_id=user_id,
                    badge_id=badge.id,
                    awarded_at=now_utc,
                )
                try:
                    db.add(user_badge)
                    db.commit()
                    newly_awarded.append(badge)

                    # Trigger in-app notification (isolated so it cannot break badge awarding)
                    try:
                        from app.services.notification_service import NotificationService
                        NotificationService.notify_badge_awarded(
                            db=db,
                            user_id=user_id,
                            badge_id=badge.id,
                            badge_name=badge.name,
                            badge_slug=badge.slug,
                        )
                    except Exception:
                        pass
                except IntegrityError:
                    # Race condition caught by unique constraint
                    db.rollback()
                except Exception as e:
                    db.rollback()
                    logger.warning(f"Error awarding badge {badge.slug} to user {user_id}: {e}")

        return newly_awarded

    # -------------------------------------------------------------------------
    # User Progress & Showcase Queries
    # -------------------------------------------------------------------------

    @classmethod
    def get_user_badges(cls, db: Session, user_id: UUID) -> List[Dict[str, Any]]:
        """Returns unlocked badges for a user sorted by award date newest first."""
        rows = (
            db.query(UserBadge, Badge)
            .join(Badge, Badge.id == UserBadge.badge_id)
            .filter(UserBadge.user_id == user_id)
            .order_by(UserBadge.awarded_at.desc())
            .all()
        )
        return [
            {
                "badge_id": badge.id,
                "name": badge.name,
                "slug": badge.slug,
                "description": badge.description,
                "icon": badge.icon,
                "awarded_at": ub.awarded_at,
            }
            for ub, badge in rows
        ]

    @classmethod
    def get_user_badge_summary(cls, db: Session, user_id: UUID) -> Tuple[int, List[Dict[str, Any]]]:
        """Returns (total_badges_count, recent_3_badges) for profile integration."""
        badges = cls.get_user_badges(db, user_id)
        return len(badges), badges[:3]

    @classmethod
    def get_user_badge_progress(cls, db: Session, user_id: UUID) -> List[Dict[str, Any]]:
        """Calculates authoritative progress towards all active badges for the user."""
        active_badges = cls.list_badges(db, include_inactive=False)
        earned_rows = db.query(UserBadge).filter(UserBadge.user_id == user_id).all()
        earned_dict = {ub.badge_id: ub.awarded_at for ub in earned_rows}

        # Authoritative metrics
        solves_count = ScoringService.get_user_solve_count(db, user_id)
        total_points = ScoringService.get_user_score(db, user_id)
        streak_info = StreakService.get_user_streak(db, user_id)
        max_streak = max(streak_info.get("current_streak", 0), streak_info.get("longest_streak", 0))

        distinct_categories_count = (
            db.query(func.count(func.distinct(Challenge.category_id)))
            .join(Solve, Solve.challenge_id == Challenge.id)
            .filter(Solve.user_id == user_id)
            .scalar()
            or 0
        )

        team_ids_tuples = (
            db.query(TeamMember.team_id)
            .filter(TeamMember.user_id == user_id, TeamMember.is_active == True)
            .all()
        )
        team_ids = [t[0] for t in team_ids_tuples]
        event_reg_query = db.query(func.count(func.distinct(EventRegistration.event_id))).filter(
            EventRegistration.is_active == True
        )
        if team_ids:
            event_reg_query = event_reg_query.filter(
                or_(
                    EventRegistration.user_id == user_id,
                    EventRegistration.team_id.in_(team_ids)
                )
            )
        else:
            event_reg_query = event_reg_query.filter(EventRegistration.user_id == user_id)
        events_participated = int(event_reg_query.scalar() or 0)

        progress_list = []
        for badge in active_badges:
            is_unlocked = badge.id in earned_dict
            c_type = badge.criteria_type
            req_val = badge.criteria_value

            if c_type == CriteriaType.FIRST_SOLVE.value:
                curr_val = min(solves_count, 1)
                req_val = 1
            elif c_type == CriteriaType.SOLVE_COUNT.value:
                curr_val = solves_count
            elif c_type == CriteriaType.POINTS_REACHED.value:
                curr_val = total_points
            elif c_type == CriteriaType.STREAK_DAYS.value:
                curr_val = max_streak
            elif c_type == CriteriaType.CATEGORY_SOLVES.value:
                curr_val = distinct_categories_count
            elif c_type == CriteriaType.EVENT_PARTICIPATION.value:
                curr_val = events_participated
            else:
                curr_val = 0

            if is_unlocked:
                pct = 100.0
                curr_val = max(curr_val, req_val)
            else:
                pct = min(100.0, round((curr_val / req_val) * 100.0, 1)) if req_val > 0 else 100.0

            progress_list.append({
                "badge_id": badge.id,
                "name": badge.name,
                "slug": badge.slug,
                "description": badge.description,
                "icon": badge.icon,
                "criteria_type": badge.criteria_type,
                "current_value": curr_val,
                "required_value": req_val,
                "progress_percentage": pct,
                "is_unlocked": is_unlocked,
            })

        # Sort: unlocked first, then by progress percentage descending
        progress_list.sort(key=lambda x: (not x["is_unlocked"], -x["progress_percentage"]))
        return progress_list

    @classmethod
    def get_single_badge_progress(cls, db: Session, user_id: UUID, badge_id: UUID) -> Dict[str, Any]:
        """Calculates progress for a single specific badge."""
        badge = cls.get_badge(db, badge_id)
        all_progress = cls.get_user_badge_progress(db, user_id)
        for item in all_progress:
            if item["badge_id"] == badge.id:
                return item
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Badge not found.")
