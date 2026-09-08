from uuid import uuid4
from datetime import datetime, timezone, timedelta
import pytest
from app.models.user import User, UserRole
from app.models.category import Category
from app.models.challenge import Challenge, ChallengeDifficulty, ChallengeType
from app.models.event import Event, EventStatus, event_challenges
from app.models.event_registration import EventRegistration, RegistrationType
from app.core.security import hash_password, create_access_token
from app.services.challenge_service import hash_flag


@pytest.fixture
def discussion_setup(db_session):
    """Sets up students, moderator, admin, category, and challenges for discussion testing."""
    # 1. Users
    student_a = User(
        username="alice_student",
        email="alice@college.edu",
        hashed_password=hash_password("Pass123!"),
        role=UserRole.STUDENT,
        college="OWASP College"
    )
    student_b = User(
        username="bob_student",
        email="bob@college.edu",
        hashed_password=hash_password("Pass123!"),
        role=UserRole.STUDENT,
        college="OWASP College"
    )
    moderator = User(
        username="eve_moderator",
        email="eve@college.edu",
        hashed_password=hash_password("Pass123!"),
        role=UserRole.MODERATOR,
        college="OWASP College"
    )
    admin = User(
        username="charlie_admin",
        email="charlie@college.edu",
        hashed_password=hash_password("Pass123!"),
        role=UserRole.ADMIN,
        college="OWASP College"
    )
    db_session.add_all([student_a, student_b, moderator, admin])
    db_session.commit()

    token_a = create_access_token(data={"sub": str(student_a.id), "role": student_a.role.value})
    token_b = create_access_token(data={"sub": str(student_b.id), "role": student_b.role.value})
    token_mod = create_access_token(data={"sub": str(moderator.id), "role": moderator.role.value})
    token_admin = create_access_token(data={"sub": str(admin.id), "role": admin.role.value})

    # 2. Category
    cat = Category(name="Web Exploitation", description="Web security challenges")
    db_session.add(cat)
    db_session.commit()

    # 3. Active Challenge
    chall = Challenge(
        title="SQLi Login Bypass",
        description="Bypass authentication via SQL injection",
        category_id=cat.id,
        difficulty=ChallengeDifficulty.EASY,
        points=100,
        flag_hash=hash_flag("flag{admin_login_bypassed_2026}"),
        is_active=True,
        challenge_type=ChallengeType.STATIC
    )
    # 4. Inactive Challenge
    inactive_chall = Challenge(
        title="Unpublished Heap Exploitation",
        description="Draft challenge under review",
        category_id=cat.id,
        difficulty=ChallengeDifficulty.INSANE,
        points=500,
        flag_hash=hash_flag("flag{draft_super_secret_flag}"),
        is_active=False,
        challenge_type=ChallengeType.STATIC
    )
    db_session.add_all([chall, inactive_chall])
    db_session.commit()

    return {
        "student_a": student_a,
        "student_b": student_b,
        "moderator": moderator,
        "admin": admin,
        "headers_a": {"Authorization": f"Bearer {token_a}"},
        "headers_b": {"Authorization": f"Bearer {token_b}"},
        "headers_mod": {"Authorization": f"Bearer {token_mod}"},
        "headers_admin": {"Authorization": f"Bearer {token_admin}"},
        "category": cat,
        "challenge": chall,
        "inactive_challenge": inactive_chall,
    }


# =============================================================================
# Discussion CRUD Tests
# =============================================================================

def test_authenticated_user_can_create_discussion(client, discussion_setup):
    setup = discussion_setup
    payload = {
        "title": "How to approach SQL injection filter bypass?",
        "content": "I noticed the query replaces single quotes. Any general hints?",
        "contains_spoiler": False
    }
    res = client.post(
        f"/api/challenges/{setup['challenge'].id}/discussions",
        json=payload,
        headers=setup["headers_a"]
    )
    assert res.status_code == 201
    data = res.json()
    assert data["title"] == payload["title"]
    assert data["content"] == payload["content"]
    assert data["is_pinned"] is False
    assert data["is_locked"] is False
    assert data["is_deleted"] is False
    assert data["contains_spoiler"] is False
    assert data["user"]["username"] == "alice_student"
    assert data["comments_count"] == 0


def test_unauthenticated_user_cannot_create_discussion(client, discussion_setup):
    setup = discussion_setup
    payload = {
        "title": "Unauthenticated title",
        "content": "Unauthenticated content"
    }
    res = client.post(
        f"/api/challenges/{setup['challenge'].id}/discussions",
        json=payload
    )
    assert res.status_code == 401


