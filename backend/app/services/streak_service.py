from datetime import datetime, date, timedelta, timezone
from typing import Dict, Any, Optional, Set
from uuid import UUID
from sqlalchemy.orm import Session

from app.models.activity import UserActivity


class StreakService:
    """Authoritative streak computation engine based on distinct UTC calendar active days."""

    @staticmethod
    def get_user_streak(db: Session, user_id: UUID) -> Dict[str, Any]:
        """Calculates current streak, longest streak, and last active date.
        
        Rules:
        - Active day = at least one verified CTF action in user_activities on that UTC date.
        - Multiple activities on the same date count as 1 active day.
        - Current streak is preserved if active today OR active yesterday (allowing user
          to continue the streak today before UTC midnight).
        - If neither today nor yesterday has activity, current streak is 0.
        - Longest streak = maximum consecutive active days across user history.
        """
        records = db.query(UserActivity.created_at)\
            .filter(UserActivity.user_id == user_id)\
            .order_by(UserActivity.created_at.asc())\
            .all()

        if not records:
            return {
                "current_streak": 0,
                "longest_streak": 0,
                "last_active_date": None,
            }

        distinct_dates: Set[date] = set()
        for (created_at,) in records:
            if created_at is not None:
                if created_at.tzinfo is None:
                    d = created_at.date()
                else:
                    d = created_at.astimezone(timezone.utc).date()
                distinct_dates.add(d)

        sorted_dates = sorted(list(distinct_dates))
        if not sorted_dates:
            return {
                "current_streak": 0,
                "longest_streak": 0,
                "last_active_date": None,
            }

        last_active_date = sorted_dates[-1]

        # 1. Compute longest streak
        longest_streak = 1
        temp_streak = 1
        for i in range(1, len(sorted_dates)):
            if sorted_dates[i] == sorted_dates[i - 1] + timedelta(days=1):
                temp_streak += 1
            else:
                temp_streak = 1
            if temp_streak > longest_streak:
                longest_streak = temp_streak

        # 2. Compute current streak
        today_utc = datetime.now(timezone.utc).date()
        yesterday_utc = today_utc - timedelta(days=1)

        current_streak = 0
        if last_active_date == today_utc:
            # Active today, count backward from today
            current_streak = 1
            check_date = today_utc - timedelta(days=1)
            while check_date in distinct_dates:
                current_streak += 1
                check_date -= timedelta(days=1)
        elif last_active_date == yesterday_utc:
            # Active yesterday, streak is currently maintained up to yesterday
            current_streak = 1
            check_date = yesterday_utc - timedelta(days=1)
            while check_date in distinct_dates:
                current_streak += 1
                check_date -= timedelta(days=1)
        else:
            # Missed both yesterday and today
            current_streak = 0

        return {
            "current_streak": current_streak,
            "longest_streak": longest_streak,
            "last_active_date": last_active_date.isoformat(),
        }
