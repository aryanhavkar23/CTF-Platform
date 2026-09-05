from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator


class HintCreate(BaseModel):
    """Schema for creating a challenge hint."""
    title: str = "Hint"
    content: str
    points_deduction: int = Field(0, ge=0)
    point_deduction: Optional[int] = Field(None, ge=0)
    display_order: int = 1
    order: Optional[int] = None
    is_active: bool = True

    @model_validator(mode="before")
    @classmethod
    def harmonize_fields(cls, values: dict):
        if isinstance(values, dict):
            if "point_deduction" in values and values["point_deduction"] is not None:
                values.setdefault("points_deduction", values["point_deduction"])
            elif "points_deduction" in values and values["points_deduction"] is not None:
                values.setdefault("point_deduction", values["points_deduction"])

            if "order" in values and values["order"] is not None:
                values.setdefault("display_order", values["order"])
            elif "display_order" in values and values["display_order"] is not None:
                values.setdefault("order", values["display_order"])
        return values


class HintUpdate(BaseModel):
    """Schema for updating a challenge hint."""
    title: Optional[str] = None
    content: Optional[str] = None
    points_deduction: Optional[int] = Field(None, ge=0)
    point_deduction: Optional[int] = Field(None, ge=0)
    display_order: Optional[int] = None
    order: Optional[int] = None
    is_active: Optional[bool] = None

    @model_validator(mode="before")
    @classmethod
    def harmonize_fields(cls, values: dict):
        if isinstance(values, dict):
            if "point_deduction" in values and values["point_deduction"] is not None:
                values["points_deduction"] = values["point_deduction"]
            if "order" in values and values["order"] is not None:
                values["display_order"] = values["order"]
        return values


class HintResponse(BaseModel):
    """Safe hint response. Content is None for students until unlocked."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    challenge_id: UUID
    title: str
    content: Optional[str] = None
    points_deduction: int = Field(default=0, validation_alias="point_deduction")
    point_deduction: int = Field(default=0)
    display_order: int = Field(default=1, validation_alias="order")
    order: int = Field(default=1)
    is_active: bool
    used: bool = False
    created_at: datetime
    updated_at: datetime


class HintUsageResponse(BaseModel):
    """Response returned upon unlocking a hint with revealed content."""
    model_config = ConfigDict(from_attributes=True)

    hint_id: UUID
    challenge_id: UUID
    title: str
    content: str
    points_deducted: int
    used_at: datetime
