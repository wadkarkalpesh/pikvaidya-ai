"""
PikVaidya AI — Expert Review Workflow Database Model
====================================================
Stores human agronomist reviews, verification audits, and prediction
corrections without silently mutating underlying ML training sets.
"""

import enum
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, Enum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class ReviewStatus(str, enum.Enum):
    PENDING = "PENDING"
    UNDER_REVIEW = "UNDER_REVIEW"
    CONFIRMED = "CONFIRMED"
    CORRECTED = "CORRECTED"
    REJECTED = "REJECTED"


class ExpertReview(Base):
    __tablename__ = "expert_reviews"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    diagnosis_id: Mapped[int] = mapped_column(ForeignKey("diagnoses.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    farmer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    expert_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus, name="review_status_enum", native_enum=False),
        default=ReviewStatus.PENDING,
        nullable=False,
        index=True,
    )

    # Initial AI diagnostic state
    original_disease_en: Mapped[str] = mapped_column(String(255), nullable=False)
    original_confidence: Mapped[Optional[float]] = mapped_column(nullable=True)
    farmer_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Human Expert Evaluation & Correction
    is_agreement: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    corrected_disease_en: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    corrected_disease_mr: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    pathogen_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    expert_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recommended_treatment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    diagnosis: Mapped["Diagnosis"] = relationship("Diagnosis", backref="expert_review")
    farmer: Mapped["User"] = relationship("User", foreign_keys=[farmer_id], backref="requested_reviews")
    expert: Mapped[Optional["User"]] = relationship("User", foreign_keys=[expert_id], backref="completed_reviews")

