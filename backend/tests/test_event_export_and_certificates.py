from datetime import datetime, timedelta, timezone
from uuid import uuid4
import pytest

from app.models.user import User, UserRole
from app.models.event import Event, EventStatus, event_challenges
from app.models.event_registration import EventRegistration
from app.models.challenge import Challenge, ChallengeDifficulty, ChallengeType
from app.models.submission import Submission
from app.models.solve import Solve
from app.core.security import hash_password, create_access_token
from app.services.challenge_service import ChallengeService, hash_flag


@pytest.fixture
def cert_event_setup(db_session):
    """Creates users, ended event, challenges, and solve records for export and certificate testing."""
    ChallengeService.seed_categories(db_session)
    now = datetime.now(timezone.utc)

    student1 = User(
        username="winner_alice",
        email="alice@college.edu",
        name="Alice Champion",
        college="MIT Security",
        hashed_password=hash_password("Pass123!"),
        role=UserRole.STUDENT,
        is_active=True,
    )
    student2 = User(
        username="outsider_bob",
        email="bob@college.edu",
        name="Bob Unregistered",
        college="Stanford",
        hashed_password=hash_password("Pass123!"),
        role=UserRole.STUDENT,
        is_active=True,
    )
    admin = User(
        username="director_dave",
        email="dave@college.edu",
        name="Dave Admin",
        college="OWASP College",
        hashed_password=hash_password("AdminPass123!"),
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add_all([student1, student2, admin])
    db_session.flush()

    # Create ended event
    event = Event(
        name="Spring Security CTF 2026",
        slug="spring-sec-2026",
        description="Official College Championship",
        start_at=now - timedelta(hours=3),
        end_at=now - timedelta(minutes=15),
        status=EventStatus.ENDED,
        is_active=True,
        created_by=admin.id,
    )
    db_session.add(event)
    db_session.flush()

    # Register student1
    reg = EventRegistration(
        event_id=event.id,
        user_id=student1.id,
        registration_type="individual",
        is_active=True,
    )
    db_session.add(reg)
    db_session.flush()

    # Create challenge & attach to event
    cat = ChallengeService.get_categories(db_session)[0]
    chal = Challenge(
        title="Event Crypto Puzzle",
        description="Solve RSA oracle",
        category_id=cat.id,
        difficulty=ChallengeDifficulty.MEDIUM,
        points=250,
        flag_hash=hash_flag("CTF{event_crypto_flag_solved}"),
        is_active=True,
        challenge_type=ChallengeType.STATIC,
    )
    db_session.add(chal)
    db_session.flush()

    db_session.execute(
        event_challenges.insert().values(
            event_id=event.id,
            challenge_id=chal.id,
            points_override=None,
            is_active=True,
        )
    )
    db_session.flush()

    # Record solve for student1
    sub = Submission(
        user_id=student1.id,
        challenge_id=chal.id,
        event_id=event.id,
        submitted_flag_hash="dummy_hash",
        is_correct=True,
        points_awarded=250,
    )
    db_session.add(sub)
    db_session.flush()

    solve = Solve(
        user_id=student1.id,
        challenge_id=chal.id,
        event_id=event.id,
        submission_id=sub.id,
        points_awarded=250,
    )
    db_session.add(solve)
    db_session.commit()

    def make_header(user):
        token = create_access_token(
            data={"sub": str(user.id), "email": user.email, "role": user.role.value}
        )
        return {"Authorization": f"Bearer {token}"}

    return {
        "student1": student1,
        "student2": student2,
        "admin": admin,
        "event": event,
        "challenge": chal,
        "student1_headers": make_header(student1),
        "student2_headers": make_header(student2),
        "admin_headers": make_header(admin),
    }


def test_student_forbidden_from_export(client, cert_event_setup):
    """Students cannot access administrative event export."""
    event = cert_event_setup["event"]
    res = client.get(
        f"/api/events/{event.id}/export",
        headers=cert_event_setup["student1_headers"],
    )
    assert res.status_code == 403


def test_event_results_export_json(client, cert_event_setup):
    """Admin exports complete event results in JSON format."""
    event = cert_event_setup["event"]
    res = client.get(
        f"/api/events/{event.id}/export?format=json",
        headers=cert_event_setup["admin_headers"],
    )
    assert res.status_code == 200
    data = res.json()
    assert data["event_id"] == str(event.id)
    assert data["event_name"] == "Spring Security CTF 2026"
    assert "leaderboard" in data
    assert len(data["leaderboard"]) >= 1
    top_entry = data["leaderboard"][0]
    assert top_entry["participant_name"] == "winner_alice"
    assert top_entry["total_points"] == 250
    assert top_entry["rank"] == 1
    assert "challenges" in data
    assert len(data["challenges"]) >= 1
    assert data["challenges"][0]["solve_count"] == 1


def test_event_results_export_csv(client, cert_event_setup):
    """Admin exports complete event results in CSV format."""
    event = cert_event_setup["event"]
    res = client.get(
        f"/api/events/{event.id}/export?format=csv",
        headers=cert_event_setup["admin_headers"],
    )
    assert res.status_code == 200
    assert "text/csv" in res.headers.get("content-type", "")
    assert f"attachment; filename=event_results_{event.id}.csv" in res.headers.get("content-disposition", "")
    text = res.text
    assert "Rank,Participant Type,Participant Name,College,Total Points,Solved Challenges,Last Solve Time" in text
    assert "1,individual,winner_alice,MIT Security,250,1" in text


def test_participant_generate_certificate(client, cert_event_setup):
    """Registered participant can generate verifiable digital certificate with valid rank and token."""
    event = cert_event_setup["event"]
    res = client.get(
        f"/api/events/{event.id}/certificate",
        headers=cert_event_setup["student1_headers"],
    )
    assert res.status_code == 200
    cert = res.json()
    assert cert["recipient_name"] == "Alice Champion"
    assert cert["event_name"] == "Spring Security CTF 2026"
    assert cert["rank"] == 1
    assert cert["award_title"] == "1st Place Champion"
    assert cert["points"] == 250
    assert cert["solved_count"] == 1
    assert cert["is_valid"] is True
    assert "verification_token" in cert
    assert "verification_url" in cert


def test_unregistered_user_cannot_get_certificate(client, cert_event_setup):
    """Non-participants cannot request certificates."""
    event = cert_event_setup["event"]
    res = client.get(
        f"/api/events/{event.id}/certificate",
        headers=cert_event_setup["student2_headers"],
    )
    assert res.status_code == 403
    assert "not registered" in res.json()["detail"].lower()


def test_public_certificate_verification_success(client, cert_event_setup):
    """Digital certificate token is publicly verifiable without authentication."""
    event = cert_event_setup["event"]

    # First get certificate
    cert_res = client.get(
        f"/api/events/{event.id}/certificate",
        headers=cert_event_setup["student1_headers"],
    )
    assert cert_res.status_code == 200
    token = cert_res.json()["verification_token"]

    # Public verification request (zero auth headers)
    verify_res = client.get(f"/api/events/certificates/verify/{token}")
    assert verify_res.status_code == 200
    verified = verify_res.json()
    assert verified["recipient_name"] == "Alice Champion"
    assert verified["event_name"] == "Spring Security CTF 2026"
    assert verified["rank"] == 1
    assert verified["award_title"] == "1st Place Champion"
    assert verified["points"] == 250
    assert verified["is_valid"] is True


def test_tampered_certificate_verification_failure(client, cert_event_setup):
    """Tampered token with forged rank or signature fails verification."""
    event = cert_event_setup["event"]
    student1 = cert_event_setup["student1"]

    # Forged token with invalid signature
    fake_token = f"{student1.id}_{event.id}_1_9999_fake_signature_12345678901234"
    res = client.get(f"/api/events/certificates/verify/{fake_token}")
    assert res.status_code == 404
    assert "tampered" in res.json()["detail"].lower() or "failed" in res.json()["detail"].lower()

    # Malformed token format
    res_malformed = client.get("/api/events/certificates/verify/not-a-valid-token")
    assert res_malformed.status_code == 400
