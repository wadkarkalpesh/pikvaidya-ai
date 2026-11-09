"""
PikVaidya AI — Multimodal Crop-Health Prediction Schemas
========================================================
Defines Pydantic v2 data models for:
1. Agricultural context metadata (crop, growth stage, soil, irrigation).
2. Historical microclimate feature engineering vectors (24h, 3d, 7d, 14d).
3. Environmental stress & disease conduciveness profiles.
4. Separate image and weather prediction outputs.
5. Calibrated multimodal fusion assessment & explainability breakdown.
"""

from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict, model_validator


class CropGrowthStage(str, Enum):
    GERMINATION = "germination"
    VEGETATIVE = "vegetative"
    TILLERING = "tillering"
    FLOWERING_FRUITING = "flowering_fruiting"
    GRAND_GROWTH = "grand_growth"
    BULB_DEVELOPMENT = "bulb_development"
    MATURITY = "maturity"
    UNKNOWN = "unknown"


class SoilType(str, Enum):
    BLACK_COTTON = "black_cotton"
    LOAMY = "loamy"
    CLAY_LOAM = "clay_loam"
    SANDY_LOAM = "sandy_loam"
    RED_SOIL = "red_soil"
    LATERITE = "laterite"
    UNKNOWN = "unknown"


class IrrigationMethod(str, Enum):
    DRIP = "drip"
    SPRINKLER = "sprinkler"
    FLOOD_FURROW = "flood_furrow"
    RAINFED = "rainfed"
    UNKNOWN = "unknown"


