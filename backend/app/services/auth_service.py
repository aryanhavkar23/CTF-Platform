import re
import secrets
from uuid import UUID
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.config import settings
from app.models.user import User, UserRole
from app.schemas.user import UserRegisterRequest
from app.core.security import (
    hash_password,
    verify_password,
    create_password_reset_token,
    verify_password_reset_token,
)


class AuthService:
    """Authoritative business logic for user registration, authentication, OAuth, and credential management."""

    @staticmethod
    def is_college_email(email: str) -> bool:
        """Determines whether an email originates from an accredited collegiate or institutional domain."""
        clean_email = email.lower().strip()
        if not settings.COLLEGE_EMAIL_DOMAINS:
            return False
        return any(clean_email.endswith(domain.lower()) for domain in settings.COLLEGE_EMAIL_DOMAINS)

    @staticmethod
    def register_user(db: Session, request: UserRegisterRequest) -> User:
        # Check email uniqueness
        existing_email = db.query(User).filter(User.email == request.email.lower()).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Check username uniqueness
        existing_username = db.query(User).filter(User.username == request.username).first()
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )

        # Hash password securely
        password_hash = hash_password(request.password)
        is_collegiate = AuthService.is_college_email(request.email)

        # Extract GitHub username from validated URL
        github_username = None
        if request.github_profile_url:
            parts = request.github_profile_url.rstrip("/").split("/")
            if parts:
                github_username = parts[-1]

        # Create user - explicitly enforced as STUDENT
        new_user = User(
            username=request.username,
            email=request.email.lower(),
            hashed_password=password_hash,
            role=UserRole.STUDENT,
            college=request.college,
            github_profile_url=request.github_profile_url,
            github_username=github_username,
            is_active=True,
            is_verified=is_collegiate
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user

    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> User:
        user = db.query(User).filter(User.email == email.lower()).first()
        
        # Generic error message avoids user enumeration
        if not user or not user.hashed_password or not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"}
            )

        if not user.is_active or user.is_banned:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is suspended or disabled"
            )

        return user

    @staticmethod
    def change_password(db: Session, user: User, current_password: str, new_password: str) -> User:
        """Allows an authenticated user to update their passphrase with validation."""
        if user.hashed_password:
            if not verify_password(current_password, user.hashed_password):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Incorrect current password"
                )

        user.hashed_password = hash_password(new_password)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def request_password_reset(db: Session, email: str) -> Optional[str]:
        """Generates a cryptographic signed password reset token for a valid account."""
        user = db.query(User).filter(User.email == email.lower()).first()
        if not user or not user.is_active or user.is_banned:
            # Mask existence of account
            return None

        token = create_password_reset_token(user.email, expires_minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)
        return token

    @staticmethod
    def reset_password(db: Session, reset_token: str, new_password: str) -> User:
        """Applies a new password using a validated single-use reset token."""
        email = verify_password_reset_token(reset_token)
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid, tampered, or expired password reset token"
            )

        user = db.query(User).filter(User.email == email).first()
        if not user or not user.is_active or user.is_banned:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User account is unavailable or deactivated"
            )

        user.hashed_password = hash_password(new_password)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def authenticate_or_register_oauth(
        db: Session,
        provider: str,
        oauth_id: str,
        email: str,
        name: Optional[str] = None,
        college: Optional[str] = None
    ) -> User:
        """Logs in an existing OAuth user or auto-provisions a new student operative."""
        clean_email = email.lower().strip()

        # 1. Search by provider and oauth_id
        user = db.query(User).filter(User.oauth_provider == provider, User.oauth_id == oauth_id).first()

        # 2. If not found, search by email to link account
        if not user:
            user = db.query(User).filter(User.email == clean_email).first()
            if user:
                user.oauth_provider = provider
                user.oauth_id = oauth_id
                if name and not user.name:
                    user.name = name
                if college and not user.college:
                    user.college = college
                db.add(user)
                db.commit()
                db.refresh(user)

        # 3. If still not found, auto-provision new account
        if not user:
            # Generate clean username from email or name
            base_handle = re.sub(r"[^a-zA-Z0-9_-]", "", clean_email.split("@")[0]) or "operative"
            candidate_username = base_handle[:40]
            
            # Ensure uniqueness
            suffix = 1
            while db.query(User).filter(User.username == candidate_username).first():
                candidate_username = f"{base_handle[:35]}_{suffix}"
                suffix += 1

            is_collegiate = AuthService.is_college_email(clean_email)
            user = User(
                username=candidate_username,
                email=clean_email,
                hashed_password=None,  # Pure OAuth login
                oauth_provider=provider,
                oauth_id=oauth_id,
                name=name,
                college=college,
                role=UserRole.STUDENT,
                is_active=True,
                is_verified=is_collegiate
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        if not user.is_active or user.is_banned:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is suspended or disabled"
            )

        return user

    @staticmethod
    def get_user_by_id(db: Session, user_id: UUID) -> Optional[User]:
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email.lower()).first()
