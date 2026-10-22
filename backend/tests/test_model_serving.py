import io
import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.core.config import settings
from app.services.model_service import model_service


def test_predict_valid_image(client: TestClient, sample_jpeg_bytes: bytes):
    """Verifies that a valid crop leaf image returns proper predictions,

    all class probabilities, model version, and explanation status.
    """
    files = {"file": ("sugarcane_leaf.jpg", sample_jpeg_bytes, "image/jpeg")}
    data = {"crop": "sugarcane", "generate_gradcam": "false"}

    response = client.post("/api/v1/diagnose/predict", files=files, data=data)
    assert response.status_code == 200
    payload = response.json()

    assert payload["crop"] == "sugarcane"
    assert payload["predicted_class"] in ["Healthy", "Mosaic", "RedRot", "Rust", "Yellow"]
    assert 0.0 <= payload["confidence"] <= 1.0

    class_scores = payload["class_scores"]
    assert len(class_scores) == 5
    for cls_name in ["Healthy", "Mosaic", "RedRot", "Rust", "Yellow"]:
        assert cls_name in class_scores
        assert 0.0 <= class_scores[cls_name] <= 1.0

    # Probabilities should sum to approximately 1.0
    total_prob = sum(class_scores.values())
    assert 0.99 <= total_prob <= 1.01

    assert payload["model_version"] == "EfficientNet-B0-v1.0"
    assert payload["explanation_status"] == "available"
    assert payload["heatmap_path"] is None


def test_predict_with_gradcam_generation(client: TestClient, sample_jpeg_bytes: bytes):
    """Verifies that Grad-CAM visual heatmaps are properly generated and saved safely."""
    files = {"file": ("sugarcane_rust.jpg", sample_jpeg_bytes, "image/jpeg")}
    data = {
        "crop": "sugarcane",
        "generate_gradcam": "true",
        "save_heatmap": "true",
    }

    response = client.post("/api/v1/diagnose/predict", files=files, data=data)
    assert response.status_code == 200
    payload = response.json()

    assert payload["explanation_status"] == "generated"
    heatmap_path = payload["heatmap_path"]
    assert heatmap_path is not None

    # Verify physical file existence and decodability
    full_path = Path(heatmap_path)
    assert full_path.exists()
    assert full_path.is_file()

    with Image.open(full_path) as img:
        assert img.size == (224, 224)
        assert img.format in ["JPEG", "MPO"]

    # Safe cleanup after test
    try:
        full_path.unlink()
    except OSError:
        pass


def test_predict_invalid_extension(client: TestClient):
    """Verifies that non-image file extensions are rejected with HTTP 400."""
    files = {"file": ("malicious_payload.sh", b"echo hello", "text/x-sh")}
    response = client.post("/api/v1/diagnose/predict", files=files)
    assert response.status_code == 400
    assert "Unsupported file extension" in response.json()["detail"]


def test_predict_corrupted_header(client: TestClient):
    """Verifies that files with image extensions but invalid magic bytes are rejected."""
    files = {"file": ("fake_image.jpg", b"Plain text file content", "image/jpeg")}
    response = client.post("/api/v1/diagnose/predict", files=files)
    assert response.status_code == 400
    assert "header does not match a valid image" in response.json()["detail"]


def test_predict_empty_file(client: TestClient):
    """Verifies that empty files are rejected with HTTP 400."""
    files = {"file": ("empty.jpg", b"", "image/jpeg")}
    response = client.post("/api/v1/diagnose/predict", files=files)
    assert response.status_code == 400
    assert "Empty or corrupted file" in response.json()["detail"]


def test_predict_file_too_large(client: TestClient, monkeypatch):
    """Verifies that uploads exceeding MAX_UPLOAD_SIZE_MB trigger HTTP 413."""
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_MB", 1)  # 1 MB threshold for test
    oversized_data = b"\xff\xd8\xff" + (b"A" * (1024 * 1024 + 100))
    files = {"file": ("large.jpg", oversized_data, "image/jpeg")}

    response = client.post("/api/v1/diagnose/predict", files=files)
    assert response.status_code == 413
    assert "exceeds maximum allowed size" in response.json()["detail"]


def test_predict_unsupported_crop(client: TestClient, sample_jpeg_bytes: bytes):
    """Verifies that attempting prediction on an un-serviced crop returns HTTP 400."""
    files = {"file": ("leaf.jpg", sample_jpeg_bytes, "image/jpeg")}
    data = {"crop": "pineapple"}

    response = client.post("/api/v1/diagnose/predict", files=files, data=data)
    assert response.status_code == 400
    assert "only serves sugarcane" in response.json()["detail"]


def test_predict_model_loading_error(client: TestClient, sample_jpeg_bytes: bytes, monkeypatch):
    """Verifies that a failure to load the model returns HTTP 503 Service Unavailable."""
    # Temporarily set model_service as unloaded and simulate loading error
    original_loaded = model_service.is_loaded
    model_service.is_loaded = False

    def mock_load_model(*args, **kwargs):
        raise FileNotFoundError("Simulated missing checkpoint file.")

    monkeypatch.setattr(model_service, "load_model", mock_load_model)

    files = {"file": ("leaf.jpg", sample_jpeg_bytes, "image/jpeg")}
    data = {"crop": "sugarcane"}

    response = client.post("/api/v1/diagnose/predict", files=files, data=data)
    # Restore model_service state
    model_service.is_loaded = original_loaded

    assert response.status_code == 503
    assert "Model serving error" in response.json()["detail"]


def test_predict_inference_failure(client: TestClient, sample_jpeg_bytes: bytes, monkeypatch):
    """Verifies that a runtime exception during the model forward pass returns HTTP 500."""
    def mock_predict(*args, **kwargs):
        from app.services.model_service import InferenceError
        raise InferenceError("Simulated computational runtime crash.")

    monkeypatch.setattr(model_service, "predict", mock_predict)

    files = {"file": ("leaf.jpg", sample_jpeg_bytes, "image/jpeg")}
    data = {"crop": "sugarcane"}

    response = client.post("/api/v1/diagnose/predict", files=files, data=data)
    assert response.status_code == 500
    assert "Inference failure" in response.json()["detail"]


def test_predict_alias_route(client: TestClient, sample_jpeg_bytes: bytes):
    """Verifies that /api/v1/diagnostics/predict functions identically as an alias."""
    files = {"file": ("leaf.jpg", sample_jpeg_bytes, "image/jpeg")}
    data = {"crop": "sugarcane"}

    response = client.post("/api/v1/diagnostics/predict", files=files, data=data)
    assert response.status_code == 200
    assert response.json()["crop"] == "sugarcane"
