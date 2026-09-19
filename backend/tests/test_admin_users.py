from uuid import uuid4
import pytest
from app.models.user import User, UserRole
from app.models.challenge import Challenge, ChallengeDifficulty, ChallengeType
from app.core.security import hash_password, create_access_token
from app.services.challenge_service import ChallengeService


@pytest.fixture
def admin_user_fixture(db_session):
    """Sets up users with different roles for admin management tests."""
    ChallengeService.seed_categories(db_session)

    student1 = User(
        username="alice_student",
        email="alice@mit.edu",
        name="Alice Walker",
        college="MIT",
        hashed_password=hash_password("Pass123!"),
        role=UserRole.STUDENT,
        is_active=True,
        is_banned=False,
        is_muted=False,
    )
    student2 = User(
        username="bob_student",
        email="bob@stanford.edu",
        name="Bob Builder",
        college="Stanford",
        hashed_password=hash_password("Pass123!"),
        role=UserRole.STUDENT,
        is_active=True,
        is_banned=False,
        is_muted=False,
    )
    moderator = User(
        username="carol_mod",
        email="carol@mit.edu",
        name="Carol Danvers",
        college="MIT",
        hashed_password=hash_password("Pass123!"),
        role=UserRole.MODERATOR,
        is_active=True,
        is_banned=False,
        is_muted=False,
    )
    admin = User(
        username="dave_admin",
        email="dave@owasp.org",
        name="Dave Director",
        college="OWASP College",
        hashed_password=hash_password("Pass123!"),
        role=UserRole.ADMIN,
        is_active=True,
        is_banned=False,
        is_muted=False,
    )
    db_session.add_all([student1, student2, moderator, admin])
    db_session.flush()

    def make_header(user):
        token = create_access_token(
            data={"sub": str(user.id), "email": user.email, "role": user.role.value}
        )
        return {"Authorization": f"Bearer {token}"}

    return {
        "student1": student1,
        "student2": student2,
        "moderator": moderator,
        "admin": admin,
        "student1_headers": make_header(student1),
        "student2_headers": make_header(student2),
        "mod_headers": make_header(moderator),
        "admin_headers": make_header(admin),
    }


def test_student_forbidden_from_admin_users(client, admin_user_fixture):
    """Students cannot access administrative user endpoints."""
    res = client.get("/api/admin/users", headers=admin_user_fixture["student1_headers"])
    assert res.status_code == 403


def test_admin_list_users_with_search_and_filter(client, admin_user_fixture):
    """Admins and moderators can list, search, and filter users."""
    # List all
    res = client.get("/api/admin/users", headers=admin_user_fixture["admin_headers"])
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 4
    assert len(data["items"]) >= 4

    # Search by college
    res_search = client.get("/api/admin/users?search=Stanford", headers=admin_user_fixture["mod_headers"])
    assert res_search.status_code == 200
    items = res_search.json()["items"]
    assert len(items) == 1
    assert items[0]["username"] == "bob_student"

    # Filter by role
    res_role = client.get("/api/admin/users?role=moderator", headers=admin_user_fixture["admin_headers"])
    assert res_role.status_code == 200
    items_mod = res_role.json()["items"]
    assert all(u["role"] == "moderator" for u in items_mod)


def test_admin_get_user_details_with_submissions(client, db_session, admin_user_fixture):
    """Retrieves user detail with recent submission tracking."""
    alice = admin_user_fixture["student1"]
    res = client.get(f"/api/admin/users/{alice.id}", headers=admin_user_fixture["admin_headers"])
    assert res.status_code == 200
    data = res.json()
    assert data["username"] == "alice_student"
    assert "recent_submissions" in data
    assert isinstance(data["recent_submissions"], list)


