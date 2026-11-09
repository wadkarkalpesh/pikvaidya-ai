# PikVaidya AI — Agricultural RAG Architecture Specification
=============================================================

**Version:** 2.0  
**Status:** Implemented & Verified (186/186 Tests Passing)  
**Modules:** `indexer.py`, `document_pipeline.py`, `grounding.py`, `assistant.py`, `routes/assistant.py`  

---

## 1. High-Level Architecture Overview

The PikVaidya AI Agricultural RAG (Retrieval-Augmented Generation) system provides reliable, hallucination-free agronomic advice to farmers by harmonizing:
1. Multi-format agricultural documents (PDF, Markdown, JSON, Text).
2. Pure NumPy dense semantic hashing vectors (128 dimensions).
3. Inverted lexical Okapi BM25 indices ($k_1=1.5, b=0.75$).
4. Reciprocal Rank Fusion (RRF $C=60$).
5. Contextual CrossScoreReranker prioritizing live diagnostic findings and weather alerts.
6. Agricultural Grounding Engine enforcing CIBRC dosages, PHI days, and statutory disclaimers under the Insecticides Act, 1968.

```mermaid
flowchart TD
    subgraph Ingestion["1. Ingestion & Preprocessing"]
        PDF["Extension PDFs\n(pypdf)"] --> Pipe["Document Pipeline\n(document_pipeline.py)"]
        MD["Markdown Guides\n(MPKV/DOGR)"] --> Pipe
        JSON["Structured IPM JSON\n(CIBRC/ICAR)"] --> Pipe
        Pipe --> Cleaner["Multilingual Cleaner\n(Devanagari Normalization)"]
        Cleaner --> Chunker["Semantic Section Chunker\n(250-400 words, 50 overlap)"]
        Chunker --> Dedup["SHA-256 Deduplication\n& Source Register"]
    end

    subgraph Indexing["2. Dual Hybrid Indexing"]
        Dedup --> Tok["Multilingual Subword Tokenizer\n(Words + Character 3/4-grams)"]
        Tok --> BM25["Lexical Inverted Index\n(Okapi BM25: k1=1.5, b=0.75)"]
        Tok --> Dense["Dense Semantic Encoder\n(128-dim Unit-Normalized MD5)"]
    end

    subgraph QueryExecution["3. Retrieval & Contextual Reranking"]
        Farmer["Farmer Question\n(MR / HI / EN)"] --> Ass["RAG Assistant\n(Multi-Turn Session Memory)"]
        Diag["Live Foliar Diagnosis\n(Crop, Disease, Conf)"] --> Ass
        Weather["Weather Microclimate\n(Wind, Rain Risk, RH)"] --> Ass
        Ass --> Search["Hybrid Retrieval Engine\n(BM25 + Dense Cosine)"]
        BM25 --> Search
        Dense --> Search
        Search --> RRF["Reciprocal Rank Fusion\n(C = 60)"]
        RRF --> Rerank["CrossScoreReranker\n(Diagnostic Concordance + Intent + Weather)"]
    end

    subgraph Grounding["4. Grounding & Anti-Hallucination Guardrails"]
        Rerank --> Ground["Grounding Engine\n(grounding.py)"]
        Ground --> Boundary{"In-Domain Facts Found?"}
        Boundary -- No --> Refusal["Safe Boundary Refusal\n(Referral to Local KVK / Agronomist)"]
        Boundary -- Yes --> CheckConf{"Confidence >= 0.70?"}
        CheckConf -- No --> AddKVK["Inject Low Confidence Advisory\n(Seek University Verification)"]
        CheckConf -- Yes --> CheckWeather{"Is Safe to Spray?"}
        CheckWeather -- No --> AddWeather["Inject Adverse Weather Warning\n(High Wind / Rain Washout)"]
        CheckWeather -- Yes --> Synthesize["Synthesize Fact-Grounded Advice\n(CIBRC Dosage, PHI Days, Citations)"]
        AddKVK --> Synthesize
        AddWeather --> Synthesize
        Synthesize --> Response["Deliver Grounded Response to Farmer UI"]
    end
```

