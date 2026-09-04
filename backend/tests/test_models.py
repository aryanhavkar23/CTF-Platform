import uuid
from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy.exc import IntegrityError
from app.models import (
    User, UserRole, Team, team_members,
    Category, Challenge, ChallengeDifficulty, ChallengeType,
    Event, event_challenges, Submission
)


def test_create_user_with_roles(db_session):
    """Test user creation with student, moderator, and admin roles."""
    student = User(
        username="alice",
        email="alice@college.edu",
        hashed_password="secure_hashed_password_alice",
        role=UserRole.STUDENT,
        college="OWASP University"
    )
    mod = User(
        username="bob_mod",
        email="bob@college.edu",
        hashed_password="secure_hashed_password_bob",
        role=UserRole.MODERATOR
    )
    admin = User(
        username="carol_admin",
        email="carol@college.edu",
        hashed_password="secure_hashed_password_carol",
        role=UserRole.ADMIN
    )

    db_session.add_all([student, mod, admin])
    db_session.flush()

    assert student.id is not None
    assert student.role == UserRole.STUDENT
    assert student.is_active is True
    assert student.created_at is not None

    assert mod.role == UserRole.MODERATOR
    assert admin.role == UserRole.ADMIN


def test_user_unique_username(db_session):
    """Test that username must be unique."""
    u1 = User(
        username="unique_user",
        email="unique1@college.edu",
        hashed_password="hash1"
    )
    db_session.add(u1)
    db_session.flush()

    # Duplicate username
    u2 = User(
        username="unique_user",
        email="unique2@college.edu",
        hashed_password="hash2"
    )
    db_session.add(u2)
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_user_unique_email(db_session):
    """Test that email must be unique."""
    u1 = User(
        username="user_one",
        email="same_email@college.edu",
        hashed_password="hash1"
    )
    db_session.add(u1)
    db_session.flush()

    # Duplicate email
    u2 = User(
        username="user_two",
        email="same_email@college.edu",
        hashed_password="hash2"
    )
    db_session.add(u2)
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_team_and_membership(db_session):
    """Test team creation, captain relationship, and member association."""
    captain = User(
        username="captain_jack",
        email="jack@college.edu",
        hashed_password="hash_jack"
    )
    member = User(
        username="team_member_1",
        email="member1@college.edu",
        hashed_password="hash_member1"
    )
    db_session.add_all([captain, member])
    db_session.flush()

    team = Team(
        name="CyberHacks",
        captain_id=captain.id,
        invite_code="SEC123INVITE"
    )
    db_session.add(team)
    db_session.flush()

    assert team.captain.username == "captain_jack"

    # Add member to team via secondary table
    team.members.append(member)
    db_session.flush()

    assert len(team.members) == 1
    assert team.members[0].username == "team_member_1"


def test_category_and_challenge_relationships(db_session):
    """Test category creation, challenges linked to category, and difficulty enums."""
    category = Category(
        name="Web Exploitation",
        description="Challenges focused on web vulnerabilities (SQLi, XSS, SSRF)."
    )
    db_session.add(category)
    db_session.flush()

    challenge = Challenge(
        title="SQLi 101: Injection Basics",
        description="Find the flag hidden in the authentication bypass.",
        category_id=category.id,
        difficulty=ChallengeDifficulty.EASY,
        points=100,
        flag_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        is_active=True,
        challenge_type=ChallengeType.STATIC
    )
    db_session.add(challenge)
    db_session.flush()

    assert challenge.id is not None
    assert challenge.category.name == "Web Exploitation"
    assert len(category.challenges) == 1
    assert category.challenges[0].title == "SQLi 101: Injection Basics"
    assert challenge.difficulty == ChallengeDifficulty.EASY
    assert challenge.challenge_type == ChallengeType.STATIC


def test_challenge_positive_points_constraint(db_session):
    """Test that challenge points must be non-negative."""
    category = Category(name="Crypto")
    db_session.add(category)
    db_session.flush()

    invalid_challenge = Challenge(
        title="Negative Points Challenge",
        description="This should fail constraint.",
        category_id=category.id,
        difficulty=ChallengeDifficulty.HARD,
        points=-50,
        flag_hash="hash"
    )
    db_session.add(invalid_challenge)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_event_and_event_challenges(db_session):
    """Test event creation, time constraints, and challenge association."""
    now = datetime.now(timezone.utc)
    start = now + timedelta(days=1)
    end = now + timedelta(days=2)

    event = Event(
        name="Annual OWASP CTF 2026",
        description="48-hour competitive CTF.",
        start_time=start,
        end_time=end,
        is_scoreboard_frozen=False,
        is_published=True
    )
    db_session.add(event)
    db_session.flush()

    category = Category(name="Forensics")
    db_session.add(category)
    db_session.flush()

    challenge = Challenge(
        title="Packet Hunt",
        description="Analyze the PCAP file.",
        category_id=category.id,
        difficulty=ChallengeDifficulty.MEDIUM,
        points=250,
        flag_hash="pcap_flag_hash"
    )
    db_session.add(challenge)
    db_session.flush()

    # Associate challenge to event with points override
    event.challenges.append(challenge)
    db_session.flush()

    assert len(event.challenges) == 1
    assert event.challenges[0].title == "Packet Hunt"


def test_event_time_order_constraint(db_session):
    """Test that event end_time must be strictly after start_time."""
    now = datetime.now(timezone.utc)
    start = now + timedelta(days=2)
    end = now + timedelta(days=1)  # Invalid: end before start

    invalid_event = Event(
        name="Time Paradox CTF",
        start_time=start,
        end_time=end
    )
    db_session.add(invalid_event)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_submission_and_cascade_delete(db_session):
    """Test submission records, solves, and cascade behavior when challenge is deleted."""
    user = User(username="solver_dan", email="dan@college.edu", hashed_password="pw")
    category = Category(name="Reverse Engineering")
    db_session.add_all([user, category])
    db_session.flush()

    challenge = Challenge(
        title="Crackme v1",
        description="Reverse the binary.",
        category_id=category.id,
        difficulty=ChallengeDifficulty.MEDIUM,
        points=200,
        flag_hash="correct_hash"
    )
    db_session.add(challenge)
    db_session.flush()

    # Add correct submission
    submission = Submission(
        user_id=user.id,
        challenge_id=challenge.id,
        submitted_flag_hash="correct_hash",
        is_correct=True,
        points_awarded=200
    )
    db_session.add(submission)
    db_session.flush()

    assert submission.id is not None
    assert submission.user.username == "solver_dan"
    assert submission.challenge.title == "Crackme v1"
    assert submission.is_correct is True
    assert submission.points_awarded == 200

    # Delete challenge and verify submission is cascaded
    sub_id = submission.id
    db_session.delete(challenge)
    db_session.flush()

    deleted_sub = db_session.query(Submission).filter(Submission.id == sub_id).first()
    assert deleted_sub is None
