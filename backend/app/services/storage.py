import hashlib
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Tuple
from fastapi import HTTPException, UploadFile, status
from app.core.config import settings

# Supported MIME signatures (Magic bytes)
MAGIC_SIGNATURES = {
    b"\xff\xd8\xff": [".jpg", ".jpeg"],
    b"\x89PNG\r\n\x1a\n": [".png"],
    b"RIFF": [".webp"],  # WebP starts with RIFF and has WEBP at offset 8
}


class StorageService:
    def __init__(self, base_dir: str = settings.UPLOAD_DIR):
        self.base_dir = Path(base_dir)
        self.diagnostics_dir = self.base_dir / "diagnostics"
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        self.diagnostics_dir.mkdir(parents=True, exist_ok=True)

    def validate_file_extension(self, filename: str) -> str:
        ext = Path(filename).suffix.lower()
        if ext not in settings.ALLOWED_IMAGE_EXTENSIONS:
            allowed = ", ".join(settings.ALLOWED_IMAGE_EXTENSIONS)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file extension '{ext}'. Allowed extensions are: {allowed}",
            )
        return ext

    def validate_image_header(self, header: bytes, ext: str) -> None:
        # Check JPEG
        if header.startswith(b"\xff\xd8\xff"):
            if ext in [".jpg", ".jpeg"]:
                return
        # Check PNG
        if header.startswith(b"\x89PNG\r\n\x1a\n"):
            if ext == ".png":
                return
        # Check WebP (RIFF + WEBP)
        if header.startswith(b"RIFF") and len(header) >= 12 and header[8:12] == b"WEBP":
            if ext == ".webp":
                return

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File content header does not match a valid image format (JPEG, PNG, WEBP).",
        )

    async def save_diagnostic_image(self, file: UploadFile) -> Tuple[str, str, str]:
        """Validates, hashes, and stores an uploaded diagnostic image.

        Returns:
            Tuple of (relative_storage_path, original_filename, sha256_hash)
        """
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Filename cannot be empty.",
            )

        ext = self.validate_file_extension(file.filename)

        # Read first 16 bytes for header validation
        header = await file.read(16)
        if len(header) < 4:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty or corrupted file uploaded.",
            )
        self.validate_image_header(header, ext)

        # Reset read pointer or read remainder
        rest_content = await file.read()
        full_content = header + rest_content

        # Size check
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if len(full_content) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB.",
            )

        # Compute SHA256
        sha256_hash = hashlib.sha256(full_content).hexdigest()

        # Date-partitioned subdirectory
        month_str = datetime.now(timezone.utc).strftime("%Y-%m")
        target_dir = self.diagnostics_dir / month_str
        target_dir.mkdir(parents=True, exist_ok=True)

        unique_filename = f"{uuid.uuid4().hex}{ext}"
        destination = target_dir / unique_filename

        with open(destination, "wb") as f:
            f.write(full_content)

        relative_path = str(destination.relative_to(self.base_dir)).replace("\\", "/")
        return relative_path, file.filename, sha256_hash

    def remove_file(self, relative_path: str) -> bool:
        full_path = self.base_dir / relative_path
        if full_path.exists() and full_path.is_file():
            try:
                full_path.unlink()
                return True
            except OSError:
                return False
        return False


storage_service = StorageService()
