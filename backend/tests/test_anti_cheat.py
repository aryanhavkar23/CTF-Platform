import json
from uuid import uuid4
from datetime import datetime, timezone, timedelta
import pytest
from fastapi import status

from app.config import settings
from app.models.user import User, UserRole
from app.models.challenge import Challenge, ChallengeDifficulty, ChallengeType
from app.models.category import Category
from app.models.submission import Submission
from app.models.solve import Solve
from app.models.event import Event, EventStatus
from app.models.event_registration import EventRegistration, RegistrationType
from app.models.security_event import (
    SecurityEvent,
    SecurityEventReview,
    SecurityEventType,
    SecurityEventSeverity,
    SecurityEventStatus,
)
from app.core.security import hash_password, create_access_token
from app.services.challenge_service import hash_flag
from app.services.anti_cheat_service import AntiCheatService


@pytest.fixture
def auth_users(db_session):
    """Creates a full suite of users for security and RBAC testing."""
    student = User(
        username="ac_student",
        email="ac_student@college.edu",
        hashed_password=hash_password("StudentPass123!"),
        role=UserRole.STUDENT
    )
    moderator = User(
        username="ac_mod",
        email="ac_mod@college.edu",
        hashed_password=hash_password("ModPass123!"),
        role=UserRole.MODERATOR
    )
    admin = User(
        username="ac_admin",
        email="ac_admin@college.edu",
        hashed_password=hash_password("AdminPass123!"),
        role=UserRole.ADMIN
    )
    db_session.add_all([student, moderator, admin])
    db_session.flush()

    def token_header(u: User):
        token = create_access_token(data={"sub": str(u.id), "email": u.email, "role": u.role.value})
        return {"Authorization": f"Bearer {token}"}

    return {
        "student": student,
        "moderator": moderator,
        "admin": admin,
        "student_header": token_header(student),
        "mod_header": token_header(moderator),
        "admin_header": token_header(admin),
    }


@pytest.fixture
def sample_challenge(db_session):
    """Creates a sample category and active challenge."""
    cat = db_session.query(Category).first()
    if not cat:
        cat = Category(name="Web Exploitation", description="Web security challenges")
        db_session.add(cat)
        db_session.flush()

    chall = Challenge(
        title="SQLi Login Bypass",
        description="Bypass the login screen using SQL injection",
        category_id=cat.id,
        difficulty=ChallengeDifficulty.EASY,
        challenge_type=ChallengeType.STATIC,
        points=100,
        flag_hash=hash_flag("flag{sqli_admin_bypass}"),
        is_active=True
    )
    db_session.add(chall)
    db_session.flush()
    return chall


def test_submission_rate_limiting_enforcement(client, db_session, auth_users, sample_challenge, monkeypatch):
    """Verifies that exceeding the submission rate limit returns 429 and logs a security event."""
    monkeypatch.setattr(settings, "SUBMISSION_COOLDOWN_SECONDS", 0)
    monkeypatch.setattr(settings, "SUBMISSION_RATE_LIMIT", 5)
    monkeypatch.setattr(settings, "SUBMISSION_RATE_WINDOW_SECONDS", 60)

    student_header = auth_users["student_header"]
    student = auth_users["student"]

    # First 4 attempts fail normally (not rate limited)
    for i in range(4):
        res = client.post(
            "/api/submissions",
            headers=student_header,
            json={"challenge_id": str(sample_challenge.id), "flag": f"flag{{wrong_{i}}}"}
        )
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data["is_correct"] is False
        assert data["message"] == "Incorrect flag."

    # 5th attempt: reaches rate limit
    res5 = client.post(
        "/api/submissions",
        headers=student_header,
        json={"challenge_id": str(sample_challenge.id), "flag": "flag{wrong_5}"}
    )
    assert res5.status_code == status.HTTP_200_OK

    # 6th attempt: exceeds limit -> HTTP 429
    res6 = client.post(
        "/api/submissions",
        headers=student_header,
        json={"challenge_id": str(sample_challenge.id), "flag": "flag{wrong_6}"}
    )
    assert res6.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    data6 = res6.json()
    assert "Too many submission attempts. Please try again later." in data6["detail"]

    # Verify a security event was recorded
    sec_event = db_session.query(SecurityEvent).filter(
        SecurityEvent.user_id == student.id,
        SecurityEvent.event_type == SecurityEventType.SUBMISSION_RATE_EXCEEDED.value
    ).first()
    assert sec_event is not None
    assert sec_event.severity == SecurityEventSeverity.LOW.value
    assert sec_event.status == SecurityEventStatus.OPEN.value


