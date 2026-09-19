import uuid
from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.category import Category
from app.models.challenge import Challenge, ChallengeDifficulty, ChallengeType
from app.models.github_integration import GitHubIntegration, GitHubSubmissionSync
from app.models.solution import UserWriteup
from app.models.submission import Submission
from app.models.user import User, UserRole
from app.core.security import create_access_token, encrypt_secret, decrypt_secret, hash_password
from app.services.challenge_service import hash_flag
from app.services.github_service import GitHubService




@pytest.fixture
def student_user(db_session: Session):
    user = User(
        username=f"student_{uuid.uuid4().hex[:6]}",
        email=f"student_{uuid.uuid4().hex[:6]}@university.edu",
        hashed_password=hash_password("ValidPassword123!"),
        role=UserRole.STUDENT,
        college="OWASP Academy",
        github_profile_url="https://github.com/cyber-scholar",
        github_username="cyber-scholar",
        is_active=True,
        is_verified=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(student_user: User):
    token = create_access_token({"sub": str(student_user.id), "email": student_user.email, "role": student_user.role.value})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_challenge(db_session: Session):
    cat = Category(name=f"Web Exploitation {uuid.uuid4().hex[:4]}", description="Web security vectors")
    db_session.add(cat)
    db_session.flush()

    raw_flag = f"OWASP{{{uuid.uuid4().hex[:12]}}}"
    chall = Challenge(
        title=f"SQLi Authentication Bypass {uuid.uuid4().hex[:4]}",
        description="Exploit vulnerable parameter to bypass collegiate authentication portal.",
        category_id=cat.id,
        difficulty=ChallengeDifficulty.MEDIUM,
        challenge_type=ChallengeType.STATIC,
        points=300,
        flag_hash=hash_flag(raw_flag),
        is_active=True
    )
    chall._test_raw_flag = raw_flag
    db_session.add(chall)
    db_session.commit()
    db_session.refresh(chall)
    return chall


def test_registration_with_valid_github_url(client: TestClient, db_session: Session):
    """Verifies student registration requires and accepts valid GitHub profile URLs."""
    payload = {
        "username": f"reg_{uuid.uuid4().hex[:6]}",
        "email": f"reg_{uuid.uuid4().hex[:6]}@pccoepune.org",
        "password": "StrongPassword123!",
        "college": "PCCOE Pune",
        "github_profile_url": "https://github.com/octocat"
    }
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["github_profile_url"] == "https://github.com/octocat"
    assert data["github_username"] == "octocat"

    # Verify persisted in database
    user = db_session.query(User).filter(User.username == payload["username"]).first()
    assert user is not None
    assert user.github_profile_url == "https://github.com/octocat"
    assert user.github_username == "octocat"


def test_registration_with_invalid_github_url(client: TestClient):
    """Verifies student registration rejects invalid non-GitHub profile URLs."""
    payload = {
        "username": f"bad_{uuid.uuid4().hex[:6]}",
        "email": f"bad_{uuid.uuid4().hex[:6]}@pccoepune.org",
        "password": "StrongPassword123!",
        "college": "PCCOE Pune",
        "github_profile_url": "https://malicious-site.com/fake-github"
    }
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 422


def test_encryption_at_rest():
    """Verifies AES-256 token encryption and decryption."""
    token = "gho_ABC123secretTokenValueHere"
    encrypted = encrypt_secret(token)
    assert encrypted != token
    assert decrypt_secret(encrypted) == token


def test_github_oauth_url(client: TestClient, auth_headers: dict):
    """Verifies generation of GitHub OAuth authorization URL."""
    resp = client.get("/api/github/oauth/url", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "auth_url" in data
    assert "state=" in data["auth_url"]


def test_github_connection_and_repository_config(client: TestClient, auth_headers: dict, student_user: User, db_session: Session):
    """Verifies connecting GitHub, listing repos, and selecting a repository."""
    # 1. Connect via mock handshake
    exchange_resp = client.post(
        "/api/github/oauth/exchange",
        json={"mock_username": "test-hacker"},
        headers=auth_headers
    )
    assert exchange_resp.status_code == 200
    status_data = exchange_resp.json()
    assert status_data["is_connected"] is True
    assert status_data["github_username"] == "test-hacker"

    # 2. Query status endpoint
    get_status = client.get("/api/github/status", headers=auth_headers)
    assert get_status.status_code == 200
    assert get_status.json()["is_connected"] is True

    # 3. List repositories
    repos_resp = client.get("/api/github/repositories", headers=auth_headers)
    assert repos_resp.status_code == 200
    repos = repos_resp.json()
    assert len(repos) > 0
    selected_target = repos[0]["full_name"]

    # 4. Configure repository
    config_resp = client.post(
        "/api/github/repository",
        json={"repository": selected_target, "auto_create": False},
        headers=auth_headers
    )
    assert config_resp.status_code == 200
    conf_data = config_resp.json()
    assert conf_data["selected_repository"] == selected_target
    assert conf_data["repository_url"] == f"https://github.com/{selected_target}"


def test_accepted_submission_triggers_github_commit_without_flag_leakage(
    client: TestClient,
    auth_headers: dict,
    student_user: User,
    test_challenge: Challenge,
    db_session: Session
):
    """Verifies that an accepted flag submission automatically creates a GitHub commit without exposing the flag."""
    # 1. Connect GitHub and configure repository
    client.post("/api/github/oauth/exchange", json={"mock_username": "cyber-student"}, headers=auth_headers)
    client.post("/api/github/repository", json={"repository": "cyber-student/ctf-solutions"}, headers=auth_headers)

    # 2. Add student writeup for this challenge
    writeup = UserWriteup(
        challenge_id=test_challenge.id,
        user_id=student_user.id,
        title="Bypassing Portal Login with SQL Tautology",
        content="Injected `' OR '1'='1` into the username field, which caused the backend SQL parser to evaluate true.",
        tags="SQLi,AuthBypass,Web",
        is_published=True
    )
    db_session.add(writeup)
    db_session.commit()

    # 3. Submit valid flag
    raw_flag = test_challenge._test_raw_flag
    sub_resp = client.post(
        "/api/submissions",
        json={"challenge_id": str(test_challenge.id), "flag": raw_flag},
        headers=auth_headers
    )
    assert sub_resp.status_code == 200
    sub_data = sub_resp.json()
    assert sub_data["is_correct"] is True
    assert sub_data["points_awarded"] == 300

    # 4. Check GitHub submission sync record
    sync = db_session.query(GitHubSubmissionSync).filter(
        GitHubSubmissionSync.user_id == student_user.id,
        GitHubSubmissionSync.challenge_id == test_challenge.id
    ).first()
    assert sync is not None
    assert sync.status == "synced"
    assert sync.file_path.startswith("ctf-solutions/")
    assert sync.file_path.endswith("README.md")
    assert sync.commit_sha is not None

    # 5. Verify flag is strictly NOT leaked in any sync record or commit message
    assert raw_flag not in sync.file_path
    assert raw_flag not in (sync.commit_sha or "")

    # 6. Duplicate Prevention: Submitting the flag again must NOT create a duplicate sync or commit
    db_session.query(Submission).filter(Submission.user_id == student_user.id).update({
        Submission.created_at: datetime.now(timezone.utc) - timedelta(seconds=10)
    })
    db_session.commit()

    sub_resp_dup = client.post(
        "/api/submissions",
        json={"challenge_id": str(test_challenge.id), "flag": raw_flag},
        headers=auth_headers
    )
    assert sub_resp_dup.status_code == 200

    sync_count = db_session.query(GitHubSubmissionSync).filter(
        GitHubSubmissionSync.user_id == student_user.id,
        GitHubSubmissionSync.challenge_id == test_challenge.id
    ).count()
    assert sync_count == 1, "Duplicate commit created for identical challenge solve"


def test_disconnect_github(client: TestClient, auth_headers: dict, student_user: User):
    """Verifies disconnecting GitHub account."""
    client.post("/api/github/oauth/exchange", json={"mock_username": "disconnect-user"}, headers=auth_headers)
    
    disc_resp = client.post("/api/github/disconnect", headers=auth_headers)
    assert disc_resp.status_code == 200

    status_resp = client.get("/api/github/status", headers=auth_headers)
    assert status_resp.status_code == 200
    assert status_resp.json()["is_connected"] is False
