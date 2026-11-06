"""
PikVaidya AI — Abstract Weather Provider Interface
==================================================
Defines the unified adapter contract that all meteorological service
integrations (Open-Meteo, IMD, etc.) must implement.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from .schemas import (
    CurrentWeatherPayload,
    SoilTelemetry,
    HourlyForecastItem,
    DailyForecastItem,
    WeatherAlertItem,
)


class BaseWeatherProvider(ABC):
    """Abstract interface defining the standardized weather provider lifecycle."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Returns unique provider identifier (e.g. 'open-meteo', 'imd')."""
        pass

    @abstractmethod
    async def fetch_current_and_forecast(
        self,
        latitude: float,
        longitude: float,
        location_name: str,
        forecast_days: int = 7,
    ) -> Dict[str, Any]:
        """
        Retrieves real-time current metrics, 24h hourly forecast,
        7-day daily forecast, and soil telemetry for the given coordinates.
        """
        pass

    @abstractmethod
    async def fetch_historical(
        self,
        latitude: float,
        longitude: float,
        start_date: str,
        end_date: str,
    ) -> Dict[str, Any]:
        """
        Fetches historical reanalysis weather data between start_date and end_date (YYYY-MM-DD).
        """
        pass

    @abstractmethod
    async def fetch_weather_alerts(
        self,
        latitude: float,
        longitude: float,
        district: Optional[str] = None,
    ) -> List[WeatherAlertItem]:
        """
        Fetches active official meteorological alerts and warnings for the area.
        """
        pass

