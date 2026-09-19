from datetime import datetime, timezone, timedelta
from uuid import uuid4
import pytest

from app.models.user import User, UserRole
from app.models.category import Category
from app.models.challenge import Challenge, ChallengeDifficulty, ChallengeType
from app.models.submission import Submission
from app.models.solve import Solve
from app.models.team import Team, TeamMember
from app.models.event import Event, EventStatus, event_challenges
from app.models.event_registration import EventRegistration, RegistrationType
from app.models.activity import UserActivity, ActivityType
from app.models.badge import Badge, UserBadge, CriteriaType
from app.models.discussion import Discussion, DiscussionComment
from app.core.security import create_access_token, hash_password
from app.services.challenge_service import hash_flag
from app.config import settings


@pytest.fixture(autouse=True)
def disable_submission_cooldown(monkeypatch):
    """Disable cooldown during test execution."""
    monkeypatch.setattr(settings, "SUBMISSION_COOLDOWN_SECONDS", 0)


@pytest.fixture
def analytics_setup(db_session):
    """Creates a comprehensive test environment with admin, mod, student, challenges, solves, and activity."""
    # 1. Users
    admin = User(
        username="admin_an",
        email="admin_an@college.edu",
        hashed_password=hash_password("Pass123!"),
        role=UserRole.ADMIN,
        college="OWASP College",
        is_active=True,
    )
    mod = User(
        username="mod_an",
        email="mod_an@college.edu",
        hashed_password=hash_password("Pass123!"),
        role=UserRole.MODERATOR,
        college="OWASP College",
        is_active=True,
    )
    student1 = User(
        username="student_alice",
        email="alice_an@college.edu",
        hashed_password=hash_password("Pass123!"),
        role=UserRole.STUDENT,
        college="Tech University",
        is_active=True,
    )
    student2 = User(
        username="student_bob",
        email="bob_an@college.edu",
        hashed_password=hash_password("Pass123!"),
        role=UserRole.STUDENT,
        college="Tech University",
        is_active=True,
    )
    student3 = User(
        username="student_charlie",
        email="charlie_an@college.edu",
        hashed_password=hash_password("Pass123!"),
        role=UserRole.STUDENT,
        college="State College",
        is_active=True,
    )
    db_session.add_all([admin, mod, student1, student2, student3])
    db_session.commit()

    admin_token = create_access_token({"sub": str(admin.id), "role": admin.role.value})
    mod_token = create_access_token({"sub": str(mod.id), "role": mod.role.value})
    student_token = create_access_token({"sub": str(student1.id), "role": student1.role.value})

    # 2. Categories
    cat_web = Category(name="Web Exploitation", description="Web security")
    cat_crypto = Category(name="Cryptography", description="Crypto challenges")
    db_session.add_all([cat_web, cat_crypto])
    db_session.commit()

    # 3. Challenges
    ch1 = Challenge(
        title="Web 101",
        description="Easy Web SQLi",
        category_id=cat_web.id,
        difficulty=ChallengeDifficulty.EASY,
        points=100,
        flag_hash=hash_flag("flag{web101}"),
        is_active=True,
    )
    ch2 = Challenge(
        title="Crypto 201",
        description="Medium RSA",
        category_id=cat_crypto.id,
        difficulty=ChallengeDifficulty.MEDIUM,
        points=250,
        flag_hash=hash_flag("flag{rsa201}"),
        is_active=True,
    )
    ch3 = Challenge(
        title="Zero Attempt Challenge",
        description="Hard Reverse",
        category_id=cat_web.id,
        difficulty=ChallengeDifficulty.HARD,
        points=500,
        flag_hash=hash_flag("flag{hard}"),
        is_active=True,
    )
    db_session.add_all([ch1, ch2, ch3])
    db_session.commit()

    # 4. Submissions & Solves
    # Student 1 attempts & solves ch1
    sub1 = Submission(user_id=student1.id, challenge_id=ch1.id, submitted_flag_hash=hash_flag("flag{wrong}"), is_correct=False)
    sub2 = Submission(user_id=student1.id, challenge_id=ch1.id, submitted_flag_hash=hash_flag("flag{web101}"), is_correct=True)
    # Student 2 solves ch1 directly
    sub3 = Submission(user_id=student2.id, challenge_id=ch1.id, submitted_flag_hash=hash_flag("flag{web101}"), is_correct=True)
    # Student 1 attempts ch2 and fails twice
    sub4 = Submission(user_id=student1.id, challenge_id=ch2.id, submitted_flag_hash=hash_flag("flag{fail1}"), is_correct=False)
    sub5 = Submission(user_id=student1.id, challenge_id=ch2.id, submitted_flag_hash=hash_flag("flag{fail2}"), is_correct=False)
    db_session.add_all([sub1, sub2, sub3, sub4, sub5])
    db_session.flush()

    solve1 = Solve(user_id=student1.id, challenge_id=ch1.id, submission_id=sub2.id, points_awarded=100)
    solve2 = Solve(user_id=student2.id, challenge_id=ch1.id, submission_id=sub3.id, points_awarded=100)
    db_session.add_all([solve1, solve2])
    db_session.commit()

    # 5. Team
    team = Team(name="AlphaSec", college="Tech University", owner_id=student1.id, is_active=True)
    db_session.add(team)
    db_session.flush()
    tm1 = TeamMember(team_id=team.id, user_id=student1.id, role="captain")
    tm2 = TeamMember(team_id=team.id, user_id=student2.id, role="member")
    db_session.add_all([tm1, tm2])
    db_session.commit()

    # 6. Event
    now = datetime.now(timezone.utc)
    ev = Event(
        name="Spring CTF 2026",
        slug="spring-ctf-2026",
        description="Spring competition",
        start_time=now - timedelta(hours=2),
        end_time=now + timedelta(hours=2),
        status=EventStatus.LIVE,
        is_scoreboard_frozen=False,
    )
    db_session.add(ev)
    db_session.flush()

    # Assign ch1 and ch2 to event
    db_session.execute(event_challenges.insert().values(event_id=ev.id, challenge_id=ch1.id))
    db_session.execute(event_challenges.insert().values(event_id=ev.id, challenge_id=ch2.id))

    # Event registration
    reg = EventRegistration(
        event_id=ev.id,
        user_id=student1.id,
        registration_type=RegistrationType.INDIVIDUAL,
        is_active=True,
    )
    db_session.add(reg)
    db_session.commit()

    # 7. Activity
    act1 = UserActivity(user_id=student1.id, activity_type=ActivityType.CHALLENGE_SOLVED.value)
    act2 = UserActivity(user_id=student2.id, activity_type=ActivityType.CHALLENGE_SOLVED.value)
    db_session.add_all([act1, act2])
    db_session.commit()

    # 8. Badges
    badge1 = Badge(
        name="First Blood",
        slug="first-blood",
        description="First solve",
        icon="trophy",
        criteria_type=CriteriaType.FIRST_SOLVE.value,
        criteria_value=1,
        is_active=True,
    )
    db_session.add(badge1)
    db_session.flush()
    ub1 = UserBadge(user_id=student1.id, badge_id=badge1.id)
    db_session.add(ub1)
    db_session.commit()

    # 9. Discussions
    disc = Discussion(
        challenge_id=ch1.id,
        user_id=student1.id,
        title="Single quote bypass help",
        content="How do I bypass quotes?",
    )
    db_session.add(disc)
    db_session.flush()
    comm = DiscussionComment(
        discussion_id=disc.id,
        user_id=student2.id,
        content="Try URL encoding the character.",
    )
    db_session.add(comm)
    db_session.commit()

    return {
        "admin_token": admin_token,
        "mod_token": mod_token,
        "student_token": student_token,
        "admin": admin,
        "student1": student1,
        "student2": student2,
        "ch1": ch1,
        "ch2": ch2,
        "ch3": ch3,
        "event": ev,
        "team": team,
        "cat_web": cat_web,
        "cat_crypto": cat_crypto,
    }


