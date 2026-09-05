import pytest
from starlette.testclient import TestClient
from app.main import app
from app.database import get_db, Base, get_engine
from sqlalchemy.orm import sessionmaker
from app.models.user import User, UserRole
from app.core.security import create_access_token, hash_password
from app.config import settings


@pytest.fixture
def teams_setup(db_session):
    """Sets up authenticated test users (owner, member, other student, admin)."""
    owner = User(
        username="team_owner_alice",
        email="alice@college.edu",
        hashed_password=hash_password("AliceSecurePass123!"),
        role=UserRole.STUDENT,
        college="OWASP Tech",
        is_active=True,
    )
    member = User(
        username="team_member_bob",
        email="bob@college.edu",
        hashed_password=hash_password("BobSecurePass123!"),
        role=UserRole.STUDENT,
        college="OWASP Tech",
        is_active=True,
    )
    outsider = User(
        username="team_outsider_charlie",
        email="charlie@othercollege.edu",
        hashed_password=hash_password("CharlieSecurePass123!"),
        role=UserRole.STUDENT,
        college="Other College",
        is_active=True,
    )
    admin = User(
        username="team_admin_dave",
        email="admin_dave@college.edu",
        hashed_password=hash_password("AdminSecurePass123!"),
        role=UserRole.ADMIN,
        college="OWASP Tech",
        is_active=True,
    )
    db_session.add_all([owner, member, outsider, admin])
    db_session.commit()

    owner_token = create_access_token({"sub": str(owner.id), "role": owner.role.value})
    member_token = create_access_token({"sub": str(member.id), "role": member.role.value})
    outsider_token = create_access_token({"sub": str(outsider.id), "role": outsider.role.value})
    admin_token = create_access_token({"sub": str(admin.id), "role": admin.role.value})

    return {
        "owner": owner,
        "member": member,
        "outsider": outsider,
        "admin": admin,
        "owner_headers": {"Authorization": f"Bearer {owner_token}"},
        "member_headers": {"Authorization": f"Bearer {member_token}"},
        "outsider_headers": {"Authorization": f"Bearer {outsider_token}"},
        "admin_headers": {"Authorization": f"Bearer {admin_token}"},
    }


# =========================================================================
# 1. TEAM CREATION TESTS
# =========================================================================

def test_authenticated_user_can_create_team(client, teams_setup):
    """Authenticated user creates a team and automatically becomes owner."""
    res = client.post(
        "/api/teams",
        headers=teams_setup["owner_headers"],
        json={"name": "CyberKnights", "description": "Top security team", "college": "OWASP Tech"}
    )
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "CyberKnights"
    assert data["description"] == "Top security team"
    assert data["college"] == "OWASP Tech"
    assert data["owner_id"] == str(teams_setup["owner"].id)
    assert data["owner_username"] == "team_owner_alice"
    assert data["member_count"] == 1
    assert data["is_active"] is True


def test_unauthenticated_user_cannot_create_team(client):
    """Unauthenticated request must be rejected with 401."""
    res = client.post(
        "/api/teams",
        json={"name": "RogueTeam", "description": "No auth"}
    )
    assert res.status_code == 401


def test_duplicate_team_name_rejected(client, teams_setup):
    """Duplicate team name (case-insensitive) must be rejected with 409."""
    res1 = client.post(
        "/api/teams",
        headers=teams_setup["owner_headers"],
        json={"name": "UniqueTeam"}
    )
    assert res1.status_code == 201

    res2 = client.post(
        "/api/teams",
        headers=teams_setup["outsider_headers"],
        json={"name": "uniqueteam"}
    )
    assert res2.status_code == 409


def test_client_cannot_choose_arbitrary_owner(client, teams_setup):
    """Client passing an owner_id in body must be ignored; owner must come from JWT."""
    res = client.post(
        "/api/teams",
        headers=teams_setup["owner_headers"],
        json={
            "name": "TamperTeam",
            "owner_id": str(teams_setup["admin"].id)
        }
    )
    assert res.status_code == 201
    assert res.json()["owner_id"] == str(teams_setup["owner"].id)


# =========================================================================
# 2. TEAM MEMBERSHIP MANAGEMENT
# =========================================================================

def test_owner_can_add_member_and_view_members(client, teams_setup):
    """Owner adds another user and verifies member list."""
    # Create team
    create_res = client.post(
        "/api/teams",
        headers=teams_setup["owner_headers"],
        json={"name": "AlphaSquad"}
    )
    team_id = create_res.json()["id"]

    # Owner adds member by user_id
    add_res = client.post(
        f"/api/teams/{team_id}/members",
        headers=teams_setup["owner_headers"],
        json={"user_id": str(teams_setup["member"].id)}
    )
    assert add_res.status_code == 201
    member_data = add_res.json()
    assert member_data["username"] == "team_member_bob"
    assert member_data["role"] == "member"
    assert member_data["is_active"] is True

    # View members list
    members_res = client.get(f"/api/teams/{team_id}/members")
    assert members_res.status_code == 200
    members = members_res.json()
    assert len(members) == 2
    roles = {m["username"]: m["role"] for m in members}
    assert roles["team_owner_alice"] == "owner"
    assert roles["team_member_bob"] == "member"


