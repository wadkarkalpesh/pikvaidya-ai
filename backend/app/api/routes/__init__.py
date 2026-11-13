from datetime import datetime, timezone
from fastapi import APIRouter
from app.api.routes import (
    auth,
    farmer,
    farms,
    crops,
    diagnostics,
    diseases,
    advisory,
    assistant,
    weather,
    multimodal,
    crop_health,
    models,
    notifications,
    experts,
    admin,
    risk,
    sync,
)

api_router = APIRouter()

# Core Domain Routes
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(farmer.router, prefix="/farmer", tags=["Farmer Profile"])
api_router.include_router(farmer.router, prefix="/farmers", tags=["Farmer Profile"], include_in_schema=False)
api_router.include_router(farms.router, prefix="/farms", tags=["Farm Management"])
api_router.include_router(crops.router, tags=["Crop-Cycle Management"])
api_router.include_router(diagnostics.router, tags=["Crop Diagnostics"])
api_router.include_router(diseases.router, tags=["Disease Knowledge Base"])
api_router.include_router(advisory.router, tags=["Agricultural Advisory Engine"])
api_router.include_router(assistant.router, tags=["Agricultural RAG Assistant"])
api_router.include_router(weather.router, tags=["Agricultural Microclimate & Weather"])
api_router.include_router(multimodal.router, tags=["Multimodal Crop-Health Prediction Engine"])
api_router.include_router(crop_health.router, prefix="/crop-health", tags=["Unified Multi-Crop Health Prediction"])

# Expanded Advanced Enterprise Routes
api_router.include_router(models.router, prefix="/models", tags=["AI Models & Architecture"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["Notifications & Alerts"])
api_router.include_router(experts.router, prefix="/experts", tags=["Expert Review & Verification"])
api_router.include_router(admin.router, prefix="/admin", tags=["System Administration & Telemetry"])
api_router.include_router(risk.router, prefix="/risk", tags=["Environmental Disease Risk"])
api_router.include_router(sync.router, tags=["Offline Edge Synchronization"])


@api_router.get("/health", tags=["System"])
def api_v1_health():
    """Versioned health telemetry endpoint."""
    return {
        "status": "healthy",
        "service": "PikVaidya AI API v1",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
