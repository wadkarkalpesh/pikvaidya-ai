"""PikVaidya AI — Multimodal Conversational AI & LLM Orchestrator.
==================================================================
Orchestrates multimodal inputs (Text, Image, PDF, Voice) across three specialized
tool subsystems:
  1. AI MODEL TOOLS     -> Crop foliar diagnosis, confidence calibration, Grad-CAM.
  2. WEATHER TOOLS      -> Real-time microclimate, spray windows, epidemiological risk.
  3. RAG ENGINE         -> FAISS dense vector search over ICAR & university packages of practice.

Maintains multi-turn context, resolves ambiguous references, and interfaces directly
with the database layer for farmer, farm, and history telemetry.
"""

import io
import time
import base64
import logging
from typing import Dict, List, Optional, Any, Tuple
from PIL import Image
from starlette.datastructures import UploadFile
from sqlalchemy.orm import Session

from app.services.rag.assistant import rag_assistant, ChatSession, ChatMessage
from app.services.rag.grounding import AgriculturalGroundingEngine
from app.services.rag.indexer import rag_indexer
from app.services.segmentation_service import segmentation_service
from app.services.diagnostic_service import diagnostic_service
from app.services.weather_service import weather_service
from app.services.weather.feature_engineer import weather_feature_engineer
from app.services.weather.locations import resolve_location
from app.models.diagnosis import Diagnosis
from app.models.farm import Farm
from app.schemas.assistant import (
    MultimodalChatRequest,
    MultimodalChatResponse,
    ToolExecutionTrace,
)

logger = logging.getLogger(__name__)


