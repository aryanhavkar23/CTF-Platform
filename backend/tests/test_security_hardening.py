import io
import uuid
from pathlib import Path
import pytest
from pydantic import ValidationError
from fastapi import APIRouter
from fastapi.testclient import TestClient

from app.config import Settings, settings
from app.main import app
from app.database import get_db
from app.models.user import User, UserRole
from app.models.challenge import Challenge, ChallengeDifficulty, ChallengeType
from app.core.security import hash_password, create_access_token
from app.services.challenge_service import ChallengeService
from app.services.storage_service import storage_service
from app.services.notification_service import NotificationService
from app.schemas.challenge import ChallengeCreate


@pytest.fixture
def security_users(db_session):
    """Creates student, moderator, admin users and returns auth headers."""
    ChallengeService.seed_categories(db_session)

    student_a = User(
        username="sec_student_a",
        email="student_a@college.edu",
        hashed_password=hash_password("Pass123456!"),
        role=UserRole.STUDENT,
        is_active=True
    )
    student_b = User(
        username="sec_student_b",
        email="student_b@college.edu",
        hashed_password=hash_password("Pass123456!"),
        role=UserRole.STUDENT,
        is_active=True
    )
    moderator = User(
        username="sec_mod",
        email="mod@college.edu",
        hashed_password=hash_password("ModPass123456!"),
        role=UserRole.MODERATOR,
        is_active=True
    )
    admin = User(
        username="sec_admin",
        email="admin@college.edu",
        hashed_password=hash_password("AdminPass123456!"),
        role=UserRole.ADMIN,
        is_active=True
    )
    db_session.add_all([student_a, student_b, moderator, admin])
    db_session.flush()

    def make_header(user):
        token = create_access_token(
            data={"sub": str(user.id), "email": user.email, "role": user.role.value}
        )
        return {"Authorization": f"Bearer {token}"}

    return {
        "student_a": make_header(student_a),
        "student_b": make_header(student_b),
        "mod": make_header(moderator),
        "admin": make_header(admin),
        "user_a": student_a,
        "user_b": student_b,
        "mod_user": moderator,
        "admin_user": admin,
    }


# ==============================================================================
# 1. Configuration & Production Secret Validation Tests
# ==============================================================================

def test_production_config_rejects_insecure_secret():
    """Proves production mode rejects weak/default secret keys or debug=True."""
    # 1. Insecure default secret
    with pytest.raises(ValidationError, match="Production security violation"):
        Settings(
            ENVIRONMENT="production",
            DEBUG=False,
            SECRET_KEY="development_secret_key_please_change_in_production",
            CORS_ORIGINS=["https://ctf.owasp.org"]
        )

    # 2. Secret key under 32 chars
    with pytest.raises(ValidationError, match="Production security violation"):
        Settings(
            ENVIRONMENT="production",
            DEBUG=False,
            SECRET_KEY="short_secret_key",
            CORS_ORIGINS=["https://ctf.owasp.org"]
        )

    # 3. DEBUG=True in production
    with pytest.raises(ValidationError, match="Production security violation"):
        Settings(
            ENVIRONMENT="production",
            DEBUG=True,
            SECRET_KEY="super_strong_production_secret_key_1234567890",
            CORS_ORIGINS=["https://ctf.owasp.org"]
        )

    # 4. Valid production config
    valid_prod = Settings(
        ENVIRONMENT="production",
        DEBUG=False,
        SECRET_KEY="super_strong_production_secret_key_1234567890",
        CORS_ORIGINS=["https://ctf.owasp.org"]
    )
    assert valid_prod.ENVIRONMENT == "production"


def test_production_config_rejects_wildcard_cors_with_credentials():
    """Proves production rejects '*' CORS with credentials enabled."""
    with pytest.raises(ValidationError, match="Wildcard CORS origin"):
        Settings(
            ENVIRONMENT="production",
            DEBUG=False,
            SECRET_KEY="super_strong_production_secret_key_1234567890",
            CORS_ORIGINS=["*"],
            CORS_ALLOW_CREDENTIALS=True
        )


