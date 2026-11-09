"""
PikVaidya AI — Context-Aware Agricultural Advisory API Routes
=============================================================
Provides endpoints for:
1. POST /api/v1/advisory/generate - Context-aware farmer recommendations
2. GET  /api/v1/advisory/weather  - Live microclimate retrieval & spray window assessment
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.services.weather_service import weather_service
from app.services.recommendation_engine import recommendation_engine
from app.services.report_service import report_service
from app.schemas.advisory import (
    AdvisoryGenerateRequest,
    ContextualAdvisoryResponse,
    WeatherTelemetrySchema,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/advisory", tags=["Agricultural Advisory Engine"])


@router.post(
    "/generate",
    response_model=ContextualAdvisoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate Context-Aware Agricultural Advisory",
    description=(
        "Synthesizes machine-learning vision predictions, authoritative ICAR/CIBRC disease data, "
        "and real-time weather microclimate into actionable multilingual agronomic recommendations."
    ),
)
async def generate_agricultural_advisory(
    request: AdvisoryGenerateRequest,
    db: Session = Depends(get_db),
) -> ContextualAdvisoryResponse:
    """Generates an end-to-end, context-aware farmer recommendation."""
    return await recommendation_engine.generate_advisory(request, db=db)


@router.get(
    "/weather",
    response_model=WeatherTelemetrySchema,
    status_code=status.HTTP_200_OK,
    summary="Retrieve Farm Microclimate & Spray Window Status",
    description=(
        "Fetches ambient temperature, humidity, wind speed, and rain probability "
        "and evaluates whether current weather is safe for foliar spraying."
    ),
)
async def get_farm_microclimate(
    lat: Optional[float] = Query(None, description="Farm latitude coordinate"),
    lon: Optional[float] = Query(None, description="Farm longitude coordinate"),
) -> WeatherTelemetrySchema:
    """Retrieves real-time farm microclimate and spray safety status."""
    weather = await weather_service.get_current_weather(latitude=lat, longitude=lon)
    assessment = weather_service.assess_spray_suitability(weather)

    return WeatherTelemetrySchema(
        temperature_c=weather.temperature_c,
        relative_humidity_pct=weather.relative_humidity_pct,
        wind_speed_kmh=weather.wind_speed_kmh,
        precipitation_mm=weather.precipitation_mm,
        precipitation_probability_6h=weather.precipitation_probability_6h,
        weather_condition=weather.weather_condition,
        is_live=weather.is_live,
        spray_suitability=assessment.status,
        is_safe_to_spray=assessment.is_safe_to_spray,
        fungal_risk_level=assessment.fungal_risk_level,
        spray_guidance={
            "en": assessment.summary_en,
            "mr": assessment.summary_mr,
            "hi": assessment.summary_hi,
        },
    )


@router.post(
    "/pdf",
    status_code=status.HTTP_200_OK,
    summary="Download Official Multilingual Field Advisory PDF",
    description=(
        "Synthesizes diagnostic prediction, weather microclimate, and CIBRC chemical prescriptions "
        "into a downloadable, publication-grade PDF field advisory report."
    ),
)
async def generate_advisory_pdf_report(
    request: AdvisoryGenerateRequest,
    farmer_name: Optional[str] = Query("Registered Farmer", description="Farmer full name"),
    farm_location: Optional[str] = Query("Maharashtra, India", description="Farm district / taluka"),
    db: Session = Depends(get_db),
) -> Response:
    """Generates and streams an authoritative field diagnostic PDF report."""
    advisory = await recommendation_engine.generate_advisory(request, db=db)
    
    coords = None
    if request.latitude is not None and request.longitude is not None:
        coords = f"{request.latitude:.4f}° N, {request.longitude:.4f}° E"

    pdf_bytes = report_service.generate_advisory_pdf(
        advisory=advisory,
        farmer_name=farmer_name,
        farm_location=farm_location,
        farm_coordinates=coords,
    )

    clean_crop = request.crop_name.replace(" ", "_")
    clean_disease = advisory.disease_id.replace(" ", "_")
    filename = f"PikVaidya_Field_Advisory_{clean_crop}_{clean_disease}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Type": "application/pdf",
        },
    )