def test_invalid_or_inactive_challenge_rejected(client, discussion_setup):
    setup = discussion_setup
    payload = {"title": "Discussion Title", "content": "Discussion Content"}

    # Random UUID
    res_fake = client.post(f"/api/challenges/{uuid4()}/discussions", json=payload, headers=setup["headers_a"])
    assert res_fake.status_code == 404

    # Inactive challenge by normal student
    res_inactive = client.post(f"/api/challenges/{setup['inactive_challenge'].id}/discussions", json=payload, headers=setup["headers_a"])
    assert res_inactive.status_code == 404

    # Inactive challenge by admin should succeed
    res_admin = client.post(f"/api/challenges/{setup['inactive_challenge'].id}/discussions", json=payload, headers=setup["headers_admin"])
    assert res_admin.status_code == 201


def test_user_can_edit_own_discussion(client, discussion_setup):
    setup = discussion_setup
    res = client.post(
        f"/api/challenges/{setup['challenge'].id}/discussions",
        json={"title": "Original Title", "content": "Original Content", "contains_spoiler": False},
        headers=setup["headers_a"]
    )
    disc_id = res.json()["id"]

    update_payload = {
        "title": "Updated Title Here",
        "content": "Updated Content Here with more clarity",
        "contains_spoiler": True
    }
    res_put = client.put(f"/api/discussions/{disc_id}", json=update_payload, headers=setup["headers_a"])
    assert res_put.status_code == 200
    data = res_put.json()
    assert data["title"] == "Updated Title Here"
    assert data["content"] == "Updated Content Here with more clarity"
    assert data["contains_spoiler"] is True


def test_user_cannot_edit_another_users_discussion(client, discussion_setup):
    setup = discussion_setup
    res = client.post(
        f"/api/challenges/{setup['challenge'].id}/discussions",
        json={"title": "Alice's Thread", "content": "Alice's discussion text"},
        headers=setup["headers_a"]
    )
    disc_id = res.json()["id"]

    # Bob tries to edit Alice's thread
    res_hack = client.put(f"/api/discussions/{disc_id}", json={"title": "Tampered Title"}, headers=setup["headers_b"])
    assert res_hack.status_code == 403


def test_user_can_delete_own_discussion_soft_delete(client, discussion_setup):
    setup = discussion_setup
    res = client.post(
        f"/api/challenges/{setup['challenge'].id}/discussions",
        json={"title": "Discussion to be deleted", "content": "Sensitive or outdated text"},
        headers=setup["headers_a"]
    )
    disc_id = res.json()["id"]

    # Alice deletes her own discussion
    res_del = client.delete(f"/api/discussions/{disc_id}", headers=setup["headers_a"])
    assert res_del.status_code == 200
    assert res_del.json()["is_deleted"] is True

    # When Bob fetches the deleted discussion, content is masked
    res_get_bob = client.get(f"/api/discussions/{disc_id}", headers=setup["headers_b"])
    assert res_get_bob.status_code == 200
    assert res_get_bob.json()["is_deleted"] is True
    assert "[deleted]" in res_get_bob.json()["title"].lower()
    assert "[this discussion has been deleted" in res_get_bob.json()["content"].lower()

    # When moderator fetches it, original content is preserved for auditing
    res_get_mod = client.get(f"/api/discussions/{disc_id}", headers=setup["headers_mod"])
    assert res_get_mod.status_code == 200
    assert res_get_mod.json()["title"] == "Discussion to be deleted"
    assert res_get_mod.json()["content"] == "Sensitive or outdated text"


def test_user_cannot_delete_another_users_discussion(client, discussion_setup):
    setup = discussion_setup
    res = client.post(
        f"/api/challenges/{setup['challenge'].id}/discussions",
        json={"title": "Alice Thread", "content": "Alice content"},
        headers=setup["headers_a"]
    )
    disc_id = res.json()["id"]

    res_del = client.delete(f"/api/discussions/{disc_id}", headers=setup["headers_b"])
    assert res_del.status_code == 403


