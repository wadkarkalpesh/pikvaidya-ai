import io
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.crop_cycle import CropCycle
from app.models.diagnosis import DiagnosisSeverity
from app.services.model_service import model_service, UnsupportedCropError
from app.services.diagnostic_service import diagnostic_service
from app.services.disease_service import disease_service
from app.services.recommendation_engine import recommendation_engine
from app.services.rag.indexer import rag_indexer
from app.services.rag.grounding import AgriculturalGroundingEngine
from app.schemas.advisory import AdvisoryGenerateRequest


@pytest.fixture
def tomato_test_leaf_bytes() -> bytes:
    """Generates synthetic green tomato leaf bytes."""
    img = Image.new("RGB", (224, 224), color=(34, 139, 34))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_tomato_model_loading_and_architecture():
    """Verifies that the multi-crop model service loads the 10-class Tomato model."""
    model_service.load_model(crop="tomato")
    assert "tomato" in model_service.crop_models
    entry = model_service.crop_models["tomato"]
    assert entry["num_classes"] == 10
    assert "Early_blight" in entry["class_to_idx"]
    assert "Late_blight" in entry["class_to_idx"]
    assert "Healthy" in entry["class_to_idx"]
    assert "Yellow_Leaf_Curl_Virus" in entry["class_to_idx"]
    assert entry["temperature"] == 0.8350


def test_tomato_prediction_with_gradcam(tomato_test_leaf_bytes):
    """Verifies end-to-end forward pass and Grad-CAM generation for tomato foliage."""
    res = model_service.predict(
        image=tomato_test_leaf_bytes,
        crop="tomato",
        generate_gradcam=True,
        save_heatmap=False,
    )
    assert res["crop"] == "tomato"
    assert res["predicted_class"] in model_service.crop_models["tomato"]["class_to_idx"]
    assert 0.0 <= res["confidence"] <= 1.0
    assert len(res["class_scores"]) == 10
    assert res["explanation_status"] in ["available", "generated"]


def test_tomato_disease_database_seeding(db: Session):
    """Verifies that all 10 tomato disease profiles are seeded into the database."""
    disease_service.seed_default_diseases(db)
    tomato_records = disease_service.get_diseases_by_crop(db, "tomato")
    assert len(tomato_records) == 10

    d_ids = {r.disease_id for r in tomato_records}
    assert "tomato_early_blight" in d_ids
    assert "tomato_late_blight" in d_ids
    assert "tomato_bacterial_spot" in d_ids
    assert "tomato_yellow_leaf_curl_virus" in d_ids
    assert "tomato_healthy" in d_ids

    # Verify multilingual symptoms exist
    eb = disease_service.get_disease_by_id(db, "tomato_early_blight")
    assert "Alternaria" in eb.scientific_name
    assert "en" in eb.symptoms
    assert "mr" in eb.symptoms
    assert "hi" in eb.symptoms


def test_tomato_diagnostic_advisory_safety_tiers():
    """Verifies that tomato diagnostic safety gating correctly manages confidence tiers."""
    scores = {c: 0.05 for c in model_service.crop_models["tomato"]["class_to_idx"]}
    scores["Early_blight"] = 0.92

    # 1. High confidence fungal disease
    res_high = diagnostic_service.evaluate_safety_and_advisory(
        crop="tomato",
        predicted_class="Early_blight",
        confidence=0.92,
        class_scores=scores,
    )
    assert res_high.advisory_status == "HIGH_CONFIDENCE"
    assert "Azoxystrobin" in res_high.recommendations_en or "Mancozeb" in res_high.recommendations_en
    assert "मॅन्कोझेब" in res_high.recommendations_mr or "अॅझॉक्सीस्ट्रॉबिन" in res_high.recommendations_mr

    # 2. Moderate confidence suppression
    res_mod = diagnostic_service.evaluate_safety_and_advisory(
        crop="tomato",
        predicted_class="Early_blight",
        confidence=0.62,
        class_scores=scores,
    )
    assert res_mod.advisory_status == "LOW_CONFIDENCE_WARNING"
    assert "chemical recommendations are withheld" in res_mod.recommendations_en.lower()

    # 3. Healthy foliage
    res_healthy = diagnostic_service.evaluate_safety_and_advisory(
        crop="tomato",
        predicted_class="Healthy",
        confidence=0.95,
        class_scores=scores,
    )
    assert res_healthy.advisory_status == "HEALTHY"
    assert res_healthy.severity == DiagnosisSeverity.HEALTHY


@pytest.mark.anyio
async def test_tomato_context_aware_recommendation_engine(db: Session):
    """Verifies the recommendation engine generates microclimate-grounded tomato advisory."""
    disease_service.seed_default_diseases(db)

    req = AdvisoryGenerateRequest(
        crop_name="tomato",
        predicted_disease="Early_blight",
        confidence=0.88,
        latitude=18.5204,  # Pune, Maharashtra
        longitude=73.8567,
        growth_stage="Vegetative",
        severity_percentage=18.5,
    )
    advisory = await recommendation_engine.generate_advisory(req, db=db)
    assert advisory.crop_name == "tomato"
    assert advisory.confidence_tier == "HIGH"
    assert advisory.is_chemical_permitted is True
    assert len(advisory.chemical_prescriptions) >= 1
    assert "Insecticides Act, 1968" in advisory.statutory_disclaimer["en"]


def test_tomato_rag_hybrid_retrieval():
    """Verifies that RAG hybrid indexer retrieves and grounds tomato disease queries."""
    rag_indexer.build_index_from_seeds()

    # Marathi query for tomato blight
    results_mr = rag_indexer.search(
        query="टोमॅटोवरील करपा रोगाची लक्षणे कोणती?",
        crop_filter="tomato",
        language_filter="mr",
        top_k=3,
    )
    assert len(results_mr) >= 1
    assert any(r.chunk.crop == "tomato" for r in results_mr)
    assert any("करप" in r.chunk.text or "blight" in r.chunk.disease_name.lower() or "ठिपके" in r.chunk.text for r in results_mr)

    # English query for tomato late blight
    results_en = rag_indexer.search(
        query="What fungicide cures tomato late blight?",
        crop_filter="tomato",
        language_filter="en",
        top_k=3,
    )
    assert len(results_en) >= 1
    grounded = AgriculturalGroundingEngine.synthesize_response(
        query="What fungicide cures tomato late blight?",
        retrieval_results=results_en,
        language="en",
    )
    assert grounded.is_grounded is True
    assert "ICAR" in str(grounded.retrieved_sources) or "IIHR" in str(grounded.retrieved_sources)
    assert "Insecticides Act, 1968" in grounded.statutory_disclaimer


def test_tomato_api_endpoints(client: TestClient, tomato_test_leaf_bytes):
    """Verifies multi-crop FastAPI endpoints for tomato disease prediction and knowledge."""
    # 1. Direct prediction endpoint with crop=tomato
    files = {"file": ("tomato_leaf.jpg", tomato_test_leaf_bytes, "image/jpeg")}
    data = {"crop": "tomato", "generate_gradcam": "true"}
    resp = client.post("/api/v1/diagnose/predict", files=files, data=data)
    assert resp.status_code == 200
    res_json = resp.json()
    assert res_json["crop"] == "tomato"
    assert len(res_json["class_scores"]) == 10

    # 2. Disease knowledge API crop filter endpoint
    d_resp = client.get("/api/v1/diseases?crop=tomato")
    assert d_resp.status_code == 200
    d_list = d_resp.json()
    assert len(d_list) == 10
