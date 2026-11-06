"""
PikVaidya AI — Agricultural Microclimate & Weather Intelligence Service
========================================================================
Enterprise-grade modular weather service integrating real-time telemetry,
modeled root-zone soil hydrology, multi-lingual agricultural spray safety,
pathogen infection risk models, and IMD meteorological warnings for Maharashtra.
"""

from .schemas import (
    CurrentWeatherPayload,
    SoilTelemetry,
    HourlyForecastItem,
    DailyForecastItem,
    WeatherAlertItem,
    SprayWindowAssessment,
    DiseaseRiskAssessment,
    IrrigationAdvisory,
    ComprehensiveWeatherReport,
)
from .service import WeatherService, weather_service
from .cache import weather_cache
from .normalizer import normalizer
from .locations import (
    MAHARASHTRA_DISTRICTS,
    resolve_location,
    validate_coordinates,
    get_all_districts,
)

__all__ = [
    "WeatherService",
    "weather_service",
    "weather_cache",
    "normalizer",
    "CurrentWeatherPayload",
    "SoilTelemetry",
    "HourlyForecastItem",
    "DailyForecastItem",
    "WeatherAlertItem",
    "SprayWindowAssessment",
    "DiseaseRiskAssessment",
    "IrrigationAdvisory",
    "ComprehensiveWeatherReport",
    "MAHARASHTRA_DISTRICTS",
    "resolve_location",
    "validate_coordinates",
    "get_all_districts",
]

