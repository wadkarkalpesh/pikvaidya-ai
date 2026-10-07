from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class FarmBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    area: float = Field(..., gt=0, description="Area in acres or hectares")
    soil_type: str = Field(..., min_length=1, max_length=100)
    irrigation: str = Field(..., min_length=1, max_length=100)
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)


class FarmCreate(FarmBase):
    pass


class FarmUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    area: Optional[float] = Field(None, gt=0)
    soil_type: Optional[str] = Field(None, min_length=1, max_length=100)
    irrigation: Optional[str] = Field(None, min_length=1, max_length=100)
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)


class FarmResponse(FarmBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
