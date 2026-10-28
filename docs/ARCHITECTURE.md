# Architecture Reference: AI Product Scanner MVP

## 1. Directory Structure

```text
ai_product_scanner_mvp/
├── app/
│   ├── __init__.py
│   ├── main.py                          # Application entry point, lifespan, middleware & route mounting
│   ├── auth.py                          # Compatibility bridge to core/security & features/auth
│   ├── config.py                        # Compatibility bridge to core/config
│   ├── database.py                      # Compatibility bridge to infrastructure/database/session
│   ├── models.py                        # Compatibility bridge to infrastructure/database/models
│   ├── vision.py                        # Compatibility bridge to features/recognition & features/media
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py                    # Strongly typed Pydantic Settings & path resolver
│   │   ├── logging.py                   # Centralized structured logging setup
│   │   ├── security.py                  # Cryptographic password hashing & JWT token handling
│   │   └── exceptions.py                # Base domain & application exception definitions
│   ├── infrastructure/
│   │   ├── __init__.py
│   │   ├── database/
│   │   │   ├── __init__.py
│   │   │   ├── session.py               # Engine creation, SessionLocal, get_db dependency
│   │   │   └── models.py                # Centralized SQLAlchemy declarative models
│   │   └── storage/
│   │       ├── __init__.py
│   │       └── local.py                 # File upload validation, chunked stream saving, size checks
│   ├── features/
│   │   ├── __init__.py
│   │   ├── auth/
│   │   │   ├── __init__.py
│   │   │   ├── schemas.py               # Pydantic schemas: UserRegisterRequest, UserLoginRequest, UserOut
│   │   │   ├── dependencies.py          # OAuth2 bearer token current_user dependency
│   │   │   ├── service.py               # User registration and authentication business rules
│   │   │   └── router.py                # Endpoints: /api/auth/register, /api/auth/login, /api/auth/me
│   │   ├── products/
│   │   │   ├── __init__.py
│   │   │   ├── schemas.py               # Pydantic schemas: ProductCreate, ProductOut
│   │   │   ├── service.py               # Catalog management, media upload orchestration, ownership checks
│   │   │   └── router.py                # Endpoints: /api/products, /api/products/{id}
│   │   ├── media/
│   │   │   ├── __init__.py
│   │   │   └── video.py                 # OpenCV video frame extraction, sampling intervals, resizing
│   │   ├── recognition/
│   │   │   ├── __init__.py
│   │   │   ├── schemas.py               # Pydantic schemas: ScanResponse, DetectionBox
│   │   │   ├── detector.py              # Thread-safe lazy YOLO object detector wrapper
│   │   │   ├── embedder.py              # Thread-safe lazy OpenCLIP visual feature extractor
│   │   │   ├── matcher.py               # Pure NumPy cosine similarity and ranking logic
│   │   │   ├── pipeline.py              # Recognition pipeline orchestrator
│   │   │   └── router.py                # Endpoints: /api/carts/{cart_id}/scan
│   │   └── carts/
│   │       ├── __init__.py
│   │       ├── schemas.py               # Pydantic schemas: CartOut, CartItemOut, AddCartItemRequest
│   │       ├── service.py               # Cart calculations, quantity validations, line item subtotaling
│   │       └── router.py                # Endpoints: /api/carts, /api/carts/{id}, /api/carts/{id}/items
│   └── static/
│       ├── index.html                   # Single Page Application HTML shell
│       ├── app.js                       # Vanilla JS frontend client
│       └── style.css                    # UI styles
├── tests/
│   ├── __init__.py
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_config.py               # Configuration validation tests
│   │   ├── test_security.py             # Hash and JWT token tests
│   │   ├── test_matcher.py              # Pure vector matching tests
│   │   └── test_cart_service.py         # Cart total and subtotal calculation tests
│   └── api/
│       ├── __init__.py
│       └── test_api_flow.py             # End-to-end API integration tests using in-memory SQLite
├── docs/
│   └── ARCHITECTURE.md                  # This architectural reference guide
├── storage/
│   └── uploads/                         # User-isolated uploads and frame crops (git-ignored)
├── .env.example
├── .gitignore
├── pyproject.toml
├── README.md
└── requirements.txt
```

---

## 2. Responsibilities of Major Modules

