import math
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc

from app.models.user import User
from app.models.solve import Solve
from app.models.challenge import Challenge
from app.models.category import Category
from app.schemas.leaderboard import LeaderboardEntry, LeaderboardResponse, UserRankResponse


class LeaderboardService:
    """Authoritative database-backed leaderboard and ranking service.
    
    Uses verified solves as the sole source of truth with deterministic tie-breaking.
    Modular design ready for future team leaderboard extensions.
    """

    SUPPORTED_TIMEFRAMES = {"all_time", "today", "this_week", "this_month"}

    @classmethod
    def resolve_time_cutoff(cls, time_frame: Optional[str]) -> Optional[datetime]:
        """Resolves UTC start timestamp for the selected time window."""
        if not time_frame or time_frame == "all_time":
            return None
        time_frame = time_frame.strip().lower()
        now = datetime.now(timezone.utc)
        if time_frame == "today":
            return now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif time_frame == "this_week":
            start_of_week = now - timedelta(days=now.weekday())
            return start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
        elif time_frame == "this_month":
            return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            raise ValueError(
                f"Invalid time_frame '{time_frame}'. Supported: all_time, today, this_week, this_month"
            )

    @classmethod
    def resolve_category(cls, db: Session, category_name: Optional[str]) -> Optional[Category]:
        """Validates category name case-insensitively and returns Category object."""
        if not category_name:
            return None
        cat = db.query(Category).filter(
            func.lower(Category.name) == category_name.strip().lower()
        ).first()
        if not cat:
            raise ValueError(f"Category '{category_name}' not found")
        return cat

    @classmethod
    def _build_individual_query(
        cls,
        db: Session,
        college_name: Optional[str] = None,
        category_id: Optional[UUID] = None,
        time_cutoff: Optional[datetime] = None,
    ):
        """Constructs base aggregation query for individual solvers."""
        query = db.query(
            User.id.label("user_id"),
            User.username.label("username"),
            User.college.label("college"),
            func.sum(Solve.points_awarded).label("total_points"),
            func.count(Solve.id).label("solved_count"),
            func.max(Solve.created_at).label("last_solve_time"),
        ).join(Solve, Solve.user_id == User.id)\
         .join(Challenge, Challenge.id == Solve.challenge_id)\
         .filter(User.is_active == True, Solve.event_id == None)

        if college_name:
            query = query.filter(func.lower(User.college) == college_name.strip().lower())

        if category_id:
            query = query.filter(Challenge.category_id == category_id)

        if time_cutoff:
            query = query.filter(Solve.created_at >= time_cutoff)

        query = query.group_by(User.id, User.username, User.college)
        query = query.order_by(
            desc("total_points"),
            asc("last_solve_time"),
            asc(User.id)
        )
        return query

    @classmethod
    def get_global_leaderboard(
        cls,
        db: Session,
        category_name: Optional[str] = None,
        time_frame: Optional[str] = "all_time",
        page: int = 1,
        page_size: int = 20,
    ) -> LeaderboardResponse:
        """Retrieves paginated global leaderboard with deterministic ranking."""
        time_cutoff = cls.resolve_time_cutoff(time_frame)
        category_obj = cls.resolve_category(db, category_name)
        cat_id = category_obj.id if category_obj else None

        base_query = cls._build_individual_query(
            db=db,
            college_name=None,
            category_id=cat_id,
            time_cutoff=time_cutoff
        )

        subquery = base_query.order_by(None).subquery()
        total_entries = db.query(func.count()).select_from(subquery).scalar() or 0
        total_pages = math.ceil(total_entries / page_size) if total_entries > 0 else 0

        offset = (page - 1) * page_size
        rows = base_query.offset(offset).limit(page_size).all()

        items = [
            LeaderboardEntry(
                rank=offset + idx + 1,
                user_id=row.user_id,
                username=row.username,
                college=row.college,
                total_points=int(row.total_points or 0),
                solved_count=int(row.solved_count or 0),
            )
            for idx, row in enumerate(rows)
        ]

        return LeaderboardResponse(
            page=page,
            page_size=page_size,
            total_entries=total_entries,
            total_pages=total_pages,
            items=items,
        )

    @classmethod
    def get_college_leaderboard(
        cls,
        db: Session,
        college_name: str,
        category_name: Optional[str] = None,
        time_frame: Optional[str] = "all_time",
        page: int = 1,
        page_size: int = 20,
    ) -> LeaderboardResponse:
        """Retrieves paginated college leaderboard filtered by specific college."""
        if not college_name or not college_name.strip():
            raise ValueError("College name is required for college leaderboard")

        time_cutoff = cls.resolve_time_cutoff(time_frame)
        category_obj = cls.resolve_category(db, category_name)
        cat_id = category_obj.id if category_obj else None

        base_query = cls._build_individual_query(
            db=db,
            college_name=college_name,
            category_id=cat_id,
            time_cutoff=time_cutoff
        )

        subquery = base_query.order_by(None).subquery()
        total_entries = db.query(func.count()).select_from(subquery).scalar() or 0
        total_pages = math.ceil(total_entries / page_size) if total_entries > 0 else 0

        offset = (page - 1) * page_size
        rows = base_query.offset(offset).limit(page_size).all()

        items = [
            LeaderboardEntry(
                rank=offset + idx + 1,
                user_id=row.user_id,
                username=row.username,
                college=row.college,
                total_points=int(row.total_points or 0),
                solved_count=int(row.solved_count or 0),
            )
            for idx, row in enumerate(rows)
        ]

        return LeaderboardResponse(
            page=page,
            page_size=page_size,
            total_entries=total_entries,
            total_pages=total_pages,
            items=items,
        )

    @classmethod
    def get_user_rank(cls, db: Session, user: User) -> UserRankResponse:
        """Calculates authoritative global and college ranks for the given user."""
        # 1. Total score and solves count
        total_points = db.query(func.coalesce(func.sum(Solve.points_awarded), 0))\
            .filter(Solve.user_id == user.id)\
            .scalar() or 0

        solved_count = db.query(func.count(Solve.id))\
            .filter(Solve.user_id == user.id)\
            .scalar() or 0

        # If user has no solves, ranks are None
        if solved_count == 0:
            return UserRankResponse(
                user_id=user.id,
                username=user.username,
                college=user.college,
                total_points=0,
                solved_count=0,
                global_rank=None,
                college_rank=None,
            )

        # 2. Global Rank using Window function
        global_window = db.query(
            User.id.label("user_id"),
            func.row_number().over(
                order_by=[
                    desc(func.sum(Solve.points_awarded)),
                    asc(func.max(Solve.created_at)),
                    asc(User.id),
                ]
            ).label("rank"),
        ).join(Solve, Solve.user_id == User.id)\
         .filter(User.is_active == True)\
         .group_by(User.id).subquery()

        global_rank_row = db.query(global_window.c.rank)\
            .filter(global_window.c.user_id == user.id)\
            .first()
        global_rank = int(global_rank_row[0]) if global_rank_row else None

        # 3. College Rank (if user has a registered college)
        college_rank = None
        if user.college and user.college.strip():
            college_window = db.query(
                User.id.label("user_id"),
                func.row_number().over(
                    order_by=[
                        desc(func.sum(Solve.points_awarded)),
                        asc(func.max(Solve.created_at)),
                        asc(User.id),
                    ]
                ).label("rank"),
            ).join(Solve, Solve.user_id == User.id)\
             .filter(
                 User.is_active == True,
                 func.lower(User.college) == user.college.strip().lower()
             )\
             .group_by(User.id).subquery()

            college_rank_row = db.query(college_window.c.rank)\
                .filter(college_window.c.user_id == user.id)\
                .first()
            college_rank = int(college_rank_row[0]) if college_rank_row else None

        return UserRankResponse(
            user_id=user.id,
            username=user.username,
            college=user.college,
            total_points=int(total_points),
            solved_count=int(solved_count),
            global_rank=global_rank,
            college_rank=college_rank,
        )
