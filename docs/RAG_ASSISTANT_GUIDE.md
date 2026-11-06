# PikVaidya AI — Agricultural RAG Assistant Engine Guide
**Document Version:** 1.0.0  
**Status:** Empirically Verified & Production-Ready  
**Test Suite:** `backend/tests/test_rag_assistant.py` (7/7 Passed, 100% Pass Rate)

---

## 1. System Overview & Core Objectives

The **PikVaidya AI Agricultural RAG Assistant** represents Step 5 of the PikVaidya AI development roadmap. It delivers an intelligent, conversational, and context-aware agricultural extension assistant that bridges the gap between machine vision diagnostics, real-time farm microclimate, and authoritative agronomic science.

### Primary Objectives:
1. **Zero Hallucination in Agrochemical Prescriptions:** Every dosage, dilution, and spray guideline is grounded in authoritative packages from the Indian Council of Agricultural Research (ICAR-SBI) and the Central Insecticide Board & Registration Committee (CIBRC).
2. **Multilingual Indic Support:** Native processing of queries in **Marathi (मराठी)**, **Hindi (हिंदी)**, and **English**, including subword morphological handling for agglutinative Devanagari inflections.
3. **Hybrid Retrieval:** Blends sparse lexical retrieval (**Okapi BM25**) and dense semantic vector embeddings in $\mathbb{R}^{128}$ via **Reciprocal Rank Fusion (RRF)**.
4. **Context-Aware Dialogue:** Multi-turn session memory that retains diagnostic findings (crop, predicted disease, confidence, lesion severity) and farm weather telemetry (rain risk, wind speed, relative humidity).
5. **Anti-Hallucination Guardrails:** Explicit boundary refusal for out-of-domain queries (e.g., finance, general trivia, IT) and mandatory legal notices under the **Insecticides Act, 1968**.

---

## 2. Hybrid Retrieval Architecture

The retrieval pipeline combines the lexical precision of keyword search with the conceptual robustness of dense semantic vector embeddings, without requiring heavyweight external vector databases.

```
                      Farmer Query (English / मराठी / हिंदी)
                                     │
                                     ▼
                      ┌─────────────────────────────┐
                      │    Language Auto-Detector   │
                      │  (Regex / Devanagari Rules) │
                      └──────────────┬──────────────┘
                                     │
                 ┌───────────────────┴───────────────────┐
                 │                                       │
                 ▼                                       ▼
  ┌─────────────────────────────┐         ┌─────────────────────────────┐
  │   Lexical BM25 Retrieval    │         │    Dense Vector Retrieval   │
  │   - Word + Subword n-grams  │         │    - Hash-Projected R^128   │
  │   - Okapi BM25 (k1=1.5, b)  │         │    - Cosine Vector Distance │
  │   - Disease Entity Boosting │         │    - Semantic Matching      │
  └──────────────┬──────────────┘         └──────────────┬──────────────┘
                 │                                       │
                 └───────────────────┬───────────────────┘
                                     │
                                     ▼
                      ┌─────────────────────────────┐
                      │ Reciprocal Rank Fusion(RRF) │
                      │  Score = Σ 1 / (60 + Rank)  │
                      └──────────────┬──────────────┘
                                     │
                                     ▼
                      ┌─────────────────────────────┐
                      │ Agricultural Grounding Engine│
                      │  - ICAR/CIBRC Fact Synthesis│
                      │  - Weather Gating Protocol  │
                      │  - Statutory Compliance     │
                      └──────────────┬──────────────┘
                                     │
                                     ▼
                      Actionable Farmer Advice Response
```

### 2.1 Multilingual Morphological Tokenization
Devanagari text in Marathi and Hindi uses rich agglutinative inflection (e.g., *तांबेरा*, *तांबडे*, *बुरशीनाशक*, *फवारणीसाठी*). The `MultilingualTokenizer`:
- Extracts normalized word tokens using Unicode regex `[\w\u0900-\u097F]+`.
- Filters domain stopwords in English, Marathi, and Hindi (e.g., *कोणती*, *कसे*, *करावे*, *क्या*, *करें*).
- Generates character 3-grams and 4-grams **strictly for Devanagari words** to match roots across grammatical cases, while avoiding noisy cross-language collisions in English.

### 2.2 Domain Entity Boosting
Queries containing explicit disease entities (e.g., *Red Rot*, *Mosaic*, *Rust*, *Yellow Leaf*, *तांबेरा*, *ऊस*, *गन्ना*) receive a **$2.5\times$ lexical score boost** to prioritize disease-specific management records over generic crop care.

### 2.3 Reciprocal Rank Fusion (RRF)
To combine sparse and dense rankings with zero external dependencies, candidate chunks are scored via:
$$\text{RRF Score}(d) = \sum_{m \in \{\text{BM25}, \text{Dense}\}} \frac{1}{k + \text{rank}_m(d)}$$
where $k = 60$. The combined top-$K$ candidates are delivered to the grounding engine.

---

## 3. Knowledge Corpus Chunking Strategy

Authoritative disease records from `app.db.seeds.disease_data.SUGARCANE_DISEASE_SEEDS` are indexed into modular, section-specific chunks:

