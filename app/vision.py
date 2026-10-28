# Compatibility bridge for existing imports
from app.core.config import settings, ROOT_DIR as ROOT
from app.features.recognition.embedder import generate_embedding as embedding
from app.features.recognition.detector import detect_objects as detect
from app.features.recognition.matcher import match_query_to_candidates as match
from app.features.media.video import extract_frames_from_video as extract_frames

__all__ = ["settings", "ROOT", "embedding", "detect", "match", "extract_frames"]
