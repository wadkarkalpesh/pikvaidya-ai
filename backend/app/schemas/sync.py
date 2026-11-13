"""PikVaidya AI - Offline Synchronization Schemas.

Defines Pydantic models for bidirectional offline data synchronization between
client edge nodes (IndexedDB/PWA) and the central backend database.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class OfflineDiagnosisItem(BaseModel):
    client_id: Optional[str] = Field(None, description="Client-generated UUID")
    crop: str = Field(..., description="Crop identifier (e.g., sugarcane, tomato, onion)")
    disease_prediction: Optional[str] = Field(None, description="Local on-device ONNX classification")
    confidence: Optional[float] = Field(None, description="Local inference confidence score")
    notes: Optional[str] = Field(None, description="Farmer foliar observation notes")
    captured_at: str = Field(..., description="ISO 8601 offline capture timestamp")
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class SyncPushRequest(BaseModel):
    client_timestamp: str = Field(..., description="ISO timestamp of client synchronization cycle")
    device_id: Optional[str] = Field(None, description="Unique client edge hardware or browser identifier")
    diagnoses: List[OfflineDiagnosisItem] = Field(default_factory=list, description="Batch of offline diagnoses")
    farms: List[Dict[str, Any]] = Field(default_factory=list, description="Offline farm registry updates")
    crops: List[Dict[str, Any]] = Field(default_factory=list, description="Offline crop cycle changes")


class SyncConflictItem(BaseModel):
    entity_type: str
    client_id: str
    reason: str
    resolution: str


class SyncPushResponse(BaseModel):
    status: str = Field(default="success")
    synced_count: int = Field(default=0)
    conflicts: List[SyncConflictItem] = Field(default_factory=list)
    server_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    message: str = Field(default="Synchronization completed successfully")


class SyncPullResponse(BaseModel):
    status: str = Field(default="success")
    server_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    supported_crops: List[str] = Field(default_factory=lambda: ["sugarcane", "tomato", "onion"])
    offline_model_versions: Dict[str, str] = Field(default_factory=lambda: {
        "sugarcane": "sugarcane_mobilenetv3_large_v1.0.onnx",
        "tomato": "tomato_mobilenetv3_large_v1.0.onnx",
        "onion": "onion_mobilenetv3_large_v1.0.onnx"
    })
    disease_catalog_checksum: str = Field(default="sha256:d8a9f24e1b8c")

