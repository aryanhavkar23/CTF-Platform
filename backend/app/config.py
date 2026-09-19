from pathlib import Path
from typing import Optional, List
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    APP_ENV: Optional[str] = None
    DEBUG: bool = True

    # Database URLs
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/owasp_ctf"
    TEST_DATABASE_URL: Optional[str] = "sqlite:///./test.db"

    # Database Connection Pool (PostgreSQL)
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_TIMEOUT: int = 30

    # Security
    SECRET_KEY: str = "development_secret_key_please_change_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 15

    # Google OAuth 2.0 & College SSO (Phase 18)
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: Optional[str] = "http://localhost:8000/api/auth/oauth/google/callback"
    COLLEGE_EMAIL_DOMAINS: List[str] = [".edu", ".ac.in", ".edu.in", "owasp.org", "pccoepune.org"]

    # GitHub OAuth & Repository Sync Integration
    GITHUB_CLIENT_ID: Optional[str] = None
    GITHUB_CLIENT_SECRET: Optional[str] = None
    GITHUB_REDIRECT_URI: Optional[str] = "http://localhost:8000/api/github/oauth/callback"

    # CORS & Security Headers
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:5501",
        "http://127.0.0.1:5501",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ]
    CORS_ALLOW_CREDENTIALS: bool = True
    ENABLE_HSTS: bool = False

    # Challenge File Storage & Uploads
    MAX_FILE_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50 MB
    ALLOWED_FILE_EXTENSIONS: List[str] = [
        ".zip", ".tar.gz", ".tgz", ".pcap", ".pcapng", ".pdf", ".txt", ".bin",
        ".elf", ".exe", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".wav", ".mp3",
        ".raw", ".py", ".c", ".asm", ".json", ".md"
    ]

    # Submission & Rate Limiting
    SUBMISSION_RATE_LIMIT_PER_MINUTE: int = 10
    SUBMISSION_COOLDOWN_SECONDS: int = 2

    # Anti-Cheat & Submission Abuse Protection (Phase 14)
    SUBMISSION_RATE_LIMIT: int = 20
    SUBMISSION_RATE_WINDOW_SECONDS: int = 60
    FAILED_SUBMISSION_THRESHOLD: int = 15
    FAILED_SUBMISSION_WINDOW_SECONDS: int = 300
    REPEATED_CHALLENGE_ATTEMPT_THRESHOLD: int = 10
    REPEATED_CHALLENGE_ATTEMPT_WINDOW_SECONDS: int = 120
    RAPID_SOLVE_COUNT: int = 5
    RAPID_SOLVE_WINDOW_SECONDS: int = 60
    SECURITY_EVENT_COOLDOWN_SECONDS: int = 300

    # Teams
    MAX_TEAM_SIZE: int = 4

    # External Challenge URL (replaces Docker live challenges)
    CHALLENGE_HOST: str = "localhost"

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        """Strictly enforces security policies in production environments."""
        effective_env = (self.APP_ENV or self.ENVIRONMENT).lower()
        KNOWN_INSECURE_SECRETS = {
            "development_secret_key_please_change_in_production",
            "change_this_to_a_secure_random_secret_in_production_owasp_ctf_2026",
            "secret",
            "changeme",
            "password",
            "admin",
        }
        if effective_env == "production":
            # 1. Enforce strong, non-default SECRET_KEY
            if not self.SECRET_KEY or self.SECRET_KEY in KNOWN_INSECURE_SECRETS or "change_this" in self.SECRET_KEY.lower():
                raise ValueError(
                    "Production security violation: cannot use the default development secret for SECRET_KEY."
                )
            if len(self.SECRET_KEY) < 32:
                raise ValueError(
                    "Production security violation: SECRET_KEY must be at least 32 characters."
                )
            # 2. Forbid debug mode in production
            if self.DEBUG:
                raise ValueError(
                    "Production security violation: DEBUG must be set to False in production."
                )
            # 3. Forbid wildcard origins when credentials are enabled
            if ("*" in self.CORS_ORIGINS or any("*" in orig for orig in self.CORS_ORIGINS)) and self.CORS_ALLOW_CREDENTIALS:
                raise ValueError(
                    "Production security violation: Wildcard CORS origin '*' cannot be used with credentials in production."
                )
        return self

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE) if ENV_FILE.exists() else ".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
