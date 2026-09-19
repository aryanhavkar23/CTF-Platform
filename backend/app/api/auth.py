from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.user import UserRegisterRequest, UserResponse
from app.schemas.auth import (
    LoginRequest,
    TokenResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
    GoogleAuthUrlResponse,
    GoogleOAuthCallbackRequest,
)
from app.schemas.submission import UserScoreResponse
from app.services.auth_service import AuthService
from app.services.scoring_service import ScoringService
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


@router.get("/me/score", response_model=UserScoreResponse, status_code=status.HTTP_200_OK)
def get_my_score(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Returns the authenticated user's authoritative score and solve count."""
    total_score = ScoringService.get_user_score(db, current_user.id)
    solves_count = ScoringService.get_user_solve_count(db, current_user.id)
    return UserScoreResponse(
        user_id=current_user.id,
        username=current_user.username,
        total_points=total_score,
        solves_count=solves_count
    )


@router.post("/change-password", response_model=UserResponse, status_code=status.HTTP_200_OK)
def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Allows an authenticated user to change their security passphrase."""
    updated_user = AuthService.change_password(
        db=db,
        user=current_user,
        current_password=request.current_password,
        new_password=request.new_password
    )
    return updated_user


@router.post("/forgot-password", response_model=ForgotPasswordResponse, status_code=status.HTTP_200_OK)
def forgot_password(
    request: ForgotPasswordRequest,
    db: Session = Depends(get_db)
):
    """Requests a password reset link. Returns token directly in development/testing mode."""
    token = AuthService.request_password_reset(db, email=request.email)
    msg = "If the account exists, a password reset authorization has been generated."
    
    # In development or testing environment, return the token directly so users and test suites can use it
    expose_token = settings.DEBUG or settings.ENVIRONMENT != "production"
    return ForgotPasswordResponse(
        message=msg,
        reset_token=token if (expose_token and token) else None
    )


@router.post("/reset-password", response_model=UserResponse, status_code=status.HTTP_200_OK)
def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    """Applies a new password using a cryptographic single-use reset token."""
    updated_user = AuthService.reset_password(
        db=db,
        reset_token=request.reset_token,
        new_password=request.new_password
    )
    return updated_user


@router.get("/oauth/google/url", response_model=GoogleAuthUrlResponse, status_code=status.HTTP_200_OK)
def get_google_auth_url():
    """Generates the Google OAuth 2.0 authorization URL or mock URL in development."""
    if settings.GOOGLE_CLIENT_ID:
        import urllib.parse
        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "prompt": "select_account"
        }
        url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
    else:
        # Dev mock mode URL
        url = f"{settings.GOOGLE_REDIRECT_URI}?mock=true"

    return GoogleAuthUrlResponse(auth_url=url)


@router.post("/oauth/google/callback", response_model=TokenResponse, status_code=status.HTTP_200_OK)
def google_oauth_callback(
    request: GoogleOAuthCallbackRequest,
    db: Session = Depends(get_db)
):
    """Exchanges Google OAuth credentials or mock dev tokens for platform JWT and user session."""
    email = None
    sub = None
    name = None
    college = None

    # Handle local dev/testing mock simulation if configured or explicitly requested
    if request.mock_email or (not settings.GOOGLE_CLIENT_ID and not request.code and not request.id_token):
        email = str(request.mock_email or "student.scholar@university.edu").lower()
        sub = request.mock_sub or f"mock_google_{email}"
        name = request.mock_name or email.split("@")[0].title()
        college = "OWASP Collegiate Chapter"
    elif request.code and settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET:
        import urllib.request
        import urllib.parse
        import json

        token_url = "https://oauth2.googleapis.com/token"
        token_data = urllib.parse.urlencode({
            "code": request.code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code"
        }).encode("utf-8")

        req = urllib.request.Request(token_url, data=token_data, method="POST")
        try:
            with urllib.request.urlopen(req) as resp:
                token_res = json.loads(resp.read().decode("utf-8"))
                access_token = token_res.get("access_token")

                userinfo_url = f"https://www.googleapis.com/oauth2/v3/userinfo?access_token={access_token}"
                with urllib.request.urlopen(userinfo_url) as userinfo_resp:
                    profile = json.loads(userinfo_resp.read().decode("utf-8"))
                    email = profile.get("email")
                    sub = profile.get("sub")
                    name = profile.get("name")
        except Exception as e:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail=f"Google OAuth exchange failed: {str(e)}")
    elif request.id_token:
        # Direct ID token verification
        import urllib.request
        import json
        verify_url = f"https://oauth2.googleapis.com/tokeninfo?id_token={request.id_token}"
        try:
            with urllib.request.urlopen(verify_url) as resp:
                tokeninfo = json.loads(resp.read().decode("utf-8"))
                email = tokeninfo.get("email")
                sub = tokeninfo.get("sub")
                name = tokeninfo.get("name")
        except Exception as e:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail=f"Google ID token verification failed: {str(e)}")
    else:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Google OAuth credentials or authorization code"
        )

    if not email:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to extract verified email from Google identity"
        )

    user = AuthService.authenticate_or_register_oauth(
        db=db,
        provider="google",
        oauth_id=sub or f"google_{email}",
        email=email,
        name=name,
        college=college
    )

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