class LLMToolOrchestrator:
    """Autonomous agentic orchestrator for multimodal agricultural inquiries."""

    def __init__(self):
        self.supported_crops = ["sugarcane", "tomato", "onion"]

    async def execute_crop_diagnosis_tool(
        self,
        image_bytes: bytes,
        crop: str,
        filename: str = "foliar_scan.jpg",
    ) -> Tuple[Dict[str, Any], ToolExecutionTrace]:
        """Tool 1: Ingests foliar image, validates quality, and executes deep neural diagnosis."""
        start_t = time.perf_counter()
        try:
            # 1. Image Quality Gauntlet
            pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            is_valid, failure_reason, quality_metrics = segmentation_service.validate_image_quality(pil_img)
            if not is_valid:
                duration_ms = (time.perf_counter() - start_t) * 1000.0
                trace = ToolExecutionTrace(
                    tool_name="crop_diagnosis_tool",
                    status="FAILED",
                    summary=f"Quality check rejected image: {failure_reason}",
                    latency_ms=round(duration_ms, 2),
                )
                return {"error": failure_reason, "quality": quality_metrics}, trace

            # 2. Execute Neural Diagnostic Pipeline
            upload_file = UploadFile(filename=filename, file=io.BytesIO(image_bytes))
            pred = await diagnostic_service.run_standalone_prediction(
                file=upload_file,
                crop=crop,
                generate_gradcam=True,
            )
            duration_ms = (time.perf_counter() - start_t) * 1000.0

            predicted_class = pred.predicted_class
            mr_name = pred.details.get("disease_name_mr", predicted_class) if pred.details else predicted_class
            result = {
                "crop": pred.crop,
                "disease_name_en": predicted_class,
                "disease_name_mr": mr_name,
                "confidence": pred.confidence,
                "severity": pred.details.get("severity", "MODERATE") if pred.details else "MODERATE",
                "is_healthy": "healthy" in predicted_class.lower(),
                "heatmap_url": pred.heatmap_path,
                "top_predictions": pred.class_scores,
            }
            trace = ToolExecutionTrace(
                tool_name="crop_diagnosis_tool",
                status="SUCCESS",
                summary=f"Diagnosed {predicted_class} ({mr_name}) with {round(pred.confidence * 100, 1)}% confidence",
                latency_ms=round(duration_ms, 2),
            )
            return result, trace
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_t) * 1000.0
            logger.error("Crop diagnosis tool error: %s", exc)
            trace = ToolExecutionTrace(
                tool_name="crop_diagnosis_tool",
                status="FAILED",
                summary=f"Inference error: {str(exc)}",
                latency_ms=round(duration_ms, 2),
            )
            return {"error": str(exc)}, trace

    async def execute_weather_risk_tool(
        self,
        crop: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        district: Optional[str] = None,
        disease_name: Optional[str] = None,
        farm_id: Optional[int] = None,
        db: Optional[Session] = None,
    ) -> Tuple[Dict[str, Any], ToolExecutionTrace]:
        """Tool 2: Ingests farm GPS, district, or in-situ IoT telemetry, evaluates microclimate, and computes epidemiological risk."""
        start_t = time.perf_counter()
        try:
            # 1. Check for live in-situ IoT hardware node if farm_id is provided
            insitu_telemetry = None
            if db and farm_id:
                try:
                    from app.services.iot_service import iot_service
                    insitu_telemetry = iot_service.get_latest_farm_telemetry(db, farm_id)
                    # Verify telemetry is live (within last 2 hours)
                    if insitu_telemetry:
                        r_ts = insitu_telemetry.timestamp
                        if r_ts.tzinfo is None:
                            r_ts = r_ts.replace(tzinfo=timezone.utc)
                        age_secs = (datetime.now(timezone.utc) - r_ts).total_seconds()
                        if age_secs > 7200:
                            insitu_telemetry = None
                except Exception as iot_err:
                    logger.debug("Could not query in-situ IoT telemetry: %s", iot_err)

            # Resolve coordinates
            lat, lon, loc_name = 16.7050, 74.2433, "Kolhapur, Maharashtra"
            if latitude and longitude:
                lat, lon = latitude, longitude
                loc_name = f"Coordinates ({round(lat, 3)}, {round(lon, 3)})"
            elif district:
                loc = resolve_location(location_query=district)
                if loc:
                    lat, lon, loc_name = loc.latitude, loc.longitude, loc.name

            # Fetch weather telemetry
            w_data = await weather_service.get_current_weather(lat, lon)
            s_assess = weather_service.assess_spray_suitability(w_data)

            # Evaluate disease conduciveness from microclimate
            temp_eval = insitu_telemetry.ambient_temperature_c if insitu_telemetry else w_data.temperature_c
            rh_eval = insitu_telemetry.ambient_humidity_pct if insitu_telemetry else w_data.relative_humidity_pct
            wind_eval = insitu_telemetry.wind_speed_2m_kmh if insitu_telemetry else w_data.wind_speed_kmh
            spray_safe = insitu_telemetry.spray_window_safe if insitu_telemetry else s_assess.is_safe_to_spray

            is_conducive = (rh_eval > 75.0) and (20.0 <= temp_eval <= 32.0)
            if insitu_telemetry and (insitu_telemetry.leaf_wetness_active or insitu_telemetry.leaf_wetness_minutes >= 15):
                is_conducive = True

            risk_tier = "CRITICAL" if (is_conducive and not spray_safe) else ("HIGH" if is_conducive else ("MODERATE" if rh_eval > 60.0 else "LOW"))
            cond_score = 0.92 if (insitu_telemetry and insitu_telemetry.leaf_wetness_active) else (0.88 if is_conducive else (0.55 if rh_eval > 60.0 else 0.25))

            spray_rec = "Optimal spray conditions"
            if hasattr(s_assess, "advisory_recommendation") and isinstance(s_assess.advisory_recommendation, dict):
                spray_rec = s_assess.advisory_recommendation.get("en", "Optimal spray conditions")
            elif hasattr(s_assess, "summary") and isinstance(s_assess.summary, dict):
                spray_rec = s_assess.summary.get("en", "Optimal spray conditions")

            duration_ms = (time.perf_counter() - start_t) * 1000.0
            result = {
                "location": f"Farm #{farm_id} In-Situ IoT" if insitu_telemetry else loc_name,
                "temperature_c": temp_eval,
                "relative_humidity_pct": rh_eval,
                "wind_speed_kmh": wind_eval,
                "is_safe_to_spray": spray_safe,
                "spray_recommendation": spray_rec,
                "conduciveness_score": cond_score,
                "risk_tier": risk_tier,
                "is_insitu_iot": insitu_telemetry is not None,
                "leaf_wetness_minutes": insitu_telemetry.leaf_wetness_minutes if insitu_telemetry else None,
                "soil_moisture_pct": insitu_telemetry.soil_moisture_10cm_pct if insitu_telemetry else None,
            }

            summary_msg = (
                f"In-Situ IoT Node ({insitu_telemetry.device_id}): {temp_eval}°C, {rh_eval}% RH, Leaf Wetness: {insitu_telemetry.leaf_wetness_minutes}m. Spray: {'SAFE' if spray_safe else 'HOLD'}"
                if insitu_telemetry else
                f"Microclimate evaluated: {w_data.temperature_c}°C, {w_data.relative_humidity_pct}% RH. Spray status: {'SAFE' if s_assess.is_safe_to_spray else 'HOLD'}"
            )
            trace = ToolExecutionTrace(
                tool_name="weather_risk_tool",
                status="SUCCESS",
                summary=summary_msg,
                latency_ms=round(duration_ms, 2),
            )
            return result, trace
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_t) * 1000.0
            logger.error("Weather risk tool error: %s", exc)
            trace = ToolExecutionTrace(
                tool_name="weather_risk_tool",
                status="FAILED",
                summary=f"Weather retrieval error: {str(exc)}",
                latency_ms=round(duration_ms, 2),
            )
            return {"error": str(exc)}, trace

    async def execute_rag_knowledge_tool(
        self,
        query: str,
        crop: str,
        language: str,
        diagnostic_context: Optional[Dict[str, Any]] = None,
        weather_context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Dict[str, Any], ToolExecutionTrace]:
        """Tool 3: Ingests contextual query and retrieves verified ICAR/CIBRC knowledge chunks."""
        start_t = time.perf_counter()
        try:
            results = rag_indexer.search(
                query=query,
                crop_filter=crop,
                language_filter=language,
                diagnostic_context=diagnostic_context,
                weather_context=weather_context,
                top_k=4,
            )
            grounded = AgriculturalGroundingEngine.synthesize_response(
                query=query,
                retrieval_results=results,
                language=language,
                diagnostic_context=diagnostic_context,
                weather_context=weather_context,
            )
            duration_ms = (time.perf_counter() - start_t) * 1000.0
            result = {
                "answer": grounded.answer,
                "key_recommendations": grounded.key_recommendations,
                "sources": grounded.retrieved_sources,
                "is_grounded": grounded.is_grounded,
                "statutory_disclaimer": grounded.statutory_disclaimer,
            }
            trace = ToolExecutionTrace(
                tool_name="rag_knowledge_tool",
                status="SUCCESS",
                summary=f"Retrieved {len(grounded.retrieved_sources)} authoritative citations from ICAR/MPKV knowledge base",
                latency_ms=round(duration_ms, 2),
            )
            return result, trace
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_t) * 1000.0
            logger.error("RAG knowledge tool error: %s", exc)
            trace = ToolExecutionTrace(
                tool_name="rag_knowledge_tool",
                status="FAILED",
                summary=f"Retrieval error: {str(exc)}",
                latency_ms=round(duration_ms, 2),
            )
            return {"error": str(exc)}, trace

    def execute_document_analysis_tool(
        self,
        pdf_bytes: bytes,
        filename: str = "document.pdf",
    ) -> Tuple[Dict[str, Any], ToolExecutionTrace]:
        """Tool 4: Parses uploaded PDF bulletin, laboratory report, or extension advisory."""
        start_t = time.perf_counter()
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
            text_pages = [page.extract_text() or "" for page in reader.pages]
            full_text = "\n".join(text_pages).strip()
            summary = full_text[:400] + ("..." if len(full_text) > 400 else "")

            duration_ms = (time.perf_counter() - start_t) * 1000.0
            trace = ToolExecutionTrace(
                tool_name="document_analysis_tool",
                status="SUCCESS",
                summary=f"Extracted {len(reader.pages)} pages ({len(full_text)} characters) from {filename}",
                latency_ms=round(duration_ms, 2),
            )
            return {"num_pages": len(reader.pages), "text": full_text, "summary": summary}, trace
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_t) * 1000.0
            logger.error("Document analysis tool error: %s", exc)
            trace = ToolExecutionTrace(
                tool_name="document_analysis_tool",
                status="FAILED",
                summary=f"PDF extraction error: {str(exc)}",
                latency_ms=round(duration_ms, 2),
            )
            return {"error": str(exc)}, trace

    async def orchestrate(
        self,
        request: MultimodalChatRequest,
        db: Optional[Session] = None,
    ) -> MultimodalChatResponse:
        """Central LLM Agent Orchestrator: Dispatches multimodal inputs to tools and synthesizes unified response."""
        session: ChatSession = rag_assistant.get_or_create_session(request.session_id)
        active_crop = request.crop.lower().strip()
        if active_crop in self.supported_crops:
            session.active_crop = active_crop

        # 1. Resolve Voice Transcript or Text Message
        effective_message = (request.message or request.voice_transcript or "").strip()
        if not effective_message and request.image_base64:
            effective_message = f"Please analyze this {session.active_crop} foliar leaf photo."
        elif not effective_message and request.pdf_base64:
            effective_message = "Please analyze this uploaded agricultural document."

        # Detect Language
        detected_lang = rag_assistant.detect_language(
            effective_message, fallback_lang=request.language or "en"
        )

        tools_invoked: List[ToolExecutionTrace] = []
        diag_result: Optional[Dict[str, Any]] = None
        weather_result: Optional[Dict[str, Any]] = None

        # ----------------------------------------------------------------------
        # Modality Branch 1: PDF Document Ingestion
        # ----------------------------------------------------------------------
        doc_context = ""
        if request.pdf_base64:
            try:
                pdf_raw = base64.b64decode(request.pdf_base64)
                doc_data, doc_trace = self.execute_document_analysis_tool(
                    pdf_bytes=pdf_raw, filename=request.pdf_filename or "uploaded.pdf"
                )
                tools_invoked.append(doc_trace)
                if "text" in doc_data:
                    doc_context = f"\n[Extracted Document Context]: {doc_data['text'][:1200]}\n"
            except Exception as e:
                logger.warning("Could not decode PDF base64: %s", e)

        # ----------------------------------------------------------------------
        # Modality Branch 2: Image Foliar Diagnosis (Single & Multiple Images)
        # ----------------------------------------------------------------------
        all_images = []
        if request.image_base64:
            all_images.append((request.image_base64, request.image_filename or "foliar_scan.jpg"))
        if getattr(request, "images_base64", None):
            for idx, img_b64 in enumerate(request.images_base64):
                all_images.append((img_b64, f"foliar_scan_{idx+1}.jpg"))

        diag_results: List[Dict[str, Any]] = []
        for img_b64, fname in all_images:
            try:
                img_raw = base64.b64decode(img_b64)
                diag_data, diag_trace = await self.execute_crop_diagnosis_tool(
                    image_bytes=img_raw,
                    crop=session.active_crop,
                    filename=fname,
                )
                tools_invoked.append(diag_trace)
                if "disease_name_en" in diag_data:
                    diag_results.append(diag_data)
                    if not diag_result or diag_data.get("confidence", 0) > diag_result.get("confidence", 0):
                        diag_result = diag_data
                        session.active_disease = diag_data["disease_name_en"]
            except Exception as e:
                logger.warning("Could not decode image base64: %s", e)

        # ----------------------------------------------------------------------
        # Tool Dispatch 2: Weather & Microclimate Risk Tool
        # ----------------------------------------------------------------------
        # Triggered if image uploaded, or user explicitly asks about weather/spray, or GPS supplied
        weather_keywords = {"weather", "spray", "rain", "temperature", "humidity", "हवामान", "फवारणी", "पाऊस", "तापमान", "मौसम", "छिड़काव"}
        msg_words = set(effective_message.lower().split())
        needs_weather = bool(len(all_images) > 0 or (msg_words & weather_keywords) or request.farm_id or request.latitude)

        if needs_weather:
            lat = request.latitude or session.latitude
            lon = request.longitude or session.longitude
            w_data, w_trace = await self.execute_weather_risk_tool(
                crop=session.active_crop,
                latitude=lat,
                longitude=lon,
                district=getattr(request, "district", None) or getattr(session, "district", None),
                disease_name=session.active_disease,
                farm_id=request.farm_id or getattr(session, "farm_id", None),
                db=db,
            )
            tools_invoked.append(w_trace)
            if "temperature_c" in w_data:
                weather_result = w_data

        # ----------------------------------------------------------------------
        # Tool Dispatch 3: RAG Knowledge Base Retrieval
        # ----------------------------------------------------------------------
        rag_query = f"{effective_message} {doc_context}".strip()
        rag_data, rag_trace = await self.execute_rag_knowledge_tool(
            query=rag_query,
            crop=session.active_crop,
            language=detected_lang,
            diagnostic_context=diag_result,
            weather_context=weather_result,
        )
        tools_invoked.append(rag_trace)

        # ----------------------------------------------------------------------
        # Multi-Tool Synthesis & Grounding
        # ----------------------------------------------------------------------
        synthesized_reply = rag_data.get("answer", "")

        # Prepend image diagnosis findings if foliar tool succeeded
        if diag_result and not diag_result.get("error"):
            disease_display = diag_result["disease_name_mr"] if detected_lang == "mr" else diag_result["disease_name_en"]
            conf_pct = round(diag_result["confidence"] * 100, 1)
            if detected_lang == "mr":
                prefix = f"📸 **चित्र विश्लेषण निष्कर्ष:** ऊस/पिकाच्या पानावर **{disease_display}** ची लक्षणे आढळली आहेत (विश्वासार्हता: {conf_pct}%).\n\n"
            elif detected_lang == "hi":
                prefix = f"📸 **चित्र विश्लेषण परिणाम:** पत्ती पर **{disease_display}** के लक्षण पाए गए हैं (सटीकता: {conf_pct}%).\n\n"
            else:
                prefix = f"📸 **Visual Diagnosis:** Detected foliar symptoms of **{disease_display}** with {conf_pct}% confidence.\n\n"
            synthesized_reply = prefix + synthesized_reply

        # Append microclimate spray safety advisory
        if weather_result and not weather_result.get("error"):
            is_safe = weather_result.get("is_safe_to_spray", False)
            spray_status = "✅ फवारणीसाठी योग्य" if (is_safe and detected_lang == "mr") else ("❌ फवारणी टाळा (प्रतिकूल हवामान)" if detected_lang == "mr" else ("✅ Safe to Spray" if is_safe else "❌ Avoid Spraying (Adverse Weather)"))
            weather_note = f"\n\n🌦️ **हवामान व फवारणी सल्ला ({weather_result.get('location')}):** {spray_status} | तापमान: {weather_result.get('temperature_c')}°C, आर्द्रता: {weather_result.get('relative_humidity_pct')}%" if detected_lang == "mr" else f"\n\n🌦️ **Microclimate Advisory ({weather_result.get('location')}):** {spray_status} | Temp: {weather_result.get('temperature_c')}°C, RH: {weather_result.get('relative_humidity_pct')}%"
            synthesized_reply += weather_note

        # Update Session Memory
        session.history.append(ChatMessage(role="user", content=effective_message, language=detected_lang))
        session.history.append(ChatMessage(role="assistant", content=synthesized_reply, language=detected_lang))

        return MultimodalChatResponse(
            session_id=session.session_id,
            query=effective_message,
            language=detected_lang,
            reply=synthesized_reply,
            answer=synthesized_reply,
            tools_invoked=tools_invoked,
            diagnostic_result=diag_result,
            diagnostic_results=diag_results,
            weather_result=weather_result,
            sources=rag_data.get("sources", []),
            retrieved_sources=rag_data.get("sources", []),
            key_recommendations=rag_data.get("key_recommendations", []),
            is_grounded=rag_data.get("is_grounded", True),
            statutory_disclaimer=rag_data.get("statutory_disclaimer", "Consult state agricultural extension authorities before applying chemical fungicides."),
            active_crop=session.active_crop,
            active_disease=session.active_disease,
        )


llm_orchestrator = LLMToolOrchestrator()
