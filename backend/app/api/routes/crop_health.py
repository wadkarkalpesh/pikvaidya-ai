"""
PikVaidya AI — Unified Multi-Crop Health Prediction API
======================================================
Exposes common, high-throughput REST endpoints that integrate all available
crop models (sugarcane, tomato, onion) with automated crop identification,
14-day microclimate telemetry, physiological stress evaluation,
and calibrated multimodal evidence fusion.

Endpoint:
POST /api/crop-health/predict (also available as POST /api/v1/crop-health/predict)
"""

import io
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List
from PIL import Image
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.rate_limit import inference_rate_limiter
from app.services.model_service import (
    model_service,
    UnsupportedCropError,
    ModelNotLoadedError,
    InferenceError,
)
from app.services.crop_detector import crop_detector
from app.services.segmentation_service import segmentation_service
from app.services.weather.feature_engineer import weather_feature_engineer
from app.services.weather.crop_health_risk import weather_crop_health_risk_engine
from app.services.multimodal_fusion import multimodal_fusion_engine
from app.services.weather.locations import resolve_location, MAHARASHTRA_DISTRICTS
from app.schemas.multimodal import (
    AgriculturalContextInput,
    CropGrowthStage,
    SoilType,
    IrrigationMethod,
    ImageDiagnosisSummary,
    WeatherRiskAssessmentSummary,
    MultimodalPredictResponse,
    UnifiedCropHealthPredictResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Unified Multi-Crop Health Prediction"])

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAGIC_HEADERS = [
    b"\xff\xd8\xff",  # JPEG
    b"\x89PNG\r\n\x1a\n",  # PNG
    b"RIFF",  # WEBP
]


def _validate_image_file(file: UploadFile, content: bytes):
    """Enforces strict MIME, file extension, and magic header byte validation."""
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty (0 bytes).",
        )

    filename = file.filename or ""
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{suffix}'. Allowed formats: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}",
        )

    is_valid_magic = any(content.startswith(magic) for magic in MAGIC_HEADERS)
    if not is_valid_magic:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File content header does not match a valid image type (JPEG, PNG, WEBP).",
        )