class AgriculturalContextInput(BaseModel):
    """Agronomic metadata characterizing the farm plot."""
    crop_name: str = Field("sugarcane", description="Target crop (sugarcane, tomato, onion)")
    crop_variety: Optional[str] = Field(None, description="Crop cultivar / variety (e.g. Co 86032, Abhinav, Bhima Kiran)")
    growth_stage: CropGrowthStage = Field(CropGrowthStage.UNKNOWN, description="Crop developmental stage")
    sowing_date: Optional[str] = Field(None, description="Planting / sowing date (YYYY-MM-DD)")
    soil_type: SoilType = Field(SoilType.UNKNOWN, description="Soil textural class")
    irrigation_method: IrrigationMethod = Field(IrrigationMethod.UNKNOWN, description="Primary irrigation system")
    latitude: Optional[float] = Field(None, description="Farm latitude coordinate")
    longitude: Optional[float] = Field(None, description="Farm longitude coordinate")
    district: Optional[str] = Field(None, description="District / Taluka name in Maharashtra")

    model_config = ConfigDict(use_enum_values=True)

    @model_validator(mode="before")
    @classmethod
    def populate_crop_name(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "crop" in data and "crop_name" not in data:
                data["crop_name"] = data["crop"]
        return data


class HistoricalWindowMetrics(BaseModel):
    """Statistical weather features aggregated over a specific backward time window."""
    window_hours: int = Field(..., description="Aggregation window duration in hours (e.g. 24, 72, 168, 336)")
    temp_avg_c: float = Field(..., description="Mean temperature (°C)")
    temp_max_c: float = Field(..., description="Peak temperature (°C)")
    temp_min_c: float = Field(..., description="Minimum temperature (°C)")
    temp_diurnal_range_c: float = Field(..., description="Diurnal temperature swing: temp_max - temp_min (°C)")
    humidity_avg_pct: float = Field(..., description="Mean relative humidity (%)")
    humidity_min_pct: float = Field(..., description="Minimum relative humidity (%)")
    humidity_max_pct: float = Field(..., description="Maximum relative humidity (%)")
    high_humidity_hours: int = Field(..., description="Cumulative hours where RH >= 85%")
    saturation_humidity_hours: int = Field(..., description="Cumulative hours where RH >= 90%")
    rainfall_total_mm: float = Field(..., description="Cumulative rainfall volume (mm)")
    rainy_days_count: int = Field(..., description="Count of days with rainfall >= 1.0 mm")
    consecutive_rainy_days: int = Field(..., description="Maximum streak of consecutive rainy days")
    rainfall_frequency: float = Field(..., description="Fraction of days in window with precipitation (0.0 to 1.0)")
    wind_speed_avg_kmh: float = Field(..., description="Mean sustained wind speed (km/h)")
    wind_gust_max_kmh: float = Field(..., description="Peak wind gust (km/h)")
    cloud_cover_avg_pct: float = Field(..., description="Mean cloud cover percentage (%)")
    soil_moisture_avg_pct: Optional[float] = Field(None, description="Mean volumetric soil moisture percentage (0-7cm)")
    soil_moisture_trend: Optional[str] = Field("STABLE", description="Soil water trend: DEPLETING, STABLE, ACCUMULATING, SATURATED")
    soil_temp_avg_c: Optional[float] = Field(None, description="Mean root-zone soil temperature (°C)")
    growing_degree_days: float = Field(..., description="Accumulated thermal units (GDD)")


class HistoricalWeatherProfile(BaseModel):
    """Multi-window historical environmental profile."""
    latitude: float
    longitude: float
    location_name: str
    resolved_at: str
    data_source: str = Field("open-meteo-historical", description="Provider identifier")
    data_completeness_pct: float = Field(100.0, description="Percentage of valid sensor readings in requested history")
    window_24h: HistoricalWindowMetrics
    window_3d: HistoricalWindowMetrics
    window_7d: HistoricalWindowMetrics
    window_14d: HistoricalWindowMetrics


class EnvironmentalStressIndices(BaseModel):
    """Physiological crop stress factors quantified from environmental exposure."""
    heat_stress_index: float = Field(..., ge=0.0, le=1.0, description="Heat stress severity index (0=Optimal, 1=Severe scorching/desiccation)")
    water_stress_index: float = Field(..., ge=0.0, le=1.0, description="Drought / water deficit stress index (0=Hydrated, 1=Wilting)")
    excess_water_flood_index: float = Field(..., ge=0.0, le=1.0, description="Waterlogging / root asphyxiation risk index (0=Normal, 1=Submerged)")
    wind_damage_risk: float = Field(..., ge=0.0, le=1.0, description="Wind damage and spray drift hazard index (0=Calm, 1=Gale)")
    overall_environmental_stress: float = Field(..., ge=0.0, le=1.0, description="Composite environmental stress score")
    environmental_suitability_score: float = Field(..., ge=0.0, le=1.0, description="Crop-specific climatic comfort index (0=Unsuitable, 1=Ideal)")
    stress_summary: Dict[str, str] = Field(..., description="Multilingual summary of active physiological stresses")


class DiseaseConducivenessScore(BaseModel):
    """Epidemiological risk score indicating whether microclimate favors a specific pathogen."""
    disease_id: str
    disease_name_en: str
    disease_name_mr: str
    pathogen_type: str
    conduciveness_score: float = Field(..., ge=0.0, le=1.0, description="Environmental conduciveness score (0.0 to 1.0)")
    risk_tier: str = Field(..., description="Conduciveness tier: MINIMAL, MODERATE, HIGH, CRITICAL")
    favourable_conditions_met: List[str] = Field(default_factory=list, description="Specific scientific weather criteria satisfied")
    epidemiological_rationale: Dict[str, str] = Field(..., description="Multilingual biological justification")


class ImageDiagnosisSummary(BaseModel):
    """Identifiable vision model inference output."""
    crop: str
    predicted_class: str
    confidence: float
    class_scores: Dict[str, float]
    model_version: str
    explanation_status: str
    heatmap_path: Optional[str] = None
    foliar_severity: Optional[str] = None
    affected_area_percentage: Optional[float] = None


class WeatherRiskAssessmentSummary(BaseModel):
    """Identifiable weather-based crop-health and epidemiological assessment output."""
    crop: str
    environmental_stresses: EnvironmentalStressIndices
    disease_conduciveness_profile: List[DiseaseConducivenessScore]
    dominant_weather_risk: str
    overall_disease_pressure: float = Field(..., ge=0.0, le=1.0)
    spray_suitability: str
    is_safe_to_spray: bool
    spray_guidance: Dict[str, str]
    weather_summary: Dict[str, Any]


class MultimodalAssessmentSummary(BaseModel):
    """Fused multimodal prediction synthesized across visual symptoms and environmental context."""
    primary_diagnosis: str = Field(..., description="Final fused disease classification or health state")
    display_name: Dict[str, str] = Field(..., description="Multilingual name of primary diagnosed condition")
    fused_confidence: float = Field(..., ge=0.0, le=1.0, description="Calibrated posterior confidence score")
    confidence_tier: str = Field(..., description="Confidence tier: HIGH, MODERATE, LOW_INCONCLUSIVE")
    crop_health_index: float = Field(..., ge=0.0, le=100.0, description="Composite health index (0=Severely diseased/wilted, 100=Pristine)")
    health_status_label: str = Field(..., description="HEALTHY, VULNERABLE, MILDLY_INFECTED, MODERATELY_INFECTED, SEVERELY_INFECTED")
    disease_progression_velocity: str = Field(..., description="Expected infection acceleration: SLOW, MODERATE, RAPID, ARRESTED")
    agronomic_concordance: float = Field(..., ge=0.0, le=1.0, description="Alignment between visual symptoms and weather risk")
    is_environmentally_concordant: bool = Field(..., description="True if weather conditions plausibly support the visual finding")
    anomaly_warning: Optional[Dict[str, str]] = Field(None, description="Warning if visual disease appears in hostile environmental conditions")
    fusion_strategy_applied: str = Field(..., description="Method used: CALIBRATED_BAYESIAN, RULE_BASED_GATE, SUPERVISED_ML")


class MultimodalExplainability(BaseModel):
    """Transparent attribution explaining how visual and environmental factors shaped the decision."""
    image_contribution_pct: float = Field(..., ge=0.0, le=100.0, description="Relative influence of image visual features (%)")
    weather_contribution_pct: float = Field(..., ge=0.0, le=100.0, description="Relative influence of environmental conditions (%)")
    primary_contributing_factors: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Ranked list of key factors (e.g. leaf lesions, 7d rain accumulation, heat stress)",
    )
    gradcam_visual_evidence: Dict[str, Any] = Field(..., description="Grad-CAM spatial localization details & disclaimer")
    multimodal_narrative: Dict[str, str] = Field(..., description="Farmer-friendly multilingual narrative of why this assessment was made")