def test_moderator_or_admin_can_moderate_any_discussion(client, discussion_setup):
    setup = discussion_setup
    res = client.post(
        f"/api/challenges/{setup['challenge'].id}/discussions",
        json={"title": "Offensive Student Post", "content": "Needs moderation"},
        headers=setup["headers_a"]
    )
    disc_id = res.json()["id"]

    # Moderator edits title
    res_mod_edit = client.put(
        f"/api/discussions/{disc_id}",
        json={"title": "[Moderated] Clean Title"},
        headers=setup["headers_mod"]
    )
    assert res_mod_edit.status_code == 200
    assert res_mod_edit.json()["title"] == "[Moderated] Clean Title"

    # Admin deletes post
    res_admin_del = client.delete(f"/api/discussions/{disc_id}", headers=setup["headers_admin"])
    assert res_admin_del.status_code == 200
    assert res_admin_del.json()["is_deleted"] is True


# =============================================================================
# Comments & Replies Tests
# =============================================================================

def test_authenticated_user_can_comment_and_reply(client, discussion_setup):
    setup = discussion_setup
    # 1. Create discussion
    res_disc = client.post(
        f"/api/challenges/{setup['challenge'].id}/discussions",
        json={"title": "Discussion for comments", "content": "Let's talk about SQL injection payload encoding."},
        headers=setup["headers_a"]
    )
    disc_id = res_disc.json()["id"]

    # 2. Bob posts top-level comment
    res_c1 = client.post(
        f"/api/discussions/{disc_id}/comments",
        json={"content": "Try URL-encoding spaces as %20 or using inline comments /**/", "contains_spoiler": False},
        headers=setup["headers_b"]
    )
    assert res_c1.status_code == 201
    c1_id = res_c1.json()["id"]
    assert res_c1.json()["parent_comment_id"] is None
    assert res_c1.json()["user"]["username"] == "bob_student"

    # 3. Alice replies to Bob's comment
    res_reply = client.post(
        f"/api/discussions/{disc_id}/comments",
        json={"content": "Thanks! The /**/ inline comment technique worked nicely.", "parent_comment_id": c1_id},
        headers=setup["headers_a"]
    )
    assert res_reply.status_code == 201
    assert res_reply.json()["parent_comment_id"] == c1_id
    assert res_reply.json()["user"]["username"] == "alice_student"

    # 4. List comments
    res_list = client.get(f"/api/discussions/{disc_id}/comments", headers=setup["headers_a"])
    assert res_list.status_code == 200
    comments = res_list.json()["items"]
    assert len(comments) == 2


def test_user_can_edit_and_delete_own_comment(client, discussion_setup):
    setup = discussion_setup
    res_disc = client.post(
        f"/api/challenges/{setup['challenge'].id}/discussions",
        json={"title": "Comment edit test", "content": "Base discussion"},
        headers=setup["headers_a"]
    )
    disc_id = res_disc.json()["id"]

    res_c = client.post(
        f"/api/discussions/{disc_id}/comments",
        json={"content": "Initial comment typo"},
        headers=setup["headers_b"]
    )
    c_id = res_c.json()["id"]

    # Bob edits own comment
    res_edit = client.put(f"/api/comments/{c_id}", json={"content": "Fixed comment without typo"}, headers=setup["headers_b"])
    assert res_edit.status_code == 200
    assert res_edit.json()["content"] == "Fixed comment without typo"

    # Alice cannot edit Bob's comment
    res_hack = client.put(f"/api/comments/{c_id}", json={"content": "Hacked comment"}, headers=setup["headers_a"])
    assert res_hack.status_code == 403

    # Alice cannot delete Bob's comment
    res_hack_del = client.delete(f"/api/comments/{c_id}", headers=setup["headers_a"])
    assert res_hack_del.status_code == 403

    # Bob deletes own comment (soft delete)
    res_del = client.delete(f"/api/comments/{c_id}", headers=setup["headers_b"])
    assert res_del.status_code == 200
    assert res_del.json()["is_deleted"] is True

    # List shows masked content for students
    res_list = client.get(f"/api/discussions/{disc_id}/comments", headers=setup["headers_a"])
    assert res_list.json()["items"][0]["is_deleted"] is True
    assert "[this comment has been deleted]" in res_list.json()["items"][0]["content"].lower()


