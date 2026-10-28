from pathlib import Path
from PIL import Image
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.infrastructure.database.session import get_db
from app.infrastructure.database.models import User, Cart, CartItem, Product
from app.infrastructure.storage.local import validate_and_save_upload, ALLOWED_IMAGE_EXTENSIONS
from app.features.auth.dependencies import get_current_user
from app.features.recognition.schemas import ScanResponse
from app.features.recognition.pipeline import run_recognition_pipeline
from app.features.carts.service import calculate_cart_out, get_user_cart_or_404

router = APIRouter(prefix="/api/carts", tags=["recognition"])

@router.post("/{cart_id}/scan", response_model=ScanResponse)
def scan_cart_image(
    cart_id: int,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cart = db.query(Cart).filter(Cart.id == cart_id, Cart.user_id == user.id).first()
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found.")

    temp_folder = settings.resolved_uploads_dir / f"user_{user.id}" / "temporary_scans"
    saved_path = validate_and_save_upload(file, temp_folder, allow_video=False)

    try:
        with Image.open(saved_path) as im:
            image = im.convert("RGB")

        detections = run_recognition_pipeline(image, user.id, db)

        # Automatically count and add each matched product into the cart
        from collections import Counter
        matched_counts = Counter()
        for det in detections:
            matched_pid = det.get("product_id") or det.get("suggested_product_id")
            if matched_pid:
                matched_counts[matched_pid] += 1
                det["product_id"] = matched_pid
                det["needs_confirmation"] = False

        for pid, qty in matched_counts.items():
            product = db.query(Product).filter(
                Product.id == pid,
                Product.user_id == user.id,
                Product.status == "ready"
            ).first()
            if product:
                existing = db.query(CartItem).filter(
                    CartItem.cart_id == cart.id,
                    CartItem.product_id == product.id
                ).first()
                if existing:
                    existing.quantity = min(100, existing.quantity + qty)
                else:
                    db.add(CartItem(
                        cart_id=cart.id,
                        product_id=product.id,
                        quantity=min(100, qty),
                        unit_price_at_addition=product.price
                    ))

        db.commit()

        updated_cart = calculate_cart_out(get_user_cart_or_404(cart_id, user.id, db))

        return {
            "cart_id": cart_id,
            "detections": detections,
            "threshold": settings.match_threshold,
            "cart": updated_cart,
            "note": "Products matched in database were automatically added and cart total updated."
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Scan failed ({type(exc).__name__}: {exc}). Check console/model download."
        )
    finally:
        saved_path.unlink(missing_ok=True)
