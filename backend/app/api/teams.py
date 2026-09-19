from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.schemas.team import (
    TeamCreate,
    TeamUpdate,
    TeamResponse,
    TeamDetailResponse,
    TeamMemberResponse,
    UserTeamDetailResponse,
    TeamHistoryResponse,
    AddTeamMemberRequest,
    TransferOwnershipRequest,
)
from app.services.team_service import TeamService

router = APIRouter()


@router.post("", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
def create_team(
    data: TeamCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Authenticated user creates a new team and automatically becomes owner."""
    return TeamService.create_team(db, current_user, data)


@router.get("", response_model=List[TeamResponse], status_code=status.HTTP_200_OK)
def list_teams(
    college: Optional[str] = Query(None, description="Filter by college"),
    search: Optional[str] = Query(None, description="Search by team name"),
    is_active: Optional[bool] = Query(True, description="Filter active/inactive"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List teams with optional filtering and pagination."""
    return TeamService.get_teams(
        db=db,
        college=college,
        search=search,
        is_active=is_active,
        skip=skip,
        limit=limit,
    )


@router.get("/me", response_model=Optional[TeamDetailResponse], status_code=status.HTTP_200_OK)
def get_my_team(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Retrieve current user's active team details and member list."""
    return TeamService.get_my_team(db, current_user)


@router.get("/my-teams", response_model=List[UserTeamDetailResponse], status_code=status.HTTP_200_OK)
def get_my_teams(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Retrieve all active squads where the authenticated user is owner, captain, or member."""
    return TeamService.get_my_teams(db, current_user)


@router.get("/me/invitations", status_code=status.HTTP_200_OK)
def get_my_team_invitations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Retrieve pending squad invitations for the authenticated user."""
    return TeamService.get_my_invitations(db, current_user)


@router.get("/operatives/search", status_code=status.HTTP_200_OK)
def search_operatives(
    query: Optional[str] = Query(None, description="Search registered platform operatives by username, name, college, email"),
    college: Optional[str] = Query(None, description="Filter/prioritize registered platform operatives by college"),
    strict_college: bool = Query(False, description="Strictly filter by college if true, otherwise prioritize same college on top"),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Search registered platform users to invite/add to a team squad."""
    return TeamService.search_operatives(db, current_user, query=query, college=college, strict_college=strict_college, limit=limit)


@router.get("/{team_id}/history", response_model=TeamHistoryResponse, status_code=status.HTTP_200_OK)
def get_team_history(
    team_id: UUID,
    db: Session = Depends(get_db),
):
    """Retrieve tournament history, event scores, solved challenges, and rankings for a squad."""
    return TeamService.get_team_history(db, team_id)


@router.get("/{team_id}", response_model=TeamDetailResponse, status_code=status.HTTP_200_OK)
def get_team(
    team_id: UUID,
    db: Session = Depends(get_db),
):
    """Retrieve detailed information and member list for a specific team."""
    return TeamService.get_team_by_id(db, team_id)


@router.put("/{team_id}", response_model=TeamResponse, status_code=status.HTTP_200_OK)
def update_team(
    team_id: UUID,
    data: TeamUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update team metadata (only team owner or admin)."""
    return TeamService.update_team(db, current_user, team_id, data)


@router.delete("/{team_id}", status_code=status.HTTP_200_OK)
def deactivate_team(
    team_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Soft-deactivate a team (only team owner or admin)."""
    return TeamService.deactivate_team(db, current_user, team_id)


@router.get("/{team_id}/members", response_model=List[TeamMemberResponse], status_code=status.HTTP_200_OK)
def list_team_members(
    team_id: UUID,
    db: Session = Depends(get_db),
):
    """List active members of a team."""
    return TeamService.get_team_members(db, team_id)


@router.post("/{team_id}/members", response_model=TeamMemberResponse, status_code=status.HTTP_201_CREATED)
def add_team_member(
    team_id: UUID,
    payload: AddTeamMemberRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Add a member to the team (owner or admin only). Enforces max team size."""
    return TeamService.add_team_member(
        db=db,
        current_user=current_user,
        team_id=team_id,
        target_user_id=payload.user_id,
        target_username=payload.username,
        role=payload.role or "member",
    )


@router.post("/{team_id}/accept", response_model=TeamMemberResponse, status_code=status.HTTP_200_OK)
def accept_team_invite_self(
    team_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """The current authenticated user accepts a pending squad request."""
    return TeamService.accept_team_request(db, current_user, team_id)


@router.post("/{team_id}/decline", status_code=status.HTTP_200_OK)
def decline_team_invite_self(
    team_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """The current authenticated user declines a pending squad request."""
    return TeamService.decline_team_request(db, current_user, team_id)


@router.post("/{team_id}/members/{user_id}/accept", response_model=TeamMemberResponse, status_code=status.HTTP_200_OK)
def accept_team_member_request(
    team_id: UUID,
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Accept a pending member request into the squad (owner or invited operative)."""
    return TeamService.accept_team_request(db, current_user, team_id, target_user_id=user_id)


@router.delete("/{team_id}/members/{user_id}", status_code=status.HTTP_200_OK)
def remove_team_member(
    team_id: UUID,
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Remove a member from the team (owner or admin only)."""
    return TeamService.remove_team_member(db, current_user, team_id, user_id)


@router.delete("/{team_id}/leave", status_code=status.HTTP_200_OK)
def leave_team(
    team_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """A normal member leaves the team. Owner must transfer ownership first."""
    return TeamService.leave_team(db, current_user, team_id)


@router.post("/{team_id}/transfer-owner", response_model=TeamDetailResponse, status_code=status.HTTP_200_OK)
def transfer_ownership(
    team_id: UUID,
    payload: TransferOwnershipRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Transfer ownership atomically to an active team member (current owner only)."""
    return TeamService.transfer_ownership(db, current_user, team_id, payload.new_owner_id)
