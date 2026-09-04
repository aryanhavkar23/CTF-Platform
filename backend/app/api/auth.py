from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.user import UserRegisterRequest, UserResponse
from app.schemas.auth import LoginRequest, TokenResponse
from app.services.auth_service import AuthService
from app.core.security import create_access_token
from app.api.deps import get_current_active_user, require_role

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    request: UserRegisterRequest,
    db: Session = Depends(get_db)
):
    """Registers a new student user. Role assignment is locked to student."""
    user = AuthService.register_user(db, request)
    return user


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """Authenticates credentials and returns a signed JWT access token with profile."""
    user = AuthService.authenticate_user(db, email=request.email, password=request.password)
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "role": user.role.value
        }
    )
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


@router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
def get_me(
    current_user: User = Depends(get_current_active_user)
):
    """Returns the authenticated user's profile. Rejects unauthenticated callers."""
    return current_user


# Role-Based Authorization Probes (Used for RBAC testing and verification)

@router.get("/test/student", status_code=status.HTTP_200_OK)
def test_student_access(
    current_user: User = Depends(require_role(UserRole.STUDENT, UserRole.MODERATOR, UserRole.ADMIN))
):
    """Endpoint accessible by students, moderators, and admins."""
    return {
        "status": "success",
        "message": "Student access verified",
        "user": current_user.username,
        "role": current_user.role.value
    }


@router.get("/test/moderator", status_code=status.HTTP_200_OK)
def test_moderator_access(
    current_user: User = Depends(require_role(UserRole.MODERATOR, UserRole.ADMIN))
):
    """Endpoint accessible only by moderators and admins."""
    return {
        "status": "success",
        "message": "Moderator access verified",
        "user": current_user.username,
        "role": current_user.role.value
    }


@router.get("/test/admin", status_code=status.HTTP_200_OK)
def test_admin_access(
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    """Endpoint strictly accessible only by administrators."""
    return {
        "status": "success",
        "message": "Admin access verified",
        "user": current_user.username,
        "role": current_user.role.value
    }