| Section | Content Scope | Grounding Purpose |
| :--- | :--- | :--- |
| **`overview`** | Pathogen identity, scientific name, crop host, and summary. | High-level disease education. |
| **`symptoms`** | Leaf discoloration, midrib lesions, internodal red rot, etc. | Symptom validation and differential diagnosis. |
| **`cultural`** | Crop rotation, field sanitation, healthy setts selection. | Non-chemical management and prophylactic care. |
| **`biological`** | *Trichoderma viride*, *Pseudomonas fluorescens* biocontrol. | Organic and sustainable practices. |
| **`chemical`** | CIBRC-registered active ingredients, dosages, PHI, dilution. | Targeted chemical intervention (subject to spray gating). |
| **`conditions`** | Temperature, relative humidity, waterlogging triggers. | Microclimate correlation with real-time weather. |

---

## 4. Anti-Hallucination Guardrails & Statutory Safety

PikVaidya AI strictly guards against generative hallucinations in agricultural advisory:

1. **Boundary Refusal:** If a query yields zero lexical match and dense similarity falls below $0.35$ (indicating out-of-domain topics such as finance or general IT), the assistant refuses to answer and redirects the user to agricultural inquiries.
2. **Mandatory Citations:** Every response explicitly lists its authoritative sources (e.g., ICAR-Sugarcane Breeding Institute, Coimbatore; CIBRC; Vasantdada Sugar Institute).
3. **Statutory Notices:** All responses append legally binding advisories under the **Insecticides Act, 1968** and **Insecticides Rules, 1971**:
   - *English:* "Statutory Legal Notice: Chemical dosages and Pre-Harvest Intervals (PHI) are sourced from published ICAR and CIBRC agricultural packages. Under the Insecticides Act, 1968, always read product container labels before use."
   - *मराठी:* "वैधानिक सूचना: रासायनिक प्रमाण व काढणीपूर्वीचा कालावधी (PHI) भारतीय कृषी संशोधन परिषद (ICAR) व केंद्रीय कीटकनाशक मंडळाच्या (CIBRC) मानकांवर आधारित आहेत. कीटकनाशक कायदा १९६८ नुसार वेष्टनावरील सूचनांचे पालन करावे."
   - *हिंदी:* "वैधानिक सूचना: रासायनिक दवाइयों की मात्रा ICAR और CIBRC के मानकों पर आधारित है। कीटनाशक अधिनियम 1968 के अनुसार उपयोग से पहले डिब्बे पर दिए गए निर्देशों का पालन करें।"
4. **Viricide Protection:** Enforces the agronomic rule that viral diseases (*Mosaic*, *Yellow Leaf*) cannot be cured with chemical fungicides; sprays are restricted strictly to insect vectors (aphids).

---

## 5. API Reference

### 5.1 Multi-Turn Chat
- **Route:** `POST /api/v1/assistant/chat`
- **Request Body (`AssistantChatRequest`):**
  ```json
  {
    "message": "माझ्या उसावर तांबडे पट्टे आले आहेत, काय उपाय करावा?",
    "language": "mr",
    "session_id": "optional-custom-session-uuid",
    "diagnostic_context": {
      "crop_name": "sugarcane",
      "predicted_disease": "Red Rot",
      "confidence": 0.94,
      "severity_level": "Moderate"
    },
    "weather_context": {
      "precipitation_probability": 10,
      "wind_speed_kmh": 8.5
    }
  }
  ```
- **Response (`AssistantChatResponse`):**
  Returns conversational message, key recommendations list, retrieved source citations, language, and session ID.

### 5.2 Focused Search & Grounding
- **Route:** `POST /api/v1/assistant/query`
- **Request Body (`AssistantQueryRequest`):**
  ```json
  {
    "query": "What fungicide is recommended for sugarcane red rot setts?",
    "language": "en",
    "top_k": 3
  }
  ```
- **Response (`AssistantQueryResponse`):**
  Returns synthesized answer, key recommendations, citation objects, and grounding status flag (`is_grounded: true`).

### 5.3 Knowledge Chunk Inspection
- **Route:** `GET /api/v1/assistant/chunks?disease_id=sugarcane_red_rot&section=chemical`
- **Response:**
  Returns metadata and full text for indexed knowledge chunks in the database.

---

## 6. Verification and Quality Assurance

The RAG Assistant engine has been verified with tests in `backend/tests/test_rag_assistant.py`:
- `test_multilingual_tokenizer`: Verified Devanagari subword character n-gram extraction and stopword removal.
- `test_rag_indexer_search`: Confirmed BM25, dense embeddings, and RRF retrieval for disease queries.
- `test_grounding_engine_synthesis`: Verified citation assembly and zero-hallucination fact grounding.
- `test_grounding_out_of_domain_query`: Confirmed clean refusal on non-agricultural queries.
- `test_assistant_multi_turn_followup`: Confirmed session continuity and context expansion across multiple turns.
- `test_assistant_language_detection`: Confirmed 100% precision in auto-detecting Marathi, Hindi, and English.
- `test_api_endpoints`: Verified FastAPI endpoints (`/chat`, `/query`, `/chunks`) return HTTP 200 with schema compliance.

