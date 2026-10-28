import os
from pathlib import Path
from PIL import Image
from app.core.config import settings
from app.core.logging import logger

def read_text_from_image(image: Image.Image) -> str:
    """
    Extracts text from an image crop using Tesseract OCR if available.
    Returns cleaned uppercase text, or an empty string if OCR fails or is unavailable.
    """
    try:
        import pytesseract

        # Configure tesseract executable path
        cmd_path = Path(settings.tesseract_cmd)
        if cmd_path.is_file():
            pytesseract.pytesseract.tesseract_cmd = str(cmd_path)

        text = pytesseract.image_to_string(image)
        cleaned = " ".join(text.split()).strip()
        return cleaned
    except Exception as exc:
        logger.debug(f"OCR reading skipped or failed: {exc}")
        return ""
