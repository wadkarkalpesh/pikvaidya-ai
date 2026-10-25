import io
import pytest
from fastapi.testclient import TestClient
from app.models.user import User
from app.models.crop_cycle import CropCycle


def test_submit_diagnosis_unauthorized(client: TestClient, test_crop: CropCycle, sample_jpeg_bytes: bytes):
    files = {"file": ("leaf.jpg", sample_jpeg_bytes, "image/jpeg")}
    response = client.post(f"/api/v1/crops/{test_crop.id}/diagnoses", files=files)
    assert response.status_code == 401


def test_submit_diagnosis_success(
    client: TestClient,
    test_user: User,
    test_crop: CropCycle,
    auth_headers: dict,
    sample_jpeg_bytes: bytes,
):
    files = {"file": ("sugarcane_leaf.jpg", sample_jpeg_bytes, "image/jpeg")}
    data = {
        "notes": "Spotted on lower leaves after rain",
        "temperature": 29.5,
        "humidity": 82.0,
        "soil_moisture": 45.0,
    }

    response = client.post(
        f"/api/v1/crops/{test_crop.id}/diagnoses",
        files=files,
        data=data,
        headers=auth_headers,
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["crop_cycle_id"] == test_crop.id
    assert payload["user_id"] == test_user.id
    assert payload["crop_name"] == "Sugarcane"
    assert payload["status"] == "COMPLETED"
    assert payload["disease_name_en"] is not None
    assert payload["disease_name_mr"] is not None
    assert payload["severity"] in ["MILD", "MODERATE", "SEVERE", "HEALTHY", "UNAVAILABLE", "UNVALIDATED"]
    assert payload["confidence"] > 0.0
    assert payload["symptoms_mr"] is not None
    assert payload["recommendations_mr"] is not None
    assert payload["temperature"] == 29.5
    assert payload["humidity"] == 82.0
    assert "image_path" in payload
    assert len(payload["image_hash"]) == 64


def test_submit_diagnosis_unsupported_crop(
    client: TestClient,
    unsupported_crop: CropCycle,
    auth_headers: dict,
    sample_jpeg_bytes: bytes,
):
    """Verifies that an unsupported crop (e.g. Cotton) returns a structured 400 error."""
    files = {"file": ("cotton_leaf.jpg", sample_jpeg_bytes, "image/jpeg")}
    response = client.post(
        f"/api/v1/crops/{unsupported_crop.id}/diagnoses",
        files=files,
        headers=auth_headers,
    )
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "unavailable for crop 'Cotton'" in detail
    assert "sugarcane" in detail.lower()


def test_submit_diagnosis_with_gradcam(
    client: TestClient,
    test_crop: CropCycle,
    auth_headers: dict,
    sample_jpeg_bytes: bytes,
):
    """Verifies that Grad-CAM generation in authenticated workflow produces and persists a heatmap."""
    files = {"file": ("sugarcane_leaf.jpg", sample_jpeg_bytes, "image/jpeg")}
    data = {"generate_gradcam": "true"}

    response = client.post(
        f"/api/v1/crops/{test_crop.id}/diagnoses",
        files=files,
        data=data,
        headers=auth_headers,
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["heatmap_path"] is not None
    from pathlib import Path
    heatmap_file = Path(payload["heatmap_path"])
    assert heatmap_file.exists()
    try:
        heatmap_file.unlink()
    except OSError:
        pass


def test_confidence_safety_moderate_suppresses_chemicals(
    client: TestClient,
    test_crop: CropCycle,
    auth_headers: dict,
    sample_jpeg_bytes: bytes,
    monkeypatch,
):
    """Verifies that moderate confidence (0.50 <= conf < 0.75) suppresses chemical prescriptions."""
    from app.services.model_service import model_service
    def mock_predict(*args, **kwargs):
        return {
            "crop": "sugarcane",
            "predicted_class": "RedRot",
            "confidence": 0.62,
            "class_scores": {"RedRot": 0.62, "Rust": 0.20, "Mosaic": 0.10, "Yellow": 0.05, "Healthy": 0.03},
            "model_version": "EfficientNet-B0-v1.0",
            "explanation_status": "available",
            "heatmap_path": None,
        }
    monkeypatch.setattr(model_service, "predict", mock_predict)

    files = {"file": ("leaf.jpg", sample_jpeg_bytes, "image/jpeg")}
    response = client.post(
        f"/api/v1/crops/{test_crop.id}/diagnoses",
        files=files,
        headers=auth_headers,
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["advisory_status"] == "LOW_CONFIDENCE_WARNING"
    assert "SUPPRESSED" in payload["recommendations_en"].upper()
    assert "स्थगित" in payload["recommendations_mr"]
    assert "Carbendazim" not in payload["recommendations_en"]
    assert payload["severity"] == "UNAVAILABLE"
    assert payload["affected_area_percentage"] is None


def test_confidence_safety_low_inconclusive(
    client: TestClient,
    test_crop: CropCycle,
    auth_headers: dict,
    sample_jpeg_bytes: bytes,
    monkeypatch,
):
    """Verifies that low confidence (< 0.50) returns inconclusive status and suppresses all chemicals."""
    from app.services.model_service import model_service
    def mock_predict(*args, **kwargs):
        return {
            "crop": "sugarcane",
            "predicted_class": "Rust",
            "confidence": 0.38,
            "class_scores": {"Rust": 0.38, "RedRot": 0.32, "Mosaic": 0.15, "Yellow": 0.10, "Healthy": 0.05},
            "model_version": "EfficientNet-B0-v1.0",
            "explanation_status": "available",
            "heatmap_path": None,
        }
    monkeypatch.setattr(model_service, "predict", mock_predict)

    files = {"file": ("leaf.jpg", sample_jpeg_bytes, "image/jpeg")}
    response = client.post(
        f"/api/v1/crops/{test_crop.id}/diagnoses",
        files=files,
        headers=auth_headers,
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["advisory_status"] == "UNCERTAIN_PREDICTION"
    assert payload["disease_name_en"] == "Uncertain Foliar Symptoms"
    assert "WITHHELD" in payload["recommendations_en"].upper()
    assert "रोखण्यात" in payload["recommendations_mr"]
    assert "Mancozeb" not in payload["recommendations_en"]
    assert "Propiconazole" not in payload["recommendations_en"]
    assert payload["severity"] == "UNAVAILABLE"
    assert payload["affected_area_percentage"] is None


def test_severity_unvalidated_for_disease(
    client: TestClient,
    test_crop: CropCycle,
    auth_headers: dict,
    sample_jpeg_bytes: bytes,
    monkeypatch,
):
    """Verifies that unvalidated disease severity is reported as UNAVAILABLE with None percentage."""
    from app.services.model_service import model_service
    def mock_predict(*args, **kwargs):
        return {
            "crop": "sugarcane",
            "predicted_class": "RedRot",
            "confidence": 0.92,
            "class_scores": {"RedRot": 0.92, "Rust": 0.03, "Mosaic": 0.02, "Yellow": 0.02, "Healthy": 0.01},
            "model_version": "EfficientNet-B0-v1.0",
            "explanation_status": "available",
            "heatmap_path": None,
        }
    monkeypatch.setattr(model_service, "predict", mock_predict)

    files = {"file": ("leaf.jpg", sample_jpeg_bytes, "image/jpeg")}
    response = client.post(
        f"/api/v1/crops/{test_crop.id}/diagnoses",
        files=files,
        headers=auth_headers,
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["advisory_status"] == "HIGH_CONFIDENCE"
    assert payload["severity"] in ["UNAVAILABLE", "UNVALIDATED"]
    assert payload["affected_area_percentage"] is None
    # Verify statutory disclaimer is present
    assert "Advisory Notice" in payload["recommendations_en"]
    assert "वैधानिक सूचना" in payload["recommendations_mr"]
    assert "Expert Verification Required" in payload["recommendations_en"]



def test_submit_diagnosis_invalid_extension(
    client: TestClient,
    test_crop: CropCycle,
    auth_headers: dict,
):
    files = {"file": ("script.sh", b"#!/bin/bash\necho test", "text/plain")}
    response = client.post(
        f"/api/v1/crops/{test_crop.id}/diagnoses",
        files=files,
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "Unsupported file extension" in response.json()["detail"]


def test_submit_diagnosis_corrupted_header(
    client: TestClient,
    test_crop: CropCycle,
    auth_headers: dict,
):
    # Has .jpg extension but content is plain text
    files = {"file": ("fake.jpg", b"This is plain text pretending to be image", "image/jpeg")}
    response = client.post(
        f"/api/v1/crops/{test_crop.id}/diagnoses",
        files=files,
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "header does not match a valid image" in response.json()["detail"]


def test_submit_diagnosis_crop_not_found(
    client: TestClient,
    auth_headers: dict,
    sample_jpeg_bytes: bytes,
):
    files = {"file": ("leaf.jpg", sample_jpeg_bytes, "image/jpeg")}
    response = client.post(
        "/api/v1/crops/99999/diagnoses",
        files=files,
        headers=auth_headers,
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Crop cycle not found."


def test_submit_diagnosis_cross_user_forbidden(
    client: TestClient,
    test_crop: CropCycle,
    other_auth_headers: dict,
    sample_jpeg_bytes: bytes,
):
    files = {"file": ("leaf.jpg", sample_jpeg_bytes, "image/jpeg")}
    response = client.post(
        f"/api/v1/crops/{test_crop.id}/diagnoses",
        files=files,
        headers=other_auth_headers,
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized to access this crop cycle."


def test_list_crop_diagnoses(
    client: TestClient,
    test_crop: CropCycle,
    auth_headers: dict,
    sample_jpeg_bytes: bytes,
):
    # First submit one diagnosis
    files = {"file": ("leaf1.jpg", sample_jpeg_bytes, "image/jpeg")}
    client.post(
        f"/api/v1/crops/{test_crop.id}/diagnoses",
        files=files,
        headers=auth_headers,
    )

    # List crop diagnoses
    response = client.get(
        f"/api/v1/crops/{test_crop.id}/diagnoses",
        headers=auth_headers,
    )
    assert response.status_code == 200
    records = response.json()
    assert len(records) >= 1
    assert records[0]["crop_cycle_id"] == test_crop.id
    assert "disease_name_en" in records[0]


def test_list_crop_diagnoses_cross_user_forbidden(
    client: TestClient,
    test_crop: CropCycle,
    other_auth_headers: dict,
):
    response = client.get(
        f"/api/v1/crops/{test_crop.id}/diagnoses",
        headers=other_auth_headers,
    )
    assert response.status_code == 403


def test_list_farmer_diagnostics(
    client: TestClient,
    test_crop: CropCycle,
    auth_headers: dict,
    sample_jpeg_bytes: bytes,
):
    # Submit diagnosis
    files = {"file": ("leaf2.jpg", sample_jpeg_bytes, "image/jpeg")}
    client.post(
        f"/api/v1/crops/{test_crop.id}/diagnoses",
        files=files,
        headers=auth_headers,
    )

    response = client.get(
        "/api/v1/diagnostics",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) >= 1


def test_get_diagnosis_detail_and_cross_user_protection(
    client: TestClient,
    test_crop: CropCycle,
    auth_headers: dict,
    other_auth_headers: dict,
    sample_jpeg_bytes: bytes,
):
    files = {"file": ("leaf_detail.jpg", sample_jpeg_bytes, "image/jpeg")}
    create_res = client.post(
        f"/api/v1/crops/{test_crop.id}/diagnoses",
        files=files,
        headers=auth_headers,
    )
    diagnosis_id = create_res.json()["id"]

    # Owner can access
    detail_res = client.get(
        f"/api/v1/diagnostics/{diagnosis_id}",
        headers=auth_headers,
    )
    assert detail_res.status_code == 200
    assert detail_res.json()["id"] == diagnosis_id
    assert detail_res.json()["symptoms_mr"] is not None

    # Other farmer cannot access
    unauth_res = client.get(
        f"/api/v1/diagnostics/{diagnosis_id}",
        headers=other_auth_headers,
    )
    assert unauth_res.status_code == 403
    assert unauth_res.json()["detail"] == "Not authorized to access this diagnostic record."


def test_delete_diagnosis_and_protection(
    client: TestClient,
    test_crop: CropCycle,
    auth_headers: dict,
    other_auth_headers: dict,
    sample_jpeg_bytes: bytes,
):
    files = {"file": ("leaf_delete.jpg", sample_jpeg_bytes, "image/jpeg")}
    create_res = client.post(
        f"/api/v1/crops/{test_crop.id}/diagnoses",
        files=files,
        headers=auth_headers,
    )
    diagnosis_id = create_res.json()["id"]

    # Other user cannot delete
    forbidden_res = client.delete(
        f"/api/v1/diagnostics/{diagnosis_id}",
        headers=other_auth_headers,
    )
    assert forbidden_res.status_code == 403

    # Owner deletes successfully
    del_res = client.delete(
        f"/api/v1/diagnostics/{diagnosis_id}",
        headers=auth_headers,
    )
    assert del_res.status_code == 204

    # Subsequent fetch returns 404
    get_res = client.get(
        f"/api/v1/diagnostics/{diagnosis_id}",
        headers=auth_headers,
    )
    assert get_res.status_code == 404
