import json
import re
import numpy as np
from PIL import Image
from sqlalchemy.orm import Session
from app.core.config import settings
from app.infrastructure.database.models import Product, ProductImage, ProductEmbedding
from app.features.recognition.detector import detect_objects
from app.features.recognition.embedder import generate_embedding
from app.features.recognition.matcher import match_query_to_candidates
from app.features.recognition.barcode import read_barcode_from_image
from app.features.recognition.ocr import read_text_from_image

def _text_overlap_score(ocr_text: str, product_title: str) -> float:
    """
    Computes keyword matching boost between OCR text and product title.
    """
    if not ocr_text or not product_title:
        return 0.0

    ocr_words = set(re.findall(r"\w+", ocr_text.lower()))
    title_words = set(re.findall(r"\w+", product_title.lower()))

    # Ignore common short stopwords
    stopwords = {"and", "the", "for", "with", "de", "le", "la", "les", "un", "une"}
    title_words = {w for w in title_words if len(w) > 2 and w not in stopwords}

    if not title_words:
        return 0.0

    overlap = ocr_words.intersection(title_words)
    return len(overlap) / len(title_words)

def run_recognition_pipeline(image: Image.Image, user_id: int, db: Session) -> list[dict]:
    """
    Executes the complete hybrid recognition pipeline:
    1. Detect objects in scan image with YOLO.
    2. Retrieve user's catalog products & embeddings.
    3. For each detected crop:
       a. Check for Barcode/QR Code: Exact match with catalog barcode guarantees 100% confidence.
       b. Check OCR text snippet with Tesseract.
       c. Compute OpenCLIP visual embedding and calculate cosine similarity against catalog.
       d. Combine visual similarity with OCR boost.
       e. Score final confidence against MATCH_THRESHOLD.
    """
    dets = detect_objects(image)

    # Fetch user's registered ready products
    user_products = db.query(Product).filter(
        Product.user_id == user_id,
        Product.status == "ready"
    ).all()
    products_by_id = {p.id: p for p in user_products}
    barcode_to_product = {p.barcode.strip(): p for p in user_products if p.barcode and p.barcode.strip()}

    # Fetch embeddings
    rows = (
        db.query(ProductEmbedding, ProductImage, Product)
        .join(ProductImage, ProductEmbedding.product_image_id == ProductImage.id)
        .join(Product, ProductImage.product_id == Product.id)
        .filter(Product.user_id == user_id, Product.status == "ready")
        .all()
    )

    candidates = []
    for emb, _img, product in rows:
        try:
            v = np.asarray(json.loads(emb.vector_json), dtype=np.float32)
            norm = float(np.linalg.norm(v))
            if norm > 0:
                v = v / norm
            candidates.append((product.id, product.title, v))
        except Exception:
            continue

    output = []
    for i, d in enumerate(dets):
        crop = d["crop"]

        # Step A: Barcode Detection
        barcode_val = read_barcode_from_image(crop)
        if barcode_val and barcode_val in barcode_to_product:
            matched_prod = barcode_to_product[barcode_val]
            output.append({
                "detection_index": i,
                "box": d["box"],
                "detected_class": d["detected_class"],
                "detector_confidence": round(d["detector_confidence"], 3),
                "product_id": matched_prod.id,
                "suggested_product_id": matched_prod.id,
                "title": matched_prod.title,
                "suggested_title": matched_prod.title,
                "description": matched_prod.description or "",
                "price": matched_prod.price,
                "currency": matched_prod.currency,
                "similarity": 1.0,
                "barcode_detected": barcode_val,
                "ocr_text_snippet": "",
                "match_method": "barcode",
                "needs_confirmation": False
            })
            continue

        # Step B: OCR text extraction
        ocr_text = read_text_from_image(crop)
        ocr_snippet = ocr_text[:100] if ocr_text else ""

        # Step C: Visual Embedding
        crop_vector = generate_embedding(crop)
        top_match = match_query_to_candidates(crop_vector, candidates)

        if top_match:
            base_sim = top_match["similarity"]
            matched_pid = top_match["product_id"]
            product = products_by_id.get(matched_pid)

            # Step D: OCR Verification Boost
            ocr_boost = 0.0
            if product and ocr_text:
                ocr_boost = _text_overlap_score(ocr_text, product.title) * 0.15

            final_sim = min(1.0, base_sim + ocr_boost)
            match_method = "ocr_boosted" if ocr_boost > 0 else "visual"

            # Threshold check: protect against blank walls/rooms when no object box was found by YOLO
            effective_threshold = settings.match_threshold
            if d.get("detected_class") == "whole_image_fallback":
                effective_threshold = max(effective_threshold, 0.72)

            is_confident = (final_sim >= effective_threshold) and (product is not None)

            output.append({
                "detection_index": i,
                "box": d["box"],
                "detected_class": d["detected_class"],
                "detector_confidence": round(d["detector_confidence"], 3),
                "product_id": matched_pid if is_confident else None,
                "suggested_product_id": matched_pid,
                "title": (product.title if product else top_match["title"]),
                "suggested_title": top_match["title"],
                "description": (product.description or "") if product else "",
                "price": product.price if product else None,
                "currency": product.currency if product else None,
                "similarity": round(final_sim, 4),
                "barcode_detected": barcode_val,
                "ocr_text_snippet": ocr_snippet,
                "match_method": match_method,
                "needs_confirmation": not is_confident
            })
        else:
            output.append({
                "detection_index": i,
                "box": d["box"],
                "detected_class": d["detected_class"],
                "detector_confidence": round(d["detector_confidence"], 3),
                "product_id": None,
                "suggested_product_id": None,
                "title": "No registered products",
                "suggested_title": None,
                "description": "",
                "price": None,
                "currency": None,
                "similarity": 0.0,
                "barcode_detected": barcode_val,
                "ocr_text_snippet": ocr_snippet,
                "match_method": "none",
                "needs_confirmation": True
            })

    return output
