import json
import uuid
from datetime import datetime, date, timedelta, timezone
import pytest
from app.models.user import User, UserRole
from app.models.category import Category
from app.models.challenge import Challenge, ChallengeDifficulty, ChallengeType
from app.models.event import Event, EventStatus
from app.models.activity import UserActivity, ActivityType
from app.models.team import Team, TeamMember
from app.core.security import create_access_token, hash_password
from app.services.challenge_service import hash_flag
from app.services.activity_service import ActivityService
from app.services.streak_service import StreakService


@pytest.fixture
def profile_test_setup(db_session):
    """Sets up student users, categories, challenges, and auth tokens."""
    cat_web = Category(name="Web Exploitation", description="Web security")
    cat_crypto = Category(name="Cryptography", description="Crypto puzzles")
    db_session.add_all([cat_web, cat_crypto])
    db_session.flush()

    user_alice = User(
        username="alice_profile",
        email="alice@test.edu",
        hashed_password=hash_password("AliceSecure123!"),
        role=UserRole.STUDENT,
        college="Tech University",
        name="Alice Allison",
        bio="Aspiring security researcher",
        is_active=True,
        is_verified=True,
    )
    user_bob = User(
        username="bob_profile",
        email="bob@test.edu",
        hashed_password=hash_password("BobSecure123!"),
        role=UserRole.STUDENT,
        college="Tech University",
        name="Bob Roberts",
        bio="Binary wizard",
        is_active=True,
        is_verified=True,
    )
    user_inactive = User(
        username="inactive_user",
        email="inactive@test.edu",
        hashed_password=hash_password("InactivePass123!"),
        role=UserRole.STUDENT,
        is_active=False,
    )
    db_session.add_all([user_alice, user_bob, user_inactive])
    db_session.flush()

    # Practice challenges
    chall_web = Challenge(
        title="SQLi 101",
        description="Exploit the login",
        category_id=cat_web.id,
        difficulty=ChallengeDifficulty.EASY,
        challenge_type=ChallengeType.STATIC,
        points=100,
        flag_hash=hash_flag("FLAG{sqli_easy_solve}"),
        is_active=True,
    )
    chall_crypto = Challenge(
        title="RSA Basics",
        description="Factor the modulus",
        category_id=cat_crypto.id,
        difficulty=ChallengeDifficulty.MEDIUM,
        challenge_type=ChallengeType.STATIC,
        points=250,
        flag_hash=hash_flag("FLAG{rsa_medium_solve}"),
        is_active=True,
    )
    db_session.add_all([chall_web, chall_crypto])
    db_session.commit()

    token_alice = create_access_token({"sub": str(user_alice.id), "role": user_alice.role.value})
    token_bob = create_access_token({"sub": str(user_bob.id), "role": user_bob.role.value})

    return {
        "alice": user_alice,
        "bob": user_bob,
        "inactive": user_inactive,
        "token_alice": token_alice,
        "token_bob": token_bob,
        "cat_web": cat_web,
        "cat_crypto": cat_crypto,
        "chall_web": chall_web,
        "chall_crypto": chall_crypto,
    }


# ==========================================
# 1. PROFILE TESTS
# ==========================================

def test_get_my_profile_unauthenticated(client):
    """GET /api/profile/me requires valid bearer authentication."""
    resp = client.get("/api/profile/me")
    assert resp.status_code == 401


