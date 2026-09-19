from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.leaderboard import LeaderboardResponse, UserRankResponse
from app.services.leaderboard_service import LeaderboardService
from app.api.deps import get_current_active_user, get_current_user_optional

router = APIRouter(prefix="/api/leaderboard", tags=["Leaderboard"])


@router.get("", response_model=LeaderboardResponse, include_in_schema=False)
@router.get("/global", response_model=LeaderboardResponse)
def get_global_leaderboard(
    category: Optional[str] = Query(None, description="Optional category filter (e.g. Web Exploitation)"),
    time_frame: Optional[str] = Query("all_time", description="Time filter: all_time, today, this_week, this_month"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    db: Session = Depends(get_db),
):
    """Returns the authoritative global leaderboard with deterministic ranking."""
    try:
        return LeaderboardService.get_global_leaderboard(
            db=db,
            category_name=category,
            time_frame=time_frame,
            page=page,
            page_size=page_size,
        )
    except ValueError as e:
        msg = str(e)
        if "not found" in msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)


@router.get("/college", response_model=LeaderboardResponse)
def get_college_leaderboard(
    college: Optional[str] = Query(None, description="College name to filter rankings"),
    category: Optional[str] = Query(None, description="Optional category filter"),
    time_frame: Optional[str] = Query("all_time", description="Time filter: all_time, today, this_week, this_month"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Returns the college-specific leaderboard.
    
    If college parameter is omitted, uses the authenticated user's registered college,
    or defaults to the primary campus node.
    """
    target_college = college
    if not target_college:
        if current_user and current_user.college and current_user.college.strip():
            target_college = current_user.college
        else:
            target_college = "PCCOE"

    try:
        return LeaderboardService.get_college_leaderboard(
            db=db,
            college_name=target_college,
            category_name=category,
            time_frame=time_frame,
            page=page,
            page_size=page_size,
        )
    except ValueError as e:
        msg = str(e)
        if "not found" in msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)


@router.get("/me", response_model=UserRankResponse)
def get_my_rank(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Returns the authenticated user's global and college rank with total score."""
    return LeaderboardService.get_user_rank(db=db, user=current_user)
