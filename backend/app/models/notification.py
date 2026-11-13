"""
PikVaidya AI — Notification & Alert Database Model
==================================================
Manages agrometeorological alerts, disease outbreak warnings,
expert review notifications, and crop monitoring reminders.
"""

import enum
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, Enum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class NotificationType(str, enum.Enum):
    WEATHER_ALERT = "WEATHER_ALERT"
    CROP_RISK = "CROP_RISK"
    DIAGNOSIS_UPDATE = "DIAGNOSIS_UPDATE"
    EXPERT_REVIEW = "EXPERT_REVIEW"
    SYSTEM = "SYSTEM"


class NotificationSeverity(str, enum.Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    notification_type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, name="notification_type_enum", native_enum=False),
        default=NotificationType.SYSTEM,
        nullable=False,
    )
    severity: Mapped[NotificationSeverity] = mapped_column(
        Enum(NotificationSeverity, name="notification_severity_enum", native_enum=False),
        default=NotificationSeverity.INFO,
        nullable=False,
    )
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    
    # Optional foreign entity linking
    related_diagnosis_id: Mapped[Optional[int]] = mapped_column(ForeignKey("diagnoses.id", ondelete="SET NULL"), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", backref="notifications")
