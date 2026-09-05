from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class LeaderboardEntry(BaseModel):
    """Public leaderboard entry for a single user."""
    model_config = ConfigDict(from_attributes=True)

    rank: int
    user_id: UUID
    username: str
    college: Optional[str] = None
    total_points: int
    solved_count: int


class LeaderboardResponse(BaseModel):
    """Paginated leaderboard response."""
    page: int
    page_size: int
    total_entries: int
    total_pages: int
    items: List[LeaderboardEntry]


class UserRankResponse(BaseModel):
    """Authoritative user ranking response across global and college scoreboards."""
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    username: str
    college: Optional[str] = None
    total_points: int
    solved_count: int
    global_rank: Optional[int] = None
    college_rank: Optional[int] = None
