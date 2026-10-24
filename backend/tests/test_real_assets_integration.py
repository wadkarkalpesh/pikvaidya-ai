import io
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.core.config import settings
from app.models.user import User
from app.models.farm import Farm
from app.models.crop_cycle import CropCycle
from app.models.diagnosis import Diagnosis, DiagnosisStatus
from app.services.model_service import model_service


@pytest.fixture(scope="module")
def real_sugarcane_leaf_bytes() -> bytes:
    """Reads a real sugarcane leaf image from data/raw/sugarcane/Healthy."""
    # Find project root
    for p in [Path.cwd(), Path.cwd().parent]:
        img_path = p / "data" / "raw" / "sugarcane" / "Healthy" / "healthy (188).jpeg"
        if img_path.exists():
            return img_path.read_bytes()
    pytest.skip("Real sugarcane test image not found in repository.")


@pytest.fixture(scope="function")
def sugarcane_crop(db, test_farm: Farm) -> CropCycle:
    """Creates a sugarcane crop cycle for real pathology integration tests."""
    crop = CropCycle(
        farm_id=test_farm.id,
        crop="sugarcane",
        variety="Co 86032",
        growth_stage="Grand Growth",
        status="active",
    )
    db.add(crop)
    db.commit()
    db.refresh(crop)
    return crop


def test_predict_real_image_valid_output(client: TestClient, real_sugarcane_leaf_bytes: bytes):
    """Phase 6: Verifies prediction output format on real repository image asset."""
    files = {"file": ("healthy_leaf.jpeg", real_sugarcane_leaf_bytes, "image/jpeg")}
    data = {"crop": "sugarcane", "generate_gradcam": "false"}

    response = client.post("/api/v1/diagnose/predict", files=files, data=data)
    assert response.status_code == 200
    payload = response.json()

    assert payload["crop"] == "sugarcane"
    assert payload["predicted_class"] == "Healthy"
    assert payload["confidence"] > 0.85
    assert payload["model_version"] == "EfficientNet-B0-v1.0"
    assert payload["explanation_status"] == "available"
    assert payload["heatmap_path"] is None

    # Verify probability distribution
    scores = payload["class_scores"]
    assert len(scores) == 5
    assert set(scores.keys()) == {"Healthy", "Mosaic", "RedRot", "Rust", "Yellow"}
    prob_sum = sum(scores.values())
    assert 0.99 <= prob_sum <= 1.01
    for k, v in scores.items():
        assert 0.0 <= v <= 1.0


def test_predict_real_image_with_gradcam(client: TestClient, real_sugarcane_leaf_bytes: bytes):
    """Phase 6: Verifies Grad-CAM heatmap generation with real image asset."""
    files = {"file": ("healthy_leaf.jpeg", real_sugarcane_leaf_bytes, "image/jpeg")}
    data = {
        "crop": "sugarcane",
        "generate_gradcam": "true",
        "save_heatmap": "true",
    }

    response = client.post("/api/v1/diagnose/predict", files=files, data=data)
    assert response.status_code == 200
    payload = response.json()

    assert payload["explanation_status"] == "generated"
    heatmap_path_str = payload["heatmap_path"]
    assert heatmap_path_str is not None

    heatmap_path = Path(heatmap_path_str)
    assert heatmap_path.exists()
    assert heatmap_path.is_file()

    # Verify dimensions and RGB format
    orig_img = Image.open(io.BytesIO(real_sugarcane_leaf_bytes))
    with Image.open(heatmap_path) as h_img:
        assert h_img.size == orig_img.size
        assert h_img.mode == "RGB"

    # Cleanup heatmap after test
    try:
        heatmap_path.unlink()
    except OSError:
        pass


def test_predict_truncated_corrupted_image(client: TestClient, real_sugarcane_leaf_bytes: bytes):
    """Phase 6: Verifies rejection of corrupted image (truncated JPEG bytes)."""
    # Keep valid header but truncate remainder to corrupt image data
    truncated_bytes = real_sugarcane_leaf_bytes[:150]
    files = {"file": ("corrupted.jpeg", truncated_bytes, "image/jpeg")}

    response = client.post("/api/v1/diagnose/predict", files=files)
    assert response.status_code == 400
    assert "Invalid or corrupted image content" in response.json()["detail"]


