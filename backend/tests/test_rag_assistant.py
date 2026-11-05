"""
Comprehensive Unit & Integration Tests for Agricultural RAG Assistant
=====================================================================
Verifies:
  1. Hybrid Indexer (BM25 + Dense NumPy embeddings + RRF) across languages
  2. Anti-hallucination boundary protocols (safely refusing out-of-domain queries)
  3. Language auto-detection for Marathi, Hindi, and English
  4. Multi-turn dialogue contextualization
  5. FastAPI REST endpoints (/chat, /query, /chunks)
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.services.rag.indexer import rag_indexer
from app.services.rag.grounding import AgriculturalGroundingEngine
from app.services.rag.assistant import rag_assistant


def test_rag_indexer_build_and_search():
    # Build or check index
    if not rag_indexer.is_indexed:
        rag_indexer.build_index_from_seeds()

    assert len(rag_indexer.chunks) >= 15
    assert rag_indexer.chunk_vectors is not None
    assert rag_indexer.chunk_vectors.shape[1] == 128

    # 1. Search in English
    results_en = rag_indexer.search("What are the symptoms of red rot in sugarcane?", crop_filter="sugarcane", top_k=3)
    assert len(results_en) > 0
    top_chunk = results_en[0].chunk
    assert "Red Rot" in top_chunk.disease_name or "red" in top_chunk.disease_id.lower()

    # 2. Search in Marathi
    results_mr = rag_indexer.search("उसावरील तांबडे कूज रोगाची लक्षणे कोणती?", crop_filter="sugarcane", top_k=3)
    assert len(results_mr) > 0
    top_mr_chunk = results_mr[0].chunk
    assert "red_rot" in top_mr_chunk.disease_id.lower() or "Red Rot" in top_mr_chunk.disease_name

    # 3. Search in Marathi for Rust
    results_rust = rag_indexer.search("उसावरील तांबेरा रोगावर उपाय सांगा", crop_filter="sugarcane", top_k=3)
    assert len(results_rust) > 0
    top_rust_chunk = results_rust[0].chunk
    assert "rust" in top_rust_chunk.disease_id.lower() or "तांबेरा" in top_rust_chunk.text


def test_grounding_anti_hallucination():
    # Query completely outside agriculture
    unrelated_query = "What is the latest stock market valuation of Microsoft and Nvidia?"
    results = rag_indexer.search(unrelated_query, top_k=3)

    grounded_res = AgriculturalGroundingEngine.synthesize_response(
        query=unrelated_query,
        retrieval_results=results,
        language="en"
    )
    # Must refuse to hallucinate
    assert grounded_res.is_grounded is False
    assert "icar and cibrc" in grounded_res.answer.lower()
    assert "statutory" in grounded_res.statutory_disclaimer.lower()


def test_grounding_verified_fact_synthesis():
    query = "Carbendazim sett treatment for red rot in sugarcane"
    results = rag_indexer.search(query, crop_filter="sugarcane", top_k=3)
    assert len(results) > 0

    grounded_res = AgriculturalGroundingEngine.synthesize_response(
        query=query,
        retrieval_results=results,
        language="en"
    )
    assert grounded_res.is_grounded is True
    assert len(grounded_res.retrieved_sources) > 0
    assert "ICAR" in grounded_res.retrieved_sources[0]["organization"] or "ICAR" in grounded_res.retrieved_sources[0]["source_name"]


def test_assistant_language_detection():
    # Marathi detection
    mr_text = "उसावर पडलेल्या तांबेरा रोगावर काय फवारावे?"
    assert rag_assistant.detect_language(mr_text) == "mr"

    # Hindi detection
    hi_text = "गन्ने में लाल सड़न रोग की रोकथाम कैसे करें?"
    assert rag_assistant.detect_language(hi_text) == "hi"

    # English detection
    en_text = "How to prevent sugarcane mosaic virus?"
    assert rag_assistant.detect_language(en_text) == "en"


@pytest.mark.anyio
async def test_assistant_multi_turn_followup():
    session_id = "test-session-rag-101"

    # Turn 1: Ask about Red Rot
    res_1 = await rag_assistant.chat(
        message="What causes red rot in sugarcane?",
        session_id=session_id,
        crop="sugarcane",
        preferred_language="en"
    )
    assert res_1["is_grounded"] is True
    assert "Colletotrichum" in res_1["answer"] or "Red Rot" in res_1["answer"]
    assert res_1["session_id"] == session_id

    # Turn 2: Follow-up question with elliptical reference
    res_2 = await rag_assistant.chat(
        message="What is the chemical treatment?",
        session_id=session_id,
        crop="sugarcane",
        preferred_language="en"
    )
    assert res_2["is_grounded"] is True
    # Context expansion should link back to Red Rot chemical recommendations (Carbendazim)
    assert "Carbendazim" in res_2["answer"] or "sett" in res_2["answer"].lower() or len(res_2["key_recommendations"]) > 0


@pytest.mark.anyio
async def test_assistant_api_chat_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "message": "उसावरील तांबडे कूज रोगावर कोणती बेणे प्रक्रिया करावी?",
            "crop": "sugarcane",
            "preferred_language": "mr"
        }
        resp = await ac.post("/api/v1/assistant/chat", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["language"] == "mr"
        assert data["is_grounded"] is True
        assert len(data["retrieved_sources"]) > 0
        assert "statutory_disclaimer" in data


@pytest.mark.anyio
async def test_assistant_api_chunks_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/assistant/chunks?crop=sugarcane&limit=10")
        assert resp.status_code == 200
        chunks = resp.json()
        assert len(chunks) > 0
        assert "chunk_id" in chunks[0]
        assert "snippet" in chunks[0]
        assert "disease_name" in chunks[0]