def test_parent_comment_from_another_discussion_rejected_idor(client, discussion_setup):
    setup = discussion_setup
    # Discussion 1
    d1 = client.post(
        f"/api/challenges/{setup['challenge'].id}/discussions",
        json={"title": "Discussion One", "content": "Content One"},
        headers=setup["headers_a"]
    ).json()

    # Discussion 2
    d2 = client.post(
        f"/api/challenges/{setup['challenge'].id}/discussions",
        json={"title": "Discussion Two", "content": "Content Two"},
        headers=setup["headers_b"]
    ).json()

    # Comment in Discussion 1
    c1 = client.post(
        f"/api/discussions/{d1['id']}/comments",
        json={"content": "Comment in discussion 1"},
        headers=setup["headers_a"]
    ).json()

    # Try to reply in Discussion 2 using parent_comment_id from Discussion 1 (IDOR attack)
    res_idor = client.post(
        f"/api/discussions/{d2['id']}/comments",
        json={"content": "Malicious cross-discussion reply", "parent_comment_id": c1["id"]},
        headers=setup["headers_b"]
    )
    assert res_idor.status_code == 400
    assert "different discussion" in res_idor.json()["detail"].lower() or "not belong" in res_idor.json()["detail"].lower()


def test_reply_to_deleted_parent_comment_rejected(client, discussion_setup):
    setup = discussion_setup
    d = client.post(
        f"/api/challenges/{setup['challenge'].id}/discussions",
        json={"title": "Deleted parent test", "content": "Base content"},
        headers=setup["headers_a"]
    ).json()

    c = client.post(
        f"/api/discussions/{d['id']}/comments",
        json={"content": "Comment to be deleted"},
        headers=setup["headers_b"]
    ).json()

    # Delete comment
    client.delete(f"/api/comments/{c['id']}", headers=setup["headers_b"])

    # Attempt to reply to deleted comment
    res_reply = client.post(
        f"/api/discussions/{d['id']}/comments",
        json={"content": "Replying to deleted", "parent_comment_id": c["id"]},
        headers=setup["headers_a"]
    )
    assert res_reply.status_code == 400
    assert "cannot reply to a deleted comment" in res_reply.json()["detail"].lower()


# =============================================================================
# Locking Tests
# =============================================================================

def test_locking_and_unlocking_behavior(client, discussion_setup):
    setup = discussion_setup
    d = client.post(
        f"/api/challenges/{setup['challenge'].id}/discussions",
        json={"title": "Locking Discussion Test", "content": "Test discussion to be locked."},
        headers=setup["headers_a"]
    ).json()
    disc_id = d["id"]

    # Normal student cannot lock
    res_hack_lock = client.post(f"/api/discussions/{disc_id}/lock", headers=setup["headers_a"])
    assert res_hack_lock.status_code == 403

    # Moderator locks discussion
    res_lock = client.post(f"/api/discussions/{disc_id}/lock", headers=setup["headers_mod"])
    assert res_lock.status_code == 200
    assert res_lock.json()["is_locked"] is True

    # Student cannot comment while locked
    res_comment = client.post(
        f"/api/discussions/{disc_id}/comments",
        json={"content": "Attempting comment during lock"},
        headers=setup["headers_b"]
    )
    assert res_comment.status_code == 400
    assert "locked" in res_comment.json()["detail"].lower()

    # Existing discussion still readable
    res_read = client.get(f"/api/discussions/{disc_id}", headers=setup["headers_b"])
    assert res_read.status_code == 200
    assert res_read.json()["is_locked"] is True

    # Moderator unlocks discussion
    res_unlock = client.post(f"/api/discussions/{disc_id}/unlock", headers=setup["headers_mod"])
    assert res_unlock.status_code == 200
    assert res_unlock.json()["is_locked"] is False

    # Student can comment again
    res_comment_after = client.post(
        f"/api/discussions/{disc_id}/comments",
        json={"content": "Commenting restored successfully!"},
        headers=setup["headers_b"]
    )
    assert res_comment_after.status_code == 201


# =============================================================================
# Pinning Tests
# =============================================================================

