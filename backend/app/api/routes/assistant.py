"""
PikVaidya AI — Agricultural RAG Conversational Assistant Routes
==============================================================
Provides endpoints for interactive farmer Q&A grounded in verified ICAR/CIBRC knowledge:
1. POST /api/v1/assistant/chat   - Multi-turn conversational chat
2. POST /api/v1/assistant/query  - Direct RAG query
3. GET  /api/v1/assistant/chunks - Catalog of indexed knowledge chunks
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.services.rag.assistant import rag_assistant
from app.services.rag.indexer import rag_indexer
from app.services.rag.orchestrator import llm_orchestrator
from app.schemas.assistant import (
    ChatQueryRequest,
    ChatQueryResponse,
    KnowledgeChunkResponse,
    MultimodalChatRequest,
    MultimodalChatResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assistant", tags=["Agricultural RAG Assistant"])


@router.post(
    "/chat",
    response_model=ChatQueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Interactive Multilingual Agricultural Chat (Multi-turn RAG)",
    description=(
        "Answers farmer questions in Marathi (मराठी), Hindi (हिंदी), or English. "
        "Strictly grounded in verified ICAR/CIBRC agricultural packages with zero hallucination."
    ),
)
async def chat_with_assistant(
    request: ChatQueryRequest,
    db: Session = Depends(get_db),
) -> ChatQueryResponse:
    """Processes interactive farmer query with conversational memory and RAG grounding."""
    res = await rag_assistant.chat(
        message=request.message,
        session_id=request.session_id,
        crop=request.crop,
        diagnosis_id=request.diagnosis_id,
        farm_id=request.farm_id,
        preferred_language=request.preferred_language or request.language,
        diagnostic_context=request.diagnostic_context,
        weather_context=request.weather_context,
        db=db,
    )
    return ChatQueryResponse(**res)


@router.post(
    "/query",
    response_model=ChatQueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Direct Stateless Agronomic Query",
    description="Stateless single-turn query against the agricultural RAG index.",
)
async def query_assistant(
    request: ChatQueryRequest,
    db: Session = Depends(get_db),
) -> ChatQueryResponse:
    """Executes single-turn RAG retrieval and response synthesis."""
    res = await rag_assistant.chat(
        message=request.message,
        session_id=None,  # Clean stateless session
        crop=request.crop,
        diagnosis_id=request.diagnosis_id,
        farm_id=request.farm_id,
        preferred_language=request.preferred_language or request.language,
        diagnostic_context=request.diagnostic_context,
        weather_context=request.weather_context,
        db=db,
    )
    return ChatQueryResponse(**res)


@router.post(
    "/multimodal-chat",
    response_model=MultimodalChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Multimodal Conversational AI & LLM Agent Orchestrator",
    description=(
        "Processes multimodal farmer inputs (Text, Image, PDF, Voice) through the LLM Orchestrator, "
        "dispatching AI Model tools (foliar pathology), Weather tools (microclimate & spray safety), "
        "and RAG tools (ICAR/MPKV knowledge) with full session memory and database telemetry binding."
    ),
)
async def multimodal_chat(
    request: MultimodalChatRequest,
    db: Session = Depends(get_db),
) -> MultimodalChatResponse:
    """Dispatches multimodal input to specialized tools and synthesizes grounded agent response."""
    return await llm_orchestrator.orchestrate(request=request, db=db)


@router.get(
    "/chunks",
    response_model=List[KnowledgeChunkResponse],
    status_code=status.HTTP_200_OK,
    summary="List Indexed Knowledge Chunks",
    description="Inspect indexed agricultural documents, sections, and language translations.",
)
def list_knowledge_chunks(
    crop: Optional[str] = Query(None, description="Filter by crop (e.g. sugarcane)"),
    lang: Optional[str] = Query(None, description="Filter by language ('en', 'mr', 'hi')"),
    limit: int = Query(50, ge=1, le=200, description="Max chunks to return"),
) -> List[KnowledgeChunkResponse]:
    """Returns catalog of indexed pathology knowledge chunks."""
    if not rag_indexer.is_indexed:
        rag_indexer.build_index_from_seeds()

    results = []
    for c in rag_indexer.chunks:
        if crop and c.crop.lower() != crop.lower():
            continue
        if lang and c.language.lower() != lang.lower():
            continue

        results.append(
            KnowledgeChunkResponse(
                chunk_id=c.chunk_id,
                disease_id=c.disease_id,
                crop=c.crop,
                disease_name=c.disease_name,
                scientific_name=c.scientific_name,
                section=c.section,
                language=c.language,
                snippet=c.text[:200] + ("..." if len(c.text) > 200 else ""),
                metadata=c.metadata,
            )
        )
        if len(results) >= limit:
            break

    return results

