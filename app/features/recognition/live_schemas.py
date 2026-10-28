from pydantic import BaseModel, Field
from typing import List, Optional

from app.features.carts.session_schemas import ShoppingSessionOut

class LiveDetectionBox(BaseModel):
    tracking_id: str
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
    status: str = "candidate"  # "candidate", "confirmed_in_session", "uncertain"

class LiveScanResponse(BaseModel):
    session_id: int
    detections: List[LiveDetectionBox]
    threshold: float
    frame_timestamp_ms: Optional[int] = None
    session: Optional[ShoppingSessionOut] = None
    note: str = "Live frame analyzed. Matched products are automatically added to the shopping list."
