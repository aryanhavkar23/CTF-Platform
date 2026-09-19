from datetime import datetime, timezone, timedelta
from uuid import uuid4
from unittest.mock import MagicMock, patch
import pytest
from fastapi import status
from docker.errors import DockerException, NotFound

from app.config import settings
from app.models.user import User, UserRole
from app.models.challenge import Challenge, ChallengeDifficulty, ChallengeType, InstanceMode
from app.models.challenge_instance import ChallengeInstance, ChallengeInstanceStatus
from app.models.category import Category
from app.models.team import Team, TeamMember
from app.models.event import Event, EventStatus
from app.models.event_registration import EventRegistration, RegistrationType
from app.core.security import hash_password, create_access_token
from app.services.challenge_service import hash_flag
from app.services.docker_challenge_service import DockerChallengeService, docker_challenge_service


@pytest.fixture
def auth_context(db_session):
    student1 = User(
        username="docker_student1",
        email="docker1@college.edu",
        hashed_password=hash_password("Pass123!"),
        role=UserRole.STUDENT
    )
    student2 = User(
        username="docker_student2",
        email="docker2@college.edu",
        hashed_password=hash_password("Pass123!"),
        role=UserRole.STUDENT
    )
    admin = User(
        username="docker_admin",
        email="docker_admin@college.edu",
        hashed_password=hash_password("AdminPass123!"),
        role=UserRole.ADMIN
    )
    db_session.add_all([student1, student2, admin])
    db_session.flush()

    def token_header(u: User):
        token = create_access_token(data={"sub": str(u.id), "email": u.email, "role": u.role.value})
        return {"Authorization": f"Bearer {token}"}

    return {
        "student1": student1,
        "student2": student2,
        "admin": admin,
        "student1_header": token_header(student1),
        "student2_header": token_header(student2),
        "admin_header": token_header(admin),
    }


@pytest.fixture
def live_challenge_fixture(db_session):
    category = Category(name="Web Live Exploitation", description="Live container services")
    db_session.add(category)
    db_session.flush()

    live_chal = Challenge(
        title="Live Web Vulnerability",
        description="Inspect and exploit the live web container service.",
        category_id=category.id,
        difficulty=ChallengeDifficulty.MEDIUM,
        points=250,
        flag_hash=hash_flag("flag{live_container_pwned_123}"),
        is_active=True,
        challenge_type=ChallengeType.LIVE,
        is_live_instance=True,
        docker_image="hello-live-challenge:latest",
        container_port=80,
        protocol="http",
        instance_mode=InstanceMode.PER_USER,
        cpu_limit=0.5,
        memory_limit="256m",
        ttl_seconds=3600,
        healthcheck_path="/"
    )

    static_chal = Challenge(
        title="Static Forensic Challenge",
        description="Download file and extract metadata.",
        category_id=category.id,
        difficulty=ChallengeDifficulty.EASY,
        points=100,
        flag_hash=hash_flag("flag{static_file_flag}"),
        is_active=True,
        challenge_type=ChallengeType.STATIC,
        is_live_instance=False
    )

    db_session.add_all([live_chal, static_chal])
    db_session.commit()
    db_session.refresh(live_chal)
    db_session.refresh(static_chal)

    return {
        "category": category,
        "live": live_chal,
        "static": static_chal,
    }


@pytest.fixture
def mock_docker():
    """Provides a controlled mock Docker client with recorded calls and dummy container."""
    mock_client = MagicMock()
    mock_container = MagicMock()
    mock_container.id = "mock_container_id_abcdef123456"
    mock_container.status = "running"
    mock_container.stop = MagicMock()
    mock_container.remove = MagicMock()

    mock_client.ping.return_value = True
    mock_client.networks.get.return_value = MagicMock(name="ctf_challenges_net")
    mock_client.containers.run.return_value = mock_container
    mock_client.containers.get.return_value = mock_container

    # Inject into global service
    old_client = docker_challenge_service._client
    docker_challenge_service._client = mock_client

    with patch.object(DockerChallengeService, "check_container_health", return_value=True), \
         patch("app.services.docker_challenge_service.is_port_available", return_value=True):
        yield {
            "client": mock_client,
            "container": mock_container,
        }

    docker_challenge_service._client = old_client


