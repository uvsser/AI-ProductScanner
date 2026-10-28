# Architecture & Refactoring Specification

## 1. Executive Summary & Problem Analysis

The **AI Product Scanner MVP** is a local-first application combining computer vision (YOLO11n object detection), visual embeddings (OpenCLIP ViT-B-32), catalog similarity search, and shopping cart workflow with a FastAPI backend and browser-based vanilla JavaScript frontend.

### 1.1 Identified Architectural Issues in Existing Codebase
1. **Monolithic & God-File API Layer (`app/main.py`)**:
   - `app/main.py` contains 220 lines with 5 distinct business domains mixed into one file: Authentication, Products, Media Uploads, Visual Scanning / Recognition, and Cart Management.
   - Raw dictionary schemas (`payload: dict`, `files: List[UploadFile]`) instead of Pydantic validation schemas.
   - Business logic, database queries, file I/O, and image transformations are directly inside FastAPI route handlers.
2. **Missing Separation of Concerns**:
   - Routes perform direct filesystem operations (`shutil.rmtree`, saving files) without a storage abstraction.
   - Vector operations and catalog matching queries are embedded directly into route handlers.
3. **Database Session & Lifecycle Anti-Patterns**:
   - `Base.metadata.create_all(bind=engine)` runs on module import in `app/main.py`.
   - SQLite path resolution is duplicated and relies on string replacements in `app/database.py`.
   - Inconsistent transactions and commit patterns (multiple manual commits in middle of loop without rollback on intermediate failures).
4. **AI & Vision Pipeline Coupling**:
   - `app/vision.py` bundles model loading, frame extraction, object detection, and cosine similarity matching into one module.
   - Recognition cannot be tested or swapped without loading torch and ultralytics.
   - Synchronous, computationally heavy AI inference blocks FastAPI request handling without execution strategy or worker isolation.
5. **Security & Validation Deficits**:
   - File extensions are checked only superficially; storage paths used raw user strings without sanitization.
   - Error handling exposes internal trace details (`type(exc).__name__: {exc}`).
   - Password hashing uses outdated bcrypt/passlib configurations vulnerable to known length truncation issues.
6. **Zero Automated Testing**:
   - The project had no test files, no unit tests for cart calculations, ownership checks, or recognition matching.
7. **Observability & Logging**:
   - No structured logging, correlation/request IDs, or contextual error tracing. Standard `print` or default FastAPI logging was relied upon.

---

## 2. Target Architecture (Modular Monolith)

We structure the application into a clean **Feature-Driven Modular Monolith**:

```text
ai_product_scanner_mvp/
├── app/
│   ├── __init__.py
│   ├── main.py                          # FastAPI app factory, middleware, router mount, lifespan
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py                    # Validated Pydantic settings & path helpers
│   │   ├── logging.py                   # Structured logging & request correlation
│   │   ├── security.py                  # Password hashing & JWT token management
│   │   └── exceptions.py                # Core domain & HTTP exception handlers
│   ├── infrastructure/
│   │   ├── __init__.py
│   │   ├── database/
│   │   │   ├── __init__.py
│   │   │   ├── session.py               # Engine, SessionLocal, get_db dependency
│   │   │   └── models.py                # Centralized SQLAlchemy ORM models
│   │   └── storage/
│   │       ├── __init__.py
│   │       └── local.py                 # File storage abstraction & upload validation
│   ├── features/
│   │   ├── __init__.py
│   │   ├── auth/
│   │   │   ├── __init__.py
│   │   │   ├── schemas.py               # Register, Login, Token, UserOut
│   │   │   ├── dependencies.py          # current_user dependency
│   │   │   ├── service.py               # Auth business rules & password verification
│   │   │   └── router.py                # /api/auth routes
│   │   ├── products/
│   │   │   ├── __init__.py
│   │   │   ├── schemas.py               # ProductCreate, ProductOut, ProductList
│   │   │   ├── service.py               # Catalog management, product ownership
│   │   │   └── router.py                # /api/products routes
│   │   ├── media/
│   │   │   ├── __init__.py
│   │   │   └── video.py                 # OpenCV video frame extraction & preprocessing
│   │   ├── recognition/
│   │   │   ├── __init__.py
│   │   │   ├── schemas.py               # ScanResult, DetectionRegion, MatchCandidate
│   │   │   ├── detector.py              # YOLO object detection wrapper
│   │   │   ├── embedder.py              # OpenCLIP embedding wrapper
│   │   │   ├── matcher.py               # Similarity scoring & vector math
│   │   │   ├── pipeline.py              # Recognition pipeline orchestrator
│   │   │   └── router.py                # /api/carts/{cart_id}/scan route
│   │   └── carts/
│   │       ├── __init__.py
│   │       ├── schemas.py               # CartOut, CartItemCreate, CartItemUpdate
│   │       ├── service.py               # Cart operations, quantity updates, total pricing
│   │       └── router.py                # /api/carts routes
│   └── static/
│       ├── app.js
│       ├── index.html
│       └── style.css
├── tests/
│   ├── __init__.py
│   ├── conftest.py                      # In-memory DB fixture, mock tokens, mock AI
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_config.py               # Settings validation
│   │   ├── test_security.py             # Password hashing & JWT token expiry
│   │   ├── test_cart_service.py         # Subtotals, quantities, currency calculations
│   │   └── test_recognition_matcher.py  # Cosine similarity and thresholding logic
│   └── api/
│       ├── __init__.py
│       ├── test_auth_api.py             # User registration & login endpoints
│       ├── test_products_api.py         # Product CRUD & isolation between users
│       └── test_carts_api.py            # Cart item confirmation & calculation endpoints
├── docs/
│   └── ARCHITECTURE.md                  # Comprehensive architectural reference
├── .env.example
├── .gitignore
├── pyproject.toml
├── README.md
└── requirements.txt
```

