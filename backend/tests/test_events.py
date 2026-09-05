from datetime import datetime, timedelta, timezone
from uuid import uuid4
import pytest
from app.models.event import Event, EventStatus
from app.models.user import UserRole
from app.models.challenge import Challenge, ChallengeDifficulty, WriteupVisibility
from app.models.team import Team, TeamMember
from app.services.challenge_service import hash_flag
from app.services.writeup_service import WriteupService
from app.schemas.writeup import WriteupCreate


from app.models.user import User, UserRole
from app.core.security import hash_password, create_access_token
from app.services.challenge_service import ChallengeService


def _utc_now():
    return datetime.now(timezone.utc)


@pytest.fixture
def test_setup(db_session):
    ChallengeService.seed_categories(db_session)

    student1 = User(
        username="student1",
        email="student1@college.edu",
        hashed_password=hash_password("Pass1234!"),
        role=UserRole.STUDENT,
        college="PCCOE",
        is_active=True,
    )
    student2 = User(
        username="student2",
        email="student2@college.edu",
        hashed_password=hash_password("Pass1234!"),
        role=UserRole.STUDENT,
        college="COEP",
        is_active=True,
    )
    admin = User(
        username="admin_user",
        email="admin@college.edu",
        hashed_password=hash_password("AdminPass123!"),
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add_all([student1, student2, admin])
    db_session.flush()

    def token_header(u):
        t = create_access_token(data={"sub": str(u.id), "email": u.email, "role": u.role.value})
        return {"Authorization": f"Bearer {t}"}

    return {
        "student1_header": token_header(student1),
        "student2_header": token_header(student2),
        "admin_header": token_header(admin),
        "student1": student1,
        "student2": student2,
        "admin": admin,
    }


@pytest.fixture
def event_setup(client, db_session, test_setup):
    """Creates a sample category and challenge for event testing."""
    cat_res = client.get("/api/categories")
    cat_id = cat_res.json()[0]["id"]

    chal_res = client.post(
        "/api/challenges",
        headers=test_setup["admin_header"],
        json={
            "title": "Corrupted Header",
            "description": "Analyze this file header",
            "category_id": cat_id,
            "difficulty": "medium",
            "points": 200,
            "flag": "flag{magic_bytes_restored_2026}",
            "is_active": True,
        },
    )
    chal_id = chal_res.json()["id"]

    return {
        "category_id": cat_id,
        "challenge_id": chal_id,
        "flag": "flag{magic_bytes_restored_2026}",
    }


# =============================================================================
# 1. Event CRUD & Date Validation Tests
# =============================================================================

def test_admin_create_event_success(client, test_setup):
    """Admin successfully creates an event with valid dates and auto slug."""
    now = _utc_now()
    reg_start = now - timedelta(days=2)
    reg_end = now + timedelta(days=1)
    start_at = now + timedelta(days=2)
    end_at = now + timedelta(days=4)

    payload = {
        "name": "OWASP Spring Hackathon 2026",
        "description": "Annual college-wide CTF championship",
        "start_at": start_at.isoformat(),
        "end_at": end_at.isoformat(),
        "registration_start_at": reg_start.isoformat(),
        "registration_end_at": reg_end.isoformat(),
    }
    res = client.post("/api/events", headers=test_setup["admin_header"], json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == payload["name"]
    assert data["slug"] == "owasp-spring-hackathon-2026"
    assert data["status"] == "upcoming"
    assert data["is_registration_open"] is True


def test_event_date_sequence_validation(client, test_setup):
    """Event date sequence violations are rejected with 422 Unprocessable Entity."""
    now = _utc_now()

    # Case 1: end_at before start_at
    res = client.post(
        "/api/events",
        headers=test_setup["admin_header"],
        json={
            "name": "Invalid Order Event",
            "start_at": (now + timedelta(days=3)).isoformat(),
            "end_at": (now + timedelta(days=1)).isoformat(),
        },
    )
    assert res.status_code == 422

    # Case 2: registration_end_at after start_at
    res = client.post(
        "/api/events",
        headers=test_setup["admin_header"],
        json={
            "name": "Invalid Reg Order Event",
            "start_at": (now + timedelta(days=2)).isoformat(),
            "end_at": (now + timedelta(days=4)).isoformat(),
            "registration_start_at": now.isoformat(),
            "registration_end_at": (now + timedelta(days=3)).isoformat(),
        },
    )
    assert res.status_code == 422


def test_student_cannot_create_or_update_event(client, test_setup):
    """Students are forbidden from creating, updating, or deleting events (403)."""
    now = _utc_now()
    payload = {
        "name": "Student Hack Event",
        "start_at": (now + timedelta(days=1)).isoformat(),
        "end_at": (now + timedelta(days=2)).isoformat(),
    }
    res = client.post("/api/events", headers=test_setup["student1_header"], json=payload)
    assert res.status_code == 403

    # Create an event as admin
    create_res = client.post("/api/events", headers=test_setup["admin_header"], json=payload)
    event_id = create_res.json()["id"]

    # Student update attempt
    up_res = client.put(
        f"/api/events/{event_id}",
        headers=test_setup["student1_header"],
        json={"name": "Hacked Name"},
    )
    assert up_res.status_code == 403

    # Student delete attempt
    del_res = client.delete(f"/api/events/{event_id}", headers=test_setup["student1_header"])
    assert del_res.status_code == 403


def test_duplicate_event_name_or_slug_conflict(client, test_setup):
    """Creating an event with a duplicate name or slug returns 409 Conflict."""
    now = _utc_now()
    payload = {
        "name": "Unique Name Event",
        "slug": "unique-slug",
        "start_at": (now + timedelta(days=1)).isoformat(),
        "end_at": (now + timedelta(days=2)).isoformat(),
    }
    res1 = client.post("/api/events", headers=test_setup["admin_header"], json=payload)
    assert res1.status_code == 201

    res2 = client.post("/api/events", headers=test_setup["admin_header"], json=payload)
    assert res2.status_code == 409


# =============================================================================
# 2. Event Challenge Linking Tests
# =============================================================================

def test_event_challenge_management(client, test_setup, event_setup):
    """Admin can link challenge with points override and remove challenge from event."""
    now = _utc_now()
    ev_res = client.post(
        "/api/events",
        headers=test_setup["admin_header"],
        json={
            "name": "Challenge Link Event",
            "start_at": (now + timedelta(days=1)).isoformat(),
            "end_at": (now + timedelta(days=2)).isoformat(),
        },
    )
    event_id = ev_res.json()["id"]

    # Add challenge with points override
    add_res = client.post(
        f"/api/events/{event_id}/challenges",
        headers=test_setup["admin_header"],
        json={
            "challenge_id": event_setup["challenge_id"],
            "display_order": 5,
            "points_override": 350,
        },
    )
    assert add_res.status_code == 200

    # Admin lists challenges (even though event is upcoming)
    admin_list = client.get(f"/api/events/{event_id}/challenges", headers=test_setup["admin_header"])
    assert admin_list.status_code == 200
    assert len(admin_list.json()) == 1
    assert admin_list.json()[0]["points"] == 350
    assert admin_list.json()[0]["display_order"] == 5

    # Remove challenge
    del_res = client.delete(
        f"/api/events/{event_id}/challenges/{event_setup['challenge_id']}",
        headers=test_setup["admin_header"],
    )
    assert del_res.status_code == 200

    admin_list2 = client.get(f"/api/events/{event_id}/challenges", headers=test_setup["admin_header"])
    assert len(admin_list2.json()) == 0


# =============================================================================
# 3. Registration Flow Tests (Individual + Team)
# =============================================================================

def test_individual_registration_and_duplicate_prevention(client, test_setup):
    """Students can register individually and duplicates are blocked."""
    now = _utc_now()
    ev_res = client.post(
        "/api/events",
        headers=test_setup["admin_header"],
        json={
            "name": "Registration Window Event",
            "registration_start_at": (now - timedelta(hours=2)).isoformat(),
            "registration_end_at": (now + timedelta(hours=2)).isoformat(),
            "start_at": (now + timedelta(hours=3)).isoformat(),
            "end_at": (now + timedelta(hours=10)).isoformat(),
        },
    )
    event_id = ev_res.json()["id"]

    # Student 1 registers
    reg_res = client.post(
        f"/api/events/{event_id}/register",
        headers=test_setup["student1_header"],
        json={"registration_type": "individual"},
    )
    assert reg_res.status_code == 201
    assert reg_res.json()["registration_type"] == "individual"
    assert reg_res.json()["participant_name"] == "student1"

    # Status check
    status_res = client.get(f"/api/events/{event_id}/registration", headers=test_setup["student1_header"])
    assert status_res.status_code == 200
    assert status_res.json()["is_registered"] is True

    # Duplicate registration rejected
    dup_res = client.post(
        f"/api/events/{event_id}/register",
        headers=test_setup["student1_header"],
        json={"registration_type": "individual"},
    )
    assert dup_res.status_code == 400
    assert "already registered" in dup_res.json()["detail"].lower()


def test_registration_window_enforcement(client, test_setup):
    """Registration outside configured window is rejected."""
    now = _utc_now()
    # Expired registration window
    ev_res = client.post(
        "/api/events",
        headers=test_setup["admin_header"],
        json={
            "name": "Closed Reg Event",
            "registration_start_at": (now - timedelta(days=5)).isoformat(),
            "registration_end_at": (now - timedelta(days=1)).isoformat(),
            "start_at": (now + timedelta(hours=1)).isoformat(),
            "end_at": (now + timedelta(hours=10)).isoformat(),
        },
    )
    event_id = ev_res.json()["id"]

    res = client.post(
        f"/api/events/{event_id}/register",
        headers=test_setup["student1_header"],
        json={"registration_type": "individual"},
    )
    assert res.status_code == 400
    assert "closed" in res.json()["detail"].lower()


def test_team_registration_by_owner(client, test_setup):
    """Only team owner may register team, and team member cannot register individually."""
    # Create team owned by student1
    team_res = client.post(
        "/api/teams",
        headers=test_setup["student1_header"],
        json={"name": "CyberKnights", "description": "Elite team"},
    )
    team_id = team_res.json()["id"]

    # Student2 tries to register student1's team (forbidden)
    now = _utc_now()
    ev_res = client.post(
        "/api/events",
        headers=test_setup["admin_header"],
        json={
            "name": "Team CTF 2026",
            "start_at": (now + timedelta(days=1)).isoformat(),
            "end_at": (now + timedelta(days=2)).isoformat(),
        },
    )
    event_id = ev_res.json()["id"]

    unauth_res = client.post(
        f"/api/events/{event_id}/register",
        headers=test_setup["student2_header"],
        json={"registration_type": "team", "team_id": team_id},
    )
    assert unauth_res.status_code == 403
    assert "only the team owner" in unauth_res.json()["detail"].lower()

    # Owner registers team successfully
    auth_res = client.post(
        f"/api/events/{event_id}/register",
        headers=test_setup["student1_header"],
        json={"registration_type": "team", "team_id": team_id},
    )
    assert auth_res.status_code == 201
    assert auth_res.json()["participant_name"] == "CyberKnights"

    # Owner cannot register individually for same event
    ind_res = client.post(
        f"/api/events/{event_id}/register",
        headers=test_setup["student1_header"],
        json={"registration_type": "individual"},
    )
    assert ind_res.status_code == 400


# =============================================================================
# 4. Live Event Access, Submissions & Point Isolation Tests
# =============================================================================

def test_live_event_access_and_submission(client, test_setup, event_setup):
    """Students can access challenges and submit flags only during LIVE event."""
    now = _utc_now()
    # 1. Create event with open registration window
    ev_res = client.post(
        "/api/events",
        headers=test_setup["admin_header"],
        json={
            "name": "Live Flag Competition",
            "start_at": (now + timedelta(hours=1)).isoformat(),
            "end_at": (now + timedelta(hours=4)).isoformat(),
            "registration_start_at": (now - timedelta(hours=2)).isoformat(),
            "registration_end_at": (now + timedelta(hours=1)).isoformat(),
        },
    )
    assert ev_res.status_code == 201
    event_id = ev_res.json()["id"]

    # 2. Add challenge with 500 points override
    client.post(
        f"/api/events/{event_id}/challenges",
        headers=test_setup["admin_header"],
        json={
            "challenge_id": event_setup["challenge_id"],
            "display_order": 1,
            "points_override": 500,
        },
    )

    # 3. Register student1 while registration is open
    reg_res = client.post(
        f"/api/events/{event_id}/register",
        headers=test_setup["student1_header"],
        json={"registration_type": "individual"},
    )
    assert reg_res.status_code == 201

    # 4. While event is UPCOMING, challenge access is forbidden even for registered students
    upcoming_challs = client.get(f"/api/events/{event_id}/challenges", headers=test_setup["student1_header"])
    assert upcoming_challs.status_code == 403
    assert "only accessible when the event is live" in upcoming_challs.json()["detail"].lower()

    # 5. Make event LIVE by updating start_at
    client.put(
        f"/api/events/{event_id}",
        headers=test_setup["admin_header"],
        json={
            "start_at": (now - timedelta(minutes=30)).isoformat(),
            "registration_start_at": (now - timedelta(hours=2)).isoformat(),
            "registration_end_at": (now - timedelta(minutes=30)).isoformat(),
        },
    )

    # 6. Unregistered student2 cannot view challenges
    unreg_challs = client.get(f"/api/events/{event_id}/challenges", headers=test_setup["student2_header"])
    assert unreg_challs.status_code == 403

    # 7. Registered student1 can now view challenges
    reg_challs = client.get(f"/api/events/{event_id}/challenges", headers=test_setup["student1_header"])
    assert reg_challs.status_code == 200
    assert len(reg_challs.json()) == 1
    assert reg_challs.json()[0]["points"] == 500

    # 8. Submit flag to event
    sub_res = client.post(
        f"/api/events/{event_id}/submissions",
        headers=test_setup["student1_header"],
        json={
            "challenge_id": event_setup["challenge_id"],
            "flag": event_setup["flag"],
        },
    )
    assert sub_res.status_code == 200
    assert sub_res.json()["is_correct"] is True
    assert sub_res.json()["points_awarded"] == 500

    import time
    time.sleep(2.1)

    # 9. Duplicate solve in event awards 0
    dup_sub = client.post(
        f"/api/events/{event_id}/submissions",
        headers=test_setup["student1_header"],
        json={
            "challenge_id": event_setup["challenge_id"],
            "flag": event_setup["flag"],
        },
    )
    assert dup_sub.status_code == 200
    assert dup_sub.json()["points_awarded"] == 0

    # 10. Verify event solves do NOT count on global practice leaderboard
    global_res = client.get("/api/leaderboard/global")
    global_items = global_res.json()["items"]
    s1_practice = [i for i in global_items if i["username"] == "student1"]
    assert len(s1_practice) == 0


# =============================================================================
# 5. Scoreboard Freeze Tests
# =============================================================================

def test_event_scoreboard_freeze_and_unfreeze(client, test_setup, event_setup):
    """Scoreboard freeze locks public view while permitting admin live view and subsequent unfreeze."""
    now = _utc_now()
    ev_res = client.post(
        "/api/events",
        headers=test_setup["admin_header"],
        json={
            "name": "Freeze Championship",
            "start_at": (now + timedelta(hours=1)).isoformat(),
            "end_at": (now + timedelta(hours=4)).isoformat(),
            "registration_start_at": (now - timedelta(hours=2)).isoformat(),
            "registration_end_at": (now + timedelta(hours=1)).isoformat(),
        },
    )
    assert ev_res.status_code == 201
    event_id = ev_res.json()["id"]

    client.post(
        f"/api/events/{event_id}/challenges",
        headers=test_setup["admin_header"],
        json={"challenge_id": event_setup["challenge_id"], "points_override": 100},
    )

    # Register student1 and student2 while registration is open
    client.post(f"/api/events/{event_id}/register", headers=test_setup["student1_header"], json={"registration_type": "individual"})
    client.post(f"/api/events/{event_id}/register", headers=test_setup["student2_header"], json={"registration_type": "individual"})

    # Transition event to LIVE
    client.put(
        f"/api/events/{event_id}",
        headers=test_setup["admin_header"],
        json={
            "start_at": (now - timedelta(minutes=30)).isoformat(),
            "registration_start_at": (now - timedelta(hours=2)).isoformat(),
            "registration_end_at": (now - timedelta(minutes=30)).isoformat(),
        },
    )

    # Student 1 solves BEFORE freeze
    client.post(
        f"/api/events/{event_id}/submissions",
        headers=test_setup["student1_header"],
        json={"challenge_id": event_setup["challenge_id"], "flag": event_setup["flag"]},
    )

    # Leaderboard before freeze
    lb1 = client.get(f"/api/events/{event_id}/leaderboard")
    assert lb1.json()["is_scoreboard_frozen"] is False
    assert lb1.json()["items"][0]["participant_name"] == "student1"
    assert lb1.json()["items"][0]["total_points"] == 100

    # Admin freezes scoreboard
    freeze_res = client.post(f"/api/events/{event_id}/freeze-scoreboard", headers=test_setup["admin_header"])
    assert freeze_res.status_code == 200
    assert freeze_res.json()["is_scoreboard_frozen"] is True

    # Student 2 solves AFTER freeze
    chal2_res = client.post(
        "/api/challenges",
        headers=test_setup["admin_header"],
        json={
            "title": "Post Freeze Chall",
            "description": "solve during freeze",
            "category_id": event_setup["category_id"],
            "difficulty": "easy",
            "points": 300,
            "flag": "flag{freeze_solve_123}",
            "is_active": True,
        },
    )
    chal2_id = chal2_res.json()["id"]
    client.post(
        f"/api/events/{event_id}/challenges",
        headers=test_setup["admin_header"],
        json={"challenge_id": chal2_id, "points_override": 300},
    )

    client.post(
        f"/api/events/{event_id}/submissions",
        headers=test_setup["student2_header"],
        json={"challenge_id": chal2_id, "flag": "flag{freeze_solve_123}"},
    )

    # Public requests leaderboard -> frozen at freeze time!
    # Student 2's post-freeze solve is not visible
    pub_lb = client.get(f"/api/events/{event_id}/leaderboard")
    assert pub_lb.json()["is_scoreboard_frozen"] is True
    s2_pub = [e for e in pub_lb.json()["items"] if e["participant_name"] == "student2"][0]
    assert s2_pub["total_points"] == 0

    # Admin requests leaderboard -> live view includes post-freeze solve
    admin_lb = client.get(f"/api/events/{event_id}/leaderboard", headers=test_setup["admin_header"])
    s2_admin = [e for e in admin_lb.json()["items"] if e["participant_name"] == "student2"][0]
    assert s2_admin["total_points"] == 300

    # Admin unfreezes scoreboard
    unfreeze_res = client.post(f"/api/events/{event_id}/unfreeze-scoreboard", headers=test_setup["admin_header"])
    assert unfreeze_res.status_code == 200

    # Public view is now unfrozen and updated
    pub_lb2 = client.get(f"/api/events/{event_id}/leaderboard")
    assert pub_lb2.json()["is_scoreboard_frozen"] is False
    s2_updated = [e for e in pub_lb2.json()["items"] if e["participant_name"] == "student2"][0]
    assert s2_updated["total_points"] == 300


# =============================================================================
# 6. Writeup AFTER_EVENT Visibility Integration
# =============================================================================

def test_after_event_writeup_visibility(client, db_session, test_setup, event_setup):
    """Writeup with AFTER_EVENT visibility unlocks only after event ends."""
    now = _utc_now()

    # Create event ending in the future (LIVE)
    ev_res = client.post(
        "/api/events",
        headers=test_setup["admin_header"],
        json={
            "name": "Writeup Event Test",
            "start_at": (now - timedelta(hours=2)).isoformat(),
            "end_at": (now + timedelta(hours=2)).isoformat(),
        },
    )
    assert ev_res.status_code == 201
    event_id = ev_res.json()["id"]

    # Link challenge to event
    client.post(
        f"/api/events/{event_id}/challenges",
        headers=test_setup["admin_header"],
        json={"challenge_id": event_setup["challenge_id"]},
    )

    # Admin creates AFTER_EVENT writeup
    wu_res = client.post(
        f"/api/challenges/{event_setup['challenge_id']}/writeups",
        headers=test_setup["admin_header"],
        json={
            "title": "Official Solution",
            "content": "Step 1: check magic bytes; Step 2: restore png header.",
            "visibility": "after_event",
        },
    )
    assert wu_res.status_code == 200
    writeup_id = wu_res.json()["id"]

    # Student cannot view writeup while event is active (returns 403)
    writeup_res = client.get(
        f"/api/challenges/{event_setup['challenge_id']}/writeups/{writeup_id}",
        headers=test_setup["student1_header"],
    )
    assert writeup_res.status_code == 403
    assert "event has not concluded" in writeup_res.json()["detail"].lower()

    # List writeups hides it while event is active
    list_res = client.get(
        f"/api/challenges/{event_setup['challenge_id']}/writeups",
        headers=test_setup["student1_header"],
    )
    assert list_res.status_code == 200
    assert len(list_res.json()) == 0

    # Update event to have ended in past
    client.put(
        f"/api/events/{event_id}",
        headers=test_setup["admin_header"],
        json={
            "end_at": (now - timedelta(minutes=5)).isoformat(),
            "status": "ended",
        },
    )

    # Student can now view writeup!
    unlocked_res = client.get(
        f"/api/challenges/{event_setup['challenge_id']}/writeups/{writeup_id}",
        headers=test_setup["student1_header"],
    )
    assert unlocked_res.status_code == 200
    assert "magic bytes" in unlocked_res.json()["content"]

    # List writeups also returns it now
    list_res2 = client.get(
        f"/api/challenges/{event_setup['challenge_id']}/writeups",
        headers=test_setup["student1_header"],
    )
    assert list_res2.status_code == 200
    assert len(list_res2.json()) == 1
