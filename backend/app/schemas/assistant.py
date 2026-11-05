"""
PikVaidya AI — Agricultural RAG Assistant Schemas
=================================================
Pydantic v2 schemas for conversational agricultural queries and retrieval responses.
"""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field, ConfigDict


class ChatQueryRequest(BaseModel):
    message: str = Field(..., description="Farmer's conversational question in Marathi, Hindi, or English")
    session_id: Optional[str] = Field(None, description="Optional UUID to continue previous dialogue session")
    crop: str = Field("sugarcane", description="Target crop context")
    diagnosis_id: Optional[int] = Field(None, description="Optional ID of prior diagnosis to bind into context")
    farm_id: Optional[int] = Field(None, description="Optional ID of farm to bind GPS and microclimate into context")
    preferred_language: Optional[str] = Field(None, description="Preferred response language ('mr', 'hi', 'en')")


class ChatQueryResponse(BaseModel):
    session_id: str
    query: str
    language: str
    answer: str
    key_recommendations: List[str]
    retrieved_sources: List[Dict[str, str]]
    is_grounded: bool
    statutory_disclaimer: str
    active_crop: Optional[str] = None
    active_disease: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class KnowledgeChunkResponse(BaseModel):
    chunk_id: str
    disease_id: str
    crop: str
    disease_name: str
    scientific_name: str
    section: str
    language: str
    snippet: str
    metadata: Dict[str, Any]

    model_config = ConfigDict(from_attributes=True)
