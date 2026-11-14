"""PikVaidya AI — Agricultural RAG Assistant Schemas.
=================================================
Pydantic v2 schemas for conversational agricultural queries, multimodal inputs,
and LLM agent tool orchestration responses.
"""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field, ConfigDict, model_validator


class ChatQueryRequest(BaseModel):
    message: Optional[str] = Field(None, description="Farmer's conversational question in Marathi, Hindi, or English")
    query: Optional[str] = Field(None, description="Query alias for message")
    session_id: Optional[str] = Field(None, description="Optional UUID to continue previous dialogue session")
    crop: str = Field("sugarcane", description="Target crop context")
    diagnosis_id: Optional[int] = Field(None, description="Optional ID of prior diagnosis to bind into context")
    farm_id: Optional[int] = Field(None, description="Optional ID of farm to bind GPS and microclimate into context")
    preferred_language: Optional[str] = Field(None, description="Preferred response language ('mr', 'hi', 'en')")
    language: Optional[str] = Field(None, description="Language code alias")
    diagnostic_context: Optional[Dict[str, Any]] = Field(None, description="Optional foliar diagnostic findings")
    weather_context: Optional[Dict[str, Any]] = Field(None, description="Optional live weather conditions")

    @model_validator(mode="before")
    @classmethod
    def populate_message(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "query" in data and not data.get("message"):
                data["message"] = data["query"]
            elif "message" in data and not data.get("query"):
                data["query"] = data["message"]
        return data


class ToolExecutionTrace(BaseModel):
    tool_name: str = Field(..., description="Name of the invoked tool (e.g., crop_diagnosis_tool, weather_risk_tool)")
    status: str = Field(default="SUCCESS", description="Execution status: SUCCESS, SKIPPED, or FAILED")
    summary: str = Field(..., description="Summary of tool execution output")
    latency_ms: float = Field(default=0.0, description="Execution duration in milliseconds")


class MultimodalChatRequest(BaseModel):
    message: Optional[str] = Field(None, description="Farmer text query")
    image_base64: Optional[str] = Field(None, description="Base64 encoded JPEG/PNG foliar image")
    images_base64: List[str] = Field(default_factory=list, description="List of multiple base64 encoded images")
    image_filename: Optional[str] = Field(None, description="Optional filename of uploaded image")
    pdf_base64: Optional[str] = Field(None, description="Base64 encoded PDF agricultural document or soil card")
    pdf_filename: Optional[str] = Field(None, description="Optional filename of uploaded PDF")
    voice_transcript: Optional[str] = Field(None, description="Transcribed voice speech in Marathi/Hindi/English")
    session_id: Optional[str] = Field(None, description="Dialogue session ID for conversational memory")
    crop: str = Field("sugarcane", description="Target crop (sugarcane, tomato, onion)")
    farm_id: Optional[int] = Field(None, description="Optional farm ID to bind GPS coordinates")
    diagnosis_id: Optional[int] = Field(None, description="Optional prior diagnosis ID to bind")
    language: Optional[str] = Field(None, description="Preferred language code ('mr', 'hi', 'en')")
    latitude: Optional[float] = Field(None, description="WGS84 GPS latitude")
    longitude: Optional[float] = Field(None, description="WGS84 GPS longitude")
    district: Optional[str] = Field(None, description="Optional Maharashtra district name (e.g. Pune, Kolhapur)")


class MultimodalChatResponse(BaseModel):
    session_id: str
    query: str
    language: str
    reply: str
    answer: str
    tools_invoked: List[ToolExecutionTrace] = Field(default_factory=list)
    diagnostic_result: Optional[Dict[str, Any]] = None
    diagnostic_results: List[Dict[str, Any]] = Field(default_factory=list)
    weather_result: Optional[Dict[str, Any]] = None
    sources: List[Dict[str, str]] = Field(default_factory=list)
    retrieved_sources: List[Dict[str, str]] = Field(default_factory=list)
    key_recommendations: List[str] = Field(default_factory=list)
    is_grounded: bool = True
    statutory_disclaimer: str
    active_crop: Optional[str] = None
    active_disease: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ChatQueryResponse(BaseModel):
    session_id: str
    query: str
    language: str
    answer: str
    reply: Optional[str] = None
    key_recommendations: List[str]
    retrieved_sources: List[Dict[str, str]]
    sources: Optional[List[Dict[str, str]]] = None
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
