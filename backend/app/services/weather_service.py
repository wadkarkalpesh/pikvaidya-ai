"""
PikVaidya AI — Agricultural Microclimate & Weather Service
==========================================================
Backward-compatible proxy and adapter delegating to the modular
enterprise package `app.services.weather`.
"""

from app.services.weather.schemas import (
    WeatherData,
    SprayWindowAssessment,
    CurrentWeatherPayload,
    SoilTelemetry,
    HourlyForecastItem,
    DailyForecastItem,
    WeatherAlertItem,
    DiseaseRiskAssessment,
    IrrigationAdvisory,
    ComprehensiveWeatherReport,
)
from app.services.weather.service import WeatherService, weather_service
from app.services.weather.locations import (
    MAHARASHTRA_DISTRICTS,
    resolve_location,
    validate_coordinates,
)

__all__ = [
    "WeatherData",
    "SprayWindowAssessment",
    "WeatherService",
    "weather_service",
    "CurrentWeatherPayload",
    "SoilTelemetry",
    "HourlyForecastItem",
    "DailyForecastItem",
    "WeatherAlertItem",
    "DiseaseRiskAssessment",
    "IrrigationAdvisory",
    "ComprehensiveWeatherReport",
    "MAHARASHTRA_DISTRICTS",
    "resolve_location",
    "validate_coordinates",
]