# ==============================================================================
# 2. HTTP Security Headers Tests
# ==============================================================================

def test_security_headers_present(client):
    """Verifies presence of standard defense-in-depth security headers."""
    res = client.get("/health")
    assert res.status_code == 200
    assert res.headers.get("X-Content-Type-Options") == "nosniff"
    assert res.headers.get("X-Frame-Options") == "DENY"
    assert res.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "Permissions-Policy" in res.headers
    assert "Content-Security-Policy" in res.headers
    assert "default-src 'self'" in res.headers["Content-Security-Policy"]


# ==============================================================================
# 3. Request ID Correlation Middleware Tests
# ==============================================================================

def test_request_id_middleware(client):
    """Verifies X-Request-ID is generated, returned, and preserved if supplied."""
    # Generated
    res = client.get("/health")
    assert res.status_code == 200
    req_id = res.headers.get("X-Request-ID")
    assert req_id is not None
    assert len(req_id) >= 16

    # Preserved when client provides it
    custom_id = "custom-trace-uuid-123456789"
    res2 = client.get("/health", headers={"X-Request-ID": custom_id})
    assert res2.headers.get("X-Request-ID") == custom_id


# ==============================================================================
# 4. Global Error Handling & Traceback Masking Tests
# ==============================================================================

def test_global_exception_handler_masks_traceback_when_debug_false(db_session):
    """Verifies unhandled errors return generic detail without tracebacks when DEBUG=False."""
    test_err_router = APIRouter()

    @test_err_router.get("/api/test-server-error-hardening")
    def trigger_error():
        raise RuntimeError("Database password leaked: secret_pass_12345")

    app.include_router(test_err_router)

    orig_debug = settings.DEBUG
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        settings.DEBUG = False
        with TestClient(app, raise_server_exceptions=False) as safe_client:
            res = safe_client.get("/api/test-server-error-hardening")
            assert res.status_code == 500
            data = res.json()
            assert data["detail"] == "An internal server error occurred."
            assert "request_id" in data
            assert "secret_pass_12345" not in res.text
            assert "RuntimeError" not in res.text
    finally:
        settings.DEBUG = orig_debug
        app.dependency_overrides.pop(get_db, None)


# ==============================================================================
# 5. Health & Readiness Probes Tests
# ==============================================================================

def test_liveness_and_readiness_probes(client):
    """Verifies /health, /health/ready, and /api/health probes."""
    # 1. Liveness
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
    assert "environment" in res.json()

    # 2. Readiness
    res_ready = client.get("/health/ready")
    assert res_ready.status_code == 200
    assert res_ready.json()["status"] == "ready"
    assert res_ready.json()["database"] == "connected"

    # 3. Backwards compatible /api/health
    res_api = client.get("/api/health")
    assert res_api.status_code == 200
    assert res_api.json()["status"] == "healthy"


# ==============================================================================
# 6. File Upload & Download Security Tests
# ==============================================================================

def test_file_upload_size_limit_rejection(client, db_session, security_users):
    """Verifies files exceeding MAX_FILE_UPLOAD_SIZE return HTTP 413."""
    cat = ChallengeService.get_categories(db_session)[0]
    chal = ChallengeService.create_challenge(
        db_session,
        ChallengeCreate(
            title="Upload Size Test Challenge",
            description="Testing upload limits",
            category_id=cat.id,
            difficulty=ChallengeDifficulty.EASY,
            points=100,
            flag="CTF{upload_size_limit_flag}"
        )
    )

    orig_limit = settings.MAX_FILE_UPLOAD_SIZE
    try:
        settings.MAX_FILE_UPLOAD_SIZE = 50  # 50 bytes
        oversized_content = b"A" * 150
        res = client.post(
            f"/api/challenges/{chal.id}/files",
            headers=security_users["admin"],
            files={"file": ("test.txt", io.BytesIO(oversized_content), "text/plain")}
        )
        assert res.status_code == 413
        assert "exceeds maximum allowed limit" in res.json()["detail"]
    finally:
        settings.MAX_FILE_UPLOAD_SIZE = orig_limit


