from fastapi import APIRouter
from app.api.routes import auth, farmer, farms, crops

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(farmer.router, prefix="/farmer", tags=["Farmer Profile"])
api_router.include_router(farms.router, prefix="/farms", tags=["Farm Management"])
api_router.include_router(crops.router, tags=["Crop-Cycle Management"])
