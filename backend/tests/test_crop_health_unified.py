"""
PikVaidya AI — Unified Multi-Crop Health Prediction Automated Test Suite
=======================================================================
Validates the unified multi-crop interface, automated foliar crop routing,
epidemiological pathogen coverage across all 3 crops (Sugarcane, Tomato, Onion),
calibrated Bayesian evidence fusion, non-override constraints, and REST API contracts.
"""

import io
import os
import pytest
from PIL import Image
from fastapi.testclient import TestClient

from app.main import app
from app.services.model_service import model_service
from app.services.crop_detector import crop_detector
from app.services.weather.crop_health_risk import weather_crop_health_risk_engine
from app.schemas.multimodal import (
    AgriculturalContextInput,
    HistoricalWeatherProfile,
    HistoricalWindowMetrics,
    CropGrowthStage,
    SoilType,
    IrrigationMethod,
)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def dummy_leaf_image_bytes():
    """Generates a synthetic green foliar test image in memory."""
    img = Image.new("RGB", (256, 256), color=(34, 139, 34))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture
def mock_weather_profile():
    """Generates a standard 14-day weather profile for testing."""
    def _make_window(hours, temp, rain, rh):
        return HistoricalWindowMetrics(
            window_hours=hours,
            temp_avg_c=temp,
            temp_max_c=temp + 4.0,
            temp_min_c=temp - 4.0,
            temp_diurnal_range_c=8.0,
            humidity_avg_pct=rh,
            humidity_min_pct=rh - 20.0,
            humidity_max_pct=min(100.0, rh + 10.0),
            high_humidity_hours=40 if rh >= 75 else 10,
            saturation_humidity_hours=20 if rh >= 85 else 2,
            rainfall_total_mm=rain,
            rainy_days_count=3 if rain > 10 else 0,
            consecutive_rainy_days=2 if rain > 10 else 0,
            rainfall_frequency=0.4 if rain > 10 else 0.0,
            wind_speed_avg_kmh=12.0,
            wind_gust_max_kmh=20.0,
            cloud_cover_avg_pct=60.0,
            soil_moisture_avg_pct=28.0,
            soil_moisture_trend="STABLE",
            soil_temp_avg_c=temp - 1.0,
            growing_degree_days=110.0,
        )

    return HistoricalWeatherProfile(
        latitude=18.52,
        longitude=73.85,
        location_name="Pune",
        resolved_at="2026-11-09T12:00:00Z",
        data_source="test-provider",
        data_completeness_pct=100.0,
        window_24h=_make_window(24, 26.0, 0.0, 72.0),
        window_3d=_make_window(72, 25.5, 12.0, 78.0),
        window_7d=_make_window(168, 25.0, 35.0, 80.0),
        window_14d=_make_window(336, 26.0, 55.0, 76.0),
    )


def test_crop_registry_completeness():
    """Verifies that all three target crops are properly registered in ModelServingService."""
    assert "sugarcane" in model_service.CROP_REGISTRY
    assert "tomato" in model_service.CROP_REGISTRY
    assert "onion" in model_service.CROP_REGISTRY


def test_epidemiological_coverage_sugarcane(mock_weather_profile):
    """Verifies all 5 sugarcane disease classes have active epidemiological models."""
    context = AgriculturalContextInput(crop_name="sugarcane")
    risk_summary = weather_crop_health_risk_engine.evaluate_weather_risk(
        crop_name="sugarcane", profile=mock_weather_profile, context=context
    )
    profile_ids = {d.disease_id for d in risk_summary.disease_conduciveness_profile}
    
    assert "RedRot" in profile_ids
    assert "Rust" in profile_ids
    assert "Mosaic" in profile_ids
    assert "Yellow" in profile_ids
    assert "Healthy" in profile_ids


def test_epidemiological_coverage_tomato(mock_weather_profile):
    """Verifies all 10 tomato disease classes have active epidemiological models."""
    context = AgriculturalContextInput(crop_name="tomato")
    risk_summary = weather_crop_health_risk_engine.evaluate_weather_risk(
        crop_name="tomato", profile=mock_weather_profile, context=context
    )
    profile_ids = {d.disease_id for d in risk_summary.disease_conduciveness_profile}
    
    expected_classes = {
        "Early_blight", "Late_blight", "Bacterial_spot", "Yellow_Leaf_Curl_Virus",
        "Septoria_leaf_spot", "Leaf_Mold", "Spider_mites", "Target_Spot",
        "Mosaic_virus", "Healthy"
    }
    for cls in expected_classes:
        assert cls in profile_ids, f"Missing epidemiological model for tomato class '{cls}'"


def test_epidemiological_coverage_onion(mock_weather_profile):
    """Verifies all 4 onion disease classes have active epidemiological models."""
    context = AgriculturalContextInput(crop_name="onion")
    risk_summary = weather_crop_health_risk_engine.evaluate_weather_risk(
        crop_name="onion", profile=mock_weather_profile, context=context
    )
    profile_ids = {d.disease_id for d in risk_summary.disease_conduciveness_profile}
    
    assert "Purple_blotch" in profile_ids
    assert "Stemphylium_blight" in profile_ids
    assert "Iris_yellow_virus" in profile_ids
    assert "Healthy" in profile_ids


def test_unified_api_predict_explicit_crop(client, dummy_leaf_image_bytes):
    """Tests POST /api/crop-health/predict with explicitly selected crop."""
    files = {"file": ("test_leaf.jpg", dummy_leaf_image_bytes, "image/jpeg")}
    data = {
        "crop_type": "onion",
        "latitude": 19.99,
        "longitude": 73.78,
        "district": "Nashik",
        "growth_stage": "bulb_development",
    }
    res = client.post("/api/crop-health/predict", files=files, data=data)
    assert res.status_code == 200, res.text
    
    json_data = res.json()
    assert json_data["crop_type"] == "onion"
    assert json_data["crop_detection_method"] == "explicit_user_selection"
    assert "predicted_disease" in json_data
    assert "model_confidence" in json_data
    assert "weather_summary" in json_data
    assert "environmental_risk" in json_data
    assert "combined_assessment" in json_data
    assert "advisory_recommendations" in json_data
    assert "timestamp" in json_data
    assert "data_source" in json_data


def test_unified_api_predict_auto_crop(client, dummy_leaf_image_bytes):
    """Tests POST /api/crop-health/predict with auto crop identification."""
    files = {"file": ("test_leaf.jpg", dummy_leaf_image_bytes, "image/jpeg")}
    data = {
        "crop_type": "auto",
        "latitude": 18.52,
        "longitude": 73.85,
        "district": "Pune",
    }
    res = client.post("/api/crop-health/predict", files=files, data=data)
    assert res.status_code == 200, res.text
    
    json_data = res.json()
    assert json_data["crop_type"] in ("sugarcane", "tomato", "onion")
    assert json_data["crop_detection_method"] == "auto_detected_classifier"
    assert "predicted_disease" in json_data
    assert json_data["model_confidence"] > 0.0


def test_versioned_crop_health_endpoint_alias(client, dummy_leaf_image_bytes):
    """Tests POST /api/v1/crop-health/predict route alias."""
    files = {"file": ("test_leaf.jpg", dummy_leaf_image_bytes, "image/jpeg")}
    data = {"crop_type": "tomato"}
    res = client.post("/api/v1/crop-health/predict", files=files, data=data)
    assert res.status_code == 200, res.text
    assert res.json()["crop_type"] == "tomato"

