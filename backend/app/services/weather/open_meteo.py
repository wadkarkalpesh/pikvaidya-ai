"""
PikVaidya AI — Open-Meteo Weather Provider Adapter
==================================================
Implements primary weather and microclimate data retrieval using the
Open-Meteo REST API (Forecast and Historical Archive).
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import httpx

from .base_provider import BaseWeatherProvider
from .normalizer import normalizer
from .schemas import (
    CurrentWeatherPayload,
    SoilTelemetry,
    HourlyForecastItem,
    DailyForecastItem,
    WeatherAlertItem,
)

logger = logging.getLogger(__name__)


class OpenMeteoProvider(BaseWeatherProvider):
    """
    Open-Meteo API Provider Implementation.
    Delivers free, open-access, non-commercial meteorological and soil data without requiring API keys.
    """

    BASE_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
    BASE_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
    DEFAULT_TIMEOUT = 6.0
    MAX_RETRIES = 2

    @property
    def provider_name(self) -> str:
        return "open-meteo"

    async def _get_with_retry(self, url: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Executes HTTP GET with timeout handling and exponential backoff retry."""
        last_error = None
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=self.DEFAULT_TIMEOUT) as client:
                    resp = await client.get(url, params=params)
                    if resp.status_code == 200:
                        return resp.json()
                    elif resp.status_code == 429:
                        logger.warning(f"Open-Meteo rate limit reached (HTTP 429).")
                        raise RuntimeError("Weather provider rate limited.")
                    else:
                        logger.warning(f"Open-Meteo returned status {resp.status_code}: {resp.text[:120]}")
                        resp.raise_for_status()
            except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as exc:
                last_error = exc
                if attempt < self.MAX_RETRIES:
                    backoff = 0.5 * (2 ** attempt)
                    logger.info(f"Open-Meteo transient error ({exc}). Retrying in {backoff}s...")
                    await asyncio.sleep(backoff)
                else:
                    logger.error(f"Open-Meteo request failed after {self.MAX_RETRIES + 1} attempts: {exc}")

        raise last_error or RuntimeError("Open-Meteo request failed.")

    async def fetch_current_and_forecast(
        self,
        latitude: float,
        longitude: float,
        location_name: str,
        forecast_days: int = 7,
    ) -> Dict[str, Any]:
        """
        Fetches full meteorological telemetry including current, hourly, daily, and soil.
        """
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": (
                "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,rain,"
                "weather_code,surface_pressure,cloud_cover,wind_speed_10m,wind_direction_10m,wind_gusts_10m"
            ),
            "hourly": (
                "temperature_2m,relative_humidity_2m,precipitation_probability,precipitation,"
                "weather_code,wind_speed_10m,soil_temperature_0_to_7cm,soil_moisture_0_to_7cm"
            ),
            "daily": (
                "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,"
                "precipitation_probability_max,wind_speed_10m_max"
            ),
            "forecast_days": min(max(forecast_days, 1), 7),
            "timezone": "auto",
        }

        raw = await self._get_with_retry(self.BASE_FORECAST_URL, params)
        now_iso = datetime.now(timezone.utc).isoformat()

        curr_raw = raw.get("current", {})
        hourly_raw = raw.get("hourly", {})
        daily_raw = raw.get("daily", {})

        # 1. Parse Current Weather
        w_code = int(curr_raw.get("weather_code", 0))
        precip_probs = hourly_raw.get("precipitation_probability", [0])
        next_6h_prob = float(max(precip_probs[:6])) if precip_probs else 0.0

        current_payload = CurrentWeatherPayload(
            temperature_c=round(float(curr_raw.get("temperature_2m", 28.0)), 1),
            apparent_temperature_c=round(float(curr_raw.get("apparent_temperature", curr_raw.get("temperature_2m", 28.0))), 1),
            relative_humidity_pct=round(float(curr_raw.get("relative_humidity_2m", 65.0)), 1),
            surface_pressure_hpa=normalizer.normalize_pressure(curr_raw.get("surface_pressure")),
            cloud_cover_pct=round(float(curr_raw.get("cloud_cover", 0.0)), 1),
            wind_speed_kmh=round(float(curr_raw.get("wind_speed_10m", 8.0)), 1),
            wind_direction_deg=round(float(curr_raw.get("wind_direction_10m", 0.0)), 1),
            wind_gusts_kmh=round(float(curr_raw.get("wind_gusts_10m", curr_raw.get("wind_speed_10m", 8.0))), 1),
            precipitation_mm=round(float(curr_raw.get("precipitation", 0.0)), 1),
            precipitation_probability_6h=round(next_6h_prob, 1),
            weather_condition=normalizer.get_wmo_description(w_code, "en"),
            weather_code=w_code,
            is_live=True,
            data_source=self.provider_name,
            fetched_at=now_iso,
            latitude=latitude,
            longitude=longitude,
            location_name=location_name,
        )

        # 2. Parse Soil Telemetry (Modeled ERA5-Land Land-Surface Data)
        soil_payload = None
        soil_temps = hourly_raw.get("soil_temperature_0_to_7cm", [])
        soil_moists = hourly_raw.get("soil_moisture_0_to_7cm", [])
        if soil_moists and len(soil_moists) > 0:
            current_sm = float(soil_moists[0])
            current_st = float(soil_temps[0]) if soil_temps else current_payload.temperature_c - 1.5
            sm_status, sm_desc = normalizer.categorize_soil_moisture(current_sm)

            soil_payload = SoilTelemetry(
                soil_temperature_c=round(current_st, 1),
                soil_moisture_m3m3=round(current_sm, 3),
                soil_moisture_percentage=round(current_sm * 100.0, 1),
                is_modeled=True,
                moisture_status=sm_status,
                description=sm_desc,
            )

        # 3. Parse Next 24 Hours Forecast
        hourly_items: List[HourlyForecastItem] = []
        times = hourly_raw.get("time", [])[:24]
        h_temps = hourly_raw.get("temperature_2m", [])[:24]
        h_rhs = hourly_raw.get("relative_humidity_2m", [])[:24]
        h_probs = hourly_raw.get("precipitation_probability", [])[:24]
        h_precips = hourly_raw.get("precipitation", [])[:24]
        h_winds = hourly_raw.get("wind_speed_10m", [])[:24]
        h_codes = hourly_raw.get("weather_code", [])[:24]

        for i in range(len(times)):
            c_code = int(h_codes[i]) if i < len(h_codes) else 0
            hourly_items.append(
                HourlyForecastItem(
                    time=times[i],
                    temperature_c=round(float(h_temps[i]), 1) if i < len(h_temps) else 25.0,
                    relative_humidity_pct=round(float(h_rhs[i]), 1) if i < len(h_rhs) else 60.0,
                    precipitation_probability=round(float(h_probs[i]), 1) if i < len(h_probs) else 0.0,
                    precipitation_mm=round(float(h_precips[i]), 1) if i < len(h_precips) else 0.0,
                    wind_speed_kmh=round(float(h_winds[i]), 1) if i < len(h_winds) else 5.0,
                    weather_condition=normalizer.get_wmo_description(c_code, "en"),
                    weather_code=c_code,
                )
            )

        # 4. Parse 7-Day Daily Forecast
        daily_items: List[DailyForecastItem] = []
        d_dates = daily_raw.get("time", [])[:7]
        d_codes = daily_raw.get("weather_code", [])[:7]
        d_maxs = daily_raw.get("temperature_2m_max", [])[:7]
        d_mins = daily_raw.get("temperature_2m_min", [])[:7]
        d_sums = daily_raw.get("precipitation_sum", [])[:7]
        d_probs = daily_raw.get("precipitation_probability_max", [])[:7]
        d_winds = daily_raw.get("wind_speed_10m_max", [])[:7]

        for i in range(len(d_dates)):
            dc_code = int(d_codes[i]) if i < len(d_codes) else 0
            daily_items.append(
                DailyForecastItem(
                    date=d_dates[i],
                    weather_code=dc_code,
                    weather_condition=normalizer.get_wmo_description(dc_code, "en"),
                    temp_max_c=round(float(d_maxs[i]), 1) if i < len(d_maxs) else 30.0,
                    temp_min_c=round(float(d_mins[i]), 1) if i < len(d_mins) else 20.0,
                    precipitation_sum_mm=round(float(d_sums[i]), 1) if i < len(d_sums) else 0.0,
                    precipitation_probability_max=round(float(d_probs[i]), 1) if i < len(d_probs) else 0.0,
                    wind_speed_max_kmh=round(float(d_winds[i]), 1) if i < len(d_winds) else 10.0,
                )
            )

        return {
            "current": current_payload,
            "soil": soil_payload,
            "hourly_24h": hourly_items,
            "daily_7d": daily_items,
        }

    async def fetch_historical(
        self,
        latitude: float,
        longitude: float,
        start_date: str,
        end_date: str,
    ) -> Dict[str, Any]:
        """Fetches historical reanalysis weather data via Open-Meteo Archive with resilient fallback."""
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": start_date,
            "end_date": end_date,
            "hourly": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,soil_temperature_0_to_7cm",
            "timezone": "auto",
        }
        try:
            return await self._get_with_retry(self.BASE_ARCHIVE_URL, params)
        except Exception as exc:
            logger.warning(f"Archive API unavailable ({exc}). Returning regional agro-climatic baseline.")
            return {
                "latitude": latitude,
                "longitude": longitude,
                "timezone": "auto",
                "hourly": {
                    "time": [f"{start_date}T00:00", f"{start_date}T06:00", f"{start_date}T12:00", f"{start_date}T18:00"],
                    "temperature_2m": [22.0, 24.5, 31.0, 26.5],
                    "relative_humidity_2m": [75.0, 65.0, 48.0, 60.0],
                    "precipitation": [0.0, 0.0, 0.0, 0.0],
                    "wind_speed_10m": [7.5, 9.0, 12.0, 8.5],
                    "soil_temperature_0_to_7cm": [21.5, 23.0, 28.5, 25.0],
                },
                "is_fallback": True,
                "fallback_reason": str(exc),
            }


    async def fetch_weather_alerts(
        self,
        latitude: float,
        longitude: float,
        district: Optional[str] = None,
    ) -> List[WeatherAlertItem]:
        """Open-Meteo does not emit official government alerts; alert synthesis handled by alert rules."""
        return []
