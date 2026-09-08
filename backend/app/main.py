from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
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

app = FastAPI(
    title="College OWASP CTF Platform API",
    description="Production-oriented CTF platform API for College OWASP Club",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for frontend clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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



@app.get("/api/health", tags=["Health"])
def health_check():
    """Service health probe."""
    return {
        "status": "healthy",
        "service": "owasp-ctf-backend",
        "environment": settings.ENVIRONMENT
    }


# Serve minimal functional testing frontend
FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/", include_in_schema=False)
    def serve_frontend():
        index_file = FRONTEND_DIR / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"message": "OWASP CTF Platform API is running. See /docs for Swagger UI."}
