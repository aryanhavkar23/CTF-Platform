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
)
from app.schemas.hint import (
    HintCreate,
    HintUpdate,
    HintResponse,
    HintUsageResponse,
)
from app.schemas.writeup import (
    WriteupCreate,
    WriteupUpdate,
    WriteupResponse,
)
from app.schemas.submission import ChallengeStatusResponse
from app.services.challenge_service import ChallengeService
from app.services.hint_service import HintService
from app.services.writeup_service import WriteupService
from app.services.scoring_service import ScoringService
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


@router.get("/{challenge_id}/status", response_model=ChallengeStatusResponse, status_code=status.HTTP_200_OK)
def get_challenge_status(
    challenge_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Returns whether the authenticated user has solved, attempted, or not attempted the challenge."""
    # Ensure challenge exists
    ChallengeService.get_challenge(db, challenge_id, is_admin_or_mod=True)
    status_info = ScoringService.get_challenge_status(db, current_user.id, challenge_id)
    return ChallengeStatusResponse(
        challenge_id=status_info["challenge_id"],
        status=status_info["status"],
        points_earned=status_info["points_earned"],
        solved_at=status_info["solved_at"]
    )


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
    hint = HintService.create_hint(db, challenge_id, request)
    return HintResponse.model_validate(hint)


@router.get("/{challenge_id}/hints", response_model=List[HintResponse], status_code=status.HTTP_200_OK)
def list_hints(
    challenge_id: UUID,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Lists hints for a challenge. Content is hidden from students unless unlocked."""
    return HintService.get_hints_for_challenge(db, challenge_id, current_user)


@router.get("/{challenge_id}/hints/{hint_id}", response_model=HintResponse, status_code=status.HTTP_200_OK)
def get_hint(
    challenge_id: UUID,
    hint_id: UUID,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Retrieves a single hint. Content is hidden from students unless unlocked."""
    return HintService.get_hint(db, challenge_id, hint_id, current_user)


@router.put("/{challenge_id}/hints/{hint_id}", response_model=HintResponse, status_code=status.HTTP_200_OK)
@router.patch("/{challenge_id}/hints/{hint_id}", response_model=HintResponse, status_code=status.HTTP_200_OK)
def update_hint(
    challenge_id: UUID,
    hint_id: UUID,
    request: HintUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.MODERATOR, UserRole.ADMIN)),
):
    """Updates a hint. Restricted to moderators and administrators."""
    hint = HintService.update_hint(db, challenge_id, hint_id, request)
    return HintResponse.model_validate(hint)


@router.delete("/{challenge_id}/hints/{hint_id}", status_code=status.HTTP_200_OK)
def delete_hint(
    challenge_id: UUID,
    hint_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.MODERATOR, UserRole.ADMIN)),
):
    """Deletes a hint. Restricted to moderators and administrators."""
    HintService.delete_hint(db, challenge_id, hint_id)
    return {"status": "deleted", "hint_id": str(hint_id)}


@router.post("/{challenge_id}/hints/{hint_id}/use", response_model=HintUsageResponse, status_code=status.HTTP_200_OK)
def use_hint(
    challenge_id: UUID,
    hint_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Student unlocks a hint. Records point deduction and reveals hint content."""
    return HintService.use_hint(db, challenge_id, hint_id, current_user)


# Writeups Management

@router.post("/{challenge_id}/writeups", response_model=WriteupResponse, status_code=status.HTTP_200_OK)
@router.post("/{challenge_id}/writeup", response_model=WriteupResponse, status_code=status.HTTP_200_OK)
def set_writeup(
    challenge_id: UUID,
    request: WriteupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.MODERATOR, UserRole.ADMIN)),
):
    """Creates or updates a challenge writeup. Restricted to moderators and administrators."""
    writeup = WriteupService.create_or_update_writeup(db, challenge_id, request)
    return WriteupResponse.model_validate(writeup)


@router.get("/{challenge_id}/writeups", response_model=List[WriteupResponse], status_code=status.HTTP_200_OK)
def list_writeups(
    challenge_id: UUID,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Retrieves writeups for a challenge, enforcing visibility rules."""
    writeups = WriteupService.get_writeups_for_challenge(db, challenge_id, current_user)
    return [WriteupResponse.model_validate(w) for w in writeups]


@router.get("/{challenge_id}/writeup", response_model=WriteupResponse, status_code=status.HTTP_200_OK)
@router.get("/{challenge_id}/writeups/{writeup_id}", response_model=WriteupResponse, status_code=status.HTTP_200_OK)
def get_writeup(
    challenge_id: UUID,
    writeup_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Retrieves writeup according to visibility rules. Locked writeups reject students with 403."""
    writeup = WriteupService.get_writeup(db, challenge_id, user=current_user, writeup_id=writeup_id)
    return WriteupResponse.model_validate(writeup)


@router.put("/{challenge_id}/writeups/{writeup_id}", response_model=WriteupResponse, status_code=status.HTTP_200_OK)
@router.patch("/{challenge_id}/writeups/{writeup_id}", response_model=WriteupResponse, status_code=status.HTTP_200_OK)
def update_writeup(
    challenge_id: UUID,
    writeup_id: UUID,
    request: WriteupUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.MODERATOR, UserRole.ADMIN)),
):
    """Updates a challenge writeup. Restricted to moderators and administrators."""
    writeup = WriteupService.update_writeup(db, challenge_id, writeup_id, request)
    return WriteupResponse.model_validate(writeup)


@router.delete("/{challenge_id}/writeups/{writeup_id}", status_code=status.HTTP_200_OK)
@router.delete("/{challenge_id}/writeup", status_code=status.HTTP_200_OK)
def delete_writeup(
    challenge_id: UUID,
    writeup_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.MODERATOR, UserRole.ADMIN)),
):
    """Deletes a challenge writeup. Restricted to moderators and administrators."""
    WriteupService.delete_writeup(db, challenge_id, writeup_id)
    return {"status": "deleted"}


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
