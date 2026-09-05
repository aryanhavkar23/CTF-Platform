from datetime import datetime, timedelta, timezone
from uuid import uuid4
import pytest
from app.models.user import User, UserRole
from app.models.category import Category
from app.models.challenge import Challenge, ChallengeDifficulty, ChallengeType
from app.models.submission import Submission
from app.models.solve import Solve
from app.core.security import hash_password, create_access_token
from app.services.challenge_service import hash_flag


@pytest.fixture
def leaderboard_setup(db_session):
    """Sets up categories, challenges, and multiple users from different colleges."""
    # 1. Categories
    web_cat = Category(name="Web Exploitation", description="Web security")
    crypto_cat = Category(name="Cryptography", description="Crypto challenges")
    pwn_cat = Category(name="Pwn / Binary Exploitation", description="Binary exploitation")
    db_session.add_all([web_cat, crypto_cat, pwn_cat])
    db_session.commit()

    # 2. Challenges
    c1 = Challenge(
        title="Web 101",
        description="Easy web",
        category_id=web_cat.id,
        difficulty=ChallengeDifficulty.EASY,
        points=100,
        flag_hash=hash_flag("flag{web101}"),
        is_active=True,
        challenge_type=ChallengeType.STATIC
    )
    c2 = Challenge(
        title="Web 201",
        description="Medium web",
        category_id=web_cat.id,
        difficulty=ChallengeDifficulty.MEDIUM,
        points=200,
        flag_hash=hash_flag("flag{web201}"),
        is_active=True,
        challenge_type=ChallengeType.STATIC
    )
    c3 = Challenge(
        title="Crypto 300",
        description="Hard crypto",
        category_id=crypto_cat.id,
        difficulty=ChallengeDifficulty.HARD,
        points=300,
        flag_hash=hash_flag("flag{crypto300}"),
        is_active=True,
        challenge_type=ChallengeType.STATIC
    )
    c4 = Challenge(
        title="Pwn 500",
        description="Insane pwn",
        category_id=pwn_cat.id,
        difficulty=ChallengeDifficulty.INSANE,
        points=500,
        flag_hash=hash_flag("flag{pwn500}"),
        is_active=True,
        challenge_type=ChallengeType.STATIC
    )
    db_session.add_all([c1, c2, c3, c4])
    db_session.commit()

    # 3. Users across colleges
    user_a = User(
        username="alice_pccoe",
        email="alice@pccoe.edu",
        hashed_password=hash_password("Secret123!"),
        role=UserRole.STUDENT,
        college="PCCOE"
    )
    user_b = User(
        username="bob_pccoe",
        email="bob@pccoe.edu",
        hashed_password=hash_password("Secret123!"),
        role=UserRole.STUDENT,
        college="PCCOE"
    )
    user_c = User(
        username="charlie_coep",
        email="charlie@coep.edu",
        hashed_password=hash_password("Secret123!"),
        role=UserRole.STUDENT,
        college="COEP"
    )
    user_d = User(
        username="david_zero",
        email="david@zero.edu",
        hashed_password=hash_password("Secret123!"),
        role=UserRole.STUDENT,
        college="COEP"
    )
    db_session.add_all([user_a, user_b, user_c, user_d])
    db_session.commit()

    token_a = create_access_token(data={"sub": str(user_a.id), "role": user_a.role.value})
    token_d = create_access_token(data={"sub": str(user_d.id), "role": user_d.role.value})

    return {
        "web_cat": web_cat,
        "crypto_cat": crypto_cat,
        "pwn_cat": pwn_cat,
        "c1": c1,
        "c2": c2,
        "c3": c3,
        "c4": c4,
        "user_a": user_a,
        "user_b": user_b,
        "user_c": user_c,
        "user_d": user_d,
        "header_a": {"Authorization": f"Bearer {token_a}"},
        "header_d": {"Authorization": f"Bearer {token_d}"},
    }


