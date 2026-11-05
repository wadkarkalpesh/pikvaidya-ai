"""
Unit tests for WeatherService & Spray Window Assessment
======================================================
"""

import pytest
from app.services.weather_service import weather_service, WeatherData, SprayWindowAssessment


@pytest.mark.anyio
async def test_get_current_weather_fallback_or_live():
    # Calling get_current_weather should return valid WeatherData without throwing exceptions
    weather = await weather_service.get_current_weather(latitude=16.7050, longitude=74.2433)
    assert isinstance(weather, WeatherData)
    assert -10.0 <= weather.temperature_c <= 60.0
    assert 0.0 <= weather.relative_humidity_pct <= 100.0
    assert weather.wind_speed_kmh >= 0.0
    assert weather.precipitation_mm >= 0.0
    assert 0.0 <= weather.precipitation_probability_6h <= 100.0
    assert len(weather.weather_condition) > 0


def test_assess_spray_suitability_optimal():
    optimal_weather = WeatherData(
        temperature_c=25.0,
        relative_humidity_pct=60.0,
        wind_speed_kmh=8.0,
        precipitation_mm=0.0,
        precipitation_probability_6h=10.0,
        weather_condition="Clear sky"
    )
    assessment = weather_service.assess_spray_suitability(optimal_weather)
    assert assessment.status == "OPTIMAL"
    assert assessment.is_safe_to_spray is True
    assert "OPTIMAL" in assessment.status
    assert len(assessment.summary_en) > 0
    assert len(assessment.summary_mr) > 0
    assert len(assessment.summary_hi) > 0


def test_assess_spray_suitability_rain_risk():
    rain_weather = WeatherData(
        temperature_c=26.0,
        relative_humidity_pct=85.0,
        wind_speed_kmh=10.0,
        precipitation_mm=2.5,
        precipitation_probability_6h=75.0,
        weather_condition="Moderate rain"
    )
    assessment = weather_service.assess_spray_suitability(rain_weather)
    assert assessment.status == "UNFAVOURABLE_RAIN_RISK"
    assert assessment.is_safe_to_spray is False
    assert "POSTPONE" in assessment.advisory_recommendation_en
    assert "पुढे ढकला" in assessment.advisory_recommendation_mr
    assert assessment.fungal_risk_level == "HIGH"


def test_assess_spray_suitability_high_wind():
    windy_weather = WeatherData(
        temperature_c=27.0,
        relative_humidity_pct=50.0,
        wind_speed_kmh=22.0,  # Above 15 km/h threshold
        precipitation_mm=0.0,
        precipitation_probability_6h=5.0,
        weather_condition="Windy"
    )
    assessment = weather_service.assess_spray_suitability(windy_weather)
    assert assessment.status == "UNFAVOURABLE_DRIFT_RISK"
    assert assessment.is_safe_to_spray is False
    assert "DRIFT" in assessment.advisory_recommendation_en


def test_assess_spray_suitability_heat_stress():
    hot_weather = WeatherData(
        temperature_c=38.5,  # Above 35°C threshold
        relative_humidity_pct=40.0,
        wind_speed_kmh=7.0,
        precipitation_mm=0.0,
        precipitation_probability_6h=0.0,
        weather_condition="Hot"
    )
    assessment = weather_service.assess_spray_suitability(hot_weather)
    assert assessment.status == "UNFAVOURABLE_HEAT_STRESS"
    assert assessment.is_safe_to_spray is False
    assert "MID-DAY" in assessment.advisory_recommendation_en
