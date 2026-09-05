from uuid import uuid4
import pytest
from app.models.user import User, UserRole
from app.models.category import Category
from app.models.challenge import Challenge, ChallengeDifficulty, ChallengeType, WriteupVisibility
from app.core.security import hash_password, create_access_token
from app.services.challenge_service import hash_flag


@pytest.fixture
def phase6_setup(db_session):
    """Sets up users, category, and an active challenge."""
    # 1. Users
    student = User(
        username="p6_student",
        email="p6_student@college.edu",
        hashed_password=hash_password("Pass123!"),
        role=UserRole.STUDENT,
        college="OWASP College"
    )
    moderator = User(
        username="p6_moderator",
        email="p6_moderator@college.edu",
        hashed_password=hash_password("Pass123!"),
        role=UserRole.MODERATOR,
        college="OWASP College"
    )
    admin = User(
        username="p6_admin",
        email="p6_admin@college.edu",
        hashed_password=hash_password("Pass123!"),
        role=UserRole.ADMIN,
        college="OWASP College"
    )
    db_session.add_all([student, moderator, admin])
    db_session.commit()

    student_token = create_access_token(data={"sub": str(student.id), "role": student.role.value})
    mod_token = create_access_token(data={"sub": str(moderator.id), "role": moderator.role.value})
    admin_token = create_access_token(data={"sub": str(admin.id), "role": admin.role.value})

    # 2. Category
    cat = Category(name="Forensics & Analysis", description="Forensic challenges")
    db_session.add(cat)
    db_session.commit()

    # 3. 500-point Challenge
    chall = Challenge(
        title="Memory Dump Deep Dive",
        description="Analyze dump file to find hidden password",
        category_id=cat.id,
        difficulty=ChallengeDifficulty.HARD,
        points=500,
        flag_hash=hash_flag("flag{volatility_expert_master}"),
        is_active=True,
        challenge_type=ChallengeType.STATIC
    )
    db_session.add(chall)
    db_session.commit()

    return {
        "student": student,
        "moderator": moderator,
        "admin": admin,
        "student_header": {"Authorization": f"Bearer {student_token}"},
        "mod_header": {"Authorization": f"Bearer {mod_token}"},
        "admin_header": {"Authorization": f"Bearer {admin_token}"},
        "category": cat,
        "challenge": chall,
    }


# =========================================================================
# 1. HINT AUTHORING & PERMISSIONS
# =========================================================================

def test_admin_and_moderator_can_create_hints(client, phase6_setup):
    """Admin and moderator can create hints; student is rejected with 403."""
    chall_id = phase6_setup["challenge"].id

    # Admin creates Hint 1
    res_admin = client.post(
        f"/api/challenges/{chall_id}/hints",
        headers=phase6_setup["admin_header"],
        json={
            "title": "First Step Hint",
            "content": "Check the memory profile using volatility imageinfo.",
            "points_deduction": 50,
            "display_order": 1
        }
    )
    assert res_admin.status_code == 201
    data_admin = res_admin.json()
    assert data_admin["title"] == "First Step Hint"
    assert data_admin["content"] == "Check the memory profile using volatility imageinfo."
    assert data_admin["points_deduction"] == 50
    assert data_admin["display_order"] == 1

    # Moderator creates Hint 2
    res_mod = client.post(
        f"/api/challenges/{chall_id}/hints",
        headers=phase6_setup["mod_header"],
        json={
            "title": "Process List Hint",
            "content": "Inspect suspicious PID using pslist and malfind.",
            "points_deduction": 100,
            "display_order": 2
        }
    )
    assert res_mod.status_code == 201
    assert res_mod.json()["points_deduction"] == 100

    # Student cannot create hint -> 403
    res_student = client.post(
        f"/api/challenges/{chall_id}/hints",
        headers=phase6_setup["student_header"],
        json={
            "title": "Illegal Student Hint",
            "content": "Secret info",
            "points_deduction": 0,
            "display_order": 3
        }
    )
    assert res_student.status_code == 403