@router.post(
    "/predict",
    response_model=UnifiedCropHealthPredictResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(inference_rate_limiter.check)],
    summary="Unified Multi-Crop Health Prediction Endpoint",
    description=(
        "Common prediction interface integrating Sugarcane, Tomato, and Onion models. "
        "Accepts a crop image, automatically detects or receives the crop type, routes the image "
        "to the specialized model, computes 14-day microclimate telemetry, and produces a tri-partite output: "
        "(1) Image-based disease diagnosis, (2) Environmental crop-health risk, and (3) Combined assessment."
    ),
)
@router.post(
    "/crop-health/predict",
    response_model=UnifiedCropHealthPredictResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(inference_rate_limiter.check)],
    include_in_schema=False,
)
async def predict_crop_health(
    file: Optional[UploadFile] = File(None, description="Crop leaf photograph (JPEG, PNG, WEBP)"),
    image: Optional[UploadFile] = File(None, description="Alias for file upload"),
    crop_type: Optional[str] = Form(None, description="Target crop: sugarcane, tomato, onion (or 'auto' for automatic detection)"),
    crop: Optional[str] = Form(None, description="Alias for crop_type"),
    crop_name: Optional[str] = Form(None, description="Alias for crop_type"),
    latitude: Optional[float] = Form(None, description="Farm latitude coordinate"),
    longitude: Optional[float] = Form(None, description="Farm longitude coordinate"),
    district: Optional[str] = Form(None, description="Maharashtra district name (e.g. Pune, Nashik, Kolhapur)"),
    crop_variety: Optional[str] = Form(None, description="Cultivar or variety (e.g. Co 86032, Abhinav, Bhima Kiran)"),
    growth_stage: Optional[str] = Form("unknown", description="Developmental growth stage"),
    soil_type: Optional[str] = Form("unknown", description="Soil texture class"),
    irrigation_method: Optional[str] = Form("unknown", description="Irrigation method: drip, sprinkler, flood, rainfed"),
    strategy: Optional[str] = Form("CALIBRATED_BAYESIAN", description="Fusion method: CALIBRATED_BAYESIAN or RULE_BASED_GATE"),
    generate_gradcam: bool = Form(True, description="Generate Grad-CAM activation heatmap overlay"),
    captured_at: Optional[str] = Form(None, description="Original offline capture ISO timestamp if synced from queue"),
) -> UnifiedCropHealthPredictResponse:
    """
    Executes unified multi-crop health prediction workflow:
    1. Validates and preprocesses crop foliar image.
    2. Identifies or receives crop species (auto-routing).
    3. Executes calibrated disease classification + Grad-CAM saliency.
    4. Fetches 14-day historical weather telemetry and evaluates physiological stress.
    5. Evaluates crop-specific epidemiological pathogen models.
    6. Combines outputs into a tri-partite assessment with actionable recommendations.
    """
    upload_file = file or image
    if upload_file is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No image file provided. Please attach a valid leaf image.",
        )

    # 1. Read & Validate Uploaded Image
    try:
        content = await upload_file.read()
        _validate_image_file(upload_file, content)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to read image upload: {e}")

    # 2. Foliage Quality Check (Out-of-Distribution Defense)
    try:
        pil_img = Image.open(io.BytesIO(content)).convert("RGB")
        is_valid_foliage, cov_ratio, foliar_msg = segmentation_service.validate_foliar_quality(pil_img)
        if not is_valid_foliage:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid foliage sample: {foliar_msg} (Foliar coverage: {cov_ratio*100:.1f}%)",
            )
    except HTTPException:
        raise
    except Exception as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Image processing error: {err}")

    # 3. Resolve Target Crop (Auto-routing or Explicit Specification)
    target_crop = (crop_type or crop or crop_name or "auto").strip().lower()
    detection_method = "explicit_user_selection"
    detection_conf = None

    if target_crop in ("auto", "unknown", "detect", "", "none"):
        target_crop, detection_conf, _ = crop_detector.identify_crop(content)
        detection_method = "auto_detected_classifier"
        logger.info(f"Unified router identified crop as '{target_crop}' (Confidence: {detection_conf:.4f})")

    if target_crop not in model_service.CROP_REGISTRY:
        supported_crops = ", ".join(model_service.CROP_REGISTRY.keys())
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported crop: '{target_crop}'. Supported crops: {supported_crops}",
        )

    # 4. Vision Forward Pass & Grad-CAM
    try:
        vis_res = model_service.predict(
            image=content,
            crop=target_crop,
            generate_gradcam=generate_gradcam,
            save_heatmap=True,
        )
        emp_severity, emp_area = segmentation_service.estimate_foliar_severity(
            image=pil_img,
            predicted_class=vis_res["predicted_class"],
            crop=target_crop,
        )
    except UnsupportedCropError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except (ModelNotLoadedError, InferenceError) as e:
        logger.error(f"Vision inference failure: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Inference forward pass failed.")

    image_summary = ImageDiagnosisSummary(
        crop=target_crop,
        predicted_class=vis_res["predicted_class"],
        confidence=vis_res["confidence"],
        class_scores=vis_res["class_scores"],
        model_version=vis_res["model_version"],
        explanation_status=vis_res["explanation_status"],
        heatmap_path=vis_res.get("heatmap_path"),
        foliar_severity=emp_severity.value,
        affected_area_percentage=round(emp_area, 2),
    )

    # 5. Resolve Agricultural Context & Geographical Location
    lat, lon, loc_name = resolve_location(district, latitude, longitude)
    context_obj = AgriculturalContextInput(
        crop_name=target_crop,
        crop_variety=crop_variety,
        growth_stage=CropGrowthStage(growth_stage.lower()) if growth_stage and growth_stage.lower() in CropGrowthStage._value2member_map_ else CropGrowthStage.UNKNOWN,
        soil_type=SoilType(soil_type.lower()) if soil_type and soil_type.lower() in SoilType._value2member_map_ else SoilType.UNKNOWN,
        irrigation_method=IrrigationMethod(irrigation_method.lower()) if irrigation_method and irrigation_method.lower() in IrrigationMethod._value2member_map_ else IrrigationMethod.UNKNOWN,
        latitude=lat,
        longitude=lon,
        district=loc_name,
    )

    # 6. Retrieve Historical Multi-Window Microclimate Profile
    try:
        hist_profile = await weather_feature_engineer.get_historical_profile(
            latitude=lat,
            longitude=lon,
            crop_name=target_crop,
            location_name=loc_name,
        )
    except Exception as w_err:
        logger.warning(f"Feature engineering warning ({w_err}); synthesizing regional baseline profile.")
        hist_profile = weather_feature_engineer._build_synthetic_regional_profile(lat, lon, loc_name, target_crop)

    # 7. Evaluate Environmental Stress & Crop-Specific Disease Conduciveness
    weather_risk = weather_crop_health_risk_engine.evaluate_weather_risk(
        crop_name=target_crop,
        profile=hist_profile,
        context=context_obj,
    )

    # 8. Execute Calibrated Multimodal Fusion
    multimodal_res = multimodal_fusion_engine.fuse(
        image_prediction=image_summary,
        weather_risk=weather_risk,
        context=context_obj,
        strategy=strategy or "CALIBRATED_BAYESIAN",
    )

    now_iso = datetime.now(timezone.utc).isoformat()

    return UnifiedCropHealthPredictResponse(
        crop_type=target_crop,
        crop_detection_method=detection_method,
        crop_detection_confidence=detection_conf,
        predicted_disease=vis_res["predicted_class"],
        disease_name_multilingual=multimodal_res.multimodal_assessment.display_name,
        model_confidence=vis_res["confidence"],
        weather_summary=weather_risk.weather_summary,
        environmental_risk=weather_risk.model_dump(),
        combined_assessment=multimodal_res.multimodal_assessment.model_dump(),
        gradcam_image_url=vis_res.get("heatmap_path"),
        advisory_recommendations=multimodal_res.recommendations,
        data_source=f"PikVaidya Multimodal v2.2.0 | {hist_profile.data_source}",
        timestamp=now_iso,
        image_prediction=image_summary,
        weather_risk=weather_risk,
        multimodal_assessment=multimodal_res.multimodal_assessment,
        explainability=multimodal_res.explainability,
        agricultural_context=context_obj,
        statutory_disclaimer=multimodal_res.statutory_disclaimer,
        captured_at=captured_at,
        is_offline_synced=bool(captured_at),
    )

