"""PikVaidya AI — Multimodal Conversational AI & LLM Orchestrator Tests.

Validates the complete 5-layer architecture:
1. Input Modalities: Text, Image, PDF, Voice
2. Conversational AI Language Detection
3. LLM Orchestration & Tool Dispatch (AI Model Tools, Weather Tools, RAG Engine)
4. Context & Memory Layer
5. Database Layer Binding
"""

import io
import base64
import numpy as np
from PIL import Image
import pytest
from starlette.testclient import TestClient
from sqlalchemy.orm import Session


def test_multimodal_text_query(client: TestClient):
    """Verifies text input triggers conversational AI and RAG knowledge tool."""
    payload = {
        "message": "उसावरील तांबेरा रोगाची लक्षणे काय आहेत?",
        "crop": "sugarcane",
        "language": "mr"
    }
    res = client.post("/api/v1/assistant/multimodal-chat", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["session_id"] is not None
    assert data["language"] == "mr"
    assert len(data["reply"]) > 20
    assert any(t["tool_name"] == "rag_knowledge_tool" for t in data["tools_invoked"])


def test_multimodal_weather_tool_dispatch(client: TestClient):
    """Verifies meteorological keywords trigger the Weather Risk tool."""
    payload = {
        "message": "आज हवामान कसे आहे आणि फवारणी करावी का?",
        "crop": "sugarcane",
        "latitude": 16.7050,
        "longitude": 74.2433,
        "language": "mr"
    }
    res = client.post("/api/v1/assistant/multimodal-chat", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["weather_result"] is not None
    assert "temperature_c" in data["weather_result"]
    assert "is_safe_to_spray" in data["weather_result"]
    assert any(t["tool_name"] == "weather_risk_tool" for t in data["tools_invoked"])


def test_multimodal_voice_transcript(client: TestClient):
    """Verifies spoken voice transcript is processed by the conversational AI orchestrator."""
    payload = {
        "voice_transcript": "गन्ने में लाल सड़न रोग की रोकथाम कैसे करें?",
        "crop": "sugarcane",
        "language": "hi"
    }
    res = client.post("/api/v1/assistant/multimodal-chat", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["language"] == "hi"
    assert "रोकथाम" in data["reply"] or len(data["reply"]) > 20
    assert any(t["tool_name"] == "rag_knowledge_tool" for t in data["tools_invoked"])


def test_multimodal_image_diagnosis_tool(client: TestClient):
    """Verifies foliar image input triggers AI Model Tool (Crop Diagnosis) + Weather + RAG."""
    # Create valid textured leaf image
    rng = np.random.RandomState(42)
    arr = rng.randint(40, 180, (250, 250, 3), dtype=np.uint8)
    arr[..., 1] = np.clip(arr[..., 1] + 50, 0, 255)
    img = Image.fromarray(arr)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    b64_img = base64.b64encode(buf.getvalue()).decode("utf-8")

    payload = {
        "message": "Check this foliar leaf symptom.",
        "image_base64": b64_img,
        "crop": "sugarcane",
        "latitude": 16.7050,
        "longitude": 74.2433
    }
    res = client.post("/api/v1/assistant/multimodal-chat", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["diagnostic_result"] is not None
    assert "disease_name_en" in data["diagnostic_result"]
    assert data["diagnostic_result"]["confidence"] > 0.0
    tool_names = [t["tool_name"] for t in data["tools_invoked"]]
    assert "crop_diagnosis_tool" in tool_names
    assert "weather_risk_tool" in tool_names
    assert "rag_knowledge_tool" in tool_names


def test_multimodal_pdf_document_tool(client: TestClient):
    """Verifies uploaded PDF document triggers the Document Analysis tool."""
    # Simple synthetic minimal PDF
    pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n4 0 obj\n<< /Length 55 >>\nstream\nBT /F1 12 Tf 72 712 Td (Soil Test Report: pH 7.2, Nitrogen Adequate) Tj ET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000216 00000 n \ntrailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n320\n%%EOF"
    b64_pdf = base64.b64encode(pdf_content).decode("utf-8")

    payload = {
        "message": "Please review this soil report.",
        "pdf_base64": b64_pdf,
        "pdf_filename": "soil_report.pdf",
        "crop": "sugarcane"
    }
    res = client.post("/api/v1/assistant/multimodal-chat", json=payload)
    assert res.status_code == 200
    data = res.json()
    tool_names = [t["tool_name"] for t in data["tools_invoked"]]
    assert "document_analysis_tool" in tool_names
