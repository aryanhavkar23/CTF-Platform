import pytest
from datetime import datetime, timezone
from app.models.user import User, UserRole
from app.models.category import Category
from app.models.challenge import Challenge, ChallengeDifficulty
from app.core.security import create_access_token


@pytest.fixture
def social_test_setup(db_session):
    """Sets up two test users and a challenge for testing community writeups and follows."""
    user_a = User(
        username="operative_alice",
        email="alice_social@test.edu",
        role=UserRole.STUDENT,
        name="Alice Operative",
        college="MIT",
        is_active=True,
    )
    user_b = User(
        username="operative_bob",
        email="bob_social@test.edu",
        role=UserRole.STUDENT,
        name="Bob Operative",
        college="Stanford",
        is_active=True,
    )
    cat = Category(name="Social Reverse", description="Test category")
    db_session.add_all([user_a, user_b, cat])
    db_session.flush()

    chall = Challenge(
        title="Keygen Me Social",
        description="Crack the social keygen.",
        points=100,
        category_id=cat.id,
        difficulty=ChallengeDifficulty.MEDIUM,
        flag_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        is_active=True,
    )
    db_session.add(chall)
    db_session.commit()

    alice_token = create_access_token({"sub": str(user_a.id), "role": user_a.role.value})
    bob_token = create_access_token({"sub": str(user_b.id), "role": user_b.role.value})

    return {
        "alice": user_a,
        "bob": user_b,
        "challenge": chall,
        "alice_token": alice_token,
        "bob_token": bob_token,
    }


def test_community_writeup_lifecycle(client, social_test_setup):
    """Test publishing, listing, updating, upvoting, and deleting community writeups."""
    alice_token = social_test_setup["alice_token"]
    bob_token = social_test_setup["bob_token"]
    chall_id = social_test_setup["challenge"].id

    # 1. Alice publishes a solution/writeup
    resp_pub = client.post(
        f"/api/challenges/{chall_id}/solutions",
        json={
            "title": "Reverse Engineering with Ghidra & Python",
            "content": "Step 1: Open binary in Ghidra.\nStep 2: Locate validation routine at 0x401000.\nStep 3: Solve linear equations in Python.",
            "tags": "Ghidra, Python, Math"
        },
        headers={"Authorization": f"Bearer {alice_token}"}
    )
    assert resp_pub.status_code == 201
    writeup = resp_pub.json()
    assert writeup["title"] == "Reverse Engineering with Ghidra & Python"
    assert writeup["author_username"] == "operative_alice"
    assert writeup["upvotes_count"] == 0
    writeup_id = writeup["id"]

    # 2. Bob lists community writeups
    resp_list = client.get(
        f"/api/challenges/{chall_id}/solutions",
        headers={"Authorization": f"Bearer {bob_token}"}
    )
    assert resp_list.status_code == 200
    items = resp_list.json()
    assert len(items) == 1
    assert items[0]["id"] == writeup_id
    assert items[0]["is_author"] is False
    assert items[0]["is_upvoted_by_me"] is False

    # 3. Bob upvotes Alice's writeup
    resp_up = client.post(
        f"/api/challenges/{chall_id}/solutions/{writeup_id}/upvote",
        headers={"Authorization": f"Bearer {bob_token}"}
    )
    assert resp_up.status_code == 200
    assert resp_up.json()["upvotes_count"] == 1
    assert resp_up.json()["is_upvoted"] is True

    # 4. Bob toggles upvote again (removes upvote)
    resp_up2 = client.post(
        f"/api/challenges/{chall_id}/solutions/{writeup_id}/upvote",
        headers={"Authorization": f"Bearer {bob_token}"}
    )
    assert resp_up2.status_code == 200
    assert resp_up2.json()["upvotes_count"] == 0
    assert resp_up2.json()["is_upvoted"] is False

    # 5. Bob re-adds upvote
    client.post(
        f"/api/challenges/{chall_id}/solutions/{writeup_id}/upvote",
        headers={"Authorization": f"Bearer {bob_token}"}
    )

    # 6. Alice updates her writeup
    resp_edit = client.put(
        f"/api/challenges/{chall_id}/solutions/{writeup_id}",
        json={"title": "Updated: Ghidra & Z3 Solver"},
        headers={"Authorization": f"Bearer {alice_token}"}
    )
    assert resp_edit.status_code == 200
    assert resp_edit.json()["title"] == "Updated: Ghidra & Z3 Solver"

    # 7. Bob cannot edit Alice's writeup
    resp_bad_edit = client.put(
        f"/api/challenges/{chall_id}/solutions/{writeup_id}",
        json={"title": "Hacked Title"},
        headers={"Authorization": f"Bearer {bob_token}"}
    )
    assert resp_bad_edit.status_code == 403

    # 8. Alice deletes her writeup
    resp_del = client.delete(
        f"/api/challenges/{chall_id}/solutions/{writeup_id}",
        headers={"Authorization": f"Bearer {alice_token}"}
    )
    assert resp_del.status_code == 200
    assert resp_del.json()["status"] == "deleted"

    # 9. Verify writeups list is now empty
    resp_empty = client.get(
        f"/api/challenges/{chall_id}/solutions",
        headers={"Authorization": f"Bearer {bob_token}"}
    )
    assert resp_empty.status_code == 200
    assert len(resp_empty.json()) == 0


