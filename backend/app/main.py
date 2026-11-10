import logging
import sys
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime, timezone

# Ensure backend directory is on sys.path for direct root execution
_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.api.routes import api_router
from app.api.routes.diseases import router as diseases_router
from app.api.routes.crop_health import router as crop_health_router
from app.core.config import settings
from app.services.model_service import model_service

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager: Pre-loads the primary ML model once at application startup."""
    try:
        model_service.load_model()
        logger.info(f"Model successfully loaded at application startup: {model_service.model_version}")
    except Exception as e:
        logger.warning(f"Could not pre-load model at application startup: {e}")
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Explainable Multimodal Agricultural Decision-Support Platform API",
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Set all CORS enabled origins
if settings.CORS_ORIGINS:
    has_wildcard = "*" in settings.CORS_ORIGINS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=not has_wildcard,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# Include API Router (under /api/v1)
app.include_router(api_router, prefix=settings.API_V1_STR)

# Mount unversioned endpoints under /api for platform contracts
app.include_router(diseases_router, prefix="/api", include_in_schema=False)
app.include_router(crop_health_router, prefix="/api/crop-health", tags=["Unified Multi-Crop Health Prediction"])


# Static file serving for uploaded images and generated Grad-CAM overlays
uploads_dir = Path("uploads")
uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

# Model serving for Edge AI / PWA offline model caching
models_dir = Path("models")
if models_dir.exists():
    app.mount("/models", StaticFiles(directory=str(models_dir)), name="models")

# Frontend static asset serving (if compiled)
frontend_dist = _backend_dir.parent / "frontend" / "dist"
if not frontend_dist.exists():
    frontend_dist = Path("frontend/dist")

if frontend_dist.exists() and (frontend_dist / "index.html").exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")
    app.mount("/dashboard", StaticFiles(directory=str(frontend_dist), html=True), name="dashboard")


@app.get("/", tags=["System"])
def root():
    if frontend_dist.exists() and (frontend_dist / "index.html").exists():
        return FileResponse(str(frontend_dist / "index.html"))
    return {
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs_url": "/docs",
        "api_v1_prefix": settings.API_V1_STR,
        "status": "online"
    }


@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
