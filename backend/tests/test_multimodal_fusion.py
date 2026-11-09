"""
Unit and Integration Tests for Multimodal Crop-Health Prediction Engine
======================================================================
Tests physiological stress quantification, epidemiological pathogen models,
Calibrated Bayesian evidence fusion, non-override constraints, environmental
anomaly detection, and multimodal REST API endpoints.
"""

import io
from typing import Optional
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.schemas.multimodal import (
    AgriculturalContextInput,
    HistoricalWeatherProfile,
    HistoricalWindowMetrics,
    ImageDiagnosisSummary,
    CropGrowthStage,
    SoilType,
    IrrigationMethod,
)
from app.services.weather.crop_health_risk import (
    WeatherCropHealthRiskEngine,
    weather_crop_health_risk_engine,
)
from app.services.multimodal_fusion import (
    MultimodalFusionEngine,
    multimodal_fusion_engine,
)


def _build_test_window_metrics(
    window_hours: int = 168,
    temp_avg: float = 27.0,
    temp_max: Optional[float] = None,
    temp_min: Optional[float] = None,
    humidity_avg: float = 75.0,
    high_humidity_hours: int = 40,
    rainfall_total: float = 35.0,
    consecutive_rainy_days: int = 2,
    wind_avg: float = 12.0,
    soil_moisture: float = 28.0,
    soil_trend: str = "STABLE",
) -> HistoricalWindowMetrics:
    t_max = temp_max if temp_max is not None else temp_avg + 5.0
    t_min = temp_min if temp_min is not None else max(5.0, temp_avg - 5.0)
    return HistoricalWindowMetrics(
        window_hours=window_hours,
        temp_avg_c=temp_avg,
        temp_max_c=t_max,
        temp_min_c=t_min,
        temp_diurnal_range_c=t_max - t_min,
        humidity_avg_pct=humidity_avg,
        humidity_min_pct=max(20.0, humidity_avg - 20.0),
        humidity_max_pct=min(100.0, humidity_avg + 15.0),
        high_humidity_hours=high_humidity_hours,
        saturation_humidity_hours=high_humidity_hours // 2,
        rainfall_total_mm=rainfall_total,
        rainy_days_count=consecutive_rainy_days + 1,
        consecutive_rainy_days=consecutive_rainy_days,
        rainfall_frequency=0.3,
        wind_speed_avg_kmh=wind_avg,
        wind_gust_max_kmh=wind_avg + 10.0,
        cloud_cover_avg_pct=50.0,
        soil_moisture_avg_pct=soil_moisture,
        soil_moisture_trend=soil_trend,
        soil_temp_avg_c=temp_avg - 1.0,
        growing_degree_days=120.0,
    )