def test_normal_member_cannot_add_member(client, teams_setup):
    """A regular member cannot add another member."""
    # Create team & add bob
    team_res = client.post("/api/teams", headers=teams_setup["owner_headers"], json={"name": "BetaSquad"})
    team_id = team_res.json()["id"]
    client.post(f"/api/teams/{team_id}/members", headers=teams_setup["owner_headers"], json={"user_id": str(teams_setup["member"].id)})

    # Bob attempts to add Charlie -> 403 Forbidden
    res = client.post(
        f"/api/teams/{team_id}/members",
        headers=teams_setup["member_headers"],
        json={"user_id": str(teams_setup["outsider"].id)}
    )
    assert res.status_code == 403


def test_duplicate_membership_rejected(client, teams_setup):
    """User cannot be added twice to the same team."""
    team_res = client.post("/api/teams", headers=teams_setup["owner_headers"], json={"name": "GammaSquad"})
    team_id = team_res.json()["id"]

    # Add Bob once
    client.post(f"/api/teams/{team_id}/members", headers=teams_setup["owner_headers"], json={"user_id": str(teams_setup["member"].id)})

    # Attempt to add Bob again -> 400 Bad Request
    res = client.post(
        f"/api/teams/{team_id}/members",
        headers=teams_setup["owner_headers"],
        json={"user_id": str(teams_setup["member"].id)}
    )
    assert res.status_code == 400
    assert "already an active member" in res.json()["detail"]


def test_inactive_team_cannot_accept_members(client, teams_setup):
    """Inactive team cannot accept new members."""
    team_res = client.post("/api/teams", headers=teams_setup["owner_headers"], json={"name": "InactiveTeam"})
    team_id = team_res.json()["id"]

    # Deactivate team
    client.delete(f"/api/teams/{team_id}", headers=teams_setup["owner_headers"])

    # Attempt to add member -> 400 Bad Request
    res = client.post(
        f"/api/teams/{team_id}/members",
        headers=teams_setup["owner_headers"],
        json={"user_id": str(teams_setup["member"].id)}
    )
    assert res.status_code == 400
    assert "inactive" in res.json()["detail"].lower()


def test_maximum_team_size_enforced(client, db_session, teams_setup):
    """Configured MAX_TEAM_SIZE must be strictly enforced."""
    team_res = client.post("/api/teams", headers=teams_setup["owner_headers"], json={"name": "MaxSquad"})
    team_id = team_res.json()["id"]

    # Team already has 1 member (the owner).
    # Create extra users to fill up to MAX_TEAM_SIZE (4)
    extra_users = []
    for i in range(1, 5):
        u = User(
            username=f"extra_user_{i}",
            email=f"extra{i}@college.edu",
            hashed_password=hash_password("ExtraPass123!"),
            role=UserRole.STUDENT,
            is_active=True
        )
        db_session.add(u)
        extra_users.append(u)
    db_session.commit()

    # Add 2nd, 3rd, 4th members -> should succeed
    for u in extra_users[:3]:
        res = client.post(
            f"/api/teams/{team_id}/members",
            headers=teams_setup["owner_headers"],
            json={"user_id": str(u.id)}
        )
        assert res.status_code == 201

    # Team now has 4 members (owner + 3 extra)
    detail_res = client.get(f"/api/teams/{team_id}")
    assert detail_res.json()["member_count"] == 4

    # Adding 5th member must fail with 400 Bad Request
    res_overflow = client.post(
        f"/api/teams/{team_id}/members",
        headers=teams_setup["owner_headers"],
        json={"user_id": str(extra_users[3].id)}
    )
    assert res_overflow.status_code == 400
    assert "maximum size" in res_overflow.json()["detail"].lower()


# =========================================================================
# 3. REMOVING MEMBERS & LEAVING
# =========================================================================

def test_owner_can_remove_member(client, teams_setup):
    """Owner removes a member from the team."""
    team_res = client.post("/api/teams", headers=teams_setup["owner_headers"], json={"name": "DeltaSquad"})
    team_id = team_res.json()["id"]
    client.post(f"/api/teams/{team_id}/members", headers=teams_setup["owner_headers"], json={"user_id": str(teams_setup["member"].id)})

    # Owner removes member
    del_res = client.delete(
        f"/api/teams/{team_id}/members/{teams_setup['member'].id}",
        headers=teams_setup["owner_headers"]
    )
    assert del_res.status_code == 200

    # Verify member is gone
    members_res = client.get(f"/api/teams/{team_id}/members")
    assert len(members_res.json()) == 1


