"""
PikVaidya AI — IoT Device & Telemetry Schemas
=============================================
Pydantic v2 schemas for in-situ agricultural IoT device registration,
authentication, real-time telemetry ingestion, and LoRaWAN webhook payloads.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class IoTDeviceCreate(BaseModel):
    device_id: str = Field(..., min_length=3, max_length=64, description="Unique hardware identifier or LoRaWAN DevEUI")
    device_name: str = Field(..., min_length=1, max_length=255, description="Human readable device name")
    farm_id: Optional[int] = Field(None, description="Associated farm identifier")
    device_type: str = Field(
        default="WEATHER_STATION",
        description="WEATHER_STATION, CANOPY_MONITOR, SOIL_PROBE, or INTEGRATED_NODE"
    )
    hardware_model: str = Field(default="ESP32-LoRa-Solar-v1", description="Hardware microcontroller and sensor suite model")
    firmware_version: str = Field(default="1.0.0", description="Installed firmware version")
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0, description="GPS Latitude")
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0, description="GPS Longitude")
    altitude_m: Optional[float] = Field(None, description="Altitude in meters above sea level")


class IoTDeviceUpdate(BaseModel):
    device_name: Optional[str] = Field(None, min_length=1, max_length=255)
    farm_id: Optional[int] = None
    device_type: Optional[str] = None
    hardware_model: Optional[str] = None
    firmware_version: Optional[str] = None
    status: Optional[str] = Field(None, description="ACTIVE, OFFLINE, MAINTENANCE, DECOMMISSIONED")
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)


class IoTDeviceResponse(BaseModel):
    id: int
    device_id: str
    device_name: str
    farm_id: Optional[int] = None
    device_type: str
    hardware_model: str
    firmware_version: str
    status: str
    battery_level_pct: Optional[float] = None
    battery_voltage_v: Optional[float] = None
    solar_charging: bool = False
    signal_rssi: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    last_telemetry_at: Optional[datetime] = None
    created_at: datetime
    api_key: Optional[str] = Field(None, description="Raw device API secret key, returned only upon creation")

    model_config = ConfigDict(from_attributes=True)


class IoTTelemetryIngest(BaseModel):
    ambient_temperature_c: float = Field(..., ge=-25.0, le=65.0, description="Ambient air temperature in Celsius")
    ambient_humidity_pct: float = Field(..., ge=0.0, le=100.0, description="Ambient relative humidity percentage")
    canopy_temperature_c: Optional[float] = Field(None, ge=-25.0, le=65.0, description="In-canopy microclimate temperature in Celsius")
    canopy_humidity_pct: Optional[float] = Field(None, ge=0.0, le=100.0, description="In-canopy relative humidity percentage")
    leaf_wetness_minutes: int = Field(default=0, ge=0, le=60, description="Duration of free moisture on foliage in the last hour")
    leaf_wetness_active: bool = Field(default=False, description="Whether leaf wetness is currently active")
    soil_moisture_10cm_pct: Optional[float] = Field(None, ge=0.0, le=100.0, description="Volumetric water content at 10cm depth (%)")
    soil_moisture_30cm_pct: Optional[float] = Field(None, ge=0.0, le=100.0, description="Volumetric water content at 30cm depth (%)")
    soil_temperature_c: Optional[float] = Field(None, ge=-15.0, le=60.0, description="Soil temperature at root-zone")
    rainfall_rate_mmh: float = Field(default=0.0, ge=0.0, le=300.0, description="Instantaneous rain rate (mm/h)")
    rainfall_cumulative_mm: float = Field(default=0.0, ge=0.0, description="Cumulative rainfall (mm) since midnight or reset")
    wind_speed_2m_kmh: float = Field(default=0.0, ge=0.0, le=200.0, description="Wind speed at 2 meters height (km/h)")
    wind_gust_kmh: Optional[float] = Field(None, ge=0.0, le=250.0, description="Peak wind gust speed (km/h)")
    solar_radiation_wm2: Optional[float] = Field(None, ge=0.0, le=2000.0, description="Solar irradiance (W/m²)")
    atmospheric_pressure_hpa: Optional[float] = Field(None, ge=700.0, le=1150.0, description="Barometric pressure (hPa)")
    battery_level_pct: Optional[float] = Field(None, ge=0.0, le=100.0, description="Device battery state of charge (%)")
    battery_voltage_v: Optional[float] = Field(None, ge=0.0, le=30.0, description="Battery pack voltage (V)")
    signal_rssi: Optional[int] = Field(None, ge=-140, le=0, description="Cellular/LoRa RSSI signal level (dBm)")
    timestamp: Optional[datetime] = Field(None, description="Observation timestamp; defaults to current UTC time if omitted")


class LoRaWANUplinkPayload(BaseModel):
    """Standard LoRaWAN application payload structure (compatible with ChirpStack v4 & The Things Network v3)."""
    end_device_ids: Optional[Dict[str, Any]] = None
    device_id: Optional[str] = None
    dev_eui: Optional[str] = None
    uplink_message: Optional[Dict[str, Any]] = None
    decoded_payload: Optional[Dict[str, Any]] = None
    data: Optional[str] = None  # Base64 encoded FRMPayload
    f_port: Optional[int] = None
    f_cnt: Optional[int] = None
    rx_metadata: Optional[List[Dict[str, Any]]] = None


class IoTTelemetryResponse(BaseModel):
    id: int
    device_id: str
    farm_id: Optional[int] = None
    timestamp: datetime
    ambient_temperature_c: float
    ambient_humidity_pct: float
    canopy_temperature_c: Optional[float] = None
    canopy_humidity_pct: Optional[float] = None
    leaf_wetness_minutes: int
    leaf_wetness_active: bool
    soil_moisture_10cm_pct: Optional[float] = None
    soil_moisture_30cm_pct: Optional[float] = None
    soil_temperature_c: Optional[float] = None
    rainfall_rate_mmh: float
    rainfall_cumulative_mm: float
    wind_speed_2m_kmh: float
    wind_gust_kmh: Optional[float] = None
    solar_radiation_wm2: Optional[float] = None
    atmospheric_pressure_hpa: Optional[float] = None
    spray_window_safe: bool
    fungal_conduciveness_score: float
    frost_risk: bool
    heat_stress_risk: bool
    battery_level_pct: Optional[float] = None
    signal_rssi: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class IoTTelemetrySummary(BaseModel):
    farm_id: int
    device_id: str
    device_name: str
    is_live: bool
    last_reading_at: Optional[datetime] = None
    current_temp_c: float
    current_humidity_pct: float
    canopy_temp_c: Optional[float] = None
    canopy_humidity_pct: Optional[float] = None
    current_soil_moisture_pct: Optional[float] = None
    leaf_wetness_hours_last_24h: float
    total_rainfall_last_24h_mm: float
    max_wind_speed_2m_kmh: float
    spray_window_status: str
    fungal_spore_risk_level: str
    active_alerts: List[str]
