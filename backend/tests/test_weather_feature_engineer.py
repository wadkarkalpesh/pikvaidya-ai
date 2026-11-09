"""
Unit and Integration Tests for Multimodal Weather Feature Engineer
===================================================================
Tests multi-window historical microclimate extraction (24h, 3d, 7d, 14d),
thermal indices, moisture accumulation, rainfall patterns, soil dynamics,
and robust climatological regional fallback under network failures.
"""

import pytest
from unittest.mock import patch
import aiohttp

from app.services.weather.feature_engineer import (
    weather_feature_engineer,
    WeatherFeatureEngineer,
)
from app.schemas.multimodal import (
    HistoricalWeatherProfile,
    HistoricalWindowMetrics,
)


@pytest.mark.anyio
async def test_get_historical_profile_pune():
    """Verifies historical profile retrieval for Pune coordinates."""
    profile = await weather_feature_engineer.get_historical_profile(
        latitude=18.5204,
        longitude=73.8567,
        crop_name="sugarcane",
        location_name="Pune",
    )
    assert isinstance(profile, HistoricalWeatherProfile)
    assert profile.location_name is not None
    assert profile.latitude is not None
    assert profile.longitude is not None

    # Check all four temporal windows exist
    assert profile.window_24h is not None
    assert profile.window_3d is not None
    assert profile.window_7d is not None
    assert profile.window_14d is not None

    # Verify window duration hours
    assert profile.window_24h.window_hours == 24
    assert profile.window_3d.window_hours == 72
    assert profile.window_7d.window_hours == 168
    assert profile.window_14d.window_hours == 336


@pytest.mark.anyio
async def test_multi_window_metric_invariants():
    """Verifies that mathematical and agronomic invariants hold across window scales."""
    profile = await weather_feature_engineer.get_historical_profile(
        latitude=18.5204,
        longitude=73.8567,
        crop_name="tomato",
    )
    
    # Check 14-day vs 7-day vs 24h precipitation monotonicity
    assert profile.window_14d.rainfall_total_mm >= profile.window_7d.rainfall_total_mm - 1e-3
    assert profile.window_7d.rainfall_total_mm >= profile.window_24h.rainfall_total_mm - 1e-3

    # Check relative humidity and temperature bounds
    for w in [profile.window_24h, profile.window_3d, profile.window_7d, profile.window_14d]:
        assert 0.0 <= w.humidity_min_pct <= w.humidity_avg_pct <= w.humidity_max_pct <= 100.0
        assert 0 <= w.high_humidity_hours <= w.window_hours
        assert -10.0 <= w.temp_min_c <= w.temp_avg_c <= w.temp_max_c <= 60.0
        assert w.temp_diurnal_range_c >= 0.0
        assert w.growing_degree_days >= 0.0
        assert 0.0 <= w.rainfall_frequency <= 1.0


def test_engineer_features_from_synthetic_raw():
    """Verifies window feature engineering using a synthetic raw Open-Meteo dictionary."""
    engineer = WeatherFeatureEngineer()
    
    # 336 hours of synthetic telemetry
    hours_count = 336
    synthetic_hourly = {
        "time": [f"2026-11-01T{h%24:02d}:00" for h in range(hours_count)],
        "temperature_2m": [22.0 + (h % 12) for h in range(hours_count)],
        "relative_humidity_2m": [60.0 + (h % 35) for h in range(hours_count)],
        "precipitation": [0.5 if h % 24 == 0 else 0.0 for h in range(hours_count)],
        "wind_speed_10m": [10.0 + (h % 8) for h in range(hours_count)],
        "wind_gusts_10m": [15.0 + (h % 10) for h in range(hours_count)],
        "cloud_cover": [40.0 for _ in range(hours_count)],
        "soil_moisture_0_to_7cm": [0.28 for _ in range(hours_count)],
        "soil_temperature_0_to_7cm": [23.0 for _ in range(hours_count)],
    }
    synthetic_daily = {
        "time": [f"2026-11-{d+1:02d}" for d in range(14)],
        "temperature_2m_max": [32.0 for _ in range(14)],
        "temperature_2m_min": [18.0 for _ in range(14)],
        "precipitation_sum": [1.0 for _ in range(14)],
    }

    raw = {"hourly": synthetic_hourly, "daily": synthetic_daily}
    profile = engineer.engineer_features_from_raw(
        raw_telemetry=raw,
        latitude=19.9975,
        longitude=73.7898,
        location_name="Nashik",
        crop_name="tomato",
    )

    assert isinstance(profile, HistoricalWeatherProfile)
    assert profile.window_24h.temp_avg_c > 0.0
    assert profile.window_7d.rainfall_total_mm > 0.0
    assert profile.window_14d.growing_degree_days > 0.0


def test_synthetic_regional_profile_fallback():
    """Verifies that regional climatological fallback generates complete and valid profiles."""
    engineer = WeatherFeatureEngineer()
    profile = engineer._build_synthetic_regional_profile(
        latitude=16.7050,
        longitude=74.2433,
        location_name="Kolhapur",
        crop_name="sugarcane",
    )
    assert profile.location_name == "Kolhapur"
    assert profile.data_completeness_pct >= 80.0
    assert profile.window_24h.temp_avg_c > 20.0
    assert profile.window_14d.window_hours == 336
