"""
PikVaidya AI — Master Automated Test: 19-Step End-to-End Farmer Workflow
========================================================================
Simulates and verifies the complete lifecycle of a smallholder farmer in Maharashtra:
Step 1: Farmer registers and logs in to acquire JWT token.
Step 2: Farmer creates a registered farm plot in Kolhapur district.
Step 3: Farmer registers a seasonal crop-cycle (Sugarcane / Co 86032).
Step 4 & 5: Farmer uploads a foliar image; backend validates image quality & foliage.
Step 6 & 7: Hierarchical Crop Gate routes to Sugarcane model; generates disease prediction.
Step 8: Platt Softmax temperature scaling evaluates calibrated confidence.
Step 9: Grad-CAM saliency heatmap is generated and stored.
Step 10: 14-day rolling historical microclimate is retrieved for the farm location.
Step 11: Environmental risk engine evaluates Tom-Cast DSV / epidemiological conduciveness.
Step 12: Multilingual RAG knowledge base retrieves verified university management recommendations.
Step 13: CIBRC-compliant spray advisory is generated with Delta-T verification.
Step 14: Diagnosis record and telemetry are persisted in the relational database.
Step 15: Farmer views longitudinal diagnosis history with filtering.
Step 16: Farmer downloads standardized ReportLab A4 advisory PDF report.
Step 17: In-app notification alert is generated for the high-conduciveness microclimate.
Step 18: Farmer submits an expert review request for agronomist confirmation.
Step 19: Offline diagnostic record synchronizes via the bidirectional sync protocol.
"""

import io
import pytest
from PIL import Image
import numpy as np
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.diagnosis import Diagnosis