def _create_solve(db_session, user, challenge, points, created_at=None):
    """Helper to record a verified solve."""
    sub = Submission(
        user_id=user.id,
        challenge_id=challenge.id,
        submitted_flag_hash="dummy_flag_hash",
        is_correct=True,
        points_awarded=points
    )
    db_session.add(sub)
    db_session.commit()

    solve = Solve(
        user_id=user.id,
        challenge_id=challenge.id,
        submission_id=sub.id,
        points_awarded=points,
        created_at=created_at or datetime.now(timezone.utc)
    )
    db_session.add(solve)
    db_session.commit()
    return solve


# 1. Global Leaderboard Tests
def test_global_leaderboard_ranking_descending(client, db_session, leaderboard_setup):
    """Global leaderboard correctly ranks users descending by total earned points."""
    # User A solves c4 (500 pts)
    _create_solve(db_session, leaderboard_setup["user_a"], leaderboard_setup["c4"], 500)
    # User B solves c3 (300 pts)
    _create_solve(db_session, leaderboard_setup["user_b"], leaderboard_setup["c3"], 300)
    # User C solves c1 (100 pts)
    _create_solve(db_session, leaderboard_setup["user_c"], leaderboard_setup["c1"], 100)

    res = client.get("/api/leaderboard/global")
    assert res.status_code == 200
    data = res.json()
    assert data["total_entries"] == 3
    assert len(data["items"]) == 3

    # Verify order: A (500, rank 1), B (300, rank 2), C (100, rank 3)
    assert data["items"][0]["username"] == "alice_pccoe"
    assert data["items"][0]["total_points"] == 500
    assert data["items"][0]["rank"] == 1
    assert data["items"][0]["solved_count"] == 1

    assert data["items"][1]["username"] == "bob_pccoe"
    assert data["items"][1]["total_points"] == 300
    assert data["items"][1]["rank"] == 2
    assert data["items"][1]["solved_count"] == 1

    assert data["items"][2]["username"] == "charlie_coep"
    assert data["items"][2]["total_points"] == 100
    assert data["items"][2]["rank"] == 3
    assert data["items"][2]["solved_count"] == 1


def test_deterministic_tie_breaking(client, db_session, leaderboard_setup):
    """Users with the same score are tie-broken by earlier achievement of that score."""
    base_time = datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc)
    
    # Alice solves 300 pts at 10:00:00
    _create_solve(
        db_session,
        leaderboard_setup["user_a"],
        leaderboard_setup["c3"],
        300,
        created_at=base_time
    )

    # Bob solves 300 pts at 10:15:00 (15 minutes later)
    _create_solve(
        db_session,
        leaderboard_setup["user_b"],
        leaderboard_setup["c3"],
        300,
        created_at=base_time + timedelta(minutes=15)
    )

    res = client.get("/api/leaderboard/global")
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) == 2

    # Alice reached 300 first -> Rank 1
    assert items[0]["username"] == "alice_pccoe"
    assert items[0]["rank"] == 1
    assert items[0]["total_points"] == 300

    # Bob reached 300 later -> Rank 2
    assert items[1]["username"] == "bob_pccoe"
    assert items[1]["rank"] == 2
    assert items[1]["total_points"] == 300


def test_duplicate_solves_do_not_increase_score(client, db_session, leaderboard_setup):
    """Leaderboard aggregates only distinct verified challenge solves."""
    _create_solve(db_session, leaderboard_setup["user_a"], leaderboard_setup["c1"], 100)

    # Add extra submission attempts for same challenge (should not be in solves due to unique constraint)
    sub2 = Submission(
        user_id=leaderboard_setup["user_a"].id,
        challenge_id=leaderboard_setup["c1"].id,
        submitted_flag_hash="dummy_hash",
        is_correct=True,
        points_awarded=0
    )
    db_session.add(sub2)
    db_session.commit()

    res = client.get("/api/leaderboard/global")
    items = res.json()["items"]
    assert len(items) == 1
    assert items[0]["total_points"] == 100
    assert items[0]["solved_count"] == 1


