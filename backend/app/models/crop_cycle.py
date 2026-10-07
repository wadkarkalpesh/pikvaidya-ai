from datetime import date, datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, Date, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.farm import Farm


class CropCycle(Base):
    __tablename__ = "crop_cycles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    farm_id: Mapped[int] = mapped_column(ForeignKey("farms.id", ondelete="CASCADE"), nullable=False, index=True)
    crop: Mapped[str] = mapped_column(String(100), nullable=False)
    variety: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    sowing_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    growth_stage: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)
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
    farm: Mapped["Farm"] = relationship("Farm", back_populates="crop_cycles")