def test_get_my_profile_authenticated(client, profile_test_setup):
    """GET /api/profile/me returns private account info without leaking credentials."""
    headers = {"Authorization": f"Bearer {profile_test_setup['token_alice']}"}
    resp = client.get("/api/profile/me", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["username"] == "alice_profile"
    assert data["email"] == "alice@test.edu"
    assert data["role"] == "student"
    assert data["name"] == "Alice Allison"
    assert data["bio"] == "Aspiring security researcher"
    assert data["college"] == "Tech University"
    assert data["total_points"] == 0
    assert data["challenges_solved"] == 0
    assert "password" not in str(data).lower()
    assert "hash" not in str(data).lower()


def test_get_public_profile(client, profile_test_setup):
    """GET /api/profile/{user_id} returns public profile and strips private email/auth details."""
    alice = profile_test_setup["alice"]
    resp = client.get(f"/api/profile/{alice.id}")
    assert resp.status_code == 200
    data = resp.json()

    assert data["username"] == "alice_profile"
    assert data["name"] == "Alice Allison"
    assert data["college"] == "Tech University"
    assert data["bio"] == "Aspiring security researcher"
    # Private fields MUST NOT be present
    assert "email" not in data
    assert "hashed_password" not in data
    assert "role" not in data


def test_get_public_profile_not_found(client, profile_test_setup):
    """Non-existent or inactive user returns 404."""
    random_id = uuid.uuid4()
    resp = client.get(f"/api/profile/{random_id}")
    assert resp.status_code == 404

    inactive = profile_test_setup["inactive"]
    resp_inactive = client.get(f"/api/profile/{inactive.id}")
    assert resp_inactive.status_code == 404


def test_update_own_profile(client, profile_test_setup):
    """PUT /api/profile/me allows user to update name, bio, college, and avatar_url."""
    headers = {"Authorization": f"Bearer {profile_test_setup['token_alice']}"}
    payload = {
        "name": "Alice A. Cooper",
        "bio": "Specialized in reverse engineering and web exploitation.",
        "college": "OWASP Global Academy",
        "avatar_url": "https://example.com/avatar.png",
    }
    resp = client.put("/api/profile/me", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["name"] == "Alice A. Cooper"
    assert data["bio"] == "Specialized in reverse engineering and web exploitation."
    assert data["college"] == "OWASP Global Academy"
    assert data["avatar_url"] == "https://example.com/avatar.png"


def test_update_profile_security_protection(client, profile_test_setup, db_session):
    """Profile update rejects role changes, score tampering, and sanitizes XSS."""
    headers = {"Authorization": f"Bearer {profile_test_setup['token_alice']}"}
    payload = {
        "name": "<script>alert('xss')</script>Clean Name",
        "bio": "<b>Bold bio</b><iframe src='bad.site'></iframe>",
        "role": "admin",
        "total_points": 999999,
        "is_verified": True,
    }
    resp = client.put("/api/profile/me", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    # Verify HTML tags were stripped
    assert "<script>" not in data["name"]
    assert "Clean Name" in data["name"]
    assert "<iframe" not in data["bio"]
    assert "Bold bio" in data["bio"]

    # Verify role and points were NOT changed
    assert data["role"] == "student"
    assert data["total_points"] == 0

    # Double check database row directly
    db_user = db_session.query(User).filter(User.id == profile_test_setup["alice"].id).first()
    assert db_user.role == UserRole.STUDENT


def test_invalid_avatar_url_scheme(client, profile_test_setup):
    """PUT /api/profile/me rejects javascript: URL scheme for avatar."""
    headers = {"Authorization": f"Bearer {profile_test_setup['token_alice']}"}
    resp = client.put("/api/profile/me", json={"avatar_url": "javascript:alert(1)"}, headers=headers)
    assert resp.status_code == 422


# ==========================================
# 2. SOLVED CHALLENGES & LEADERBOARD INTEGRATION
# ==========================================

def test_solved_challenge_history(client, profile_test_setup):
    """Successful solve records solve history, updates score, and hides flags/hashes."""
    alice_headers = {"Authorization": f"Bearer {profile_test_setup['token_alice']}"}
    chall = profile_test_setup["chall_web"]

    # 1. Initially no solves
    resp_init = client.get("/api/profile/me/solved", headers=alice_headers)
    assert resp_init.status_code == 200
    assert resp_init.json() == []

    # 2. Submit correct flag
    sub_resp = client.post(
        "/api/submissions",
        json={"challenge_id": str(chall.id), "flag": "FLAG{sqli_easy_solve}"},
        headers=alice_headers,
    )
    assert sub_resp.status_code == 200
    assert sub_resp.json()["is_correct"] is True

    # 3. Check /me/solved
    resp_me = client.get("/api/profile/me/solved", headers=alice_headers)
    assert resp_me.status_code == 200
    solves_me = resp_me.json()
    assert len(solves_me) == 1
    assert solves_me[0]["challenge_title"] == "SQLi 101"
    assert solves_me[0]["category"] == "Web Exploitation"
    assert solves_me[0]["difficulty"] == "easy"
    assert solves_me[0]["points_awarded"] == 100
    assert "flag" not in str(solves_me).lower()

    # 4. Check public /{user_id}/solved
    alice_id = profile_test_setup["alice"].id
    resp_pub = client.get(f"/api/profile/{alice_id}/solved")
    assert resp_pub.status_code == 200
    assert len(resp_pub.json()) == 1

    # 5. Check profile total_points and rank integration
    profile_resp = client.get("/api/profile/me", headers=alice_headers)
    prof_data = profile_resp.json()
    assert prof_data["total_points"] == 100
    assert prof_data["challenges_solved"] == 1
    assert prof_data["global_rank"] == 1


# ==========================================
# 3. ACTIVITY TRACKING SYSTEM
# ==========================================

def test_activity_lifecycle(client, profile_test_setup, db_session):
    """Verifies automated activity tracking across solves, hints, events, and teams."""
    alice = profile_test_setup["alice"]
    alice_headers = {"Authorization": f"Bearer {profile_test_setup['token_alice']}"}

    # Action 1: Solve challenge
    client.post(
        "/api/submissions",
        json={"challenge_id": str(profile_test_setup["chall_web"].id), "flag": "FLAG{sqli_easy_solve}"},
        headers=alice_headers,
    )

    # Action 2: Create team
    team_resp = client.post(
        "/api/teams",
        json={"name": "CyberKnights", "description": "Alice's elite squad"},
        headers=alice_headers,
    )
    assert team_resp.status_code == 201

    # Action 3: Register for an upcoming event
    now = datetime.now(timezone.utc)
    ev = Event(
        name="Winter CTF 2026",
        slug="winter-ctf-2026",
        description="Annual CTF",
        start_at=now + timedelta(days=2),
        end_at=now + timedelta(days=4),
        registration_start_at=now - timedelta(days=1),
        registration_end_at=now + timedelta(days=1),
        status=EventStatus.UPCOMING,
        is_active=True,
    )
    db_session.add(ev)
    db_session.commit()

    reg_resp = client.post(
        f"/api/events/{ev.id}/register",
        json={"registration_type": "individual"},
        headers=alice_headers,
    )
    assert reg_resp.status_code == 201

    # Verify Activity feed: newest first, pagination
    feed_resp = client.get("/api/profile/me/activity?page=1&limit=10", headers=alice_headers)
    assert feed_resp.status_code == 200
    feed = feed_resp.json()

    assert feed["total"] >= 3
    types = [item["activity_type"] for item in feed["items"]]
    assert "event_registered" in types
    assert "team_created" in types
    assert "challenge_solved" in types

    # Public activity endpoint check
    pub_feed = client.get(f"/api/profile/{alice.id}/activity?page=1&limit=5")
    assert pub_feed.status_code == 200
    assert pub_feed.json()["total"] == feed["total"]


# ==========================================
# 4. HEATMAP & STREAKS
# ==========================================

def test_activity_heatmap(client, profile_test_setup, db_session):
    """GET /api/profile/me/activity/heatmap returns daily activity counts across range."""
    alice = profile_test_setup["alice"]
    alice_headers = {"Authorization": f"Bearer {profile_test_setup['token_alice']}"}

    today = datetime.now(timezone.utc).date()
    yesterday = today - timedelta(days=1)
    two_days_ago = today - timedelta(days=2)

    # Insert test activities directly with specific dates
    a1 = UserActivity(
        user_id=alice.id,
        activity_type=ActivityType.CHALLENGE_SOLVED,
        created_at=datetime(two_days_ago.year, two_days_ago.month, two_days_ago.day, 10, 0, 0, tzinfo=timezone.utc),
    )
    a2 = UserActivity(
        user_id=alice.id,
        activity_type=ActivityType.HINT_USED,
        created_at=datetime(today.year, today.month, today.day, 12, 0, 0, tzinfo=timezone.utc),
    )
    a3 = UserActivity(
        user_id=alice.id,
        activity_type=ActivityType.CHALLENGE_SOLVED,
        created_at=datetime(today.year, today.month, today.day, 15, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add_all([a1, a2, a3])
    db_session.commit()

    resp = client.get(
        f"/api/profile/me/activity/heatmap?start_date={two_days_ago.isoformat()}&end_date={today.isoformat()}",
        headers=alice_headers,
    )
    assert resp.status_code == 200
    heatmap = resp.json()

    # Should contain 3 days: two_days_ago (1), yesterday (0), today (2)
    assert len(heatmap) == 3
    date_map = {item["date"]: item["count"] for item in heatmap}
    assert date_map[two_days_ago.isoformat()] == 1
    assert date_map[yesterday.isoformat()] == 0
    assert date_map[today.isoformat()] == 2


def test_streak_calculation(client, profile_test_setup, db_session):
    """Test streak progression: consecutive days, same day deduplication, and broken streaks."""
    alice = profile_test_setup["alice"]
    alice_headers = {"Authorization": f"Bearer {profile_test_setup['token_alice']}"}

    today = datetime.now(timezone.utc).date()
    d1 = today - timedelta(days=2)
    d2 = today - timedelta(days=1)
    d3 = today

    # Day 1: 1 activity
    db_session.add(UserActivity(
        user_id=alice.id,
        activity_type=ActivityType.CHALLENGE_SOLVED,
        created_at=datetime(d1.year, d1.month, d1.day, 9, 0, 0, tzinfo=timezone.utc),
    ))
    # Day 2: 2 activities on same day -> must count as 1 active day
    db_session.add(UserActivity(
        user_id=alice.id,
        activity_type=ActivityType.HINT_USED,
        created_at=datetime(d2.year, d2.month, d2.day, 11, 0, 0, tzinfo=timezone.utc),
    ))
    db_session.add(UserActivity(
        user_id=alice.id,
        activity_type=ActivityType.TEAM_JOINED,
        created_at=datetime(d2.year, d2.month, d2.day, 14, 0, 0, tzinfo=timezone.utc),
    ))
    # Day 3: 1 activity
    db_session.add(UserActivity(
        user_id=alice.id,
        activity_type=ActivityType.EVENT_REGISTERED,
        created_at=datetime(d3.year, d3.month, d3.day, 8, 0, 0, tzinfo=timezone.utc),
    ))
    db_session.commit()

    resp = client.get("/api/profile/me/streak", headers=alice_headers)
    assert resp.status_code == 200
    streak_data = resp.json()

    assert streak_data["current_streak"] == 3
    assert streak_data["longest_streak"] == 3
    assert streak_data["last_active_date"] == d3.isoformat()


def test_streak_broken_when_days_missed(db_session, profile_test_setup):
    """Streak drops to 0 when user missed both yesterday and today."""
    bob = profile_test_setup["bob"]
    today = datetime.now(timezone.utc).date()
    four_days_ago = today - timedelta(days=4)
    three_days_ago = today - timedelta(days=3)

    db_session.add(UserActivity(
        user_id=bob.id,
        activity_type=ActivityType.CHALLENGE_SOLVED,
        created_at=datetime(four_days_ago.year, four_days_ago.month, four_days_ago.day, 12, 0, 0, tzinfo=timezone.utc),
    ))
    db_session.add(UserActivity(
        user_id=bob.id,
        activity_type=ActivityType.CHALLENGE_SOLVED,
        created_at=datetime(three_days_ago.year, three_days_ago.month, three_days_ago.day, 12, 0, 0, tzinfo=timezone.utc),
    ))
    db_session.commit()

    streak = StreakService.get_user_streak(db_session, bob.id)
    assert streak["current_streak"] == 0
    assert streak["longest_streak"] == 2
    assert streak["last_active_date"] == three_days_ago.isoformat()


# ==========================================
# 5. CATEGORY STATS
# ==========================================

def test_category_stats(client, profile_test_setup, monkeypatch):
    """GET /api/profile/me/category-stats aggregates solved count and points earned per category."""
    from app.config import settings
    monkeypatch.setattr(settings, "SUBMISSION_COOLDOWN_SECONDS", 0)

    alice_headers = {"Authorization": f"Bearer {profile_test_setup['token_alice']}"}

    # Solve Web challenge (100 pts)
    r1 = client.post(
        "/api/submissions",
        json={"challenge_id": str(profile_test_setup["chall_web"].id), "flag": "FLAG{sqli_easy_solve}"},
        headers=alice_headers,
    )
    assert r1.status_code == 200

    # Solve Crypto challenge (250 pts)
    r2 = client.post(
        "/api/submissions",
        json={"challenge_id": str(profile_test_setup["chall_crypto"].id), "flag": "FLAG{rsa_medium_solve}"},
        headers=alice_headers,
    )
    assert r2.status_code == 200

    resp = client.get("/api/profile/me/category-stats", headers=alice_headers)
    assert resp.status_code == 200
    stats = resp.json()

    stats_dict = {item["category"]: item for item in stats}
    assert "Web Exploitation" in stats_dict
    assert stats_dict["Web Exploitation"]["solved_count"] == 1
    assert stats_dict["Web Exploitation"]["points_earned"] == 100

    assert "Cryptography" in stats_dict
    assert stats_dict["Cryptography"]["solved_count"] == 1
    assert stats_dict["Cryptography"]["points_earned"] == 250
