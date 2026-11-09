"""
Comprehensive Unit & Integration Tests for Offline Sync Ingestion & Telemetry
=============================================================================
Verifies:
  1. Multi-crop health prediction endpoint with offline queued sync payload:
     - Accepts 'image' alias alongside 'file'.
     - Accepts 'crop_name' alias alongside 'crop_type'.
     - Accepts 'captured_at' offline timestamp and returns it in response.
     - Confirms 'is_offline_synced' flag is True when captured_at is provided.
  2. Offline sync without captured_at (standard live upload):
     - Confirms 'is_offline_synced' is False.
  3. Validation constraints preserved for corrupted/empty payloads.
"""

import io
import pytest
from PIL import Image
from httpx import AsyncClient, ASGITransport
from app.main import app


def create_test_leaf_image(width=224, height=224, color=(40, 160, 40)):
    """Generates a valid green leaf image in memory."""
    buf = io.BytesIO()
    img = Image.new("RGB", (width, height), color)
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.mark.anyio
async def test_offline_sync_with_captured_at_timestamp():
    transport = ASGITransport(app=app)
    img_bytes = create_test_leaf_image()

    offline_timestamp = "2026-11-09T18:30:00.000Z"

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        files = {"image": ("field_offline_capture.jpg", img_bytes, "image/jpeg")}
        data = {
            "crop_name": "tomato",
            "district": "Pune",
            "captured_at": offline_timestamp
        }

        resp = await ac.post("/api/crop-health/predict", files=files, data=data)
        assert resp.status_code == 200
        result = resp.json()

        assert result["crop_type"] == "tomato"
        assert result["captured_at"] == offline_timestamp
        assert result["is_offline_synced"] is True
        assert "predicted_disease" in result
        assert "combined_assessment" in result
        assert "advisory_recommendations" in result


@pytest.mark.anyio
async def test_live_prediction_without_offline_timestamp():
    transport = ASGITransport(app=app)
    img_bytes = create_test_leaf_image()

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        files = {"file": ("live_scan.jpg", img_bytes, "image/jpeg")}
        data = {
            "crop_type": "sugarcane",
            "district": "Kolhapur"
        }

        resp = await ac.post("/api/crop-health/predict", files=files, data=data)
        assert resp.status_code == 200
        result = resp.json()

        assert result["crop_type"] == "sugarcane"
        assert result["captured_at"] is None
        assert result["is_offline_synced"] is False


@pytest.mark.anyio
async def test_offline_sync_auto_crop_detection():
    transport = ASGITransport(app=app)
    img_bytes = create_test_leaf_image()

    offline_timestamp = "2026-11-09T19:15:00.000Z"

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        files = {"image": ("unknown_crop_capture.jpg", img_bytes, "image/jpeg")}
        data = {
            "crop_name": "auto",
            "district": "Nashik",
            "captured_at": offline_timestamp
        }

        resp = await ac.post("/api/crop-health/predict", files=files, data=data)
        assert resp.status_code == 200
        result = resp.json()

        assert result["crop_type"] in ["sugarcane", "tomato", "onion"]
        assert result["captured_at"] == offline_timestamp
        assert result["is_offline_synced"] is True


@pytest.mark.anyio
async def test_offline_sync_empty_file_rejected():
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        files = {"image": ("corrupted.jpg", b"", "image/jpeg")}
        data = {"crop_name": "onion"}

        resp = await ac.post("/api/crop-health/predict", files=files, data=data)
        assert resp.status_code == 400
        assert "empty" in resp.json()["detail"].lower()
