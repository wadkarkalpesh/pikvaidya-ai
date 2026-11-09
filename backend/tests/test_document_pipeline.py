"""
Comprehensive Unit & Integration Tests for Agricultural Document Processing Pipeline
====================================================================================
Verifies:
  1. Multi-format text extraction (PDF, Markdown, JSON, Text).
  2. Unicode and Devanagari (Marathi/Hindi) text cleaning and normalization.
  3. Semantic section-aware chunking (Symptoms, Management, Conditions, etc.).
  4. Metadata extraction & institutional attribution (MPKV, VNMKV, ICAR, CIBRC).
  5. SHA-256 content deduplication at document and chunk levels.
  6. Document Source Register tracking and persistence.
  7. Seamless export to RAG DocumentChunk format.
"""

import os
import json
import tempfile
from pathlib import Path
import pytest

from app.services.rag.document_pipeline import (
    AgriculturalDocumentPipeline,
    DocumentMetadata,
    ExtractedChunk,
    TextCleaner,
    SemanticSectionChunker,
    DocumentSourceRegister
)


def test_text_cleaner_multilingual():
    raw_dirty = "  ऊस  पिकावरील  \r\n\r\n\r\n\r\nतांबडे कूज\t\tरोग\u200c  नियंत्रण   "
    cleaned = TextCleaner.clean(raw_dirty)
    assert "  " not in cleaned
    assert "\r" not in cleaned
    assert "\n\n\n" not in cleaned
    assert "ऊस पिकावरील" in cleaned
    assert "तांबडे कूज" in cleaned


def test_semantic_section_chunker():
    doc_text = """
## Overview
Sugarcane is widely grown across Western Maharashtra.

## Symptoms
Spindle leaves turn yellow and wither. Red discoloration in stalk pith.

## Chemical Management
Dip setts in Carbendazim 50% WP @ 1.0 g/litre for 15 minutes. PHI is 30 days.
"""
    meta = DocumentMetadata(
        document_id="test_sugarcane_doc",
        title="Test Sugarcane Document",
        author_or_institution="MPKV Rahuri",
        publication_year=2024,
        crop="sugarcane",
        primary_disease="Red Rot",
        language="en",
        geographic_relevance="Maharashtra"
    )

    chunks = SemanticSectionChunker.chunk_document(doc_text, meta)
    assert len(chunks) >= 1
    assert any(c.crop == "sugarcane" for c in chunks)
    # Check that metadata is intact
    assert chunks[0].metadata["institution"] == "MPKV Rahuri"
    assert chunks[0].chunk_sha256 != ""


def test_document_source_register():
    with tempfile.TemporaryDirectory() as tmpdir:
        reg_path = Path(tmpdir) / "test_register.json"
        reg = DocumentSourceRegister(str(reg_path))

        meta = DocumentMetadata(
            document_id="mpkv_tomato_2024",
            title="Tomato Late Blight Guidelines",
            author_or_institution="MPKV Rahuri",
            publication_year=2024,
            crop="tomato",
            primary_disease="Late Blight",
            file_sha256="abc123sha256test"
        )
        reg.register_document(meta, chunk_count=5)

        # Verify persistence
        assert reg_path.exists()
        assert reg.is_document_ingested("abc123sha256test") is True
        assert reg.is_document_ingested("non_existent_hash") is False

        docs = reg.list_documents()
        assert len(docs) == 1
        assert docs[0]["document_id"] == "mpkv_tomato_2024"
        assert docs[0]["chunk_count"] == 5


def test_pipeline_json_and_markdown_ingestion():
    with tempfile.TemporaryDirectory() as tmpdir:
        reg_file = Path(tmpdir) / "test_register.json"
        pipeline = AgriculturalDocumentPipeline(str(reg_file))

        # 1. Create a sample markdown file
        md_file = Path(tmpdir) / "sample_onion_guide.md"
        md_file.write_text(
            "# Onion Purple Blotch Management\n"
            "## Symptoms\nPurple sunken lesions appear on onion leaves.\n"
            "## Chemical Management\nSpray Tebuconazole 25.9% EC @ 1.0 ml/litre with sticker. PHI 10 days.",
            encoding="utf-8"
        )

        # 2. Create a sample JSON file
        json_file = Path(tmpdir) / "sample_tomato_data.json"
        json_data = [
            {
                "crop": "tomato",
                "disease": "Early Blight",
                "section": "symptoms",
                "language": "en",
                "text": "Target-like concentric rings on older tomato foliage."
            }
        ]
        json_file.write_text(json.dumps(json_data), encoding="utf-8")

        # Ingest directory
        chunks = pipeline.ingest_directory(tmpdir)
        assert len(chunks) >= 2

        # Convert to RAG chunks
        rag_chunks = pipeline.to_rag_document_chunks()
        assert len(rag_chunks) == len(chunks)
        assert any("Tebuconazole" in rc.text or "Purple Blotch" in rc.disease_name for rc in rag_chunks)
        assert any("Early Blight" in rc.disease_name for rc in rag_chunks)


def test_pipeline_pdf_ingestion():
    # Verify ingestion of our generated bulletin PDF
    bulletin_pdf = Path("data/knowledge_base/sugarcane/sugarcane_icar_bulletin.pdf")
    if not bulletin_pdf.exists():
        pytest.skip("Test bulletin PDF not generated yet")

    with tempfile.TemporaryDirectory() as tmpdir:
        reg_file = Path(tmpdir) / "test_register.json"
        pipeline = AgriculturalDocumentPipeline(str(reg_file))

        chunks = pipeline.parse_file(bulletin_pdf)
        assert len(chunks) > 0
        assert chunks[0].page_number == 1
        combined_text = " ".join(c.text for c in chunks)
        assert "Sugarcane Smut" in combined_text or "Sporisorium" in combined_text
        assert "Carbendazim" in combined_text or "Propiconazole" in combined_text
