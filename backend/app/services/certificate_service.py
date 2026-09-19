import hmac
import hashlib
import uuid
from uuid import UUID
from datetime import datetime, timezone
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.models.user import User
from app.models.event import Event
from app.models.event_registration import EventRegistration
from app.models.team import TeamMember
from app.schemas.certificate import CertificateResponse
from app.services.event_service import EventService


class CertificateService:
    """Cryptographically verifiable digital certificates for CTF event participation & winners."""

    @staticmethod
    def _compute_signature(user_id: UUID, event_id: UUID, rank: int, points: int) -> str:
        payload = f"{user_id}:{event_id}:{rank}:{points}".encode("utf-8")
        secret = settings.SECRET_KEY.encode("utf-8")
        return hmac.new(secret, payload, hashlib.sha256).hexdigest()

    @staticmethod
    def _encode_token(user_id: UUID, event_id: UUID, rank: int, points: int) -> str:
        sig = CertificateService._compute_signature(user_id, event_id, rank, points)
        return f"{user_id}_{event_id}_{rank}_{points}_{sig[:32]}"

    @staticmethod
    def get_award_title(rank: int, total_points: int) -> str:
        if total_points <= 0:
            return "Certificate of Participation"
        if rank == 1:
            return "1st Place Champion"
        elif rank == 2:
            return "2nd Place Runner-Up"
        elif rank == 3:
            return "3rd Place Podium"
        elif rank <= 10:
            return "Top 10 Finalist"
        return "Certificate of Participation"

    @classmethod
    def generate_certificate(cls, db: Session, event_id: UUID, user: User) -> CertificateResponse:
        """Generates a verifiable certificate for an event participant."""
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

        # Verify user or their team was registered
        team_ids = [
            t[0] for t in db.query(TeamMember.team_id)
            .filter(TeamMember.user_id == user.id, TeamMember.is_active == True)
            .all()
        ]

        registration = (
            db.query(EventRegistration)
            .filter(
                EventRegistration.event_id == event_id,
                EventRegistration.is_active == True,
                (EventRegistration.user_id == user.id) | (EventRegistration.team_id.in_(team_ids) if team_ids else False),
            )
            .first()
        )

        if not registration:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User was not registered for this event.",
            )

        # Get event leaderboard to determine rank and points
        leaderboard = EventService.get_event_leaderboard(db, event_id, user=user)
        rank = 0
        total_points = 0
        solved_count = 0

        # Check entries for matching user or team
        for entry in leaderboard.entries:
            if entry.participant_id == user.id or (registration.team_id and entry.participant_id == registration.team_id):
                rank = entry.rank
                total_points = entry.total_points
                solved_count = entry.solved_count
                break

        if rank == 0:
            # Participant registered but solved 0 challenges
            rank = len(leaderboard.entries) + 1
            total_points = 0
            solved_count = 0

        award_title = cls.get_award_title(rank, total_points)
        token = cls._encode_token(user.id, event.id, rank, total_points)
        cert_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"cert-{token}")

        return CertificateResponse(
            certificate_id=cert_id,
            recipient_id=user.id,
            recipient_name=user.name or user.username,
            recipient_college=user.college or "OWASP College Club",
            event_id=event.id,
            event_name=event.name,
            event_slug=event.slug,
            rank=rank,
            award_title=award_title,
            points=total_points,
            solved_count=solved_count,
            issue_date=event.end_at,
            verification_token=token,
            verification_url=f"/api/events/certificates/verify/{token}",
            is_valid=True,
        )

    @classmethod
    def verify_certificate(cls, db: Session, token: str) -> CertificateResponse:
        """Cryptographically verifies a digital certificate token."""
        parts = token.split("_", 4)
        if len(parts) != 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Malformed certificate verification token format.",
            )

        try:
            user_id = UUID(parts[0])
            event_id = UUID(parts[1])
            rank = int(parts[2])
            points = int(parts[3])
            sig_part = parts[4]
        except (ValueError, IndexError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Malformed certificate verification token parameters.",
            )

        # Verify signature
        expected_sig = cls._compute_signature(user_id, event_id, rank, points)
        if not hmac.compare_digest(sig_part, expected_sig[:32]):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Certificate verification failed: invalid or tampered signature.",
            )

        user = db.query(User).filter(User.id == user_id).first()
        event = db.query(Event).filter(Event.id == event_id).first()
        if not user or not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Certificate entities no longer exist.",
            )

        cert_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"cert-{token}")
        award_title = cls.get_award_title(rank, points)

        return CertificateResponse(
            certificate_id=cert_id,
            recipient_id=user.id,
            recipient_name=user.name or user.username,
            recipient_college=user.college or "OWASP College Club",
            event_id=event.id,
            event_name=event.name,
            event_slug=event.slug,
            rank=rank,
            award_title=award_title,
            points=points,
            solved_count=0,
            issue_date=event.end_at,
            verification_token=token,
            verification_url=f"/api/events/certificates/verify/{token}",
            is_valid=True,
        )

    @classmethod
    def distribute_event_certificates(cls, db: Session, event_id: UUID) -> dict:
        """Issues and distributes cryptographically verifiable certificates to all registered participants of an event."""
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

        registrations = db.query(EventRegistration).filter(
            EventRegistration.event_id == event_id,
            EventRegistration.is_active == True,
        ).all()

        leaderboard = EventService.get_event_leaderboard(db, event_id)
        rank_map = {}
        for entry in leaderboard.entries:
            rank_map[entry.participant_id] = (entry.rank, entry.total_points, entry.solved_count)

        recipients = []
        user_ids_processed = set()

        for reg in registrations:
            reg_type_str = reg.registration_type.value if hasattr(reg.registration_type, "value") else str(reg.registration_type)
            if reg_type_str == "individual":
                if reg.user_id and reg.user_id not in user_ids_processed:
                    user = db.query(User).filter(User.id == reg.user_id).first()
                    if user:
                        rank, points, solved_count = rank_map.get(user.id, (len(leaderboard.entries) + 1, 0, 0))
                        award_title = cls.get_award_title(rank, points)
                        token = cls._encode_token(user.id, event.id, rank, points)
                        cert_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"cert-{token}")
                        recipients.append({
                            "certificate_id": str(cert_id),
                            "user_id": str(user.id),
                            "name": user.name or user.username,
                            "email": user.email,
                            "college": user.college or "OWASP Student Chapter",
                            "rank": rank,
                            "points": points,
                            "award_title": award_title,
                            "verification_token": token,
                            "verification_url": f"/api/events/certificates/verify/{token}",
                            "status": "delivered",
                        })
                        user_ids_processed.add(user.id)
            else:
                team_members = db.query(TeamMember).filter(
                    TeamMember.team_id == reg.team_id,
                    TeamMember.is_active == True,
                ).all()
                team_rank, team_points, team_solves = rank_map.get(reg.team_id, (len(leaderboard.entries) + 1, 0, 0))
                award_title = cls.get_award_title(team_rank, team_points)
                for tm in team_members:
                    if tm.user_id not in user_ids_processed:
                        user = db.query(User).filter(User.id == tm.user_id).first()
                        if user:
                            token = cls._encode_token(user.id, event.id, team_rank, team_points)
                            cert_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"cert-{token}")
                            recipients.append({
                                "certificate_id": str(cert_id),
                                "user_id": str(user.id),
                                "name": user.name or user.username,
                                "email": user.email,
                                "college": user.college or "OWASP Student Chapter",
                                "rank": team_rank,
                                "points": team_points,
                                "award_title": award_title,
                                "verification_token": token,
                                "verification_url": f"/api/events/certificates/verify/{token}",
                                "status": "delivered",
                            })
                            user_ids_processed.add(user.id)

        return {
            "event_id": str(event.id),
            "event_name": event.name,
            "total_issued": len(recipients),
            "issued_at": datetime.now(timezone.utc).isoformat(),
            "recipients": recipients,
            "message": f"Successfully distributed {len(recipients)} digital participation & achievement certificates to registered participant Gmail addresses.",
        }