def test_admin_and_mod_can_update_and_delete_hints(client, phase6_setup):
    """Admin and moderator can update and delete hints; students are forbidden."""
    chall_id = phase6_setup["challenge"].id

    # Create hint
    res = client.post(
        f"/api/challenges/{chall_id}/hints",
        headers=phase6_setup["admin_header"],
        json={"title": "Original Title", "content": "Original content", "points_deduction": 30}
    )
    hint_id = res.json()["id"]

    # Student update rejected
    res_stu_up = client.put(
        f"/api/challenges/{chall_id}/hints/{hint_id}",
        headers=phase6_setup["student_header"],
        json={"points_deduction": 0}
    )
    assert res_stu_up.status_code == 403

    # Moderator update accepted
    res_mod_up = client.put(
        f"/api/challenges/{chall_id}/hints/{hint_id}",
        headers=phase6_setup["mod_header"],
        json={"title": "Updated Title", "points_deduction": 45}
    )
    assert res_mod_up.status_code == 200
    assert res_mod_up.json()["title"] == "Updated Title"
    assert res_mod_up.json()["points_deduction"] == 45

    # Student delete rejected
    res_stu_del = client.delete(
        f"/api/challenges/{chall_id}/hints/{hint_id}",
        headers=phase6_setup["student_header"]
    )
    assert res_stu_del.status_code == 403

    # Admin delete accepted
    res_adm_del = client.delete(
        f"/api/challenges/{chall_id}/hints/{hint_id}",
        headers=phase6_setup["admin_header"]
    )
    assert res_adm_del.status_code == 200
    assert res_adm_del.json()["status"] == "deleted"


# =========================================================================
# 2. HINT VISIBILITY & CONTENT ISOLATION
# =========================================================================

def test_unused_hint_content_is_never_exposed_to_student(client, phase6_setup):
    """Students only receive hint metadata (title, deduction, display order); content is None."""
    chall_id = phase6_setup["challenge"].id

    # Admin creates hint
    client.post(
        f"/api/challenges/{chall_id}/hints",
        headers=phase6_setup["admin_header"],
        json={
            "title": "Secret Clue",
            "content": "VERY_CONFIDENTIAL_CLUE_DO_NOT_LEAK",
            "points_deduction": 75,
            "display_order": 1
        }
    )

    # Student lists hints
    res = client.get(f"/api/challenges/{chall_id}/hints", headers=phase6_setup["student_header"])
    assert res.status_code == 200
    hints = res.json()
    assert len(hints) == 1
    hint = hints[0]
    assert hint["title"] == "Secret Clue"
    assert hint["points_deduction"] == 75
    assert hint["content"] is None
    assert hint["used"] is False

    # Admin lists hints -> sees full content
    admin_res = client.get(f"/api/challenges/{chall_id}/hints", headers=phase6_setup["admin_header"])
    assert admin_res.json()[0]["content"] == "VERY_CONFIDENTIAL_CLUE_DO_NOT_LEAK"


# =========================================================================
# 3. STUDENT HINT UNLOCKING & USAGE RULES
# =========================================================================

def test_student_can_unlock_hint_and_reveal_content(client, phase6_setup):
    """Student unlocks hint via /use: receives revealed content and used flag becomes True."""
    chall_id = phase6_setup["challenge"].id

    create_res = client.post(
        f"/api/challenges/{chall_id}/hints",
        headers=phase6_setup["admin_header"],
        json={
            "title": "Profile Hint",
            "content": "Use Win7SP1x64 profile.",
            "points_deduction": 40,
            "display_order": 1
        }
    )
    hint_id = create_res.json()["id"]

    # Student unlocks hint
    use_res = client.post(
        f"/api/challenges/{chall_id}/hints/{hint_id}/use",
        headers=phase6_setup["student_header"]
    )
    assert use_res.status_code == 200
    use_data = use_res.json()
    assert use_data["hint_id"] == hint_id
    assert use_data["content"] == "Use Win7SP1x64 profile."
    assert use_data["points_deducted"] == 40

    # Subsequent listing by this student now includes the revealed content
    list_res = client.get(f"/api/challenges/{chall_id}/hints", headers=phase6_setup["student_header"])
    unlocked_hint = list_res.json()[0]
    assert unlocked_hint["used"] is True
    assert unlocked_hint["content"] == "Use Win7SP1x64 profile."


def test_inactive_hint_cannot_be_used(client, phase6_setup):
    """Inactive hints cannot be used by students."""
    chall_id = phase6_setup["challenge"].id

    create_res = client.post(
        f"/api/challenges/{chall_id}/hints",
        headers=phase6_setup["admin_header"],
        json={
            "title": "Disabled Hint",
            "content": "Secret",
            "points_deduction": 50,
            "is_active": False
        }
    )
    hint_id = create_res.json()["id"]

    res = client.post(
        f"/api/challenges/{chall_id}/hints/{hint_id}/use",
        headers=phase6_setup["student_header"]
    )
    assert res.status_code == 400
    assert "inactive" in res.json()["detail"].lower()


