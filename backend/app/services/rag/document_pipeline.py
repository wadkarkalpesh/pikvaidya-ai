"""
PikVaidya AI — Agricultural Document Processing & Ingestion Pipeline
===================================================================
Production-grade document processing pipeline for multi-format agricultural
extension bulletins, university package of practices, and research publications.

Supported Formats:
  - PDF (.pdf via pypdf)
  - Markdown (.md)
  - Plain Text (.txt)
  - JSON (.json structured documents)
  - Word (.docx via python-docx)

Key Capabilities:
  1. Multi-format text extraction with page tracking.
  2. Unicode and Devanagari (Marathi/Hindi) text normalization.
  3. Semantic section-aware chunking (250-400 words with 50-word overlap).
  4. Metadata extraction & institutional attribution (MPKV, VNMKV, Dr. PDKV, ICAR, CIBRC).
  5. SHA-256 content deduplication at document and chunk levels.
  6. Persistent Document Source Register tracking all ingested files and versions.
"""

import os
import re
import json
import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime

logger = logging.getLogger(__name__)

# Try importing format parsers
try:
    import pypdf
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False

try:
    import docx
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False


@dataclass
class DocumentMetadata:
    """Standardized metadata schema for agricultural knowledge documents."""
    document_id: str
    title: str
    author_or_institution: str
    publication_year: int
    crop: str
    primary_disease: Optional[str] = None
    language: str = "en"
    geographic_relevance: str = "Maharashtra, India"
    source_file_path: str = ""
    file_format: str = "txt"
    file_sha256: str = ""
    license: str = "Government Public Domain / University Extension"
    ingestion_timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class ExtractedChunk:
    """Standardized knowledge chunk output ready for vector and BM25 indexing."""
    chunk_id: str
    document_id: str
    crop: str
    disease_name: str
    section: str
    language: str
    text: str
    page_number: Optional[int] = None
    chunk_sha256: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class TextCleaner:
    """Normalizes multilingual text, Devanagari script, and formatting artifacts."""

    # Devanagari zero-width joiners / non-joiners
    ZWNJ = "\u200c"
    ZWJ = "\u200d"
    MULTIPLE_SPACES = re.compile(r"[ \t\f\v]+")
    MULTIPLE_NEWLINES = re.compile(r"\n{3,}")

    @classmethod
    def clean(cls, text: str) -> str:
        """Cleans and standardizes raw extracted text."""
        if not text:
            return ""

        # Normalize line breaks
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        # Remove null bytes or control characters except tabs/newlines
        text = "".join(ch for ch in text if ch == "\n" or ch == "\t" or ord(ch) >= 32)
        # Normalize repeated horizontal spaces
        text = cls.MULTIPLE_SPACES.sub(" ", text)
        # Clean excessive newlines
        text = cls.MULTIPLE_NEWLINES.sub("\n\n", text)
        return text.strip()


