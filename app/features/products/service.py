import json
import shutil
from pathlib import Path
from uuid import uuid4
from typing import List
from PIL import Image, UnidentifiedImageError
from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.infrastructure.database.models import User, Product, ProductImage, ProductEmbedding
from app.infrastructure.storage.local import validate_and_save_upload, ALLOWED_IMAGE_EXTENSIONS
from app.features.media.video import extract_frames_from_video
from app.features.recognition.embedder import generate_embedding
from app.features.products.schemas import ProductOut

def format_product_out(p: Product) -> dict:
    uploads_dir = settings.resolved_uploads_dir
    preview_urls = []
    if p.images:
        for img in p.images:
            try:
                rel = Path(img.file_path).relative_to(uploads_dir)
                preview_urls.append(f"/uploads/{rel.as_posix()}")
            except ValueError:
                pass
    return {
        "id": p.id,
        "title": p.title,
        "description": p.description,
        "barcode": getattr(p, "barcode", "") or "",
        "price": p.price,
        "currency": p.currency,
        "status": p.status,
        "image_count": len(p.images) if p.images else 0,
        "thumbnail_url": preview_urls[0] if preview_urls else None,
        "preview_urls": preview_urls[:6]
    }

def list_user_products(user_id: int, db: Session) -> list[dict]:
    products = (
        db.query(Product)
        .options(joinedload(Product.images))
        .filter(Product.user_id == user_id)
        .order_by(Product.id.desc())
        .all()
    )
    return [format_product_out(p) for p in products]

def delete_user_product(product_id: int, user_id: int, db: Session) -> bool:
    product = db.query(Product).filter(Product.id == product_id, Product.user_id == user_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")

    folder = settings.resolved_uploads_dir / f"user_{user_id}" / f"product_{product.id}"
    db.delete(product)
    db.commit()
    shutil.rmtree(folder, ignore_errors=True)
    return True

def create_product_with_media(
    user_id: int,
    title: str,
    description: str,
    barcode: str,
    price: float,
    currency: str,
    files: List[UploadFile],
    db: Session
) -> dict:
    title = title.strip()
    barcode = barcode.strip()
    currency = currency.strip().upper()

    if not title or len(title) > 200:
        raise HTTPException(400, "Title is required (max 200 chars).")
    if price < 0:
        raise HTTPException(400, "Price must be zero or more.")
    if not files:
        raise HTTPException(400, "Upload at least one image or video.")

    product = Product(
        user_id=user_id,
        title=title,
        description=description.strip(),
        barcode=barcode,
        price=price,
        currency=currency,
        status="processing"
    )
    db.add(product)
    db.commit()
    db.refresh(product)

    product_folder = settings.resolved_uploads_dir / f"user_{user_id}" / f"product_{product.id}"
    product_folder.mkdir(parents=True, exist_ok=True)
    total_processed = 0

    try:
        for upload in files:
            saved_path = validate_and_save_upload(upload, product_folder, allow_video=True)
            ext = saved_path.suffix.lower()

            if ext in ALLOWED_IMAGE_EXTENSIONS:
                try:
                    with Image.open(saved_path) as im:
                        im.verify()
                except (UnidentifiedImageError, OSError):
                    saved_path.unlink(missing_ok=True)
                    raise HTTPException(400, f"Invalid image file: {upload.filename}")
                image_records = [(saved_path, "upload")]
            else:
                frames_dir = product_folder / f"frames_{uuid4().hex[:6]}"
                frames = extract_frames_from_video(saved_path, frames_dir)
                image_records = [(frame, "video_frame") for frame in frames]

            for img_path, source_type in image_records:
                img_row = ProductImage(
                    product_id=product.id,
                    file_path=str(img_path),
                    source_type=source_type
                )
                db.add(img_row)
                db.commit()
                db.refresh(img_row)

                vector = generate_embedding(Image.open(img_path).convert("RGB"))
                db.add(ProductEmbedding(
                    product_image_id=img_row.id,
                    vector_json=json.dumps(vector.tolist()),
                    encoder_version=f"{settings.clip_model_name}:{settings.clip_pretrained}"
                ))
                db.commit()
                total_processed += 1

        if not total_processed:
            raise HTTPException(400, "No usable image frames were found.")

        product.status = "ready"
        db.commit()
        db.refresh(product)
        return format_product_out(product)

    except HTTPException:
        product.status = "failed"
        db.commit()
        raise
    except Exception as exc:
        product.status = "failed"
        db.commit()
        raise HTTPException(
            500,
            f"AI processing failed ({type(exc).__name__}: {exc}). Check model download and console output."
        )