def test_hint_cannot_be_used_twice(client, phase6_setup):
    """Attempting to use the same hint twice is rejected with 400."""
    chall_id = phase6_setup["challenge"].id

    create_res = client.post(
        f"/api/challenges/{chall_id}/hints",
        headers=phase6_setup["admin_header"],
        json={"title": "One-time Hint", "content": "Once only", "points_deduction": 20}
    )
    hint_id = create_res.json()["id"]

    # First use -> 200
    res1 = client.post(
        f"/api/challenges/{chall_id}/hints/{hint_id}/use",
        headers=phase6_setup["student_header"]
    )
    assert res1.status_code == 200

    # Second use -> 400
    res2 = client.post(
        f"/api/challenges/{chall_id}/hints/{hint_id}/use",
        headers=phase6_setup["student_header"]
    )
    assert res2.status_code == 400
    assert "already been unlocked" in res2.json()["detail"].lower()


def test_hint_cannot_be_used_after_solving(client, phase6_setup):
    """A student who has already solved a challenge cannot use additional hints."""
    chall_id = phase6_setup["challenge"].id

    create_res = client.post(
        f"/api/challenges/{chall_id}/hints",
        headers=phase6_setup["admin_header"],
        json={"title": "Late Hint", "content": "Too late", "points_deduction": 30}
    )
    hint_id = create_res.json()["id"]

    # Student solves challenge first
    sub_res = client.post(
        "/api/submissions",
        headers=phase6_setup["student_header"],
        json={"challenge_id": str(chall_id), "flag": "flag{volatility_expert_master}"}
    )
    assert sub_res.status_code == 200
    assert sub_res.json()["is_correct"] is True

    # Student attempts to use hint after solve -> 400
    res = client.post(
        f"/api/challenges/{chall_id}/hints/{hint_id}/use",
        headers=phase6_setup["student_header"]
    )
    assert res.status_code == 400
    assert "after already solving" in res.json()["detail"].lower()


# =========================================================================
# 4. SCORING INTEGRATION: 500 - 50 - 100 = 350
# =========================================================================

def test_full_hint_deduction_and_scoring_flow(client, phase6_setup):
    """
    Challenge base = 500
    Hint 1 deduction = 50
    Hint 2 deduction = 100
    Student unlocks both: 500 - 50 - 100 = 350
    Solve awards exactly 350 points.
    Challenge base points remain 500.
    Leaderboard reflects 350 points.
    """
    chall_id = phase6_setup["challenge"].id

    # 1. Admin creates Hint 1 (-50)
    h1_res = client.post(
        f"/api/challenges/{chall_id}/hints",
        headers=phase6_setup["admin_header"],
        json={"title": "Hint 1", "content": "Clue 1", "points_deduction": 50, "display_order": 1}
    )
    h1_id = h1_res.json()["id"]

    # 2. Admin creates Hint 2 (-100)
    h2_res = client.post(
        f"/api/challenges/{chall_id}/hints",
        headers=phase6_setup["admin_header"],
        json={"title": "Hint 2", "content": "Clue 2", "points_deduction": 100, "display_order": 2}
    )
    h2_id = h2_res.json()["id"]

    # 3. Student uses Hint 1
    use1 = client.post(
        f"/api/challenges/{chall_id}/hints/{h1_id}/use",
        headers=phase6_setup["student_header"]
    )
    assert use1.status_code == 200
    assert use1.json()["points_deducted"] == 50

    # 4. Student uses Hint 2
    use2 = client.post(
        f"/api/challenges/{chall_id}/hints/{h2_id}/use",
        headers=phase6_setup["student_header"]
    )
    assert use2.status_code == 200
    assert use2.json()["points_deducted"] == 100

    # 5. Student submits correct flag
    sub_res = client.post(
        "/api/submissions",
        headers=phase6_setup["student_header"],
        json={"challenge_id": str(chall_id), "flag": "flag{volatility_expert_master}"}
    )
    assert sub_res.status_code == 200
    sub_data = sub_res.json()
    assert sub_data["is_correct"] is True
    # Awarded points MUST be 350
    assert sub_data["points_awarded"] == 350

    # 6. Verify challenge base points remain 500 in challenge API
    chall_res = client.get(f"/api/challenges/{chall_id}", headers=phase6_setup["student_header"])
    assert chall_res.json()["points"] == 500

    # 7. Verify student user score is 350
    score_res = client.get("/api/auth/me/score", headers=phase6_setup["student_header"])
    assert score_res.json()["total_points"] == 350
    assert score_res.json()["solves_count"] == 1

    # 8. Verify leaderboard reflects 350 points
    lb_res = client.get("/api/leaderboard/global")
    assert lb_res.status_code == 200
    items = lb_res.json()["items"]
    assert len(items) == 1
    assert items[0]["username"] == "p6_student"
    assert items[0]["total_points"] == 350


