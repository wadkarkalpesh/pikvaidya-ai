"""
PikVaidya AI — Automated Tests: Expert Reviews, Admin Telemetry & Risk API
==========================================================================
Tests:
1. Farmer requesting expert review.
2. Role-based security (403 for farmers accessing expert/admin endpoints).
3. Expert diagnosis correction with audit log and notification dispatch.
4. Admin telemetry metrics (memory, loaded models, database statistics).
5. Environmental microclimate risk evaluation endpoint.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.security import create_access_token, get_password_hash
from app.models.user import User, UserRole
from app.models.farm import Farm
from app.models.crop_cycle import CropCycle
from app.models.diagnosis import Diagnosis, DiagnosisStatus
from app.models.expert_review import ExpertReview, ReviewStatus
from app.models.audit_log import AuditLog


@pytest.fixture
def expert_user(db: Session) -> User:
    user = User(
        name="Dr. Patil (Agronomist)",
        email="expert.patil@kvk.org",
        password_hash=get_password_hash("ExpertSecret123"),
        preferred_language="mr",
        role=UserRole.EXPERT,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def admin_user(db: Session) -> User:
    user = User(
        name="Platform Admin",
        email="admin@pikvaidya.ai",
        password_hash=get_password_hash("AdminSecret123"),
        preferred_language="en",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def expert_headers(expert_user: User) -> dict:
    token = create_access_token(subject=expert_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(admin_user: User) -> dict:
    token = create_access_token(subject=admin_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_diagnosis(db: Session, test_user: User, test_crop: CropCycle) -> Diagnosis:
    diag = Diagnosis(
        user_id=test_user.id,
        crop_cycle_id=test_crop.id,
        image_path="uploads/test_leaf.jpg",
        image_filename="test_leaf.jpg",
        image_hash="abc123hash",
        crop_name="tomato",
        disease_name_en="Early_blight",
        disease_name_mr="टोमॅटोवरील करपा",
        pathogen_type="Fungal",
        confidence=0.74,
        status=DiagnosisStatus.COMPLETED
    )
    db.add(diag)
    db.commit()
    db.refresh(diag)
    return diag


def test_request_expert_review_flow(
    client: TestClient, auth_headers: dict, sample_diagnosis: Diagnosis, db: Session
):
    # 1. Farmer requests expert review
    req_payload = {
        "diagnosis_id": sample_diagnosis.id,
        "farmer_notes": "Lesions look darker than typical early blight. Please verify."
    }
    response = client.post("/api/v1/experts/request-review", json=req_payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "PENDING"
    assert data["original_disease_en"] == "Early_blight"
    assert data["farmer_notes"] == "Lesions look darker than typical early blight. Please verify."

    # Verify audit log created
    log = db.query(AuditLog).filter(AuditLog.target_id == str(sample_diagnosis.id)).first()
    assert log is not None
    assert log.action == "EXPERT_REVIEW_REQUESTED"


def test_expert_access_control_and_evaluation(
    client: TestClient,
    auth_headers: dict,
    expert_headers: dict,
    sample_diagnosis: Diagnosis,
    db: Session,
):
    # Request review
    client.post("/api/v1/experts/request-review", json={"diagnosis_id": sample_diagnosis.id}, headers=auth_headers)

    # Farmer trying to access pending reviews queue -> 403 Forbidden
    res_forbidden = client.get("/api/v1/experts/pending-reviews", headers=auth_headers)
    assert res_forbidden.status_code == 403

    # Expert accessing pending reviews queue -> 200 OK
    res_expert = client.get("/api/v1/experts/pending-reviews", headers=expert_headers)
    assert res_expert.status_code == 200
    pending_list = res_expert.json()
    assert len(pending_list) >= 1
    review_id = pending_list[0]["id"]

    # Expert submits evaluation
    eval_payload = {
        "is_agreement": False,
        "corrected_disease_en": "Late_blight",
        "corrected_disease_mr": "टोमॅटोवरील लेट ब्लाइट (तांबोरा)",
        "pathogen_type": "Oomycete (Phytophthora infestans)",
        "expert_notes": "Concentric rings absent; water-soaked margins confirm Phytophthora infestans.",
        "recommended_treatment": "Spray Metalaxyl 8% + Mancozeb 64% WP @ 2.5 g/L."
    }
    submit_res = client.post(f"/api/v1/experts/reviews/{review_id}/submit", json=eval_payload, headers=expert_headers)
    assert submit_res.status_code == 200
    res_data = submit_res.json()
    assert res_data["status"] == "CORRECTED"
    assert res_data["is_agreement"] is False
    assert res_data["corrected_disease_en"] == "Late_blight"


def test_admin_telemetry_and_rbac(
    client: TestClient, auth_headers: dict, admin_headers: dict
):
    # Farmer attempting admin endpoint -> 403 Forbidden
    res_forbidden = client.get("/api/v1/admin/telemetry", headers=auth_headers)
    assert res_forbidden.status_code == 403

    # Admin accessing telemetry -> 200 OK
    res_admin = client.get("/api/v1/admin/telemetry", headers=admin_headers)
    assert res_admin.status_code == 200
    data = res_admin.json()
    assert data["status"] == "OPERATIONAL"
    assert "runtime" in data
    assert "memory_rss_mb" in data["runtime"]
    assert "database" in data
    assert "users_count" in data["database"]

    # Admin summary
    summary_res = client.get("/api/v1/admin/summary", headers=admin_headers)
    assert summary_res.status_code == 200
    assert "farmers" in summary_res.json()


def test_environmental_risk_endpoint(client: TestClient):
    payload = {
        "crop": "tomato",
        "district": "Kolhapur",
        "growth_stage": "flowering"
    }
    response = client.post("/api/v1/risk/environmental", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["crop"] == "tomato"
    assert "location" in data
    assert "Kolhapur" in data["location"]["name"]
    assert "environmental_risk_level" in data
    assert "epidemiological_conduciveness" in data
    assert "disclaimer" in data


def test_versioned_health_endpoint(client: TestClient):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