def test_static_challenge_cannot_start_instance(client, auth_context, live_challenge_fixture, mock_docker):
    """Static challenges cannot launch containers (HTTP 400)."""
    static_id = live_challenge_fixture["static"].id
    res = client.post(f"/api/challenges/{static_id}/instance", headers=auth_context["student1_header"])
    assert res.status_code == status.HTTP_400_BAD_REQUEST
    assert "static challenge" in res.json()["detail"].lower()


def test_unauthenticated_cannot_start_instance(client, live_challenge_fixture):
    """Unauthenticated users cannot launch containers (HTTP 401)."""
    live_id = live_challenge_fixture["live"].id
    res = client.post(f"/api/challenges/{live_id}/instance")
    assert res.status_code == status.HTTP_401_UNAUTHORIZED


def test_student_start_and_inspect_live_instance(client, auth_context, live_challenge_fixture, mock_docker):
    """Student starts live instance, receives safe URL/port, and zero secret leakage."""
    live_id = live_challenge_fixture["live"].id
    res = client.post(f"/api/challenges/{live_id}/instance", headers=auth_context["student1_header"])
    assert res.status_code == status.HTTP_200_OK
    data = res.json()

    assert data["status"] == "running"
    assert data["host"] == settings.CHALLENGE_HOST
    assert 20000 <= data["port"] <= 25000
    assert f":{data['port']}" in data["url"]
    assert data["protocol"] == "http"
    assert data["expires_at"] is not None

    # CRITICAL: Security check - Verify no secret leakage
    res_str = res.text
    assert "flag{" not in res_str
    assert "flag_hash" not in res_str
    assert "mock_container_id" not in res_str  # Docker container id hidden from students
    assert "socket" not in res_str

    # Inspect active instance via GET
    get_res = client.get(f"/api/challenges/{live_id}/instance", headers=auth_context["student1_header"])
    assert get_res.status_code == status.HTTP_200_OK
    get_data = get_res.json()
    assert get_data["instance_id"] == data["instance_id"]
    assert get_data["port"] == data["port"]


def test_duplicate_instance_request_returns_existing(client, auth_context, live_challenge_fixture, mock_docker):
    """Subsequent requests within TTL return existing running instance without spawning duplicates."""
    live_id = live_challenge_fixture["live"].id
    res1 = client.post(f"/api/challenges/{live_id}/instance", headers=auth_context["student1_header"])
    assert res1.status_code == status.HTTP_200_OK

    res2 = client.post(f"/api/challenges/{live_id}/instance", headers=auth_context["student1_header"])
    assert res2.status_code == status.HTTP_200_OK

    assert res1.json()["instance_id"] == res2.json()["instance_id"]
    assert res1.json()["port"] == res2.json()["port"]
    # Docker run should only have been called once
    assert mock_docker["client"].containers.run.call_count == 1


def test_user_isolation(client, auth_context, live_challenge_fixture, mock_docker):
    """Student B cannot access or stop Student A's challenge instance."""
    live_id = live_challenge_fixture["live"].id
    res1 = client.post(f"/api/challenges/{live_id}/instance", headers=auth_context["student1_header"])
    assert res1.status_code == status.HTTP_200_OK

    # Student B queries GET -> Not found (because Student B has no active instance)
    res_b = client.get(f"/api/challenges/{live_id}/instance", headers=auth_context["student2_header"])
    assert res_b.status_code == status.HTTP_404_NOT_FOUND

    # Student B tries to DELETE -> Not found (cannot stop someone else's instance)
    del_b = client.delete(f"/api/challenges/{live_id}/instance", headers=auth_context["student2_header"])
    assert del_b.status_code == status.HTTP_404_NOT_FOUND


