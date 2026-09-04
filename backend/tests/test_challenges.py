import io
from uuid import uuid4
import pytest
from app.models.user import User, UserRole
from app.models.challenge import ChallengeDifficulty, WriteupVisibility
from app.core.security import hash_password, create_access_token
from app.services.challenge_service import ChallengeService


@pytest.fixture
def auth_tokens(db_session):
    """Creates a student, moderator, and admin user, returning valid JWT auth headers."""
    # Seed standard categories
    ChallengeService.seed_categories(db_session)

    student = User(
        username="test_student",
        email="student@college.edu",
        hashed_password=hash_password("StudentPass123!"),
        role=UserRole.STUDENT
    )
    moderator = User(
        username="test_moderator",
        email="mod@college.edu",
        hashed_password=hash_password("ModPass123!"),
        role=UserRole.MODERATOR
    )
    admin = User(
        username="test_admin",
        email="admin@college.edu",
        hashed_password=hash_password("AdminPass123!"),
        role=UserRole.ADMIN
    )
    db_session.add_all([student, moderator, admin])
    db_session.flush()

    def make_header(user):
        token = create_access_token(
            data={"sub": str(user.id), "email": user.email, "role": user.role.value}
        )
        return {"Authorization": f"Bearer {token}"}

    return {
        "student": make_header(student),
        "moderator": make_header(moderator),
        "admin": make_header(admin),
        "student_user": student,
        "mod_user": moderator,
        "admin_user": admin,
    }


def get_first_category_id(client):
    """Helper to get a valid category ID from the API."""
    res = client.get("/api/categories")
    assert res.status_code == 200
    categories = res.json()
    assert len(categories) > 0
    return categories[0]["id"]


# 1. Student Permissions & Viewing

def test_student_list_active_challenges_only(client, auth_tokens):
    """Student can list active challenges, but inactive challenges are hidden."""
    cat_id = get_first_category_id(client)

    # Admin creates 1 active challenge and 1 inactive challenge
    client.post("/api/challenges", headers=auth_tokens["admin"], json={
        "title": "Active Challenge 1",
        "description": "Active desc",
        "category_id": cat_id,
        "difficulty": "easy",
        "points": 100,
        "flag": "flag{active_one}",
        "is_active": True
    })
    client.post("/api/challenges", headers=auth_tokens["admin"], json={
        "title": "Hidden Inactive Challenge",
        "description": "Hidden desc",
        "category_id": cat_id,
        "difficulty": "hard",
        "points": 500,
        "flag": "flag{hidden_one}",
        "is_active": False
    })

    # Student listing
    res = client.get("/api/challenges", headers=auth_tokens["student"])
    assert res.status_code == 200
    titles = [c["title"] for c in res.json()]
    assert "Active Challenge 1" in titles
    assert "Hidden Inactive Challenge" not in titles


def test_student_view_challenge_safe(client, auth_tokens):
    """Student can view challenge details safely without flag exposure."""
    cat_id = get_first_category_id(client)
    create_res = client.post("/api/challenges", headers=auth_tokens["admin"], json={
        "title": "Web Basics",
        "description": "Inspect the headers",
        "category_id": cat_id,
        "difficulty": "easy",
        "points": 150,
        "flag": "flag{super_secret_web_flag}",
        "is_active": True
    })
    chall_id = create_res.json()["id"]

    # Student retrieves challenge
    view_res = client.get(f"/api/challenges/{chall_id}", headers=auth_tokens["student"])
    assert view_res.status_code == 200
    data = view_res.json()
    assert data["title"] == "Web Basics"
    assert data["points"] == 150
    assert "flag" not in data
    assert "flag_hash" not in data


def test_student_forbidden_from_admin_actions(client, auth_tokens):
    """Students receive 403 when attempting create, update, or delete operations."""
    cat_id = get_first_category_id(client)

    # 1. Create attempt
    res_create = client.post("/api/challenges", headers=auth_tokens["student"], json={
        "title": "Unauthorized Create",
        "description": "desc",
        "category_id": cat_id,
        "difficulty": "easy",
        "points": 50,
        "flag": "flag{fail}"
    })
    assert res_create.status_code == 403
    assert res_create.json()["detail"] == "Insufficient permissions"

    # Create challenge as admin first
    create_res = client.post("/api/challenges", headers=auth_tokens["admin"], json={
        "title": "Target Challenge",
        "description": "desc",
        "category_id": cat_id,
        "difficulty": "easy",
        "points": 50,
        "flag": "flag{test}"
    })
    chall_id = create_res.json()["id"]

    # 2. Update attempt
    res_update = client.patch(f"/api/challenges/{chall_id}", headers=auth_tokens["student"], json={"points": 9999})
    assert res_update.status_code == 403

    # 3. Delete attempt
    res_delete = client.delete(f"/api/challenges/{chall_id}", headers=auth_tokens["student"])
    assert res_delete.status_code == 403


