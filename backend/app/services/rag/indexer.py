"""
PikVaidya AI — Agricultural RAG Hybrid Retrieval & Vector Indexer
================================================================
Implements production-grade hybrid retrieval (Lexical BM25 + Dense Semantic Embeddings)
with Reciprocal Rank Fusion (RRF) for multilingual agricultural knowledge documents
(English, Marathi, and Hindi).

Architecture:
1. Multilingual Tokenization: Words + Subword character n-grams (3-grams, 4-grams)
   with domain stopword filtering to prevent generic terms from diluting disease entities.
2. Domain Entity Boosting: Prioritizes explicit agricultural disease mentions (Red Rot, Rust, Mosaic, etc.).
3. Lexical BM25 Index: Inverted index with Okapi BM25 ranking (k1=1.5, b=0.75).
4. Dense Semantic Vector Index: Pure NumPy normalized vector embeddings with cosine similarity.
5. Reciprocal Rank Fusion (RRF): Blends sparse and dense rankings with zero external dependencies.
"""

import math
import re
import os
import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
import numpy as np

from app.db.seeds.disease_data import SUGARCANE_DISEASE_SEEDS
from app.db.seeds.tomato_disease_data import TOMATO_DISEASE_SEEDS
from app.db.seeds.onion_disease_data import ONION_DISEASE_SEEDS

logger = logging.getLogger(__name__)


@dataclass
class DocumentChunk:
    chunk_id: str
    disease_id: str
    crop: str
    disease_name: str
    scientific_name: str
    pathogen_type: str
    section: str  # "overview", "symptoms", "prevention", "cultural", "biological", "chemical", "conditions"
    language: str  # "en", "mr", "hi"
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievalResult:
    chunk: DocumentChunk
    score: float
    lexical_score: float
    dense_score: float
    rank: int


class MultilingualTokenizer:
    """Tokenizes English, Devanagari (Marathi/Hindi), and mixed text into words and subword n-grams."""

    WORD_REGEX = re.compile(r"[\w\u0900-\u097F]+", re.UNICODE)

    STOPWORDS = {
        "what", "are", "the", "of", "in", "to", "is", "for", "and", "a", "an", "on", "with",
        "how", "tell", "me", "about", "which", "do", "does", "can", "should", "from",
        "कोणती", "आहे", "काय", "कसे", "करावे", "करावी", "सांगा", "पडलेल्या", "वरील", "आहेत",
        "के", "की", "का", "में", "से", "है", "करें", "बताएं", "होता", "होती", "पर", "लिए"
    }

    @classmethod
    def tokenize(cls, text: str, remove_stopwords: bool = True) -> List[str]:
        """Extracts normalized words from text."""
        raw_words = cls.WORD_REGEX.findall(text.lower())
        tokens = []
        for w in raw_words:
            if len(w) > 1:
                if not remove_stopwords or w not in cls.STOPWORDS:
                    tokens.append(w)
        return tokens

    @classmethod
    def get_subword_ngrams(cls, text: str, n_min: int = 3, n_max: int = 4) -> List[str]:
        """Extracts words and Devanagari character n-grams to handle Indic suffixes and derivations."""
        words = cls.tokenize(text, remove_stopwords=True)
        ngrams = []
        for w in words:
            ngrams.append(w)  # Include full word
            # Only generate character n-grams for Devanagari words to capture Indic inflections
            if re.search(r"[\u0900-\u097F]", w) and len(w) >= 4:
                for n in range(n_min, min(len(w) + 1, n_max + 1)):
                    for i in range(len(w) - n + 1):
                        ngrams.append(w[i:i + n])
        return ngrams


class DenseSemanticEncoder:
    """Projects text into normalized dense vectors using deterministic feature hashing."""

    DIMENSION = 128

    @classmethod
    def encode(cls, text: str) -> np.ndarray:
        """Embeds text into a unit-normalized vector in R^128."""
        tokens = MultilingualTokenizer.get_subword_ngrams(text)
        vec = np.zeros(cls.DIMENSION, dtype=np.float32)

        if not tokens:
            return vec

        for t in tokens:
            # Deterministic MD5 hash to 128 dimensions with signed weights
            h = int(hashlib.md5(t.encode("utf-8")).hexdigest(), 16)
            idx = h % cls.DIMENSION
            sign = 1.0 if (h >> 7) & 1 else -1.0
            vec[idx] += sign

        norm = np.linalg.norm(vec)
        if norm > 1e-6:
            vec /= norm
        return vec


