import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, Float, Text, DateTime, ForeignKey, Enum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.crop_cycle import CropCycle


class DiagnosisStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class DiagnosisSeverity(str, enum.Enum):
    HEALTHY = "HEALTHY"
    MILD = "MILD"
    MODERATE = "MODERATE"
    SEVERE = "SEVERE"


class Diagnosis(Base):
    __tablename__ = "diagnoses"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    crop_cycle_id: Mapped[int] = mapped_column(
        ForeignKey("crop_cycles.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Image metadata
    image_path: Mapped[str] = mapped_column(String(500), nullable=False)
    image_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    image_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # Crop snapshot
    crop_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Diagnostic inference results
    disease_name_en: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    disease_name_mr: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    pathogen_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    severity: Mapped[Optional[DiagnosisSeverity]] = mapped_column(
        Enum(DiagnosisSeverity, name="diagnosis_severity_enum", native_enum=False),
        nullable=True,
    )
    affected_area_percentage: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Advisory & bilingual explanations
    symptoms_en: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    symptoms_mr: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recommendations_en: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recommendations_mr: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Environmental context telemetry
    temperature: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    humidity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    soil_moisture: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Status & Farmer Observation Notes
    status: Mapped[DiagnosisStatus] = mapped_column(
        Enum(DiagnosisStatus, name="diagnosis_status_enum", native_enum=False),
        default=DiagnosisStatus.PENDING,
        nullable=False,
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="diagnoses")
    crop_cycle: Mapped["CropCycle"] = relationship("CropCycle", back_populates="diagnoses")