def test_leetcode_style_followers_system(client, social_test_setup):
    """Test following, unfollowing, counts, list endpoints, and self-follow rejection."""
    alice = social_test_setup["alice"]
    bob = social_test_setup["bob"]
    alice_token = social_test_setup["alice_token"]
    bob_token = social_test_setup["bob_token"]

    # 1. Alice tries to follow herself -> rejected 400
    resp_self = client.post(
        f"/api/users/{alice.id}/follow",
        headers={"Authorization": f"Bearer {alice_token}"}
    )
    assert resp_self.status_code == 400

    # 2. Bob follows Alice
    resp_follow = client.post(
        f"/api/users/{alice.id}/follow",
        headers={"Authorization": f"Bearer {bob_token}"}
    )
    assert resp_follow.status_code == 200
    f_data = resp_follow.json()
    assert f_data["is_following"] is True
    assert f_data["followers_count"] == 1
    assert f_data["following_count"] == 0

    # 3. Check Alice's profile reflects followers_count = 1
    resp_profile = client.get(
        f"/api/profile/{alice.id}",
        headers={"Authorization": f"Bearer {bob_token}"}
    )
    assert resp_profile.status_code == 200
    assert resp_profile.json()["followers_count"] == 1
    assert resp_profile.json()["following_count"] == 0

    # 4. Check Bob's profile reflects following_count = 1
    resp_bob_profile = client.get(
        f"/api/profile/{bob.id}",
        headers={"Authorization": f"Bearer {bob_token}"}
    )
    assert resp_bob_profile.status_code == 200
    assert resp_bob_profile.json()["following_count"] == 1
    assert resp_bob_profile.json()["followers_count"] == 0

    # 5. List Alice's followers -> should include Bob
    resp_alice_followers = client.get(
        f"/api/users/{alice.id}/followers",
        headers={"Authorization": f"Bearer {alice_token}"}
    )
    assert resp_alice_followers.status_code == 200
    followers = resp_alice_followers.json()
    assert len(followers) == 1
    assert followers[0]["username"] == "operative_bob"

    # 6. List Bob's following -> should include Alice
    resp_bob_following = client.get(
        f"/api/users/{bob.id}/following",
        headers={"Authorization": f"Bearer {bob_token}"}
    )
    assert resp_bob_following.status_code == 200
    following = resp_bob_following.json()
    assert len(following) == 1
    assert following[0]["username"] == "operative_alice"

    # 7. Bob unfollows Alice
    resp_unfollow = client.delete(
        f"/api/users/{alice.id}/follow",
        headers={"Authorization": f"Bearer {bob_token}"}
    )
    assert resp_unfollow.status_code == 200
    assert resp_unfollow.json()["is_following"] is False
    assert resp_unfollow.json()["followers_count"] == 0
