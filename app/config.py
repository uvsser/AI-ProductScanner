# Compatibility bridge for existing config imports
from app.core.config import settings, ROOT_DIR as ROOT

STORAGE = settings.resolved_storage_dir
UPLOADS = settings.resolved_uploads_dir

__all__ = ["settings", "ROOT", "STORAGE", "UPLOADS"]