def test_file_upload_disallowed_extension_rejection(client, db_session, security_users):
    """Verifies prohibited file extensions return HTTP 400."""
    cat = ChallengeService.get_categories(db_session)[0]
    chal = ChallengeService.create_challenge(
        db_session,
        ChallengeCreate(
            title="Upload Ext Test Challenge",
            description="Testing ext limits",
            category_id=cat.id,
            difficulty=ChallengeDifficulty.EASY,
            points=100,
            flag="CTF{upload_ext_limit_flag}"
        )
    )

    # Disallowed: .php, .jsp, .sh
    for bad_file in ["webshell.php", "shell.jsp", "script.sh"]:
        res = client.post(
            f"/api/challenges/{chal.id}/files",
            headers=security_users["admin"],
            files={"file": (bad_file, io.BytesIO(b"malicious payload"), "application/octet-stream")}
        )
        assert res.status_code == 400
        assert "not allowed for security reasons" in res.json()["detail"]

    # Allowed: .pcap
    res_ok = client.post(
        f"/api/challenges/{chal.id}/files",
        headers=security_users["admin"],
        files={"file": ("packet.pcap", io.BytesIO(b"packet-data"), "application/vnd.tcpdump.pcap")}
    )
    assert res_ok.status_code == 201


def test_inactive_challenge_file_download_authorization(client, db_session, security_users):
    """Verifies students cannot download files from inactive challenges, but admins can."""
    cat = ChallengeService.get_categories(db_session)[0]
    chal = ChallengeService.create_challenge(
        db_session,
        ChallengeCreate(
            title="Inactive File Challenge",
            description="Only admins can download attachments before release",
            category_id=cat.id,
            difficulty=ChallengeDifficulty.MEDIUM,
            points=200,
            flag="CTF{inactive_chal_flag}",
            is_active=False
        )
    )

    # Admin uploads file
    upload_res = client.post(
        f"/api/challenges/{chal.id}/files",
        headers=security_users["admin"],
        files={"file": ("secret_chal.pcap", io.BytesIO(b"top secret challenge data"), "application/octet-stream")}
    )
    assert upload_res.status_code == 201
    file_id = upload_res.json()["id"]

    # Student attempts download -> 403
    student_res = client.get(
        f"/api/challenges/{chal.id}/files/{file_id}/download",
        headers=security_users["student_a"]
    )
    assert student_res.status_code == 403
    assert "Cannot download files for an inactive challenge" in student_res.json()["detail"]

    # Admin downloads -> 200
    admin_res = client.get(
        f"/api/challenges/{chal.id}/files/{file_id}/download",
        headers=security_users["admin"]
    )
    assert admin_res.status_code == 200
    assert admin_res.content == b"top secret challenge data"


def test_storage_path_traversal_prevention():
    """Verifies storage service sanitizes paths and prevents directory traversal."""
    # 1. Path traversal in save_file original filename
    key, size = storage_service.save_file(b"traversal test", "../../../etc/cron.d/evil")
    assert ".." not in key
    assert key.endswith("_evil")

    # 2. Path traversal in get_file_path
    file_path = storage_service.get_file_path(key)
    assert str(file_path).startswith(str(storage_service.storage_root.resolve()))

    # Cleanup
    storage_service.delete_file(key)


# ==============================================================================
# 7. SQL Injection & Authorization Tests
# ==============================================================================

def test_sql_injection_resistance_on_search(client, security_users):
    """Verifies SQL injection payloads in search/filter params are handled safely."""
    sqli_payloads = [
        "' OR '1'='1",
        "'; DROP TABLE users; --",
        "1 UNION SELECT null, username, hashed_password FROM users--"
    ]
    for payload in sqli_payloads:
        # Testing on challenges endpoint with category query
        res = client.get(f"/api/challenges?category_id={payload}")
        # UUID conversion fails gracefully with 422 Unprocessable Entity
        assert res.status_code in [422, 200]
        assert "syntax error" not in res.text.lower()