# 2. College Leaderboard Tests
def test_college_filtering_and_ranking(client, db_session, leaderboard_setup):
    """College leaderboard strictly returns users from the specified college."""
    _create_solve(db_session, leaderboard_setup["user_a"], leaderboard_setup["c1"], 100) # PCCOE
    _create_solve(db_session, leaderboard_setup["user_b"], leaderboard_setup["c2"], 200) # PCCOE
    _create_solve(db_session, leaderboard_setup["user_c"], leaderboard_setup["c3"], 300) # COEP

    res = client.get("/api/leaderboard/college?college=PCCOE")
    assert res.status_code == 200
    data = res.json()
    assert data["total_entries"] == 2
    items = data["items"]
    assert len(items) == 2

    # Within PCCOE: Bob (200 pts) is Rank 1, Alice (100 pts) is Rank 2
    assert items[0]["username"] == "bob_pccoe"
    assert items[0]["rank"] == 1
    assert items[0]["college"] == "PCCOE"

    assert items[1]["username"] == "alice_pccoe"
    assert items[1]["rank"] == 2
    assert items[1]["college"] == "PCCOE"


def test_college_my_college_default(client, db_session, leaderboard_setup):
    """Authenticated user calling college leaderboard without param defaults to their college."""
    _create_solve(db_session, leaderboard_setup["user_a"], leaderboard_setup["c1"], 100)
    _create_solve(db_session, leaderboard_setup["user_c"], leaderboard_setup["c3"], 300)

    # user_a is from PCCOE
    res = client.get("/api/leaderboard/college", headers=leaderboard_setup["header_a"])
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) == 1
    assert items[0]["username"] == "alice_pccoe"


def test_college_unauthenticated_without_param_rejected(client):
    """Unauthenticated call to college leaderboard without college parameter returns 400."""
    res = client.get("/api/leaderboard/college")
    assert res.status_code == 400
    assert "college query parameter is required" in res.json()["detail"].lower()


# 3. Category Leaderboard Tests
def test_category_filtering(client, db_session, leaderboard_setup):
    """Category filter only counts solves belonging to that specific category."""
    # Alice solves Web 101 (100) and Crypto 300 (300) -> Total: 400
    _create_solve(db_session, leaderboard_setup["user_a"], leaderboard_setup["c1"], 100)
    _create_solve(db_session, leaderboard_setup["user_a"], leaderboard_setup["c3"], 300)

    # Bob solves Web 201 (200) -> Total: 200
    _create_solve(db_session, leaderboard_setup["user_b"], leaderboard_setup["c2"], 200)

    # In Web Exploitation category: Bob (200 pts) > Alice (100 pts)
    res = client.get("/api/leaderboard/global?category=Web%20Exploitation")
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) == 2

    assert items[0]["username"] == "bob_pccoe"
    assert items[0]["total_points"] == 200
    assert items[0]["rank"] == 1

    assert items[1]["username"] == "alice_pccoe"
    assert items[1]["total_points"] == 100
    assert items[1]["rank"] == 2


def test_invalid_category_rejected(client):
    """Non-existent category name returns 404."""
    res = client.get("/api/leaderboard/global?category=UnknownCategory999")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


# 4. Time Filtering Tests
def test_time_filtering_today_and_all_time(client, db_session, leaderboard_setup):
    """Time filter includes only points earned during the selected time period."""
    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(days=1, hours=2)

    # Alice solved yesterday
    _create_solve(
        db_session,
        leaderboard_setup["user_a"],
        leaderboard_setup["c1"],
        100,
        created_at=yesterday
    )

    # Bob solved today
    _create_solve(
        db_session,
        leaderboard_setup["user_b"],
        leaderboard_setup["c2"],
        200,
        created_at=now
    )

    # all_time includes both
    res_all = client.get("/api/leaderboard/global?time_frame=all_time")
    assert res_all.status_code == 200
    assert res_all.json()["total_entries"] == 2

    # today includes only Bob
    res_today = client.get("/api/leaderboard/global?time_frame=today")
    assert res_today.status_code == 200
    today_items = res_today.json()["items"]
    assert len(today_items) == 1
    assert today_items[0]["username"] == "bob_pccoe"
    assert today_items[0]["total_points"] == 200


def test_invalid_time_frame_rejected(client):
    """Unsupported time_frame returns 400."""
    res = client.get("/api/leaderboard/global?time_frame=last_decade")
    assert res.status_code == 400
    assert "invalid time_frame" in res.json()["detail"].lower()


