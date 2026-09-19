import io
import csv
from uuid import UUID
from datetime import datetime, timezone
from typing import Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.event import Event, event_challenges
from app.models.challenge import Challenge
from app.models.category import Category
from app.models.solve import Solve
from app.models.submission import Submission
from app.models.user import User
from app.models.team import Team, TeamMember
from app.models.event_registration import EventRegistration
from app.models.security_event import SecurityEvent
from app.services.event_service import EventService


class EventExportService:
    """Service to export event rankings and challenge statistics in JSON or CSV formats."""

    @staticmethod
    def export_json(db: Session, event_id: UUID) -> Dict[str, Any]:
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

        leaderboard = EventService.get_event_leaderboard(db, event_id)

        # Get event challenges with solve counts
        challenges_query = (
            db.query(
                Challenge.id,
                Challenge.title,
                Challenge.difficulty,
                Challenge.points,
                Category.name.label("category_name"),
            )
            .join(event_challenges, Challenge.id == event_challenges.c.challenge_id)
            .join(Category, Challenge.category_id == Category.id)
            .filter(event_challenges.c.event_id == event_id)
            .all()
        )

        challenges_list = []
        for ch in challenges_query:
            solve_count = (
                db.query(func.count(Solve.id))
                .filter(Solve.event_id == event_id, Solve.challenge_id == ch.id)
                .scalar()
                or 0
            )
            challenges_list.append({
                "id": str(ch.id),
                "title": ch.title,
                "category": ch.category_name,
                "difficulty": ch.difficulty.value if hasattr(ch.difficulty, "value") else str(ch.difficulty),
                "points": ch.points,
                "solve_count": solve_count,
            })

        leaderboard_items = [
            {
                "rank": e.rank,
                "participant_id": str(e.participant_id),
                "participant_name": e.participant_name,
                "participant_type": e.participant_type,
                "college": e.college,
                "total_points": e.total_points,
                "solved_count": e.solved_count,
                "last_solve_time": e.last_solve_time.isoformat() if e.last_solve_time else None,
            }
            for e in leaderboard.entries
        ]

        return {
            "event_id": str(event.id),
            "event_name": event.name,
            "event_slug": event.slug,
            "start_at": event.start_at.isoformat(),
            "end_at": event.end_at.isoformat(),
            "is_frozen": event.is_scoreboard_frozen,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "leaderboard": leaderboard_items,
            "challenges": challenges_list,
        }

    @staticmethod
    def export_csv(db: Session, event_id: UUID) -> str:
        data = EventExportService.export_json(db, event_id)
        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            "Rank",
            "Participant Type",
            "Participant Name",
            "College",
            "Total Points",
            "Solved Challenges",
            "Last Solve Time",
        ])

        for row in data["leaderboard"]:
            writer.writerow([
                row["rank"],
                row["participant_type"],
                row["participant_name"],
                row["college"] or "N/A",
                row["total_points"],
                row["solved_count"],
                row["last_solve_time"] or "N/A",
            ])

        return output.getvalue()

    @staticmethod
    def get_audit_breakdown(db: Session, event_id: UUID) -> Dict[str, Any]:
        """Provides complete post-mortem audit breakdown for an event including per-participant/team questions solved/failed, cheating logs, and certificate distribution status."""
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

        leaderboard = EventService.get_event_leaderboard(db, event_id)

        # 1. Challenge lookup
        challenges_query = (
            db.query(
                Challenge.id,
                Challenge.title,
                Challenge.difficulty,
                Challenge.points,
                Category.name.label("category_name"),
            )
            .join(event_challenges, Challenge.id == event_challenges.c.challenge_id)
            .join(Category, Challenge.category_id == Category.id)
            .filter(event_challenges.c.event_id == event_id)
            .all()
        )
        challenge_map = {
            ch.id: {
                "id": str(ch.id),
                "title": ch.title,
                "category": ch.category_name,
                "difficulty": ch.difficulty.value if hasattr(ch.difficulty, "value") else str(ch.difficulty),
                "points": ch.points,
            }
            for ch in challenges_query
        }

        # 2. Solves and Submissions in this event
        solves = db.query(Solve).filter(Solve.event_id == event_id).all()
        submissions = db.query(Submission).filter(Submission.event_id == event_id).all()

        # Map solves by user and by team
        user_solves = {}
        team_solves = {}
        for s in solves:
            ch_info = challenge_map.get(s.challenge_id, {
                "id": str(s.challenge_id),
                "title": "Challenge Vector",
                "category": "Jeopardy",
                "difficulty": "medium",
                "points": s.points_awarded,
            })
            solve_entry = {
                **ch_info,
                "points_awarded": s.points_awarded,
                "solved_at": s.created_at.isoformat() if s.created_at else None,
            }
            if s.user_id:
                user_solves.setdefault(s.user_id, []).append(solve_entry)
            if s.team_id:
                team_solves.setdefault(s.team_id, []).append(solve_entry)

        # Map wrong submissions by user and by team
        user_wrongs = {}
        team_wrongs = {}
        for sub in submissions:
            if not sub.is_correct:
                ch_info = challenge_map.get(sub.challenge_id, {
                    "id": str(sub.challenge_id),
                    "title": "Challenge Vector",
                    "category": "Jeopardy",
                })
                if sub.user_id:
                    user_wrongs.setdefault(sub.user_id, {}).setdefault(sub.challenge_id, {
                        **ch_info,
                        "attempts_count": 0,
                    })["attempts_count"] += 1
                if sub.team_id:
                    team_wrongs.setdefault(sub.team_id, {}).setdefault(sub.challenge_id, {
                        **ch_info,
                        "attempts_count": 0,
                    })["attempts_count"] += 1

        # 3. Registrations and Leaderboard map
        leaderboard_map = {e.participant_id: e for e in leaderboard.entries}
        registrations = db.query(EventRegistration).filter(
            EventRegistration.event_id == event_id,
            EventRegistration.is_active == True,
        ).all()

        participants_list = []
        teams_list = []
        seen_user_ids = set()
        seen_team_ids = set()

        for reg in registrations:
            reg_type = reg.registration_type.value if hasattr(reg.registration_type, "value") else str(reg.registration_type)
            if reg_type == "individual" and reg.user_id and reg.user_id not in seen_user_ids:
                seen_user_ids.add(reg.user_id)
                u = db.query(User).filter(User.id == reg.user_id).first()
                if u:
                    l_entry = leaderboard_map.get(u.id)
                    rank = l_entry.rank if l_entry else len(leaderboard.entries) + len(participants_list) + 1
                    total_pts = l_entry.total_points if l_entry else 0
                    p_solves = user_solves.get(u.id, [])
                    p_wrongs = list(user_wrongs.get(u.id, {}).values())
                    total_wrong = sum(w["attempts_count"] for w in p_wrongs)

                    participants_list.append({
                        "participant_id": str(u.id),
                        "name": u.name or u.username,
                        "username": u.username,
                        "email": u.email,
                        "college": u.college or "OWASP Student Member",
                        "rank": rank,
                        "total_points": total_pts,
                        "solved_count": len(p_solves),
                        "solved_challenges": p_solves,
                        "failed_attempts_count": total_wrong,
                        "failed_challenges": p_wrongs,
                        "is_banned": u.is_banned,
                        "certificate_status": "sent" if (total_pts > 0 or len(p_solves) > 0) else "pending",
                    })
            elif reg_type == "team" and reg.team_id and reg.team_id not in seen_team_ids:
                seen_team_ids.add(reg.team_id)
                t = db.query(Team).filter(Team.id == reg.team_id).first()
                if t:
                    l_entry = leaderboard_map.get(t.id)
                    rank = l_entry.rank if l_entry else len(leaderboard.entries) + len(teams_list) + 1
                    total_pts = l_entry.total_points if l_entry else 0
                    t_solves = team_solves.get(t.id, [])
                    t_wrongs = list(team_wrongs.get(t.id, {}).values())
                    total_wrong = sum(w["attempts_count"] for w in t_wrongs)

                    members = (
                        db.query(User.id, User.username, User.name, User.email, User.is_banned)
                        .join(TeamMember, User.id == TeamMember.user_id)
                        .filter(TeamMember.team_id == t.id, TeamMember.is_active == True)
                        .all()
                    )

                    teams_list.append({
                        "team_id": str(t.id),
                        "name": t.name,
                        "college": t.college or "Collegiate Squad",
                        "rank": rank,
                        "total_points": total_pts,
                        "solved_count": len(t_solves),
                        "solved_challenges": t_solves,
                        "failed_attempts_count": total_wrong,
                        "failed_challenges": t_wrongs,
                        "is_active": t.is_active,
                        "members": [
                            {
                                "id": str(m[0]),
                                "username": m[1],
                                "name": m[2] or m[1],
                                "email": m[3],
                                "is_banned": m[4],
                            }
                            for m in members
                        ],
                        "certificate_status": "sent" if (total_pts > 0 or len(t_solves) > 0) else "pending",
                    })

        # Sort by rank
        participants_list.sort(key=lambda p: p["rank"])
        teams_list.sort(key=lambda t: t["rank"])

        # 4. Cheating & Anti-Cheat Incidents for this event
        sec_events = (
            db.query(SecurityEvent)
            .filter((SecurityEvent.event_id == event_id) | (SecurityEvent.event_id.is_(None)))
            .order_by(SecurityEvent.created_at.desc())
            .all()
        )
        cheating_logs = []
        for se in sec_events:
            u_name = None
            if se.user_id:
                usr = db.query(User).filter(User.id == se.user_id).first()
                u_name = usr.username if usr else None
            t_name = None
            if se.team_id:
                tm = db.query(Team).filter(Team.id == se.team_id).first()
                t_name = tm.name if tm else None

            cheating_logs.append({
                "id": str(se.id),
                "user_id": str(se.user_id) if se.user_id else None,
                "username": u_name or "operative",
                "team_id": str(se.team_id) if se.team_id else None,
                "team_name": t_name,
                "event_type": se.event_type,
                "severity": se.severity,
                "status": se.status,
                "description": se.description,
                "created_at": se.created_at.isoformat() if se.created_at else None,
                "is_actioned": se.status in ("actioned", "reviewed"),
            })

        # 5. Challenge vectors solve breakdown
        challenges_summary = []
        for ch_id, ch_meta in challenge_map.items():
            ch_solves_count = db.query(func.count(Solve.id)).filter(Solve.event_id == event_id, Solve.challenge_id == ch_id).scalar() or 0
            ch_wrong_count = db.query(func.count(Submission.id)).filter(Submission.event_id == event_id, Submission.challenge_id == ch_id, Submission.is_correct == False).scalar() or 0
            
            # First blood
            first_solve = db.query(Solve).filter(Solve.event_id == event_id, Solve.challenge_id == ch_id).order_by(Solve.created_at.asc()).first()
            first_blood = None
            if first_solve:
                fb_user = db.query(User).filter(User.id == first_solve.user_id).first()
                if fb_user:
                    first_blood = fb_user.username

            challenges_summary.append({
                **ch_meta,
                "solve_count": ch_solves_count,
                "wrong_count": ch_wrong_count,
                "first_blood": first_blood,
            })

        return {
            "event": {
                "id": str(event.id),
                "name": event.name,
                "description": event.description,
                "start_at": event.start_at.isoformat(),
                "end_at": event.end_at.isoformat(),
                "status": event.status,
                "computed_status": "ended" if event.end_at < datetime.now(timezone.utc) else (event.status or "ended"),
                "is_scoreboard_frozen": event.is_scoreboard_frozen,
            },
            "leaderboard": [
                {
                    "rank": e.rank,
                    "participant_id": str(e.participant_id),
                    "participant_name": e.participant_name,
                    "participant_type": e.participant_type,
                    "college": e.college,
                    "total_points": e.total_points,
                    "solved_count": e.solved_count,
                    "last_solve_time": e.last_solve_time.isoformat() if e.last_solve_time else None,
                }
                for e in leaderboard.entries
            ],
            "participants": participants_list,
            "teams": teams_list,
            "cheating_audit": cheating_logs,
            "challenges_summary": challenges_summary,
            "total_participants": len(participants_list),
            "total_teams": len(teams_list),
            "total_solves": len(solves),
        }

