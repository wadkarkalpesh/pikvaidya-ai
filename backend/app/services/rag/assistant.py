"""
PikVaidya AI — Agricultural RAG Conversational Assistant
========================================================
Orchestrates multi-turn dialogue, language auto-detection (Marathi, Hindi, English),
session memory, query contextualization, and fact-grounded response generation.

Capabilities:
1. Multi-turn Session Memory: Maintains conversational context for follow-up questions.
2. Indic Language Detection: Distinguishes Marathi (मराठी) and Hindi (हिंदी) from English.
3. Diagnostic & Telemetry Binding: Links live foliar diagnoses and weather to chat queries.
4. Hallucination-Free Responses: Restricts agronomic answers strictly to retrieved ICAR citations.
"""

import re
import uuid
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from sqlalchemy.orm import Session

from app.services.rag.indexer import rag_indexer
from app.services.rag.grounding import AgriculturalGroundingEngine, GroundedResponse
from app.services.weather_service import weather_service
from app.models.diagnosis import Diagnosis
from app.models.farm import Farm

logger = logging.getLogger(__name__)


@dataclass
class ChatMessage:
    role: str  # "user" or "assistant"
    content: str
    language: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChatSession:
    session_id: str
    history: List[ChatMessage] = field(default_factory=list)
    active_crop: str = "sugarcane"
    active_disease: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class AgriculturalRAGAssistant:
    """Manages conversational agricultural advisory sessions with hybrid RAG retrieval."""

    def __init__(self):
        self.sessions: Dict[str, ChatSession] = {}
        # Distinct Marathi linguistic markers
        self.MR_KEYWORDS = {"ऊस", "उसावर", "उसावरील", "आहे", "आहेत", "करावे", "करावी", "नाही", "पाने", "पानांवर", "औषध", "फवारणी", "काय", "कोणती", "कशी", "सांगा", "पडलेल्या", "कूज", "तांबेरा"}
        # Distinct Hindi linguistic markers
        self.HI_KEYWORDS = {"गन्ना", "गन्ने", "है", "करें", "नहीं", "पत्तियां", "पत्ती", "दवा", "छिड़काव", "रोकथाम", "कैसे", "उपाय", "में", "बताएं", "होता", "होती", "लाल"}

    def detect_language(self, text: str, fallback_lang: str = "en") -> str:
        """Detects whether text is in Marathi, Hindi, or English."""
        # Check Devanagari Unicode block
        devanagari_chars = len(re.findall(r"[\u0900-\u097F]", text))
        if devanagari_chars > 3:
            words = set(re.findall(r"[\w\u0900-\u097F]+", text.lower()))
            mr_count = len(words & self.MR_KEYWORDS)
            hi_count = len(words & self.HI_KEYWORDS)
            if hi_count > mr_count:
                return "hi"
            if mr_count > hi_count:
                return "mr"
            if "ळ" in text:
                return "mr"
            return fallback_lang if fallback_lang in ["mr", "hi"] else "mr"

        return fallback_lang.lower() if fallback_lang in ["en", "mr", "hi"] else "en"

    def get_or_create_session(self, session_id: Optional[str] = None) -> ChatSession:
        """Retrieves existing session or creates a new one."""
        sid = session_id.strip() if session_id and session_id.strip() else str(uuid.uuid4())
        if sid not in self.sessions:
            self.sessions[sid] = ChatSession(session_id=sid)
        return self.sessions[sid]

    async def chat(
        self,
        message: str,
        session_id: Optional[str] = None,
        crop: str = "sugarcane",
        diagnosis_id: Optional[int] = None,
        farm_id: Optional[int] = None,
        preferred_language: Optional[str] = None,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Executes multi-turn conversational chat with RAG fact grounding.
        """
        session = self.get_or_create_session(session_id)
        session.active_crop = crop.lower().strip()

        # 1. Detect language
        detected_lang = self.detect_language(message, fallback_lang=preferred_language or "en")

        # 2. Contextualize query with multi-turn history
        search_query = self._expand_query_with_history(message, session)

        # 3. Resolve diagnostic context if diagnosis_id is provided
        diag_context = None
        if diagnosis_id and db:
            diag = db.query(Diagnosis).filter(Diagnosis.id == diagnosis_id).first()
            if diag:
                diag_context = {
                    "disease_name": diag.disease_name_en,
                    "predicted_disease": diag.disease_name_en,
                    "confidence": diag.confidence or 0.85,
                    "severity": diag.severity.value if diag.severity else "MODERATE"
                }
                session.active_disease = diag.disease_name_en

        # 4. Resolve farm microclimate if farm_id is provided
        weather_context = None
        if farm_id and db:
            farm = db.query(Farm).filter(Farm.id == farm_id).first()
            if farm and farm.latitude and farm.longitude:
                session.latitude = farm.latitude
                session.longitude = farm.longitude
                try:
                    w_data = await weather_service.get_current_weather(farm.latitude, farm.longitude)
                    s_assess = weather_service.assess_spray_suitability(w_data)
                    weather_context = {
                        "temperature_c": w_data.temperature_c,
                        "relative_humidity_pct": w_data.relative_humidity_pct,
                        "wind_speed_kmh": w_data.wind_speed_kmh,
                        "is_safe_to_spray": s_assess.is_safe_to_spray
                    }
                except Exception as w_err:
                    logger.warning(f"Could not load weather context: {w_err}")

        # 5. Hybrid RAG Search
        retrieval_results = rag_indexer.search(
            query=search_query,
            crop_filter=session.active_crop,
            language_filter=detected_lang,
            top_k=4
        )

        # 6. Fact Grounding & Response Synthesis
        grounded_res = AgriculturalGroundingEngine.synthesize_response(
            query=message,
            retrieval_results=retrieval_results,
            language=detected_lang,
            diagnostic_context=diag_context,
            weather_context=weather_context
        )

        # 7. Update Session Memory
        session.history.append(ChatMessage(role="user", content=message, language=detected_lang))
        session.history.append(ChatMessage(role="assistant", content=grounded_res.answer, language=detected_lang))

        # Truncate history to last 10 messages to maintain clean bounds
        if len(session.history) > 10:
            session.history = session.history[-10:]

        return {
            "session_id": session.session_id,
            "query": message,
            "language": detected_lang,
            "answer": grounded_res.answer,
            "key_recommendations": grounded_res.key_recommendations,
            "retrieved_sources": grounded_res.retrieved_sources,
            "is_grounded": grounded_res.is_grounded,
            "statutory_disclaimer": grounded_res.statutory_disclaimer,
            "active_crop": session.active_crop,
            "active_disease": session.active_disease
        }

    def _expand_query_with_history(self, current_msg: str, session: ChatSession) -> str:
        """Enriches follow-up questions with previous entity context if query is short or elliptical."""
        tokens = current_msg.split()
        # If short follow-up (e.g. "dosage?", "औषध काय?", "how to spray?")
        if len(tokens) <= 4 and session.active_disease:
            return f"{session.active_crop} {session.active_disease} {current_msg}"
        return f"{session.active_crop} {current_msg}"


rag_assistant = AgriculturalRAGAssistant()