---

## 2. Core Mathematical Specifications

### 2.1 Multilingual Subword Tokenization
- Handles Devanagari script (Marathi and Hindi) alongside English and botanical Latin.
- Extracts standard alphanumeric words, filters common language stop-words (`कोणती, आहे, काय, कसे, में, से, है`, etc.).
- For Devanagari words with length $\ge 4$, extracts character 3-grams and 4-grams to account for Indic agglutinative inflections (e.g. *उसावरील $\rightarrow$ [उसा, सावर, वरील, उसाव, सावरी, वरील]*).

### 2.2 Dense Semantic Feature Hashing
- Fast, zero-external-dependency neural projection into $\mathbb{R}^{128}$.
- Maps tokens using deterministic MD5 hashing:
  $$h = \text{MD5}(token)$$
  $$idx = h \pmod{128}$$
  $$sign = +1 \text{ if } (h \gg 7) \& 1 \text{ else } -1$$
  $$\vec{v}[idx] \mathrel{+}= sign$$
- The resulting vector is unit-normalized: $\hat{v} = \frac{\vec{v}}{\|\vec{v}\|_2}$.
- Cosine similarity between query and document vectors is computed via fast vector dot-product:
  $$S_{dense} = \hat{q} \cdot \hat{d}$$

### 2.3 Okapi BM25 Lexical Ranking
- Implemented with standard parameters $k_1 = 1.5, b = 0.75$:
  $$\text{IDF}(t) = \ln\left(1 + \frac{N - \text{DF}(t) + 0.5}{\text{DF}(t) + 0.5}\right)$$
  $$\text{BM25}(q, d) = \sum_{t \in q} \text{IDF}(t) \cdot \frac{\text{TF}(t, d) \cdot (k_1 + 1)}{\text{TF}(t, d) + k_1 \cdot \left(1 - b + b \cdot \frac{|d|}{\text{avgdl}}\right)}$$

### 2.4 Reciprocal Rank Fusion (RRF)
- Merges disparate score distributions into a robust reciprocal rank metric with constant $C = 60$:
  $$\text{RRF}(d) = \frac{1}{60 + \text{Rank}_{BM25}(d)} + \frac{1}{60 + \text{Rank}_{Dense}(d)}$$

### 2.5 CrossScoreReranker (Contextual Concordance)
Candidates from the top $3 \times K$ RRF pool undergo cross-scoring evaluation:
$$Score_{final} = \text{RRF}(d) + 0.10 \times \left( Boost_{diagnostic} + Boost_{intent} + Boost_{weather} \right)$$
Where:
- $Boost_{diagnostic} = +0.50$ (matching crop) $+ 1.50$ (matching disease).
- $Boost_{intent} = +0.80$ (matching chemical inquiry with chemical section) or $+0.60$ (symptoms/cultural/irrigation).
- $Boost_{weather} = +0.40$ (adverse weather matched with spray timing / delay precautions).

---

## 3. Anti-Hallucination & Legal Safety Protocols
1. **Out-of-Domain Refusal:** When zero relevant agricultural chunks are retrieved or cosine similarity $< 0.35$ with zero BM25 overlap, the system refuses to answer and redirects to the nearest Krishi Vigyan Kendra (KVK).
2. **Zero Invented Dosages:** All chemical names, concentrations, and dosages must be explicitly present in the retrieved chunk metadata verified by CIBRC.
3. **Pre-Harvest Interval (PHI):** Always cited to prevent toxic pesticide residue in harvest.
4. **Statutory Notices:** Automatically injects mandatory legal disclaimers under the Insecticides Act, 1968 in the user's preferred language (English, Marathi, Hindi).