def _build_test_profile(
    temp_avg: float = 27.0,
    temp_max: Optional[float] = None,
    humidity_avg: float = 75.0,
    high_humidity_hours: int = 40,
    rainfall_total: float = 35.0,
    wind_avg: float = 12.0,
    soil_moisture: float = 28.0,
    soil_trend: str = "STABLE",
) -> HistoricalWeatherProfile:
    t_max = temp_max if temp_max is not None else temp_avg + 5.0
    w24 = _build_test_window_metrics(
        window_hours=24,
        temp_avg=temp_avg,
        temp_max=t_max,
        humidity_avg=humidity_avg,
        high_humidity_hours=min(24, high_humidity_hours // 7),
        rainfall_total=rainfall_total / 7.0,
        wind_avg=wind_avg,
        soil_moisture=soil_moisture,
        soil_trend=soil_trend,
    )
    w3d = _build_test_window_metrics(
        window_hours=72,
        temp_avg=temp_avg,
        temp_max=t_max,
        humidity_avg=humidity_avg,
        high_humidity_hours=high_humidity_hours // 2,
        rainfall_total=rainfall_total * 0.4,
        wind_avg=wind_avg,
        soil_moisture=soil_moisture,
        soil_trend=soil_trend,
    )
    w7d = _build_test_window_metrics(
        window_hours=168,
        temp_avg=temp_avg,
        temp_max=t_max,
        humidity_avg=humidity_avg,
        high_humidity_hours=high_humidity_hours,
        rainfall_total=rainfall_total,
        wind_avg=wind_avg,
        soil_moisture=soil_moisture,
        soil_trend=soil_trend,
    )
    w14d = _build_test_window_metrics(
        window_hours=336,
        temp_avg=temp_avg,
        temp_max=t_max,
        humidity_avg=humidity_avg,
        high_humidity_hours=high_humidity_hours * 2,
        rainfall_total=rainfall_total * 1.5,
        wind_avg=wind_avg,
        soil_moisture=soil_moisture,
        soil_trend=soil_trend,
    )
    return HistoricalWeatherProfile(
        latitude=18.5204,
        longitude=73.8567,
        location_name="Pune",
        resolved_at="2026-11-09T00:00:00",
        data_source="open-meteo-test",
        data_completeness_pct=100.0,
        window_24h=w24,
        window_3d=w3d,
        window_7d=w7d,
        window_14d=w14d,
    )


# ==============================================================================
# 1. Physiological Stress Index Tests
# ==============================================================================

def test_physiological_stress_indices():
    """Validates heat stress, drought/deficit, flood risk, and spray drift."""
    engine = WeatherCropHealthRiskEngine()

    # Extreme Heat Scenario: 41°C avg, 45°C max, dry soil (10%)
    hot_profile = _build_test_profile(
        temp_avg=41.0, temp_max=45.0, humidity_avg=25.0, rainfall_total=0.0, soil_moisture=10.0
    )
    risk_summary = engine.evaluate_weather_risk("tomato", hot_profile)
    stresses = risk_summary.environmental_stresses

    assert stresses.heat_stress_index > 0.50
    assert stresses.water_stress_index > 0.40
    assert stresses.excess_water_flood_index < 0.20

    # High Waterlogging / Flood Scenario
    flood_profile = _build_test_profile(
        temp_avg=24.0, rainfall_total=180.0, soil_moisture=45.0, soil_trend="SATURATED"
    )
    flood_risk = engine.evaluate_weather_risk("sugarcane", flood_profile)
    assert flood_risk.environmental_stresses.excess_water_flood_index > 0.50

    # High Wind Hazard
    windy_profile = _build_test_profile(wind_avg=28.0)
    wind_risk = engine.evaluate_weather_risk("onion", windy_profile)
    assert wind_risk.environmental_stresses.wind_damage_risk > 0.60


# ==============================================================================
# 2. Disease Conduciveness Model Tests
# ==============================================================================

def test_tomato_early_blight_conduciveness():
    """Tests Tom-Cast DSV based conduciveness for Alternaria solani."""
    engine = WeatherCropHealthRiskEngine()
    ag_ctx = AgriculturalContextInput(crop_name="tomato")

    # High conduciveness: warm (25°C), high humidity hours
    humid_profile = _build_test_profile(
        temp_avg=25.0, humidity_avg=88.0, high_humidity_hours=65, rainfall_total=45.0
    )
    risk_summary = engine.evaluate_weather_risk("tomato", humid_profile, ag_ctx)
    conduciveness = {d.disease_id: d for d in risk_summary.disease_conduciveness_profile}
    
    assert "Early_blight" in conduciveness
    assert conduciveness["Early_blight"].conduciveness_score >= 0.50
    assert conduciveness["Early_blight"].risk_tier in ["MODERATE", "HIGH", "CRITICAL"]


def test_sugarcane_red_rot_conduciveness():
    """Tests ICAR-SBI epidemiological conditions for Colletotrichum falcatum."""
    engine = WeatherCropHealthRiskEngine()
    ag_ctx = AgriculturalContextInput(crop_name="sugarcane", soil_type="clay_loam")

    # High risk: warm (29°C), saturated soil, waterlogging
    waterlogged_profile = _build_test_profile(
        temp_avg=29.0,
        humidity_avg=86.0,
        high_humidity_hours=60,
        rainfall_total=130.0,
        soil_moisture=42.0,
        soil_trend="SATURATED",
    )
    sugarcane_risk = engine.evaluate_weather_risk("sugarcane", waterlogged_profile, ag_ctx)
    conduciveness = {d.disease_id: d for d in sugarcane_risk.disease_conduciveness_profile}

    assert "RedRot" in conduciveness
    assert conduciveness["RedRot"].conduciveness_score >= 0.50


# ==============================================================================
# 3. Multimodal Fusion Engine Tests (Bayesian & Non-Override)
# ==============================================================================

def test_strict_non_override_constraint():
    """STRICT NON-OVERRIDE: Visual diagnosis with conf >= 0.75 CANNOT be flipped by weather."""
    engine = MultimodalFusionEngine()
    arid_profile = _build_test_profile(
        temp_avg=42.0, temp_max=46.0, humidity_avg=18.0, high_humidity_hours=0, rainfall_total=0.0
    )
    weather_risk = weather_crop_health_risk_engine.evaluate_weather_risk("tomato", arid_profile)
    ag_ctx = AgriculturalContextInput(crop_name="tomato")

    # High visual confidence (0.94) for Early_blight
    img_summary = ImageDiagnosisSummary(
        crop="tomato",
        predicted_class="Early_blight",
        confidence=0.94,
        class_scores={"Early_blight": 0.94, "Late_blight": 0.03, "Healthy": 0.03},
        model_version="v2.1-convnext",
        explanation_status="GRADCAM_ACTIVE",
        foliar_severity="MODERATE",
        affected_area_percentage=14.5,
    )

    fused = engine.fuse(
        image_prediction=img_summary,
        weather_risk=weather_risk,
        context=ag_ctx,
        strategy="CALIBRATED_BAYESIAN",
    )

    # Class must strictly remain Early_blight
    assert fused.multimodal_assessment.primary_diagnosis == "Early_blight"
    # Environmental anomaly warning generated due to arid conditions
    assert fused.multimodal_assessment.anomaly_warning is not None
    assert "Environmental Incongruence" in fused.multimodal_assessment.anomaly_warning["en"]


def test_bayesian_reinforcement_for_moderate_confidence():
    """Moderate visual confidence (0.62) with high weather conduciveness receives calibrated boost."""
    engine = MultimodalFusionEngine()
    humid_profile = _build_test_profile(
        temp_avg=24.0, humidity_avg=88.0, high_humidity_hours=55, rainfall_total=40.0
    )
    weather_risk = weather_crop_health_risk_engine.evaluate_weather_risk("tomato", humid_profile)
    ag_ctx = AgriculturalContextInput(crop_name="tomato")

    img_summary = ImageDiagnosisSummary(
        crop="tomato",
        predicted_class="Early_blight",
        confidence=0.62,
        class_scores={"Early_blight": 0.62, "Healthy": 0.38},
        model_version="v2.1-convnext",
        explanation_status="GRADCAM_ACTIVE",
        foliar_severity="MILD",
        affected_area_percentage=5.0,
    )

    fused = engine.fuse(
        image_prediction=img_summary,
        weather_risk=weather_risk,
        context=ag_ctx,
        strategy="CALIBRATED_BAYESIAN",
    )

    assert fused.multimodal_assessment.primary_diagnosis == "Early_blight"
    assert fused.multimodal_assessment.fused_confidence >= 0.60
    assert fused.multimodal_assessment.disease_progression_velocity in ["MODERATE", "RAPID"]


def test_composite_crop_health_score():
    """Verifies that composite crop health score responds appropriately to disease and environmental stress."""
    engine = MultimodalFusionEngine()
    weather_risk = weather_crop_health_risk_engine.evaluate_weather_risk(
        crop_name="sugarcane",
        profile=_build_test_profile(temp_avg=28.0, humidity_avg=70.0),
    )

    # 1. Healthy crop under low stress should have high score
    healthy_img = ImageDiagnosisSummary(
        crop="sugarcane",
        predicted_class="Healthy",
        confidence=0.96,
        class_scores={"Healthy": 0.96, "RedRot": 0.04},
        model_version="v2.1-convnext",
        explanation_status="GRADCAM_ACTIVE",
        foliar_severity="HEALTHY",
        affected_area_percentage=0.0,
    )
    healthy_fused = engine.fuse(image_prediction=healthy_img, weather_risk=weather_risk)
    assert healthy_fused.multimodal_assessment.crop_health_index >= 80.0

    # 2. Diseased crop with severe lesions should have lower health score
    diseased_img = ImageDiagnosisSummary(
        crop="sugarcane",
        predicted_class="RedRot",
        confidence=0.92,
        class_scores={"Healthy": 0.08, "RedRot": 0.92},
        model_version="v2.1-convnext",
        explanation_status="GRADCAM_ACTIVE",
        foliar_severity="SEVERE",
        affected_area_percentage=35.0,
    )
    diseased_fused = engine.fuse(image_prediction=diseased_img, weather_risk=weather_risk)
    assert diseased_fused.multimodal_assessment.crop_health_index < healthy_fused.multimodal_assessment.crop_health_index


# ==============================================================================
# 4. Multimodal API Route Tests
# ==============================================================================

def test_api_multimodal_crops(client: TestClient):
    """Tests GET /api/v1/multimodal/crops endpoint."""
    res = client.get("/api/v1/multimodal/crops")
    assert res.status_code == 200
    data = res.json()
    assert "supported_crops" in data
    assert "sugarcane" in data["supported_crops"]
    assert "tomato" in data["supported_crops"]
    assert "onion" in data["supported_crops"]
    assert "districts" in data
    assert "pune" in data["districts"]


def test_api_multimodal_weather_risk(client: TestClient):
    """Tests POST /api/v1/multimodal/weather-risk endpoint."""
    payload = {
        "crop_name": "tomato",
        "district": "pune",
        "growth_stage": "flowering_fruiting",
        "soil_type": "loamy",
    }
    res = client.post("/api/v1/multimodal/weather-risk", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["crop"] == "tomato"
    assert "environmental_stresses" in data
    assert "heat_stress_index" in data["environmental_stresses"]
    assert "disease_conduciveness_profile" in data
    assert len(data["disease_conduciveness_profile"]) > 0


def test_api_multimodal_predict(client: TestClient, sample_jpeg_bytes: bytes):
    """Tests POST /api/v1/multimodal/predict full multimodal forward pass."""
    files = {"file": ("tomato_leaf.jpg", sample_jpeg_bytes, "image/jpeg")}
    data = {
        "crop": "tomato",
        "district": "nashik",
        "generate_gradcam": "true",
    }
    res = client.post("/api/v1/multimodal/predict", files=files, data=data)
    assert res.status_code == 200
    resp_json = res.json()
    assert resp_json["image_prediction"]["crop"] == "tomato"
    assert "multimodal_assessment" in resp_json
    assert "weather_risk" in resp_json
    assert "explainability" in resp_json
    assert resp_json["multimodal_assessment"]["crop_health_index"] >= 0.0


def test_api_diagnose_predict_multimodal_enrichment(client: TestClient, sample_jpeg_bytes: bytes):
    """Tests that POST /api/v1/diagnose/predict attaches multimodal_assessment in details when district is passed."""
    files = {"file": ("sugarcane_leaf.jpg", sample_jpeg_bytes, "image/jpeg")}
    data = {
        "crop": "sugarcane",
        "district": "kolhapur",
        "generate_gradcam": "false",
    }
    res = client.post("/api/v1/diagnose/predict", files=files, data=data)
    assert res.status_code == 200
    resp_json = res.json()
    assert resp_json["crop"] == "sugarcane"
    assert "details" in resp_json
    assert "multimodal_assessment" in resp_json["details"]
    assert resp_json["details"]["multimodal_assessment"] is not None
    assert "multimodal_assessment" in resp_json["details"]["multimodal_assessment"]
    assert "crop_health_index" in resp_json["details"]["multimodal_assessment"]["multimodal_assessment"]


# ==============================================================================
# 5. Dedicated Onion Multimodal Pathology & Weather Risk Tests
# ==============================================================================

def test_onion_epidemiological_pathogen_models():
    """Verifies all 4 onion epidemiological pathogen models: Purple Blotch, Stemphylium, IYSV, Healthy."""
    engine = WeatherCropHealthRiskEngine()

    # 1. Warm & High Humidity (Alternaria porri / Purple Blotch conducive)
    humid_profile = _build_test_profile(
        temp_avg=26.0, humidity_avg=88.0, high_humidity_hours=42, rainfall_total=25.0
    )
    risk_humid = engine.evaluate_weather_risk("onion", humid_profile)
    conducive_humid = {d.disease_id: d for d in risk_humid.disease_conduciveness_profile}
    assert "Purple_blotch" in conducive_humid
    assert "Stemphylium_blight" in conducive_humid
    assert "Iris_yellow_virus" in conducive_humid
    assert "Healthy" in conducive_humid
    assert conducive_humid["Purple_blotch"].conduciveness_score >= 0.60

    # 2. Cool & Overcast (Stemphylium vesicarium conducive)
    cool_profile = _build_test_profile(
        temp_avg=21.0, humidity_avg=85.0, high_humidity_hours=38, rainfall_total=12.0
    )
    risk_cool = engine.evaluate_weather_risk("onion", cool_profile)
    conducive_cool = {d.disease_id: d for d in risk_cool.disease_conduciveness_profile}
    assert conducive_cool["Stemphylium_blight"].conduciveness_score >= 0.60

    # 3. Hot, Dry & Rainless (Thrips tabaci / Iris Yellow Spot Virus conducive)
    dry_profile = _build_test_profile(
        temp_avg=30.0, temp_max=36.0, humidity_avg=45.0, high_humidity_hours=4, rainfall_total=0.0
    )
    risk_dry = engine.evaluate_weather_risk("onion", dry_profile)
    conducive_dry = {d.disease_id: d for d in risk_dry.disease_conduciveness_profile}
    assert conducive_dry["Iris_yellow_virus"].conduciveness_score >= 0.60
    assert conducive_dry["Iris_yellow_virus"].pathogen_type == "viral_vector"


def test_api_multimodal_predict_onion(client: TestClient, sample_jpeg_bytes: bytes):
    """Tests POST /api/v1/multimodal/predict for Onion crop in Nashik district."""
    files = {"file": ("onion_leaf.jpg", sample_jpeg_bytes, "image/jpeg")}
    data = {
        "crop": "onion",
        "district": "nashik",
        "generate_gradcam": "true",
    }
    res = client.post("/api/v1/multimodal/predict", files=files, data=data)
    assert res.status_code == 200
    resp_json = res.json()
    assert resp_json["image_prediction"]["crop"] == "onion"
    assert resp_json["weather_risk"]["crop"] == "onion"
    assert "multimodal_assessment" in resp_json
    assert resp_json["multimodal_assessment"]["primary_diagnosis"] in [
        "Onion___healthy",
        "Onion___iris_yellow_virus",
        "Onion___purple_blotch",
        "Onion___stemphylium_blight",
    ]
    assert 0.0 <= resp_json["multimodal_assessment"]["crop_health_index"] <= 100.0
    assert "explainability" in resp_json
    assert "mr" in resp_json["explainability"]["multimodal_narrative"]
    assert "recommendations" in resp_json
    assert "spray_safety_verdict" in resp_json["recommendations"]