# 5. User Rank (/api/leaderboard/me) Tests
def test_user_rank_authenticated_returns_correct_ranks(client, db_session, leaderboard_setup):
    """Returns exact global and college rank matching public leaderboards."""
    _create_solve(db_session, leaderboard_setup["user_a"], leaderboard_setup["c1"], 100) # PCCOE
    _create_solve(db_session, leaderboard_setup["user_b"], leaderboard_setup["c2"], 200) # PCCOE
    _create_solve(db_session, leaderboard_setup["user_c"], leaderboard_setup["c4"], 500) # COEP

    # Global: C (500, #1), B (200, #2), A (100, #3)
    # In PCCOE: B (200, #1), A (100, #2)
    res = client.get("/api/leaderboard/me", headers=leaderboard_setup["header_a"])
    assert res.status_code == 200
    data = res.json()
    assert data["username"] == "alice_pccoe"
    assert data["total_points"] == 100
    assert data["solved_count"] == 1
    assert data["global_rank"] == 3
    assert data["college_rank"] == 2


def test_user_with_zero_solves_has_none_rank(client, leaderboard_setup):
    """User who has never solved a challenge returns 0 points and null rank."""
    res = client.get("/api/leaderboard/me", headers=leaderboard_setup["header_d"])
    assert res.status_code == 200
    data = res.json()
    assert data["username"] == "david_zero"
    assert data["total_points"] == 0
    assert data["solved_count"] == 0
    assert data["global_rank"] is None
    assert data["college_rank"] is None


def test_unauthenticated_me_rejected(client):
    """Calling /api/leaderboard/me without JWT returns 401."""
    res = client.get("/api/leaderboard/me")
    assert res.status_code == 401


# 6. Pagination Tests
def test_pagination_slices_and_ranks(client, db_session, leaderboard_setup):
    """Pagination preserves global overall rank calculation across pages."""
    # Alice: 500, Bob: 200, Charlie: 100
    _create_solve(db_session, leaderboard_setup["user_a"], leaderboard_setup["c4"], 500)
    _create_solve(db_session, leaderboard_setup["user_b"], leaderboard_setup["c2"], 200)
    _create_solve(db_session, leaderboard_setup["user_c"], leaderboard_setup["c1"], 100)

    # Page 1, size 2 -> Alice (rank 1), Bob (rank 2)
    res1 = client.get("/api/leaderboard/global?page=1&page_size=2")
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["page"] == 1
    assert data1["page_size"] == 2
    assert data1["total_entries"] == 3
    assert data1["total_pages"] == 2
    assert len(data1["items"]) == 2
    assert data1["items"][0]["rank"] == 1
    assert data1["items"][1]["rank"] == 2

    # Page 2, size 2 -> Charlie (rank 3)
    res2 = client.get("/api/leaderboard/global?page=2&page_size=2")
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["page"] == 2
    assert len(data2["items"]) == 1
    assert data2["items"][0]["rank"] == 3
    assert data2["items"][0]["username"] == "charlie_coep"


def test_max_page_size_enforced(client):
    """Requesting page_size > 100 returns 422 Unprocessable Entity."""
    res = client.get("/api/leaderboard/global?page_size=101")
    assert res.status_code == 422


def test_empty_page_handled(client, db_session, leaderboard_setup):
    """Requesting out-of-bounds page returns empty items list."""
    _create_solve(db_session, leaderboard_setup["user_a"], leaderboard_setup["c1"], 100)
    res = client.get("/api/leaderboard/global?page=999&page_size=20")
    assert res.status_code == 200
    data = res.json()
    assert data["items"] == []
    assert data["total_entries"] == 1


# 7. Security & Data Isolation Tests
def test_public_leaderboard_no_sensitive_leakage(client, db_session, leaderboard_setup):
    """Public leaderboard responses strictly omit password_hash, email, or private fields."""
    _create_solve(db_session, leaderboard_setup["user_a"], leaderboard_setup["c1"], 100)
    res = client.get("/api/leaderboard/global")
    item = res.json()["items"][0]

    assert "email" not in item
    assert "hashed_password" not in item
    assert "password_hash" not in item
    assert "is_active" not in item
    assert "role" not in item