def test_admin_update_user_role(client, admin_user_fixture):
    """Administrators can promote or demote user roles."""
    bob = admin_user_fixture["student2"]
    res = client.patch(
        f"/api/admin/users/{bob.id}",
        headers=admin_user_fixture["admin_headers"],
        json={"role": "moderator"}
    )
    assert res.status_code == 200
    assert res.json()["role"] == "moderator"


def test_admin_ban_user_and_enforce_block(client, admin_user_fixture):
    """Banning a user sets is_banned=True and prevents active API requests."""
    bob = admin_user_fixture["student2"]

    # 1. Ban Bob
    res = client.patch(
        f"/api/admin/users/{bob.id}",
        headers=admin_user_fixture["admin_headers"],
        json={"is_banned": True}
    )
    assert res.status_code == 200
    assert res.json()["is_banned"] is True
    assert res.json()["is_active"] is False

    # 2. Bob tries to access an authenticated endpoint
    res_block = client.get("/api/profile/me", headers=admin_user_fixture["student2_headers"])
    assert res_block.status_code == 403
    assert "suspended" in res_block.json()["detail"].lower()


def test_admin_mute_user_and_enforce_discussion_restriction(client, db_session, admin_user_fixture):
    """Muted users are blocked from creating discussions or comments."""
    alice = admin_user_fixture["student1"]
    cat = ChallengeService.get_categories(db_session)[0]

    # Create challenge & mark solved for Alice
    from app.schemas.challenge import ChallengeCreate
    from app.services.submission_service import SubmissionService
    chal = ChallengeService.create_challenge(
        db_session,
        ChallengeCreate(
            title="Discussion Mute Test",
            description="Testing mute",
            category_id=cat.id,
            difficulty=ChallengeDifficulty.EASY,
            points=100,
            flag="CTF{mute_test_flag}"
        )
    )
    from app.models.submission import Submission
    from app.models.solve import Solve
    sub = Submission(
        user_id=alice.id,
        challenge_id=chal.id,
        submitted_flag_hash="dummy_flag_hash_123",
        is_correct=True,
        points_awarded=100
    )
    db_session.add(sub)
    db_session.flush()
    solve = Solve(user_id=alice.id, challenge_id=chal.id, submission_id=sub.id, points_awarded=100)
    db_session.add(solve)
    db_session.flush()

    # Alice can post initially
    res_post = client.post(
        f"/api/challenges/{chal.id}/discussions",
        headers=admin_user_fixture["student1_headers"],
        json={"title": "Great Challenge", "content": "I solved this easily!"}
    )
    assert res_post.status_code == 201

    # Admin mutes Alice
    res_mute = client.patch(
        f"/api/admin/users/{alice.id}",
        headers=admin_user_fixture["admin_headers"],
        json={"is_muted": True}
    )
    assert res_mute.status_code == 200
    assert res_mute.json()["is_muted"] is True

    # Alice tries to post another discussion
    res_post_blocked = client.post(
        f"/api/challenges/{chal.id}/discussions",
        headers=admin_user_fixture["student1_headers"],
        json={"title": "Another Post", "content": "Can I post?"}
    )
    assert res_post_blocked.status_code == 403
    assert "muted" in res_post_blocked.json()["detail"].lower()


def test_admin_self_demotion_and_self_ban_blocked(client, admin_user_fixture):
    """Administrators cannot ban or demote themselves."""
    admin = admin_user_fixture["admin"]

    # 1. Self demotion
    res_demote = client.patch(
        f"/api/admin/users/{admin.id}",
        headers=admin_user_fixture["admin_headers"],
        json={"role": "student"}
    )
    assert res_demote.status_code == 400
    assert "cannot demote themselves" in res_demote.json()["detail"].lower()

    # 2. Self ban
    res_ban = client.patch(
        f"/api/admin/users/{admin.id}",
        headers=admin_user_fixture["admin_headers"],
        json={"is_banned": True}
    )
    assert res_ban.status_code == 400
    assert "cannot ban themselves" in res_ban.json()["detail"].lower()
