"""
PikVaidya AI — Agricultural Weather & Microclimate API Routes
=============================================================
Provides production REST endpoints for:
1. GET /api/v1/weather/current           - Real-time weather, modeled soil moisture & spray status
2. GET /api/v1/weather/forecast          - 24-hour hourly & 7-day daily agricultural forecasts
3. GET /api/v1/weather/district/{name}   - District-level weather for Maharashtra agro-climatic zones
4. GET /api/v1/weather/locations         - List of indexed Maharashtra agricultural districts
5. GET /api/v1/weather/historical        - Historical weather records via Open-Meteo Archive
6. GET /api/v1/weather/alerts            - IMD & meteorological severe weather warnings
"""

import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, Path, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.services.weather import (
    weather_service,
    ComprehensiveWeatherReport,
    CurrentWeatherPayload,
    HourlyForecastItem,
    DailyForecastItem,
    WeatherAlertItem,
    MAHARASHTRA_DISTRICTS,
    resolve_location,
    validate_coordinates,
    get_all_districts,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/weather", tags=["Agricultural Microclimate & Weather"])


@router.get(
    "/current",
    response_model=ComprehensiveWeatherReport,
    status_code=status.HTTP_200_OK,
    summary="Get Current Weather & Soil Telemetry",
    description=(
        "Retrieves real-time atmospheric microclimate, modeled root-zone soil hydrology, "
        "and statutory spray safety evaluation. Supports GPS coordinates or Maharashtra district name."
    ),
)
async def get_current_weather(
    lat: Optional[float] = Query(None, description="Latitude in decimal degrees (-90 to +90)"),
    lon: Optional[float] = Query(None, description="Longitude in decimal degrees (-180 to +180)"),
    district: Optional[str] = Query(None, description="Maharashtra district name (e.g. Pune, Kolhapur)"),
    persist: bool = Query(False, description="Persist observation snapshot to database"),
    db: Session = Depends(get_db),
) -> ComprehensiveWeatherReport:
    """Retrieves comprehensive real-time microclimate intelligence."""
    try:
        resolved_lat, resolved_lon, resolved_name = resolve_location(
            location_query=district,
            latitude=lat,
            longitude=lon
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )

    try:
        report = await weather_service.get_comprehensive_weather(
            latitude=resolved_lat,
            longitude=resolved_lon,
            location_name=resolved_name
        )

        if persist:
            weather_service.record_observation(db=db, report=report)

        return report
    except Exception as exc:
        logger.error(f"Error fetching current weather: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to retrieve weather data: {exc}"
        )


@router.get(
    "/forecast",
    status_code=status.HTTP_200_OK,
    summary="Get Agricultural Weather Forecast",
    description="Provides 24-hour hourly forecast slices and 7-day daily agricultural projections.",
)
async def get_weather_forecast(
    lat: Optional[float] = Query(None, description="Latitude coordinate"),
    lon: Optional[float] = Query(None, description="Longitude coordinate"),
    district: Optional[str] = Query(None, description="District name"),
    days: int = Query(7, ge=1, le=14, description="Forecast horizon in days (1-14)"),
) -> Dict[str, Any]:
    """Retrieves hourly and daily agricultural weather forecast slices."""
    try:
        resolved_lat, resolved_lon, resolved_name = resolve_location(
            location_query=district,
            latitude=lat,
            longitude=lon
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

    try:
        hourly, daily = await weather_service.get_forecast_only(
            latitude=resolved_lat,
            longitude=resolved_lon,
            days=days
        )
        return {
            "location_name": resolved_name,
            "latitude": resolved_lat,
            "longitude": resolved_lon,
            "forecast_days": days,
            "hourly_24h": hourly,
            "daily": daily,
        }
    except Exception as exc:
        logger.error(f"Error fetching forecast: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Forecast generation failed."
        )


@router.get(
    "/district/{district_name}",
    response_model=ComprehensiveWeatherReport,
    status_code=status.HTTP_200_OK,
    summary="Get Weather for Maharashtra District",
    description="Retrieves comprehensive weather for a named Maharashtra agricultural district.",
)
async def get_district_weather(
    district_name: str = Path(..., description="District identifier (e.g. kolhapur, pune, nashik, sangli)"),
    db: Session = Depends(get_db),
) -> ComprehensiveWeatherReport:
    """Retrieves full microclimate profile for a specific Maharashtra district."""
    norm = district_name.strip().lower()
    
    # Check if district exists in registry
    resolved_lat, resolved_lon, resolved_loc = resolve_location(location_query=norm)
    
    report = await weather_service.get_comprehensive_weather(
        latitude=resolved_lat,
        longitude=resolved_lon,
        location_name=resolved_loc
    )
    return report


@router.get(
    "/locations",
    status_code=status.HTTP_200_OK,
    summary="List Pre-Configured Maharashtra Districts",
    description="Returns pre-indexed Maharashtra agricultural districts, coordinates, and agro-climatic zones.",
)
async def list_weather_locations() -> Dict[str, Any]:
    """Returns all pre-indexed Maharashtra districts with agricultural metadata."""
    districts = get_all_districts()
    return {
        "region": "Maharashtra, India",
        "total_districts": len(districts),
        "districts": districts,
    }


@router.get(
    "/historical",
    status_code=status.HTTP_200_OK,
    summary="Query Historical Weather Telemetry",
    description="Retrieves historical daily weather telemetry via Open-Meteo Archive API.",
)
async def get_historical_weather(
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)", pattern=r"^\d{4}-\d{2}-\d{2}$"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)", pattern=r"^\d{4}-\d{2}-\d{2}$"),
    lat: Optional[float] = Query(None, description="Latitude coordinate"),
    lon: Optional[float] = Query(None, description="Longitude coordinate"),
    district: Optional[str] = Query(None, description="Maharashtra district name"),
) -> Dict[str, Any]:
    """Retrieves historical weather records from Open-Meteo Archive API."""
    try:
        resolved_lat, resolved_lon, resolved_name = resolve_location(
            location_query=district,
            latitude=lat,
            longitude=lon
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

    try:
        history = await weather_service.get_historical_weather(
            latitude=resolved_lat,
            longitude=resolved_lon,
            start_date=start_date,
            end_date=end_date
        )
        return {
            "location_name": resolved_name,
            "latitude": resolved_lat,
            "longitude": resolved_lon,
            "start_date": start_date,
            "end_date": end_date,
            "records": history,
        }
    except Exception as exc:
        logger.error(f"Error fetching historical weather: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Historical weather retrieval failed: {exc}"
        )


@router.get(
    "/alerts",
    response_model=List[WeatherAlertItem],
    status_code=status.HTTP_200_OK,
    summary="Get Meteorological Alerts & Government Warnings",
    description="Retrieves active weather warnings and agricultural advisories for the target region.",
)
async def get_weather_alerts(
    lat: Optional[float] = Query(None, description="Latitude coordinate"),
    lon: Optional[float] = Query(None, description="Longitude coordinate"),
    district: Optional[str] = Query(None, description="Maharashtra district name"),
) -> List[WeatherAlertItem]:
    """Retrieves active meteorological alerts from IMD and Open-Meteo."""
    try:
        resolved_lat, resolved_lon, resolved_name = resolve_location(
            location_query=district,
            latitude=lat,
            longitude=lon
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

    alerts = await weather_service.get_weather_alerts(
        latitude=resolved_lat,
        longitude=resolved_lon,
        location_name=resolved_name
    )
    return alerts
