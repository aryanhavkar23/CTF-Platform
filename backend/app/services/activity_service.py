import json
from datetime import datetime, date, timedelta, timezone
from typing import Optional, List, Dict, Any, Tuple, Union
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.activity import UserActivity, ActivityType
from app.models.user import User


class ActivityService:
    """Authoritative service for tracking CTF user activities."""

    @staticmethod
    def record_activity(
        db: Session,
        user_id: UUID,
        activity_type: Union[ActivityType, str],
        reference_id: Optional[UUID] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> UserActivity:
        """Records a verified user action into the user_activities ledger."""
        act_type_str = activity_type.value if hasattr(activity_type, "value") else str(activity_type)
        meta_str = json.dumps(metadata) if metadata is not None else None

        activity = UserActivity(
            user_id=user_id,
            activity_type=act_type_str,
            reference_id=reference_id,
            metadata_json=meta_str,
        )
        db.add(activity)
        db.commit()
        db.refresh(activity)
        return activity

    @staticmethod
    def get_user_activities(
        db: Session,
        user_id: UUID,
        page: int = 1,
        limit: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Retrieves paginated activity feed for a user, sorted newest first."""
        if page < 1:
            page = 1
        if limit < 1:
            limit = 20
        if limit > 100:
            limit = 100

        query = db.query(UserActivity).filter(UserActivity.user_id == user_id)
        total = query.count()

        offset = (page - 1) * limit
        rows = query.order_by(UserActivity.created_at.desc()).offset(offset).limit(limit).all()

        results = []
        for r in rows:
            meta = None
            if r.metadata_json:
                try:
                    meta = json.loads(r.metadata_json)
                except Exception:
                    meta = None

            results.append({
                "id": r.id,
                "user_id": r.user_id,
                "activity_type": r.activity_type,
                "reference_id": r.reference_id,
                "metadata": meta,
                "created_at": r.created_at,
            })

        return results, total

    @staticmethod
    def get_activity_heatmap(
        db: Session,
        user_id: UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        """Returns daily activity counts across the date range, including zero-count days."""
        today_utc = datetime.now(timezone.utc).date()

        if end_date is None:
            end_date = today_utc
        if start_date is None:
            # Default window: past 365 days
            start_date = end_date - timedelta(days=365)

        if start_date > end_date:
            start_date, end_date = end_date, start_date

        start_dt = datetime(start_date.year, start_date.month, start_date.day, 0, 0, 0, tzinfo=timezone.utc)
        end_dt = datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59, tzinfo=timezone.utc)

        activities = db.query(UserActivity.created_at)\
            .filter(
                UserActivity.user_id == user_id,
                UserActivity.created_at >= start_dt,
                UserActivity.created_at <= end_dt
            ).all()

        counts_by_date: Dict[str, int] = {}
        for (created_at,) in activities:
            if created_at is not None:
                if created_at.tzinfo is None:
                    act_date = created_at.date()
                else:
                    act_date = created_at.astimezone(timezone.utc).date()
                d_str = act_date.isoformat()
                counts_by_date[d_str] = counts_by_date.get(d_str, 0) + 1

        # Populate all days in the contiguous date range
        heatmap: List[Dict[str, Any]] = []
        cur_date = start_date
        while cur_date <= end_date:
            d_str = cur_date.isoformat()
            heatmap.append({
                "date": d_str,
                "count": counts_by_date.get(d_str, 0),
            })
            cur_date += timedelta(days=1)

        return heatmap