class CrossScoreReranker:
    """
    Context-aware cross-reranker that rescores candidates based on
    diagnostic concordance (crop, predicted disease), user intent (symptoms vs chemical vs cultural),
    and environmental microclimate alerts.
    """

    INTENT_KEYWORDS = {
        "symptoms": ["symptom", "लक्षण", "पहचान", "दिसते", "चिन्ह", "spot", "blight", "rot", "look", "how does"],
        "chemical": ["spray", "chemical", "medicine", "औषध", "फवारणी", "दवाई", "कीटकनाशक", "बुरशीनाशक", "fungicide", "insecticide", "dose", "dosage", "phi", "ml", "gram", "लिटर", "प्रमाण"],
        "cultural": ["organic", "biological", "cultural", "prevention", "सेंद्रिय", "मशागतीय", "जैविक", "बचाव", "ट्रायकोडर्मा", "सापळे", "trap", "mulch"],
        "nutrition": ["nutrition", "fertilizer", "fertigation", "खत", "युरिया", "npk", "पोषण", "potash", "sulphur"],
        "irrigation": ["water", "irrigation", "पाणी", "सिंचन", "drip", "ठिबक"]
    }

    @classmethod
    def rerank(
        cls,
        candidates: List[Tuple[int, float, float, float]],
        chunks: List[DocumentChunk],
        query: str,
        diagnostic_context: Optional[Dict[str, Any]] = None,
        weather_context: Optional[Dict[str, Any]] = None,
        top_k: int = 4
    ) -> List[Tuple[int, float, float, float]]:
        """
        Reranks top fused candidates using contextual cross-scoring.
        Returns sorted list of (chunk_idx, combined_score, bm25_score, dense_score).
        """
        if not candidates:
            return []

        q_lower = query.lower()
        # Detect query intent
        detected_intents = set()
        for intent, kw_list in cls.INTENT_KEYWORDS.items():
            if any(kw in q_lower for kw in kw_list):
                detected_intents.add(intent)

        scored_candidates = []
        for (idx, rrf_score, b_score, d_score) in candidates:
            chunk = chunks[idx]
            concordance_boost = 0.0

            # 1. Diagnostic concordance boost
            if diagnostic_context:
                diag_crop = (diagnostic_context.get("crop") or "").lower()
                diag_disease = (diagnostic_context.get("predicted_disease") or diagnostic_context.get("disease_name") or "").lower()

                if diag_crop and diag_crop == chunk.crop.lower():
                    concordance_boost += 0.50

                if diag_disease:
                    clean_diag = re.sub(r"[^a-z0-9]", "", diag_disease)
                    clean_chunk_d = re.sub(r"[^a-z0-9]", "", chunk.disease_name.lower())
                    clean_chunk_id = re.sub(r"[^a-z0-9]", "", chunk.disease_id.lower())
                    if clean_diag in clean_chunk_d or clean_diag in clean_chunk_id or clean_chunk_d in clean_diag:
                        concordance_boost += 1.50

            # 2. Query intent concordance
            if "chemical" in detected_intents and chunk.section == "chemical":
                concordance_boost += 0.80
            elif "symptoms" in detected_intents and chunk.section == "symptoms":
                concordance_boost += 0.60
            elif "cultural" in detected_intents and chunk.section in ["cultural_and_biological", "ipm", "prevention"]:
                concordance_boost += 0.60
            elif "nutrition" in detected_intents and chunk.section == "nutrition":
                concordance_boost += 0.60
            elif "irrigation" in detected_intents and chunk.section == "irrigation":
                concordance_boost += 0.60

            # 3. Weather context concordance
            if weather_context and not weather_context.get("is_safe_to_spray", True):
                if "spray" in chunk.text.lower() or "weather" in chunk.text.lower() or "हवामान" in chunk.text:
                    concordance_boost += 0.40

            # Combined score: RRF score + scaled concordance boost
            combined_score = rrf_score + (concordance_boost * 0.10)
            scored_candidates.append((idx, combined_score, b_score, d_score))

        # Re-sort descending by combined score
        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        return scored_candidates[:top_k]


