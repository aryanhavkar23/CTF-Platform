from typing import Optional, List, Union
from uuid import UUID
from fastapi import APIRouter, Depends, status, Query, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.models.challenge import ChallengeDifficulty
from app.schemas.challenge import (
    ChallengeCreate,
    ChallengeUpdate,
    ChallengeResponse,
    ChallengeAdminResponse,
    ChallengeFileResponse,
    HintCreate,
    HintUpdate,
    HintResponse,
    WriteupCreate,
    WriteupResponse,
)
from app.services.challenge_service import ChallengeService
from app.services.storage_service import storage_service
from app.api.deps import require_role, get_current_user_optional, get_current_active_user

router = APIRouter(prefix="/api/challenges", tags=["Challenges"])


@router.get("", response_model=List[Union[ChallengeAdminResponse, ChallengeResponse]], status_code=status.HTTP_200_OK)
def list_challenges(
    category_id: Optional[UUID] = Query(None, description="Filter by category ID"),
    difficulty: Optional[ChallengeDifficulty] = Query(None, description="Filter by difficulty"),
    is_active: Optional[bool] = Query(None, description="Filter by active status (Admin/Mod only)"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Lists challenges. Students and guests only see active challenges without flag information."""
    is_admin_or_mod = current_user is not None and current_user.role in [UserRole.MODERATOR, UserRole.ADMIN]
    
    challenges = ChallengeService.list_challenges(
        db=db,
        category_id=category_id,
        difficulty=difficulty,
        is_active=is_active if is_admin_or_mod else None,
        is_admin_or_mod=is_admin_or_mod
    )

    if is_admin_or_mod:
        return [ChallengeAdminResponse.model_validate(c) for c in challenges]
    return [ChallengeResponse.model_validate(c) for c in challenges]


@router.get("/{challenge_id}", response_model=Union[ChallengeAdminResponse, ChallengeResponse], status_code=status.HTTP_200_OK)
def get_challenge(
    challenge_id: UUID,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Returns challenge details. Flag and flag_hash are strictly stripped from student responses."""
    is_admin_or_mod = current_user is not None and current_user.role in [UserRole.MODERATOR, UserRole.ADMIN]
    challenge = ChallengeService.get_challenge(db, challenge_id, is_admin_or_mod=is_admin_or_mod)

    if is_admin_or_mod:
        return ChallengeAdminResponse.model_validate(challenge)
    return ChallengeResponse.model_validate(challenge)


@router.post("", response_model=ChallengeAdminResponse, status_code=status.HTTP_201_CREATED)
def create_challenge(
    request: ChallengeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.MODERATOR, UserRole.ADMIN)),
):
    """Creates a new challenge. Restricted to moderators and administrators."""
    challenge = ChallengeService.create_challenge(db, request)
    return ChallengeAdminResponse.model_validate(challenge)


@router.patch("/{challenge_id}", response_model=ChallengeAdminResponse, status_code=status.HTTP_200_OK)
def update_challenge(
    challenge_id: UUID,
    request: ChallengeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.MODERATOR, UserRole.ADMIN)),
):
    """Updates an existing challenge. Restricted to moderators and administrators."""
    challenge = ChallengeService.update_challenge(db, challenge_id, request)
    return ChallengeAdminResponse.model_validate(challenge)


@router.delete("/{challenge_id}", status_code=status.HTTP_200_OK)
def delete_challenge(
    challenge_id: UUID,
    hard: bool = Query(False, description="Set true for permanent delete, false for safe deactivation"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.MODERATOR, UserRole.ADMIN)),
):
    """Safely deactivates (or hard deletes) a challenge. Restricted to moderators and administrators."""
    result = ChallengeService.deactivate_challenge(db, challenge_id, hard=hard)
    return result


# Hints Management

@router.post("/{challenge_id}/hints", response_model=HintResponse, status_code=status.HTTP_201_CREATED)
def add_hint(
    challenge_id: UUID,
    request: HintCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.MODERATOR, UserRole.ADMIN)),
):
    """Adds a hint to a challenge. Restricted to moderators and administrators."""
    hint = ChallengeService.add_hint(db, challenge_id, request)
    return HintResponse.model_validate(hint)


@router.patch("/{challenge_id}/hints/{hint_id}", response_model=HintResponse, status_code=status.HTTP_200_OK)
def update_hint(
    challenge_id: UUID,
    hint_id: UUID,
    request: HintUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.MODERATOR, UserRole.ADMIN)),
):
    """Updates a hint. Restricted to moderators and administrators."""
    hint = ChallengeService.update_hint(db, hint_id, request)
    return HintResponse.model_validate(hint)


@router.delete("/{challenge_id}/hints/{hint_id}", status_code=status.HTTP_200_OK)
def delete_hint(
    challenge_id: UUID,
    hint_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.MODERATOR, UserRole.ADMIN)),
):
    """Deletes a hint. Restricted to moderators and administrators."""
    ChallengeService.delete_hint(db, hint_id)
    return {"status": "deleted", "hint_id": str(hint_id)}


# Writeups Management

@router.post("/{challenge_id}/writeup", response_model=WriteupResponse, status_code=status.HTTP_200_OK)
def set_writeup(
    challenge_id: UUID,
    request: WriteupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.MODERATOR, UserRole.ADMIN)),
):
    """Creates or updates a challenge writeup. Restricted to moderators and administrators."""
    writeup = ChallengeService.create_or_update_writeup(db, challenge_id, request)
    return WriteupResponse.model_validate(writeup)


@router.get("/{challenge_id}/writeup", response_model=WriteupResponse, status_code=status.HTTP_200_OK)
def get_writeup(
    challenge_id: UUID,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Retrieves writeup according to visibility rules. Non-public writeups reject students with 403."""
    is_admin_or_mod = current_user is not None and current_user.role in [UserRole.MODERATOR, UserRole.ADMIN]
    writeup = ChallengeService.get_writeup(db, challenge_id, is_admin_or_mod=is_admin_or_mod)
    return WriteupResponse.model_validate(writeup)


# Challenge Files

@router.post("/{challenge_id}/files", response_model=ChallengeFileResponse, status_code=status.HTTP_201_CREATED)
async def upload_challenge_file(
    challenge_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.MODERATOR, UserRole.ADMIN)),
):
    """Uploads an attachment file for a challenge. Restricted to moderators and administrators."""
    file_bytes = await file.read()
    file_record = ChallengeService.add_challenge_file(db, challenge_id, file.filename, file_bytes)
    return ChallengeFileResponse.model_validate(file_record)


@router.get("/{challenge_id}/files/{file_id}/download")
def download_challenge_file(
    challenge_id: UUID,
    file_id: UUID,
    db: Session = Depends(get_db),
):
    """Downloads challenge file safely without path traversal or internal disk path disclosure."""
    file_rec = ChallengeService.get_challenge_file(db, file_id)
    if file_rec.challenge_id != challenge_id:
        raise HTTPException(status_code=404, detail="File does not belong to this challenge")

    file_path = storage_service.get_file_path(file_rec.storage_path)
    return FileResponse(
        path=str(file_path),
        filename=file_rec.filename,
        media_type="application/octet-stream"
    )
