import logging
import uuid
from pathlib import Path

from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.config import settings
from app.database import get_db
from app.api.auth import router as auth_router
from app.api.categories import router as categories_router
from app.api.challenges import router as challenges_router
from app.api.submissions import router as submissions_router
from app.api.leaderboard import router as leaderboard_router
from app.api.teams import router as teams_router
from app.api.events import router as events_router
from app.api.profile import router as profile_router
from app.api.badges import router as badges_router
from app.api.discussions import router as discussions_router
from app.api.notifications import router as notifications_router
from app.api.analytics import router as analytics_router
from app.api.anti_cheat import router as anti_cheat_router
from app.api.admin_users import router as admin_users_router
from app.api.community_writeups import router as community_writeups_router
from app.api.follows import router as follows_router
from app.api.github import router as github_router

logger = logging.getLogger(__name__)

app = FastAPI(
    title="College OWASP CTF Platform API",
    description="Production-oriented CTF platform API for College OWASP Club",
    version="0.1.0",
    docs_url="/docs" if settings.DEBUG or settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.DEBUG or settings.ENVIRONMENT != "production" else None
)


# 1. Request ID Correlation Middleware
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# 2. HTTP Security Headers Middleware
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = (
        "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
        "magnetometer=(), microphone=(), payment=(), usb=()"
    )
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "img-src 'self' data: https:; "
        "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com data:; "
        "connect-src 'self' http: https: ws: wss:;"
    )
    if settings.ENABLE_HSTS:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    if settings.ENVIRONMENT != "production":
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


# 3. CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if settings.CORS_ORIGINS else ["*"],
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 4. Global Exception Handler (Masks internal stack traces in non-debug mode)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(
        "Unhandled server error [request_id=%s] on %s %s: %s",
        request_id, request.method, request.url.path, exc,
        exc_info=True
    )
    if settings.DEBUG:
        detail = str(exc)
    else:
        detail = "An internal server error occurred."

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": detail, "request_id": request_id},
        headers={"X-Request-ID": request_id}
    )


# Mount API routes
app.include_router(auth_router)
app.include_router(categories_router)
app.include_router(challenges_router)
app.include_router(submissions_router)
app.include_router(leaderboard_router)
app.include_router(teams_router, prefix="/api/teams", tags=["Teams"])
app.include_router(events_router, prefix="/api/events", tags=["Events"])
app.include_router(profile_router)
app.include_router(badges_router)
app.include_router(discussions_router)
app.include_router(notifications_router)
app.include_router(analytics_router)
app.include_router(anti_cheat_router)
app.include_router(admin_users_router)
app.include_router(community_writeups_router)
app.include_router(follows_router)
app.include_router(github_router)


# 5. Production Health & Readiness Probes
@app.get("/health", tags=["Health"])
def health_liveness():
    """Service liveness probe (RFC/Kubernetes standard)."""
    return {
        "status": "ok",
        "service": "owasp-ctf-backend",
        "environment": settings.ENVIRONMENT
    }


@app.get("/health/ready", tags=["Health"])
def health_readiness(db: Session = Depends(get_db)):
    """Service readiness probe checking database connectivity."""
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "ready",
            "database": "connected"
        }
    except Exception as e:
        logger.error("Readiness check failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not ready: database connection unavailable."
        )


@app.get("/api/health", tags=["Health"])
def health_check():
    """Backwards-compatible health probe."""
    return {
        "status": "healthy",
        "service": "owasp-ctf-backend",
        "environment": settings.ENVIRONMENT
    }


# Serve minimal functional testing frontend
FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
    if (FRONTEND_DIR / "css").exists():
        app.mount("/css", StaticFiles(directory=str(FRONTEND_DIR / "css")), name="css")
    if (FRONTEND_DIR / "js").exists():
        app.mount("/js", StaticFiles(directory=str(FRONTEND_DIR / "js")), name="js")

    @app.get("/", include_in_schema=False)
    def serve_frontend():
        index_file = FRONTEND_DIR / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"message": "OWASP CTF Platform API is running. See /docs for Swagger UI."}