def test_member_cannot_remove_another_member(client, teams_setup):
    """Normal member cannot remove another member."""
    team_res = client.post("/api/teams", headers=teams_setup["owner_headers"], json={"name": "EpsilonSquad"})
    team_id = team_res.json()["id"]
    client.post(f"/api/teams/{team_id}/members", headers=teams_setup["owner_headers"], json={"user_id": str(teams_setup["member"].id)})
    client.post(f"/api/teams/{team_id}/members", headers=teams_setup["owner_headers"], json={"user_id": str(teams_setup["outsider"].id)})

    # Bob attempts to remove Charlie -> 403
    res = client.delete(
        f"/api/teams/{team_id}/members/{teams_setup['outsider'].id}",
        headers=teams_setup["member_headers"]
    )
    assert res.status_code == 403


def test_owner_cannot_remove_themselves(client, teams_setup):
    """Owner cannot remove themselves via remove member endpoint."""
    team_res = client.post("/api/teams", headers=teams_setup["owner_headers"], json={"name": "ZetaSquad"})
    team_id = team_res.json()["id"]

    res = client.delete(
        f"/api/teams/{team_id}/members/{teams_setup['owner'].id}",
        headers=teams_setup["owner_headers"]
    )
    assert res.status_code == 400


def test_normal_member_can_leave(client, teams_setup):
    """A regular member can leave their team."""
    team_res = client.post("/api/teams", headers=teams_setup["owner_headers"], json={"name": "EtaSquad"})
    team_id = team_res.json()["id"]
    client.post(f"/api/teams/{team_id}/members", headers=teams_setup["owner_headers"], json={"user_id": str(teams_setup["member"].id)})

    # Bob leaves
    leave_res = client.delete(f"/api/teams/{team_id}/leave", headers=teams_setup["member_headers"])
    assert leave_res.status_code == 200

    # Verify Bob left
    members_res = client.get(f"/api/teams/{team_id}/members")
    assert len(members_res.json()) == 1


def test_owner_cannot_leave_without_transferring_ownership(client, teams_setup):
    """Owner attempting to leave must receive 400 Bad Request."""
    team_res = client.post("/api/teams", headers=teams_setup["owner_headers"], json={"name": "ThetaSquad"})
    team_id = team_res.json()["id"]

    leave_res = client.delete(f"/api/teams/{team_id}/leave", headers=teams_setup["owner_headers"])
    assert leave_res.status_code == 400
    assert "transfer" in leave_res.json()["detail"].lower()


# =========================================================================
# 4. OWNERSHIP TRANSFER
# =========================================================================

def test_atomic_ownership_transfer(client, teams_setup):
    """Owner transfers ownership to Bob: Bob becomes owner, Alice becomes member."""
    team_res = client.post("/api/teams", headers=teams_setup["owner_headers"], json={"name": "IotaSquad"})
    team_id = team_res.json()["id"]
    client.post(f"/api/teams/{team_id}/members", headers=teams_setup["owner_headers"], json={"user_id": str(teams_setup["member"].id)})

    # Alice transfers ownership to Bob
    trans_res = client.post(
        f"/api/teams/{team_id}/transfer-owner",
        headers=teams_setup["owner_headers"],
        json={"new_owner_id": str(teams_setup["member"].id)}
    )
    assert trans_res.status_code == 200
    detail = trans_res.json()
    assert detail["owner_id"] == str(teams_setup["member"].id)
    assert detail["owner_username"] == "team_member_bob"

    # Verify roles in members list: Bob is owner, Alice is member
    members = {m["username"]: m["role"] for m in detail["members"]}
    assert members["team_member_bob"] == "owner"
    assert members["team_owner_alice"] == "member"


def test_transfer_to_non_member_rejected(client, teams_setup):
    """Cannot transfer ownership to someone outside the team."""
    team_res = client.post("/api/teams", headers=teams_setup["owner_headers"], json={"name": "KappaSquad"})
    team_id = team_res.json()["id"]

    # Alice attempts to transfer to Charlie (not in team)
    res = client.post(
        f"/api/teams/{team_id}/transfer-owner",
        headers=teams_setup["owner_headers"],
        json={"new_owner_id": str(teams_setup["outsider"].id)}
    )
    assert res.status_code == 400
    assert "active member" in res.json()["detail"].lower()