# =========================================================================
# 5. WRITEUP SYSTEM & VISIBILITY RULES
# =========================================================================

def test_writeup_visibility_rules(client, phase6_setup):
    """
    Tests visibility enforcement:
    - hidden: 403 to students, 200 to admin
    - after_solve: 403 before solve, 200 after solve
    - public: 200 to all
    - after_event: 403 to students
    - student forbidden from creating/updating/deleting writeups
    """
    chall_id = phase6_setup["challenge"].id

    # 1. Student cannot create writeup -> 403
    stu_create = client.post(
        f"/api/challenges/{chall_id}/writeups",
        headers=phase6_setup["student_header"],
        json={"title": "Hacker Writeup", "content": "I hacked it"}
    )
    assert stu_create.status_code == 403

    # 2. Admin creates writeup with visibility = HIDDEN
    admin_create = client.post(
        f"/api/challenges/{chall_id}/writeups",
        headers=phase6_setup["admin_header"],
        json={"title": "Official Solution", "content": "Admin internal solution notes", "visibility": "hidden"}
    )
    assert admin_create.status_code == 200
    writeup_id = admin_create.json()["id"]

    # Student tries to view hidden writeup -> 403
    stu_hidden = client.get(f"/api/challenges/{chall_id}/writeup", headers=phase6_setup["student_header"])
    assert stu_hidden.status_code == 403

    # Admin views hidden writeup -> 200
    adm_hidden = client.get(f"/api/challenges/{chall_id}/writeup", headers=phase6_setup["admin_header"])
    assert adm_hidden.status_code == 200
    assert adm_hidden.json()["content"] == "Admin internal solution notes"

    # 3. Update visibility to AFTER_SOLVE
    client.put(
        f"/api/challenges/{chall_id}/writeups/{writeup_id}",
        headers=phase6_setup["admin_header"],
        json={"visibility": "after_solve"}
    )

    # Student hasn't solved yet -> 403
    stu_unsolved = client.get(f"/api/challenges/{chall_id}/writeup", headers=phase6_setup["student_header"])
    assert stu_unsolved.status_code == 403
    assert "solving the challenge is required" in stu_unsolved.json()["detail"].lower()

    # Student solves challenge
    client.post(
        "/api/submissions",
        headers=phase6_setup["student_header"],
        json={"challenge_id": str(chall_id), "flag": "flag{volatility_expert_master}"}
    )

    # Student now views after_solve writeup -> 200
    stu_solved = client.get(f"/api/challenges/{chall_id}/writeup", headers=phase6_setup["student_header"])
    assert stu_solved.status_code == 200
    assert stu_solved.json()["content"] == "Admin internal solution notes"

    # 4. Update visibility to AFTER_EVENT -> locked for students
    client.put(
        f"/api/challenges/{chall_id}/writeups/{writeup_id}",
        headers=phase6_setup["admin_header"],
        json={"visibility": "after_event"}
    )
    stu_event = client.get(f"/api/challenges/{chall_id}/writeup", headers=phase6_setup["student_header"])
    assert stu_event.status_code == 403
    assert "event has not concluded" in stu_event.json()["detail"].lower()

    # 5. Update visibility to PUBLIC -> 200
    client.put(
        f"/api/challenges/{chall_id}/writeups/{writeup_id}",
        headers=phase6_setup["admin_header"],
        json={"visibility": "public"}
    )
    stu_pub = client.get(f"/api/challenges/{chall_id}/writeup", headers=phase6_setup["student_header"])
    assert stu_pub.status_code == 200


def test_writeup_and_hint_wrong_challenge_rejected(client, phase6_setup):
    """Requesting hint or writeup with non-matching challenge ID is rejected with 404."""
    chall_id = phase6_setup["challenge"].id
    other_chall_id = uuid4()

    # Hint for other challenge
    res_hint = client.get(
        f"/api/challenges/{other_chall_id}/hints",
        headers=phase6_setup["admin_header"]
    )
    assert res_hint.status_code == 404

    # Writeup for other challenge
    res_writeup = client.get(
        f"/api/challenges/{other_chall_id}/writeup",
        headers=phase6_setup["admin_header"]
    )
    assert res_writeup.status_code == 404