def test_pinning_and_unpinning_prioritization(client, discussion_setup):
    setup = discussion_setup
    chall_id = setup["challenge"].id

    # Create Discussion 1
    d1 = client.post(
        f"/api/challenges/{chall_id}/discussions",
        json={"title": "First Discussion", "content": "Regular discussion content 1"},
        headers=setup["headers_a"]
    ).json()

    # Create Discussion 2
    d2 = client.post(
        f"/api/challenges/{chall_id}/discussions",
        json={"title": "Official Rules & Discussion Guidelines", "content": "Must-read pinned guidelines"},
        headers=setup["headers_b"]
    ).json()

    # Student cannot pin
    res_hack_pin = client.post(f"/api/discussions/{d2['id']}/pin", headers=setup["headers_a"])
    assert res_hack_pin.status_code == 403

    # Admin pins Discussion 2
    res_pin = client.post(f"/api/discussions/{d2['id']}/pin", headers=setup["headers_admin"])
    assert res_pin.status_code == 200
    assert res_pin.json()["is_pinned"] is True

    # List discussions - pinned Discussion 2 must appear first
    res_list = client.get(f"/api/challenges/{chall_id}/discussions", headers=setup["headers_a"])
    assert res_list.status_code == 200
    items = res_list.json()["items"]
    assert len(items) >= 2
    assert items[0]["id"] == d2["id"]
    assert items[0]["is_pinned"] is True

    # Moderator unpins Discussion 2
    res_unpin = client.post(f"/api/discussions/{d2['id']}/unpin", headers=setup["headers_mod"])
    assert res_unpin.status_code == 200
    assert res_unpin.json()["is_pinned"] is False


# =============================================================================
# Spoiler, Content Security & Flag Confidentiality Tests
# =============================================================================

def test_spoilers_metadata_and_security(client, discussion_setup):
    setup = discussion_setup
    payload = {
        "title": "Major hint for bypass payload",
        "content": "Use boolean-based blind SQLi: ' or 1=1--",
        "contains_spoiler": True
    }
    res = client.post(
        f"/api/challenges/{setup['challenge'].id}/discussions",
        json=payload,
        headers=setup["headers_a"]
    )
    assert res.status_code == 201
    assert res.json()["contains_spoiler"] is True


def test_stored_xss_sanitization(client, discussion_setup):
    setup = discussion_setup
    payload = {
        "title": "Title with <script>alert(1)</script>",
        "content": "Malicious payload <script>window.location='http://evil.com'</script> and <img src=x onerror=alert('xss')>",
        "contains_spoiler": False
    }
    res = client.post(
        f"/api/challenges/{setup['challenge'].id}/discussions",
        json=payload,
        headers=setup["headers_a"]
    )
    assert res.status_code == 201
    data = res.json()
    # Ensure script tags are neutralized
    assert "<script>" not in data["title"].lower()
    assert "<script>" not in data["content"].lower()
    assert "onerror=" not in data["content"].lower()


def test_exact_flag_leakage_prevented(client, discussion_setup):
    setup = discussion_setup
    # The active challenge flag is: flag{admin_login_bypassed_2026}
    payload = {
        "title": "Here is the flag guys",
        "content": "The flag is flag{admin_login_bypassed_2026} just copy it!"
    }
    res = client.post(
        f"/api/challenges/{setup['challenge'].id}/discussions",
        json=payload,
        headers=setup["headers_a"]
    )
    assert res.status_code == 400
    assert "prohibited" in res.json()["detail"].lower()


def test_event_restricted_challenge_discussion_access(client, discussion_setup, db_session):
    setup = discussion_setup
    now = datetime.now(timezone.utc)

    # 1. Create a LIVE event
    event = Event(
        name="Spring CTF Live 2026",
        slug="spring-ctf-live-2026",
        start_at=now - timedelta(hours=1),
        end_at=now + timedelta(hours=3),
        status=EventStatus.LIVE,
        is_active=True,
    )
    db_session.add(event)
    db_session.commit()

    # 2. Link active challenge to the event
    db_session.execute(
        event_challenges.insert().values(
            event_id=event.id,
            challenge_id=setup["challenge"].id,
            is_active=True,
            display_order=1,
            added_at=now,
        )
    )
    db_session.commit()

    # 3. Student A is NOT registered for the event: should be rejected
    res_unregistered = client.post(
        f"/api/challenges/{setup['challenge'].id}/discussions",
        json={"title": "Event discussion attempt", "content": "Can I post here?"},
        headers=setup["headers_a"]
    )
    assert res_unregistered.status_code == 403
    assert "registered" in res_unregistered.json()["detail"].lower()

    # 4. Register Student A for the event
    reg = EventRegistration(
        event_id=event.id,
        user_id=setup["student_a"].id,
        registration_type=RegistrationType.INDIVIDUAL,
        registered_at=now,
    )
    db_session.add(reg)
    db_session.commit()

    # 5. Now Student A can participate
    res_registered = client.post(
        f"/api/challenges/{setup['challenge'].id}/discussions",
        json={"title": "Registered discussion post", "content": "Now I am registered and can discuss!"},
        headers=setup["headers_a"]
    )
    assert res_registered.status_code == 201
