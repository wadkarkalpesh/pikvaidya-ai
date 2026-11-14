"""
PikVaidya AI — Environmental Crop-Health Risk API
=================================================
Dedicated REST endpoints evaluating microclimatic disease conduciveness,
Tom-Cast DSV, Wallin Late Blight, and physiological crop stress.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, status

from app.services.weather.locations import resolve_location, MAHARASHTRA_DISTRICTS
from app.services.weather.feature_engineer import weather_feature_engineer
from app.services.weather.crop_health_risk import weather_crop_health_risk_engine

router = APIRouter()


class EnvironmentalRiskRequest(BaseModel):
    crop: str = Field(..., description="Target crop: sugarcane, tomato, or onion")
    district: Optional[str] = Field(None, description="Maharashtra district name")
    latitude: Optional[float] = Field(None, description="Field latitude")
    longitude: Optional[float] = Field(None, description="Field longitude")
    growth_stage: Optional[str] = Field(None, description="Optional crop growth stage")
    soil_type: Optional[str] = Field(None, description="Optional soil classification")


@router.post("/environmental", response_model=Dict[str, Any], summary="Assess environmental disease risk")
async def evaluate_environmental_risk(payload: EnvironmentalRiskRequest):
    """
    Evaluates microclimate and 14-day rolling historical epidemiological risk.
    Crucial: Distinguishes environmental conduciveness from confirmed foliar diagnosis.
    """
    normalized_crop = payload.crop.strip().lower()
    if normalized_crop not in ("sugarcane", "tomato", "onion"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported crop '{payload.crop}'. Supported: sugarcane, tomato, onion."
        )

    # Resolve coordinates
    resolved_lat, resolved_lon, loc_name = resolve_location(
        location_query=payload.district,
        latitude=payload.latitude,
        longitude=payload.longitude,
    )

    # Fetch 14-day rolling agrometeorological profile
    weather_profile = await weather_feature_engineer.get_historical_profile(
        latitude=resolved_lat,
        longitude=resolved_lon,
        location_name=loc_name,
    )

    # Compute crop-specific environmental risk
    assessment = weather_crop_health_risk_engine.evaluate_weather_risk(
        crop_name=normalized_crop,
        profile=weather_profile,
    )

    return {
        "crop": normalized_crop,
        "location": {
            "name": loc_name,
            "latitude": resolved_lat,
            "longitude": resolved_lon,
        },
        "environmental_risk_level": assessment.dominant_weather_risk,
        "overall_disease_pressure": assessment.overall_disease_pressure,
        "is_safe_to_spray": assessment.is_safe_to_spray,
        "spray_suitability": assessment.spray_suitability,
        "spray_guidance": assessment.spray_guidance,
        "epidemiological_conduciveness": [
            {
                "disease": getattr(d, "disease_name_en", getattr(d, "disease_name", "Unknown")),
                "disease_name_mr": getattr(d, "disease_name_mr", ""),
                "conduciveness_score": d.conduciveness_score,
                "risk_tier": d.risk_tier,
                "favourable_conditions_met": d.favourable_conditions_met,
                "epidemiological_rationale": d.epidemiological_rationale,
            }
            for d in assessment.disease_conduciveness_profile
        ],
        "weather_summary": assessment.weather_summary,
        "disclaimer": "Environmental risk indicates disease-favourable microclimates only; it does not confirm physical pathogen presence on foliage."
    }


@router.get("/districts", response_model=List[str], summary="List monitored Maharashtra districts")
def list_monitored_districts():
    """Returns list of supported agrarian districts in Maharashtra."""
    return list(MAHARASHTRA_DISTRICTS.keys())
