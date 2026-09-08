import pytest
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from app.models.user import User, UserRole
from app.models.category import Category
from app.models.challenge import Challenge, ChallengeDifficulty, ChallengeType
from app.models.team import Team, TeamMember
from app.models.event import Event, EventStatus
from app.models.badge import Badge, CriteriaType
from app.models.notification import Notification, NotificationType
from app.core.security import hash_password, create_access_token
from app.services.challenge_service import hash_flag
from app.services.notification_service import NotificationService
from app.services.submission_service import SubmissionService
from app.services.badge_service import BadgeService
from app.services.team_service import TeamService
from app.services.event_service import EventService
from app.services.discussion_service import DiscussionService
from app.schemas.event import EventRegistrationRequest
from app.schemas.discussion import DiscussionCreate, CommentCreate


@pytest.fixture
def notif_setup(db_session):
    """Sets up users, category, and challenge for notification testing."""
    alice = User(
        username="alice_notif",
        email="alice_notif@college.edu",
        hashed_password=hash_password("Pass123!"),
        role=UserRole.STUDENT,
        college="OWASP College",
        is_active=True,
    )
    bob = User(
        username="bob_notif",
        email="bob_notif@college.edu",
        hashed_password=hash_password("Pass123!"),
        role=UserRole.STUDENT,
        college="OWASP College",
        is_active=True,
    )
    admin = User(
        username="admin_notif",
        email="admin_notif@college.edu",
        hashed_password=hash_password("Pass123!"),
        role=UserRole.ADMIN,
        college="OWASP College",
        is_active=True,
    )
    db_session.add_all([alice, bob, admin])
    db_session.commit()

    token_alice = create_access_token(data={"sub": str(alice.id), "role": alice.role.value})
    token_bob = create_access_token(data={"sub": str(bob.id), "role": bob.role.value})
    token_admin = create_access_token(data={"sub": str(admin.id), "role": admin.role.value})

    cat = Category(name="Crypto", description="Cryptography challenges")
    db_session.add(cat)
    db_session.commit()

    flag_raw = "FLAG{test_notif_solve_2026}"
    chall = Challenge(
        title="Caesar Cipher 101",
        description="Decrypt the shift cipher.",
        points=100,
        difficulty=ChallengeDifficulty.EASY,
        challenge_type=ChallengeType.STATIC,
        category_id=cat.id,
        flag_hash=hash_flag(flag_raw),
        is_active=True,
    )
    db_session.add(chall)
    db_session.commit()

    return {
        "alice": alice,
        "bob": bob,
        "admin": admin,
        "token_alice": token_alice,
        "token_bob": token_bob,
        "token_admin": token_admin,
        "category": cat,
        "challenge": chall,
        "flag_raw": flag_raw,
    }


# =============================================================================
# 1. Service Layer Tests: Creation, Deduplication, Pagination
# =============================================================================

def test_create_and_deduplicate_notification(db_session, notif_setup):
    alice = notif_setup["alice"]

    n1 = NotificationService.create_notification(
        db=db_session,
        user_id=alice.id,
        type=NotificationType.CHALLENGE_SOLVED.value,
        title="Solved Challenge",
        message="Good job solving the challenge.",
        data={"challenge_id": str(uuid4())},
        event_key="unique_event_key_1",
    )
    assert n1 is not None
    assert n1.title == "Solved Challenge"
    assert n1.is_read is False

    # Second call with the same event_key returns existing notification without creating duplicate
    n2 = NotificationService.create_notification(
        db=db_session,
        user_id=alice.id,
        type=NotificationType.CHALLENGE_SOLVED.value,
        title="Solved Challenge Duplicate",
        message="Duplicate message",
        event_key="unique_event_key_1",
    )
    assert n2 is not None
    assert n2.id == n1.id

    all_notifs = db_session.query(Notification).filter(Notification.user_id == alice.id).all()
    assert len(all_notifs) == 1