def test_failed_submission_threshold_triggers_security_event(client, db_session, auth_users, sample_challenge, monkeypatch):
    """Verifies excessive failed submissions trigger a HIGH severity security event with cooldown deduplication."""
    monkeypatch.setattr(settings, "SUBMISSION_COOLDOWN_SECONDS", 0)
    monkeypatch.setattr(settings, "SUBMISSION_RATE_LIMIT", 100)
    monkeypatch.setattr(settings, "FAILED_SUBMISSION_THRESHOLD", 5)
    monkeypatch.setattr(settings, "FAILED_SUBMISSION_WINDOW_SECONDS", 300)
    monkeypatch.setattr(settings, "SECURITY_EVENT_COOLDOWN_SECONDS", 300)

    student_header = auth_users["student_header"]
    student = auth_users["student"]

    # Submit 4 wrong flags -> below threshold, no security event
    for i in range(4):
        res = client.post(
            "/api/submissions",
            headers=student_header,
            json={"challenge_id": str(sample_challenge.id), "flag": f"flag{{fail_{i}}}"}
        )
        assert res.status_code == status.HTTP_200_OK

    events_count = db_session.query(SecurityEvent).filter(
        SecurityEvent.user_id == student.id,
        SecurityEvent.event_type == SecurityEventType.EXCESSIVE_FAILED_SUBMISSIONS.value
    ).count()
    assert events_count == 0

    # 5th wrong submission -> reaches threshold -> triggers event
    res5 = client.post(
        "/api/submissions",
        headers=student_header,
        json={"challenge_id": str(sample_challenge.id), "flag": "flag{fail_5}"}
    )
    assert res5.status_code == status.HTTP_200_OK

    event = db_session.query(SecurityEvent).filter(
        SecurityEvent.user_id == student.id,
        SecurityEvent.event_type == SecurityEventType.EXCESSIVE_FAILED_SUBMISSIONS.value
    ).first()
    assert event is not None
    assert event.severity == SecurityEventSeverity.HIGH.value

    # 6th wrong submission -> within cooldown window, should not create duplicate event
    res6 = client.post(
        "/api/submissions",
        headers=student_header,
        json={"challenge_id": str(sample_challenge.id), "flag": "flag{fail_6}"}
    )
    assert res6.status_code == status.HTTP_200_OK

    total_failed_events = db_session.query(SecurityEvent).filter(
        SecurityEvent.user_id == student.id,
        SecurityEvent.event_type == SecurityEventType.EXCESSIVE_FAILED_SUBMISSIONS.value
    ).count()
    assert total_failed_events == 1


def test_repeated_attempts_on_single_challenge(client, db_session, auth_users, sample_challenge, monkeypatch):
    """Verifies that targeting the same challenge repeatedly triggers a REPEATED_CHALLENGE_ATTEMPTS event."""
    monkeypatch.setattr(settings, "SUBMISSION_COOLDOWN_SECONDS", 0)
    monkeypatch.setattr(settings, "SUBMISSION_RATE_LIMIT", 100)
    monkeypatch.setattr(settings, "REPEATED_CHALLENGE_ATTEMPT_THRESHOLD", 4)
    monkeypatch.setattr(settings, "REPEATED_CHALLENGE_ATTEMPT_WINDOW_SECONDS", 120)

    student_header = auth_users["student_header"]
    student = auth_users["student"]

    for i in range(4):
        res = client.post(
            "/api/submissions",
            headers=student_header,
            json={"challenge_id": str(sample_challenge.id), "flag": f"flag{{try_same_{i}}}"}
        )
        assert res.status_code == status.HTTP_200_OK

    event = db_session.query(SecurityEvent).filter(
        SecurityEvent.user_id == student.id,
        SecurityEvent.challenge_id == sample_challenge.id,
        SecurityEvent.event_type == SecurityEventType.REPEATED_CHALLENGE_ATTEMPTS.value
    ).first()
    assert event is not None
    assert event.severity == SecurityEventSeverity.MEDIUM.value


