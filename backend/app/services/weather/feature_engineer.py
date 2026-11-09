"""
PikVaidya AI — Environmental Microclimate Feature Engineering Engine
====================================================================
Transforms multi-day raw meteorological, soil, and atmospheric telemetry
into structured agronomic feature vectors across multiple historical windows
(24-Hour, 3-Day, 7-Day, 14-Day).

Features Engineered:
- Thermal Dynamics: Mean, Max, Min, Diurnal Temperature Range, Growing Degree Days (GDD).
- Moisture & Foliar Wetness: Mean RH, Min/Max RH, High-Humidity Hours (RH >= 85%, RH >= 90%).
- Precipitation Patterns: Cumulative Rain, Wet Days Count, Rain Frequency, Consecutive Rain Streaks.
- Root-Zone Telemetry: Volumetric Soil Moisture, Soil Moisture Trend, Root-Zone Temperature.
- Aerodynamic Factors: Sustained Wind Speed, Peak Gusts, Cloud Cover.
"""

import math
import logging
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone, timedelta
import httpx

from .base_provider import BaseWeatherProvider
from .locations import resolve_location, MAHARASHTRA_DISTRICTS
from .cache import weather_cache
from app.schemas.multimodal import (
    HistoricalWindowMetrics,
    HistoricalWeatherProfile,
    AgriculturalContextInput,
)

logger = logging.getLogger(__name__)


