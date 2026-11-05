"""
Integration tests for Advisory API Endpoints
============================================
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.anyio
async def test_generate_advisory_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "crop_name": "sugarcane",
            "predicted_disease": "RedRot",
            "confidence": 0.89,
            "severity": "MODERATE",
            "affected_area_percentage": 25.0,
            "temperature": 27.5,
            "humidity": 68.0,
            "crop_stage": "grand_growth",
            "preferred_language": "mr"
        }
        resp = await ac.post("/api/v1/advisory/generate", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["crop_name"] == "sugarcane"
        assert data["confidence_tier"] == "HIGH"
        assert data["is_chemical_permitted"] is True
        assert "weather_telemetry" in data
        assert "statutory_disclaimer" in data
        assert "cultural_practices" in data


@pytest.mark.anyio
async def test_generate_advisory_suppressed_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "crop_name": "sugarcane",
            "predicted_disease": "Rust",
            "confidence": 0.60,
            "severity": "MILD"
        }
        resp = await ac.post("/api/v1/advisory/generate", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["confidence_tier"] == "MODERATE"
        assert data["is_chemical_permitted"] is False
        assert data["chemical_suppression_reason"] is not None


@pytest.mark.anyio
async def test_weather_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/advisory/weather?lat=16.7050&lon=74.2433")
        assert resp.status_code == 200
        data = resp.json()
        assert "temperature_c" in data
        assert "relative_humidity_pct" in data
        assert "spray_suitability" in data
        assert "is_safe_to_spray" in data
        assert "fungal_risk_level" in data
