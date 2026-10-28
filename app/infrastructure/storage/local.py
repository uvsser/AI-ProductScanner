from pathlib import Path
from uuid import uuid4
from fastapi import UploadFile, HTTPException
from app.core.config import settings

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv"}

def validate_and_save_upload(upload: UploadFile, target_folder: Path, allow_video: bool = True) -> Path:
    original_ext = Path(upload.filename or "").suffix.lower()
    allowed_exts = ALLOWED_IMAGE_EXTENSIONS | (ALLOWED_VIDEO_EXTENSIONS if allow_video else set())

    if original_ext not in allowed_exts:
        if allow_video:
            raise HTTPException(400, "Unsupported file type. Use JPG/PNG/WEBP or MP4/MOV/AVI/MKV.")
        raise HTTPException(400, "Upload a scan image, not a video.")

    target_folder.mkdir(parents=True, exist_ok=True)
    destination = target_folder / f"{uuid4().hex}{original_ext}"
    max_bytes = settings.max_upload_mb * 1024 * 1024
    total_written = 0

    try:
        with destination.open("wb") as out:
            while True:
                chunk = upload.file.read(1024 * 1024)
                if not chunk:
                    break
                total_written += len(chunk)
                if total_written > max_bytes:
                    raise HTTPException(413, f"File exceeds maximum upload size of {settings.max_upload_mb} MB.")
                out.write(chunk)
    except Exception:
        destination.unlink(missing_ok=True)
        raise

    return destination
