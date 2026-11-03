import io
import pytest
from PIL import Image
import numpy as np
from fastapi.testclient import TestClient

from app.models.diagnosis import DiagnosisSeverity
from app.services.segmentation_service import segmentation_service
from app.core.rate_limit import SlidingWindowRateLimiter


def test_validate_foliar_quality_valid_foliage():
    # Create green foliar image (ForestGreen)
    img = Image.new("RGB", (100, 100), color=(34, 139, 34))
    is_valid, cov, msg = segmentation_service.validate_foliar_quality(img)
    assert is_valid is True
    assert cov > 0.5
    assert "Valid foliar vegetation" in msg


def test_validate_foliar_quality_non_leaf_rejection():
    # Pure white
    white_img = Image.new("RGB", (100, 100), color=(255, 255, 255))
    is_valid, cov, msg = segmentation_service.validate_foliar_quality(white_img)
    assert is_valid is False
    assert cov < 0.05
    assert "below the minimum required threshold" in msg

    # Pure blue (e.g. sky / vehicle)
    blue_img = Image.new("RGB", (100, 100), color=(0, 0, 255))
    is_valid, cov, msg = segmentation_service.validate_foliar_quality(blue_img)
    assert is_valid is False
    assert cov < 0.05


def test_estimate_foliar_severity_healthy():
    img = Image.new("RGB", (100, 100), color=(34, 139, 34))
    sev, area = segmentation_service.estimate_foliar_severity(img, "Healthy")
    assert sev == DiagnosisSeverity.HEALTHY
    assert area == 0.0


def test_estimate_foliar_severity_diseased():
    # Create an image with green background and reddish necrotic lesion
    arr = np.zeros((100, 100, 3), dtype=np.uint8)
    # 70% foliage (green)
    arr[:, :, 0] = 50
    arr[:, :, 1] = 160
    arr[:, :, 2] = 40
    # 30% necrotic lesion (reddish-brown)
    arr[0:30, 0:100, 0] = 180
    arr[0:30, 0:100, 1] = 40
    arr[0:30, 0:100, 2] = 30

    img = Image.fromarray(arr)
    sev, area = segmentation_service.estimate_foliar_severity(img, "RedRot")
    assert sev in [DiagnosisSeverity.MODERATE, DiagnosisSeverity.SEVERE]
    assert area is not None
    assert area > 10.0


def test_rate_limiter_throttling():
    limiter = SlidingWindowRateLimiter(max_requests=3, window_seconds=60)
    client_ip = "192.168.1.100"

    assert limiter.is_allowed(client_ip) is True
    assert limiter.is_allowed(client_ip) is True
    assert limiter.is_allowed(client_ip) is True
    # 4th request within window must be rejected
    assert limiter.is_allowed(client_ip) is False


def test_predict_endpoint_rejects_non_leaf_image(client: TestClient):
    # Uploading a pure white non-leaf image should trigger HTTP 400
    white_img = Image.new("RGB", (100, 100), color=(255, 255, 255))
    buf = io.BytesIO()
    white_img.save(buf, format="JPEG")
    white_bytes = buf.getvalue()

    files = {"file": ("white.jpg", white_bytes, "image/jpeg")}
    response = client.post("/api/v1/diagnose/predict", files=files, data={"crop": "sugarcane"})
    assert response.status_code == 400
    assert "below the minimum required threshold" in response.json()["detail"]


def test_predict_endpoint_returns_foliar_segmentation_details(
    client: TestClient, sample_jpeg_bytes: bytes
):
    files = {"file": ("leaf.jpg", sample_jpeg_bytes, "image/jpeg")}
    response = client.post(
        "/api/v1/diagnose/predict",
        files=files,
        data={"crop": "sugarcane", "generate_gradcam": "false"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert "foliar_segmentation" in payload["details"]
    foliar_data = payload["details"]["foliar_segmentation"]
    assert "foliar_coverage_ratio" in foliar_data
    assert "empirical_affected_area_percentage" in foliar_data
    assert "empirical_severity" in foliar_data

