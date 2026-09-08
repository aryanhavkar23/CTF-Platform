from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_

from app.models.user import User
from app.models.solve import Solve
from app.models.challenge import Challenge
from app.models.category import Category
from app.models.team import Team, TeamMember
from app.models.event_registration import EventRegistration
from app.schemas.profile import ProfileUpdate
from app.services.scoring_service import ScoringService
from app.services.leaderboard_service import LeaderboardService
from app.services.streak_service import StreakService


class ProfileService:
    """Service handling profile retrieval, customization, solved history, and category analytics."""

    @staticmethod
    def get_profile(db: Session, user: User, is_self: bool = False) -> Dict[str, Any]:
        """Assembles authoritative profile stats for a user."""
        total_points = ScoringService.get_user_score(db, user.id)
        challenges_solved = ScoringService.get_user_solve_count(db, user.id)
        rank_info = LeaderboardService.get_user_rank(db, user)
        streak_info = StreakService.get_user_streak(db, user.id)

        # Compute events participated
        team_ids_tuples = db.query(TeamMember.team_id)\
            .filter(TeamMember.user_id == user.id, TeamMember.is_active == True)\
            .all()
        team_ids = [t[0] for t in team_ids_tuples]

        event_reg_query = db.query(func.count(func.distinct(EventRegistration.event_id)))\
            .filter(EventRegistration.is_active == True)
        if team_ids:
            event_reg_query = event_reg_query.filter(
                or_(
                    EventRegistration.user_id == user.id,
                    EventRegistration.team_id.in_(team_ids)
                )
            )
        else:
            event_reg_query = event_reg_query.filter(EventRegistration.user_id == user.id)
        events_participated = int(event_reg_query.scalar() or 0)

        # Compute current active team
        current_team_row = db.query(Team.name)\
            .join(TeamMember, TeamMember.team_id == Team.id)\
            .filter(TeamMember.user_id == user.id, TeamMember.is_active == True, Team.is_active == True)\
            .first()
        current_team_name = current_team_row[0] if current_team_row else None

        # Compute badges summary
        from app.services.badge_service import BadgeService
        badges_count, recent_badges = BadgeService.get_user_badge_summary(db, user.id)

        profile_data = {
            "id": user.id,
            "username": user.username,
            "name": user.name or user.username,
            "college": user.college,
            "bio": user.bio,
            "avatar_url": user.avatar_url,
            "created_at": user.created_at,
            "total_points": total_points,
            "global_rank": rank_info.global_rank,
            "college_rank": rank_info.college_rank,
            "challenges_solved": challenges_solved,
            "current_streak": streak_info["current_streak"],
            "longest_streak": streak_info["longest_streak"],
            "events_participated": events_participated,
            "current_team": current_team_name,
            "badges_count": badges_count,
            "recent_badges": recent_badges,
        }

        if is_self:
            profile_data["email"] = user.email
            profile_data["role"] = user.role.value if hasattr(user.role, "value") else str(user.role)
            profile_data["is_verified"] = user.is_verified

        return profile_data

    @staticmethod
    def update_profile(db: Session, user: User, update_data: ProfileUpdate) -> User:
        """Applies validated and sanitized updates to the user's profile."""
        if update_data.name is not None:
            user.name = update_data.name
        if update_data.college is not None:
            user.college = update_data.college
        if update_data.bio is not None:
            user.bio = update_data.bio
        if update_data.avatar_url is not None:
            user.avatar_url = update_data.avatar_url

        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def get_user_solved_challenges(db: Session, user_id: UUID) -> List[Dict[str, Any]]:
        """Retrieves verified solve history for the given user without exposing flags or hidden metadata."""
        rows = db.query(Solve, Challenge, Category)\
            .join(Challenge, Challenge.id == Solve.challenge_id)\
            .join(Category, Category.id == Challenge.category_id)\
            .filter(Solve.user_id == user_id, Challenge.is_active == True)\
            .order_by(Solve.created_at.desc())\
            .all()

        results = []
        for solve, challenge, category in rows:
            results.append({
                "challenge_id": challenge.id,
                "challenge_title": challenge.title,
                "category": category.name,
                "difficulty": challenge.difficulty.value if hasattr(challenge.difficulty, "value") else str(challenge.difficulty),
                "points_awarded": solve.points_awarded,
                "solved_at": solve.created_at,
            })
        return results

    @staticmethod
    def get_user_category_stats(db: Session, user_id: UUID) -> List[Dict[str, Any]]:
        """Calculates solved challenge count and points earned broken down by category."""
        # Query all active categories to ensure complete distribution
        all_categories = db.query(Category).order_by(Category.name.asc()).all()

        solve_aggs = db.query(
            Challenge.category_id,
            func.count(Solve.id).label("solved_count"),
            func.sum(Solve.points_awarded).label("points_earned"),
        ).join(Solve, Solve.challenge_id == Challenge.id)\
         .filter(Solve.user_id == user_id)\
         .group_by(Challenge.category_id)\
         .all()

        stats_map = {
            cat_id: {"solved_count": int(cnt or 0), "points_earned": int(pts or 0)}
            for cat_id, cnt, pts in solve_aggs
        }

        category_stats = []
        for cat in all_categories:
            agg = stats_map.get(cat.id, {"solved_count": 0, "points_earned": 0})
            category_stats.append({
                "category": cat.name,
                "solved_count": agg["solved_count"],
                "points_earned": agg["points_earned"],
            })

        return category_stats
