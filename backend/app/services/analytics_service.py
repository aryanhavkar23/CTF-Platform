from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func, case, distinct, desc, asc

from app.models.user import User, UserRole
from app.models.category import Category
from app.models.challenge import Challenge, ChallengeDifficulty
from app.models.submission import Submission
from app.models.solve import Solve
from app.models.team import Team, TeamMember
from app.models.event import Event, EventStatus, event_challenges
from app.models.event_registration import EventRegistration, RegistrationType
from app.models.activity import UserActivity
from app.models.badge import Badge, UserBadge
from app.models.discussion import Discussion, DiscussionComment
from app.schemas.analytics import PeriodFilter


class AnalyticsService:
    """Service providing read-only aggregation metrics for admin analytics."""

    @staticmethod
    def _get_period_cutoff(period: PeriodFilter) -> Optional[datetime]:
        """Returns UTC datetime cutoff threshold for the specified period filter."""
        now = datetime.now(timezone.utc)
        if period == PeriodFilter.TODAY:
            return now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == PeriodFilter.SEVEN_DAYS:
            return now - timedelta(days=7)
        elif period == PeriodFilter.THIRTY_DAYS:
            return now - timedelta(days=30)
        elif period == PeriodFilter.NINETY_DAYS:
            return now - timedelta(days=90)
        return None

    @classmethod
    def get_platform_overview(cls, db: Session, period: PeriodFilter = PeriodFilter.ALL) -> Dict[str, Any]:
        """Calculates high-level platform health metrics."""
        cutoff = cls._get_period_cutoff(period)

        total_users = db.query(func.count(User.id)).scalar() or 0
        
        active_users_q = db.query(func.count(distinct(UserActivity.user_id)))
        if cutoff:
            active_users_q = active_users_q.filter(UserActivity.created_at >= cutoff)
        active_users = active_users_q.scalar() or 0

        total_challenges = db.query(func.count(Challenge.id)).scalar() or 0
        active_challenges = db.query(func.count(Challenge.id)).filter(Challenge.is_active == True).scalar() or 0

        sub_q = db.query(
            func.count(Submission.id).label("total"),
            func.coalesce(func.sum(case((Submission.is_correct == True, 1), else_=0)), 0).label("correct"),
            func.coalesce(func.sum(case((Submission.is_correct == False, 1), else_=0)), 0).label("incorrect")
        )
        if cutoff:
            sub_q = sub_q.filter(Submission.created_at >= cutoff)
        sub_row = sub_q.first()
        total_sub = sub_row[0] or 0
        cor_sub = int(sub_row[1] or 0)
        incor_sub = int(sub_row[2] or 0)

        solves_q = db.query(func.count(Solve.id))
        if cutoff:
            solves_q = solves_q.filter(Solve.created_at >= cutoff)
        total_solves = solves_q.scalar() or 0

        total_teams = db.query(func.count(Team.id)).scalar() or 0
        active_teams = db.query(func.count(Team.id)).filter(Team.is_active == True).scalar() or 0

        total_events = db.query(func.count(Event.id)).scalar() or 0
        completed_events = db.query(func.count(Event.id)).filter(Event.status == EventStatus.ENDED).scalar() or 0

        badges_q = db.query(func.count(UserBadge.id))
        if cutoff:
            badges_q = badges_q.filter(UserBadge.awarded_at >= cutoff)
        total_badges = badges_q.scalar() or 0

        disc_q = db.query(func.count(Discussion.id)).filter(Discussion.is_deleted == False)
        if cutoff:
            disc_q = disc_q.filter(Discussion.created_at >= cutoff)
        total_discussions = disc_q.scalar() or 0

        return {
            "period": period.value,
            "total_users": total_users,
            "active_users": active_users,
            "total_challenges": total_challenges,
            "active_challenges": active_challenges,
            "total_submissions": total_sub,
            "correct_submissions": cor_sub,
            "incorrect_submissions": incor_sub,
            "total_solves": total_solves,
            "total_teams": total_teams,
            "active_teams": active_teams,
            "total_events": total_events,
            "completed_events": completed_events,
            "total_badges_awarded": total_badges,
            "total_discussions": total_discussions
        }

    @classmethod
    def get_user_analytics(cls, db: Session, period: PeriodFilter = PeriodFilter.ALL) -> Dict[str, Any]:
        """Calculates user demographics, growth, and engagement statistics."""
        cutoff = cls._get_period_cutoff(period)

        total_users = db.query(func.count(User.id)).scalar() or 0

        new_users_q = db.query(func.count(User.id))
        if cutoff:
            new_users_q = new_users_q.filter(User.created_at >= cutoff)
        new_users = new_users_q.scalar() or 0

        active_users_q = db.query(func.count(distinct(UserActivity.user_id)))
        if cutoff:
            active_users_q = active_users_q.filter(UserActivity.created_at >= cutoff)
        active_users = active_users_q.scalar() or 0

        users_with_solves = db.query(func.count(distinct(Solve.user_id))).scalar() or 0
        users_without_solves = max(0, total_users - users_with_solves)

        college_rows = db.query(
            func.coalesce(User.college, "Unspecified").label("college"),
            func.count(User.id).label("count")
        ).group_by("college").order_by(desc("count")).all()
        by_college = [{"college": r[0], "count": r[1]} for r in college_rows]

        role_rows = db.query(
            User.role,
            func.count(User.id).label("count")
        ).group_by(User.role).order_by(desc("count")).all()
        by_role = [
            {"role": r[0].value if hasattr(r[0], "value") else str(r[0]), "count": r[1]}
            for r in role_rows
        ]

        return {
            "period": period.value,
            "total_users": total_users,
            "new_users": new_users,
            "active_users": active_users,
            "users_with_solves": users_with_solves,
            "users_without_solves": users_without_solves,
            "by_college": by_college,
            "by_role": by_role
        }

    @classmethod
    def get_activity_trend(cls, db: Session, period: PeriodFilter = PeriodFilter.THIRTY_DAYS) -> Dict[str, Any]:
        """Returns daily activity event counts for the specified period."""
        cutoff = cls._get_period_cutoff(period)

        q = db.query(
            func.date(UserActivity.created_at).label("day"),
            func.count(UserActivity.id).label("count")
        )
        if cutoff:
            q = q.filter(UserActivity.created_at >= cutoff)
        q = q.group_by("day").order_by("day")
        rows = q.all()

        data = [{"date": str(r[0]), "activities": r[1]} for r in rows]
        return {
            "period": period.value,
            "data": data
        }

    @classmethod
    def get_challenge_analytics(cls, db: Session) -> List[Dict[str, Any]]:
        """Computes aggregate attempt and solve metrics for all challenges."""
        # Query submission stats grouped by challenge_id
        sub_stats = db.query(
            Submission.challenge_id,
            func.count(Submission.id).label("total_attempts"),
            func.coalesce(func.sum(case((Submission.is_correct == True, 1), else_=0)), 0).label("correct_attempts"),
            func.count(distinct(case((Submission.is_correct == True, Submission.user_id), else_=None))).label("unique_solvers")
        ).group_by(Submission.challenge_id).all()

        stats_map = {
            r[0]: (r[1], int(r[2]), r[3])
            for r in sub_stats
        }

        challenges = db.query(Challenge, Category.name).outerjoin(
            Category, Challenge.category_id == Category.id
        ).order_by(asc(Challenge.title)).all()

        results = []
        for ch, cat_name in challenges:
            tot, cor, solvers = stats_map.get(ch.id, (0, 0, 0))
            rate = round(cor / tot, 4) if tot > 0 else 0.0
            results.append({
                "challenge_id": ch.id,
                "title": ch.title,
                "category": cat_name or "Uncategorized",
                "difficulty": ch.difficulty.value if hasattr(ch.difficulty, "value") else str(ch.difficulty),
                "points": ch.points,
                "total_attempts": tot,
                "correct_attempts": cor,
                "unique_solvers": solvers,
                "solve_rate": rate
            })

        return results

    @classmethod
    def get_difficulty_analytics(cls, db: Session) -> List[Dict[str, Any]]:
        """Aggregates challenge counts and solve rates grouped by difficulty."""
        chall_analytics = cls.get_challenge_analytics(db)
        
        diff_order = ["easy", "medium", "hard", "insane"]
        diff_buckets = {d: {"challenge_count": 0, "attempts": 0, "solves": 0} for d in diff_order}

        for c in chall_analytics:
            d = c["difficulty"].lower()
            if d in diff_buckets:
                diff_buckets[d]["challenge_count"] += 1
                diff_buckets[d]["attempts"] += c["total_attempts"]
                diff_buckets[d]["solves"] += c["correct_attempts"]

        results = []
        for d in diff_order:
            b = diff_buckets[d]
            rate = round(b["solves"] / b["attempts"], 4) if b["attempts"] > 0 else 0.0
            results.append({
                "difficulty": d.capitalize(),
                "challenge_count": b["challenge_count"],
                "attempts": b["attempts"],
                "solves": b["solves"],
                "average_solve_rate": rate
            })
        return results

    @classmethod
    def get_category_analytics(cls, db: Session) -> List[Dict[str, Any]]:
        """Aggregates metrics for each challenge category."""
        chall_analytics = cls.get_challenge_analytics(db)
        categories = db.query(Category).order_by(asc(Category.name)).all()

        cat_map = {c.name: c.id for c in categories}
        cat_buckets = {
            c.name: {
                "category_id": c.id,
                "category_name": c.name,
                "challenge_count": 0,
                "attempts": 0,
                "solves": 0,
                "solvers": set(),
                "total_points": 0
            }
            for c in categories
        }

        # Query points awarded per category from Solve
        solves_with_cat = db.query(
            Challenge.category_id,
            func.coalesce(func.sum(Solve.points_awarded), 0)
        ).join(Challenge, Solve.challenge_id == Challenge.id).group_by(Challenge.category_id).all()
        points_map = {r[0]: int(r[1]) for r in solves_with_cat}

        for c in chall_analytics:
            c_name = c["category"]
            if c_name in cat_buckets:
                cat_buckets[c_name]["challenge_count"] += 1
                cat_buckets[c_name]["attempts"] += c["total_attempts"]
                cat_buckets[c_name]["solves"] += c["correct_attempts"]
                # Approximate unique solvers sum
                cat_buckets[c_name]["total_points"] = points_map.get(cat_buckets[c_name]["category_id"], 0)

        # Query exact distinct solvers per category
        solvers_per_cat = db.query(
            Challenge.category_id,
            func.count(distinct(Solve.user_id))
        ).join(Challenge, Solve.challenge_id == Challenge.id).group_by(Challenge.category_id).all()
        solvers_map = {r[0]: r[1] for r in solvers_per_cat}

        results = []
        for c in categories:
            b = cat_buckets[c.name]
            unique_solvers = solvers_map.get(c.id, 0)
            rate = round(b["solves"] / b["attempts"], 4) if b["attempts"] > 0 else 0.0
            results.append({
                "category_id": c.id,
                "category_name": c.name,
                "challenge_count": b["challenge_count"],
                "attempts": b["attempts"],
                "solves": b["solves"],
                "unique_solvers": unique_solvers,
                "total_points_awarded": points_map.get(c.id, 0),
                "average_solve_rate": rate
            })
        return results

    @classmethod
    def get_challenge_insights(cls, db: Session, min_attempts: int = 10) -> Dict[str, Any]:
        """Identifies most difficult, most solved, and most attempted challenges."""
        chall_analytics = cls.get_challenge_analytics(db)

        # Most difficult: challenges with >= min_attempts, lowest solve_rate
        qualifying = [c for c in chall_analytics if c["total_attempts"] >= min_attempts]
        if not qualifying and chall_analytics:
            # Fallback to any challenges with at least 1 attempt to avoid blank results in small dev environments
            qualifying = [c for c in chall_analytics if c["total_attempts"] >= 1]

        most_diff = sorted(qualifying, key=lambda x: (x["solve_rate"], -x["total_attempts"]))[:10]
        most_solved = sorted(chall_analytics, key=lambda x: (-x["unique_solvers"], -x["solve_rate"]))[:10]
        most_attempted = sorted(chall_analytics, key=lambda x: (-x["total_attempts"], -x["correct_attempts"]))[:10]

        return {
            "min_attempts_threshold": min_attempts,
            "most_difficult": most_diff,
            "most_solved": most_solved,
            "most_attempted": most_attempted
        }

    @classmethod
    def get_submission_analytics(cls, db: Session, period: PeriodFilter = PeriodFilter.ALL) -> Dict[str, Any]:
        """Analyzes submission trends, accuracy rates, and behavioral metrics."""
        cutoff = cls._get_period_cutoff(period)

        sub_q = db.query(
            func.count(Submission.id).label("total"),
            func.coalesce(func.sum(case((Submission.is_correct == True, 1), else_=0)), 0).label("correct"),
            func.coalesce(func.sum(case((Submission.is_correct == False, 1), else_=0)), 0).label("incorrect"),
            func.count(distinct(Submission.user_id)).label("unique_submitters")
        )
        if cutoff:
            sub_q = sub_q.filter(Submission.created_at >= cutoff)
        row = sub_q.first()

        tot = row[0] or 0
        cor = int(row[1] or 0)
        incor = int(row[2] or 0)
        submitters = row[3] or 0
        accuracy = round(cor / tot, 4) if tot > 0 else 0.0

        avg_attempts_before_solve = round(tot / cor, 2) if cor > 0 else 0.0

        # Submissions by day
        day_q = db.query(
            func.date(Submission.created_at).label("day"),
            func.count(Submission.id).label("total"),
            func.coalesce(func.sum(case((Submission.is_correct == True, 1), else_=0)), 0).label("correct"),
            func.coalesce(func.sum(case((Submission.is_correct == False, 1), else_=0)), 0).label("incorrect")
        )
        if cutoff:
            day_q = day_q.filter(Submission.created_at >= cutoff)
        day_rows = day_q.group_by("day").order_by("day").all()
        by_day = [
            {"date": str(r[0]), "total": r[1], "correct": int(r[2]), "incorrect": int(r[3])}
            for r in day_rows
        ]

        # Challenges with highest failure rate
        fail_q = db.query(
            Challenge.id,
            Challenge.title,
            func.count(Submission.id).label("attempts"),
            func.coalesce(func.sum(case((Submission.is_correct == False, 1), else_=0)), 0).label("failed")
        ).join(Submission, Challenge.id == Submission.challenge_id)
        if cutoff:
            fail_q = fail_q.filter(Submission.created_at >= cutoff)
        fail_rows = fail_q.group_by(Challenge.id, Challenge.title).all()

        fail_items = []
        for ch_id, title, attempts, failed in fail_rows:
            if attempts > 0:
                fail_rate = round(int(failed) / attempts, 4)
                fail_items.append({
                    "challenge_id": ch_id,
                    "title": title,
                    "failure_rate": fail_rate,
                    "attempts": attempts
                })
        highest_failure = sorted(fail_items, key=lambda x: (-x["failure_rate"], -x["attempts"]))[:10]

        # Frequent submitters
        user_q = db.query(
            User.id,
            User.username,
            func.count(Submission.id).label("submission_count")
        ).join(Submission, User.id == Submission.user_id)
        if cutoff:
            user_q = user_q.filter(Submission.created_at >= cutoff)
        user_rows = user_q.group_by(User.id, User.username).order_by(desc("submission_count")).limit(10).all()

        frequent_submitters = [
            {"user_id": r[0], "username": r[1], "submission_count": r[2]}
            for r in user_rows
        ]

        return {
            "period": period.value,
            "total_submissions": tot,
            "correct_submissions": cor,
            "incorrect_submissions": incor,
            "accuracy_rate": accuracy,
            "unique_submitters": submitters,
            "average_attempts_before_solve": avg_attempts_before_solve,
            "submissions_by_day": by_day,
            "challenges_highest_failure": highest_failure,
            "frequent_submitters": frequent_submitters
        }

    @classmethod
    def get_events_analytics(cls, db: Session) -> List[Dict[str, Any]]:
        """Summarizes performance and participation for all CTF events."""
        events = db.query(Event).order_by(desc(Event.start_time)).all()

        results = []
        for ev in events:
            reg_count = db.query(func.count(EventRegistration.id)).filter(
                EventRegistration.event_id == ev.id,
                EventRegistration.is_active == True
            ).scalar() or 0

            # Count assigned challenges
            chall_count = db.query(func.count(event_challenges.c.challenge_id)).filter(
                event_challenges.c.event_id == ev.id
            ).scalar() or 0

            # Submissions and solves during event
            sub_count = db.query(func.count(Submission.id)).join(
                event_challenges, Submission.challenge_id == event_challenges.c.challenge_id
            ).filter(
                event_challenges.c.event_id == ev.id,
                Submission.created_at >= ev.start_time,
                Submission.created_at <= ev.end_time
            ).scalar() or 0

            solve_count = db.query(func.count(Solve.id)).filter(Solve.event_id == ev.id).scalar() or 0

            # Active participants (unique users who solved or submitted)
            active_participants = db.query(func.count(distinct(Solve.user_id))).filter(
                Solve.event_id == ev.id
            ).scalar() or 0

            results.append({
                "event_id": ev.id,
                "name": ev.name,
                "slug": ev.slug,
                "status": ev.status.value if hasattr(ev.status, "value") else str(ev.status),
                "registration_count": reg_count,
                "active_participants": active_participants,
                "challenges_assigned": chall_count,
                "total_submissions": sub_count,
                "total_solves": solve_count,
                "is_scoreboard_frozen": ev.is_scoreboard_frozen
            })
        return results

    @classmethod
    def get_event_detail_analytics(cls, db: Session, event_id: UUID) -> Optional[Dict[str, Any]]:
        """Returns deep-dive analytics for a single competition event."""
        ev = db.query(Event).filter(Event.id == event_id).first()
        if not ev:
            return None

        regs = db.query(EventRegistration).filter(
            EventRegistration.event_id == ev.id,
            EventRegistration.is_active == True
        ).all()

        tot_regs = len(regs)
        ind_regs = sum(1 for r in regs if r.registration_type == RegistrationType.INDIVIDUAL)
        team_regs = sum(1 for r in regs if r.registration_type == RegistrationType.TEAM)

        solves = db.query(Solve).filter(Solve.event_id == ev.id).all()
        tot_solves = len(solves)
        unique_participants = len(set(s.user_id for s in solves))

        sub_count = db.query(func.count(Submission.id)).join(
            event_challenges, Submission.challenge_id == event_challenges.c.challenge_id
        ).filter(
            event_challenges.c.event_id == ev.id,
            Submission.created_at >= ev.start_time,
            Submission.created_at <= ev.end_time
        ).scalar() or 0

        participation_rate = round(unique_participants / max(tot_regs, 1), 4) if tot_regs > 0 else 0.0

        # Challenge performance within event
        ch_assigned = db.query(Challenge).join(
            event_challenges, Challenge.id == event_challenges.c.challenge_id
        ).filter(event_challenges.c.event_id == ev.id).all()

        ch_perf = []
        for ch in ch_assigned:
            attempts = db.query(func.count(Submission.id)).filter(
                Submission.challenge_id == ch.id,
                Submission.created_at >= ev.start_time,
                Submission.created_at <= ev.end_time
            ).scalar() or 0
            s_count = sum(1 for s in solves if s.challenge_id == ch.id)
            s_rate = round(s_count / attempts, 4) if attempts > 0 else 0.0
            ch_perf.append({
                "challenge_id": ch.id,
                "title": ch.title,
                "attempts": attempts,
                "solves": s_count,
                "solve_rate": s_rate
            })

        # Top participants
        top_user_scores = db.query(
            Solve.user_id,
            User.username,
            func.coalesce(func.sum(Solve.points_awarded), 0).label("score"),
            func.count(Solve.id).label("solves")
        ).join(User, Solve.user_id == User.id).filter(
            Solve.event_id == ev.id
        ).group_by(Solve.user_id, User.username).order_by(desc("score")).limit(10).all()

        top_participants = [
            {
                "participant_id": r[0],
                "name": r[1],
                "registration_type": "individual",
                "score": int(r[2]),
                "solves": r[3]
            }
            for r in top_user_scores
        ]

        return {
            "event_id": ev.id,
            "name": ev.name,
            "slug": ev.slug,
            "status": ev.status.value if hasattr(ev.status, "value") else str(ev.status),
            "total_registrations": tot_regs,
            "individual_registrations": ind_regs,
            "team_registrations": team_regs,
            "unique_participants": unique_participants,
            "total_submissions": sub_count,
            "total_solves": tot_solves,
            "participation_rate": participation_rate,
            "challenge_performance": ch_perf,
            "top_participants": top_participants
        }

    @classmethod
    def get_team_analytics(cls, db: Session) -> Dict[str, Any]:
        """Calculates team participation, roster sizes, and solve metrics."""
        total_teams = db.query(func.count(Team.id)).scalar() or 0
        active_teams = db.query(func.count(Team.id)).filter(Team.is_active == True).scalar() or 0

        total_members = db.query(func.count(TeamMember.id)).scalar() or 0
        avg_size = round(total_members / max(total_teams, 1), 2) if total_teams > 0 else 0.0

        college_rows = db.query(
            func.coalesce(Team.college, "Unspecified").label("college"),
            func.count(Team.id).label("count")
        ).group_by("college").order_by(desc("count")).all()
        by_college = [{"college": r[0], "count": r[1]} for r in college_rows]

        # Teams with solves
        teams_with_solves = db.query(func.count(distinct(Solve.team_id))).filter(
            Solve.team_id != None
        ).scalar() or 0
        teams_without_solves = max(0, total_teams - teams_with_solves)

        return {
            "total_teams": total_teams,
            "active_teams": active_teams,
            "average_team_size": avg_size,
            "by_college": by_college,
            "teams_with_solves": teams_with_solves,
            "teams_without_solves": teams_without_solves
        }

    @classmethod
    def get_badge_analytics(cls, db: Session) -> Dict[str, Any]:
        """Analyzes badge distribution and acquisition frequency."""
        total_definitions = db.query(func.count(Badge.id)).scalar() or 0
        total_awarded = db.query(func.count(UserBadge.id)).scalar() or 0

        # Query awarded count per badge
        award_counts = db.query(
            Badge.id,
            Badge.name,
            Badge.slug,
            Badge.icon,
            Badge.is_active,
            func.count(UserBadge.id).label("awarded_count")
        ).outerjoin(UserBadge, Badge.id == UserBadge.badge_id).group_by(
            Badge.id, Badge.name, Badge.slug, Badge.icon, Badge.is_active
        ).all()

        badge_items = [
            {
                "badge_id": r[0],
                "name": r[1],
                "slug": r[2],
                "icon": r[3],
                "is_active": r[4],
                "awarded_count": r[5]
            }
            for r in award_counts
        ]

        most_awarded = sorted(badge_items, key=lambda x: -x["awarded_count"])[:10]
        # Least awarded active badges
        active_badges = [b for b in badge_items if b["is_active"]]
        least_awarded = sorted(active_badges, key=lambda x: x["awarded_count"])[:10]

        return {
            "total_badge_definitions": total_definitions,
            "total_badges_awarded": total_awarded,
            "most_awarded_badges": [
                {k: b[k] for k in ["badge_id", "name", "slug", "icon", "awarded_count"]}
                for b in most_awarded
            ],
            "least_awarded_badges": [
                {k: b[k] for k in ["badge_id", "name", "slug", "icon", "awarded_count"]}
                for b in least_awarded
            ]
        }

    @classmethod
    def get_discussion_analytics(cls, db: Session, period: PeriodFilter = PeriodFilter.ALL) -> Dict[str, Any]:
        """Tracks challenge forum discussions, replies, and moderation states."""
        cutoff = cls._get_period_cutoff(period)

        total_discussions = db.query(func.count(Discussion.id)).scalar() or 0
        total_comments = db.query(func.count(DiscussionComment.id)).scalar() or 0

        period_disc_q = db.query(func.count(Discussion.id))
        if cutoff:
            period_disc_q = period_disc_q.filter(Discussion.created_at >= cutoff)
        period_disc = period_disc_q.scalar() or 0

        period_comm_q = db.query(func.count(DiscussionComment.id))
        if cutoff:
            period_comm_q = period_comm_q.filter(DiscussionComment.created_at >= cutoff)
        period_comm = period_comm_q.scalar() or 0

        locked_disc = db.query(func.count(Discussion.id)).filter(Discussion.is_locked == True).scalar() or 0
        deleted_disc = db.query(func.count(Discussion.id)).filter(Discussion.is_deleted == True).scalar() or 0

        # Most discussed challenges (threads + comments)
        disc_per_ch = db.query(
            Challenge.id,
            Challenge.title,
            func.count(distinct(Discussion.id)).label("thread_count"),
            func.count(DiscussionComment.id).label("comment_count")
        ).join(Discussion, Challenge.id == Discussion.challenge_id).outerjoin(
            DiscussionComment, Discussion.id == DiscussionComment.discussion_id
        ).filter(Discussion.is_deleted == False).group_by(Challenge.id, Challenge.title).all()

        most_discussed = []
        for ch_id, title, t_cnt, c_cnt in disc_per_ch:
            most_discussed.append({
                "challenge_id": ch_id,
                "title": title,
                "thread_count": t_cnt,
                "comment_count": c_cnt
            })
        most_discussed = sorted(most_discussed, key=lambda x: -(x["thread_count"] + x["comment_count"]))[:10]

        return {
            "period": period.value,
            "total_discussions": total_discussions,
            "total_comments": total_comments,
            "period_discussions": period_disc,
            "period_comments": period_comm,
            "locked_discussions": locked_disc,
            "deleted_discussions": deleted_disc,
            "most_discussed_challenges": most_discussed
        }

    @classmethod
    def get_leaderboard_insights(cls, db: Session) -> Dict[str, Any]:
        """Generates statistical score distribution and top performers overview."""
        # Query practice scores per user (event_id is None)
        user_scores = db.query(
            User.id,
            User.username,
            User.college,
            func.coalesce(func.sum(Solve.points_awarded), 0).label("score"),
            func.count(Solve.id).label("solves")
        ).join(Solve, User.id == Solve.user_id).filter(
            Solve.event_id == None
        ).group_by(User.id, User.username, User.college).order_by(desc("score")).all()

        ranked_count = len(user_scores)
        scores = [int(r[3]) for r in user_scores]
        total_score_sum = sum(scores)
        avg_score = round(total_score_sum / max(ranked_count, 1), 2) if ranked_count > 0 else 0.0

        if ranked_count > 0:
            sorted_scores = sorted(scores)
            mid = ranked_count // 2
            if ranked_count % 2 == 0:
                median_score = round((sorted_scores[mid - 1] + sorted_scores[mid]) / 2.0, 2)
            else:
                median_score = float(sorted_scores[mid])
        else:
            median_score = 0.0

        # Score distribution buckets
        ranges = [
            {"min": 0, "max": 100, "label": "0 - 100 pts", "users": 0},
            {"min": 101, "max": 500, "label": "101 - 500 pts", "users": 0},
            {"min": 501, "max": 1000, "label": "501 - 1,000 pts", "users": 0},
            {"min": 1001, "max": 2500, "label": "1,001 - 2,500 pts", "users": 0},
            {"min": 2501, "max": None, "label": "2,501+ pts", "users": 0}
        ]

        for s in scores:
            for r in ranges:
                if r["max"] is not None:
                    if r["min"] <= s <= r["max"]:
                        r["users"] += 1
                        break
                else:
                    if s >= r["min"]:
                        r["users"] += 1
                        break

        top_users = []
        for idx, r in enumerate(user_scores[:10]):
            top_users.append({
                "rank": idx + 1,
                "user_id": r[0],
                "username": r[1],
                "college": r[2],
                "score": int(r[3]),
                "solves": r[4]
            })

        return {
            "ranked_users_count": ranked_count,
            "average_score": avg_score,
            "median_score": median_score,
            "score_distribution": ranges,
            "top_users": top_users
        }

    @classmethod
    def get_dashboard_summary(cls, db: Session, period: PeriodFilter = PeriodFilter.THIRTY_DAYS) -> Dict[str, Any]:
        """Provides a composite summary for admin monitoring."""
        overview = cls.get_platform_overview(db, period)
        activity_trend = cls.get_activity_trend(db, period)["data"]
        category_summary = cls.get_category_analytics(db)
        difficulty_summary = cls.get_difficulty_analytics(db)
        top_challenges = cls.get_challenge_insights(db)["most_solved"][:5]
        event_summary = cls.get_events_analytics(db)

        return {
            "overview": overview,
            "activity_trend": activity_trend,
            "category_summary": category_summary,
            "difficulty_summary": difficulty_summary,
            "top_challenges": top_challenges,
            "event_summary": event_summary
        }
