from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings, ROOT_DIR
from app.core.logging import setup_logging, logger
from app.core.exceptions import DomainException
from app.infrastructure.database.session import Base, engine

from app.features.auth.router import router as auth_router
from app.features.products.router import router as products_router
from app.features.carts.router import router as carts_router
from app.features.recognition.router import router as recognition_router
from app.features.carts.session_router import router as sessions_router
from app.features.recognition.live_router import router as live_scan_router

# Setup application logging
setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database schema...")
    Base.metadata.create_all(bind=engine)
    logger.info("Application startup complete. Ready for live camera shopping requests.")
    yield
    logger.info("Application shutting down.")

app = FastAPI(
    title="AI Product Scanner & Live Camera Shopping",
    version="2.0.0",
    description="Physical store multi-modal live camera shopping system with YOLO, CLIP, Barcode, OCR and session tracking.",
    lifespan=lifespan
)

# Exception handlers
@app.exception_handler(DomainException)
async def domain_exception_handler(request: Request, exc: DomainException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message}
    )

# Static files
app.mount("/static", StaticFiles(directory=str(ROOT_DIR / "app" / "static")), name="static")
app.mount("/uploads", StaticFiles(directory=str(settings.resolved_uploads_dir)), name="uploads")

# Include feature routers
app.include_router(auth_router)
app.include_router(products_router)
app.include_router(carts_router)
app.include_router(recognition_router)
app.include_router(sessions_router)
app.include_router(live_scan_router)

@app.get("/")
def home():
    return FileResponse(ROOT_DIR / "app" / "static" / "index.html")

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "message": "Live camera scanner API ready; models load on first inference request."
    }
