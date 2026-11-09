from fastapi import APIRouter
from app.api.routes import auth, farmer, farms, crops, diagnostics, diseases, advisory, assistant, weather, multimodal, crop_health

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(farmer.router, prefix="/farmer", tags=["Farmer Profile"])
api_router.include_router(farms.router, prefix="/farms", tags=["Farm Management"])
api_router.include_router(crops.router, tags=["Crop-Cycle Management"])
api_router.include_router(diagnostics.router, tags=["Crop Diagnostics"])
api_router.include_router(diseases.router, tags=["Disease Knowledge Base"])
api_router.include_router(advisory.router, tags=["Agricultural Advisory Engine"])
api_router.include_router(assistant.router, tags=["Agricultural RAG Assistant"])
api_router.include_router(weather.router, tags=["Agricultural Microclimate & Weather"])
api_router.include_router(multimodal.router, tags=["Multimodal Crop-Health Prediction Engine"])
api_router.include_router(crop_health.router, prefix="/crop-health", tags=["Unified Multi-Crop Health Prediction"])