def test_team_instance_sharing_and_isolation(client, db_session, auth_context, live_challenge_fixture, mock_docker):
    """Per-team challenges allow team members to share instance and prevent outside access."""
    # Create Team
    team = Team(name="Alpha Live Team", invite_code="ALIVE123", owner_id=auth_context["student1"].id)
    db_session.add(team)
    db_session.flush()

    tm1 = TeamMember(team_id=team.id, user_id=auth_context["student1"].id)
    db_session.add(tm1)
    db_session.commit()

    # Create team-mode challenge
    team_chal = Challenge(
        title="Live Team Service",
        description="Team-wide isolated challenge service.",
        category_id=live_challenge_fixture["category"].id,
        difficulty=ChallengeDifficulty.HARD,
        points=400,
        flag_hash=hash_flag("flag{team_pwn_success}"),
        is_active=True,
        challenge_type=ChallengeType.LIVE,
        is_live_instance=True,
        docker_image="hello-live-challenge:latest",
        instance_mode=InstanceMode.PER_TEAM,
    )
    db_session.add(team_chal)
    db_session.commit()

    # Student 1 (in team) starts instance
    res1 = client.post(f"/api/challenges/{team_chal.id}/instance", headers=auth_context["student1_header"])
    assert res1.status_code == status.HTTP_200_OK
    inst_id = res1.json()["instance_id"]

    # Add Student 2 to same team
    tm2 = TeamMember(team_id=team.id, user_id=auth_context["student2"].id)
    db_session.add(tm2)
    db_session.commit()

    # Student 2 now gets the exact same team instance
    res2 = client.get(f"/api/challenges/{team_chal.id}/instance", headers=auth_context["student2_header"])
    assert res2.status_code == status.HTTP_200_OK
    assert res2.json()["instance_id"] == inst_id


def test_event_live_challenge_access_validation(client, db_session, auth_context, live_challenge_fixture, mock_docker):
    """Event-scoped challenge requires registered participant."""
    now = datetime.now(timezone.utc)
    event = Event(
        name="Live CTF Tournament",
        slug="live-ctf-tournament",
        description="Championship CTF",
        start_at=now - timedelta(hours=1),
        end_at=now + timedelta(hours=3),
        status=EventStatus.LIVE
    )
    db_session.add(event)
    db_session.commit()

    live_id = live_challenge_fixture["live"].id

    # Unregistered student attempts to start instance under event -> 403
    res = client.post(f"/api/challenges/{live_id}/instance?event_id={event.id}", headers=auth_context["student1_header"])
    assert res.status_code == status.HTTP_403_FORBIDDEN
    assert "registered" in res.json()["detail"].lower()

    # Register student
    reg = EventRegistration(
        event_id=event.id,
        user_id=auth_context["student1"].id,
        registration_type=RegistrationType.INDIVIDUAL
    )
    db_session.add(reg)
    db_session.commit()

    # Now starting succeeds
    res_ok = client.post(f"/api/challenges/{live_id}/instance?event_id={event.id}", headers=auth_context["student1_header"])
    assert res_ok.status_code == status.HTTP_200_OK


def test_container_stop_and_delete(client, auth_context, live_challenge_fixture, mock_docker):
    """Student terminates active instance, stopping container and marking status."""
    live_id = live_challenge_fixture["live"].id
    client.post(f"/api/challenges/{live_id}/instance", headers=auth_context["student1_header"])

    # Stop instance
    stop_res = client.delete(f"/api/challenges/{live_id}/instance", headers=auth_context["student1_header"])
    assert stop_res.status_code == status.HTTP_200_OK
    assert stop_res.json()["status"] == "stopped"

    # Verify container stop/remove called
    mock_docker["container"].stop.assert_called()
    mock_docker["container"].remove.assert_called()


def test_ttl_expiration_cleanup(db_session, auth_context, live_challenge_fixture, mock_docker):
    """Expired instances are cleanly terminated and marked EXPIRED by cleanup worker."""
    chal = live_challenge_fixture["live"]
    past = datetime.now(timezone.utc) - timedelta(minutes=10)

    inst = ChallengeInstance(
        challenge_id=chal.id,
        user_id=auth_context["student1"].id,
        container_id="expired_container_123",
        container_name="ctf_inst_test_expired",
        status=ChallengeInstanceStatus.RUNNING,
        internal_port=80,
        external_port=20010,
        external_host="localhost",
        url="http://localhost:20010",
        started_at=past - timedelta(hours=1),
        expires_at=past,
    )
    db_session.add(inst)
    db_session.commit()

    cleaned = docker_challenge_service.cleanup_expired_instances(db_session)
    assert cleaned >= 1

    db_session.refresh(inst)
    assert inst.status == ChallengeInstanceStatus.EXPIRED
    assert inst.stopped_at is not None


