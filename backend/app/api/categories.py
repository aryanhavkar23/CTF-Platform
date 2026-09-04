from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.challenge import CategoryResponse
from app.services.challenge_service import ChallengeService

router = APIRouter(prefix="/api/categories", tags=["Categories"])


@router.get("", response_model=List[CategoryResponse], status_code=status.HTTP_200_OK)
def list_categories(db: Session = Depends(get_db)):
    """Returns available challenge categories (auto-seeds defaults if empty)."""
    categories = ChallengeService.get_categories(db)
    if not categories:
        categories = ChallengeService.seed_categories(db)
    return categories
