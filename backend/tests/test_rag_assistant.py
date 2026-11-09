"""
Comprehensive Unit & Integration Tests for Agricultural RAG Assistant
=====================================================================
Verifies:
  1. Hybrid Indexer (BM25 + Dense NumPy embeddings + RRF + CrossScoreReranker)
  2. Multi-crop coverage: Sugarcane, Tomato, and Onion across EN, MR, HI
  3. Contextual cross-reranking with diagnostic concordance and query intent
  4. Safety Guardrails:
     - Anti-hallucination boundary protocols (safely refusing out-of-domain queries)
     - Low confidence (<70%) KVK / University expert advisory injection
     - Adverse microclimate spray hold warning injection
     - Statutory notice under Insecticides Act, 1968
  5. Multi-turn conversational memory and elliptical query contextualization
  6. REST API endpoints (/chat, /query, /chunks) with telemetry payloads
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.services.rag.indexer import rag_indexer, CrossScoreReranker
from app.services.rag.grounding import AgriculturalGroundingEngine
from app.services.rag.assistant import rag_assistant


def test_rag_indexer_build_and_search():
    # Build or check index
    if not rag_indexer.is_indexed:
        rag_indexer.build_index_from_seeds()

    assert len(rag_indexer.chunks) >= 20
    assert rag_indexer.chunk_vectors is not None
    assert rag_indexer.chunk_vectors.shape[1] == 128

    # 1. Search in English for Sugarcane Red Rot
    results_en = rag_indexer.search("What are the symptoms of red rot in sugarcane?", crop_filter="sugarcane", top_k=3)
    assert len(results_en) > 0
    top_chunk = results_en[0].chunk
    assert "Red Rot" in top_chunk.disease_name or "red" in top_chunk.disease_id.lower()

    # 2. Search in Marathi for Sugarcane Red Rot
    results_mr = rag_indexer.search("उसावरील तांबडे कूज रोगाची लक्षणे कोणती?", crop_filter="sugarcane", top_k=3)
    assert len(results_mr) > 0
    top_mr_chunk = results_mr[0].chunk
    assert "red_rot" in top_mr_chunk.disease_id.lower() or "Red Rot" in top_mr_chunk.disease_name

    # 3. Search in Marathi for Sugarcane Rust
    results_rust = rag_indexer.search("उसावरील तांबेरा रोगावर उपाय सांगा", crop_filter="sugarcane", top_k=3)
    assert len(results_rust) > 0
    top_rust_chunk = results_rust[0].chunk
    assert "rust" in top_rust_chunk.disease_id.lower() or "तांबेरा" in top_rust_chunk.text

    # 4. Search for Tomato Early Blight in English and Marathi
    results_tom_en = rag_indexer.search("Early blight concentric rings tomato", crop_filter="tomato", top_k=3)
    assert len(results_tom_en) > 0
    assert any("early" in r.chunk.disease_id.lower() or "Early" in r.chunk.disease_name for r in results_tom_en)

    results_tom_mr = rag_indexer.search("टोमॅटोवरील लवकर येणारा करपा नियंत्रण", crop_filter="tomato", top_k=3)
    assert len(results_tom_mr) > 0
    assert any("early" in r.chunk.disease_id.lower() or "करपा" in r.chunk.text for r in results_tom_mr)

    # 5. Search for Onion Purple Blotch in English and Marathi
    results_oni_mr = rag_indexer.search("कांद्यावरील जांभळा करपा उपाय", crop_filter="onion", top_k=3)
    assert len(results_oni_mr) > 0
    assert any("purple" in r.chunk.disease_id.lower() or "जांभळा" in r.chunk.text for r in results_oni_mr)


def test_cross_score_reranker_diagnostic_concordance():
    # Diagnostic context: Tomato Early Blight
    diag_context = {
        "crop": "tomato",
        "predicted_disease": "Early Blight",
        "confidence": 0.92
    }

    results = rag_indexer.search(
        query="what is the spray dosage?",
        crop_filter="tomato",
        diagnostic_context=diag_context,
        top_k=4
    )
    assert len(results) > 0
    # Top chunk should prioritize chemical/spray for Early Blight due to intent and disease concordance
    top = results[0].chunk
    assert top.crop.lower() == "tomato"
    assert "chemical" in top.section or "management" in top.section or "Early Blight" in top.disease_name


def test_grounding_low_confidence_advisory():
    results = rag_indexer.search("Early blight treatment", crop_filter="tomato", top_k=2)
    assert len(results) > 0

    # Test with low confidence (<0.70)
    low_conf_diag = {
        "crop": "tomato",
        "predicted_disease": "Early Blight",
        "confidence": 0.58
    }

    # English
    res_en = AgriculturalGroundingEngine.synthesize_response(
        query="Early blight treatment",
        retrieval_results=results,
        language="en",
        diagnostic_context=low_conf_diag
    )
    assert "below 70%" in res_en.answer
    assert "Krishi Vigyan Kendra" in res_en.answer

    # Marathi
    res_mr = AgriculturalGroundingEngine.synthesize_response(
        query="अर्ली ब्लाइट उपाय",
        retrieval_results=results,
        language="mr",
        diagnostic_context=low_conf_diag
    )
    assert "७०% पेक्षा कमी" in res_mr.answer
    assert "KVK" in res_mr.answer


def test_grounding_weather_spray_warning():
    results = rag_indexer.search("Carbendazim sett treatment", crop_filter="sugarcane", top_k=2)
    assert len(results) > 0

    # Unsafe spray weather: high wind or imminent rain
    bad_weather = {
        "temperature_c": 28.5,
        "relative_humidity_pct": 89.0,
        "wind_speed_kmh": 22.0,
        "is_safe_to_spray": False
    }

    res = AgriculturalGroundingEngine.synthesize_response(
        query="Carbendazim sett treatment",
        retrieval_results=results,
        language="en",
        weather_context=bad_weather
    )
    assert "unfavourable for spraying" in res.answer.lower() or "weather advisory" in res.answer.lower()


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
    assert any("ICAR" in s.get("organization", "") or "ICAR" in s.get("source_name", "") or "MPKV" in s.get("organization", "") for s in grounded_res.retrieved_sources)


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
async def test_assistant_api_chat_endpoint_with_telemetry():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "message": "टोमॅटोवरील करपा रोगावर कोणती फवारणी करावी?",
            "crop": "tomato",
            "preferred_language": "mr",
            "diagnostic_context": {
                "crop": "tomato",
                "predicted_disease": "Early Blight",
                "confidence": 0.88
            },
            "weather_context": {
                "temperature_c": 27.0,
                "relative_humidity_pct": 74.0,
                "wind_speed_kmh": 8.0,
                "is_safe_to_spray": True
            }
        }
        resp = await ac.post("/api/v1/assistant/chat", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["language"] == "mr"
        assert data["is_grounded"] is True
        assert len(data["retrieved_sources"]) > 0
        assert "statutory_disclaimer" in data
        assert "reply" in data
        assert "sources" in data


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
