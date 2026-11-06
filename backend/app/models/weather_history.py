"""
PikVaidya AI — Weather History Database Model
=============================================
Stores atmospheric and soil moisture telemetry observations for agricultural audit,
epidemiological disease progression correlation, and microclimatic trend analytics.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Float, Integer, DateTime, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class WeatherObservation(Base):
    """Historical weather observation record for agricultural microclimate tracking."""
    __tablename__ = "weather_observations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    latitude: Mapped[float] = mapped_column(Float, index=True, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, index=True, nullable=False)
    location_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    
    # Atmospheric Telemetry
    temperature: Mapped[float] = mapped_column(Float, nullable=False)
    apparent_temperature: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    humidity: Mapped[float] = mapped_column(Float, nullable=False)
    precipitation: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    precipitation_probability: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    wind_speed: Mapped[float] = mapped_column(Float, nullable=False)
    wind_direction: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    wind_gusts: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    surface_pressure: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cloud_cover: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Root-Zone Soil Telemetry (Modeled ERA5 / ICON)
    soil_moisture: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    soil_temperature: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Condition & Classification
    weather_condition: Mapped[str] = mapped_column(String(100), nullable=False)
    weather_code: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_live: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Agronomic Diagnostics
    spray_suitability: Mapped[str] = mapped_column(String(50), nullable=False)  # OPTIMAL, UNFAVOURABLE_RAIN_RISK, etc.
    fungal_risk_level: Mapped[str] = mapped_column(String(20), default="LOW", nullable=False)  # HIGH, MODERATE, LOW
    
    # Metadata
    data_source: Mapped[str] = mapped_column(String(50), default="open-meteo", nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
        nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<WeatherObservation(id={self.id}, location='{self.location_name}', "
            f"temp={self.temperature}°C, rh={self.humidity}%, status='{self.spray_suitability}')>"
        )

