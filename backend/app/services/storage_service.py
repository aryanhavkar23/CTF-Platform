import os
import re
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Tuple


class StorageService(ABC):
    """Abstract interface for file storage provider (Local, R2, S3, Supabase)."""

    @abstractmethod
    def save_file(self, file_bytes: bytes, original_filename: str) -> Tuple[str, int]:
        """Saves file bytes and returns (storage_path_reference, file_size_bytes)."""
        pass

    @abstractmethod
    def get_file_path(self, storage_path: str) -> Path:
        """Resolves internal storage path securely, preventing path traversal."""
        pass

    @abstractmethod
    def delete_file(self, storage_path: str) -> bool:
        """Deletes file from storage."""
        pass


class LocalStorageService(StorageService):
    """Secure local filesystem storage implementation."""

    def __init__(self, base_dir: Path | None = None):
        if base_dir is None:
            self.storage_root = Path(__file__).resolve().parent.parent.parent / "uploads"
        else:
            self.storage_root = base_dir
        self.storage_root.mkdir(parents=True, exist_ok=True)

    def _sanitize_filename(self, filename: str) -> str:
        # Strip path traversal and forbidden characters
        clean_name = os.path.basename(filename)
        clean_name = re.sub(r"[^\w\.-]", "_", clean_name)
        if not clean_name or clean_name.startswith("."):
            clean_name = "file_" + clean_name.lstrip(".")
        return clean_name[:200]

    def save_file(self, file_bytes: bytes, original_filename: str) -> Tuple[str, int]:
        clean_filename = self._sanitize_filename(original_filename)
        storage_key = f"{uuid.uuid4().hex}_{clean_filename}"
        target_path = (self.storage_root / storage_key).resolve()

        # Enforce storage directory boundary
        if not str(target_path).startswith(str(self.storage_root.resolve())):
            raise ValueError("Path traversal attempt detected during file save")

        target_path.write_bytes(file_bytes)
        return storage_key, len(file_bytes)

    def get_file_path(self, storage_path: str) -> Path:
        clean_path = os.path.basename(storage_path)
        target_path = (self.storage_root / clean_path).resolve()

        if not str(target_path).startswith(str(self.storage_root.resolve())):
            raise ValueError("Path traversal attempt detected during file retrieval")

        if not target_path.exists():
            raise FileNotFoundError("Requested challenge file does not exist")

        return target_path

    def delete_file(self, storage_path: str) -> bool:
        try:
            target_path = self.get_file_path(storage_path)
            if target_path.exists():
                target_path.unlink()
                return True
        except Exception:
            pass
        return False


storage_service = LocalStorageService()