# 2. Moderator / Admin Management Operations

def test_moderator_and_admin_crud(client, auth_tokens):
    """Moderator and Admin can create, update, and safely deactivate challenges."""
    cat_id = get_first_category_id(client)

    # Moderator creates challenge
    create_res = client.post("/api/challenges", headers=auth_tokens["moderator"], json={
        "title": "Crypto 101: Caesar",
        "description": "Shift by 13",
        "category_id": cat_id,
        "difficulty": "easy",
        "points": 100,
        "flag": "flag{rot13_is_not_encryption}",
        "is_active": True
    })
    assert create_res.status_code == 201
    chall = create_res.json()
    chall_id = chall["id"]
    assert chall["title"] == "Crypto 101: Caesar"
    assert chall["is_active"] is True

    # Moderator updates challenge
    update_res = client.patch(f"/api/challenges/{chall_id}", headers=auth_tokens["moderator"], json={
        "points": 120,
        "description": "Updated Caesar description"
    })
    assert update_res.status_code == 200
    assert update_res.json()["points"] == 120
    assert update_res.json()["description"] == "Updated Caesar description"

    # Admin deactivates challenge
    delete_res = client.delete(f"/api/challenges/{chall_id}", headers=auth_tokens["admin"])
    assert delete_res.status_code == 200
    assert delete_res.json()["status"] == "deactivated"
    assert delete_res.json()["is_active"] is False

    # Check student can no longer view the deactivated challenge
    student_view = client.get(f"/api/challenges/{chall_id}", headers=auth_tokens["student"])
    assert student_view.status_code == 404


def test_hint_management(client, auth_tokens):
    """Moderators can add, update, and delete hints."""
    cat_id = get_first_category_id(client)
    create_res = client.post("/api/challenges", headers=auth_tokens["admin"], json={
        "title": "Reverse Engineering 1",
        "description": "Find the keygen logic",
        "category_id": cat_id,
        "difficulty": "medium",
        "points": 200,
        "flag": "flag{ghidra_pro}"
    })
    chall_id = create_res.json()["id"]

    # 1. Add hint
    hint_res = client.post(f"/api/challenges/{chall_id}/hints", headers=auth_tokens["moderator"], json={
        "content": "Look at function sub_401120",
        "point_deduction": 20,
        "order": 1
    })
    assert hint_res.status_code == 201
    hint = hint_res.json()
    hint_id = hint["id"]
    assert hint["point_deduction"] == 20

    # 2. Update hint
    update_hint = client.patch(f"/api/challenges/{chall_id}/hints/{hint_id}", headers=auth_tokens["moderator"], json={
        "point_deduction": 25
    })
    assert update_hint.status_code == 200
    assert update_hint.json()["point_deduction"] == 25

    # 3. Delete hint
    del_hint = client.delete(f"/api/challenges/{chall_id}/hints/{hint_id}", headers=auth_tokens["moderator"])
    assert del_hint.status_code == 200
    assert del_hint.json()["status"] == "deleted"


def test_writeup_management_and_visibility(client, auth_tokens):
    """Moderator sets writeup; student can view public writeups, but locked writeups return 403."""
    cat_id = get_first_category_id(client)
    create_res = client.post("/api/challenges", headers=auth_tokens["admin"], json={
        "title": "OSINT Challenge",
        "description": "Locate the flight coordinates",
        "category_id": cat_id,
        "difficulty": "medium",
        "points": 180,
        "flag": "flag{flight_spotted}"
    })
    chall_id = create_res.json()["id"]

    # 1. Set hidden writeup
    client.post(f"/api/challenges/{chall_id}/writeup", headers=auth_tokens["moderator"], json={
        "content": "Official Writeup: Search ADS-B logs.",
        "visibility": "hidden"
    })

    # Student tries to read hidden writeup -> 403
    student_get_hidden = client.get(f"/api/challenges/{chall_id}/writeup", headers=auth_tokens["student"])
    assert student_get_hidden.status_code == 403
    assert "locked" in student_get_hidden.json()["detail"].lower()

    # Admin reads hidden writeup -> 200
    admin_get = client.get(f"/api/challenges/{chall_id}/writeup", headers=auth_tokens["admin"])
    assert admin_get.status_code == 200
    assert "ADS-B" in admin_get.json()["content"]

    # 2. Update writeup to public
    client.post(f"/api/challenges/{chall_id}/writeup", headers=auth_tokens["admin"], json={
        "content": "Official Writeup: Search ADS-B logs.",
        "visibility": "public"
    })

    # Student reads public writeup -> 200
    student_get_pub = client.get(f"/api/challenges/{chall_id}/writeup", headers=auth_tokens["student"])
    assert student_get_pub.status_code == 200
    assert "ADS-B" in student_get_pub.json()["content"]