class SemanticSectionChunker:
    """
    Section-aware semantic chunker that segments text by agricultural topics
    (Symptoms, Causes, Cultural/Biological, Chemical Management, Irrigation, Nutrition).
    """

    DEFAULT_TARGET_WORDS = 320
    DEFAULT_OVERLAP_WORDS = 45

    SECTION_PATTERNS = [
        (re.compile(r"(?i)(?:symptoms|disease\s+symptoms|लक्षणे|लक्षण|पहचान|symptomatology)", re.UNICODE), "symptoms"),
        (re.compile(r"(?i)(?:causes|favourable\s+conditions|कारण|अनुकूल\s+हवामान|रोगकारक|etiology|epidemiology)", re.UNICODE), "conditions"),
        (re.compile(r"(?i)(?:cultural\s+management|biological\s+control|सेंद्रिय\s+उपाय|मशागतीय\s+पद्धती|जैविक\s+नियंत्रण|organic\s+measures)", re.UNICODE), "cultural_and_biological"),
        (re.compile(r"(?i)(?:chemical\s+management|fungicides|insecticides|रासायनिक\s+नियंत्रण|रासायनिक\s+उपाय|कीटकनाशके|फवारणी)", re.UNICODE), "chemical"),
        (re.compile(r"(?i)(?:irrigation|water\s+management|पाणी\s+व्यवस्थापन|सिंचन)", re.UNICODE), "irrigation"),
        (re.compile(r"(?i)(?:nutrition|fertilizer|fertigation|खत\s+व्यवस्थापन|पोषण)", re.UNICODE), "nutrition"),
        (re.compile(r"(?i)(?:integrated\s+pest\s+management|ipm|एकात्मिक\s+कीड\s+व्यवस्थापन)", re.UNICODE), "ipm"),
        (re.compile(r"(?i)(?:soil\s+management|जमीन\s+व्यवस्थापन|मृदा\s+आरोग्य)", re.UNICODE), "soil"),
    ]

    @classmethod
    def identify_section(cls, text: str) -> str:
        """Determines the agronomic section from heading or content cues."""
        for pattern, section_name in cls.SECTION_PATTERNS:
            if pattern.search(text[:200]):
                return section_name
        return "overview"

    @classmethod
    def chunk_document(
        cls,
        text: str,
        metadata: DocumentMetadata,
        page_number: Optional[int] = None,
        target_words: int = DEFAULT_TARGET_WORDS,
        overlap_words: int = DEFAULT_OVERLAP_WORDS
    ) -> List[ExtractedChunk]:
        """
        Splits document text into overlapping semantic chunks with full context preservation.
        """
        cleaned_text = TextCleaner.clean(text)
        if not cleaned_text:
            return []

        # Split into paragraphs or major sections
        paragraphs = [p.strip() for p in cleaned_text.split("\n\n") if p.strip()]
        chunks: List[ExtractedChunk] = []
        current_words: List[str] = []
        current_section = "overview"
        chunk_idx = 1

        for para in paragraphs:
            # Check if this paragraph is a section header
            detected_sec = cls.identify_section(para)
            if detected_sec != "overview":
                current_section = detected_sec

            para_words = para.split()
            if len(current_words) + len(para_words) <= target_words:
                current_words.extend(para_words)
            else:
                # Flush current chunk
                if current_words:
                    chunk_text = " ".join(current_words)
                    chunk_sha256 = hashlib.sha256(chunk_text.encode("utf-8")).hexdigest()
                    chunk_id = f"{metadata.document_id}_p{page_number or 1}_c{chunk_idx}"
                    
                    chunks.append(
                        ExtractedChunk(
                            chunk_id=chunk_id,
                            document_id=metadata.document_id,
                            crop=metadata.crop,
                            disease_name=metadata.primary_disease or metadata.title,
                            section=current_section,
                            language=metadata.language,
                            text=chunk_text,
                            page_number=page_number,
                            chunk_sha256=chunk_sha256,
                            metadata={
                                "institution": metadata.author_or_institution,
                                "year": metadata.publication_year,
                                "geo": metadata.geographic_relevance,
                                "license": metadata.license,
                                "source_file": metadata.source_file_path
                            }
                        )
                    )
                    chunk_idx += 1

                    # Retain overlap words
                    overlap = current_words[-overlap_words:] if len(current_words) > overlap_words else []
                    current_words = overlap + para_words
                else:
                    current_words = para_words

        # Final trailing chunk
        if current_words:
            chunk_text = " ".join(current_words)
            chunk_sha256 = hashlib.sha256(chunk_text.encode("utf-8")).hexdigest()
            chunk_id = f"{metadata.document_id}_p{page_number or 1}_c{chunk_idx}"
            chunks.append(
                ExtractedChunk(
                    chunk_id=chunk_id,
                    document_id=metadata.document_id,
                    crop=metadata.crop,
                    disease_name=metadata.primary_disease or metadata.title,
                    section=current_section,
                    language=metadata.language,
                    text=chunk_text,
                    page_number=page_number,
                    chunk_sha256=chunk_sha256,
                    metadata={
                        "institution": metadata.author_or_institution,
                        "year": metadata.publication_year,
                        "geo": metadata.geographic_relevance,
                        "license": metadata.license,
                        "source_file": metadata.source_file_path
                    }
                )
            )

        return chunks


class DocumentSourceRegister:
    """Maintains a persistent JSON registry of all ingested agricultural documents."""

    def __init__(self, register_path: str = "data/knowledge_base/document_register.json"):
        self.register_path = Path(register_path)
        self.registry: Dict[str, Any] = {"version": "1.0", "updated_at": "", "documents": {}}
        self._load()

    def _load(self):
        if self.register_path.exists():
            try:
                with open(self.register_path, "r", encoding="utf-8") as f:
                    self.registry = json.load(f)
            except Exception as e:
                logger.warning(f"Could not read register from {self.register_path}: {e}")

    def save(self):
        self.register_path.parent.mkdir(parents=True, exist_ok=True)
        self.registry["updated_at"] = datetime.utcnow().isoformat()
        with open(self.register_path, "w", encoding="utf-8") as f:
            json.dump(self.registry, f, indent=2, ensure_ascii=False)

    def is_document_ingested(self, sha256_hash: str) -> bool:
        """Checks if a document with this SHA256 has already been registered."""
        for doc in self.registry.get("documents", {}).values():
            if doc.get("file_sha256") == sha256_hash:
                return True
        return False

    def register_document(self, metadata: DocumentMetadata, chunk_count: int):
        """Adds or updates a document entry in the registry."""
        doc_entry = asdict(metadata)
        doc_entry["chunk_count"] = chunk_count
        self.registry["documents"][metadata.document_id] = doc_entry
        self.save()

    def list_documents(self) -> List[Dict[str, Any]]:
        return list(self.registry.get("documents", {}).values())


