# AI Product Scanner MVP

Local-first product registration, image/video processing, visual matching, and shopping cart workflow.

## Target Architecture

The application is structured as a **modular monolith** with clear feature isolation:
- **`app/core`**: Configuration (`pydantic-settings`), logging, cryptographic security (Bcrypt, JWT), and domain exceptions.
- **`app/infrastructure`**: Database engine and session management (`database/`), ORM models, and storage layer (`storage/`).
- **`app/features`**: Feature modules (`auth/`, `products/`, `media/`, `recognition/`, `carts/`) with dedicated routers, services, and schemas.
- **`app/static`**: Browser frontend (HTML, CSS, JS).
- **`tests`**: Automated unit and API integration tests.

For in-depth architectural details, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## Setup (Windows PowerShell, Python 3.11 recommended)

```powershell
# Create virtual environment (if not already done)
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1

# Upgrade pip and install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

# Configure environment
Copy-Item .env.example .env
```

Edit `.env`: set a secure random string for `SECRET_KEY`.

---

## Running the Application

Start the development server:
```powershell
uvicorn app.main:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

- **Swagger API Documentation:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Health Check:** [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

---

## Running Automated Tests

Run the full automated test suite without downloading AI model weights:
```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
```

The test suite validates:
1. Pydantic settings and storage path resolution.
2. Password hashing with truncation defense and JWT expiration logic.
3. Pure vector cosine similarity calculations and empty candidate handling.
4. Shopping cart item addition, subtotaling, and total price aggregation.
5. End-to-end API lifecycle using an in-memory SQLite database.

---

## Configuration Reference

| Key | Default | Description |
| :--- | :--- | :--- |
| `SECRET_KEY` | `change-me-...` | Secret key used for signing JWT authentication tokens |
| `DATABASE_URL` | `sqlite:///./storage/app.db` | SQLAlchemy database URL (supports SQLite & PostgreSQL) |
| `STORAGE_DIR` | `./storage` | Directory where uploads and databases reside |
| `YOLO_MODEL` | `yolo11n.pt` | Ultralytics YOLO model identifier or path |
| `CLIP_MODEL_NAME` | `ViT-B-32` | OpenCLIP vision transformer backbone |
| `CLIP_PRETRAINED` | `laion2b_s34b_b79k` | Pretrained weights checkpoint tag |
| `MATCH_THRESHOLD` | `0.78` | Cosine similarity threshold for confident catalog match |
| `MIN_DETECTION_CONFIDENCE` | `0.20` | YOLO bounding box confidence threshold |
| `VIDEO_FRAME_INTERVAL_SEC` | `1.5` | Keyframe extraction interval from uploaded videos |
| `MAX_UPLOAD_MB` | `100` | Maximum upload size per file in megabytes |
