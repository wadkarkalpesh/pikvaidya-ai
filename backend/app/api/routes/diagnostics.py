import io
import logging
from pathlib import Path
from typing import List, Optional
from PIL import Image
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

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
from app.services.diagnostic_service import diagnostic_service

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
    model inference, applies confidence safety evaluation, and optionally generates
    Grad-CAM visual lesion heatmaps. Unauthenticated, ephemeral, and does not touch
    the farmer database.
    """
    try:
        result = await diagnostic_service.run_standalone_prediction(
            file=file,
            crop=crop,
            generate_gradcam=generate_gradcam,
            save_heatmap=save_heatmap,
        )
        return result
    except HTTPException:
        raise
    except UnsupportedCropError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except ModelNotLoadedError as e:
        logger.error(f"Model serving error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model serving error: Diagnostic model is currently unavailable.",
        )
    except InferenceError as e:
        logger.error(f"Inference failure: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Inference failure: Failed to execute model forward pass.",
        )
    except Exception as e:
        logger.error(f"Unexpected model execution failure: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected internal error occurred during model execution.",
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
    generate_gradcam: bool = Form(False, description="Generate Grad-CAM activation heatmap"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Submits a crop leaf photograph for an authenticated farmer's crop cycle.
    Validates crop ownership and image integrity, verifies genuine model availability,
    executes PyTorch inference with confidence safety gating, optionally generates Grad-CAM,
    and records the persistent diagnosis in the database.
    """
    try:
        diagnosis = await diagnostic_service.run_authenticated_crop_diagnosis(
            crop_id=crop_id,
            user_id=current_user.id,
            file=file,
            notes=notes,
            temperature=temperature,
            humidity=humidity,
            soil_moisture=soil_moisture,
            generate_gradcam=generate_gradcam,
            db=db,
        )
        return diagnosis
    except HTTPException:
        raise
    except UnsupportedCropError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except ModelNotLoadedError as e:
        logger.error(f"Model serving error during authenticated diagnosis: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model serving error: Diagnostic model is currently unavailable.",
        )
    except InferenceError as e:
        logger.error(f"Inference failure during authenticated diagnosis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Inference failure: Failed to execute model forward pass.",
        )



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
