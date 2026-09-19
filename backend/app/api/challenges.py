from typing import Optional, List, Union
from uuid import UUID
from fastapi import APIRouter, Depends, status, Query, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User, UserRole
from app.models.challenge import Challenge, ChallengeDifficulty, ChallengeWriteup
from app.models.solve import Solve
from app.models.submission import Submission
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
from app.schemas.submission import ChallengeStatusResponse, SubmissionResponse, SubmissionCreate
from app.services.challenge_service import ChallengeService
from app.services.hint_service import HintService
from app.services.writeup_service import WriteupService
from app.services.scoring_service import ScoringService
from app.services.submission_service import SubmissionService
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

    solved_map = {}
    if current_user:
        user_solves = db.query(Solve).filter(Solve.user_id == current_user.id).all()
        for s in user_solves:
            solved_map[s.challenge_id] = s.points_awarded

    from sqlalchemy import func
    solves_counts = dict(
        db.query(Solve.challenge_id, func.count(Solve.id))
        .group_by(Solve.challenge_id)
        .all()
    )

    result = []
    for c in challenges:
        if is_admin_or_mod:
            item = ChallengeAdminResponse.model_validate(c)
        else:
            item = ChallengeResponse.model_validate(c)
        
        is_solved = c.id in solved_map
        item.is_solved = is_solved
        item.points_awarded = solved_map.get(c.id)
        item.is_surrendered = is_solved and solved_map.get(c.id) == 0
        item.solves_count = solves_counts.get(c.id, 0)
        result.append(item)

    return result


