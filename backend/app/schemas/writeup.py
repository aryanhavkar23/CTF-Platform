from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from app.models.challenge import WriteupVisibility


class WriteupCreate(BaseModel):
    """Schema for creating a challenge writeup."""
    title: str = "Official Writeup"
    content: str
    visibility: WriteupVisibility = WriteupVisibility.HIDDEN


class WriteupUpdate(BaseModel):
    """Schema for updating a challenge writeup."""
    title: Optional[str] = None
    content: Optional[str] = None
    visibility: Optional[WriteupVisibility] = None


class WriteupResponse(BaseModel):
    """Schema for returning writeup content to authorized viewers."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    challenge_id: UUID
    title: str
    content: str
    visibility: WriteupVisibility
    created_at: datetime
    updated_at: datetime
