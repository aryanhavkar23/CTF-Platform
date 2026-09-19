from app.database import SessionLocal
from app.models.user import User
from app.models.team import Team, TeamMember
from app.models.event_registration import EventRegistration
from app.models.event import Event
from app.models.submission import Submission

with SessionLocal() as db:
    print("=== USERS ===")
    users = db.query(User).all()
    for u in users:
        print(f"User: {u.username} (id: {u.id}, role: {u.role})")

    print("\n=== TEAMS ===")
    teams = db.query(Team).all()
    for t in teams:
        members = db.query(TeamMember).filter(TeamMember.team_id == t.id).all()
        m_list = [f"{m.user.username if m.user else m.user_id} (role={m.role}, active={m.is_active})" for m in members]
        regs = db.query(EventRegistration).filter(EventRegistration.team_id == t.id).all()
        reg_events = [r.event.name if r.event else str(r.event_id) for r in regs]
        subs = db.query(Submission).filter(Submission.team_id == t.id).all()
        print(f"Team: {t.name} (id: {t.id}) | Owner: {t.owner.username if t.owner else t.owner_id} | Members: {m_list} | Events: {reg_events} | Submissions: {len(subs)}")