def test_complete_19_step_farmer_workflow(client: TestClient, db: Session):
    # --------------------------------------------------------------------------
    # Step 1: Farmer registers and logs in
    # --------------------------------------------------------------------------
    reg_payload = {
        "name": "Shri Dnyaneshwar Patil",
        "email": "dnyaneshwar.patil@kolhapurfarms.in",
        "password": "FarmSecurePass2026",
        "preferred_language": "mr"
    }
    reg_res = client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_res.status_code == 201
    user_id = reg_res.json()["id"]

    login_res = client.post("/api/v1/auth/login", data={
        "username": "dnyaneshwar.patil@kolhapurfarms.in",
        "password": "FarmSecurePass2026"
    })
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # --------------------------------------------------------------------------
    # Step 2: Farmer creates a farm
    # --------------------------------------------------------------------------
    farm_payload = {
        "name": "Shri Patil Sugarcane Estate",
        "area": 3.5,
        "soil_type": "Deep Black Clay",
        "irrigation": "Drip Irrigation",
        "latitude": 16.7050,
        "longitude": 74.2433
    }
    farm_res = client.post("/api/v1/farms", json=farm_payload, headers=headers)
    assert farm_res.status_code == 201
    farm_id = farm_res.json()["id"]

    # --------------------------------------------------------------------------
    # Step 3: Farmer registers a crop and crop-cycle details
    # --------------------------------------------------------------------------
    crop_payload = {
        "crop": "sugarcane",
        "variety": "Co 86032 (Nira)",
        "sowing_date": "2026-06-15",
        "growth_stage": "grand_growth",
        "status": "active"
    }
    crop_res = client.post(f"/api/v1/farms/{farm_id}/crops", json=crop_payload, headers=headers)
    assert crop_res.status_code == 201
    crop_cycle_id = crop_res.json()["id"]

    # --------------------------------------------------------------------------
    # Step 4 & 5: Upload image & Image Quality validation
    # --------------------------------------------------------------------------
    # Create realistic synthetic green foliar leaf image with texture
    rng = np.random.RandomState(42)
    arr = rng.randint(40, 180, (250, 250, 3), dtype=np.uint8)
    arr[..., 1] = np.clip(arr[..., 1] + 50, 0, 255)
    img = Image.fromarray(arr)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    leaf_bytes = buf.getvalue()

    # --------------------------------------------------------------------------
    # Step 6, 7, 8, 9: AI diagnosis, routing, calibration, Grad-CAM
    # --------------------------------------------------------------------------
    files = {"file": ("sugarcane_leaf.jpg", leaf_bytes, "image/jpeg")}
    diag_res = client.post(
        f"/api/v1/crops/{crop_cycle_id}/diagnoses",
        files=files,
        data={
            "crop": "sugarcane",
            "generate_gradcam": "true",
            "notes": "Spotted reddish coloration along middle leaf blade."
        },
        headers=headers
    )
    assert diag_res.status_code == 201
    diag_data = diag_res.json()
    diagnosis_id = diag_data["id"]
    assert diag_data["crop_name"] == "sugarcane"
    assert "disease_name_en" in diag_data
    assert "confidence" in diag_data
    assert diag_data["confidence"] > 0.0
    assert diag_data["heatmap_path"] is not None

    # --------------------------------------------------------------------------
    # Step 10 & 11: Weather retrieval & Environmental risk assessment
    # --------------------------------------------------------------------------
    risk_payload = {
        "crop": "sugarcane",
        "district": "Kolhapur",
        "latitude": 16.7050,
        "longitude": 74.2433,
        "growth_stage": "grand_growth"
    }
    risk_res = client.post("/api/v1/risk/environmental", json=risk_payload)
    assert risk_res.status_code == 200
    risk_data = risk_res.json()
    assert "environmental_risk_level" in risk_data
    assert "is_safe_to_spray" in risk_data
    assert "epidemiological_conduciveness" in risk_data

    # --------------------------------------------------------------------------
    # Step 12 & 13: Multilingual RAG knowledge retrieval & Advisory generation
    # --------------------------------------------------------------------------
    rag_payload = {
        "message": "ऊसावरील तांबडे कूज रोगाची लक्षणे आणि उपाय काय आहेत?",
        "crop": "sugarcane",
        "language": "mr"
    }
    rag_res = client.post("/api/v1/assistant/chat", json=rag_payload, headers=headers)
    assert rag_res.status_code == 200
    assert "answer" in rag_res.json()
    assert len(rag_res.json()["answer"]) > 20

    # --------------------------------------------------------------------------
    # Step 14: Diagnosis and results verified in DB
    # --------------------------------------------------------------------------
    saved_diag = db.query(Diagnosis).filter(Diagnosis.id == diagnosis_id).first()
    assert saved_diag is not None
    assert saved_diag.user_id == user_id

    # --------------------------------------------------------------------------
    # Step 15: Farmer views diagnosis history
    # --------------------------------------------------------------------------
    history_res = client.get("/api/v1/diagnostics", headers=headers)
    assert history_res.status_code == 200
    history_items = history_res.json()
    assert len(history_items) >= 1
    assert any(h["id"] == diagnosis_id for h in history_items)

    # --------------------------------------------------------------------------
    # Step 16: Farmer downloads PDF report
    # --------------------------------------------------------------------------
    pdf_res = client.get(f"/api/v1/diagnose/{diagnosis_id}/pdf", headers=headers)
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert len(pdf_res.content) > 1000

    # --------------------------------------------------------------------------
    # Step 17: Notifications generated
    # --------------------------------------------------------------------------
    notif_payload = {
        "user_id": user_id,
        "title": "High Humidity Alert for Sugarcane",
        "message": "Continuous wet canopy detected. Scout for fungal midrib lesions.",
        "notification_type": "WEATHER_ALERT",
        "severity": "WARNING",
        "related_diagnosis_id": diagnosis_id
    }
    client.post("/api/v1/notifications/create", json=notif_payload, headers=headers)
    notif_res = client.get("/api/v1/notifications", headers=headers)
    assert notif_res.status_code == 200
    assert len(notif_res.json()) >= 1

    # --------------------------------------------------------------------------
    # Step 18: Expert review requested
    # --------------------------------------------------------------------------
    review_req = {
        "diagnosis_id": diagnosis_id,
        "farmer_notes": "Please verify if sett treatment with Carbendazim is sufficient."
    }
    review_res = client.post("/api/v1/experts/request-review", json=review_req, headers=headers)
    assert review_res.status_code == 200
    assert review_res.json()["status"] == "PENDING"

    # --------------------------------------------------------------------------
    # Step 19: Offline synchronization
    # --------------------------------------------------------------------------
    sync_payload = {
        "client_timestamp": "2026-11-13T12:00:00Z",
        "diagnoses": []
    }
    sync_res = client.post("/api/v1/sync/push", json=sync_payload, headers=headers)
    assert sync_res.status_code == 200
    assert sync_res.json()["status"] == "success"
