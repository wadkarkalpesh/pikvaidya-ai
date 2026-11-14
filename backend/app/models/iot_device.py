"""
PikVaidya AI — IoT Device Database Model
========================================
Represents physical in-situ farm sensor nodes (microclimate stations, leaf wetness sensors,
soil matric probes, and automated weather stations) deployed across agricultural parcels.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import String, Float, Integer, DateTime, Boolean, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.farm import Farm
    from app.models.iot_telemetry import IoTTelemetry


class IoTDevice(Base):
    """Registered physical IoT sensor node deployed on an agricultural farm parcel."""
    __tablename__ = "iot_devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    device_name: Mapped[str] = mapped_column(String(255), nullable=False)
    farm_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("farms.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    
    # Device Classification
    device_type: Mapped[str] = mapped_column(
        String(50),
        default="WEATHER_STATION",
        nullable=False
    )  # WEATHER_STATION, CANOPY_MONITOR, SOIL_PROBE, INTEGRATED_NODE
    hardware_model: Mapped[str] = mapped_column(String(100), default="ESP32-LoRa-Solar-v1", nullable=False)
    firmware_version: Mapped[str] = mapped_column(String(50), default="1.0.0", nullable=False)
    
    # Authentication & Gateway Security
    api_key_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Operational Status
    status: Mapped[str] = mapped_column(
        String(50),
        default="ACTIVE",
        nullable=False
    )  # ACTIVE, OFFLINE, MAINTENANCE, DECOMMISSIONED
    
    # Telemetry Health & Connectivity
    battery_level_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    battery_voltage_v: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    solar_charging: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    signal_rssi: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # in dBm
    signal_snr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)   # in dB (LoRa)
    
    # Spatial Coordinates
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    altitude_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Lifecycle Timestamps
    last_telemetry_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Relationships
    farm: Mapped[Optional["Farm"]] = relationship("Farm")
    telemetries: Mapped[List["IoTTelemetry"]] = relationship(
        "IoTTelemetry",
        back_populates="device",
        cascade="all, delete-orphan",
        order_by="desc(IoTTelemetry.timestamp)"
    )

    def __repr__(self) -> str:
        return (
            f"<IoTDevice(id={self.id}, device_id='{self.device_id}', "
            f"name='{self.device_name}', status='{self.status}')>"
        )
