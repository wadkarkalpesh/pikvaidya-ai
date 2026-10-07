from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict, Field
from app.models.user import UserRole


class UserBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    preferred_language: str = Field(default="en", max_length=10)
    role: UserRole = UserRole.FARMER


class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=6)
    preferred_language: str = Field(default="en", max_length=10)
    role: Optional[UserRole] = UserRole.FARMER


class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    preferred_language: Optional[str] = Field(None, max_length=10)
    password: Optional[str] = Field(None, min_length=6)


class FarmerProfileUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    preferred_language: Optional[str] = Field(None, max_length=10)


class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    preferred_language: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