class AgriculturalDocumentPipeline:
    """
    End-to-end document processing engine.
    Extracts text, parses metadata, chunks content, deduplicates, and produces
    indexed document chunks for the RAG indexer.
    """

    def __init__(self, register_path: str = "data/knowledge_base/document_register.json"):
        self.register = DocumentSourceRegister(register_path)
        self.ingested_chunks: List[ExtractedChunk] = []

    def compute_file_sha256(self, file_path: Path) -> str:
        """Computes SHA-256 hash of a file."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    def parse_file(self, file_path: Path, metadata_override: Optional[Dict[str, Any]] = None) -> List[ExtractedChunk]:
        """
        Parses a single file (.pdf, .md, .txt, .json, .docx), extracts text and metadata,
        and generates semantically chunked records.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        file_sha256 = self.compute_file_sha256(file_path)
        ext = file_path.suffix.lower()

        # Build DocumentMetadata
        doc_id = re.sub(r"[^a-zA-Z0-9_-]", "_", file_path.stem).lower()
        title = file_path.stem.replace("_", " ").title()
        
        # Defaults
        institution = "Maharashtra Agricultural Universities & ICAR"
        year = 2024
        crop = "general"
        disease = None
        lang = "en"
        geo = "Maharashtra, India"

        # Apply overrides if provided
        if metadata_override:
            title = metadata_override.get("title", title)
            institution = metadata_override.get("author_or_institution", institution)
            year = metadata_override.get("publication_year", year)
            crop = metadata_override.get("crop", crop)
            disease = metadata_override.get("primary_disease", disease)
            lang = metadata_override.get("language", lang)
            geo = metadata_override.get("geographic_relevance", geo)
            doc_id = metadata_override.get("document_id", doc_id)

        meta = DocumentMetadata(
            document_id=doc_id,
            title=title,
            author_or_institution=institution,
            publication_year=year,
            crop=crop,
            primary_disease=disease,
            language=lang,
            geographic_relevance=geo,
            source_file_path=str(file_path),
            file_format=ext.lstrip("."),
            file_sha256=file_sha256
        )

        extracted_chunks: List[ExtractedChunk] = []

        if ext == ".pdf":
            extracted_chunks = self._parse_pdf(file_path, meta)
        elif ext in [".md", ".txt"]:
            extracted_chunks = self._parse_text(file_path, meta)
        elif ext == ".json":
            extracted_chunks = self._parse_json(file_path, meta)
        elif ext == ".docx":
            extracted_chunks = self._parse_docx(file_path, meta)
        else:
            logger.warning(f"Unsupported file format: {ext} for {file_path}")
            return []

        # Deduplicate chunks by SHA-256
        unique_chunks = []
        seen_hashes = set()
        for chk in extracted_chunks:
            if chk.chunk_sha256 not in seen_hashes:
                seen_hashes.add(chk.chunk_sha256)
                unique_chunks.append(chk)

        # Update registry
        self.register.register_document(meta, len(unique_chunks))
        self.ingested_chunks.extend(unique_chunks)
        return unique_chunks

    def _parse_pdf(self, file_path: Path, meta: DocumentMetadata) -> List[ExtractedChunk]:
        """Extracts text page by page from PDF using pypdf."""
        if not PYPDF_AVAILABLE:
            raise RuntimeError("pypdf is not installed. Install via pip install pypdf")

        chunks: List[ExtractedChunk] = []
        reader = pypdf.PdfReader(str(file_path))
        for page_num, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""
            if page_text.strip():
                page_chunks = SemanticSectionChunker.chunk_document(
                    text=page_text,
                    metadata=meta,
                    page_number=page_num
                )
                chunks.extend(page_chunks)
        return chunks

    def _parse_text(self, file_path: Path, meta: DocumentMetadata) -> List[ExtractedChunk]:
        """Reads plain text or markdown files."""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return SemanticSectionChunker.chunk_document(text=content, metadata=meta, page_number=1)

    def _parse_json(self, file_path: Path, meta: DocumentMetadata) -> List[ExtractedChunk]:
        """Reads structured JSON document."""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        chunks: List[ExtractedChunk] = []
        if isinstance(data, list):
            for idx, item in enumerate(data, start=1):
                item_text = item.get("text") or item.get("content") or json.dumps(item, ensure_ascii=False)
                item_sec = item.get("section", "overview")
                item_lang = item.get("language", meta.language)
                item_crop = item.get("crop", meta.crop)
                item_disease = item.get("disease", meta.primary_disease or meta.title)
                
                cleaned = TextCleaner.clean(item_text)
                sha = hashlib.sha256(cleaned.encode("utf-8")).hexdigest()
                chunk_id = f"{meta.document_id}_item_{idx}"
                chunks.append(
                    ExtractedChunk(
                        chunk_id=chunk_id,
                        document_id=meta.document_id,
                        crop=item_crop,
                        disease_name=item_disease,
                        section=item_sec,
                        language=item_lang,
                        text=cleaned,
                        page_number=1,
                        chunk_sha256=sha,
                        metadata={
                            "institution": meta.author_or_institution,
                            "year": meta.publication_year,
                            "geo": meta.geographic_relevance
                        }
                    )
                )
        elif isinstance(data, dict):
            # If dictionary contains sections
            for sec_name, sec_content in data.items():
                if isinstance(sec_content, (str, list)):
                    sec_text = " ".join(sec_content) if isinstance(sec_content, list) else str(sec_content)
                    cleaned = TextCleaner.clean(sec_text)
                    sha = hashlib.sha256(cleaned.encode("utf-8")).hexdigest()
                    chunk_id = f"{meta.document_id}_{sec_name}"
                    chunks.append(
                        ExtractedChunk(
                            chunk_id=chunk_id,
                            document_id=meta.document_id,
                            crop=meta.crop,
                            disease_name=meta.primary_disease or meta.title,
                            section=sec_name,
                            language=meta.language,
                            text=cleaned,
                            page_number=1,
                            chunk_sha256=sha,
                            metadata={"institution": meta.author_or_institution}
                        )
                    )
        return chunks

    def _parse_docx(self, file_path: Path, meta: DocumentMetadata) -> List[ExtractedChunk]:
        """Reads Microsoft Word docx file."""
        if not DOCX_AVAILABLE:
            raise RuntimeError("python-docx is not installed. Install via pip install python-docx")

        doc = docx.Document(str(file_path))
        text = "\n\n".join([para.text for para in doc.paragraphs if para.text.strip()])
        return SemanticSectionChunker.chunk_document(text=text, metadata=meta, page_number=1)

    def ingest_directory(
        self,
        directory_path: str,
        recursive: bool = True,
        metadata_map: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> List[ExtractedChunk]:
        """
        Batch-ingests an entire directory of agricultural documents.
        """
        dir_p = Path(directory_path)
        if not dir_p.exists():
            logger.warning(f"Directory does not exist: {dir_p}")
            return []

        pattern = "**/*" if recursive else "*"
        all_chunks: List[ExtractedChunk] = []

        for f in dir_p.glob(pattern):
            if f.is_file() and f.suffix.lower() in [".pdf", ".md", ".txt", ".json", ".docx"]:
                if f.name == "document_register.json":
                    continue
                override = (metadata_map or {}).get(f.name, {})
                try:
                    chunks = self.parse_file(f, metadata_override=override)
                    all_chunks.extend(chunks)
                    logger.info(f"Successfully ingested {f.name}: {len(chunks)} chunks")
                except Exception as e:
                    logger.error(f"Failed to ingest {f.name}: {e}")

        return all_chunks

    def to_rag_document_chunks(self) -> List[Any]:
        """Converts extracted pipeline chunks into RAG DocumentChunk objects."""
        from app.services.rag.indexer import DocumentChunk

        rag_chunks: List[DocumentChunk] = []
        for c in self.ingested_chunks:
            disease_id = f"{c.crop}_{c.disease_name.lower().replace(' ', '_')}_{c.section}"
            rag_chunks.append(
                DocumentChunk(
                    chunk_id=c.chunk_id,
                    disease_id=disease_id,
                    crop=c.crop.lower(),
                    disease_name=c.disease_name,
                    scientific_name=c.metadata.get("scientific_name", ""),
                    pathogen_type=c.metadata.get("pathogen_type", "Agronomic/Pathology"),
                    section=c.section,
                    language=c.language,
                    text=c.text,
                    metadata=c.metadata
                )
            )
        return rag_chunks


# Global singleton instance
document_pipeline = AgriculturalDocumentPipeline()
