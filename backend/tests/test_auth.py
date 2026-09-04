from datetime import timedelta
from uuid import uuid4
import pytest
from app.models.user import User, UserRole
from app.core.security import hash_password, create_access_token


def test_successful_registration(client):
    """1. Successful user registration returns 201 and safe profile."""
    payload = {
        "username": "student_alice",
        "email": "alice@college.edu",
        "password": "SecurePassword123!",
        "college": "OWASP College"
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "student_alice"
    assert data["email"] == "alice@college.edu"
    assert data["role"] == "student"
    assert data["college"] == "OWASP College"
    assert data["is_active"] is True
    assert "id" in data
    assert "created_at" in data


def test_duplicate_email_registration(client):
    """2. Duplicate email registration is rejected with 400 Bad Request."""
    payload1 = {
        "username": "original_user",
        "email": "duplicate@college.edu",
        "password": "Password1234!"
    }
    res1 = client.post("/api/auth/register", json=payload1)
    assert res1.status_code == 201

    payload2 = {
        "username": "different_user",
        "email": "duplicate@college.edu",
        "password": "Password1234!"
    }
    res2 = client.post("/api/auth/register", json=payload2)
    assert res2.status_code == 400
    assert "Email already registered" in res2.json()["detail"]


def test_invalid_registration_data(client):
    """3. Invalid registration inputs (short password, invalid email) fail validation with 422."""
    # Short password (<8 chars)
    res_short_pw = client.post("/api/auth/register", json={
        "username": "valid_name",
        "email": "valid@college.edu",
        "password": "short"
    })
    assert res_short_pw.status_code == 422

    # Malformed email
    res_bad_email = client.post("/api/auth/register", json={
        "username": "valid_name",
        "email": "not-an-email",
        "password": "ValidPassword123!"
    })
    assert res_bad_email.status_code == 422

    # Invalid username format (special characters)
    res_bad_username = client.post("/api/auth/register", json={
        "username": "user!@#$",
        "email": "valid@college.edu",
        "password": "ValidPassword123!"
    })
    assert res_bad_username.status_code == 422


def test_successful_login(client):
    """4. Successful login returns access token and user information."""
    # Register user
    client.post("/api/auth/register", json={
        "username": "login_user",
        "email": "login@college.edu",
        "password": "CorrectPassword123!"
    })

    # Login
    response = client.post("/api/auth/login", json={
        "email": "login@college.edu",
        "password": "CorrectPassword123!"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "login@college.edu"
    assert data["user"]["username"] == "login_user"


def test_incorrect_password(client):
    """5. Incorrect password returns 401 with generic error."""
    client.post("/api/auth/register", json={
        "username": "login_pw_test",
        "email": "wrongpw@college.edu",
        "password": "CorrectPassword123!"
    })

    response = client.post("/api/auth/login", json={
        "email": "wrongpw@college.edu",
        "password": "WrongPassword123!"
    })
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_nonexistent_email(client):
    """6. Nonexistent email returns 401 with generic error (no user enumeration)."""
    response = client.post("/api/auth/login", json={
        "email": "nobody@college.edu",
        "password": "AnyPassword123!"
    })
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_missing_authentication_token(client):
    """7. Missing authentication token on protected route is rejected with 401."""
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert "detail" in response.json()


def test_invalid_token(client):
    """8. Invalid or malformed token is rejected with 401."""
    headers = {"Authorization": "Bearer invalid.fake.token"}
    response = client.get("/api/auth/me", headers=headers)
    assert response.status_code == 401
    assert "Could not validate credentials" in response.json()["detail"]


def test_expired_token(client, db_session):
    """9. Expired JWT token is rejected with 401."""
    user = User(
        username="expired_test_user",
        email="expired@college.edu",
        hashed_password=hash_password("pw123456"),
        role=UserRole.STUDENT
    )
    db_session.add(user)
    db_session.flush()

    # Generate token already expired in the past
    expired_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role.value},
        expires_delta=timedelta(minutes=-15)
    )

    headers = {"Authorization": f"Bearer {expired_token}"}
    response = client.get("/api/auth/me", headers=headers)
    assert response.status_code == 401
    assert "Token has expired" in response.json()["detail"]


def test_authenticated_me_request(client):
    """10. Authenticated /me request returns current user profile."""
    # Register and login
    client.post("/api/auth/register", json={
        "username": "me_user",
        "email": "me@college.edu",
        "password": "Password1234!"
    })
    login_res = client.post("/api/auth/login", json={
        "email": "me@college.edu",
        "password": "Password1234!"
    })
    token = login_res.json()["access_token"]

    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "me_user"
    assert data["email"] == "me@college.edu"


def test_student_accessing_student_endpoint(client):
    """11. Student can access student-permitted endpoints."""
    client.post("/api/auth/register", json={
        "username": "student_dan",
        "email": "dan@college.edu",
        "password": "Password1234!"
    })
    login_res = client.post("/api/auth/login", json={
        "email": "dan@college.edu",
        "password": "Password1234!"
    })
    token = login_res.json()["access_token"]

    response = client.get("/api/auth/test/student", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["role"] == "student"


def test_student_attempting_admin_operation(client):
    """12. Student attempting admin operation is rejected with 403 Forbidden."""
    client.post("/api/auth/register", json={
        "username": "student_hacker",
        "email": "hacker@college.edu",
        "password": "Password1234!"
    })
    login_res = client.post("/api/auth/login", json={
        "email": "hacker@college.edu",
        "password": "Password1234!"
    })
    token = login_res.json()["access_token"]

    response = client.get("/api/auth/test/admin", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
    assert "Insufficient permissions" in response.json()["detail"]


def test_moderator_permissions(client, db_session):
    """13. Moderator can access moderator endpoints, but is denied admin endpoints."""
    mod_user = User(
        username="mod_pat",
        email="mod@college.edu",
        hashed_password=hash_password("Password1234!"),
        role=UserRole.MODERATOR
    )
    db_session.add(mod_user)
    db_session.flush()

    token = create_access_token(
        data={"sub": str(mod_user.id), "email": mod_user.email, "role": mod_user.role.value}
    )
    headers = {"Authorization": f"Bearer {token}"}

    # Can access student probe
    res_student = client.get("/api/auth/test/student", headers=headers)
    assert res_student.status_code == 200

    # Can access moderator probe
    res_mod = client.get("/api/auth/test/moderator", headers=headers)
    assert res_mod.status_code == 200
    assert res_mod.json()["role"] == "moderator"

    # CANNOT access admin probe
    res_admin = client.get("/api/auth/test/admin", headers=headers)
    assert res_admin.status_code == 403
    assert "Insufficient permissions" in res_admin.json()["detail"]


def test_admin_permissions(client, db_session):
    """14. Admin has full permissions across student, moderator, and admin endpoints."""
    admin_user = User(
        username="admin_super",
        email="admin@college.edu",
        hashed_password=hash_password("AdminPass123!"),
        role=UserRole.ADMIN
    )
    db_session.add(admin_user)
    db_session.flush()

    token = create_access_token(
        data={"sub": str(admin_user.id), "email": admin_user.email, "role": admin_user.role.value}
    )
    headers = {"Authorization": f"Bearer {token}"}

    # Admin accesses student probe
    res_student = client.get("/api/auth/test/student", headers=headers)
    assert res_student.status_code == 200

    # Admin accesses moderator probe
    res_mod = client.get("/api/auth/test/moderator", headers=headers)
    assert res_mod.status_code == 200

    # Admin accesses admin probe
    res_admin = client.get("/api/auth/test/admin", headers=headers)
    assert res_admin.status_code == 200
    assert res_admin.json()["role"] == "admin"


def test_password_hash_never_exposed(client):
    """15. Password hash is never exposed in register, login, or /me response payloads."""
    # 1. Check registration response
    reg_res = client.post("/api/auth/register", json={
        "username": "safe_user",
        "email": "safe@college.edu",
        "password": "MySecretPassword123!"
    })
    reg_data = reg_res.json()
    assert "password" not in reg_data
    assert "hashed_password" not in reg_data
    assert "password_hash" not in reg_data

    # 2. Check login response
    login_res = client.post("/api/auth/login", json={
        "email": "safe@college.edu",
        "password": "MySecretPassword123!"
    })
    login_data = login_res.json()
    assert "password" not in login_data["user"]
    assert "hashed_password" not in login_data["user"]
    assert "password_hash" not in login_data["user"]

    # 3. Check /me response
    token = login_data["access_token"]
    me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    me_data = me_res.json()
    assert "password" not in me_data
    assert "hashed_password" not in me_data
    assert "password_hash" not in me_data
