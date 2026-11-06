"""
PikVaidya AI — Agricultural Disease Knowledge Base Test Suite
=============================================================
Automated test suite covering:
  - Database schema & model initialization
  - Seed data verification (all 5 Sugarcane pathology categories)
  - CRUD operations and error handling
  - Full-text multilingual search (English, Marathi, Hindi)
  - RAG document formatting and metadata
  - FastAPI endpoints (both /api/v1/diseases and /api/diseases aliases)
  - Missing records and validation edge cases
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.disease import DiseaseInformation
from app.services.disease_service import disease_service
from app.schemas.disease import DiseaseCreate


def test_seed_and_list_diseases(db: Session, client: TestClient):
    """Verifies that the database seeds multi-crop categories with complete metadata."""
    seeded = disease_service.seed_default_diseases(db)
    assert seeded == 27, f"Expected 27 seeded records, got {seeded}"

    diseases = disease_service.get_diseases(db, limit=100)
    assert len(diseases) == 27

    sugarcane_diseases = disease_service.get_diseases(db, crop_name="sugarcane")
    assert len(sugarcane_diseases) == 5

    tomato_diseases = disease_service.get_diseases(db, crop_name="tomato")
    assert len(tomato_diseases) == 10

    onion_diseases = disease_service.get_diseases(db, crop_name="onion")
    assert len(onion_diseases) == 12

    disease_ids = {d.disease_id for d in sugarcane_diseases}
    expected_ids = {
        "sugarcane_healthy",
        "sugarcane_mosaic",
        "sugarcane_red_rot",
        "sugarcane_rust",
        "sugarcane_yellow_leaf",
    }
    assert disease_ids == expected_ids


def test_get_disease_by_id_and_not_found(db: Session, client: TestClient):
    """Verifies retrieval by disease_id and 404 handling."""
    disease_service.seed_default_diseases(db)

    # Valid query
    red_rot = disease_service.get_disease_by_id(db, "sugarcane_red_rot")
    assert red_rot is not None
    assert red_rot.disease_name == "Red Rot"
    assert "Colletotrichum falcatum" in red_rot.scientific_name
    assert red_rot.pathogen_type == "Fungal"
    assert "en" in red_rot.symptoms and "mr" in red_rot.symptoms

    # API test: 200 OK
    resp = client.get("/api/v1/diseases/sugarcane_red_rot")
    assert resp.status_code == 200
    data = resp.json()
    assert data["disease_name"] == "Red Rot"
    assert data["crop_name"] == "sugarcane"

    # API test: unversioned alias /api/diseases/{id}
    resp_alias = client.get("/api/diseases/sugarcane_red_rot")
    assert resp_alias.status_code == 200
    assert resp_alias.json()["disease_name"] == "Red Rot"

    # Missing ID: 404 Not Found
    resp_404 = client.get("/api/v1/diseases/non_existent_pathology")
    assert resp_404.status_code == 404
    assert "not found" in resp_404.json()["detail"].lower()


def test_get_diseases_by_crop(db: Session, client: TestClient):
    """Verifies retrieval of diseases by crop name."""
    disease_service.seed_default_diseases(db)

    # Valid crop: sugarcane
    resp = client.get("/api/v1/diseases/crop/sugarcane")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 5
    for item in items:
        assert item["crop_name"] == "sugarcane"

    # Unseeded crop: 404 Not Found
    resp_empty = client.get("/api/v1/diseases/crop/cotton")
    assert resp_empty.status_code == 404
    assert "cotton" in resp_empty.json()["detail"].lower()


def test_multilingual_search(db: Session, client: TestClient):
    """Verifies search across English, Marathi, and Hindi symptom and cause keywords."""
    disease_service.seed_default_diseases(db)

    # 1. Search in English by pathogen keyword: "Colletotrichum"
    resp_en = client.get("/api/v1/diseases/search?q=Colletotrichum")
    assert resp_en.status_code == 200
    results_en = resp_en.json()
    assert len(results_en) >= 1
    assert any(r["disease_id"] == "sugarcane_red_rot" for r in results_en)

    # 2. Search by symptom keyword: "uredinia" (rust pustules)
    resp_rust = client.get("/api/v1/diseases/search?q=uredinia")
    assert resp_rust.status_code == 200
    results_rust = resp_rust.json()
    assert len(results_rust) >= 1
    assert results_rust[0]["disease_id"] == "sugarcane_rust"

    # 3. Search in Marathi: "कॅन्सर" (Red Rot symptom text)
    resp_mr = client.get("/api/v1/diseases/search?q=कॅन्सर")
    assert resp_mr.status_code == 200
    results_mr = resp_mr.json()
    assert len(results_mr) >= 1
    assert any(r["disease_id"] == "sugarcane_red_rot" for r in results_mr)

    # 4. Search in Hindi: "धब्बे" (spots/blotches)
    resp_hi = client.get("/api/v1/diseases/search?q=धब्बे")
    assert resp_hi.status_code == 200
    assert len(resp_hi.json()) >= 1

    # 5. Non-existent query string
    resp_none = client.get("/api/v1/diseases/search?q=supercalifragilistic")
    assert resp_none.status_code == 200
    assert len(resp_none.json()) == 0


def test_rag_document_transformation(db: Session, client: TestClient):
    """Verifies that structured disease records format into dense RAG documents."""
    disease_service.seed_default_diseases(db)

    mosaic = disease_service.get_disease_by_id(db, "sugarcane_mosaic")
    assert mosaic is not None

    # English RAG document
    doc_en = mosaic.to_rag_document(lang="en")
    assert doc_en["document_id"] == "sugarcane_mosaic_en"
    assert doc_en["crop"] == "sugarcane"
    assert "SYMPTOMS" in doc_en["content"]
    assert "CAUSES" in doc_en["content"]
    assert "MANAGEMENT" in doc_en["content"]
    assert "Potyvirus" in doc_en["content"] or "aphid" in doc_en["content"]

    # Marathi RAG document
    doc_mr = mosaic.to_rag_document(lang="mr")
    assert doc_mr["document_id"] == "sugarcane_mosaic_mr"
    assert "हिरव्या" in doc_mr["content"]

    # Endpoint test: /api/v1/diseases/{id}/rag
    resp_rag = client.get("/api/v1/diseases/sugarcane_mosaic/rag?lang=en")
    assert resp_rag.status_code == 200
    rag_payload = resp_rag.json()
    assert rag_payload["disease_id"] == "sugarcane_mosaic"
    assert len(rag_payload["content"]) > 200


def test_crud_create_custom_disease(db: Session, client: TestClient):
    """Verifies creating a new disease record adheres to Pydantic validation and database persistence."""
    custom_in = DiseaseCreate(
        disease_id="cotton_leaf_curl",
        crop_name="cotton",
        disease_name="Cotton Leaf Curl Virus",
        scientific_name="Cotton leaf curl virus (CLCuV)",
        pathogen_type="Viral",
        symptoms={
            "en": "Upward or downward leaf curling, thickened veins, enations on underside.",
            "mr": "पानांच्या कडा वर किंवा खाली वळणे, शिरा जाड होणे.",
            "hi": "पत्तियों का मुड़ना और शिराओं का मोटा होना।"
        },
        causes={
            "en": "Transmitted by whitefly vector (Bemisia tabaci).",
            "mr": "पांढऱ्या माशीद्वारे प्रसार.",
            "hi": "सफेद मक्खी द्वारा संचरण।"
        },
        favourable_conditions={
            "temperature_range_c": "28-36°C",
            "humidity_pct": "65-85%",
            "en": "Warm humid conditions favoring whitefly multiplication."
        },
        prevention_methods={
            "en": ["Grow CLCuV resistant cotton hybrids.", "Eradicate weed hosts like Abutilon indicum."]
        },
        management_methods={
            "cultural": {"en": "Remove and bury infected plants."},
            "biological": {"en": "Spray Neem oil 1500 ppm @ 5 ml/L."},
            "chemical": [{"chemical_name": "Diafenthiuron", "formulation": "50% WP", "dosage_per_liter": "1.2 g/L", "cibrc_approved": True, "phi_days": 30}]
        },
        reference_sources=[{"source_name": "CICR Nagpur Cotton Advisory", "organization": "ICAR-CICR"}],
        language="multilingual",
        is_verified=True,
        last_verified="2026-11-01"
    )

    created = disease_service.create_disease(db, custom_in)
    assert created.disease_id == "cotton_leaf_curl"
    assert created.crop_name == "cotton"

    # Query via API
    resp = client.get("/api/v1/diseases/cotton_leaf_curl")
    assert resp.status_code == 200
    assert resp.json()["disease_name"] == "Cotton Leaf Curl Virus"

    # Query via crop endpoint
    resp_crop = client.get("/api/v1/diseases/crop/cotton")
    assert resp_crop.status_code == 200
    assert len(resp_crop.json()) == 1


def test_search_validation_empty_query(client: TestClient):
    """Verifies that an empty query returns a 422 Unprocessable Entity error."""
    resp = client.get("/api/v1/diseases/search?q=")
    assert resp.status_code == 422

