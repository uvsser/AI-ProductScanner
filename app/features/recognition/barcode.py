import cv2
import numpy as np
from PIL import Image
from app.core.logging import logger

_barcode_detector = None
_qr_detector = None

def get_barcode_detector():
    global _barcode_detector
    if _barcode_detector is None and hasattr(cv2, "barcode"):
        try:
            _barcode_detector = cv2.barcode.BarcodeDetector()
        except Exception:
            pass
    return _barcode_detector

def get_qr_detector():
    global _qr_detector
    if _qr_detector is None:
        try:
            _qr_detector = cv2.QRCodeDetector()
        except Exception:
            pass
    return _qr_detector

def read_barcode_from_image(image: Image.Image) -> str:
    """
    Attempts to read 1D Barcode or 2D QR Code from image crop.
    Returns the decoded string, or empty string if not found.
    """
    try:
        arr = cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2BGR)

        # 1. Try OpenCV 1D Barcode detector
        b_det = get_barcode_detector()
        if b_det is not None:
            res = b_det.detectAndDecode(arr)
            if res and len(res) >= 1:
                decoded_info = res[0]
                if isinstance(decoded_info, str) and decoded_info.strip():
                    return decoded_info.strip()

        # 2. Try OpenCV QR Code detector
        qr_det = get_qr_detector()
        if qr_det is not None:
            decoded_text, points, _ = qr_det.detectAndDecode(arr)
            if decoded_text and decoded_text.strip():
                return decoded_text.strip()

        # 3. Try pyzbar if available and functional
        try:
            import pyzbar.pyzbar as pyzbar
            decoded_objects = pyzbar.decode(arr)
            for obj in decoded_objects:
                data = obj.data.decode("utf-8", errors="ignore").strip()
                if data:
                    return data
        except Exception:
            pass

    except Exception as exc:
        logger.debug(f"Barcode decoding skipped or failed: {exc}")

    return ""
