# Feature Specification & Prompt Backup: Auto-Cart & Multi-Item Scanner

**Saved Date**: 2026-10-21  
**Repository**: AI Product Scanner MVP  

---

## 1. Original User Prompt Backup

```text
new fix : in photo scan and live scanner i want cart total price and description of each product to be automaticly displayed when a product match the product in the database because the objectif is to gain time after this prompt all is good , when a product is detected is added directly to the cart and the other thing that i want is make the count in the scan if a product exist more than one time
```

---

## 2. Core Requirements & Behavior

### A. Auto-Display Cart Total Price & Product Description
- **Objective**: Gain time by skipping manual suggestion reviews and extra clicks.
- **Description**: Whenever a product matches the catalog (via barcode or visual OpenCLIP similarity >= 0.78), its **full product description** is displayed directly in:
  - The scan detection cards / live candidate stream.
  - The active cart and session item rows.
- **Running Total**: The cart total price updates and displays automatically in both **Photo Scan** and **Live Scanner** immediately upon detection.

### B. Direct / Automatic Cart Addition
- **No Manual Confirmation Needed**: When a detected object confidently matches a database product (`product_id` present, `needs_confirmation: false`), it is immediately confirmed into the cart/session.
- **Hallucination Prevention**: Uncertain suggestions (similarity < 0.78, `needs_confirmation: true`) are **never** auto-added, preventing false positives from cluttering the cart.

### C. Multi-Item / Duplicate Counting
- **Duplicate Detection**: If a product exists multiple times in the camera frame or photo (e.g., 2 bottles of olive oil):
  - The system counts each distinct instance rather than treating it as a single unit.
  - The quantity is incremented accordingly (`quantity = count`).
  - Unit price, line subtotal, and cart total are calculated as `unit_price * count`.
  - The UI shows an explicit count badge (`xN items`) and line total breakdown.

---

## 3. Key Files & Implementation References

1. `app/features/recognition/pipeline.py`
   - Populates `description`, `price`, `currency`, and ensures `is_confident` adheres to `MATCH_THRESHOLD` (0.78).
2. `app/features/recognition/router.py`
   - In `scan_cart_image`, aggregates duplicate confident matches via `Counter` and auto-adds them into `cart_items` with their exact quantities.
3. `app/features/recognition/live_router.py`
   - In `scan_live_frame`, detects distinct tracked objects and increments session item quantity automatically.
4. `app/static/app.js`
   - Renders descriptions, running total bars, duplicate count badges (`xN detected`), and auto-updated cart totals.
5. `app/static/index.html` & `app/static/style.css`
   - Visual total bar `#photoCartTotalBar` and typography styling for `.detection-description` and `.item-description`.