def test_predict_spoofed_magic_bytes(client: TestClient):
    """Phase 6: Verifies rejection of non-image file spoofed with JPEG extension."""
    files = {"file": ("fake.jpg", b"Plain text file content not a jpeg", "image/jpeg")}
    response = client.post("/api/v1/diagnose/predict", files=files)
    assert response.status_code == 400
    assert "header does not match a valid image" in response.json()["detail"]


def test_predict_oversized_payload(client: TestClient, monkeypatch):
    """Phase 6: Verifies rejection of oversized uploads with HTTP 413."""
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_MB", 1)
    large_payload = b"\xff\xd8\xff" + b"X" * (1024 * 1024 + 100)
    files = {"file": ("large.jpg", large_payload, "image/jpeg")}

    response = client.post("/api/v1/diagnose/predict", files=files)
    assert response.status_code == 413
    assert "exceeds maximum allowed size" in response.json()["detail"]


def test_predict_model_loading_failure_safe_error(client: TestClient, real_sugarcane_leaf_bytes: bytes, monkeypatch):
    """Phase 6: Verifies that model loading failure returns HTTP 503 without leaking paths."""
    original_loaded = model_service.is_loaded
    model_service.is_loaded = False

    def mock_load():
        raise FileNotFoundError("Simulated internal checkpoint missing")

    monkeypatch.setattr(model_service, "load_model", mock_load)

    files = {"file": ("leaf.jpeg", real_sugarcane_leaf_bytes, "image/jpeg")}
    response = client.post("/api/v1/diagnose/predict", files=files)

    model_service.is_loaded = original_loaded

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert "Model serving error" in detail
    # Ensure no internal filesystem paths or stack traces leaked
    assert "C:\\" not in detail
    assert "E:\\" not in detail
    assert "Traceback" not in detail


def test_full_database_persistence_workflow(
    client: TestClient,
    sugarcane_crop: CropCycle,
    auth_headers: dict,
    real_sugarcane_leaf_bytes: bytes,
    db,
):
    """Phase 6: Verifies full end-to-end database persistence with real image upload."""
    files = {"file": ("real_leaf.jpeg", real_sugarcane_leaf_bytes, "image/jpeg")}
    data = {
        "notes": "Real field leaf from Kolhapur sugarcane farm",
        "temperature": 32.0,
        "humidity": 75.0,
        "soil_moisture": 60.0,
    }

    # 1. Submit diagnosis
    response = client.post(
        f"/api/v1/crops/{sugarcane_crop.id}/diagnoses",
        files=files,
        data=data,
        headers=auth_headers,
    )
    assert response.status_code == 201
    payload = response.json()
    diagnosis_id = payload["id"]
    image_rel_path = payload["image_path"]

    assert payload["status"] == "COMPLETED"
    assert payload["crop_name"] == "sugarcane"
    assert payload["disease_name_en"] is not None
    assert payload["disease_name_mr"] is not None
    assert payload["symptoms_en"] is not None
    assert payload["symptoms_mr"] is not None
    assert payload["recommendations_en"] is not None
    assert payload["recommendations_mr"] is not None

    # Verify physical file stored in upload directory
    stored_file = Path(settings.UPLOAD_DIR) / image_rel_path
    assert stored_file.exists()

    # 2. Retrieve diagnosis detail
    detail_res = client.get(
        f"/api/v1/diagnostics/{diagnosis_id}",
        headers=auth_headers,
    )
    assert detail_res.status_code == 200
    assert detail_res.json()["id"] == diagnosis_id

    # 3. Retrieve list for crop
    list_res = client.get(
        f"/api/v1/crops/{sugarcane_crop.id}/diagnoses",
        headers=auth_headers,
    )
    assert list_res.status_code == 200
    assert any(d["id"] == diagnosis_id for d in list_res.json())

    # 4. Delete diagnosis and verify disk and DB cleanup
    del_res = client.delete(
        f"/api/v1/diagnostics/{diagnosis_id}",
        headers=auth_headers,
    )
    assert del_res.status_code == 204
    assert not stored_file.exists(), "Stored image file was not deleted upon diagnosis deletion"

    # Subsequent GET returns 404
    assert client.get(f"/api/v1/diagnostics/{diagnosis_id}", headers=auth_headers).status_code == 404
