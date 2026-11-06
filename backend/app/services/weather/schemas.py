"""
PikVaidya AI — Weather Data Schemas & Transfer Objects
======================================================
Defines strongly typed Pydantic models for current conditions,
soil telemetry, forecasts, alerts, and agricultural advisories.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass
from pydantic import BaseModel, Field, ConfigDict


@dataclass
class WeatherData:
    """Legacy backward-compatible weather data container."""
    temperature_c: float
    relative_humidity_pct: float
    wind_speed_kmh: float
    precipitation_mm: float
    precipitation_probability_6h: float
    weather_condition: str
    is_live: bool = True
    latitude: Optional[float] = None
    longitude: Optional[float] = None



class SoilTelemetry(BaseModel):
    """Foliar and root-zone soil telemetry."""
    soil_temperature_c: float = Field(..., description="Soil temperature at 0-7cm depth (°C)")
    soil_moisture_m3m3: float = Field(..., description="Volumetric soil water content (m³/m³)")
    soil_moisture_percentage: float = Field(..., description="Volumetric soil water content percentage (%)")
    is_modeled: bool = Field(True, description="Indicates data is derived from atmospheric land-surface models (ERA5-Land / ICON)")
    moisture_status: str = Field(..., description="Agronomic moisture status: SATURATED, OPTIMAL, DRY, SEVERELY_DEPLETED")
    description: str = Field(..., description="Agronomic interpretation of current soil moisture condition")


class CurrentWeatherPayload(BaseModel):
    """Real-time microclimate observations."""
    temperature_c: float = Field(..., description="Ambient air temperature at 2m (°C)")
    apparent_temperature_c: float = Field(..., description="Perceived temperature / heat index (°C)")
    relative_humidity_pct: float = Field(..., description="Relative humidity (%)")
    surface_pressure_hpa: float = Field(..., description="Atmospheric barometric pressure (hPa)")
    cloud_cover_pct: float = Field(..., description="Total cloud cover percentage (%)")
    wind_speed_kmh: float = Field(..., description="Sustained wind speed at 10m (km/h)")
    wind_direction_deg: float = Field(..., description="Wind direction azimuth (0-360 degrees)")
    wind_gusts_kmh: float = Field(..., description="Peak wind gusts (km/h)")
    precipitation_mm: float = Field(..., description="Current precipitation rate (mm/h)")
    precipitation_probability_6h: float = Field(..., description="Rain probability in the next 6 hours (%)")
    weather_condition: str = Field(..., description="WMO weather interpretation description")
    weather_code: int = Field(..., description="Standard WMO weather condition code (0-99)")
    is_live: bool = Field(True, description="True if fetched live; False if served from offline baseline")
    data_source: str = Field("open-meteo", description="Provider identifier (open-meteo, imd, fallback)")
    fetched_at: str = Field(..., description="ISO 8601 observation timestamp")
    latitude: float = Field(..., description="Resolved latitude coordinate")
    longitude: float = Field(..., description="Resolved longitude coordinate")
    location_name: str = Field(..., description="Resolved locality or district name")


class HourlyForecastItem(BaseModel):
    """Hourly forecast slice for 24-hour agricultural planning."""
    time: str = Field(..., description="ISO timestamp of forecast hour")
    temperature_c: float = Field(..., description="Predicted air temperature (°C)")
    relative_humidity_pct: float = Field(..., description="Predicted relative humidity (%)")
    precipitation_probability: float = Field(..., description="Probability of precipitation (%)")
    precipitation_mm: float = Field(..., description="Predicted precipitation volume (mm)")
    wind_speed_kmh: float = Field(..., description="Predicted wind speed at 10m (km/h)")
    weather_condition: str = Field(..., description="Condition description")
    weather_code: int = Field(..., description="WMO code")


class DailyForecastItem(BaseModel):
    """Daily forecast summary for 7-day agricultural scheduling."""
    date: str = Field(..., description="Forecast date (YYYY-MM-DD)")
    weather_code: int = Field(..., description="Dominant WMO code")
    weather_condition: str = Field(..., description="Condition summary")
    temp_max_c: float = Field(..., description="Maximum daytime temperature (°C)")
    temp_min_c: float = Field(..., description="Minimum nighttime temperature (°C)")
    precipitation_sum_mm: float = Field(..., description="Total expected daily precipitation (mm)")
    precipitation_probability_max: float = Field(..., description="Maximum precipitation probability (%)")
    wind_speed_max_kmh: float = Field(..., description="Maximum wind speed (km/h)")


class WeatherAlertItem(BaseModel):
    """Meteorological warnings and severe-weather advisories."""
    severity: str = Field(..., description="Severity level: CRITICAL, WARNING, WATCH, ADVISORY")
    category: str = Field(..., description="Alert category: RAIN, WIND, HEAT, DISEASE_RISK")
    title: str = Field(..., description="Short alert headline")
    title_mr: Optional[str] = Field(None, description="Marathi headline")
    title_hi: Optional[str] = Field(None, description="Hindi headline")
    description: str = Field(..., description="Detailed explanation of the meteorological hazard")
    description_mr: Optional[str] = Field(None, description="Marathi explanation")
    description_hi: Optional[str] = Field(None, description="Hindi explanation")
    source: str = Field(..., description="Issuing authority (e.g. IMD, Open-Meteo, PikVaidya Rules)")
    issued_at: str = Field(..., description="Timestamp of issue")


class SprayWindowAssessment(BaseModel):
    """Agronomic and regulatory evaluation of spraying safety."""
    status: str = Field(..., description="OPTIMAL, UNFAVOURABLE_RAIN_RISK, UNFAVOURABLE_DRIFT_RISK, UNFAVOURABLE_HEAT_STRESS, MARGINAL")
    is_safe_to_spray: bool = Field(..., description="Boolean gating flag")
    summary: Dict[str, str] = Field(..., description="Trilingual summary ('en', 'mr', 'hi')")
    advisory_recommendation: Dict[str, str] = Field(..., description="Trilingual detailed advice")
    fungal_risk_level: str = Field(..., description="HIGH, MODERATE, LOW")

    @property
    def summary_en(self) -> str:
        return self.summary.get("en", "")

    @property
    def summary_mr(self) -> str:
        return self.summary.get("mr", "")

    @property
    def summary_hi(self) -> str:
        return self.summary.get("hi", "")

    @property
    def advisory_recommendation_en(self) -> str:
        return self.advisory_recommendation.get("en", "")

    @property
    def advisory_recommendation_mr(self) -> str:
        return self.advisory_recommendation.get("mr", "")

    @property
    def advisory_recommendation_hi(self) -> str:
        return self.advisory_recommendation.get("hi", "")



class DiseaseRiskAssessment(BaseModel):
    """Microclimate-driven pathogen conduciveness evaluation."""
    crop: str = Field(..., description="Target crop")
    disease: str = Field(..., description="Target pathogen or disease")
    risk_level: str = Field(..., description="HIGH, MODERATE, LOW")
    favourable_conditions_met: List[str] = Field(..., description="List of matched environmental conditions")
    description: Dict[str, str] = Field(..., description="Trilingual risk explanation")
    agronomic_action: Dict[str, str] = Field(..., description="Recommended scouting or preventive action")


class IrrigationAdvisory(BaseModel):
    """Soil-moisture and precipitation-aware irrigation advisory."""
    status: str = Field(..., description="DEFER_IRRIGATION, NORMAL_IRRIGATION, SUPPLEMENTARY_IRRIGATION")
    soil_moisture_status: str = Field(..., description="SATURATED, OPTIMAL, DRY, SEVERELY_DEPLETED")
    rain_forecast_next_48h_mm: float = Field(..., description="Expected precipitation in next 48 hours (mm)")
    reason: Dict[str, str] = Field(..., description="Trilingual explanation")
    recommendation: Dict[str, str] = Field(..., description="Actionable watering recommendation")


class ComprehensiveWeatherReport(BaseModel):
    """Unified master payload delivering complete weather intelligence."""
    current: CurrentWeatherPayload
    soil: Optional[SoilTelemetry] = None
    hourly_24h: List[HourlyForecastItem] = Field(default_factory=list)
    daily_7d: List[DailyForecastItem] = Field(default_factory=list)
    spray_window: SprayWindowAssessment
    disease_risks: List[DiseaseRiskAssessment] = Field(default_factory=list)
    irrigation: Optional[IrrigationAdvisory] = None
    alerts: List[WeatherAlertItem] = Field(default_factory=list)
    location_name: str
    latitude: float
    longitude: float
    data_source: str
    last_updated: str

    model_config = ConfigDict(from_attributes=True)