def test_privilege_escalation_blocked(client, security_users):
    """Verifies users cannot elevate their own role to moderator or admin."""
    # 1. Attempting role injection during registration
    reg_data = {
        "username": "attacker_user_sec",
        "email": "attacker_sec@college.edu",
        "password": "AttackerPass123!",
        "role": "admin"
    }
    reg_res = client.post("/api/auth/register", json=reg_data)
    assert reg_res.status_code == 201
    user_info = reg_res.json()
    # Role MUST remain STUDENT regardless of registration payload
    assert user_info["role"] == "student"

    # 2. Student attempting admin-only endpoints
    admin_res = client.get("/api/admin/security-events", headers=security_users["student_a"])
    assert admin_res.status_code == 403

    analytics_res = client.get("/api/admin/analytics/overview", headers=security_users["student_a"])
    assert analytics_res.status_code == 403

    docker_admin_res = client.get("/api/admin/challenge-instances", headers=security_users["student_a"])
    assert docker_admin_res.status_code == 403


def test_idor_protection(client, db_session, security_users):
    """Verifies users cannot read, modify, or delete another user's notifications or private data."""
    # Create notification for User A
    notif_a = NotificationService.create_notification(
        db=db_session,
        user_id=security_users["user_a"].id,
        type="system",
        title="Private Notification for User A",
        message="Confidential alert"
    )

    # User B attempts to mark User A's notification as read (forbidden)
    res_read = client.post(
        f"/api/notifications/{notif_a.id}/read",
        headers=security_users["student_b"]
    )
    assert res_read.status_code in [403, 404]

    # User B attempts to delete User A's notification (forbidden)
    res_del = client.delete(
        f"/api/notifications/{notif_a.id}",
        headers=security_users["student_b"]
    )
    assert res_del.status_code in [403, 404]

    # User A can successfully mark it as read
    res_ok = client.post(
        f"/api/notifications/{notif_a.id}/read",
        headers=security_users["student_a"]
    )
    assert res_ok.status_code == 200
    assert res_ok.json()["is_read"] is True


def test_flag_secrecy_audit(client, db_session, security_users):
    """Verifies flags and flag hashes never appear in public challenge lists or endpoints."""
    cat = ChallengeService.get_categories(db_session)[0]
    secret_flag = "CTF{flag_secrecy_audit_super_secret_string_12345}"
    chal = ChallengeService.create_challenge(
        db_session,
        ChallengeCreate(
            title="Flag Secrecy Challenge",
            description="Verify flags never leak to clients",
            category_id=cat.id,
            difficulty=ChallengeDifficulty.EASY,
            points=150,
            flag=secret_flag,
            is_active=True
        )
    )

    # 1. Challenge list
    res_list = client.get("/api/challenges")
    assert res_list.status_code == 200
    assert secret_flag not in res_list.text
    assert chal.flag_hash not in res_list.text
    for item in res_list.json():
        assert "flag" not in item
        assert "flag_hash" not in item

    # 2. Challenge detail as student
    res_detail = client.get(f"/api/challenges/{chal.id}", headers=security_users["student_a"])
    assert res_detail.status_code == 200
    assert secret_flag not in res_detail.text
    assert chal.flag_hash not in res_detail.text
    data = res_detail.json()
    assert "flag" not in data
    assert "flag_hash" not in data


def test_malformed_and_tampered_jwt_rejected(client):
    """Verifies that malformed or forged JWT tokens are strictly rejected with 401."""
    # Bogus token format
    res_bogus = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid.jwt.token"})
    assert res_bogus.status_code == 401

    # Missing bearer prefix
    res_no_prefix = client.get("/api/auth/me", headers={"Authorization": "just-a-string"})
    assert res_no_prefix.status_code == 401

    # Empty auth header
    res_empty = client.get("/api/auth/me", headers={"Authorization": ""})
    assert res_empty.status_code == 401