def test_admin_list_and_force_stop_instance(client, auth_context, live_challenge_fixture, mock_docker):
    """Admin inspects container metadata and can force-terminate any container."""
    live_id = live_challenge_fixture["live"].id
    client.post(f"/api/challenges/{live_id}/instance", headers=auth_context["student1_header"])

    # Admin lists instances
    list_res = client.get("/api/admin/challenge-instances", headers=auth_context["admin_header"])
    assert list_res.status_code == status.HTTP_200_OK
    data = list_res.json()
    assert data["total"] >= 1
    item = data["items"][0]
    assert item["container_id"] == "mock_container_id_abcdef123456"
    assert item["username"] == "docker_student1"

    # Admin force-stops instance
    inst_id = item["id"]
    kill_res = client.post(f"/api/admin/challenge-instances/{inst_id}/stop", headers=auth_context["admin_header"])
    assert kill_res.status_code == status.HTTP_200_OK
    assert kill_res.json()["status"] == "stopped"


def test_docker_unavailable_safe_error(client, auth_context, live_challenge_fixture):
    """If Docker daemon is unreachable, returns safe HTTP 503 without leaking raw tracebacks."""
    failing_service = DockerChallengeService()
    failing_service._client = MagicMock()
    failing_service._client.ping.side_effect = DockerException("Error while fetching server API version")

    with patch("app.api.live_challenges.docker_challenge_service", failing_service):
        live_id = live_challenge_fixture["live"].id
        res = client.post(f"/api/challenges/{live_id}/instance", headers=auth_context["student1_header"])
        assert res.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        detail = res.json()["detail"]
        assert "currently unavailable" in detail
        # No internal python paths or raw socket pipes leaked
        assert "docker.sock" not in detail
        assert "Traceback" not in detail


def test_security_hardening_validation(client, auth_context, live_challenge_fixture, mock_docker):
    """Verify strictly enforced container hardening flags."""
    live_id = live_challenge_fixture["live"].id
    res = client.post(f"/api/challenges/{live_id}/instance", headers=auth_context["student1_header"])
    assert res.status_code == status.HTTP_200_OK

    run_calls = mock_docker["client"].containers.run.call_args_list
    assert len(run_calls) == 1
    _, kwargs = run_calls[0]

    # Verification of container hardening rules
    assert kwargs.get("privileged") is False, "Containers must NEVER run privileged"
    assert kwargs.get("cap_drop") == ["ALL"], "Must drop all Linux capabilities"
    assert "no-new-privileges:true" in kwargs.get("security_opt", []), "Must forbid privilege escalation"
    assert kwargs.get("volumes") == {}, "Must NEVER mount host filesystem volumes"
    assert kwargs.get("network") == settings.CHALLENGE_DOCKER_NETWORK, "Must attach to isolated network"
    assert kwargs.get("mem_limit") == "256m", "Must apply memory limit"
    assert kwargs.get("nano_cpus") == int(0.5 * 1e9), "Must apply CPU limit"
    assert kwargs.get("pids_limit") == settings.CHALLENGE_DEFAULT_PIDS_LIMIT, "Must apply PID limit"


def test_unapproved_image_rejected(client, auth_context, live_challenge_fixture, mock_docker):
    """Reject launching challenge with unapproved Docker image prefix."""
    live_chal = live_challenge_fixture["live"]
    live_chal.docker_image = "malicious-user/evil-backdoor:v1"

    live_id = live_chal.id
    res = client.post(f"/api/challenges/{live_id}/instance", headers=auth_context["student1_header"])
    assert res.status_code == status.HTTP_403_FORBIDDEN
    assert "allowlist" in res.json()["detail"].lower()
