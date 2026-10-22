import io
from pathlib import Path
from typing import List, Optional
from PIL import Image
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.dependencies import get_current_active_user
from app.models.user import User
from app.models.farm import Farm
from app.models.crop_cycle import CropCycle
from app.models.diagnosis import Diagnosis, DiagnosisStatus
from app.schemas.diagnosis import (
    DiagnosisDetailResponse,
    DiagnosisSummaryResponse,
    PredictResponse,
)
from app.services.storage import storage_service
from app.services.ai_service import ai_service
from app.services.model_service import (
    model_service,
    ModelNotLoadedError,
    UnsupportedCropError,
    InferenceError,
)

router = APIRouter()


@router.post(
    "/diagnose/predict",
    response_model=PredictResponse,
    status_code=status.HTTP_200_OK,
    summary="Direct ML model inference endpoint for crop disease diagnosis",
)
@router.post(
    "/diagnostics/predict",
    response_model=PredictResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def predict_crop_disease(
    file: UploadFile = File(..., description="Crop leaf photograph (JPEG, PNG, WEBP)"),
    crop: str = Form("sugarcane", description="Target crop (default: sugarcane)"),
    generate_gradcam: bool = Form(False, description="Generate Grad-CAM activation heatmap"),
    save_heatmap: bool = Form(True, description="Persist generated heatmap to disk"),
):
    """Direct model-serving endpoint. Validates file integrity, evaluates PyTorch

    model inference, and optionally generates Grad-CAM visual lesion heatmaps.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename cannot be empty.",
        )

    # 1. Validate file extension
    ext = Path(file.filename).suffix.lower()
    if ext not in settings.ALLOWED_IMAGE_EXTENSIONS:
        allowed = ", ".join(settings.ALLOWED_IMAGE_EXTENSIONS)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension '{ext}'. Allowed extensions are: {allowed}",
        )

    # 2. Validate header & magic bytes
    header = await file.read(16)
    if len(header) < 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty or corrupted file uploaded.",
        )

    is_valid_header = False
    if header.startswith(b"\xff\xd8\xff") and ext in [".jpg", ".jpeg"]:
        is_valid_header = True
    elif header.startswith(b"\x89PNG\r\n\x1a\n") and ext == ".png":
        is_valid_header = True
    elif header.startswith(b"RIFF") and len(header) >= 12 and header[8:12] == b"WEBP" and ext == ".webp":
        is_valid_header = True

    if not is_valid_header:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File content header does not match a valid image format (JPEG, PNG, WEBP).",
        )

    # 3. Read complete content and check file size limit
    rest_content = await file.read()
    full_content = header + rest_content
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(full_content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB.",
        )

    # 4. Validate decodability with PIL
    try:
        with Image.open(io.BytesIO(full_content)) as img:
            img.verify()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or corrupted image content.",
        )

    # 5. Run inference through singleton ModelServingService
    try:
        result = model_service.predict(
            image=full_content,
            crop=crop,
            generate_gradcam=generate_gradcam,
            save_heatmap=save_heatmap,
        )
        return result
    except UnsupportedCropError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except ModelNotLoadedError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Model serving error: {e}",
        )
    except InferenceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference failure: {e}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected model execution failure: {e}",
        )



def _get_user_crop(crop_id: int, user_id: int, db: Session) -> CropCycle:
    crop = (
        db.query(CropCycle)
        .join(Farm, CropCycle.farm_id == Farm.id)
        .filter(CropCycle.id == crop_id)
        .first()
    )
    if not crop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Crop cycle not found.",
        )
    if crop.farm.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this crop cycle.",
        )
    return crop


def _get_user_diagnosis(diagnosis_id: int, user_id: int, db: Session) -> Diagnosis:
    diagnosis = db.query(Diagnosis).filter(Diagnosis.id == diagnosis_id).first()
    if not diagnosis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Diagnostic record not found.",
        )
    if diagnosis.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this diagnostic record.",
        )
    return diagnosis


@router.post(
    "/crops/{crop_id}/diagnoses",
    response_model=DiagnosisDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit crop leaf image for AI diagnosis",
)
async def create_crop_diagnosis(
    crop_id: int,
    file: UploadFile = File(..., description="Foliar leaf image (JPEG, PNG, WEBP)"),
    notes: Optional[str] = Form(None, description="Farmer notes or field observations"),
    temperature: Optional[float] = Form(None, description="Ambient temperature (°C)"),
    humidity: Optional[float] = Form(None, description="Relative humidity (%)"),
    soil_moisture: Optional[float] = Form(None, description="Soil moisture level (%)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Submits a crop leaf photograph, validates image integrity, executes

    AI pathological inference, and records the localized advisory.
    """
    crop = _get_user_crop(crop_id, current_user.id, db)

    # Validate and store media file
    storage_path, original_filename, image_hash = await storage_service.save_diagnostic_image(file)

    # Perform AI disease & pest pathology inference
    try:
        inference = await ai_service.analyze_crop_image(
            image_path=storage_path,
            crop_name=crop.crop,
            temperature=temperature,
            humidity=humidity,
            soil_moisture=soil_moisture,
        )

        diagnosis = Diagnosis(
            user_id=current_user.id,
            crop_cycle_id=crop.id,
            image_path=storage_path,
            image_filename=original_filename,
            image_hash=image_hash,
            crop_name=crop.crop,
            disease_name_en=inference.disease_name_en,
            disease_name_mr=inference.disease_name_mr,
            pathogen_type=inference.pathogen_type,
            confidence=inference.confidence,
            severity=inference.severity,
            affected_area_percentage=inference.affected_area_percentage,
            symptoms_en=inference.symptoms_en,
            symptoms_mr=inference.symptoms_mr,
            recommendations_en=inference.recommendations_en,
            recommendations_mr=inference.recommendations_mr,
            temperature=temperature,
            humidity=humidity,
            soil_moisture=soil_moisture,
            status=DiagnosisStatus.COMPLETED,
            notes=notes,
        )
    except Exception:
        # Mark as failed if inference encounters an unrecoverable failure
        diagnosis = Diagnosis(
            user_id=current_user.id,
            crop_cycle_id=crop.id,
            image_path=storage_path,
            image_filename=original_filename,
            image_hash=image_hash,
            crop_name=crop.crop,
            status=DiagnosisStatus.FAILED,
            notes=notes,
        )

    db.add(diagnosis)
    db.commit()
    db.refresh(diagnosis)
    return diagnosis


@router.get(
    "/crops/{crop_id}/diagnoses",
    response_model=List[DiagnosisSummaryResponse],
    summary="List all diagnostic records for a specific crop cycle",
)
def list_crop_diagnoses(
    crop_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Retrieve historical diagnostics for a given crop cycle."""
    _get_user_crop(crop_id, current_user.id, db)
    return (
        db.query(Diagnosis)
        .filter(Diagnosis.crop_cycle_id == crop_id)
        .order_by(Diagnosis.created_at.desc())
        .all()
    )


@router.get(
    "/diagnostics",
    response_model=List[DiagnosisSummaryResponse],
    summary="List all diagnostic records for authenticated farmer",
)
def list_farmer_diagnostics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Retrieve all diagnostic records submitted by the authenticated farmer."""
    return (
        db.query(Diagnosis)
        .filter(Diagnosis.user_id == current_user.id)
        .order_by(Diagnosis.created_at.desc())
        .all()
    )


@router.get(
    "/diagnostics/{diagnosis_id}",
    response_model=DiagnosisDetailResponse,
    summary="Get details of a specific diagnosis",
)
def get_diagnosis_detail(
    diagnosis_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Fetch complete diagnostic report including bilingual symptoms, severity,

    and treatment recommendations.
    """
    return _get_user_diagnosis(diagnosis_id, current_user.id, db)


@router.delete(
    "/diagnostics/{diagnosis_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a diagnostic record and its uploaded file",
)
def delete_diagnosis(
    diagnosis_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Delete a diagnostic record and unlink its stored image asset."""
    diagnosis = _get_user_diagnosis(diagnosis_id, current_user.id, db)
    file_path = diagnosis.image_path

    db.delete(diagnosis)
    db.commit()

    # Clean up physical file
    storage_service.remove_file(file_path)
    return None