def test_get_user_notifications_pagination_and_unread_filter(db_session, notif_setup):
    alice = notif_setup["alice"]

    # Create 3 notifications
    for i in range(3):
        NotificationService.create_notification(
            db=db_session,
            user_id=alice.id,
            type=NotificationType.BADGE_AWARDED.value,
            title=f"Badge {i}",
            message=f"You earned badge {i}",
        )

    # Fetch page 1 with limit 2
    items, total, unread = NotificationService.get_user_notifications(
        db=db_session,
        user_id=alice.id,
        page=1,
        limit=2,
    )
    assert total == 3
    assert unread == 3
    assert len(items) == 2

    # Mark one read
    NotificationService.mark_notification_as_read(
        db=db_session,
        notification_id=items[0].id,
        user_id=alice.id,
    )

    # Filter unread_only
    unread_items, total_unread, unread_count = NotificationService.get_user_notifications(
        db=db_session,
        user_id=alice.id,
        page=1,
        limit=10,
        unread_only=True,
    )
    assert total_unread == 2
    assert unread_count == 2
    assert len(unread_items) == 2


# =============================================================================
# 2. API Tests: Endpoints, Read Status, Deletion
# =============================================================================

def test_api_get_notifications_and_unread_count(client, db_session, notif_setup):
    alice = notif_setup["alice"]
    token = notif_setup["token_alice"]

    NotificationService.create_notification(
        db=db_session,
        user_id=alice.id,
        type=NotificationType.EVENT_REGISTERED.value,
        title="Registered for CTF",
        message="Welcome to the event!",
    )

    # Unread count endpoint
    resp = client.get("/api/notifications/unread-count", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["unread_count"] == 1

    # List endpoint
    resp = client.get("/api/notifications?page=1&limit=10", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["unread_count"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["title"] == "Registered for CTF"


def test_api_mark_as_read_and_read_all(client, db_session, notif_setup):
    alice = notif_setup["alice"]
    token = notif_setup["token_alice"]

    n1 = NotificationService.create_notification(
        db=db_session,
        user_id=alice.id,
        type=NotificationType.CHALLENGE_SOLVED.value,
        title="Solve 1",
        message="Message 1",
    )
    n2 = NotificationService.create_notification(
        db=db_session,
        user_id=alice.id,
        type=NotificationType.CHALLENGE_SOLVED.value,
        title="Solve 2",
        message="Message 2",
    )

    # Mark single as read
    resp = client.post(f"/api/notifications/{n1.id}/read", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_read"] is True
    assert data["read_at"] is not None

    # Check unread count is now 1
    count_resp = client.get("/api/notifications/unread-count", headers={"Authorization": f"Bearer {token}"})
    assert count_resp.json()["unread_count"] == 1

    # Mark all read
    all_resp = client.post("/api/notifications/read-all", headers={"Authorization": f"Bearer {token}"})
    assert all_resp.status_code == 200
    assert all_resp.json()["marked_count"] == 1

    # Verify unread count is 0
    count_resp2 = client.get("/api/notifications/unread-count", headers={"Authorization": f"Bearer {token}"})
    assert count_resp2.json()["unread_count"] == 0


def test_api_delete_notification(client, db_session, notif_setup):
    alice = notif_setup["alice"]
    token = notif_setup["token_alice"]

    n = NotificationService.create_notification(
        db=db_session,
        user_id=alice.id,
        type=NotificationType.BADGE_AWARDED.value,
        title="Badge Awarded",
        message="You won a badge",
    )

    del_resp = client.delete(f"/api/notifications/{n.id}", headers={"Authorization": f"Bearer {token}"})
    assert del_resp.status_code == 200

    # Verify deleted
    deleted_row = db_session.query(Notification).filter(Notification.id == n.id).first()
    assert deleted_row is None


# =============================================================================
# 3. Security & Anti-IDOR Tests
# =============================================================================

def test_unauthenticated_requests_fail(client, db_session, notif_setup):
    resp = client.get("/api/notifications")
    assert resp.status_code == 401

    resp_count = client.get("/api/notifications/unread-count")
    assert resp_count.status_code == 401

    resp_read = client.post(f"/api/notifications/{uuid4()}/read")
    assert resp_read.status_code == 401


def test_anti_idor_isolation_between_users(client, db_session, notif_setup):
    alice = notif_setup["alice"]
    bob = notif_setup["bob"]
    token_bob = notif_setup["token_bob"]

    # Create notification strictly for Alice
    alice_notif = NotificationService.create_notification(
        db=db_session,
        user_id=alice.id,
        type=NotificationType.BADGE_AWARDED.value,
        title="Alice's Secret Badge",
        message="Only Alice can see this.",
    )

    # Bob tries to list his notifications -> Alice's notification not included
    bob_list = client.get("/api/notifications", headers={"Authorization": f"Bearer {token_bob}"})
    assert bob_list.status_code == 200
    assert bob_list.json()["total"] == 0

    # Bob tries to mark Alice's notification as read -> 403 Forbidden
    idor_read = client.post(
        f"/api/notifications/{alice_notif.id}/read",
        headers={"Authorization": f"Bearer {token_bob}"},
    )
    assert idor_read.status_code == 403

    # Bob tries to delete Alice's notification -> 403 Forbidden
    idor_del = client.delete(
        f"/api/notifications/{alice_notif.id}",
        headers={"Authorization": f"Bearer {token_bob}"},
    )
    assert idor_del.status_code == 403

    # Ensure Alice's notification is untouched and unread
    refreshed = db_session.query(Notification).filter(Notification.id == alice_notif.id).first()
    assert refreshed is not None
    assert refreshed.is_read is False


# =============================================================================
# 4. Integration Triggers: Solve, Badge, Team, Event, Discussion
# =============================================================================

def test_challenge_solve_triggers_notification(db_session, notif_setup):
    alice = notif_setup["alice"]
    chall = notif_setup["challenge"]
    flag_raw = notif_setup["flag_raw"]

    res = SubmissionService.process_submission(
        db=db_session,
        user=alice,
        challenge_id=chall.id,
        submitted_flag=flag_raw,
    )
    assert res["is_correct"] is True

    # Verify notification created
    notifs = db_session.query(Notification).filter(Notification.user_id == alice.id).all()
    assert len(notifs) >= 1
    solve_notif = next(n for n in notifs if n.type == NotificationType.CHALLENGE_SOLVED.value)
    assert solve_notif.title == "Challenge Solved"
    assert chall.title in solve_notif.message
    assert str(chall.points) in solve_notif.message
    assert solve_notif.data["challenge_id"] == str(chall.id)
    assert solve_notif.data["points_awarded"] == chall.points


def test_badge_awarded_triggers_notification(db_session, notif_setup):
    alice = notif_setup["alice"]

    # Create badge for first solve
    badge = Badge(
        name="Pioneer Solver",
        slug="pioneer-solver",
        description="Awarded for submitting your first valid flag.",
        icon="trophy",
        criteria_type=CriteriaType.FIRST_SOLVE.value,
        criteria_value=1,
        is_active=True,
    )
    db_session.add(badge)
    db_session.commit()

    # Solve challenge to trigger badge evaluation
    chall = notif_setup["challenge"]
    flag_raw = notif_setup["flag_raw"]
    SubmissionService.process_submission(
        db=db_session,
        user=alice,
        challenge_id=chall.id,
        submitted_flag=flag_raw,
    )

    notifs = db_session.query(Notification).filter(Notification.user_id == alice.id).all()
    badge_notif = next((n for n in notifs if n.type == NotificationType.BADGE_AWARDED.value), None)
    assert badge_notif is not None
    assert badge_notif.title == "New Badge Unlocked"
    assert "Pioneer Solver" in badge_notif.message


def test_team_member_added_and_removed_trigger_notifications(db_session, notif_setup):
    alice = notif_setup["alice"]
    bob = notif_setup["bob"]

    # Alice creates a team
    from app.schemas.team import TeamCreate
    team_resp = TeamService.create_team(
        db=db_session,
        current_user=alice,
        data=TeamCreate(name="Cyber Squad", description="Elite squad"),
    )
    team_id = team_resp.id

    # Alice adds Bob to the team
    TeamService.add_team_member(
        db=db_session,
        current_user=alice,
        team_id=team_id,
        target_user_id=bob.id,
    )

    # Bob should have received a team_member_added notification
    bob_notifs = db_session.query(Notification).filter(Notification.user_id == bob.id).all()
    add_notif = next((n for n in bob_notifs if n.type == NotificationType.TEAM_MEMBER_ADDED.value), None)
    assert add_notif is not None
    assert "Cyber Squad" in add_notif.message
    assert alice.username in add_notif.message

    # Alice removes Bob from the team
    TeamService.remove_team_member(
        db=db_session,
        current_user=alice,
        team_id=team_id,
        target_user_id=bob.id,
    )

    # Bob should have received a team_member_removed notification
    db_session.expire_all()
    bob_notifs2 = db_session.query(Notification).filter(Notification.user_id == bob.id).all()
    rem_notif = next((n for n in bob_notifs2 if n.type == NotificationType.TEAM_MEMBER_REMOVED.value), None)
    assert rem_notif is not None
    assert "Cyber Squad" in rem_notif.message


def test_event_registration_triggers_notification(db_session, notif_setup):
    alice = notif_setup["alice"]
    admin = notif_setup["admin"]

    now = datetime.now(timezone.utc)
    event = Event(
        name="Autumn Cyber Clash",
        slug="autumn-cyber-clash",
        description="Annual autumn CTF",
        start_at=now + timedelta(days=2),
        end_at=now + timedelta(days=3),
        registration_start_at=now - timedelta(days=1),
        registration_end_at=now + timedelta(days=1),
        is_active=True,
        created_by=admin.id,
    )
    db_session.add(event)
    db_session.commit()

    # Alice registers individually
    EventService.register_for_event(
        db=db_session,
        event_id=event.id,
        user=alice,
        request=EventRegistrationRequest(registration_type="individual"),
    )

    notifs = db_session.query(Notification).filter(Notification.user_id == alice.id).all()
    ev_notif = next((n for n in notifs if n.type == NotificationType.EVENT_REGISTERED.value), None)
    assert ev_notif is not None
    assert "Autumn Cyber Clash" in ev_notif.message


def test_discussion_reply_triggers_notification(db_session, notif_setup):
    alice = notif_setup["alice"]
    bob = notif_setup["bob"]
    chall = notif_setup["challenge"]

    # Alice creates a discussion thread
    disc = DiscussionService.create_discussion(
        db=db_session,
        challenge_id=chall.id,
        user=alice,
        data=DiscussionCreate(
            title="Hint on Caesar Cipher step 2",
            content="Can someone confirm if the shift is ROT13?",
        ),
    )
    disc_id = disc["id"]

    # Bob replies to Alice's discussion
    bob_comment = DiscussionService.create_comment(
        db=db_session,
        discussion_id=disc_id,
        user=bob,
        data=CommentCreate(
            content="Check the ASCII table, it's not ROT13 but ROT3.",
        ),
    )

    # Alice should receive a notification about Bob's reply
    alice_notifs = db_session.query(Notification).filter(Notification.user_id == alice.id).all()
    reply_notif = next((n for n in alice_notifs if n.type == NotificationType.DISCUSSION_REPLY.value), None)
    assert reply_notif is not None
    assert bob.username in reply_notif.message
    assert "Hint on Caesar Cipher step 2" in reply_notif.message

    # Bob should NOT receive a notification for his own reply
    bob_notifs = db_session.query(Notification).filter(Notification.user_id == bob.id).all()
    assert len(bob_notifs) == 0