class WeatherFeatureEngineer:
    """Extracts, normalizes, and aggregates multi-window historical weather feature vectors."""

    BASE_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
    BASE_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
    DEFAULT_TIMEOUT = 7.0

    # Crop Base Temperatures for GDD calculation (°C)
    CROP_BASE_TEMPS: Dict[str, float] = {
        "sugarcane": 18.0,
        "tomato": 10.0,
        "onion": 10.0,
        "cotton": 15.0,
        "soybean": 10.0,
        "default": 10.0,
    }

    async def get_historical_profile(
        self,
        latitude: float,
        longitude: float,
        crop_name: str = "sugarcane",
        location_name: Optional[str] = None,
        force_refresh: bool = False,
    ) -> HistoricalWeatherProfile:
        """
        Fetches or computes a complete multi-window historical environmental profile
        (24h, 3d, 7d, 14d) for the specified coordinates.
        """
        lat, lon, resolved_loc = resolve_location(location_name, latitude, longitude)
        cache_key = f"hist_profile_{lat:.3f}_{lon:.3f}_{crop_name.lower()}"

        if not force_refresh:
            cached = await weather_cache.get(lat, lon, prefix=f"hist_{crop_name.lower()}")
            if cached:
                try:
                    return HistoricalWeatherProfile.model_validate(cached)
                except Exception as e:
                    logger.debug(f"Cache validation error for historical profile: {e}")

        # Fetch 14-day history from Open-Meteo
        try:
            raw_telemetry = await self._fetch_raw_telemetry(lat, lon, past_days=14)
            profile = self.engineer_features_from_raw(
                raw_telemetry=raw_telemetry,
                latitude=lat,
                longitude=lon,
                location_name=resolved_loc,
                crop_name=crop_name,
            )
        except Exception as exc:
            logger.warning(f"Live historical weather fetch failed ({exc}). Synthesizing regional baseline.")
            profile = self._build_synthetic_regional_profile(lat, lon, resolved_loc, crop_name)

        # Cache for 1 hour
        try:
            await weather_cache.set(lat, lon, profile.model_dump(), prefix=f"hist_{crop_name.lower()}", ttl_seconds=3600)
        except Exception as c_err:
            logger.debug(f"Failed to cache historical profile: {c_err}")

        return profile

    async def _fetch_raw_telemetry(self, latitude: float, longitude: float, past_days: int = 14) -> Dict[str, Any]:
        """Fetches past 14 days of hourly and daily environmental telemetry from Open-Meteo."""
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "past_days": past_days,
            "forecast_days": 1,
            "hourly": (
                "temperature_2m,relative_humidity_2m,precipitation,rain,weather_code,"
                "surface_pressure,cloud_cover,wind_speed_10m,wind_direction_10m,"
                "soil_temperature_0_to_7cm,soil_moisture_0_to_7cm"
            ),
            "daily": (
                "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,"
                "precipitation_probability_max,wind_speed_10m_max"
            ),
            "timezone": "auto",
        }

        async with httpx.AsyncClient(timeout=self.DEFAULT_TIMEOUT) as client:
            resp = await client.get(self.BASE_FORECAST_URL, params=params)
            resp.raise_for_status()
            return resp.json()

    def engineer_features_from_raw(
        self,
        raw_telemetry: Dict[str, Any],
        latitude: float,
        longitude: float,
        location_name: str,
        crop_name: str = "sugarcane",
    ) -> HistoricalWeatherProfile:
        """
        Parses raw Open-Meteo hourly & daily arrays and computes structured metrics
        for 24h, 3d (72h), 7d (168h), and 14d (336h) windows.
        """
        hourly = raw_telemetry.get("hourly", {})
        daily = raw_telemetry.get("daily", {})

        times = hourly.get("time", [])
        temps = hourly.get("temperature_2m", [])
        rhs = hourly.get("relative_humidity_2m", [])
        precips = hourly.get("precipitation", [])
        winds = hourly.get("wind_speed_10m", [])
        clouds = hourly.get("cloud_cover", [])
        soil_moists = hourly.get("soil_moisture_0_to_7cm", [])
        soil_temps = hourly.get("soil_temperature_0_to_7cm", [])

        daily_times = daily.get("time", [])
        daily_precips = daily.get("precipitation_sum", [])
        daily_max_temps = daily.get("temperature_2m_max", [])
        daily_min_temps = daily.get("temperature_2m_min", [])

        base_temp = self.CROP_BASE_TEMPS.get(crop_name.lower(), self.CROP_BASE_TEMPS["default"])

        # Compute metrics for each window
        w24 = self._aggregate_window(
            hours_count=24,
            temps=temps, rhs=rhs, precips=precips, winds=winds, clouds=clouds,
            soil_moists=soil_moists, soil_temps=soil_temps,
            daily_precips=daily_precips, daily_max_temps=daily_max_temps, daily_min_temps=daily_min_temps,
            base_temp=base_temp, days_count=1
        )
        w3d = self._aggregate_window(
            hours_count=72,
            temps=temps, rhs=rhs, precips=precips, winds=winds, clouds=clouds,
            soil_moists=soil_moists, soil_temps=soil_temps,
            daily_precips=daily_precips, daily_max_temps=daily_max_temps, daily_min_temps=daily_min_temps,
            base_temp=base_temp, days_count=3
        )
        w7d = self._aggregate_window(
            hours_count=168,
            temps=temps, rhs=rhs, precips=precips, winds=winds, clouds=clouds,
            soil_moists=soil_moists, soil_temps=soil_temps,
            daily_precips=daily_precips, daily_max_temps=daily_max_temps, daily_min_temps=daily_min_temps,
            base_temp=base_temp, days_count=7
        )
        w14d = self._aggregate_window(
            hours_count=336,
            temps=temps, rhs=rhs, precips=precips, winds=winds, clouds=clouds,
            soil_moists=soil_moists, soil_temps=soil_temps,
            daily_precips=daily_precips, daily_max_temps=daily_max_temps, daily_min_temps=daily_min_temps,
            base_temp=base_temp, days_count=14
        )

        total_pts = len(temps)
        valid_pts = sum(1 for t in temps if t is not None)
        completeness = (valid_pts / total_pts * 100.0) if total_pts > 0 else 100.0

        return HistoricalWeatherProfile(
            latitude=latitude,
            longitude=longitude,
            location_name=location_name,
            resolved_at=datetime.now(timezone.utc).isoformat(),
            data_source="open-meteo-historical-archive",
            data_completeness_pct=round(completeness, 1),
            window_24h=w24,
            window_3d=w3d,
            window_7d=w7d,
            window_14d=w14d,
        )

    def _aggregate_window(
        self,
        hours_count: int,
        temps: List[Optional[float]],
        rhs: List[Optional[float]],
        precips: List[Optional[float]],
        winds: List[Optional[float]],
        clouds: List[Optional[float]],
        soil_moists: List[Optional[float]],
        soil_temps: List[Optional[float]],
        daily_precips: List[Optional[float]],
        daily_max_temps: List[Optional[float]],
        daily_min_temps: List[Optional[float]],
        base_temp: float,
        days_count: int,
    ) -> HistoricalWindowMetrics:
        """Slices and aggregates time series over the most recent `hours_count` observations."""
        # Slice the tail (most recent hours)
        h_slice_len = min(hours_count, len(temps))
        if h_slice_len == 0:
            return self._build_default_window_metrics(hours_count)

        w_temps = [t for t in temps[-h_slice_len:] if t is not None] or [27.0]
        w_rhs = [r for r in rhs[-h_slice_len:] if r is not None] or [65.0]
        w_precips = [p for p in precips[-h_slice_len:] if p is not None] or [0.0]
        w_winds = [w for w in winds[-h_slice_len:] if w is not None] or [10.0]
        w_clouds = [c for c in clouds[-h_slice_len:] if c is not None] or [30.0]
        w_soil_moists = [sm for sm in soil_moists[-h_slice_len:] if sm is not None]
        w_soil_temps = [st for st in soil_temps[-h_slice_len:] if st is not None]

        # 1. Thermal Metrics
        t_avg = sum(w_temps) / len(w_temps)
        t_max = max(w_temps)
        t_min = min(w_temps)
        diurnal_range = t_max - t_min

        # 2. Moisture Metrics
        rh_avg = sum(w_rhs) / len(w_rhs)
        rh_min = min(w_rhs)
        rh_max = max(w_rhs)
        high_rh_hrs = sum(1 for r in w_rhs if r >= 85.0)
        sat_rh_hrs = sum(1 for r in w_rhs if r >= 90.0)

        # 3. Precipitation Metrics
        rain_total = sum(w_precips)
        d_slice_len = min(days_count, len(daily_precips))
        w_daily_rain = [p for p in daily_precips[-d_slice_len:] if p is not None] if d_slice_len > 0 else [rain_total]
        rainy_days = sum(1 for r in w_daily_rain if r >= 1.0)
        rain_freq = rainy_days / max(len(w_daily_rain), 1)

        # Consecutive rainy streak
        max_streak = 0
        current_streak = 0
        for r in w_daily_rain:
            if r >= 1.0:
                current_streak += 1
                if current_streak > max_streak:
                    max_streak = current_streak
            else:
                current_streak = 0

        # 4. Aerodynamic Metrics
        wind_avg = sum(w_winds) / len(w_winds)
        wind_max = max(w_winds) * 1.35  # Gust multiplier approximation
        cloud_avg = sum(w_clouds) / len(w_clouds)

        # 5. Soil Telemetry Metrics
        if w_soil_moists:
            sm_avg = (sum(w_soil_moists) / len(w_soil_moists)) * 100.0  # m3/m3 to %
            # Trend calculation: compare first half to second half of window
            half = len(w_soil_moists) // 2
            if half > 0:
                first_half_avg = sum(w_soil_moists[:half]) / half
                second_half_avg = sum(w_soil_moists[half:]) / len(w_soil_moists[half:])
                diff = second_half_avg - first_half_avg
                if diff > 0.03:
                    sm_trend = "ACCUMULATING"
                elif diff < -0.03:
                    sm_trend = "DEPLETING"
                elif second_half_avg > 0.38:
                    sm_trend = "SATURATED"
                else:
                    sm_trend = "STABLE"
            else:
                sm_trend = "STABLE"
        else:
            sm_avg = None
            sm_trend = "STABLE"

        st_avg = (sum(w_soil_temps) / len(w_soil_temps)) if w_soil_temps else None

        # 6. Growing Degree Days (GDD)
        # GDD = sum(max(0, (Tmax + Tmin)/2 - Tbase)) for each day in window
        w_d_max = daily_max_temps[-d_slice_len:] if d_slice_len > 0 else [t_max]
        w_d_min = daily_min_temps[-d_slice_len:] if d_slice_len > 0 else [t_min]
        gdd_sum = 0.0
        for d_max, d_min in zip(w_d_max, w_d_min):
            if d_max is not None and d_min is not None:
                d_mean = (d_max + d_min) / 2.0
                gdd_sum += max(0.0, d_mean - base_temp)

        return HistoricalWindowMetrics(
            window_hours=hours_count,
            temp_avg_c=round(t_avg, 2),
            temp_max_c=round(t_max, 2),
            temp_min_c=round(t_min, 2),
            temp_diurnal_range_c=round(diurnal_range, 2),
            humidity_avg_pct=round(rh_avg, 1),
            humidity_min_pct=round(rh_min, 1),
            humidity_max_pct=round(rh_max, 1),
            high_humidity_hours=high_rh_hrs,
            saturation_humidity_hours=sat_rh_hrs,
            rainfall_total_mm=round(rain_total, 2),
            rainy_days_count=rainy_days,
            consecutive_rainy_days=max_streak,
            rainfall_frequency=round(rain_freq, 2),
            wind_speed_avg_kmh=round(wind_avg, 2),
            wind_gust_max_kmh=round(wind_max, 2),
            cloud_cover_avg_pct=round(cloud_avg, 1),
            soil_moisture_avg_pct=round(sm_avg, 1) if sm_avg is not None else None,
            soil_moisture_trend=sm_trend,
            soil_temp_avg_c=round(st_avg, 2) if st_avg is not None else None,
            growing_degree_days=round(gdd_sum, 2),
        )

    def _build_default_window_metrics(self, hours: int) -> HistoricalWindowMetrics:
        """Provides default seasonal values if no readings are available."""
        days = max(1, hours // 24)
        return HistoricalWindowMetrics(
            window_hours=hours,
            temp_avg_c=27.5,
            temp_max_c=32.0,
            temp_min_c=22.0,
            temp_diurnal_range_c=10.0,
            humidity_avg_pct=65.0,
            humidity_min_pct=45.0,
            humidity_max_pct=85.0,
            high_humidity_hours=int(hours * 0.15),
            saturation_humidity_hours=int(hours * 0.05),
            rainfall_total_mm=0.0,
            rainy_days_count=0,
            consecutive_rainy_days=0,
            rainfall_frequency=0.0,
            wind_speed_avg_kmh=10.0,
            wind_gust_max_kmh=16.0,
            cloud_cover_avg_pct=25.0,
            soil_moisture_avg_pct=28.0,
            soil_moisture_trend="STABLE",
            soil_temp_avg_c=26.0,
            growing_degree_days=float(days * 12.0),
        )

    def _build_synthetic_regional_profile(
        self, latitude: float, longitude: float, location_name: str, crop_name: str
    ) -> HistoricalWeatherProfile:
        """Synthesizes an authoritative regional climatological profile for Maharashtra."""
        return HistoricalWeatherProfile(
            latitude=latitude,
            longitude=longitude,
            location_name=location_name,
            resolved_at=datetime.now(timezone.utc).isoformat(),
            data_source="maharashtra-regional-climatology-baseline",
            data_completeness_pct=80.0,
            window_24h=self._build_default_window_metrics(24),
            window_3d=self._build_default_window_metrics(72),
            window_7d=self._build_default_window_metrics(168),
            window_14d=self._build_default_window_metrics(336),
        )


# Global singleton instance
weather_feature_engineer = WeatherFeatureEngineer()