# =============================================================================
# 1. Access Control & RBAC Tests
# =============================================================================

def test_analytics_rbac_authorization(client, analytics_setup):
    """Verifies that only admin and moderator roles can access analytics endpoints."""
    url = "/api/admin/analytics/overview"

    # 1. Unauthenticated -> 401
    res_unauth = client.get(url)
    assert res_unauth.status_code == 401

    # 2. Student -> 403
    res_student = client.get(url, headers={"Authorization": f"Bearer {analytics_setup['student_token']}"})
    assert res_student.status_code == 403

    # 3. Moderator -> 200
    res_mod = client.get(url, headers={"Authorization": f"Bearer {analytics_setup['mod_token']}"})
    assert res_mod.status_code == 200

    # 4. Admin -> 200
    res_admin = client.get(url, headers={"Authorization": f"Bearer {analytics_setup['admin_token']}"})
    assert res_admin.status_code == 200


# =============================================================================
# 2. Platform Overview & Time Filters
# =============================================================================

def test_platform_overview_metrics_and_period(client, analytics_setup):
    """Verifies overview metrics counts and time period parameter."""
    headers = {"Authorization": f"Bearer {analytics_setup['admin_token']}"}

    # All time
    res = client.get("/api/admin/analytics/overview?period=all", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["period"] == "all"
    assert data["total_users"] == 5  # admin, mod, 3 students
    assert data["active_users"] == 2  # student1, student2 had activity
    assert data["total_challenges"] == 3
    assert data["active_challenges"] == 3
    assert data["total_submissions"] == 5
    assert data["correct_submissions"] == 2
    assert data["incorrect_submissions"] == 3
    assert data["total_solves"] == 2
    assert data["total_teams"] == 1
    assert data["active_teams"] == 1
    assert data["total_events"] == 1
    assert data["total_badges_awarded"] == 1
    assert data["total_discussions"] == 1

    # 7 Days filter
    res_7d = client.get("/api/admin/analytics/overview?period=7d", headers=headers)
    assert res_7d.status_code == 200
    assert res_7d.json()["period"] == "7d"


# =============================================================================
# 3. User Demographics & Privacy Protection
# =============================================================================

def test_user_analytics_and_security(client, analytics_setup):
    """Verifies user demographics aggregation and ensures zero password hash or credential leakage."""
    headers = {"Authorization": f"Bearer {analytics_setup['admin_token']}"}

    res = client.get("/api/admin/analytics/users", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["total_users"] == 5
    assert data["active_users"] == 2
    assert data["users_with_solves"] == 2
    assert data["users_without_solves"] == 3

    # Check college aggregation
    colleges = {c["college"]: c["count"] for c in data["by_college"]}
    assert colleges["Tech University"] == 2
    assert colleges["OWASP College"] == 2
    assert colleges["State College"] == 1

    # Check role aggregation
    roles = {r["role"]: r["count"] for r in data["by_role"]}
    assert roles["student"] == 3
    assert roles["admin"] == 1
    assert roles["moderator"] == 1

    # Security check: Password hashes and JWT tokens must NEVER appear in response
    assert "password" not in res.text.lower()
    assert "hash" not in res.text.lower()
    assert "token" not in res.text.lower()


# =============================================================================
# 4. Activity Trend
# =============================================================================

def test_activity_trend(client, analytics_setup):
    """Verifies activity trend daily counts."""
    headers = {"Authorization": f"Bearer {analytics_setup['admin_token']}"}

    res = client.get("/api/admin/analytics/activity?period=30d", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["period"] == "30d"
    assert len(data["data"]) >= 1
    assert data["data"][0]["activities"] >= 2


# =============================================================================
# 5. Challenge Analytics, Difficulty & Insights
# =============================================================================

def test_challenge_analytics_and_zero_attempts(client, analytics_setup):
    """Verifies challenge solve rate, attempt counts, and zero-attempt edge case."""
    headers = {"Authorization": f"Bearer {analytics_setup['admin_token']}"}

    res = client.get("/api/admin/analytics/challenges", headers=headers)
    assert res.status_code == 200
    items = res.json()

    assert len(items) == 3
    ch_map = {item["title"]: item for item in items}

    # Web 101: 3 attempts (2 correct, 1 incorrect) -> solve rate ~0.6667
    web = ch_map["Web 101"]
    assert web["total_attempts"] == 3
    assert web["correct_attempts"] == 2
    assert web["unique_solvers"] == 2
    assert web["solve_rate"] == 0.6667

    # Crypto 201: 2 attempts (0 correct, 2 incorrect) -> solve rate 0.0
    crypto = ch_map["Crypto 201"]
    assert crypto["total_attempts"] == 2
    assert crypto["correct_attempts"] == 0
    assert crypto["solve_rate"] == 0.0

    # Zero Attempt Challenge: 0 attempts -> solve rate 0.0 (no divide by zero)
    zero_ch = ch_map["Zero Attempt Challenge"]
    assert zero_ch["total_attempts"] == 0
    assert zero_ch["correct_attempts"] == 0
    assert zero_ch["solve_rate"] == 0.0

    # Security check: Flags and flag hashes must NOT be exposed
    for item in items:
        assert "flag" not in item
        assert "flag_hash" not in item


def test_difficulty_analytics(client, analytics_setup):
    """Verifies aggregated statistics grouped by challenge difficulty."""
    headers = {"Authorization": f"Bearer {analytics_setup['admin_token']}"}

    res = client.get("/api/admin/analytics/challenges/difficulty", headers=headers)
    assert res.status_code == 200
    diffs = {d["difficulty"]: d for d in res.json()}

    assert diffs["Easy"]["challenge_count"] == 1
    assert diffs["Easy"]["attempts"] == 3
    assert diffs["Easy"]["solves"] == 2

    assert diffs["Medium"]["challenge_count"] == 1
    assert diffs["Medium"]["attempts"] == 2
    assert diffs["Medium"]["solves"] == 0

    assert diffs["Hard"]["challenge_count"] == 1
    assert diffs["Hard"]["attempts"] == 0
    assert diffs["Hard"]["solves"] == 0


def test_challenge_insights_threshold(client, analytics_setup):
    """Verifies challenge insights (most difficult, most solved, most attempted)."""
    headers = {"Authorization": f"Bearer {analytics_setup['admin_token']}"}

    # Low threshold: min_attempts=1
    res = client.get("/api/admin/analytics/challenges/insights?min_attempts=1", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["min_attempts_threshold"] == 1
    assert len(data["most_difficult"]) >= 1
    # Crypto 201 had 2 failed attempts, solve_rate 0.0
    assert data["most_difficult"][0]["title"] == "Crypto 201"

    # Most solved: Web 101 had 2 solvers
    assert data["most_solved"][0]["title"] == "Web 101"

    # Most attempted: Web 101 had 3 attempts
    assert data["most_attempted"][0]["title"] == "Web 101"


# =============================================================================
# 6. Category Analytics
# =============================================================================

def test_category_analytics(client, analytics_setup):
    """Verifies category engagement metrics and point distribution."""
    headers = {"Authorization": f"Bearer {analytics_setup['admin_token']}"}

    res = client.get("/api/admin/analytics/categories", headers=headers)
    assert res.status_code == 200
    cats = {c["category_name"]: c for c in res.json()}

    assert "Web Exploitation" in cats
    web = cats["Web Exploitation"]
    assert web["challenge_count"] == 2  # ch1 and ch3
    assert web["attempts"] == 3
    assert web["solves"] == 2
    assert web["unique_solvers"] == 2
    assert web["total_points_awarded"] == 200  # 2 solves * 100 pts


# =============================================================================
# 7. Submission Analytics & Behavior
# =============================================================================

def test_submission_analytics(client, analytics_setup):
    """Verifies submission metrics, daily grouping, failure rankings, and frequent submitters."""
    headers = {"Authorization": f"Bearer {analytics_setup['admin_token']}"}

    res = client.get("/api/admin/analytics/submissions?period=all", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["total_submissions"] == 5
    assert data["correct_submissions"] == 2
    assert data["incorrect_submissions"] == 3
    assert data["accuracy_rate"] == 0.4
    assert data["unique_submitters"] == 2
    assert data["average_attempts_before_solve"] == 2.5  # 5 / 2

    assert len(data["submissions_by_day"]) >= 1
    assert len(data["challenges_highest_failure"]) >= 1
    # Crypto 201 has 100% failure rate (2/2)
    assert data["challenges_highest_failure"][0]["title"] == "Crypto 201"

    # Frequent submitters: student1 submitted 4 times, student2 submitted 1 time
    submitters = {s["username"]: s["submission_count"] for s in data["frequent_submitters"]}
    assert submitters["student_alice"] == 4
    assert submitters["student_bob"] == 1

    # Security check: submitted flag values must never be returned
    assert "flag{wrong}" not in res.text
    assert "flag{fail1}" not in res.text


# =============================================================================
# 8. Event Analytics & Performance Details
# =============================================================================

def test_events_analytics_and_detail(client, analytics_setup):
    """Verifies event list and event granular performance metrics."""
    headers = {"Authorization": f"Bearer {analytics_setup['admin_token']}"}

    # List events
    res = client.get("/api/admin/analytics/events", headers=headers)
    assert res.status_code == 200
    ev_list = res.json()
    assert len(ev_list) == 1
    assert ev_list[0]["name"] == "Spring CTF 2026"
    assert ev_list[0]["registration_count"] == 1
    assert ev_list[0]["challenges_assigned"] == 2

    # Detail event
    ev_id = analytics_setup["event"].id
    res_detail = client.get(f"/api/admin/analytics/events/{ev_id}", headers=headers)
    assert res_detail.status_code == 200
    detail = res_detail.json()
    assert detail["event_id"] == str(ev_id)
    assert detail["total_registrations"] == 1
    assert detail["individual_registrations"] == 1
    assert detail["team_registrations"] == 0
    assert len(detail["challenge_performance"]) == 2

    # Non-existent event returns 404
    fake_id = uuid4()
    res_404 = client.get(f"/api/admin/analytics/events/{fake_id}", headers=headers)
    assert res_404.status_code == 404


# =============================================================================
# 9. Team, Badge & Discussion Analytics
# =============================================================================

def test_team_badge_discussion_analytics(client, analytics_setup):
    """Verifies team rosters, badge distributions, and discussion forum statistics."""
    headers = {"Authorization": f"Bearer {analytics_setup['admin_token']}"}

    # Teams
    res_teams = client.get("/api/admin/analytics/teams", headers=headers)
    assert res_teams.status_code == 200
    team_data = res_teams.json()
    assert team_data["total_teams"] == 1
    assert team_data["active_teams"] == 1
    assert team_data["average_team_size"] == 2.0  # 2 members / 1 team
    assert team_data["by_college"][0]["college"] == "Tech University"

    # Badges
    res_badges = client.get("/api/admin/analytics/badges", headers=headers)
    assert res_badges.status_code == 200
    badge_data = res_badges.json()
    assert badge_data["total_badge_definitions"] >= 1
    assert badge_data["total_badges_awarded"] == 1
    assert badge_data["most_awarded_badges"][0]["name"] == "First Blood"

    # Discussions
    res_disc = client.get("/api/admin/analytics/discussions", headers=headers)
    assert res_disc.status_code == 200
    disc_data = res_disc.json()
    assert disc_data["total_discussions"] == 1
    assert disc_data["total_comments"] == 1
    assert len(disc_data["most_discussed_challenges"]) == 1
    assert disc_data["most_discussed_challenges"][0]["title"] == "Web 101"


# =============================================================================
# 10. Leaderboard Insights & Score Distribution
# =============================================================================

def test_leaderboard_insights(client, analytics_setup):
    """Verifies score distribution buckets and top competitor rankings."""
    headers = {"Authorization": f"Bearer {analytics_setup['admin_token']}"}

    res = client.get("/api/admin/analytics/leaderboard", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["ranked_users_count"] == 2  # student1 and student2 each have 100 pts
    assert data["average_score"] == 100.0
    assert data["median_score"] == 100.0

    # 100 pts falls in "0 - 100 pts" bucket
    dist = {b["label"]: b["users"] for b in data["score_distribution"]}
    assert dist["0 - 100 pts"] == 2

    # Top users
    assert len(data["top_users"]) == 2
    assert data["top_users"][0]["score"] == 100


# =============================================================================
# 11. Composite Dashboard Summary Endpoint
# =============================================================================

def test_dashboard_composite_summary(client, analytics_setup):
    """Verifies the unified dashboard summary payload."""
    headers = {"Authorization": f"Bearer {analytics_setup['admin_token']}"}

    res = client.get("/api/admin/analytics/dashboard?period=30d", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert "overview" in data
    assert "activity_trend" in data
    assert "category_summary" in data
    assert "difficulty_summary" in data
    assert "top_challenges" in data
    assert "event_summary" in data

    assert data["overview"]["total_users"] == 5
    assert len(data["category_summary"]) >= 1
    assert len(data["difficulty_summary"]) == 4
