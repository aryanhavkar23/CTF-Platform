import time
from uuid import uuid4
import pytest
from app.models.user import User, UserRole
from app.core.security import hash_password, create_access_token
from app.services.challenge_service import ChallengeService


@pytest.fixture
def test_setup(db_session):
    """Sets up student and admin users, seeds categories, and returns headers and models."""
    ChallengeService.seed_categories(db_session)

    student1 = User(
        username="submission_student_1",
        email="sub1@college.edu",
        hashed_password=hash_password("Pass1234!"),
        role=UserRole.STUDENT
    )
    student2 = User(
        username="submission_student_2",
        email="sub2@college.edu",
        hashed_password=hash_password("Pass1234!"),
        role=UserRole.STUDENT
    )
    admin = User(
        username="sub_admin",
        email="sub_admin@college.edu",
        hashed_password=hash_password("AdminPass123!"),
        role=UserRole.ADMIN
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


def create_test_challenge(client, admin_header, title="Test Flag Challenge", points=100, flag="flag{secret_123}", is_active=True):
    """Helper to create a challenge for submission testing."""
    cat_res = client.get("/api/categories")
    cat_id = cat_res.json()[0]["id"]
    res = client.post("/api/challenges", headers=admin_header, json={
        "title": title,
        "description": "Solve it",
        "category_id": cat_id,
        "difficulty": "easy",
        "points": points,
        "flag": flag,
        "is_active": is_active
    })
    assert res.status_code == 201
    return res.json()


# 1. Authentication & Validation

def test_unauthenticated_submission_rejected(client):
    """Unauthenticated request to submit flag is rejected with 401."""
    res = client.post("/api/submissions", json={
        "challenge_id": str(uuid4()),
        "flag": "flag{test}"
    })
    assert res.status_code == 401


def test_invalid_token_rejected(client):
    """Invalid bearer token is rejected with 401."""
    res = client.post(
        "/api/submissions",
        headers={"Authorization": "Bearer invalid.jwt.token"},
        json={"challenge_id": str(uuid4()), "flag": "flag{test}"}
    )
    assert res.status_code == 401


def test_nonexistent_challenge_rejected(client, test_setup):
    """Submitting flag for nonexistent challenge ID returns 404."""
    res = client.post(
        "/api/submissions",
        headers=test_setup["student1_header"],
        json={"challenge_id": str(uuid4()), "flag": "flag{test}"}
    )
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_inactive_challenge_rejected(client, test_setup):
    """Submitting flag for inactive challenge returns 404."""
    chall = create_test_challenge(
        client, test_setup["admin_header"],
        title="Inactive Chall", is_active=False
    )
    res = client.post(
        "/api/submissions",
        headers=test_setup["student1_header"],
        json={"challenge_id": chall["id"], "flag": "flag{secret_123}"}
    )
    assert res.status_code == 404
    assert "inactive" in res.json()["detail"].lower()


def test_empty_flag_rejected(client, test_setup):
    """Empty flag candidate fails schema validation with 422."""
    res = client.post(
        "/api/submissions",
        headers=test_setup["student1_header"],
        json={"challenge_id": str(uuid4()), "flag": ""}
    )
    assert res.status_code == 422


# 2. Correct Flag & Point Awarding

def test_correct_flag_submission(client, test_setup):
    """Submitting correct flag awards challenge points and records attempt."""
    chall = create_test_challenge(
        client, test_setup["admin_header"],
        title="Web Injection Solved", points=150, flag="flag{sql_master_1337}"
    )

    res = client.post(
        "/api/submissions",
        headers=test_setup["student1_header"],
        json={"challenge_id": chall["id"], "flag": "flag{sql_master_1337}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["is_correct"] is True
    assert data["points_awarded"] == 150
    assert "Correct flag" in data["message"]
    assert "created_at" in data

    # Verify score updated
    score_res = client.get("/api/auth/me/score", headers=test_setup["student1_header"])
    assert score_res.status_code == 200
    score_data = score_res.json()
    assert score_data["total_points"] == 150
    assert score_data["solves_count"] == 1


# 3. Incorrect Flag

def test_incorrect_flag_submission(client, test_setup):
    """Submitting incorrect flag awards 0 points and records attempt."""
    chall = create_test_challenge(
        client, test_setup["admin_header"],
        title="Crypto Caesar Test", points=100, flag="flag{caesar_real_flag}"
    )

    res = client.post(
        "/api/submissions",
        headers=test_setup["student1_header"],
        json={"challenge_id": chall["id"], "flag": "flag{wrong_guess}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["is_correct"] is False
    assert data["points_awarded"] == 0
    assert "Incorrect flag" in data["message"]

    # Verify score is still 0
    score_res = client.get("/api/auth/me/score", headers=test_setup["student1_header"])
    assert score_res.json()["total_points"] == 0
    assert score_res.json()["solves_count"] == 0


# 4. Duplicate Solve Prevention

def test_duplicate_correct_solve_no_double_points(client, test_setup):
    """Re-submitting correct flag gives 0 points and prevents double counting."""
    chall = create_test_challenge(
        client, test_setup["admin_header"],
        title="Buffer Overflow Test", points=200, flag="flag{eip_overwritten}"
    )

    # 1. First solve
    res1 = client.post(
        "/api/submissions",
        headers=test_setup["student1_header"],
        json={"challenge_id": chall["id"], "flag": "flag{eip_overwritten}"}
    )
    assert res1.status_code == 200
    assert res1.json()["points_awarded"] == 200

    # Wait for cooldown
    time.sleep(2.1)

    # 2. Duplicate solve
    res2 = client.post(
        "/api/submissions",
        headers=test_setup["student1_header"],
        json={"challenge_id": chall["id"], "flag": "flag{eip_overwritten}"}
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["is_correct"] is True
    assert data2["points_awarded"] == 0
    assert "Already solved" in data2["message"]

    # Verify score is still 200 (not 400!)
    score_res = client.get("/api/auth/me/score", headers=test_setup["student1_header"])
    assert score_res.json()["total_points"] == 200
    assert score_res.json()["solves_count"] == 1


# 5. Score Accumulation Across Different Challenges

def test_total_score_multiple_challenges(client, test_setup):
    """Total score accumulates across distinct solved challenges."""
    c1 = create_test_challenge(client, test_setup["admin_header"], title="Chall A", points=100, flag="flag{a}")
    c2 = create_test_challenge(client, test_setup["admin_header"], title="Chall B", points=250, flag="flag{b}")

    # Solve A
    res_a = client.post(
        "/api/submissions",
        headers=test_setup["student1_header"],
        json={"challenge_id": c1["id"], "flag": "flag{a}"}
    )
    assert res_a.json()["points_awarded"] == 100

    time.sleep(2.1)

    # Solve B
    res_b = client.post(
        "/api/submissions",
        headers=test_setup["student1_header"],
        json={"challenge_id": c2["id"], "flag": "flag{b}"}
    )
    assert res_b.json()["points_awarded"] == 250

    # Total score should be 350
    score_res = client.get("/api/auth/me/score", headers=test_setup["student1_header"])
    assert score_res.json()["total_points"] == 350
    assert score_res.json()["solves_count"] == 2


# 6. Challenge Status Endpoint

def test_challenge_status_lifecycle(client, test_setup):
    """Verifies status progression: not_attempted -> attempted -> solved."""
    chall = create_test_challenge(
        client, test_setup["admin_header"],
        title="Status Lifecycle Chall", points=100, flag="flag{lifecycle_flag}"
    )

    # 1. Before any submission
    s1 = client.get(f"/api/challenges/{chall['id']}/status", headers=test_setup["student1_header"])
    assert s1.status_code == 200
    assert s1.json()["status"] == "not_attempted"

    # 2. After wrong submission
    client.post(
        "/api/submissions",
        headers=test_setup["student1_header"],
        json={"challenge_id": chall["id"], "flag": "flag{wrong}"}
    )
    s2 = client.get(f"/api/challenges/{chall['id']}/status", headers=test_setup["student1_header"])
    assert s2.status_code == 200
    assert s2.json()["status"] == "attempted"

    time.sleep(2.1)

    # 3. After correct solve
    client.post(
        "/api/submissions",
        headers=test_setup["student1_header"],
        json={"challenge_id": chall["id"], "flag": "flag{lifecycle_flag}"}
    )
    s3 = client.get(f"/api/challenges/{chall['id']}/status", headers=test_setup["student1_header"])
    assert s3.status_code == 200
    assert s3.json()["status"] == "solved"
    assert s3.json()["points_earned"] == 100
    assert s3.json()["solved_at"] is not None


# 7. Privacy & Security

def test_submission_history_privacy(client, test_setup):
    """User submission history is strictly private to the authenticated caller."""
    chall = create_test_challenge(client, test_setup["admin_header"], title="Privacy Chall", flag="flag{priv}")

    # Student 1 submits
    client.post(
        "/api/submissions",
        headers=test_setup["student1_header"],
        json={"challenge_id": chall["id"], "flag": "flag{priv}"}
    )

    # Student 1 sees their submission
    h1 = client.get("/api/submissions/me", headers=test_setup["student1_header"]).json()
    assert len(h1) == 1
    assert h1[0]["challenge_title"] == "Privacy Chall"

    # Student 2 sees empty history
    h2 = client.get("/api/submissions/me", headers=test_setup["student2_header"]).json()
    assert len(h2) == 0


def test_submission_response_zero_leakage(client, test_setup):
    """Submission endpoint never returns the plaintext flag or flag hash."""
    secret = "flag{top_secret_never_leak_this_value_9999}"
    chall = create_test_challenge(client, test_setup["admin_header"], title="Leakage Test", flag=secret)

    res = client.post(
        "/api/submissions",
        headers=test_setup["student1_header"],
        json={"challenge_id": chall["id"], "flag": secret}
    )
    payload_str = res.text
    assert "flag_hash" not in payload_str
    assert "submitted_flag_hash" not in payload_str
    assert secret not in payload_str


def test_submission_rate_limiting_cooldown(client, test_setup):
    """Submissions sent faster than cooldown period are rejected with 429."""
    chall = create_test_challenge(client, test_setup["admin_header"], title="Rate Chall", flag="flag{rate}")

    # First attempt
    res1 = client.post(
        "/api/submissions",
        headers=test_setup["student1_header"],
        json={"challenge_id": chall["id"], "flag": "flag{wrong1}"}
    )
    assert res1.status_code == 200

    # Immediate second attempt (<2s) -> 429
    res2 = client.post(
        "/api/submissions",
        headers=test_setup["student1_header"],
        json={"challenge_id": chall["id"], "flag": "flag{wrong2}"}
    )
    assert res2.status_code == 429
    assert "cooldown active" in res2.json()["detail"].lower()


def test_concurrent_solves_cannot_double_award_points(tmp_path):
    """Concurrent transactions attempting to solve the same challenge atomically award points once."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.database import Base
    from app.models.user import User, UserRole
    from app.models.solve import Solve
    from app.models.category import Category
    from app.models.challenge import Challenge, ChallengeDifficulty, ChallengeType
    from app.services.challenge_service import hash_flag
    from app.services.submission_service import SubmissionService
    from concurrent.futures import ThreadPoolExecutor

    db_path = tmp_path / "concurrent_solves.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"timeout": 30, "check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    # 1. Setup category, user, challenge
    setup_session = Session()
    cat = Category(name="Concurrency Cat", description="Cat for test")
    setup_session.add(cat)
    setup_session.commit()

    user = User(
        username="concurrent_student",
        email="concurrent@college.edu",
        hashed_password="hash",
        role=UserRole.STUDENT,
        college="OWASP College"
    )
    setup_session.add(user)
    setup_session.commit()

    chall = Challenge(
        title="Concurrent Race Challenge",
        description="Race condition test",
        category_id=cat.id,
        difficulty=ChallengeDifficulty.MEDIUM,
        points=300,
        flag_hash=hash_flag("flag{concurrent_race_proof}"),
        is_active=True,
        challenge_type=ChallengeType.STATIC
    )
    setup_session.add(chall)
    setup_session.commit()
    chall_id = chall.id
    user_id = user.id
    setup_session.close()

    # 2. Worker function executed concurrently in separate sessions
    def solve_worker():
        s = Session()
        u = s.query(User).filter(User.id == user_id).first()
        try:
            # bypass rate limiting cooldown in test to simulate simultaneous network arrival
            res = SubmissionService.process_submission(
                db=s,
                user=u,
                challenge_id=chall_id,
                submitted_flag="flag{concurrent_race_proof}",
                skip_rate_limit=True
            )
            return res
        except Exception as e:
            return {"error": str(e)}
        finally:
            s.close()

    # Run simultaneously
    with ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(solve_worker)
        f2 = executor.submit(solve_worker)
        r1 = f1.result()
        r2 = f2.result()

    # Check that exactly one awarded 300 and the other awarded 0 (or already solved)
    check_session = Session()
    solves = check_session.query(Solve).filter(
        Solve.user_id == user_id,
        Solve.challenge_id == chall_id
    ).all()

    assert len(solves) == 1
    assert solves[0].points_awarded == 300

    awarded_points = [r.get("points_awarded", 0) for r in [r1, r2] if "points_awarded" in r]
    assert sum(awarded_points) == 300
    check_session.close()
    engine.dispose()

