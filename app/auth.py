# Compatibility bridge for existing imports
from app.core.security import hash_password, verify_password, create_access_token as make_token
from app.features.auth.dependencies import get_current_user as current_user

__all__ = ["hash_password", "verify_password", "make_token", "current_user"]