- **`app.core.config`**: Centralizes configuration using `pydantic-settings`. Resolves absolute paths on Windows or Linux, manages AI model names, similarity thresholds, and upload file size constraints.
- **`app.core.security`**: Encapsulates cryptographic operations (Bcrypt with truncation safety, JWT HS256 encoding/decoding). Decoupled from HTTP requests so it can be tested in isolation.
- **`app.infrastructure.database`**: Manages SQLAlchemy ORM engine, connection pooling parameters, session generators (`get_db`), and data models with cascading deletes and indices.
- **`app.infrastructure.storage`**: Safeguards upload handling: checks file extensions, enforces streaming size limits, generates collision-free UUID filenames, and prevents path traversal attacks.
- **`app.features.auth`**: Manages user accounts, credential verification, and FastAPI token dependencies (`get_current_user`).
- **`app.features.products`**: Handles product creation with multi-image or video inputs, triggers embedding generation, manages catalog queries, and isolates catalogs per user.
- **`app.features.media`**: Extracts keyframes from uploaded video streams at configured time intervals using OpenCV.
- **`app.features.recognition`**:
  - `detector.py`: Thread-safe, lazy-loaded YOLO inference.
  - `embedder.py`: Thread-safe, lazy-loaded OpenCLIP visual encoder.
  - `matcher.py`: Pure mathematical cosine similarity search, testable without GPU/torch dependencies.
  - `pipeline.py`: Orchestrates detection, embedding extraction, and catalog vector matching.
- **`app.features.carts`**: Implements shopping cart lifecycle, quantity constraints (1-100), price snapshotting upon addition, subtotal calculation, and grand total aggregation.

---

## 3. Request Lifecycle & AI Recognition Flow

```
+-----------------------------------------------------------------------------------+
| 1. HTTP Request (e.g. POST /api/carts/{cart_id}/scan)                             |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| 2. Authentication Dependency (get_current_user) -> decodes JWT, queries User DB   |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| 3. Storage Layer (validate_and_save_upload) -> validates image extension & size   |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| 4. Recognition Pipeline (run_recognition_pipeline):                               |
|    a. YOLO Object Detector -> predicts bounding boxes and extracts image crops   |
|    b. Catalog Query -> retrieves user's active product embeddings from DB         |
|    c. OpenCLIP Embedder -> computes 512-d normalized visual vector per crop       |
|    d. Vector Matcher -> calculates cosine similarity against catalog candidates   |
|    e. Threshold Evaluator -> flags confident matches vs. uncertain suggestions    |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| 5. Router formats ScanResponse -> temporary image unlinked -> JSON response sent  |
+-----------------------------------------------------------------------------------+
```

---

## 4. Quick Developer Navigation Guide

| Looking For... | Location in Codebase |
| :--- | :--- |
| **API Endpoints** | `app/features/<feature>/router.py` |
| **Business Logic / Calculations** | `app/features/<feature>/service.py` |
| **Database Queries** | `app/features/<feature>/service.py` |
| **Database Models** | `app/infrastructure/database/models.py` |
| **Database Engine & Session** | `app/infrastructure/database/session.py` |
| **AI Models (YOLO & CLIP)** | `app/features/recognition/detector.py` & `embedder.py` |
| **Vector Similarity Matcher** | `app/features/recognition/matcher.py` |
| **Upload / File Handling** | `app/infrastructure/storage/local.py` |
| **Configuration Settings** | `app/core/config.py` |
| **Automated Tests** | `tests/unit/` and `tests/api/` |

---

## 5. How to Extend the Application

### Adding a New Feature (e.g., `discounts`):
1. Create directory `app/features/discounts/`.
2. Define Pydantic schemas in `schemas.py`.
3. Add business logic and DB queries in `service.py`.
4. Define HTTP endpoints in `router.py`.
5. Mount router in `app/main.py` (`app.include_router(discounts_router)`).
6. Add unit tests under `tests/unit/test_discounts.py`.

### Replacing an AI Model (e.g., swapping YOLO or CLIP):
- **To swap the object detector**: modify `app/features/recognition/detector.py`. Ensure `detect_objects(image: Image.Image)` returns the standard dictionary format (`crop`, `box`, `detector_confidence`, `detected_class`). No router or product logic needs modification.
- **To swap the visual embedder**: modify `app/features/recognition/embedder.py`. Ensure `generate_embedding(image: Image.Image)` returns a 1D normalized `numpy.ndarray`. Update `encoder_version` in config if needed.
