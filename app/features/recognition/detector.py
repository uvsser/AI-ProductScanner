import threading
import cv2
import numpy as np
from PIL import Image
from app.core.config import settings

_lock = threading.Lock()
_yolo_model = None

def get_yolo_model():
    global _yolo_model
    with _lock:
        if _yolo_model is None:
            from ultralytics import YOLO
            _yolo_model = YOLO(settings.yolo_model)
    return _yolo_model

def detect_objects(image: Image.Image) -> list[dict]:
    """
    Runs YOLO detection on the PIL image. Returns bounding boxes and crops.
    Falls back to whole image if no high-confidence objects are detected.
    """
    model = get_yolo_model()
    arr = cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2BGR)
    result = model.predict(arr, conf=settings.min_detection_confidence, verbose=False)[0]

    found = []
    if result.boxes is not None:
        for b in result.boxes:
            x1, y1, x2, y2 = b.xyxy[0].cpu().numpy().astype(int).tolist()
            x1 = max(0, x1)
            y1 = max(0, y1)
            x2 = min(image.width, x2)
            y2 = min(image.height, y2)

            if x2 - x1 < 24 or y2 - y1 < 24:
                continue

            found.append({
                "crop": image.crop((x1, y1, x2, y2)),
                "box": [x1, y1, x2, y2],
                "detector_confidence": float(b.conf[0].item()),
                "detected_class": model.names.get(int(b.cls[0].item()), "object")
            })

    if not found:
        found = [{
            "crop": image.convert("RGB"),
            "box": [0, 0, image.width, image.height],
            "detector_confidence": 0.0,
            "detected_class": "whole_image_fallback"
        }]

    return found