def test_rapid_multi_challenge_solving_detection(client, db_session, auth_users, monkeypatch):
    """Verifies that solving multiple challenges suspiciously fast logs an incident without altering scores."""
    monkeypatch.setattr(settings, "SUBMISSION_COOLDOWN_SECONDS", 0)
    monkeypatch.setattr(settings, "SUBMISSION_RATE_LIMIT", 100)
    monkeypatch.setattr(settings, "RAPID_SOLVE_COUNT", 3)
    monkeypatch.setattr(settings, "RAPID_SOLVE_WINDOW_SECONDS", 60)

    student_header = auth_users["student_header"]
    student = auth_users["student"]

    cat = db_session.query(Category).first()
    if not cat:
        cat = Category(name="Rapid Tests", description="Rapid solve tests")
        db_session.add(cat)
        db_session.flush()

    challenges = []
    for i in range(3):
        c = Challenge(
            title=f"Rapid Challenge {i}",
            description="Testing rapid solves",
            category_id=cat.id,
            difficulty=ChallengeDifficulty.EASY,
            challenge_type=ChallengeType.STATIC,
            points=50,
            flag_hash=hash_flag(f"flag{{rapid_solve_{i}}}"),
            is_active=True
        )
        db_session.add(c)
        challenges.append(c)
    db_session.flush()

    # Solve all 3 consecutively
    for i, c in enumerate(challenges):
        res = client.post(
            "/api/submissions",
            headers=student_header,
            json={"challenge_id": str(c.id), "flag": f"flag{{rapid_solve_{i}}}"}
        )
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data["is_correct"] is True
        assert data["points_awarded"] == 50

    # Verify score is intact (3 * 50 = 150 points)
    solves = db_session.query(Solve).filter(Solve.user_id == student.id).all()
    assert len(solves) == 3
    total_score = sum(s.points_awarded for s in solves)
    assert total_score == 150

    # Verify rapid solve security event was recorded
    rapid_event = db_session.query(SecurityEvent).filter(
        SecurityEvent.user_id == student.id,
        SecurityEvent.event_type == SecurityEventType.RAPID_MULTI_CHALLENGE_SOLVING.value
    ).first()
    assert rapid_event is not None
    assert rapid_event.severity == SecurityEventSeverity.HIGH.value
    assert rapid_event.status == SecurityEventStatus.OPEN.value


def test_challenge_access_violation_detection(client, db_session, auth_users, monkeypatch):
    """Verifies that unauthorized or inactive challenge submission attempts trigger access violation events."""
    monkeypatch.setattr(settings, "SUBMISSION_COOLDOWN_SECONDS", 0)

    student_header = auth_users["student_header"]
    student = auth_users["student"]

    cat = db_session.query(Category).first()
    if not cat:
        cat = Category(name="Access Violations", description="Access violation tests")
        db_session.add(cat)
        db_session.flush()

    inactive_chall = Challenge(
        title="Secret Hidden Challenge",
        description="Not ready yet",
        category_id=cat.id,
        difficulty=ChallengeDifficulty.HARD,
        challenge_type=ChallengeType.STATIC,
        points=500,
        flag_hash=hash_flag("flag{hidden_inactive}"),
        is_active=False
    )
    db_session.add(inactive_chall)
    db_session.flush()

    res = client.post(
        "/api/submissions",
        headers=student_header,
        json={"challenge_id": str(inactive_chall.id), "flag": "flag{hidden_inactive}"}
    )
    assert res.status_code == status.HTTP_404_NOT_FOUND

    # Verify security event logged for inactive challenge attempt
    access_event = db_session.query(SecurityEvent).filter(
        SecurityEvent.user_id == student.id,
        SecurityEvent.challenge_id == inactive_chall.id,
        SecurityEvent.event_type == SecurityEventType.CHALLENGE_ACCESS_VIOLATION.value
    ).first()
    assert access_event is not None
    assert access_event.severity == SecurityEventSeverity.HIGH.value


