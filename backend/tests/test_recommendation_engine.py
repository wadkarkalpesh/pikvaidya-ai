"""
Unit tests for ContextAwareRecommendationEngine
===============================================
"""

import pytest
from app.services.recommendation_engine import recommendation_engine
from app.schemas.advisory import AdvisoryGenerateRequest, ContextualAdvisoryResponse


@pytest.mark.anyio
async def test_recommendation_high_confidence_redrot(db):
    req = AdvisoryGenerateRequest(
        crop_name="sugarcane",
        predicted_disease="RedRot",
        confidence=0.92,
        severity="MODERATE",
        affected_area_percentage=22.5,
        temperature=28.0,
        humidity=65.0,
        preferred_language="mr"
    )
    res = await recommendation_engine.generate_advisory(req, db=db)
    assert isinstance(res, ContextualAdvisoryResponse)
    assert res.confidence_tier == "HIGH"
    assert res.is_chemical_permitted is True
    assert res.chemical_suppression_reason is None
    assert len(res.chemical_prescriptions) > 0
    # Verify CIBRC prescription details
    first_chem = res.chemical_prescriptions[0]
    assert first_chem.phi_days > 0
    assert "CIBRC" in first_chem.cibrc_status
    # Verify multilingual outputs
    assert "mr" in res.disease_name
    assert "en" in res.disease_name
    assert "hi" in res.disease_name
    assert len(res.cultural_practices["mr"]) > 0
    assert "कीटकनाशक कायदा" in res.statutory_disclaimer["mr"]


@pytest.mark.anyio
async def test_recommendation_moderate_confidence_suppression(db):
    # Confidence 0.62 is below 0.75 threshold -> must suppress chemical prescriptions
    req = AdvisoryGenerateRequest(
        crop_name="sugarcane",
        predicted_disease="Rust",
        confidence=0.62,
        severity="MILD",
        affected_area_percentage=8.0,
        preferred_language="mr"
    )
    res = await recommendation_engine.generate_advisory(req, db=db)
    assert res.confidence_tier == "MODERATE"
    assert res.is_chemical_permitted is False
    assert res.chemical_suppression_reason is not None
    assert "withheld" in res.chemical_suppression_reason["en"].lower() or "रोखण्यात" in res.chemical_suppression_reason["mr"]
    assert len(res.chemical_prescriptions) == 0


@pytest.mark.anyio
async def test_recommendation_low_confidence_inconclusive(db):
    # Confidence 0.35 is inconclusive
    req = AdvisoryGenerateRequest(
        crop_name="sugarcane",
        predicted_disease="Mosaic",
        confidence=0.35,
        severity="UNAVAILABLE",
        preferred_language="en"
    )
    res = await recommendation_engine.generate_advisory(req, db=db)
    assert res.confidence_tier == "LOW_INCONCLUSIVE"
    assert res.is_chemical_permitted is False
    assert "inconclusive" in res.chemical_suppression_reason["en"].lower()
    assert len(res.chemical_prescriptions) == 0


@pytest.mark.anyio
async def test_recommendation_healthy_foliage(db):
    # Healthy foliage needs zero chemicals
    req = AdvisoryGenerateRequest(
        crop_name="sugarcane",
        predicted_disease="Healthy",
        confidence=0.96,
        severity="HEALTHY",
        preferred_language="mr"
    )
    res = await recommendation_engine.generate_advisory(req, db=db)
    assert res.confidence_tier == "HIGH"
    assert res.is_chemical_permitted is False
    assert "निरोगी" in res.chemical_suppression_reason["mr"]
    assert len(res.chemical_prescriptions) == 0


@pytest.mark.anyio
async def test_recommendation_weather_context_integration(db):
    # High humidity and rain triggers
    req = AdvisoryGenerateRequest(
        crop_name="sugarcane",
        predicted_disease="Rust",
        confidence=0.88,
        temperature=26.0,
        humidity=88.0,
        preferred_language="en"
    )
    res = await recommendation_engine.generate_advisory(req, db=db)
    assert res.weather_telemetry is not None
    assert res.weather_telemetry.temperature_c == 26.0
    assert res.weather_telemetry.relative_humidity_pct == 88.0
    assert len(res.spray_window_directive["en"]) > 0