# 3. Input Validation

def test_validation_errors(client, auth_tokens):
    """Invalid input values are rejected with appropriate HTTP status codes."""
    cat_id = get_first_category_id(client)

    # Negative points -> 422
    res_neg_pts = client.post("/api/challenges", headers=auth_tokens["admin"], json={
        "title": "Negative Points",
        "description": "desc",
        "category_id": cat_id,
        "difficulty": "easy",
        "points": -10,
        "flag": "flag{neg}"
    })
    assert res_neg_pts.status_code == 422

    # Invalid difficulty -> 422
    res_bad_diff = client.post("/api/challenges", headers=auth_tokens["admin"], json={
        "title": "Invalid Diff",
        "description": "desc",
        "category_id": cat_id,
        "difficulty": "impossible",
        "points": 100,
        "flag": "flag{diff}"
    })
    assert res_bad_diff.status_code == 422

    # Empty title -> 422
    res_empty_title = client.post("/api/challenges", headers=auth_tokens["admin"], json={
        "title": "",
        "description": "desc",
        "category_id": cat_id,
        "difficulty": "easy",
        "points": 100,
        "flag": "flag{empty}"
    })
    assert res_empty_title.status_code == 422

    # Nonexistent category ID -> 404
    fake_cat = str(uuid4())
    res_bad_cat = client.post("/api/challenges", headers=auth_tokens["admin"], json={
        "title": "Nonexistent Category",
        "description": "desc",
        "category_id": fake_cat,
        "difficulty": "easy",
        "points": 100,
        "flag": "flag{cat}"
    })
    assert res_bad_cat.status_code == 404


# 4. Security & File Handling

def test_security_flag_and_hash_isolation(client, auth_tokens):
    """Flags and flag hashes are NEVER exposed in challenge listing or detail queries."""
    cat_id = get_first_category_id(client)
    secret_flag = "flag{super_confidential_vault_key_12345}"

    create_res = client.post("/api/challenges", headers=auth_tokens["admin"], json={
        "title": "Confidential Vault",
        "description": "Retrieve the vault contents",
        "category_id": cat_id,
        "difficulty": "insane",
        "points": 500,
        "flag": secret_flag
    })
    chall_id = create_res.json()["id"]

    # 1. Student detail view
    student_res = client.get(f"/api/challenges/{chall_id}", headers=auth_tokens["student"])
    student_data = student_res.json()
    assert "flag" not in student_data
    assert "flag_hash" not in student_data
    assert secret_flag not in str(student_data)

    # 2. Student list view
    student_list = client.get("/api/challenges", headers=auth_tokens["student"]).json()
    for item in student_list:
        assert "flag" not in item
        assert "flag_hash" not in item
        assert secret_flag not in str(item)

    # 3. Admin view also protects plaintext flag
    admin_res = client.get(f"/api/challenges/{chall_id}", headers=auth_tokens["admin"]).json()
    assert "flag" not in admin_res
    assert "flag_hash" not in admin_res


def test_file_upload_and_safe_download(client, auth_tokens):
    """File attachments can be uploaded by admin and safely downloaded without path leaks."""
    cat_id = get_first_category_id(client)
    create_res = client.post("/api/challenges", headers=auth_tokens["admin"], json={
        "title": "Forensic Capture Challenge",
        "description": "Analyze the attached dump",
        "category_id": cat_id,
        "difficulty": "medium",
        "points": 150,
        "flag": "flag{packet_found}"
    })
    chall_id = create_res.json()["id"]

    # Upload file as admin
    file_content = b"PACKET_DUMP_STREAM_CONTENT_MAGIC_BYTES_1337"
    files = {"file": ("capture.pcap", io.BytesIO(file_content), "application/octet-stream")}
    upload_res = client.post(
        f"/api/challenges/{chall_id}/files",
        headers=auth_tokens["admin"],
        files=files
    )
    assert upload_res.status_code == 201
    file_record = upload_res.json()
    assert file_record["filename"] == "capture.pcap"
    assert file_record["file_size"] == len(file_content)
    file_id = file_record["id"]

    # Verify internal filesystem path is NOT in the response
    assert "storage_path" not in file_record
    assert "uploads" not in str(file_record)

    # Download file as student
    download_res = client.get(
        f"/api/challenges/{chall_id}/files/{file_id}/download",
        headers=auth_tokens["student"]
    )
    assert download_res.status_code == 200
    assert download_res.content == file_content
    assert 'attachment; filename="capture.pcap"' in download_res.headers.get("content-disposition", "")
