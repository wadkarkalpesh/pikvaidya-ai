"""
PikVaidya AI — Multimodal Crop-Health Prediction API Routes
===========================================================
Exposes REST endpoints that fuse computer vision foliar diagnosis with
multi-window environmental microclimate and agronomic context.

Endpoints:
1. POST /api/v1/multimodal/predict       - Full multimodal image + weather diagnostic prediction
2. POST /api/v1/multimodal/weather-risk  - Standalone environmental stress & disease conduciveness evaluation
3. GET  /api/v1/multimodal/crops         - Supported crops, growth stages, soil types & models
"""

import io
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from PIL import Image
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.config import settings
from app.core.rate_limit import inference_rate_limiter
from app.services.model_service import (
    model_service,
    UnsupportedCropError,
    ModelNotLoadedError,
    InferenceError,
)
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
    WeatherRiskOnlyResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/multimodal", tags=["Multimodal Crop-Health Prediction Engine"])

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

    # Check extension
    filename = file.filename or ""
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{suffix}'. Allowed formats: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}",
        )

    # Check magic header bytes
    is_valid_magic = any(content.startswith(magic) for magic in MAGIC_HEADERS)
    if not is_valid_magic:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File content header does not match a valid image type (JPEG, PNG, WEBP).",
        )


@router.post(
    "/predict",
    response_model=MultimodalPredictResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(inference_rate_limiter.check)],
    summary="Execute Multimodal Crop-Health Diagnostic Forward Pass",
    description=(
        "Combines convolutional neural network foliar lesion detection with 14-day historical "
        "microclimate telemetry, physiological stress indicators, and epidemiological pathogen models. "
        "Strictly guarantees that weather conditions cannot override high-confidence visual evidence."
    ),
)
async def predict_multimodal_crop_health(
    file: UploadFile = File(..., description="Crop leaf photograph (JPEG, PNG, WEBP)"),
    crop: str = Form("sugarcane", description="Target crop: sugarcane, tomato, onion"),
    latitude: Optional[float] = Form(None, description="Farm latitude coordinate"),
    longitude: Optional[float] = Form(None, description="Farm longitude coordinate"),
    district: Optional[str] = Form(None, description="Maharashtra district name (e.g. Pune, Nashik, Kolhapur)"),
    crop_variety: Optional[str] = Form(None, description="Cultivar or variety (e.g. Co 86032, Abhinav)"),
    growth_stage: Optional[str] = Form("unknown", description="Developmental stage"),
    soil_type: Optional[str] = Form("unknown", description="Soil texture type"),
    irrigation_method: Optional[str] = Form("unknown", description="Irrigation method: drip, sprinkler, flood, rainfed"),
    strategy: Optional[str] = Form("CALIBRATED_BAYESIAN", description="Fusion method: CALIBRATED_BAYESIAN or RULE_BASED_GATE"),
    generate_gradcam: bool = Form(True, description="Generate Grad-CAM activation heatmap overlay"),
) -> MultimodalPredictResponse:
    """
    Executes full multimodal pipeline:
    1. Validates and preprocesses crop foliage image.
    2. Runs deep learning image prediction with Grad-CAM explainability.
    3. Fetches 14-day historical weather telemetry and derives environmental stress indices.
    4. Computes scientific disease-conduciveness scores.
    5. Fuses outputs via Calibrated Bayesian Evidence Fusion.
    """
    normalized_crop = crop.strip().lower()
    if normalized_crop not in model_service.CROP_REGISTRY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported crop: '{crop}'. Supported crops: {', '.join(model_service.CROP_REGISTRY.keys())}",
        )

    # 1. Read & Validate Uploaded Image
    try:
        content = await file.read()
        _validate_image_file(file, content)
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

    # 3. Vision Forward Pass & Grad-CAM
    try:
        vis_res = model_service.predict(
            image=content,
            crop=normalized_crop,
            generate_gradcam=generate_gradcam,
            save_heatmap=True,
        )
        emp_severity, emp_area = segmentation_service.estimate_foliar_severity(
            image=pil_img,
            predicted_class=vis_res["predicted_class"],
            crop=normalized_crop,
        )
    except UnsupportedCropError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except (ModelNotLoadedError, InferenceError) as e:
        logger.error(f"Vision inference failure: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Inference forward pass failed.")

    image_summary = ImageDiagnosisSummary(
        crop=normalized_crop,
        predicted_class=vis_res["predicted_class"],
        confidence=vis_res["confidence"],
        class_scores=vis_res["class_scores"],
        model_version=vis_res["model_version"],
        explanation_status=vis_res["explanation_status"],
        heatmap_path=vis_res.get("heatmap_path"),
        foliar_severity=emp_severity.value,
        affected_area_percentage=round(emp_area, 2),
    )

    # 4. Resolve Agricultural Context & Location
    lat, lon, loc_name = resolve_location(district, latitude, longitude)
    context_obj = AgriculturalContextInput(
        crop_name=normalized_crop,
        crop_variety=crop_variety,
        growth_stage=CropGrowthStage(growth_stage.lower()) if growth_stage and growth_stage.lower() in CropGrowthStage._value2member_map_ else CropGrowthStage.UNKNOWN,
        soil_type=SoilType(soil_type.lower()) if soil_type and soil_type.lower() in SoilType._value2member_map_ else SoilType.UNKNOWN,
        irrigation_method=IrrigationMethod(irrigation_method.lower()) if irrigation_method and irrigation_method.lower() in IrrigationMethod._value2member_map_ else IrrigationMethod.UNKNOWN,
        latitude=lat,
        longitude=lon,
        district=loc_name,
    )

    # 5. Retrieve Historical Multi-Window Microclimate Profile
    try:
        hist_profile = await weather_feature_engineer.get_historical_profile(
            latitude=lat,
            longitude=lon,
            crop_name=normalized_crop,
            location_name=loc_name,
        )
    except Exception as w_err:
        logger.warning(f"Feature engineering warning ({w_err}); synthesizing regional baseline profile.")
        hist_profile = weather_feature_engineer._build_synthetic_regional_profile(lat, lon, loc_name, normalized_crop)

    # 6. Evaluate Environmental Stress & Disease Conduciveness
    weather_risk = weather_crop_health_risk_engine.evaluate_weather_risk(
        crop_name=normalized_crop,
        profile=hist_profile,
        context=context_obj,
    )

    # 7. Execute Multimodal Fusion
    multimodal_res = multimodal_fusion_engine.fuse(
        image_prediction=image_summary,
        weather_risk=weather_risk,
        context=context_obj,
        strategy=strategy or "CALIBRATED_BAYESIAN",
    )

    return multimodal_res


