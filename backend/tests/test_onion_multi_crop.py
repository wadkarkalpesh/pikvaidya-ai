"""
PikVaidya AI — Onion Multi-Crop Pathology Test Suite
===================================================
Automated test suite validating the complete Onion Pathology Engine:
  - 4-Class Model Loading (MobileNetV3-Large, T*=2.2000)
  - ONNX Runtime Inference & Numerical Parity
  - Stateless Foliar Diagnostic API (/api/v1/diagnose/predict)
  - Context-Aware CIBRC Recommendation Engine (DOGR Fungicides, PPE, PHI)
  - Multilingual RAG Agricultural Assistant (English & Marathi)
  - Empirical Foliar Severity Segmentation
"""

import io
from PIL import Image
import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.services.model_service import model_service
from app.services.disease_service import disease_service
from app.services.recommendation_engine import recommendation_engine
from app.services.segmentation_service import segmentation_service
from app.services.rag.indexer import rag_indexer
from app.models.diagnosis import DiagnosisSeverity

client = TestClient(app)


@pytest.fixture
def onion_sample_leaf() -> bytes:
    """Creates a synthetic onion leaf JPEG with valid foliar coverage for diagnostic tests."""
    arr = np.zeros((224, 224, 3), dtype=np.uint8)
    # Ample green foliage blade
    arr[:, 30:190] = [45, 140, 55]
    # Purple blotch lesion in center
    arr[60:140, 70:150] = [70, 25, 55]
    img = Image.fromarray(arr)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_onion_model_registry():
    """Verify onion model is registered and loads 4 classes."""
    assert "onion" in model_service.CROP_REGISTRY
    model_service.load_model(crop="onion")
    entry = model_service.crop_models["onion"]
    assert entry["model"] is not None
    assert len(entry["idx_to_class"]) == 4
    class_names = set(entry["idx_to_class"].values())
    assert "Onion___healthy" in class_names
    assert "Onion___purple_blotch" in class_names
    assert "Onion___stemphylium_blight" in class_names
    assert "Onion___iris_yellow_virus" in class_names


def test_onion_onnx_parity(onion_sample_leaf: bytes):
    """Verify ONNX runtime inference yields parity on onion leaf."""
    res_py = model_service.predict(onion_sample_leaf, crop="onion", use_onnx=False)
    res_ox = model_service.predict(onion_sample_leaf, crop="onion", use_onnx=True)

    assert res_py["crop"] == "onion"
    assert res_ox["crop"] == "onion"
    assert res_py["predicted_class"] == res_ox["predicted_class"]
    assert abs(res_py["confidence"] - res_ox["confidence"]) < 0.05


def test_onion_predict_endpoint(onion_sample_leaf: bytes):
    """Verify /api/v1/diagnose/predict endpoint serves onion crop."""
    files = {"file": ("onion_leaf.jpg", onion_sample_leaf, "image/jpeg")}
    data = {"crop": "onion", "generate_gradcam": "false"}

    response = client.post("/api/v1/diagnose/predict", files=files, data=data)
    assert response.status_code == 200
    payload = response.json()

    assert payload["crop"] == "onion"
    assert payload["predicted_class"] in [
        "Onion___healthy",
        "Onion___purple_blotch",
        "Onion___stemphylium_blight",
        "Onion___iris_yellow_virus",
    ]
    assert 0.0 <= payload["confidence"] <= 1.0
    assert len(payload["class_scores"]) == 4


@pytest.mark.anyio
async def test_onion_cibrc_advisory_generation(db: Session):
    """Verify context-aware recommendations for Onion Purple Blotch."""
    disease_service.seed_default_diseases(db)

    from app.schemas.advisory import AdvisoryGenerateRequest
    req = AdvisoryGenerateRequest(
        crop_name="onion",
        predicted_disease="Onion___purple_blotch",
        confidence=0.92,
        temperature=26.0,
        humidity=78.0,
        wind_speed_kmh=8.0,
        precipitation_probability=5.0,
        preferred_language="en",
    )

    advisory = await recommendation_engine.generate_advisory(req, db=db)
    assert advisory.crop_name == "onion"
    assert advisory.weather_telemetry.spray_suitability == "OPTIMAL"
    assert len(advisory.chemical_prescriptions) >= 1
    # Verify CIBRC active ingredients
    actives = " ".join([p.chemical_name for p in advisory.chemical_prescriptions])
    assert any(ing in actives for ing in ["Mancozeb", "Difenoconazole", "Tebuconazole"])
    assert advisory.statutory_disclaimer is not None


def test_onion_rag_assistant_retrieval():
    """Verify RAG index retrieves onion disease knowledge."""
    rag_indexer.build_index_from_seeds()
    query = "How to control purple blotch in onion crop?"
    results = rag_indexer.search(query, top_k=3, crop_filter="onion")

    assert len(results) > 0
    top_chunk = results[0].chunk
    assert top_chunk.crop == "onion"
    assert "purple_blotch" in top_chunk.disease_id or "Alternaria" in top_chunk.text


def test_onion_foliar_severity():
    """Verify empirical lesion severity segmentation on onion."""
    arr = np.zeros((100, 100, 3), dtype=np.uint8)
    # Healthy blade
    arr[:, 30:70] = [45, 140, 55]
    # Purple blotch lesion
    arr[20:60, 32:68] = [70, 25, 55]
    img = Image.fromarray(arr)

    sev, area = segmentation_service.estimate_foliar_severity(img, "Onion___purple_blotch", crop="onion")
    assert sev in [DiagnosisSeverity.MILD, DiagnosisSeverity.MODERATE, DiagnosisSeverity.SEVERE]
    assert area is not None
    assert area >= 1.0
