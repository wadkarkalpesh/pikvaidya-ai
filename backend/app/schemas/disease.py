"""
PikVaidya AI — Disease Knowledge Pydantic Schemas
=================================================
Validates request bodies and serializes API responses for
agricultural disease information.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class DiseaseBase(BaseModel):
    crop_name: str = Field(..., description="Target crop (e.g., sugarcane, tomato, cotton, soybean, onion)")
    disease_name: str = Field(..., description="Standard common name of pathology")
    scientific_name: str = Field(..., description="Binomial taxonomic name of causal agent")
    pathogen_type: str = Field(..., description="Pathogen category (Fungal, Viral, Bacterial, Physiological, None)")

    symptoms: Dict[str, str] = Field(..., description="Multilingual symptoms: {'en': '...', 'mr': '...', 'hi': '...'}")
    causes: Dict[str, str] = Field(..., description="Multilingual causes: {'en': '...', 'mr': '...', 'hi': '...'}")
    favourable_conditions: Dict[str, Any] = Field(..., description="Environmental triggers and weather thresholds")
    prevention_methods: Dict[str, List[str]] = Field(..., description="Multilingual list of preventative measures")
    management_methods: Dict[str, Any] = Field(..., description="Cultural, biological, and CIBRC chemical controls")
    reference_sources: List[Dict[str, Any]] = Field(..., description="Authoritative scientific citations")

    language: str = Field("multilingual", description="Primary or composite language code")
    is_verified: bool = Field(True, description="Whether record is verified against ICAR/CIBRC standards")
    last_verified: str = Field(..., description="Verification date/stamp (YYYY-MM-DD)")


class DiseaseCreate(DiseaseBase):
    disease_id: str = Field(..., description="Unique slug identifier (e.g., sugarcane_red_rot)")


class DiseaseUpdate(BaseModel):
    crop_name: Optional[str] = None
    disease_name: Optional[str] = None
    scientific_name: Optional[str] = None
    pathogen_type: Optional[str] = None
    symptoms: Optional[Dict[str, str]] = None
    causes: Optional[Dict[str, str]] = None
    favourable_conditions: Optional[Dict[str, Any]] = None
    prevention_methods: Optional[Dict[str, List[str]]] = None
    management_methods: Optional[Dict[str, Any]] = None
    reference_sources: Optional[List[Dict[str, Any]]] = None
    is_verified: Optional[bool] = None
    last_verified: Optional[str] = None


class DiseaseResponse(DiseaseBase):
    model_config = ConfigDict(from_attributes=True)

    disease_id: str
    created_at: datetime
    updated_at: datetime


class DiseaseSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    disease_id: str
    crop_name: str
    disease_name: str
    scientific_name: str
    pathogen_type: str
    is_verified: bool
    last_verified: str


class DiseaseSearchResult(BaseModel):
    disease_id: str
    crop_name: str
    disease_name: str
    scientific_name: str
    pathogen_type: str
    match_snippet: str
    matched_field: str
    language: str

