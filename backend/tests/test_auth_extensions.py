import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.user import User, UserRole
from app.core.security import hash_password, create_access_token


@pytest.fixture
def test_user(db_session: Session) -> User:
    """Creates a standard verified active student user."""
    user = User(
        username="test_scholar",
        email="scholar@university.edu",
        hashed_password=hash_password("CurrentPassword123!"),
        role=UserRole.STUDENT,
        college="OWASP Collegiate Chapter",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user: User) -> dict:
    token = create_access_token(data={"sub": str(test_user.id), "email": test_user.email, "role": test_user.role.value})
    return {"Authorization": f"Bearer {token}"}


def test_collegiate_email_auto_verification(client: TestClient, db_session: Session):
    """Verify that collegiate domain emails automatically achieve verified status upon registration."""
    res_edu = client.post("/api/auth/register", json={
        "username": "edu_student",
        "email": "student@mit.edu",
        "password": "Password123!",
        "college": "MIT Cyber"
    })
    assert res_edu.status_code == 201
    assert res_edu.json()["is_verified"] is True

    res_std = client.post("/api/auth/register", json={
        "username": "gmail_student",
        "email": "student@generic.com",
        "password": "Password123!",
        "college": "Community Hub"
    })
    assert res_std.status_code == 201
    assert res_std.json()["is_verified"] is False


def test_change_password_success(client: TestClient, auth_headers: dict, test_user: User):
    """Test successful password change by authenticated user."""
    res = client.post("/api/auth/change-password", headers=auth_headers, json={
        "current_password": "CurrentPassword123!",
        "new_password": "NewSecretPassphrase999!"
    })
    assert res.status_code == 200

    # Old password should no longer work
    fail_res = client.post("/api/auth/login", json={
        "email": test_user.email,
        "password": "CurrentPassword123!"
    })
    assert fail_res.status_code == 401

    # New password works
    success_res = client.post("/api/auth/login", json={
        "email": test_user.email,
        "password": "NewSecretPassphrase999!"
    })
    assert success_res.status_code == 200
    assert "access_token" in success_res.json()


def test_change_password_invalid_current(client: TestClient, auth_headers: dict):
    """Test failure when current password does not match stored hash."""
    res = client.post("/api/auth/change-password", headers=auth_headers, json={
        "current_password": "WrongPassword!",
        "new_password": "NewSecretPassphrase999!"
    })
    assert res.status_code == 400
    assert "Incorrect current password" in res.json()["detail"]


def test_forgot_and_reset_password_lifecycle(client: TestClient, test_user: User):
    """Complete test of requesting a reset token, resetting password, and authenticating."""
    # 1. Request password reset
    res = client.post("/api/auth/forgot-password", json={
        "email": test_user.email
    })
    assert res.status_code == 200
    data = res.json()
    assert "reset_token" in data
    token = data["reset_token"]
    assert token is not None

    # 2. Reset password using token
    res_reset = client.post("/api/auth/reset-password", json={
        "reset_token": token,
        "new_password": "BrandNewPassphrase123!"
    })
    assert res_reset.status_code == 200

    # 3. Authenticate with newly set password
    login_res = client.post("/api/auth/login", json={
        "email": test_user.email,
        "password": "BrandNewPassphrase123!"
    })
    assert login_res.status_code == 200


def test_reset_password_invalid_token(client: TestClient):
    """Test rejection when submitting an invalid or forged token."""
    res = client.post("/api/auth/reset-password", json={
        "reset_token": "forged.or.invalid.token",
        "new_password": "BrandNewPassphrase123!"
    })
    assert res.status_code == 400
    assert "Invalid" in res.json()["detail"]


def test_google_auth_url(client: TestClient):
    """Test retrieval of Google OAuth redirect URL."""
    res = client.get("/api/auth/oauth/google/url")
    assert res.status_code == 200
    assert "auth_url" in res.json()


def test_google_oauth_provisioning_new_user(client: TestClient, db_session: Session):
    """Test auto-provisioning a new student account via Google OAuth callback."""
    res = client.post("/api/auth/oauth/google/callback", json={
        "mock_email": "fresh_operative@stanford.edu",
        "mock_name": "Fresh Operative",
        "mock_sub": "google_sub_1092830192"
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    user_info = data["user"]
    assert user_info["email"] == "fresh_operative@stanford.edu"
    assert user_info["role"] == "student"
    assert user_info["is_verified"] is True  # .edu domain


def test_google_oauth_account_linking(client: TestClient, test_user: User):
    """Test linking Google OAuth identity to an existing account with matching email."""
    res = client.post("/api/auth/oauth/google/callback", json={
        "mock_email": test_user.email,
        "mock_name": "Linked Scholar",
        "mock_sub": "google_sub_883719"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["user"]["id"] == str(test_user.id)


def test_google_oauth_banned_user_rejection(client: TestClient, db_session: Session):
    """Test that suspended accounts cannot bypass security checks via OAuth."""
    banned_user = User(
        username="rogue_agent",
        email="rogue@darknet.org",
        hashed_password=None,
        oauth_provider="google",
        oauth_id="google_rogue_999",
        role=UserRole.STUDENT,
        is_active=True,
        is_banned=True
    )
    db_session.add(banned_user)
    db_session.commit()

    res = client.post("/api/auth/oauth/google/callback", json={
        "mock_email": "rogue@darknet.org",
        "mock_sub": "google_rogue_999"
    })
    assert res.status_code == 403
