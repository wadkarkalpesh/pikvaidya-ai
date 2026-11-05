"""
PikVaidya AI — Context-Aware Agricultural Advisory Schemas
==========================================================
Pydantic v2 schemas defining input context requests and structured multilingual
recommendation payloads incorporating ML diagnosis, disease knowledge, and microclimate.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict


class WeatherTelemetrySchema(BaseModel):
    temperature_c: float = Field(..., description="Ambient temperature in Celsius")
    relative_humidity_pct: float = Field(..., description="Relative humidity percentage")
    wind_speed_kmh: float = Field(..., description="Wind speed in km/h")
    precipitation_mm: float = Field(..., description="Precipitation in mm")
    precipitation_probability_6h: float = Field(..., description="Rain probability in next 6 hours")
    weather_condition: str = Field(..., description="WMO weather summary")
    is_live: bool = Field(True, description="Whether live API telemetry was successfully resolved")
    spray_suitability: str = Field(..., description="Spray safety status: OPTIMAL, UNFAVOURABLE_RAIN_RISK, etc.")
    is_safe_to_spray: bool = Field(..., description="Boolean gating flag for spray operations")
    fungal_risk_level: str = Field(..., description="Fungal infection conduciveness: HIGH, MODERATE, LOW")
    spray_guidance: Dict[str, str] = Field(..., description="Multilingual spray directive ('en', 'mr', 'hi')")


class AdvisoryGenerateRequest(BaseModel):
    crop_name: str = Field("sugarcane", description="Target crop (e.g. sugarcane)")
    predicted_disease: str = Field(..., description="Predicted disease class: Healthy, Mosaic, RedRot, Rust, Yellow")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model classification confidence score")
    severity: Optional[str] = Field("UNAVAILABLE", description="Severity category: HEALTHY, MILD, MODERATE, SEVERE")
    affected_area_percentage: Optional[float] = Field(None, ge=0.0, le=100.0, description="Foliar lesion surface area %")
    latitude: Optional[float] = Field(None, description="GPS latitude of the farm")
    longitude: Optional[float] = Field(None, description="GPS longitude of the farm")
    temperature: Optional[float] = Field(None, description="Manual ambient temperature override (°C)")
    humidity: Optional[float] = Field(None, description="Manual relative humidity override (%)")
    crop_stage: Optional[str] = Field("grand_growth", description="Crop growth stage: germination, tillering, grand_growth, maturity")
    preferred_language: Optional[str] = Field("mr", description="Primary UI language: 'mr' (Marathi), 'en' (English), 'hi' (Hindi)")


class AdvisoryChemicalPrescription(BaseModel):
    chemical_name: str = Field(..., description="Standard generic chemical formulation")
    trade_examples: str = Field(..., description="Common commercially available trade names in India")
    dosage: str = Field(..., description="Approved application dosage per liter or per hectare")
    dilution_rate: str = Field(..., description="Water dilution requirements")
    phi_days: int = Field(..., description="Pre-Harvest Interval in days")
    cibrc_status: str = Field(..., description="Statutory approval body (CIBRC, ICAR)")
    target_pathogen_or_vector: str = Field(..., description="Biological target (e.g. Fungal pathogen or insect vector)")
    ppe_guidelines: Dict[str, str] = Field(..., description="Mandatory protective gear instructions")


class ContextualAdvisoryResponse(BaseModel):
    crop_name: str
    disease_id: str
    disease_name: Dict[str, str]
    scientific_name: str
    pathogen_type: str
    confidence: float
    confidence_tier: str  # HIGH, MODERATE, LOW_INCONCLUSIVE
    severity: str
    affected_area_percentage: Optional[float]
    is_chemical_permitted: bool
    chemical_suppression_reason: Optional[Dict[str, str]] = None
    weather_telemetry: Optional[WeatherTelemetrySchema] = None
    overview: Dict[str, str]
    cultural_practices: Dict[str, List[str]]
    biological_controls: Dict[str, List[str]]
    chemical_prescriptions: List[AdvisoryChemicalPrescription]
    spray_window_directive: Dict[str, str]
    expert_consultation_notice: Dict[str, str]
    statutory_disclaimer: Dict[str, str]
    reference_sources: List[Dict[str, str]]

    model_config = ConfigDict(from_attributes=True)