def test_non_owner_cannot_transfer_ownership(client, teams_setup):
    """Non-owner attempting to transfer ownership receives 403 Forbidden."""
    team_res = client.post("/api/teams", headers=teams_setup["owner_headers"], json={"name": "LambdaSquad"})
    team_id = team_res.json()["id"]
    client.post(f"/api/teams/{team_id}/members", headers=teams_setup["owner_headers"], json={"user_id": str(teams_setup["member"].id)})

    # Bob attempts to transfer ownership
    res = client.post(
        f"/api/teams/{team_id}/transfer-owner",
        headers=teams_setup["member_headers"],
        json={"new_owner_id": str(teams_setup["owner"].id)}
    )
    assert res.status_code == 403


# =========================================================================
# 5. TEAM UPDATE & DEACTIVATION
# =========================================================================

def test_team_update_and_deactivation(client, teams_setup):
    """Owner and admin can update/deactivate team; member cannot."""
    team_res = client.post("/api/teams", headers=teams_setup["owner_headers"], json={"name": "MuSquad", "description": "Original"})
    team_id = team_res.json()["id"]
    client.post(f"/api/teams/{team_id}/members", headers=teams_setup["owner_headers"], json={"user_id": str(teams_setup["member"].id)})

    # Bob cannot update
    bob_up = client.put(f"/api/teams/{team_id}", headers=teams_setup["member_headers"], json={"description": "Hacked"})
    assert bob_up.status_code == 403

    # Alice can update
    alice_up = client.put(f"/api/teams/{team_id}", headers=teams_setup["owner_headers"], json={"description": "Updated by Owner"})
    assert alice_up.status_code == 200
    assert alice_up.json()["description"] == "Updated by Owner"

    # Admin can deactivate
    admin_del = client.delete(f"/api/teams/{team_id}", headers=teams_setup["admin_headers"])
    assert admin_del.status_code == 200

    # Team is now inactive
    detail = client.get(f"/api/teams/{team_id}").json()
    assert detail["is_active"] is False


# =========================================================================
# 6. COMPLETE MANUAL FLOW INTEGRATION TEST (Section 20)
# =========================================================================

def test_complete_section_20_flow(client, teams_setup):
    """
    User A registers (Alice)
    User B registers (Bob)
    User A creates Team Alpha
    User A automatically becomes owner
    User A adds User B
    Team Alpha has 2 members
    User B cannot remove User A
    User B cannot edit Team Alpha
    User A transfers ownership to User B
    User B becomes owner
    User A becomes member
    User A leaves team
    Team remains owned by User B
    """
    # 1. User A creates Team Alpha
    create_res = client.post(
        "/api/teams",
        headers=teams_setup["owner_headers"],
        json={"name": "Team Alpha", "description": "Flag hunters", "college": "OWASP Tech"}
    )
    assert create_res.status_code == 201
    team = create_res.json()
    team_id = team["id"]
    assert team["owner_username"] == "team_owner_alice"

    # 2. User A adds User B
    add_res = client.post(
        f"/api/teams/{team_id}/members",
        headers=teams_setup["owner_headers"],
        json={"user_id": str(teams_setup["member"].id)}
    )
    assert add_res.status_code == 201

    # 3. Team Alpha has 2 members
    detail_res = client.get(f"/api/teams/{team_id}")
    assert detail_res.json()["member_count"] == 2

    # 4. User B cannot remove User A
    rem_res = client.delete(
        f"/api/teams/{team_id}/members/{teams_setup['owner'].id}",
        headers=teams_setup["member_headers"]
    )
    assert rem_res.status_code == 403

    # 5. User B cannot edit Team Alpha
    edit_res = client.put(
        f"/api/teams/{team_id}",
        headers=teams_setup["member_headers"],
        json={"name": "Team Beta"}
    )
    assert edit_res.status_code == 403

    # 6. User A transfers ownership to User B
    transfer_res = client.post(
        f"/api/teams/{team_id}/transfer-owner",
        headers=teams_setup["owner_headers"],
        json={"new_owner_id": str(teams_setup["member"].id)}
    )
    assert transfer_res.status_code == 200
    t_data = transfer_res.json()
    assert t_data["owner_id"] == str(teams_setup["member"].id)
    assert t_data["owner_username"] == "team_member_bob"

    # 7. User A leaves team
    leave_res = client.delete(
        f"/api/teams/{team_id}/leave",
        headers=teams_setup["owner_headers"]
    )
    assert leave_res.status_code == 200

    # 8. Team remains owned by User B with 1 member
    final_detail = client.get(f"/api/teams/{team_id}").json()
    assert final_detail["owner_id"] == str(teams_setup["member"].id)
    assert final_detail["member_count"] == 1
    assert len(final_detail["members"]) == 1
    assert final_detail["members"][0]["username"] == "team_member_bob"
    assert final_detail["members"][0]["role"] == "owner"