def test_zero_flag_and_secret_leakage(client, db_session, auth_users, sample_challenge):
    """Ensures submitted flags, flag hashes, passwords, and tokens never leak into security event records."""
    sec_event = AntiCheatService.record_security_event(
        db=db_session,
        event_type=SecurityEventType.EXCESSIVE_FAILED_SUBMISSIONS,
        severity=SecurityEventSeverity.HIGH,
        description="Excessive failed submissions observed",
        user_id=auth_users["student"].id,
        challenge_id=sample_challenge.id,
        metadata={"reason": "excessive_wrong_flags"}
    )

    admin_header = auth_users["admin_header"]
    res = client.get(f"/api/admin/security-events/{sec_event.id}", headers=admin_header)
    assert res.status_code == status.HTTP_200_OK
    raw_text = res.text

    assert "flag{" not in raw_text
    assert "flag_hash" not in raw_text
    assert "hashed_password" not in raw_text
    assert "Bearer" not in raw_text


def test_admin_security_events_rbac(client, auth_users):
    """Verifies student is forbidden (403), unauthenticated is unauthorized (401), and admin/mod have access."""
    # Unauthenticated -> 401
    res_unauth = client.get("/api/admin/security-events")
    assert res_unauth.status_code == status.HTTP_401_UNAUTHORIZED

    # Student -> 403
    res_student = client.get("/api/admin/security-events", headers=auth_users["student_header"])
    assert res_student.status_code == status.HTTP_403_FORBIDDEN

    # Moderator -> 200
    res_mod = client.get("/api/admin/security-events", headers=auth_users["mod_header"])
    assert res_mod.status_code == status.HTTP_200_OK

    # Admin -> 200
    res_admin = client.get("/api/admin/security-events", headers=auth_users["admin_header"])
    assert res_admin.status_code == status.HTTP_200_OK


def test_admin_review_security_event_and_audit_trail(client, db_session, auth_users, sample_challenge):
    """Verifies that reviewing an incident records an immutable review trail and updates status."""
    sec_event = AntiCheatService.record_security_event(
        db=db_session,
        event_type=SecurityEventType.RAPID_MULTI_CHALLENGE_SOLVING,
        severity=SecurityEventSeverity.HIGH,
        description="Suspect solve burst",
        user_id=auth_users["student"].id,
        challenge_id=sample_challenge.id
    )

    mod_header = auth_users["mod_header"]

    # Review as dismissed with note
    review_res = client.post(
        f"/api/admin/security-events/{sec_event.id}/review",
        headers=mod_header,
        json={"status": "dismissed", "note": "Verified legitimate campus network activity."}
    )
    assert review_res.status_code == status.HTTP_200_OK
    data = review_res.json()
    assert data["status"] == "dismissed"
    assert len(data["reviews"]) >= 1
    assert data["reviews"][0]["previous_status"] == "open"
    assert data["reviews"][0]["new_status"] == "dismissed"
    assert data["reviews"][0]["note"] == "Verified legitimate campus network activity."
    assert data["reviews"][0]["reviewer_username"] == auth_users["moderator"].username

    # Verify audit record persisted in security_event_reviews table
    review_db = db_session.query(SecurityEventReview).filter(
        SecurityEventReview.security_event_id == sec_event.id
    ).first()
    assert review_db is not None
    assert review_db.reviewer_id == auth_users["moderator"].id
    assert review_db.new_status == "dismissed"


