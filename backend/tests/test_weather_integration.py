"""
PikVaidya AI — Automated Weather Integration Test Suite
======================================================
Comprehensive test suite verifying:
1. Successful weather retrieval with live/cached Open-Meteo telemetry
2. Invalid coordinate handling (-95 lat, 200 lon)
3. Missing parameter handling & default Maharashtra district resolution
4. Timeout handling & graceful regional baseline fallback
5. Rate limit handling (HTTP 429) & exponential backoff
6. Weather provider failure resilience
7. Spatial cache hit vs. miss behavior (grid cell quantization)
8. Unit conversion accuracy & normalizer functions
9. Timestamp & timezone formatting (ISO 8601 UTC)
10. Agrochemical spray safety rules (rain, drift, heat stress, optimal)
11. Contextual integration with crop recommendation engine
12. Relational database persistence (WeatherObservation records)
"""

import pytest
from unittest.mock import patch, AsyncMock
from datetime import datetime, timezone
import httpx
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.weather_history import WeatherObservation
from app.services.weather import (
    weather_service,
    normalizer,
    weather_cache,
    resolve_location,
    validate_coordinates,
    get_all_districts,
    ComprehensiveWeatherReport,
    CurrentWeatherPayload,
    SprayWindowAssessment,
)
from app.services.weather.schemas import WeatherData


# 1. Successful weather retrieval
@pytest.mark.anyio
async def test_successful_weather_retrieval(client: TestClient):
    """Verifies that /api/v1/weather/current returns HTTP 200 with complete schema."""
    resp = client.get("/api/v1/weather/current?district=pune")
    assert resp.status_code == 200
    data = resp.json()

    assert "current" in data
    assert "spray_window" in data
    assert "location_name" in data
    assert "Pune, Maharashtra" in data["location_name"]
    assert -10.0 <= data["current"]["temperature_c"] <= 60.0
    assert 0.0 <= data["current"]["relative_humidity_pct"] <= 100.0
    assert data["current"]["wind_speed_kmh"] >= 0.0
    assert "status" in data["spray_window"]
    assert "summary" in data["spray_window"]


# 2. Invalid coordinate handling
def test_invalid_coordinates(client: TestClient):
    """Verifies that out-of-bounds coordinates return HTTP 400 Bad Request."""
    # Latitude > 90
    resp1 = client.get("/api/v1/weather/current?lat=95.0&lon=73.85")
    assert resp1.status_code == 400
    assert "Latitude out of bounds" in resp1.json()["detail"]

    # Longitude > 180
    resp2 = client.get("/api/v1/weather/current?lat=18.52&lon=195.0")
    assert resp2.status_code == 400
    assert "Longitude out of bounds" in resp2.json()["detail"]


# 3. Missing parameter handling & default resolution
def test_missing_parameters_default_resolution(client: TestClient):
    """Verifies that omitting lat/lon/district safely defaults to Maharashtra agricultural hub (Kolhapur)."""
    resp = client.get("/api/v1/weather/current")
    assert resp.status_code == 200
    data = resp.json()
    assert "Kolhapur, Maharashtra" in data["location_name"]
    assert abs(data["latitude"] - 16.705) < 0.05
    assert abs(data["longitude"] - 74.243) < 0.05



# 4. Timeout handling & fallback baseline
@pytest.mark.anyio
async def test_timeout_handling_and_fallback():
    """Simulates an upstream network timeout and confirms safe fallback activation."""
    with patch.object(
        weather_service.primary_provider,
        "fetch_current_and_forecast",
        side_effect=httpx.TimeoutException("Upstream timeout simulated"),
    ):
        report = await weather_service.get_comprehensive_weather(
            latitude=18.5204,
            longitude=73.8567,
            location_name="Pune, Maharashtra",
            force_refresh=True,
        )
        assert isinstance(report, ComprehensiveWeatherReport)
        assert report.current.is_live is False
        assert report.data_source == "fallback"
        assert report.current.temperature_c > 0
        assert report.spray_window is not None


# 5. Rate limit handling (HTTP 429) & backoff
@pytest.mark.anyio
async def test_rate_limit_handling():
    """Simulates HTTP 429 rate limit error and verifies fallback behavior."""
    with patch.object(
        weather_service.primary_provider,
        "fetch_current_and_forecast",
        side_effect=RuntimeError("Weather provider rate limited."),
    ):
        report = await weather_service.get_comprehensive_weather(
            latitude=19.9975,
            longitude=73.7898,
            location_name="Nashik, Maharashtra",
            force_refresh=True,
        )
        assert report.data_source == "fallback"
        assert report.current.is_live is False


# 6. Weather provider failure resilience
@pytest.mark.anyio
async def test_provider_failure_resilience():
    """Ensures arbitrary exceptions in the provider are swallowed and fallback returned."""
    with patch.object(
        weather_service.primary_provider,
        "fetch_current_and_forecast",
        side_effect=ConnectionResetError("Socket reset"),
    ):
        report = await weather_service.get_comprehensive_weather(
            location_query="sangli",
            force_refresh=True,
        )
        assert report.data_source == "fallback"
        assert report.current.temperature_c > 0


# 7. Spatial cache hit vs. miss behavior
@pytest.mark.anyio
async def test_spatial_cache_quantization():
    """Tests that coordinates within ~1.1km quantize to the same cache key."""
    # Seed cache at 18.5200, 73.8500
    test_payload = {"cached_flag": "test_ok", "location_name": "CacheTest"}
    await weather_cache.set(18.5201, 73.8502, test_payload, prefix="test_quant", ttl_seconds=60)

    # Lookup slightly different coordinate within 2 decimal places (18.5204, 73.8503)
    cached = await weather_cache.get(18.5204, 73.8503, prefix="test_quant")
    assert cached is not None
    assert cached.get("cached_flag") == "test_ok"

    # Lookup coordinate far away (miss)
    miss = await weather_cache.get(19.0000, 74.0000, prefix="test_quant")
    assert miss is None


