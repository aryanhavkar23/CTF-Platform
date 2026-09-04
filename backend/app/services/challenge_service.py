import hashlib
from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.config import settings
from app.models.category import Category
from app.models.challenge import (
    Challenge,
    ChallengeDifficulty,
    ChallengeType,
    ChallengeFile,
    ChallengeHint,
    ChallengeWriteup,
    WriteupVisibility,
)
from app.schemas.challenge import (
    ChallengeCreate,
    ChallengeUpdate,
    HintCreate,
    HintUpdate,
    WriteupCreate,
    WriteupUpdate,
)
from app.services.storage_service import storage_service

STANDARD_CATEGORIES = [
    ("Web Exploitation", "Exploitation of web applications, APIs, and web services."),
    ("Cryptography", "Ciphers, encryption algorithms, hashing, and mathematical security."),
    ("Forensics", "File analysis, memory dumps, network PCAP inspection, and artifact extraction."),
    ("Reverse Engineering", "Decompilation, binary disassembly, and code logic reverse-engineering."),
    ("Pwn / Binary Exploitation", "Buffer overflows, binary exploitation, and memory corruption."),
    ("OSINT", "Open-source intelligence and investigative recon."),
    ("Steganography", "Hiding secrets, messages, and payloads within media files."),
    ("Misc", "Miscellaneous cybersecurity challenges, scripting, and trivia."),
]


def hash_flag(flag: str) -> str:
    """Computes deterministic cryptographic hash of the challenge flag."""
    clean_flag = flag.strip()
    salted = f"{clean_flag}:{settings.SECRET_KEY}".encode("utf-8")
    return hashlib.sha256(salted).hexdigest()


