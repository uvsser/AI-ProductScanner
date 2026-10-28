import io
import time
from PIL import Image, UnidentifiedImageError
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form
from sqlalchemy.orm import Session

from app.core.config import settings
from app.infrastructure.database.session import get_db
from app.infrastructure.database.models import User, Cart, CartItem, Product
from app.features.auth.dependencies import get_current_user
from app.features.recognition.live_schemas import LiveScanResponse, LiveDetectionBox
from app.features.recognition.pipeline import run_recognition_pipeline
from app.features.recognition.tracker import get_session_tracker
from app.features.carts.session_service import get_authorized_session_or_404, calculate_session_out

router = APIRouter(prefix="/api/v1/live-scan", tags=["live-scan"])

@router.post("/{session_id}/frame", response_model=LiveScanResponse)
def scan_live_frame(
    session_id: int,
    file: UploadFile = File(...),
    frame_timestamp_ms: int = Form(default=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. Authorize session & tenancy
    session = get_authorized_session_or_404(session_id, user.id, db)
    if session.status != "open":
        raise HTTPException(status_code=400, detail=f"Session is {session.status}. Open a new session.")

    # 2. Validate and decode frame in-memory (no disk leak for live video frames)
    try:
        content = file.file.read()
        if len(content) > 10 * 1024 * 1024:  # Max 10MB per live frame
            raise HTTPException(status_code=413, detail="Frame exceeds 10MB limit.")
        image = Image.open(io.BytesIO(content)).convert("RGB")
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status_code=400, detail="Invalid image frame data.")

    # 3. Run recognition pipeline (YOLO + CLIP + Barcode + OCR)
    raw_detections = run_recognition_pipeline(image, user.id, db)

    # 4. Attach session tracker (IoU + Temporal duplicate tracking)
    tracker = get_session_tracker(session_id)
    tracked_detections = tracker.update(raw_detections)

    # 5. Auto-confirm detected products into live cart session
    session_modified = False
    confirmed_product_ids = {item.product_id for item in session.items}

    for det in tracked_detections:
        # Never auto-add whole_image_fallback in live video frames to avoid background noise additions
        if det.get("detected_class") == "whole_image_fallback":
            continue

        pid = det.get("product_id") or det.get("suggested_product_id")
        tid = det.get("tracking_id")
        is_already_confirmed_track = (det.get("status") == "confirmed_in_session")

        if pid and not is_already_confirmed_track:
            product = db.query(Product).filter(
                Product.id == pid,
                Product.user_id == user.id,
                Product.status == "ready"
            ).first()
            if product:
                existing_item = db.query(CartItem).filter(
                    CartItem.cart_id == session.id,
                    CartItem.product_id == product.id
                ).first()
                if not existing_item:
                    db.add(CartItem(
                        cart_id=session.id,
                        product_id=product.id,
                        quantity=1,
                        unit_price_at_addition=product.price
                    ))
                    session_modified = True
                if tid:
                    tracker.mark_confirmed(tid)
                det["status"] = "confirmed_in_session"
                det["product_id"] = product.id
                det["needs_confirmation"] = False
                confirmed_product_ids.add(pid)
        elif pid in confirmed_product_ids:
            det["status"] = "confirmed_in_session"
            det["product_id"] = pid
            det["needs_confirmation"] = False

    if session_modified:
        db.commit()

    updated_session = calculate_session_out(get_authorized_session_or_404(session_id, user.id, db))

    return {
        "session_id": session_id,
        "detections": tracked_detections,
        "threshold": settings.match_threshold,
        "frame_timestamp_ms": frame_timestamp_ms or int(time.time() * 1000),
        "session": updated_session,
        "note": "Live frame analyzed. Matched products are automatically confirmed into your shopping list."
    }
