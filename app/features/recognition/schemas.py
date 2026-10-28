from pydantic import BaseModel, Field
from typing import List, Optional

from app.features.carts.schemas import CartOut

class DetectionBox(BaseModel):
    detection_index: int
    box: List[int]
    detected_class: str
    detector_confidence: float
    product_id: Optional[int] = None
    suggested_product_id: Optional[int] = None
    title: str
    suggested_title: Optional[str] = None
    description: Optional[str] = ""
    price: Optional[float] = None
    currency: Optional[str] = None
    similarity: float
    barcode_detected: Optional[str] = ""
    ocr_text_snippet: Optional[str] = ""
    match_method: str = "visual"  # "barcode", "visual", "ocr_boosted", "none"
    needs_confirmation: bool

class ScanResponse(BaseModel):
    cart_id: int
    detections: List[DetectionBox]
    threshold: float
    cart: Optional[CartOut] = None
    note: str = "Products matching your catalog are automatically added to the cart."