---

## 3. Module Mapping Matrix

| Existing Module / Code | New Target Destination | Improvements Made |
| :--- | :--- | :--- |
| `app/config.py` | `app/core/config.py` | Absolute path resolution, strongly-typed settings, validator logic |
| `app/auth.py` | `app/core/security.py`, `app/features/auth/dependencies.py`, `app/features/auth/service.py` | Separation of crypto utils from HTTP dependencies & business rules |
| `app/database.py` | `app/infrastructure/database/session.py` | Clean engine setup, safe SQLite URL handling, thread-safe session generator |
| `app/models.py` | `app/infrastructure/database/models.py` | Retained centralized ORM declarative models, indexed relations, cascade behaviors |
| `app/vision.py` (YOLO) | `app/features/recognition/detector.py` | Isolated YOLO lazy initialization, detection class & confidence parsing |
| `app/vision.py` (CLIP) | `app/features/recognition/embedder.py` | Isolated CLIP lazy model loader and normalized tensor embedding |
| `app/vision.py` (Video) | `app/features/media/video.py` | Dedicated video frame extractor with interval and aspect ratio handling |
| `app/vision.py` (Match) | `app/features/recognition/matcher.py` | Pure NumPy cosine similarity and ranking (100% testable without torch) |
| `app/main.py` (Auth routes) | `app/features/auth/router.py` | Pydantic validation (`UserRegisterRequest`, `UserLoginRequest`), status codes |
| `app/main.py` (Product routes)| `app/features/products/router.py` & `service.py` | Transaction boundaries, catalog isolation per user, storage management |
| `app/main.py` (Scan route) | `app/features/recognition/router.py` & `pipeline.py` | End-to-end recognition orchestrator calling detector, embedder, and matcher |
| `app/main.py` (Cart routes) | `app/features/carts/router.py` & `service.py` | Isolated calculation logic for totals, quantity bounds, item ownership |
| `app/main.py` (File saving) | `app/infrastructure/storage/local.py` | Safe filename generation, extension whitelist, chunked size verification |
| `app/main.py` (App entry) | `app/main.py` | Clean lifespan event (`create_all` on startup, clean shutdown), middleware, CORS |

---

## 4. Migration & Safety Rules

1. **Backwards Compatibility**: All API routes (`/api/auth/*`, `/api/products*`, `/api/carts*`, `/api/health`, `/`) maintain identical JSON request/response shapes to keep `app.js` and frontend fully operational.
2. **Deterministic Imports**: All imports use package-level relative or absolute paths anchored at `app.*`.
3. **Zero-Weight Testability**: Business logic, cart totals, catalog matching, token encoding, and file validators can be executed instantly with Python's standard `unittest` framework without downloading model weights.
