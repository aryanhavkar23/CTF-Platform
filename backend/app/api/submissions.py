from typing import List
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.submission import (
    SubmissionCreate,
    SubmissionResponse,
    SubmissionHistoryResponse,
)
from app.services.submission_service import SubmissionService
from app.api.deps import get_current_active_user

router = APIRouter(prefix="/api/submissions", tags=["Submissions"])


@router.post("", response_model=SubmissionResponse, status_code=status.HTTP_200_OK)
def submit_flag(
    request: SubmissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Submits a challenge flag. User identity is strictly derived from JWT session."""
    result = SubmissionService.process_submission(
        db=db,
        user=current_user,
        challenge_id=request.challenge_id,
        submitted_flag=request.flag
    )
    sub = result["submission"]
    return SubmissionResponse(
        id=sub.id,
        challenge_id=sub.challenge_id,
        is_correct=result["is_correct"],
        points_awarded=result["points_awarded"],
        message=result["message"],
        created_at=sub.created_at
    )


@router.get("/me", response_model=List[SubmissionHistoryResponse], status_code=status.HTTP_200_OK)
def get_my_submissions(
    limit: int = Query(50, ge=1, le=100, description="Max records to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Returns authenticated user's personal flag submission history."""
    history = SubmissionService.get_user_submissions(
        db=db,
        user_id=current_user.id,
        limit=limit
    )
    return history
