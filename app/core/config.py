import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    # App & Security
    secret_key: str = "change-me-to-a-long-random-secret" #jwt secret key
    access_token_expire_hours: int = 12 #jwt token expiry time
    database_url: str = "sqlite:///./storage/app.db" #database url
    storage_dir: str = "./storage" #storage directory

    # AI / Vision Models
    yolo_model: str = "yolo11n.pt" #yolo model name
    clip_model_name: str = "ViT-B-32" #clip model name
    clip_pretrained: str = "laion2b_s34b_b79k" #clip model pretrained weights

    # OCR and Barcode
    tesseract_cmd: str = r"C:\Program Files\Tesseract-OCR\tesseract.exe" #tesseract command path

    # Thresholds & Constraints
    match_threshold: float = 0.60 #match threshold for object detection
    min_detection_confidence: float = 0.20 #minimum detection confidence for object detection
    video_frame_interval_sec: float = 1.5 #video frame interval for object detection
    max_upload_mb: int = 100 #maximum upload size in MB

    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def resolved_storage_dir(self) -> Path:
        p = Path(self.storage_dir)
        if not p.is_absolute():
            p = (ROOT_DIR / p).resolve()
        return p

    @property
    def resolved_uploads_dir(self) -> Path:
        uploads = self.resolved_storage_dir / "uploads"
        uploads.mkdir(parents=True, exist_ok=True)
        return uploads

settings = Settings()