@router.get("/{challenge_id}", response_model=Union[ChallengeAdminResponse, ChallengeResponse], status_code=status.HTTP_200_OK)
def get_challenge(
    challenge_id: UUID,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Returns challenge details. Flag and flag_hash are strictly stripped from student responses."""
    is_admin_or_mod = current_user is not None and current_user.role in [UserRole.MODERATOR, UserRole.ADMIN]
    challenge = ChallengeService.get_challenge(db, challenge_id, is_admin_or_mod=is_admin_or_mod)
    safe_hints = HintService.get_hints_for_challenge(db, challenge_id, current_user)

    solve = None
    if current_user:
        solve = db.query(Solve).filter(Solve.user_id == current_user.id, Solve.challenge_id == challenge_id).first()

    from sqlalchemy import func
    total_solves = db.query(func.count(Solve.id)).filter(Solve.challenge_id == challenge_id).scalar() or 0

    writeup = db.query(ChallengeWriteup).filter(ChallengeWriteup.challenge_id == challenge_id).first()
    writeup_text = None
    if solve:
        if writeup and writeup.content:
            writeup_text = writeup.content
        else:
            from app.api.challenges import CHALLENGE_FLAG_MAP
            expected_flag = CHALLENGE_FLAG_MAP.get(challenge.title, f"OWASP_DEMO{{{challenge.title.lower().replace(' ', '_')}}}")
            writeup_text = f"🚩 OFFICIAL FLAG: {expected_flag}\n\nOfficial Analysis Solution for '{challenge.title}':\n\n1. Analyze challenge parameters.\n2. Apply cryptanalysis or exploit technique.\n3. The verified flag is `{expected_flag}`."

    if is_admin_or_mod:
        resp = ChallengeAdminResponse.model_validate(challenge)
    else:
        resp = ChallengeResponse.model_validate(challenge)

    resp.hints = safe_hints
    resp.is_solved = solve is not None
    resp.points_awarded = solve.points_awarded if solve else None
    resp.is_surrendered = solve is not None and solve.points_awarded == 0
    resp.solves_count = total_solves
    resp.writeup_content = writeup_text

    if resp.is_solved:
        from app.api.challenges import CHALLENGE_FLAG_MAP
        resp.submitted_flag = CHALLENGE_FLAG_MAP.get(challenge.title, "")

    return resp


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
@router.post("/{challenge_id}/hints/{hint_id}/unlock", response_model=HintUsageResponse, status_code=status.HTTP_200_OK)
def use_hint(
    challenge_id: UUID,
    hint_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Student unlocks a hint. Records point deduction and reveals hint content."""
    return HintService.use_hint(db, challenge_id, hint_id, current_user)


@router.post("/{challenge_id}/submit", response_model=SubmissionResponse, status_code=status.HTTP_200_OK)
def submit_challenge_flag(
    challenge_id: UUID,
    request: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Submits flag directly to challenge endpoint."""
    flag_val = str(request.get("flag", "")).strip()
    result = SubmissionService.process_submission(
        db=db,
        user=current_user,
        challenge_id=challenge_id,
        submitted_flag=flag_val
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


CHALLENGE_FLAG_MAP = {
    # Web Exploitation
    "DEMO_WEB_01 — Hidden Parameter": "OWASP_DEMO{web_hidden_parameter_01}",
    "DEMO_WEB_02 — Broken Authentication": "OWASP_DEMO{broken_auth_jwt_bypass_02}",
    "DEMO_WEB_03 — SQL Injection Lab": "OWASP_DEMO{sql_injection_union_exfil_03}",
    
    # Cryptography
    "DEMO_CRYPTO_01 — Caesar's Shadow": "OWASP_DEMO{caesar_shadow_shift_13}",
    "DEMO_CRYPTO_02 — RSA Mistake": "OWASP_DEMO{rsa_small_exponent_cube_root_02}",
    "DEMO_CRYPTO_03 — Broken Cipher": "OWASP_DEMO{aes_ecb_byte_at_a_time_oracle_03}",
    
    # Forensics
    "DEMO_FORENSICS_01 — Memory Fragment": "OWASP_DEMO{memory_strings_dump_01}",
    "DEMO_FORENSICS_02 — Network Trail": "OWASP_DEMO{wireshark_http_stream_exfil_02}",
    "DEMO_FORENSICS_03 — Disk Evidence": "OWASP_DEMO{forensics_ext4_inode_recovery_03}",
    
    # Reverse Engineering
    "DEMO_REVERSE_01 — Crack the Binary": "OWASP_DEMO{reverse_strings_hardcoded_01}",
    "DEMO_REVERSE_02 — Hidden Logic": "OWASP_DEMO{reverse_xor_key_unravel_02}",
    "DEMO_REVERSE_03 — Assembly Trail": "OWASP_DEMO{assembly_vm_state_machine_03}",
    
    # Pwn / Binary Exploitation
    "DEMO_PWN_01 — Stack Basics": "OWASP_DEMO{stack_overflow_variable_overwrite_01}",
    "DEMO_PWN_02 — Memory Leak": "OWASP_DEMO{format_string_stack_leak_02}",
    "DEMO_PWN_03 — Control Flow": "OWASP_DEMO{ret2win_rip_hijack_payload_03}",
    
    # OSINT
    "DEMO_OSINT_01 — Digital Footprint": "OWASP_DEMO{osint_github_commit_leak_01}",
    "DEMO_OSINT_02 — Trace the Identity": "OWASP_DEMO{osint_social_persona_recon_02}",
    "DEMO_OSINT_03 — Open Source Trail": "OWASP_DEMO{osint_geolocation_flight_radar_03}",
    
    # Steganography
    "DEMO_STEG_01 — Hidden Message": "OWASP_DEMO{steg_exif_metadata_secret_01}",
    "DEMO_STEG_02 — Pixels Speak": "OWASP_DEMO{steg_least_significant_bit_02}",
    "DEMO_STEG_03 — Layered Secret": "OWASP_DEMO{steg_outguess_spectrogram_audio_03}",
    
    # Misc
    "DEMO_MISC_01 — Security Puzzle": "OWASP_DEMO{misc_base64_qr_code_01}",
    "DEMO_MISC_02 — Logic Trap": "OWASP_DEMO{misc_regex_crossword_master_02}",
    "DEMO_MISC_03 — Final Clue": "OWASP_DEMO{misc_zip_bomb_recursive_tar_03}",
}


@router.post("/{challenge_id}/surrender", status_code=status.HTTP_200_OK)
@router.post("/{challenge_id}/reveal-solution", status_code=status.HTTP_200_OK)
def surrender_and_reveal_solution(
    challenge_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Allows an operative to forfeit points (0 pts) and unlock the full solution writeup."""
    challenge = db.query(Challenge).filter(Challenge.id == challenge_id).first()
    if not challenge or not challenge.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Challenge not found or inactive"
        )

    # If not already solved, record solve with 0 points
    existing_solve = db.query(Solve).filter(
        Solve.user_id == current_user.id,
        Solve.challenge_id == challenge_id
    ).first()

    if not existing_solve:
        sub = Submission(
            user_id=current_user.id,
            challenge_id=challenge_id,
            submitted_flag_hash="FORFEIT_SOLUTION_VIEW",
            is_correct=True,
            points_awarded=0
        )
        db.add(sub)
        db.flush()

        solve = Solve(
            user_id=current_user.id,
            challenge_id=challenge_id,
            submission_id=sub.id,
            points_awarded=0
        )
        db.add(solve)
        db.commit()

    # Find the official flag for this challenge
    flag_val = None
    for title_key, f_val in CHALLENGE_FLAG_MAP.items():
        prefix = title_key.split("—")[0].strip()
        if prefix in challenge.title or challenge.title in title_key:
            flag_val = f_val
            break
    if not flag_val:
        flag_val = CHALLENGE_FLAG_MAP.get(challenge.title, f"OWASP_DEMO{{{challenge.title.lower().replace(' ', '_')}}}")

    # Retrieve challenge writeup / solution
    writeup = db.query(ChallengeWriteup).filter(ChallengeWriteup.challenge_id == challenge_id).first()
    base_content = writeup.content if (writeup and writeup.content) else (
        f"Official Analysis Solution for '{challenge.title}':\n\n"
        f"1. Analyze the challenge vectors and parameter structure.\n"
        f"2. Execute exploit or decode steps as outlined in the vulnerability matrix.\n"
        f"3. The operative flag is verified via server SHA-256 hash comparison."
    )

    if flag_val not in base_content:
        solution_text = f"🚩 OFFICIAL FLAG: {flag_val}\n\n{base_content}"
    else:
        solution_text = base_content

    return {
        "status": "surrendered",
        "points_awarded": 0,
        "flag": flag_val,
        "message": "Challenge surrendered. 0 points awarded. Full solution unlocked.",
        "solution": solution_text
    }


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
    from pathlib import Path
    ext = Path(file.filename or "").suffix.lower()
    if settings.ALLOWED_FILE_EXTENSIONS and ext not in settings.ALLOWED_FILE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File extension '{ext}' is not allowed for security reasons."
        )

    file_bytes = await file.read()
    if len(file_bytes) > settings.MAX_FILE_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds maximum allowed limit ({settings.MAX_FILE_UPLOAD_SIZE // (1024*1024)}MB)."
        )

    file_record = ChallengeService.add_challenge_file(db, challenge_id, file.filename, file_bytes)
    return ChallengeFileResponse.model_validate(file_record)


@router.get("/{challenge_id}/files/{file_id}/download")
def download_challenge_file(
    challenge_id: UUID,
    file_id: UUID,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Downloads challenge file safely without path traversal or internal disk path disclosure."""
    file_rec = ChallengeService.get_challenge_file(db, file_id)
    if file_rec.challenge_id != challenge_id:
        raise HTTPException(status_code=404, detail="File does not belong to this challenge")

    is_admin_or_mod = current_user is not None and current_user.role in [UserRole.MODERATOR, UserRole.ADMIN]
    if file_rec.challenge and not file_rec.challenge.is_active and not is_admin_or_mod:
        raise HTTPException(status_code=403, detail="Cannot download files for an inactive challenge")

    file_path = storage_service.get_file_path(file_rec.storage_path)
    return FileResponse(
        path=str(file_path),
        filename=file_rec.filename,
        media_type="application/octet-stream"
    )
