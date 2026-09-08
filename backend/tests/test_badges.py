import uuid
from datetime import datetime, date, timedelta, timezone
import pytest

from app.models.user import User, UserRole
from app.models.category import Category
from app.models.challenge import Challenge, ChallengeDifficulty, ChallengeType
from app.models.event import Event, EventStatus
from app.models.activity import UserActivity, ActivityType
from app.models.badge import Badge, UserBadge, CriteriaType
from app.core.security import create_access_token, hash_password
from app.services.challenge_service import hash_flag
from app.services.badge_service import BadgeService
from app.config import settings


@pytest.fixture(autouse=True)
def disable_submission_cooldown(monkeypatch):
    """Disable submission cooldown in badge tests for rapid testing."""
    monkeypatch.setattr(settings, "SUBMISSION_COOLDOWN_SECONDS", 0)


@pytest.fixture
def badge_test_setup(db_session):
    """Sets up admin, student, categories, challenges, badges, and auth tokens."""
    admin_user = User(
        username="admin_badge",
        email="admin_badge@test.edu",
        hashed_password=hash_password("AdminPass123!"),
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True,
    )
    student_alice = User(
        username="alice_badge",
        email="alice_badge@test.edu",
        hashed_password=hash_password("AlicePass123!"),
        role=UserRole.STUDENT,
        college="OWASP College",
        name="Alice Allison",
        is_active=True,
        is_verified=True,
    )
    student_bob = User(
        username="bob_badge",
        email="bob_badge@test.edu",
        hashed_password=hash_password("BobPass123!"),
        role=UserRole.STUDENT,
        college="OWASP College",
        name="Bob Builder",
        is_active=True,
        is_verified=True,
    )
    db_session.add_all([admin_user, student_alice, student_bob])
    db_session.flush()

    cat1 = Category(name="Web Exploitation", description="Web security")
    cat2 = Category(name="Cryptography", description="Crypto puzzles")
    cat3 = Category(name="Forensics", description="Memory and disk forensics")
    db_session.add_all([cat1, cat2, cat3])
    db_session.flush()

    # Create several challenges with known flags
    challenges = []
    for i in range(1, 7):
        ch = Challenge(
            title=f"Challenge {i}",
            description=f"Desc {i}",
            category_id=cat1.id if i <= 2 else (cat2.id if i <= 4 else cat3.id),
            difficulty=ChallengeDifficulty.EASY,
            challenge_type=ChallengeType.STATIC,
            points=200,
            flag_hash=hash_flag(f"flag{{challenge_{i}}}"),
            is_active=True,
        )
        challenges.append(ch)
    db_session.add_all(challenges)
    db_session.flush()

    # Create standard badge definitions in DB
    b_first_solve = Badge(
        name="First Blood",
        slug="first-blood",
        description="Solved first challenge.",
        icon="drop-crosshair",
        criteria_type=CriteriaType.FIRST_SOLVE.value,
        criteria_value=1,
        is_active=True,
    )
    b_solve_5 = Badge(
        name="Novice Hacker",
        slug="novice-hacker",
        description="Solved 5 challenges.",
        icon="terminal",
        criteria_type=CriteriaType.SOLVE_COUNT.value,
        criteria_value=5,
        is_active=True,
    )
    b_points_1000 = Badge(
        name="Point Hunter",
        slug="point-hunter",
        description="Reached 1000 points.",
        icon="target",
        criteria_type=CriteriaType.POINTS_REACHED.value,
        criteria_value=1000,
        is_active=True,
    )
    b_cat_3 = Badge(
        name="Cyber Explorer",
        slug="cyber-explorer",
        description="Solved challenges across 3 categories.",
        icon="compass",
        criteria_type=CriteriaType.CATEGORY_SOLVES.value,
        criteria_value=3,
        is_active=True,
    )
    b_streak_3 = Badge(
        name="Streak Starter",
        slug="streak-starter",
        description="3-day streak.",
        icon="flame",
        criteria_type=CriteriaType.STREAK_DAYS.value,
        criteria_value=3,
        is_active=True,
    )
    b_event_part = Badge(
        name="Event Participant",
        slug="event-participant",
        description="Participate in an event.",
        icon="trophy",
        criteria_type=CriteriaType.EVENT_PARTICIPATION.value,
        criteria_value=1,
        is_active=True,
    )
    db_session.add_all([b_first_solve, b_solve_5, b_points_1000, b_cat_3, b_streak_3, b_event_part])
    db_session.commit()

    admin_token = create_access_token({"sub": str(admin_user.id)})
    alice_token = create_access_token({"sub": str(student_alice.id)})
    bob_token = create_access_token({"sub": str(student_bob.id)})

    return {
        "admin": admin_user,
        "alice": student_alice,
        "bob": student_bob,
        "admin_token": admin_token,
        "alice_token": alice_token,
        "bob_token": bob_token,
        "challenges": challenges,
        "badges": {
            "first_solve": b_first_solve,
            "solve_5": b_solve_5,
            "points_1000": b_points_1000,
            "cat_3": b_cat_3,
            "streak_3": b_streak_3,
            "event_part": b_event_part,
        }
    }


