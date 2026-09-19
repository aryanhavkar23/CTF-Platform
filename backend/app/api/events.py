from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status, HTTPException, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.deps import (
    get_current_active_user,
    get_current_user_optional,
    require_role,
)
from app.models.user import User, UserRole
from app.schemas.event import (
    EventCreate,
    EventUpdate,
    EventResponse,
    EventChallengeAdd,
    EventChallengeResponse,
    EventRegistrationRequest,
    EventRegistrationResponse,
    EventParticipantResponse,
    EventLeaderboardResponse,
)
from app.schemas.submission import SubmissionCreate, SubmissionResponse
from app.schemas.certificate import CertificateResponse
from app.services.event_service import EventService
from app.services.submission_service import SubmissionService
from app.services.certificate_service import CertificateService
from app.services.event_export_service import EventExportService

router = APIRouter()


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
def create_event(
    data: EventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """Admins and moderators can create new CTF events."""
    event = EventService.create_event(db, data, creator_id=current_user.id)
    return EventService.to_event_response(event)


@router.get("", response_model=List[EventResponse], status_code=status.HTTP_200_OK)
def list_events(
    include_inactive: bool = Query(False, description="Include inactive events (admin/mod only)"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """List all available events. Students view active events; admins/mods can include inactive."""
    events = EventService.get_events(db, include_inactive=include_inactive, user=current_user)
    return [EventService.to_event_response(e) for e in events]


@router.get("/certificates/verify/{token}", response_model=CertificateResponse)
def verify_certificate(
    token: str,
    db: Session = Depends(get_db),
):
    """Publicly verify the authenticity of a digital certificate token."""
    return CertificateService.verify_certificate(db, token)


@router.get("/{event_id_or_slug}", response_model=EventResponse, status_code=status.HTTP_200_OK)
def get_event(
    event_id_or_slug: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Retrieve detailed event metadata by UUID or URL-friendly slug."""
    try:
        event_id = UUID(event_id_or_slug)
        event = EventService.get_event_by_id(db, event_id, current_user)
    except ValueError:
        event = EventService.get_event_by_slug(db, event_id_or_slug, current_user)
    return EventService.to_event_response(event)


@router.put("/{event_id}", response_model=EventResponse, status_code=status.HTTP_200_OK)
def update_event(
    event_id: UUID,
    data: EventUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """Update event timing, status, and metadata. Restricted to admins and moderators."""
    event = EventService.update_event(db, event_id, data)
    return EventService.to_event_response(event)


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(
    event_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """Delete an event and its associated registrations. Restricted to admins and moderators."""
    EventService.delete_event(db, event_id)
    return None


# -----------------------------------------------------------------------------
# Event Challenges
# -----------------------------------------------------------------------------

@router.post("/{event_id}/challenges", status_code=status.HTTP_200_OK)
def add_challenge_to_event(
    event_id: UUID,
    data: EventChallengeAdd,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """Associate a challenge with an event with optional points override and display order."""
    return EventService.add_challenge_to_event(db, event_id, data)


@router.delete("/{event_id}/challenges/{challenge_id}", status_code=status.HTTP_200_OK)
def remove_challenge_from_event(
    event_id: UUID,
    challenge_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """Remove a challenge from an event."""
    EventService.remove_challenge_from_event(db, event_id, challenge_id)
    return {"message": "Challenge removed from event successfully."}


@router.get("/{event_id}/challenges", response_model=List[EventChallengeResponse], status_code=status.HTTP_200_OK)
def list_event_challenges(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """List challenges assigned to this event.
    
    Students can only view when event is LIVE and they are registered.
    Admins/mods can view anytime.
    """
    return EventService.get_event_challenges(db, event_id, current_user)


# -----------------------------------------------------------------------------
# Event Registration
# -----------------------------------------------------------------------------

@router.post("/{event_id}/register", response_model=EventRegistrationResponse, status_code=status.HTTP_201_CREATED)
def register_for_event(
    event_id: UUID,
    data: EventRegistrationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Register for an event as an individual or team.
    
    Team registration requires the caller to be the team owner/captain.
    """
    return EventService.register_for_event(db, event_id, current_user, data)


@router.post("/{event_id}/unregister", status_code=status.HTTP_200_OK)
def unregister_from_event(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Unregister from an active event before it concludes."""
    return EventService.unregister_from_event(db, event_id, current_user)


@router.get("/{event_id}/registration", status_code=status.HTTP_200_OK)
def get_registration_status(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Check whether the authenticated user (or any of their teams) is registered for this event."""
    reg = EventService.get_user_registration(db, event_id, current_user.id)
    if not reg:
        return {"is_registered": False, "registration": None}
    r_type = reg.registration_type.value if hasattr(reg.registration_type, "value") else str(reg.registration_type)
    return {
        "is_registered": True,
        "registration": {
            "id": str(reg.id),
            "registration_type": r_type,
            "user_id": str(reg.user_id) if reg.user_id else None,
            "team_id": str(reg.team_id) if reg.team_id else None,
            "registered_at": reg.registered_at.isoformat(),
        }
    }


@router.get("/{event_id}/participants", response_model=List[EventParticipantResponse], status_code=status.HTTP_200_OK)
def list_participants(
    event_id: UUID,
    db: Session = Depends(get_db),
):
    """List all registered participants (individuals and teams) in the event."""
    return EventService.get_participants(db, event_id)


# -----------------------------------------------------------------------------
# Event Leaderboard & Freeze
# -----------------------------------------------------------------------------

@router.get("/{event_id}/leaderboard", response_model=EventLeaderboardResponse, status_code=status.HTTP_200_OK)
def get_event_leaderboard(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Retrieve isolated event leaderboard.
    
    If frozen, public requests view leaderboard frozen at freeze timestamp.
    Admins/moderators view live leaderboard.
    """
    return EventService.get_event_leaderboard(db, event_id, current_user)


@router.post("/{event_id}/freeze-scoreboard", status_code=status.HTTP_200_OK)
def freeze_scoreboard(
    event_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """Freeze public scoreboard view for this event. Restricted to admins and moderators."""
    event = EventService.freeze_scoreboard(db, event_id)
    return {
        "message": "Scoreboard frozen successfully.",
        "is_scoreboard_frozen": event.is_scoreboard_frozen,
        "scoreboard_frozen_at": event.scoreboard_frozen_at.isoformat() if event.scoreboard_frozen_at else None,
    }


@router.post("/{event_id}/unfreeze-scoreboard", status_code=status.HTTP_200_OK)
def unfreeze_scoreboard(
    event_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """Unfreeze public scoreboard view. Restricted to admins and moderators."""
    event = EventService.unfreeze_scoreboard(db, event_id)
    return {
        "message": "Scoreboard unfrozen successfully.",
        "is_scoreboard_frozen": event.is_scoreboard_frozen,
        "scoreboard_frozen_at": None,
    }


# -----------------------------------------------------------------------------
# Event Flag Submissions
# -----------------------------------------------------------------------------

@router.post("/{event_id}/submissions", response_model=SubmissionResponse, status_code=status.HTTP_200_OK)
def submit_event_flag(
    event_id: UUID,
    data: SubmissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Submit a flag candidate for an event challenge.
    
    Enforces event live/ended practice status, participant registration, rate limits, and isolated points.
    """
    result = SubmissionService.process_submission(
        db=db,
        user=current_user,
        challenge_id=data.challenge_id,
        submitted_flag=data.flag,
        event_id=event_id,
    )
    sub = result["submission"]
    return SubmissionResponse(
        id=sub.id,
        challenge_id=sub.challenge_id,
        is_correct=result["is_correct"],
        points_awarded=result["points_awarded"],
        message=result["message"],
        created_at=sub.created_at,
    )


@router.post("/{event_id}/challenges/{challenge_id}/submit", response_model=SubmissionResponse, status_code=status.HTTP_200_OK)
def submit_event_challenge_flag_alias(
    event_id: UUID,
    challenge_id: UUID,
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Submit a flag candidate directly to event challenge path."""
    flag_val = data.get("flag", "")
    result = SubmissionService.process_submission(
        db=db,
        user=current_user,
        challenge_id=challenge_id,
        submitted_flag=flag_val,
        event_id=event_id,
    )
    sub = result["submission"]
    return SubmissionResponse(
        id=sub.id,
        challenge_id=sub.challenge_id,
        is_correct=result["is_correct"],
        points_awarded=result["points_awarded"],
        message=result["message"],
        created_at=sub.created_at,
    )


# -----------------------------------------------------------------------------
# Event Results Export & Digital Certificates
# -----------------------------------------------------------------------------

@router.get("/{event_id}/export")
def export_event_results(
    event_id: UUID,
    format: str = Query("json", regex="^(json|csv)$", description="Export format: json or csv"),
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """Export complete event results, rankings, and challenge solve metrics in JSON or CSV format."""
    if format == "csv":
        csv_content = EventExportService.export_csv(db, event_id)
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=event_results_{event_id}.csv"},
        )
    return EventExportService.export_json(db, event_id)


@router.get("/{event_id}/certificate", response_model=CertificateResponse)
def get_event_certificate(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Generate or retrieve verifiable digital certificate for an event participant."""
    return CertificateService.generate_certificate(db, event_id, current_user)


@router.post("/{event_id}/distribute-certificates", status_code=status.HTTP_200_OK)
def distribute_event_certificates(
    event_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """Generate and distribute digital certificates to all registered event participants and their registered emails."""
    return CertificateService.distribute_event_certificates(db, event_id)


@router.get("/{event_id}/audit-breakdown", status_code=status.HTTP_200_OK)
def get_event_audit_breakdown(
    event_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """Retrieve detailed post-mortem audit metrics, individual/team question breakdown, cheating history, and certificate statuses."""
    return EventExportService.get_audit_breakdown(db, event_id)