class AgriculturalRAGIndexer:
    """Hybrid RAG indexing and search engine for agricultural pathology."""

    def __init__(self):
        self.chunks: List[DocumentChunk] = []
        self.chunk_vectors: Optional[np.ndarray] = None
        self.inverted_index: Dict[str, List[Tuple[int, float]]] = {}  # token -> [(chunk_idx, term_freq)]
        self.doc_lengths: List[int] = []
        self.avg_doc_length: float = 0.0
        self.idf_cache: Dict[str, float] = {}
        self.is_indexed: bool = False

    def build_index_from_seeds(self):
        """Builds comprehensive knowledge chunks from authoritative seed records."""
        all_chunks: List[DocumentChunk] = []
        all_seeds = SUGARCANE_DISEASE_SEEDS + TOMATO_DISEASE_SEEDS + ONION_DISEASE_SEEDS

        for record in all_seeds:
            disease_id = record["disease_id"]
            crop = record["crop_name"]
            disease_name = record["disease_name"]
            scientific_name = record.get("scientific_name", "")
            pathogen_type = record.get("pathogen_type", "")
            refs = record.get("reference_sources", [])

            # Check if record is single-language or multi-language dict
            if isinstance(record.get("symptoms"), str):
                target_langs = [record.get("language", "en")]
            else:
                target_langs = ["en", "mr", "hi"]

            # Index across target languages
            for lang in target_langs:
                # 1. Symptoms chunk
                if isinstance(record.get("symptoms"), dict):
                    sym_text = record.get("symptoms", {}).get(lang, "")
                else:
                    sym_text = str(record.get("symptoms", ""))

                if sym_text:
                    all_chunks.append(
                        DocumentChunk(
                            chunk_id=f"{disease_id}_{lang}_symptoms",
                            disease_id=disease_id,
                            crop=crop,
                            disease_name=disease_name,
                            scientific_name=scientific_name,
                            pathogen_type=pathogen_type,
                            section="symptoms",
                            language=lang,
                            text=f"Crop: {crop.capitalize()} | Disease: {disease_name} ({scientific_name}) | Symptoms: {sym_text}",
                            metadata={"type": "symptoms", "references": refs}
                        )
                    )

                # 2. Causes & Favourable Conditions chunk
                if isinstance(record.get("causes"), dict):
                    causes_text = record.get("causes", {}).get(lang, "")
                    fav_text = record.get("favourable_conditions", {}).get(lang, "")
                else:
                    causes_text = str(record.get("causes", ""))
                    fav_text = str(record.get("favourable_conditions", ""))

                if causes_text or fav_text:
                    all_chunks.append(
                        DocumentChunk(
                            chunk_id=f"{disease_id}_{lang}_conditions",
                            disease_id=disease_id,
                            crop=crop,
                            disease_name=disease_name,
                            scientific_name=scientific_name,
                            pathogen_type=pathogen_type,
                            section="conditions",
                            language=lang,
                            text=f"Crop: {crop.capitalize()} | Disease: {disease_name} | Causes: {causes_text} | Environmental Triggers: {fav_text}",
                            metadata={"type": "causes_and_conditions", "references": refs}
                        )
                    )

                # 3. Cultural & Biological Prevention chunk
                if isinstance(record.get("prevention_methods"), dict):
                    prev_list = record.get("prevention_methods", {}).get(lang, [])
                    cult_text = record.get("management_methods", {}).get("cultural", {}).get(lang, "")
                    bio_text = record.get("management_methods", {}).get("biological", {}).get(lang, "")
                    prev_combined = " ".join(prev_list) if isinstance(prev_list, list) else str(prev_list)
                    mgt_text = f"Cultural Controls: {cult_text} | Biological Controls: {bio_text} | Prevention: {prev_combined}".strip()
                else:
                    prev_val = record.get("prevention_methods", "")
                    mgt_val = record.get("management_methods", "")
                    mgt_text = f"Prevention: {prev_val} | Management: {mgt_val}".strip()

                if mgt_text:
                    all_chunks.append(
                        DocumentChunk(
                            chunk_id=f"{disease_id}_{lang}_management",
                            disease_id=disease_id,
                            crop=crop,
                            disease_name=disease_name,
                            scientific_name=scientific_name,
                            pathogen_type=pathogen_type,
                            section="cultural_and_biological",
                            language=lang,
                            text=f"Crop: {crop.capitalize()} | Disease: {disease_name} | {mgt_text}",
                            metadata={"type": "non_chemical_management", "references": refs}
                        )
                    )

                # 4. Chemical Management chunk
                if isinstance(record.get("management_methods"), dict):
                    chem_list = record.get("management_methods", {}).get("chemical", [])
                    if chem_list:
                        chem_details = []
                        for c in chem_list:
                            c_name = c.get("chemical_name", "Chemical")
                            c_trade = c.get("trade_names", "")
                            c_dose = c.get("dosage", "")
                            c_phi = c.get("waiting_period_phi_days", 30)
                            c_target = c.get("target_pathogen", "")
                            chem_details.append(f"{c_name} (Brands: {c_trade}) @ {c_dose}, PHI: {c_phi} days, Target: {c_target}")

                        chem_str = " ; ".join(chem_details)
                        all_chunks.append(
                            DocumentChunk(
                                chunk_id=f"{disease_id}_{lang}_chemical",
                                disease_id=disease_id,
                                crop=crop,
                                disease_name=disease_name,
                                scientific_name=scientific_name,
                                pathogen_type=pathogen_type,
                                section="chemical",
                                language=lang,
                                text=f"Crop: {crop.capitalize()} | Disease: {disease_name} | Approved Chemical Fungicides/Insecticides (CIBRC): {chem_str}",
                                metadata={"type": "chemical_management", "references": refs, "phi_tracked": True}
                            )
                        )

        self.index_chunks(all_chunks)

    def build_index(self, include_knowledge_base: bool = True):
        """Builds comprehensive knowledge chunks from authoritative seed records and pipeline documents."""
        all_chunks: List[DocumentChunk] = []
        all_seeds = SUGARCANE_DISEASE_SEEDS + TOMATO_DISEASE_SEEDS + ONION_DISEASE_SEEDS

        for record in all_seeds:
            disease_id = record["disease_id"]
            crop = record["crop_name"]
            disease_name = record["disease_name"]
            scientific_name = record.get("scientific_name", "")
            pathogen_type = record.get("pathogen_type", "")
            refs = record.get("reference_sources", [])

            # Check if record is single-language or multi-language dict
            if isinstance(record.get("symptoms"), str):
                target_langs = [record.get("language", "en")]
            else:
                target_langs = ["en", "mr", "hi"]

            # Index across target languages
            for lang in target_langs:
                # 1. Symptoms chunk
                if isinstance(record.get("symptoms"), dict):
                    sym_text = record.get("symptoms", {}).get(lang, "")
                else:
                    sym_text = str(record.get("symptoms", ""))

                if sym_text:
                    all_chunks.append(
                        DocumentChunk(
                            chunk_id=f"{disease_id}_{lang}_symptoms",
                            disease_id=disease_id,
                            crop=crop,
                            disease_name=disease_name,
                            scientific_name=scientific_name,
                            pathogen_type=pathogen_type,
                            section="symptoms",
                            language=lang,
                            text=f"Crop: {crop.capitalize()} | Disease: {disease_name} ({scientific_name}) | Symptoms: {sym_text}",
                            metadata={"type": "symptoms", "references": refs}
                        )
                    )

                # 2. Causes & Favourable Conditions chunk
                if isinstance(record.get("causes"), dict):
                    causes_text = record.get("causes", {}).get(lang, "")
                    fav_text = record.get("favourable_conditions", {}).get(lang, "")
                else:
                    causes_text = str(record.get("causes", ""))
                    fav_text = str(record.get("favourable_conditions", ""))

                if causes_text or fav_text:
                    all_chunks.append(
                        DocumentChunk(
                            chunk_id=f"{disease_id}_{lang}_conditions",
                            disease_id=disease_id,
                            crop=crop,
                            disease_name=disease_name,
                            scientific_name=scientific_name,
                            pathogen_type=pathogen_type,
                            section="conditions",
                            language=lang,
                            text=f"Crop: {crop.capitalize()} | Disease: {disease_name} | Causes: {causes_text} | Environmental Triggers: {fav_text}",
                            metadata={"type": "causes_and_conditions", "references": refs}
                        )
                    )

                # 3. Cultural & Biological Prevention chunk
                if isinstance(record.get("prevention_methods"), dict):
                    prev_list = record.get("prevention_methods", {}).get(lang, [])
                    cult_text = record.get("management_methods", {}).get("cultural", {}).get(lang, "")
                    bio_text = record.get("management_methods", {}).get("biological", {}).get(lang, "")
                    prev_combined = " ".join(prev_list) if isinstance(prev_list, list) else str(prev_list)
                    mgt_text = f"Cultural Controls: {cult_text} | Biological Controls: {bio_text} | Prevention: {prev_combined}".strip()
                else:
                    prev_val = record.get("prevention_methods", "")
                    mgt_val = record.get("management_methods", "")
                    mgt_text = f"Prevention: {prev_val} | Management: {mgt_val}".strip()

                if mgt_text:
                    all_chunks.append(
                        DocumentChunk(
                            chunk_id=f"{disease_id}_{lang}_management",
                            disease_id=disease_id,
                            crop=crop,
                            disease_name=disease_name,
                            scientific_name=scientific_name,
                            pathogen_type=pathogen_type,
                            section="cultural_and_biological",
                            language=lang,
                            text=f"Crop: {crop.capitalize()} | Disease: {disease_name} | {mgt_text}",
                            metadata={"type": "non_chemical_management", "references": refs}
                        )
                    )

                # 4. Chemical Management chunk
                if isinstance(record.get("management_methods"), dict):
                    chem_list = record.get("management_methods", {}).get("chemical", [])
                    if chem_list:
                        chem_details = []
                        for c in chem_list:
                            c_name = c.get("chemical_name", "Chemical")
                            c_trade = c.get("trade_names", "")
                            c_dose = c.get("dosage", "")
                            c_phi = c.get("waiting_period_phi_days", 30)
                            c_target = c.get("target_pathogen", "")
                            chem_details.append(f"{c_name} (Brands: {c_trade}) @ {c_dose}, PHI: {c_phi} days, Target: {c_target}")

                        chem_str = " ; ".join(chem_details)
                        all_chunks.append(
                            DocumentChunk(
                                chunk_id=f"{disease_id}_{lang}_chemical",
                                disease_id=disease_id,
                                crop=crop,
                                disease_name=disease_name,
                                scientific_name=scientific_name,
                                pathogen_type=pathogen_type,
                                section="chemical",
                                language=lang,
                                text=f"Crop: {crop.capitalize()} | Disease: {disease_name} | Approved Chemical Fungicides/Insecticides (CIBRC): {chem_str}",
                                metadata={"type": "chemical_management", "references": refs, "phi_tracked": True}
                            )
                        )

        # Ingest external knowledge base documents if available
        if include_knowledge_base:
            kb_dir = Path("data/knowledge_base")
            if kb_dir.exists():
                try:
                    from app.services.rag.document_pipeline import document_pipeline
                    document_pipeline.ingest_directory(str(kb_dir))
                    kb_chunks = document_pipeline.to_rag_document_chunks()
                    all_chunks.extend(kb_chunks)
                    logger.info(f"Loaded {len(kb_chunks)} additional chunks from knowledge base directory")
                except Exception as e:
                    logger.warning(f"Could not load knowledge base documents: {e}")

        self.index_chunks(all_chunks)

    def build_index_from_seeds(self):
        """Loads seed and knowledge base documents into index."""
        self.build_index(include_knowledge_base=True)

    def index_chunks(self, chunks: List[DocumentChunk]):
        """Builds BM25 and dense vector structures from chunks."""
        self.chunks = chunks
        num_docs = len(chunks)
        if num_docs == 0:
            return

        # 1. Dense Semantic Embeddings Matrix
        vectors = []
        doc_lengths = []
        tokenized_docs = []

        for c in chunks:
            tokens = MultilingualTokenizer.get_subword_ngrams(c.text)
            tokenized_docs.append(tokens)
            doc_lengths.append(len(tokens))
            vectors.append(DenseSemanticEncoder.encode(c.text))

        self.chunk_vectors = np.array(vectors, dtype=np.float32)
        self.doc_lengths = doc_lengths
        self.avg_doc_length = float(np.mean(doc_lengths)) if doc_lengths else 1.0

        # 2. BM25 Inverted Index
        self.inverted_index = {}
        doc_frequencies: Dict[str, int] = {}

        for doc_idx, tokens in enumerate(tokenized_docs):
            term_counts: Dict[str, int] = {}
            for t in tokens:
                term_counts[t] = term_counts.get(t, 0) + 1

            for t, count in term_counts.items():
                if t not in self.inverted_index:
                    self.inverted_index[t] = []
                self.inverted_index[t].append((doc_idx, float(count)))
                doc_frequencies[t] = doc_frequencies.get(t, 0) + 1

        # 3. Compute IDF
        self.idf_cache = {}
        for term, df in doc_frequencies.items():
            # Standard Lucene/BM25 IDF formula
            idf = math.log(1.0 + (num_docs - df + 0.5) / (df + 0.5))
            self.idf_cache[term] = max(idf, 0.1)

        self.is_indexed = True

    def search(
        self,
        query: str,
        crop_filter: Optional[str] = None,
        language_filter: Optional[str] = None,
        diagnostic_context: Optional[Dict[str, Any]] = None,
        weather_context: Optional[Dict[str, Any]] = None,
        top_k: int = 4
    ) -> List[RetrievalResult]:
        """
        Executes Reciprocal Rank Fusion (RRF) search combining BM25 and Dense Cosine Similarity
        with domain entity boosting and contextual cross-scoring reranking.
        """
        if not self.is_indexed or not self.chunks:
            self.build_index_from_seeds()

        query_tokens = MultilingualTokenizer.get_subword_ngrams(query)
        query_vec = DenseSemanticEncoder.encode(query)
        num_docs = len(self.chunks)

        # Detect explicit disease mentions for entity boosting
        q_lower = query.lower()
        boost_target = None
        if "red rot" in q_lower or "redrot" in q_lower or "तांबडे" in q_lower or "लाल सड़न" in q_lower or "लाल सड" in q_lower or "red_rot" in q_lower:
            boost_target = "red"
        elif "rust" in q_lower or "तांबेरा" in q_lower or "गेरुआ" in q_lower:
            boost_target = "rust"
        elif "bacterial" in q_lower or "जीवाणू" in q_lower or "bacterial_spot" in q_lower:
            boost_target = "bacterial"
        elif "early blight" in q_lower or "अल्टरनेरिया" in q_lower or "लवकर" in q_lower:
            boost_target = "early"
        elif "late blight" in q_lower or "लेट ब्लाइट" in q_lower or "उशिरा" in q_lower:
            boost_target = "late"
        elif "leaf mold" in q_lower or "मखमली" in q_lower:
            boost_target = "mold"
        elif "septoria" in q_lower or "सेप्टोरिया" in q_lower:
            boost_target = "septoria"
        elif "spider mite" in q_lower or "mite" in q_lower or "कोळी" in q_lower or "मकड़ी" in q_lower:
            boost_target = "mite"
        elif "target spot" in q_lower:
            boost_target = "target"
        elif "curl" in q_lower or "चुरडा" in q_lower or "पांढरी माशी" in q_lower or "whitefly" in q_lower:
            boost_target = "curl"
        elif "mosaic" in q_lower or "मोझॅक" in q_lower or "मोजेक" in q_lower:
            boost_target = "mosaic"
        elif "yellow" in q_lower or "पिवळा" in q_lower or "पीली" in q_lower:
            boost_target = "yellow"
        elif "healthy" in q_lower or "निरोगी" in q_lower or "स्वस्थ" in q_lower:
            boost_target = "healthy"

        # If not explicitly in query text, extract target disease from diagnostic context
        if not boost_target and diagnostic_context:
            diag_disease = (diagnostic_context.get("predicted_disease") or diagnostic_context.get("disease_name") or "").lower()
            if "early" in diag_disease:
                boost_target = "early"
            elif "late" in diag_disease:
                boost_target = "late"
            elif "red" in diag_disease:
                boost_target = "red"
            elif "rust" in diag_disease:
                boost_target = "rust"
            elif "purple" in diag_disease:
                boost_target = "purple"
            elif "stemphylium" in diag_disease:
                boost_target = "stemphylium"
            elif "bacterial" in diag_disease:
                boost_target = "bacterial"
            elif "curl" in diag_disease:
                boost_target = "curl"
            elif "smut" in diag_disease:
                boost_target = "smut"
            elif "healthy" in diag_disease:
                boost_target = "healthy"

        crop_boost = None
        if "tomato" in q_lower or "टोमॅटो" in q_lower or "टमाटर" in q_lower:
            crop_boost = "tomato"
        elif "sugarcane" in q_lower or "ऊस" in q_lower or "गन्ना" in q_lower:
            crop_boost = "sugarcane"
        elif "onion" in q_lower or "कांदा" in q_lower or "प्याज" in q_lower:
            crop_boost = "onion"
        elif diagnostic_context and diagnostic_context.get("crop"):
            crop_boost = diagnostic_context.get("crop", "").lower()

        # 1. Compute BM25 scores
        k1 = 1.5
        b = 0.75
        bm25_scores = np.zeros(num_docs, dtype=np.float32)

        for t in query_tokens:
            if t in self.inverted_index:
                idf = self.idf_cache.get(t, 0.5)
                for doc_idx, tf in self.inverted_index[t]:
                    doc_len = self.doc_lengths[doc_idx]
                    denom = tf + k1 * (1.0 - b + b * (doc_len / max(self.avg_doc_length, 1.0)))
                    bm25_scores[doc_idx] += idf * ((tf * (k1 + 1.0)) / max(denom, 1e-6))

        # 2. Compute Dense Cosine Similarities
        if self.chunk_vectors is not None:
            dense_scores = np.dot(self.chunk_vectors, query_vec)
        else:
            dense_scores = np.zeros(num_docs, dtype=np.float32)

        # 3. Apply entity boost if detected
        if boost_target:
            for idx, chunk in enumerate(self.chunks):
                clean_id = chunk.disease_id.lower().replace("_", "")
                if boost_target in clean_id:
                    bm25_scores[idx] += 30.0
                    dense_scores[idx] += 0.50

        if crop_boost:
            for idx, chunk in enumerate(self.chunks):
                if chunk.crop.lower() == crop_boost:
                    bm25_scores[idx] += 15.0
                    dense_scores[idx] += 0.25

        # 4. Filter candidates by crop and language
        eligible_indices = []
        for idx, chunk in enumerate(self.chunks):
            if crop_filter and chunk.crop.lower() != crop_filter.lower():
                continue
            if language_filter and chunk.language.lower() != language_filter.lower():
                continue
            eligible_indices.append(idx)

        if not eligible_indices:
            eligible_indices = list(range(num_docs))

        # Rank BM25
        bm25_ranked = sorted(eligible_indices, key=lambda i: bm25_scores[i], reverse=True)
        bm25_rank_map = {idx: rank + 1 for rank, idx in enumerate(bm25_ranked)}

        # Rank Dense
        dense_ranked = sorted(eligible_indices, key=lambda i: dense_scores[i], reverse=True)
        dense_rank_map = {idx: rank + 1 for rank, idx in enumerate(dense_ranked)}

        # 5. Reciprocal Rank Fusion (RRF constant C = 60)
        rrf_constant = 60.0
        fused_results = []

        for idx in eligible_indices:
            r_bm25 = bm25_rank_map.get(idx, num_docs)
            r_dense = dense_rank_map.get(idx, num_docs)
            rrf_score = (1.0 / (rrf_constant + r_bm25)) + (1.0 / (rrf_constant + r_dense))

            # Include if there is any lexical or strong semantic correlation
            if bm25_scores[idx] > 0.1 or dense_scores[idx] > 0.25:
                fused_results.append((idx, rrf_score, float(bm25_scores[idx]), float(dense_scores[idx])))

        # Sort by RRF score
        fused_results.sort(key=lambda x: x[1], reverse=True)

        # Contextual Cross-Score Reranking (Diagnostic concordance + Intent + Weather)
        reranked_candidates = CrossScoreReranker.rerank(
            candidates=fused_results[:max(top_k * 3, 10)],
            chunks=self.chunks,
            query=query,
            diagnostic_context=diagnostic_context,
            weather_context=weather_context,
            top_k=top_k
        )

        results = []
        for rank, (idx, final_score, b_score, d_score) in enumerate(reranked_candidates, start=1):
            results.append(
                RetrievalResult(
                    chunk=self.chunks[idx],
                    score=round(final_score, 5),
                    lexical_score=round(b_score, 4),
                    dense_score=round(d_score, 4),
                    rank=rank
                )
            )

        return results


# Global singleton instance
rag_indexer = AgriculturalRAGIndexer()
# Initialize on module load
rag_indexer.build_index_from_seeds()