# =============================================================================
# 1. Admin Badge Management Tests
# =============================================================================

def test_admin_create_badge_success(client, badge_test_setup):
    admin_token = badge_test_setup["admin_token"]
    payload = {
        "name": "Custom Elite",
        "slug": "custom-elite",
        "description": "Earned by achieving great things.",
        "icon": "shield-check",
        "criteria_type": "solve_count",
        "criteria_value": 50,
        "is_active": True,
    }
    resp = client.post(
        "/api/badges",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Custom Elite"
    assert data["slug"] == "custom-elite"
    assert data["criteria_type"] == "solve_count"
    assert data["criteria_value"] == 50


def test_student_cannot_create_or_update_badge(client, badge_test_setup):
    alice_token = badge_test_setup["alice_token"]
    badge_id = badge_test_setup["badges"]["first_solve"].id

    # Create attempt
    resp_create = client.post(
        "/api/badges",
        json={
            "name": "Hacked Badge",
            "slug": "hacked-badge",
            "description": "Should fail",
            "icon": "alert",
            "criteria_type": "first_solve",
            "criteria_value": 1,
        },
        headers={"Authorization": f"Bearer {alice_token}"}
    )
    assert resp_create.status_code == 403

    # Update attempt
    resp_update = client.put(
        f"/api/badges/{badge_id}",
        json={"name": "Hacked Name"},
        headers={"Authorization": f"Bearer {alice_token}"}
    )
    assert resp_update.status_code == 403

    # Delete attempt
    resp_del = client.delete(
        f"/api/badges/{badge_id}",
        headers={"Authorization": f"Bearer {alice_token}"}
    )
    assert resp_del.status_code == 403


def test_duplicate_badge_slug_rejected(client, badge_test_setup):
    admin_token = badge_test_setup["admin_token"]
    payload = {
        "name": "Duplicate First Blood",
        "slug": "first-blood",  # Already exists
        "description": "Conflict attempt",
        "icon": "drop",
        "criteria_type": "first_solve",
        "criteria_value": 1,
    }
    resp = client.post(
        "/api/badges",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 409


def test_admin_update_badge(client, badge_test_setup):
    admin_token = badge_test_setup["admin_token"]
    badge_id = badge_test_setup["badges"]["first_solve"].id

    resp = client.put(
        f"/api/badges/{badge_id}",
        json={
            "description": "Updated description for first blood.",
            "criteria_value": 2,
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["description"] == "Updated description for first blood."
    assert data["criteria_value"] == 2


def test_admin_delete_or_deactivate_badge(client, db_session, badge_test_setup):
    admin_token = badge_test_setup["admin_token"]
    alice = badge_test_setup["alice"]

    # 1. Badge never awarded -> should hard delete
    temp_badge = Badge(
        name="Temp Badge",
        slug="temp-badge",
        description="Never awarded",
        icon="temp",
        criteria_type="solve_count",
        criteria_value=10,
        is_active=True,
    )
    db_session.add(temp_badge)
    db_session.commit()
    t_id = temp_badge.id

    resp_del = client.delete(
        f"/api/badges/{t_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp_del.status_code == 200
    assert resp_del.json()["action"] == "deleted"

    # 2. Badge already awarded to user -> should soft deactivate
    awarded_badge = badge_test_setup["badges"]["first_solve"]
    ub = UserBadge(user_id=alice.id, badge_id=awarded_badge.id)
    db_session.add(ub)
    db_session.commit()

    resp_deact = client.delete(
        f"/api/badges/{awarded_badge.id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp_deact.status_code == 200
    assert resp_deact.json()["action"] == "deactivated"
    db_session.refresh(awarded_badge)
    assert awarded_badge.is_active is False


def test_badge_list_active_and_inactive(client, db_session, badge_test_setup):
    admin_token = badge_test_setup["admin_token"]
    alice_token = badge_test_setup["alice_token"]

    inactive_badge = Badge(
        name="Hidden Badge",
        slug="hidden-badge",
        description="Inactive test badge",
        icon="ghost",
        criteria_type="first_solve",
        criteria_value=1,
        is_active=False,
    )
    db_session.add(inactive_badge)
    db_session.commit()

    # Public / Student list: should not include inactive
    resp_student = client.get("/api/badges", headers={"Authorization": f"Bearer {alice_token}"})
    assert resp_student.status_code == 200
    slugs = [b["slug"] for b in resp_student.json()]
    assert "hidden-badge" not in slugs

    # Admin list with include_inactive=True: should include inactive
    resp_admin = client.get("/api/badges?include_inactive=true", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp_admin.status_code == 200
    admin_slugs = [b["slug"] for b in resp_admin.json()]
    assert "hidden-badge" in admin_slugs


# =============================================================================
# 2. Automated Badge Awarding & Criteria Unlocks
# =============================================================================

def test_first_solve_badge_awarded_on_solve(client, db_session, badge_test_setup):
    alice = badge_test_setup["alice"]
    alice_token = badge_test_setup["alice_token"]
    ch1 = badge_test_setup["challenges"][0]

    # Verify initially no badges
    resp_init = client.get("/api/profile/me/badges", headers={"Authorization": f"Bearer {alice_token}"})
    assert resp_init.status_code == 200
    assert len(resp_init.json()) == 0

    # Submit correct flag for challenge 1
    resp_sub = client.post(
        "/api/submissions",
        json={"challenge_id": str(ch1.id), "flag": "flag{challenge_1}"},
        headers={"Authorization": f"Bearer {alice_token}"}
    )
    assert resp_sub.status_code == 200
    assert resp_sub.json()["is_correct"] is True

    # Check that "first-blood" badge is now unlocked
    resp_badges = client.get("/api/profile/me/badges", headers={"Authorization": f"Bearer {alice_token}"})
    assert resp_badges.status_code == 200
    earned = resp_badges.json()
    assert len(earned) == 1
    assert earned[0]["slug"] == "first-blood"


def test_solve_count_and_points_badge_threshold(client, db_session, badge_test_setup):
    alice = badge_test_setup["alice"]
    alice_token = badge_test_setup["alice_token"]
    challenges = badge_test_setup["challenges"]

    # Solve challenges 1 to 5 (each 200 pts => 5 solves, 1000 total points)
    for i in range(5):
        resp = client.post(
            "/api/submissions",
            json={"challenge_id": str(challenges[i].id), "flag": f"flag{{challenge_{i+1}}}"},
            headers={"Authorization": f"Bearer {alice_token}"}
        )
        assert resp.status_code == 200
        assert resp.json()["is_correct"] is True

    # Check earned badges: should have "first-blood", "novice-hacker" (5 solves), and "point-hunter" (1000 pts)
    resp_badges = client.get("/api/profile/me/badges", headers={"Authorization": f"Bearer {alice_token}"})
    assert resp_badges.status_code == 200
    earned_slugs = {b["slug"] for b in resp_badges.json()}
    assert "first-blood" in earned_slugs
    assert "novice-hacker" in earned_slugs
    assert "point-hunter" in earned_slugs


def test_category_solves_badge(client, db_session, badge_test_setup):
    alice = badge_test_setup["alice"]
    alice_token = badge_test_setup["alice_token"]
    challenges = badge_test_setup["challenges"]

    # Challenge 1 is Cat 1, Challenge 3 is Cat 2, Challenge 5 is Cat 3
    for idx in [0, 2, 4]:
        client.post(
            "/api/submissions",
            json={"challenge_id": str(challenges[idx].id), "flag": f"flag{{challenge_{idx+1}}}"},
            headers={"Authorization": f"Bearer {alice_token}"}
        )

    resp_badges = client.get("/api/profile/me/badges", headers={"Authorization": f"Bearer {alice_token}"})
    earned_slugs = {b["slug"] for b in resp_badges.json()}
    assert "cyber-explorer" in earned_slugs


def test_streak_days_badge(client, db_session, badge_test_setup):
    alice = badge_test_setup["alice"]
    alice_token = badge_test_setup["alice_token"]

    # Insert 3 distinct active calendar days of activity for Alice
    now = datetime.now(timezone.utc)
    for days_ago in [2, 1, 0]:
        act = UserActivity(
            user_id=alice.id,
            activity_type=ActivityType.CHALLENGE_SOLVED.value,
            created_at=now - timedelta(days=days_ago),
        )
        db_session.add(act)
    db_session.commit()

    # Trigger evaluation
    BadgeService.evaluate_and_award_badges(db_session, alice.id)

    resp_badges = client.get("/api/profile/me/badges", headers={"Authorization": f"Bearer {alice_token}"})
    earned_slugs = {b["slug"] for b in resp_badges.json()}
    assert "streak-starter" in earned_slugs


def test_event_participation_badge(client, db_session, badge_test_setup):
    alice_token = badge_test_setup["alice_token"]

    # Create an upcoming event
    now = datetime.now(timezone.utc)
    event = Event(
        name="OWASP Hackathon 2026",
        slug="owasp-hackathon-2026",
        description="Annual club event",
        start_at=now + timedelta(hours=2),
        end_at=now + timedelta(hours=10),
        registration_start_at=now - timedelta(hours=1),
        registration_end_at=now + timedelta(hours=2),
        is_active=True,
    )
    db_session.add(event)
    db_session.commit()

    # Alice registers for the event
    reg_resp = client.post(
        f"/api/events/{event.id}/register",
        json={"registration_type": "individual"},
        headers={"Authorization": f"Bearer {alice_token}"}
    )
    assert reg_resp.status_code == 201

    # Badge "event-participant" should be awarded automatically
    resp_badges = client.get("/api/profile/me/badges", headers={"Authorization": f"Bearer {alice_token}"})
    earned_slugs = {b["slug"] for b in resp_badges.json()}
    assert "event-participant" in earned_slugs


# =============================================================================
# 3. Idempotency & Duplicate Protection
# =============================================================================

def test_badge_idempotency_duplicate_protection(client, db_session, badge_test_setup):
    alice = badge_test_setup["alice"]
    alice_token = badge_test_setup["alice_token"]
    ch1 = badge_test_setup["challenges"][0]

    # First solve
    client.post(
        "/api/submissions",
        json={"challenge_id": str(ch1.id), "flag": "flag{challenge_1}"},
        headers={"Authorization": f"Bearer {alice_token}"}
    )

    # Re-run badge evaluation 5 times explicitly
    for _ in range(5):
        new_badges = BadgeService.evaluate_and_award_badges(db_session, alice.id)
        assert len(new_badges) == 0

    # Verify in DB user_badges has exactly 1 entry for this user and badge
    badge_fb = badge_test_setup["badges"]["first_solve"]
    count = db_session.query(UserBadge).filter(
        UserBadge.user_id == alice.id,
        UserBadge.badge_id == badge_fb.id
    ).count()
    assert count == 1


# =============================================================================
# 4. Badge Progress Tracking
# =============================================================================

def test_badge_progress_calculation(client, db_session, badge_test_setup):
    alice = badge_test_setup["alice"]
    alice_token = badge_test_setup["alice_token"]
    challenges = badge_test_setup["challenges"]

    # Initially at 0 solves
    resp_prog_init = client.get("/api/profile/me/badge-progress", headers={"Authorization": f"Bearer {alice_token}"})
    assert resp_prog_init.status_code == 200
    prog_map = {item["slug"]: item for item in resp_prog_init.json()}
    assert prog_map["first-blood"]["current_value"] == 0
    assert prog_map["first-blood"]["progress_percentage"] == 0.0
    assert prog_map["first-blood"]["is_unlocked"] is False
    assert prog_map["novice-hacker"]["current_value"] == 0
    assert prog_map["novice-hacker"]["required_value"] == 5

    # Solve 2 challenges
    for i in range(2):
        client.post(
            "/api/submissions",
            json={"challenge_id": str(challenges[i].id), "flag": f"flag{{challenge_{i+1}}}"},
            headers={"Authorization": f"Bearer {alice_token}"}
        )

    resp_prog_mid = client.get("/api/profile/me/badge-progress", headers={"Authorization": f"Bearer {alice_token}"})
    prog_map2 = {item["slug"]: item for item in resp_prog_mid.json()}

    # First blood is unlocked (100%)
    assert prog_map2["first-blood"]["is_unlocked"] is True
    assert prog_map2["first-blood"]["progress_percentage"] == 100.0

    # Novice hacker (requires 5, solved 2 => 40.0%)
    assert prog_map2["novice-hacker"]["current_value"] == 2
    assert prog_map2["novice-hacker"]["required_value"] == 5
    assert prog_map2["novice-hacker"]["progress_percentage"] == 40.0
    assert prog_map2["novice-hacker"]["is_unlocked"] is False

    # Test single badge progress route
    badge_novice_id = badge_test_setup["badges"]["solve_5"].id
    single_resp = client.get(f"/api/profile/me/badges/{badge_novice_id}/progress", headers={"Authorization": f"Bearer {alice_token}"})
    assert single_resp.status_code == 200
    assert single_resp.json()["progress_percentage"] == 40.0


# =============================================================================
# 5. Profile Integration & Public Privacy
# =============================================================================

def test_profile_shows_badges_count_and_recent_badges(client, db_session, badge_test_setup):
    alice = badge_test_setup["alice"]
    alice_token = badge_test_setup["alice_token"]
    bob_token = badge_test_setup["bob_token"]
    ch1 = badge_test_setup["challenges"][0]

    # Alice solves challenge 1
    client.post(
        "/api/submissions",
        json={"challenge_id": str(ch1.id), "flag": "flag{challenge_1}"},
        headers={"Authorization": f"Bearer {alice_token}"}
    )

    # Alice checks her own profile
    resp_me = client.get("/api/profile/me", headers={"Authorization": f"Bearer {alice_token}"})
    assert resp_me.status_code == 200
    me_data = resp_me.json()
    assert me_data["badges_count"] == 1
    assert len(me_data["recent_badges"]) == 1
    assert me_data["recent_badges"][0]["slug"] == "first-blood"

    # Bob checks Alice's public profile
    resp_pub = client.get(f"/api/profile/{alice.id}", headers={"Authorization": f"Bearer {bob_token}"})
    assert resp_pub.status_code == 200
    pub_data = resp_pub.json()
    assert pub_data["badges_count"] == 1
    assert len(pub_data["recent_badges"]) == 1
    assert pub_data["recent_badges"][0]["slug"] == "first-blood"
    assert "email" not in pub_data  # Privacy verification

    # Public user badges route
    resp_user_badges = client.get(f"/api/profile/{alice.id}/badges", headers={"Authorization": f"Bearer {bob_token}"})
    assert resp_user_badges.status_code == 200
    assert len(resp_user_badges.json()) == 1


# =============================================================================
# 6. Admin Badge Users & Stats
# =============================================================================

def test_get_badge_users_and_stats(client, db_session, badge_test_setup):
    admin_token = badge_test_setup["admin_token"]
    alice = badge_test_setup["alice"]
    alice_token = badge_test_setup["alice_token"]
    ch1 = badge_test_setup["challenges"][0]
    badge_fb = badge_test_setup["badges"]["first_solve"]

    # Solve by Alice
    client.post(
        "/api/submissions",
        json={"challenge_id": str(ch1.id), "flag": "flag{challenge_1}"},
        headers={"Authorization": f"Bearer {alice_token}"}
    )

    # Admin queries badge users
    resp_users = client.get(
        f"/api/badges/{badge_fb.id}/users",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp_users.status_code == 200
    users = resp_users.json()
    assert len(users) == 1
    assert users[0]["username"] == alice.username
    assert "hashed_password" not in users[0]
    assert "email" not in users[0]

    # Badge stats
    resp_stats = client.get(f"/api/badges/{badge_fb.id}/stats")
    assert resp_stats.status_code == 200
    assert resp_stats.json()["total_users_awarded"] == 1


# =============================================================================
# 7. Zero Score Impact Guarantee
# =============================================================================

def test_scoring_zero_impact(client, db_session, badge_test_setup):
    alice = badge_test_setup["alice"]
    alice_token = badge_test_setup["alice_token"]
    ch1 = badge_test_setup["challenges"][0]

    # Submit flag (ch1 is 200 points)
    resp = client.post(
        "/api/submissions",
        json={"challenge_id": str(ch1.id), "flag": "flag{challenge_1}"},
        headers={"Authorization": f"Bearer {alice_token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["points_awarded"] == 200

    # Check score via profile endpoint
    resp_score = client.get("/api/profile/me", headers={"Authorization": f"Bearer {alice_token}"})
    assert resp_score.status_code == 200
    assert resp_score.json()["total_points"] == 200

    # Check leaderboard
    resp_lb = client.get("/api/leaderboard/global")
    assert resp_lb.status_code == 200
    items = resp_lb.json()["items"]
    alice_entry = next((e for e in items if e["user_id"] == str(alice.id)), None)
    assert alice_entry is not None
    assert alice_entry["total_points"] == 200
