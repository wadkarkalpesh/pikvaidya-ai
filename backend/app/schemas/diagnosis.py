from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict
from app.models.diagnosis import DiagnosisSeverity, DiagnosisStatus


class DiagnosisBase(BaseModel):
    notes: Optional[str] = None
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    soil_moisture: Optional[float] = None


class DiagnosisCreate(DiagnosisBase):
    pass


class DiagnosisSummaryResponse(BaseModel):
    id: int
    crop_cycle_id: int
    crop_name: str
    disease_name_en: Optional[str] = None
    disease_name_mr: Optional[str] = None
    confidence: Optional[float] = None
    severity: Optional[DiagnosisSeverity] = None
    status: DiagnosisStatus
    image_path: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DiagnosisDetailResponse(BaseModel):
    id: int
    user_id: int
    crop_cycle_id: int
    crop_name: str
    image_path: str
    image_filename: str
    image_hash: str
    heatmap_path: Optional[str] = None
    
    # AI Diagnosis Fields
    disease_name_en: Optional[str] = None
    disease_name_mr: Optional[str] = None
    pathogen_type: Optional[str] = None
    confidence: Optional[float] = None
    severity: Optional[DiagnosisSeverity] = None
    affected_area_percentage: Optional[float] = None
    
    # Bilingual Advisory & Safety Status
    advisory_status: Optional[str] = None
    symptoms_en: Optional[str] = None
    symptoms_mr: Optional[str] = None
    recommendations_en: Optional[str] = None
    recommendations_mr: Optional[str] = None
    
    # Environmental telemetry
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    soil_moisture: Optional[float] = None
    
    status: DiagnosisStatus
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PredictResponse(BaseModel):
    crop: str
    predicted_class: str
    confidence: float
    class_scores: Dict[str, float]
    model_version: str
    explanation_status: str
    heatmap_path: Optional[str] = None
    advisory_status: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


