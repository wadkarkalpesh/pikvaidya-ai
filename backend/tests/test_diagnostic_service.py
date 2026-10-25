import io
import pytest
from PIL import Image
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.crop_cycle import CropCycle
from app.models.diagnosis import DiagnosisStatus, DiagnosisSeverity
from app.services.diagnostic_service import (
    diagnostic_service,
    UnsupportedCropError,
    STATUTORY_DISCLAIMER_EN,
    EXPERT_REVIEW_NOTICE_EN,
)


def test_service_check_crop_support_success():
    assert diagnostic_service.check_crop_support("sugarcane") == "sugarcane"
    assert diagnostic_service.check_crop_support("Sugarcane") == "sugarcane"
    assert diagnostic_service.check_crop_support("co 86032 sugarcane") == "sugarcane"


def test_service_check_crop_support_unsupported():
    with pytest.raises(UnsupportedCropError) as exc_info:
        diagnostic_service.check_crop_support("Cotton")
    assert "unavailable for crop 'Cotton'" in str(exc_info.value)

    with pytest.raises(UnsupportedCropError):
        diagnostic_service.check_crop_support("Tomato")

    with pytest.raises(UnsupportedCropError):
        diagnostic_service.check_crop_support("Soybean")


def test_service_evaluate_high_confidence_healthy():
    scores = {"Healthy": 0.95, "Mosaic": 0.02, "RedRot": 0.01, "Rust": 0.01, "Yellow": 0.01}
    eval_result = diagnostic_service.evaluate_safety_and_advisory(
        crop="sugarcane",
        predicted_class="Healthy",
        confidence=0.95,
        class_scores=scores,
    )
    assert eval_result.advisory_status == "HEALTHY"
    assert eval_result.severity == DiagnosisSeverity.HEALTHY
    assert eval_result.affected_area_percentage == 0.0
    assert "No chemical fungicides" in eval_result.recommendations_en


def test_service_evaluate_high_confidence_disease():
    scores = {"RedRot": 0.88, "Rust": 0.05, "Mosaic": 0.03, "Yellow": 0.02, "Healthy": 0.02}
    eval_result = diagnostic_service.evaluate_safety_and_advisory(
        crop="sugarcane",
        predicted_class="RedRot",
        confidence=0.88,
        class_scores=scores,
    )
    assert eval_result.advisory_status == "HIGH_CONFIDENCE"
    assert eval_result.severity == DiagnosisSeverity.UNAVAILABLE
    assert eval_result.affected_area_percentage is None
    assert EXPERT_REVIEW_NOTICE_EN in eval_result.recommendations_en
    assert STATUTORY_DISCLAIMER_EN in eval_result.recommendations_en
    assert "Carbendazim" in eval_result.recommendations_en


def test_service_evaluate_moderate_confidence_suppression():
    scores = {"Rust": 0.65, "RedRot": 0.15, "Mosaic": 0.10, "Yellow": 0.05, "Healthy": 0.05}
    eval_result = diagnostic_service.evaluate_safety_and_advisory(
        crop="sugarcane",
        predicted_class="Rust",
        confidence=0.65,
        class_scores=scores,
    )
    assert eval_result.advisory_status == "LOW_CONFIDENCE_WARNING"
    assert eval_result.severity == DiagnosisSeverity.UNAVAILABLE
    assert eval_result.affected_area_percentage is None
    # Verify chemical prescriptions are suppressed
    assert "SUPPRESSED" in eval_result.recommendations_en
    assert "Mancozeb" not in eval_result.recommendations_en
    assert "Propiconazole" not in eval_result.recommendations_en


def test_service_evaluate_low_confidence_inconclusive():
    scores = {"Yellow": 0.42, "Mosaic": 0.30, "Rust": 0.15, "RedRot": 0.08, "Healthy": 0.05}
    eval_result = diagnostic_service.evaluate_safety_and_advisory(
        crop="sugarcane",
        predicted_class="Yellow",
        confidence=0.42,
        class_scores=scores,
    )
    assert eval_result.advisory_status == "UNCERTAIN_PREDICTION"
    assert eval_result.disease_name_en == "Uncertain Foliar Symptoms"
    assert eval_result.severity == DiagnosisSeverity.UNAVAILABLE
    assert eval_result.affected_area_percentage is None
    assert "WITHHELD" in eval_result.recommendations_en
    assert STATUTORY_DISCLAIMER_EN in eval_result.recommendations_en


@pytest.mark.anyio
async def test_service_standalone_prediction_pipeline(sample_jpeg_bytes: bytes):
    upload_file = UploadFile(
        file=io.BytesIO(sample_jpeg_bytes),
        filename="sugarcane_test.jpg",
        headers={"content-type": "image/jpeg"},
    )
    res = await diagnostic_service.run_standalone_prediction(
        file=upload_file,
        crop="sugarcane",
        generate_gradcam=False,
    )
    assert res.crop == "sugarcane"
    assert res.predicted_class in ["Healthy", "Mosaic", "RedRot", "Rust", "Yellow"]
    assert 0.0 <= res.confidence <= 1.0
    assert res.advisory_status is not None
    assert res.details is not None


@pytest.mark.anyio
async def test_service_authenticated_diagnosis_persistence(
    db: Session,
    test_user: User,
    test_crop: CropCycle,
    sample_jpeg_bytes: bytes,
):
    upload_file = UploadFile(
        file=io.BytesIO(sample_jpeg_bytes),
        filename="sugarcane_field.jpg",
        headers={"content-type": "image/jpeg"},
    )
    diagnosis = await diagnostic_service.run_authenticated_crop_diagnosis(
        crop_id=test_crop.id,
        user_id=test_user.id,
        file=upload_file,
        notes="Field test diagnosis",
        temperature=31.0,
        humidity=78.0,
        soil_moisture=55.0,
        generate_gradcam=False,
        db=db,
    )
    assert diagnosis.id is not None
    assert diagnosis.user_id == test_user.id
    assert diagnosis.crop_cycle_id == test_crop.id
    assert diagnosis.status == DiagnosisStatus.COMPLETED
    assert diagnosis.crop_name == "Sugarcane"
    assert diagnosis.confidence is not None
    assert diagnosis.advisory_status is not None
    assert diagnosis.recommendations_en is not None
    assert diagnosis.recommendations_mr is not None
    # Clean up physical file
    from app.services.storage import storage_service
    storage_service.remove_file(diagnosis.image_path)
