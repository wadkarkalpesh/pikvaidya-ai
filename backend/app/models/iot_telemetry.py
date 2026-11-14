"""
PikVaidya AI — IoT Sensor Telemetry Database Model
==================================================
Stores high-resolution, in-situ sensor telemetry streams captured by field IoT devices,
including canopy microclimate, leaf wetness duration, root-zone soil matric parameters,
and physical ambient atmospheric observations.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, Float, Integer, DateTime, Boolean, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.iot_device import IoTDevice
    from app.models.farm import Farm


class IoTTelemetry(Base):
    """Time-series sensor observation captured by an in-situ agricultural IoT node."""
    __tablename__ = "iot_telemetry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_id: Mapped[str] = mapped_column(
        ForeignKey("iot_devices.device_id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    farm_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("farms.id", ondelete="CASCADE"),
        index=True,
        nullable=True
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        index=True,
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    # In-Situ Atmospheric & Canopy Microclimate
    ambient_temperature_c: Mapped[float] = mapped_column(Float, nullable=False)
    ambient_humidity_pct: Mapped[float] = mapped_column(Float, nullable=False)
    canopy_temperature_c: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    canopy_humidity_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # High-Value Pathological Indicators (Leaf Surface Wetness)
    leaf_wetness_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 0 to 60 mins/hr
    leaf_wetness_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Root-Zone Soil Dynamics
    soil_moisture_10cm_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    soil_moisture_30cm_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    soil_temperature_c: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Hydrological & Kinematic Observations
    rainfall_rate_mmh: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    rainfall_cumulative_mm: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    wind_speed_2m_kmh: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    wind_gust_kmh: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    solar_radiation_wm2: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    atmospheric_pressure_hpa: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Real-Time Evaluated Agronomic Risk Indices
    spray_window_safe: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    fungal_conduciveness_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # 0.0 to 1.0
    frost_risk: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    heat_stress_risk: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Hardware Telemetry State
    battery_level_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    battery_voltage_v: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    signal_rssi: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Audit & Ingestion Trace
    raw_payload: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    device: Mapped["IoTDevice"] = relationship("IoTDevice", back_populates="telemetries")
    farm: Mapped[Optional["Farm"]] = relationship("Farm")

    def __repr__(self) -> str:
        return (
            f"<IoTTelemetry(id={self.id}, device='{self.device_id}', "
            f"temp={self.ambient_temperature_c}°C, wetness={self.leaf_wetness_minutes}m, "
            f"safe_to_spray={self.spray_window_safe})>"
        )
