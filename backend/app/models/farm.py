from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import String, Float, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.crop_cycle import CropCycle


class Farm(Base):
    __tablename__ = "farms"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    area: Mapped[float] = mapped_column(Float, nullable=False)
    soil_type: Mapped[str] = mapped_column(String(100), nullable=False)
    irrigation: Mapped[str] = mapped_column(String(100), nullable=False)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
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
    owner: Mapped["User"] = relationship("User", back_populates="farms")
    crop_cycles: Mapped[List["CropCycle"]] = relationship(
        "CropCycle",
        back_populates="farm",
        cascade="all, delete-orphan"
    )
