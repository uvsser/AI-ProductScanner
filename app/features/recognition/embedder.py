import threading
import numpy as np
import torch
from PIL import Image
from app.core.config import settings

_lock = threading.Lock()
_clip_model = None
_clip_preprocess = None
_device = "cuda" if torch.cuda.is_available() else "cpu"

def get_clip_model():
    global _clip_model, _clip_preprocess
    with _lock:
        if _clip_model is None:
            import open_clip
            model, _, preprocess = open_clip.create_model_and_transforms(
                settings.clip_model_name,
                pretrained=settings.clip_pretrained
            )
            _clip_model = model.to(_device).eval()
            _clip_preprocess = preprocess
    return _clip_model, _clip_preprocess

def generate_embedding(image: Image.Image) -> np.ndarray:
    """
    Computes normalized OpenCLIP visual embedding vector for a given PIL image.
    """
    model, preprocess = get_clip_model()
    tensor = preprocess(image.convert("RGB")).unsqueeze(0).to(_device)
    with torch.no_grad():
        vec = model.encode_image(tensor)
        vec = vec / vec.norm(dim=-1, keepdim=True)
    return vec[0].detach().cpu().numpy().astype(np.float32)