class MultimodalPredictResponse(BaseModel):
    """Complete, end-to-end multimodal diagnostic response payload."""
    multimodal_assessment: MultimodalAssessmentSummary
    image_prediction: ImageDiagnosisSummary
    weather_risk: WeatherRiskAssessmentSummary
    explainability: MultimodalExplainability
    agricultural_context: AgriculturalContextInput
    recommendations: Dict[str, Any]
    statutory_disclaimer: Dict[str, str]
    captured_at: Optional[str] = Field(None, description="Original offline capture timestamp if synced from queue")
    is_offline_synced: Optional[bool] = Field(None, description="Whether this diagnosis was captured offline and synced")

    model_config = ConfigDict(from_attributes=True)


class WeatherRiskOnlyResponse(BaseModel):
    """Standalone environmental crop-health assessment response (when no leaf photo is uploaded)."""
    crop: str
    location_name: str
    latitude: float
    longitude: float
    agricultural_context: AgriculturalContextInput
    environmental_stresses: EnvironmentalStressIndices
    disease_conduciveness_profile: List[DiseaseConducivenessScore]
    overall_crop_health_risk: float = Field(..., ge=0.0, le=1.0)
    health_risk_tier: str
    spray_suitability: str
    is_safe_to_spray: bool
    historical_weather_summary: Dict[str, Any]
    preventative_advisory: Dict[str, Any]
    statutory_disclaimer: Dict[str, str]
    captured_at: Optional[str] = Field(None, description="Original offline capture timestamp if synced from queue")
    is_offline_synced: Optional[bool] = Field(None, description="Whether this diagnosis was captured offline and synced")

    model_config = ConfigDict(from_attributes=True)


class UnifiedCropHealthPredictResponse(BaseModel):
    """Unified multi-crop health prediction response payload conforming to platform contract."""
    crop_type: str = Field(..., description="Target crop (sugarcane, tomato, onion)")
    crop_detection_method: str = Field("explicit_user_selection", description="Selection mode: explicit_user_selection or auto_detected_classifier")
    crop_detection_confidence: Optional[float] = Field(None, description="Confidence score if crop was automatically detected")
    predicted_disease: str = Field(..., description="Predicted foliar disease condition or healthy baseline")
    disease_name_multilingual: Dict[str, str] = Field(..., description="Localized disease names in English, Marathi, Hindi")
    model_confidence: float = Field(..., ge=0.0, le=1.0, description="Calibrated visual model prediction confidence")
    weather_summary: Dict[str, Any] = Field(..., description="14-day and 24-hour microclimate conditions summary")
    environmental_risk: Dict[str, Any] = Field(..., description="Crop-specific physiological stress and pathogen conduciveness profile")
    combined_assessment: Dict[str, Any] = Field(..., description="Synthesized crop health score, velocity, and health tier")
    gradcam_image_url: Optional[str] = Field(None, description="Relative URL to the Grad-CAM saliency overlay")
    advisory_recommendations: Dict[str, Any] = Field(..., description="CIBRC-compliant chemical & cultural practices, PHI, spray safety")
    data_source: str = Field("PikVaidya Multimodal v2.2.0 | Open-Meteo ERA5-Land", description="Underlying telemetry & model data source")
    timestamp: str = Field(..., description="ISO 8601 UTC timestamp of diagnostic execution")

    # Complete nested modules for rich dashboard rendering
    image_prediction: ImageDiagnosisSummary
    weather_risk: WeatherRiskAssessmentSummary
    multimodal_assessment: MultimodalAssessmentSummary
    explainability: MultimodalExplainability
    agricultural_context: AgriculturalContextInput
    statutory_disclaimer: Dict[str, str]
    captured_at: Optional[str] = Field(None, description="Original offline capture timestamp if synced from queue")
    is_offline_synced: Optional[bool] = Field(None, description="Whether this diagnosis was captured offline and synced")

    model_config = ConfigDict(from_attributes=True)