@router.post(
    "/weather-risk",
    response_model=WeatherRiskOnlyResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate Standalone Environmental Crop-Health & Disease Risk",
    description=(
        "Assesses multi-window environmental stress factors (heat, water deficit, waterlogging, wind) "
        "and evaluates crop-specific epidemiological disease conduciveness without requiring an uploaded image."
    ),
)
async def assess_standalone_weather_risk(
    context: AgriculturalContextInput,
) -> WeatherRiskOnlyResponse:
    """Evaluates field environmental disease risk and physiological crop stress."""
    crop_clean = context.crop_name.strip().lower()
    if crop_clean not in model_service.CROP_REGISTRY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported crop: '{context.crop_name}'. Supported crops: {', '.join(model_service.CROP_REGISTRY.keys())}",
        )

    lat, lon, loc_name = resolve_location(context.district, context.latitude, context.longitude)
    context.latitude = lat
    context.longitude = lon
    context.district = loc_name

    hist_profile = await weather_feature_engineer.get_historical_profile(
        latitude=lat,
        longitude=lon,
        crop_name=crop_clean,
        location_name=loc_name,
    )

    weather_risk = weather_crop_health_risk_engine.evaluate_weather_risk(
        crop_name=crop_clean,
        profile=hist_profile,
        context=context,
    )

    risk_tier = "CRITICAL" if weather_risk.overall_disease_pressure >= 0.70 else \
                "HIGH" if weather_risk.overall_disease_pressure >= 0.50 else \
                "MODERATE" if weather_risk.overall_disease_pressure >= 0.30 else "LOW"

    preventative_advisory = {
        "dominant_risk": weather_risk.dominant_weather_risk,
        "recommendation": {
            "en": "Scout field regularly. Maintain surface drainage and avoid excessive foliar wetness.",
            "mr": "पिकाची नियमित पाहणी करा. शेतात पाणी साचणार नाही याची खात्री करा.",
            "hi": "खेत की नियमित जांच करें। जलभराव न होने दें।"
        }
    }

    statutory_disclaimer = {
        "en": "Advisory Notice: Weather risk assessments represent environmental conduciveness and do not confirm physical infection.",
        "mr": "सूचना: हवामानातील रोगास अनुकूलता म्हणजे पिकावर प्रत्यक्ष रोग पडल्याची खात्री नव्हे.",
        "hi": "मौसम का जोखिम केवल पर्यावरणीय अनुकूलता दर्शाता है, यह प्रत्यक्ष रोग की पुष्टि नहीं है।"
    }

    return WeatherRiskOnlyResponse(
        crop=crop_clean,
        location_name=loc_name,
        latitude=lat,
        longitude=lon,
        agricultural_context=context,
        environmental_stresses=weather_risk.environmental_stresses,
        disease_conduciveness_profile=weather_risk.disease_conduciveness_profile,
        overall_crop_health_risk=weather_risk.overall_disease_pressure,
        health_risk_tier=risk_tier,
        spray_suitability=weather_risk.spray_suitability,
        is_safe_to_spray=weather_risk.is_safe_to_spray,
        historical_weather_summary=weather_risk.weather_summary,
        preventative_advisory=preventative_advisory,
        statutory_disclaimer=statutory_disclaimer,
    )


@router.get(
    "/crops",
    status_code=status.HTTP_200_OK,
    summary="Get Supported Crops and Context Metadata Options",
)
def list_multimodal_crops() -> Dict[str, Any]:
    """Returns supported crops, growth stages, soil types, and active risk models."""
    return {
        "supported_crops": list(model_service.CROP_REGISTRY.keys()),
        "growth_stages": [e.value for e in CropGrowthStage],
        "soil_types": [e.value for e in SoilType],
        "irrigation_methods": [e.value for e in IrrigationMethod],
        "fusion_strategies": ["CALIBRATED_BAYESIAN", "RULE_BASED_GATE"],
        "districts": list(MAHARASHTRA_DISTRICTS.keys()),
        "maharashtra_districts": list(MAHARASHTRA_DISTRICTS.keys()),
    }