def test_user_security_summary_and_suspicion_score(client, db_session, auth_users, sample_challenge):
    """Verifies the aggregated user security profile and explainable suspicion scoring endpoint."""
    student = auth_users["student"]

    # Create 2 events for student
    AntiCheatService.record_security_event(
        db=db_session,
        event_type=SecurityEventType.SUBMISSION_RATE_EXCEEDED,
        severity=SecurityEventSeverity.LOW,
        description="Rate limit exceeded",
        user_id=student.id
    )
    AntiCheatService.record_security_event(
        db=db_session,
        event_type=SecurityEventType.EXCESSIVE_FAILED_SUBMISSIONS,
        severity=SecurityEventSeverity.HIGH,
        description="Excessive failed attempts",
        user_id=student.id
    )

    admin_header = auth_users["admin_header"]
    res = client.get(f"/api/admin/security/users/{student.id}", headers=admin_header)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()

    assert data["user_id"] == str(student.id)
    assert data["username"] == student.username
    assert data["total_security_events"] == 2
    assert data["open_events"] == 2
    assert data["high_critical_events"] == 1
    assert data["suspicion_score"] == 35  # 20 (rate limit) + 15 (failed submissions)
    assert data["suspicion_level"] == "Low"
    assert len(data["recent_events"]) == 2

    # Student cannot view security summary -> 403
    student_res = client.get(f"/api/admin/security/users/{student.id}", headers=auth_users["student_header"])
    assert student_res.status_code == status.HTTP_403_FORBIDDEN


def test_security_events_filtering_and_pagination(client, db_session, auth_users):
    """Verifies that security events endpoint supports pagination and filtering by severity and status."""
    admin_header = auth_users["admin_header"]
    student = auth_users["student"]

    # Create multiple security events
    AntiCheatService.record_security_event(
        db=db_session,
        event_type=SecurityEventType.SUBMISSION_RATE_EXCEEDED,
        severity=SecurityEventSeverity.LOW,
        description="Event 1",
        user_id=student.id
    )
    AntiCheatService.record_security_event(
        db=db_session,
        event_type=SecurityEventType.EXCESSIVE_FAILED_SUBMISSIONS,
        severity=SecurityEventSeverity.HIGH,
        description="Event 2",
        user_id=student.id
    )
    AntiCheatService.record_security_event(
        db=db_session,
        event_type=SecurityEventType.CHALLENGE_ACCESS_VIOLATION,
        severity=SecurityEventSeverity.CRITICAL,
        description="Event 3",
        user_id=student.id
    )

    # Filter by severity=critical
    res_crit = client.get("/api/admin/security-events?severity=critical", headers=admin_header)
    assert res_crit.status_code == status.HTTP_200_OK
    data_crit = res_crit.json()
    assert data_crit["total"] >= 1
    assert all(item["severity"] == "critical" for item in data_crit["items"])

    # Pagination test: page_size=1
    res_page = client.get("/api/admin/security-events?page=1&page_size=1", headers=admin_header)
    assert res_page.status_code == status.HTTP_200_OK
    data_page = res_page.json()
    assert len(data_page["items"]) == 1
    assert data_page["page"] == 1
    assert data_page["page_size"] == 1
    assert data_page["total_pages"] >= 3


def test_invalid_review_status_rejected(client, db_session, auth_users):
    """Verifies that reviewing an incident with an invalid status is rejected with 422."""
    sec_event = AntiCheatService.record_security_event(
        db=db_session,
        event_type=SecurityEventType.SUBMISSION_RATE_EXCEEDED,
        severity=SecurityEventSeverity.LOW,
        description="Validation test event",
        user_id=auth_users["student"].id
    )

    admin_header = auth_users["admin_header"]
    res = client.post(
        f"/api/admin/security-events/{sec_event.id}/review",
        headers=admin_header,
        json={"status": "invalid_status_value"}
    )
    assert res.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

