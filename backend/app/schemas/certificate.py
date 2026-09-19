from typing import Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class CertificateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    certificate_id: UUID
    recipient_id: UUID
    recipient_name: str
    recipient_college: Optional[str] = None
    event_id: UUID
    event_name: str
    event_slug: str
    rank: int
    award_title: str
    points: int
    solved_count: int
    issue_date: datetime
    verification_token: str
    verification_url: str
    is_valid: bool = True
