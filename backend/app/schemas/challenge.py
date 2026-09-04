from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict
from app.models.challenge import ChallengeDifficulty, ChallengeType, WriteupVisibility


class CategoryResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChallengeFileResponse(BaseModel):
    id: UUID
    challenge_id: UUID
    filename: str
    file_size: Optional[int] = None
    created_at: datetime
    download_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class HintCreate(BaseModel):
    content: str = Field(min_length=1, description="Content or clue of the hint")
    point_deduction: int = Field(default=0, ge=0, description="Points deducted when unlocked")
    order: int = Field(default=1, ge=1, description="Sequential ordering of the hint")
    is_active: bool = True


class HintUpdate(BaseModel):
    content: Optional[str] = Field(default=None, min_length=1)
    point_deduction: Optional[int] = Field(default=None, ge=0)
    order: Optional[int] = Field(default=None, ge=1)
    is_active: Optional[bool] = None


class HintResponse(BaseModel):
    id: UUID
    challenge_id: UUID
    content: str
    point_deduction: int
    order: int
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WriteupCreate(BaseModel):
    content: str = Field(min_length=1, description="Official challenge solution and explanation")
    visibility: WriteupVisibility = Field(default=WriteupVisibility.HIDDEN)


class WriteupUpdate(BaseModel):
    content: Optional[str] = Field(default=None, min_length=1)
    visibility: Optional[WriteupVisibility] = None


class WriteupResponse(BaseModel):
    id: UUID
    challenge_id: UUID
    content: str
    visibility: WriteupVisibility
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChallengeCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1)
    category_id: UUID
    difficulty: ChallengeDifficulty
    points: int = Field(ge=0)
    flag: str = Field(min_length=1, max_length=255, description="Plaintext flag to hash securely")
    is_active: bool = True
    is_live_instance: bool = False
    docker_image: Optional[str] = None


class ChallengeUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, min_length=1)
    category_id: Optional[UUID] = None
    difficulty: Optional[ChallengeDifficulty] = None
    points: Optional[int] = Field(default=None, ge=0)
    flag: Optional[str] = Field(default=None, min_length=1, max_length=255)
    is_active: Optional[bool] = None
    is_live_instance: Optional[bool] = None
    docker_image: Optional[str] = None


class ChallengeResponse(BaseModel):
    """Student-safe challenge response. Flag and flag_hash are NEVER exposed."""
    id: UUID
    title: str
    description: str
    category_id: UUID
    category: Optional[CategoryResponse] = None
    difficulty: ChallengeDifficulty
    points: int
    challenge_type: ChallengeType
    is_live_instance: bool
    files: List[ChallengeFileResponse] = []
    hints: List[HintResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChallengeAdminResponse(ChallengeResponse):
    """Admin/Moderator challenge response including administrative fields."""
    is_active: bool
    docker_image: Optional[str] = None
    has_writeup: bool = False
    writeup: Optional[WriteupResponse] = None