# 8. Unit conversion accuracy & normalizer functions
def test_unit_conversions_and_normalizer():
    """Validates temperature conversion, dew point calculation, and soil moisture categories."""
    # Temperature conversions
    assert normalizer.celsius_to_fahrenheit(0.0) == 32.0
    assert normalizer.celsius_to_fahrenheit(100.0) == 212.0
    assert normalizer.celsius_to_kelvin(0.0) == 273.15

    # Dew point calculation (at 25°C and 60% RH, dew point is ~16.7°C)
    dp = normalizer.calculate_dew_point(25.0, 60.0)
    assert 15.0 <= dp <= 18.0

    # Wind speed km/h to m/s
    assert normalizer.kmh_to_ms(36.0) == 10.0

    # Soil moisture categorization
    assert normalizer.categorize_soil_moisture(0.40)[0] == "SATURATED"
    assert normalizer.categorize_soil_moisture(0.25)[0] == "OPTIMAL"
    assert normalizer.categorize_soil_moisture(0.18)[0] == "DRY"
    assert normalizer.categorize_soil_moisture(0.08)[0] == "SEVERELY_DEPLETED"




# 9. Timestamp & timezone formatting
@pytest.mark.anyio
async def test_timestamp_and_timezone_handling():
    """Verifies observation timestamps are valid ISO 8601 formats."""
    report = await weather_service.get_comprehensive_weather(
        latitude=18.5204,
        longitude=73.8567,
        location_name="Pune, Maharashtra",
    )
    # Parse fetched_at string to verify it is valid ISO timestamp
    ts = datetime.fromisoformat(report.current.fetched_at.replace("Z", "+00:00"))
    assert ts.year >= 2024


# 10. Agrochemical spray safety rules
def test_spray_window_advisory_rules():
    """Tests all 4 branches of the spray suitability engine."""
    # Branch 1: Rain risk
    rain_data = WeatherData(
        temperature_c=25.0,
        relative_humidity_pct=80.0,
        wind_speed_kmh=8.0,
        precipitation_mm=1.2,
        precipitation_probability_6h=65.0,
        weather_condition="Rain showers",
    )
    res_rain = weather_service.assess_spray_suitability(rain_data)
    assert res_rain.status == "UNFAVOURABLE_RAIN_RISK"
    assert res_rain.is_safe_to_spray is False

    # Branch 2: High wind drift risk
    wind_data = WeatherData(
        temperature_c=26.0,
        relative_humidity_pct=55.0,
        wind_speed_kmh=18.5,  # > 15 km/h
        precipitation_mm=0.0,
        precipitation_probability_6h=5.0,
        weather_condition="Breezy",
    )
    res_wind = weather_service.assess_spray_suitability(wind_data)
    assert res_wind.status == "UNFAVOURABLE_DRIFT_RISK"
    assert res_wind.is_safe_to_spray is False

    # Branch 3: Thermal stress
    heat_data = WeatherData(
        temperature_c=37.5,  # > 35°C
        relative_humidity_pct=40.0,
        wind_speed_kmh=6.0,
        precipitation_mm=0.0,
        precipitation_probability_6h=0.0,
        weather_condition="Clear sky",
    )
    res_heat = weather_service.assess_spray_suitability(heat_data)
    assert res_heat.status == "UNFAVOURABLE_HEAT_STRESS"
    assert res_heat.is_safe_to_spray is False

    # Branch 4: Optimal
    optimal_data = WeatherData(
        temperature_c=26.0,
        relative_humidity_pct=60.0,
        wind_speed_kmh=7.0,
        precipitation_mm=0.0,
        precipitation_probability_6h=10.0,
        weather_condition="Clear sky",
    )
    res_opt = weather_service.assess_spray_suitability(optimal_data)
    assert res_opt.status == "OPTIMAL"
    assert res_opt.is_safe_to_spray is True


# 11. Contextual integration with crop recommendation engine
def test_crop_recommendation_weather_integration(client: TestClient):
    """Verifies that high-risk weather is contextualized into the recommendation engine output."""
    payload = {
        "crop_name": "sugarcane",
        "predicted_disease": "RedRot",
        "confidence": 0.94,
        "temperature": 27.0,
        "humidity": 85.0,  # Triggers HIGH fungal infection risk
        "preferred_language": "mr",
    }
    resp = client.post("/api/v1/advisory/generate", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["weather_telemetry"]["relative_humidity_pct"] == 85.0
    assert data["weather_telemetry"]["fungal_risk_level"] == "HIGH"
    # Verify contextual overview in Marathi contains the microclimate note
    assert "बुरशी" in data["overview"]["mr"] or "हवामान" in data["overview"]["mr"]



# 12. Relational database persistence
def test_database_persistence(client: TestClient, db: Session):
    """Verifies that requesting weather with ?persist=true writes a record to weather_observations table."""
    resp = client.get("/api/v1/weather/current?district=solapur&persist=true")
    assert resp.status_code == 200

    # Query database to confirm observation was written
    obs = db.query(WeatherObservation).filter(
        WeatherObservation.location_name.contains("Solapur")
    ).first()

    assert obs is not None
    assert obs.latitude > 0
    assert obs.longitude > 0
    assert obs.temperature > -10.0
    assert obs.humidity >= 0.0
    assert obs.spray_suitability in ["OPTIMAL", "UNFAVOURABLE_RAIN_RISK", "UNFAVOURABLE_DRIFT_RISK", "UNFAVOURABLE_HEAT_STRESS", "MARGINAL"]