class ChallengeService:
    """Authoritative business logic for categories, challenges, hints, files, and writeups."""

    @staticmethod
    def seed_categories(db: Session) -> List[Category]:
        """Seeds standard OWASP categories if they do not exist."""
        categories = []
        for name, desc in STANDARD_CATEGORIES:
            cat = db.query(Category).filter(Category.name == name).first()
            if not cat:
                cat = Category(name=name, description=desc)
                db.add(cat)
            categories.append(cat)
        db.commit()
        for cat in categories:
            db.refresh(cat)
        return categories

    @staticmethod
    def get_categories(db: Session) -> List[Category]:
        return db.query(Category).order_by(Category.name).all()

    @staticmethod
    def get_category_by_id(db: Session, category_id: UUID) -> Optional[Category]:
        return db.query(Category).filter(Category.id == category_id).first()

    @staticmethod
    def create_challenge(db: Session, request: ChallengeCreate) -> Challenge:
        category = ChallengeService.get_category_by_id(db, request.category_id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category with ID {request.category_id} does not exist"
            )

        existing = db.query(Challenge).filter(Challenge.title == request.title).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"A challenge with the title {request.title!r} already exists"
            )

        flag_hashed = hash_flag(request.flag)
        challenge = Challenge(
            title=request.title,
            description=request.description,
            category_id=request.category_id,
            difficulty=request.difficulty,
            points=request.points,
            flag_hash=flag_hashed,
            is_active=request.is_active,
            challenge_type=ChallengeType.LIVE if request.is_live_instance else ChallengeType.STATIC,
            is_live_instance=request.is_live_instance,
            docker_image=request.docker_image,
        )
        db.add(challenge)
        db.commit()
        db.refresh(challenge)
        return challenge

    @staticmethod
    def get_challenge(db: Session, challenge_id: UUID, is_admin_or_mod: bool = False) -> Challenge:
        query = db.query(Challenge).filter(Challenge.id == challenge_id)
        if not is_admin_or_mod:
            query = query.filter(Challenge.is_active == True)
        
        challenge = query.first()
        if not challenge:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Challenge not found"
            )
        return challenge

    @staticmethod
    def list_challenges(
        db: Session,
        category_id: Optional[UUID] = None,
        difficulty: Optional[ChallengeDifficulty] = None,
        is_active: Optional[bool] = None,
        is_admin_or_mod: bool = False
    ) -> List[Challenge]:
        query = db.query(Challenge)

        if not is_admin_or_mod:
            query = query.filter(Challenge.is_active == True)
        elif is_active is not None:
            query = query.filter(Challenge.is_active == is_active)

        if category_id:
            query = query.filter(Challenge.category_id == category_id)
        if difficulty:
            query = query.filter(Challenge.difficulty == difficulty)

        return query.order_by(Challenge.points.asc(), Challenge.title.asc()).all()

    @staticmethod
    def update_challenge(db: Session, challenge_id: UUID, request: ChallengeUpdate) -> Challenge:
        challenge = db.query(Challenge).filter(Challenge.id == challenge_id).first()
        if not challenge:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Challenge not found"
            )

        if request.category_id:
            category = ChallengeService.get_category_by_id(db, request.category_id)
            if not category:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Category with ID {request.category_id} does not exist"
                )
            challenge.category_id = request.category_id

        if request.title and request.title != challenge.title:
            existing = db.query(Challenge).filter(Challenge.title == request.title).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"A challenge with the title {request.title!r} already exists"
                )
            challenge.title = request.title

        if request.description is not None:
            challenge.description = request.description
        if request.difficulty is not None:
            challenge.difficulty = request.difficulty
        if request.points is not None:
            challenge.points = request.points
        if request.flag is not None:
            challenge.flag_hash = hash_flag(request.flag)
        if request.is_active is not None:
            challenge.is_active = request.is_active
        if request.is_live_instance is not None:
            challenge.is_live_instance = request.is_live_instance
            challenge.challenge_type = ChallengeType.LIVE if request.is_live_instance else ChallengeType.STATIC
        if request.docker_image is not None:
            challenge.docker_image = request.docker_image

        db.commit()
        db.refresh(challenge)
        return challenge

    @staticmethod
    def deactivate_challenge(db: Session, challenge_id: UUID, hard: bool = False) -> dict:
        """Deactivates challenge safely by default to preserve submissions."""
        challenge = db.query(Challenge).filter(Challenge.id == challenge_id).first()
        if not challenge:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Challenge not found"
            )

        if hard:
            db.delete(challenge)
            db.commit()
            return {"status": "deleted", "challenge_id": str(challenge_id)}
        else:
            challenge.is_active = False
            db.commit()
            return {"status": "deactivated", "challenge_id": str(challenge_id), "is_active": False}

    # Hints
    @staticmethod
    def add_hint(db: Session, challenge_id: UUID, request: HintCreate) -> ChallengeHint:
        challenge = db.query(Challenge).filter(Challenge.id == challenge_id).first()
        if not challenge:
            raise HTTPException(status_code=404, detail="Challenge not found")

        hint = ChallengeHint(
            challenge_id=challenge_id,
            content=request.content,
            point_deduction=request.point_deduction,
            order=request.order,
            is_active=request.is_active,
        )
        db.add(hint)
        db.commit()
        db.refresh(hint)
        return hint

    @staticmethod
    def update_hint(db: Session, hint_id: UUID, request: HintUpdate) -> ChallengeHint:
        hint = db.query(ChallengeHint).filter(ChallengeHint.id == hint_id).first()
        if not hint:
            raise HTTPException(status_code=404, detail="Hint not found")

        if request.content is not None:
            hint.content = request.content
        if request.point_deduction is not None:
            hint.point_deduction = request.point_deduction
        if request.order is not None:
            hint.order = request.order
        if request.is_active is not None:
            hint.is_active = request.is_active

        db.commit()
        db.refresh(hint)
        return hint

    @staticmethod
    def delete_hint(db: Session, hint_id: UUID) -> bool:
        hint = db.query(ChallengeHint).filter(ChallengeHint.id == hint_id).first()
        if not hint:
            raise HTTPException(status_code=404, detail="Hint not found")
        db.delete(hint)
        db.commit()
        return True

    # Writeup
    @staticmethod
    def create_or_update_writeup(db: Session, challenge_id: UUID, request: WriteupCreate) -> ChallengeWriteup:
        challenge = db.query(Challenge).filter(Challenge.id == challenge_id).first()
        if not challenge:
            raise HTTPException(status_code=404, detail="Challenge not found")

        writeup = db.query(ChallengeWriteup).filter(ChallengeWriteup.challenge_id == challenge_id).first()
        if writeup:
            writeup.content = request.content
            writeup.visibility = request.visibility
        else:
            writeup = ChallengeWriteup(
                challenge_id=challenge_id,
                content=request.content,
                visibility=request.visibility
            )
            db.add(writeup)

        db.commit()
        db.refresh(writeup)
        return writeup

    @staticmethod
    def get_writeup(db: Session, challenge_id: UUID, is_admin_or_mod: bool = False) -> ChallengeWriteup:
        writeup = db.query(ChallengeWriteup).filter(ChallengeWriteup.challenge_id == challenge_id).first()
        if not writeup:
            raise HTTPException(status_code=404, detail="Writeup not found")

        if not is_admin_or_mod and writeup.visibility != WriteupVisibility.PUBLIC:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Writeup is locked according to visibility rules"
            )

        return writeup

    # Files
    @staticmethod
    def add_challenge_file(db: Session, challenge_id: UUID, filename: str, file_bytes: bytes) -> ChallengeFile:
        challenge = db.query(Challenge).filter(Challenge.id == challenge_id).first()
        if not challenge:
            raise HTTPException(status_code=404, detail="Challenge not found")

        storage_key, size = storage_service.save_file(file_bytes, filename)
        file_record = ChallengeFile(
            challenge_id=challenge_id,
            filename=filename,
            storage_path=storage_key,
            file_size=size
        )
        db.add(file_record)
        db.commit()
        db.refresh(file_record)
        return file_record

    @staticmethod
    def get_challenge_file(db: Session, file_id: UUID) -> ChallengeFile:
        file_rec = db.query(ChallengeFile).filter(ChallengeFile.id == file_id).first()
        if not file_rec:
            raise HTTPException(status_code=404, detail="File record not found")
        return file_rec
