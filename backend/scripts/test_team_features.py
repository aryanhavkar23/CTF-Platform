from app.database import SessionLocal
from app.models.user import User
from app.models.team import Team
from app.services.team_service import TeamService

with SessionLocal() as db:
    users = db.query(User).all()
    for u in users:
        my_teams = TeamService.get_my_teams(db, u)
        if my_teams:
            squad_labels = [f"{t.name} (role={t.my_role}, events={t.events_participated_count}, score={t.total_points})" for t in my_teams]
            print(f"Operative {u.username} -> Squads: {squad_labels}")

    print("\n--- TEAM HISTORIES ---")
    teams = db.query(Team).all()
    for t in teams:
        hist = TeamService.get_team_history(db, t.id)
        print(f"Squad: {t.name} | Events: {hist.events_participated_count} | Score: {hist.total_score} | Solves: {hist.total_solves}")
        for e in hist.events:
            print(f"   * Event '{e.event_name}' (status: {e.status}) -> Score: {e.score}, Rank: #{e.rank} of {e.total_teams}, Solves: {e.solves_count}")
