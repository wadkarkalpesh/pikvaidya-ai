from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class CropCycleBase(BaseModel):
    crop: str = Field(..., min_length=1, max_length=100)
    variety: Optional[str] = Field(None, max_length=100)
    sowing_date: Optional[date] = None
    growth_stage: Optional[str] = Field(None, max_length=100)
    status: str = Field(default="active", max_length=50)


class CropCycleCreate(CropCycleBase):
    pass


class CropCycleUpdate(BaseModel):
    crop: Optional[str] = Field(None, min_length=1, max_length=100)
    variety: Optional[str] = Field(None, max_length=100)
    sowing_date: Optional[date] = None
    growth_stage: Optional[str] = Field(None, max_length=100)
    status: Optional[str] = Field(None, max_length=50)


class CropCycleResponse(CropCycleBase):
    id: int
    farm_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
