# PikVaidya AI — Agricultural Disease Knowledge Base & API Guide

## 1. Overview & System Purpose

The **PikVaidya AI Disease Knowledge Base** serves as the single source of truth connecting computer vision disease classifications to authoritative agronomic knowledge, multilingual farmer advisories, and future Retrieval-Augmented Generation (RAG) assistant pipelines.

By centralizing disease profiles into a structured, validated relational schema, the system prevents arbitrary or hallucinated treatment advice and ensures that all recommendations are grounded in protocols approved by the **Indian Council of Agricultural Research (ICAR)** and the **Central Insecticide Board & Registration Committee (CIBRC)**.

---

## 2. Relational Database Schema (`disease_knowledge`)

The database table is defined via SQLAlchemy in [`backend/app/models/disease.py`](file:///E:/PikVaidya%20AI/backend/app/models/disease.py):

| Field Name | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `disease_id` | `VARCHAR(64)` | `PRIMARY KEY`, Index | Unique slug identifier (e.g., `sugarcane_red_rot`, `cotton_leaf_curl`). |
| `crop_name` | `VARCHAR(32)` | `NOT NULL`, Index | Lowercase crop name (e.g., `sugarcane`, `tomato`, `cotton`). |
| `disease_name` | `VARCHAR(128)` | `NOT NULL`, Index | Common standard disease name in English. |
| `scientific_name` | `VARCHAR(128)` | `NOT NULL` | Binomial taxonomic name of the causal agent / pathogen. |
| `pathogen_type` | `VARCHAR(64)` | `NOT NULL` | Taxonomic category: `Fungal`, `Viral`, `Bacterial`, `Physiological`, `None`. |
| `symptoms` | `JSONB / JSON` | `NOT NULL` | Multilingual symptoms object: `{"en": "...", "mr": "...", "hi": "..."}`. |
| `causes` | `JSONB / JSON` | `NOT NULL` | Multilingual etiology, vector biology, and transmission channels. |
| `favourable_conditions`| `JSONB / JSON` | `NOT NULL` | Microclimate triggers: temperature range, humidity %, rainfall triggers. |
| `prevention_methods` | `JSONB / JSON` | `NOT NULL` | Preventative cultural practices, seed treatments, and sanitation steps. |
| `management_methods` | `JSONB / JSON` | `NOT NULL` | Detailed cultural, biological, and CIBRC-registered chemical controls. |
| `reference_sources` | `JSONB / JSON` | `NOT NULL` | Authoritative scientific citations and publication references. |
| `language` | `VARCHAR(16)` | `DEFAULT 'multilingual'` | Composite or primary language code. |
| `is_verified` | `BOOLEAN` | `DEFAULT TRUE` | Audit flag confirming scientific authenticity against ICAR/CIBRC standards. |
| `last_verified` | `VARCHAR(32)` | `NOT NULL` | Verification date string (`YYYY-MM-DD`). |
| `created_at` | `TIMESTAMPTZ` | Auto-generated | Timestamp of creation in UTC. |
| `updated_at` | `TIMESTAMPTZ` | Auto-updated | Timestamp of last modification in UTC. |

---

## 3. Authoritative Initial Data (5 Sugarcane Categories)

All seeded records in [`backend/app/db/seeds/disease_data.py`](file:///E:/PikVaidya%20AI/backend/app/db/seeds/disease_data.py) are extracted from published ICAR and university package of practices:

### 1. Healthy Foliage (`sugarcane_healthy`)
* **Scientific Name:** *Saccharum officinarum* (Healthy)
* **Pathogen Type:** None
* **Agronomic Baseline:** Uniform green foliage, optimal NPK nutrition (250:115:115 kg/ha in Maharashtra), earthing up at 90 and 120 days.
* **Citations:** ICAR-Sugarcane Breeding Institute (SBI) Agronomy Bulletin No. 42; MPKV Rahuri Krishi Darshani.

### 2. Sugarcane Mosaic (`sugarcane_mosaic`)
* **Scientific Name:** *Sugarcane mosaic virus* (SCMV) / *Sorghum mosaic virus* (SrMV)
* **Pathogen Type:** Viral (Potyviridae)
* **Vector:** Aphids (*Rhopalosiphum maidis*, *Melanaphis sacchari*)
* **Symptoms:** Alternating irregular dark green and pale yellowish-green chlorotic stripes, leaf stunting.
* **Control:** Virus-free certified tissue culture setts; aerated steam therapy (54°C, 2.5 hrs); aphid vector deterrence using 5% NSKE (Neem Seed Kernel Extract) or Imidacloprid 17.8% SL @ 0.3 ml/L.
* **Citations:** ICAR-SBI Disease Bulletin No. 18; TNAU Agritech Portal.

### 3. Red Rot (`sugarcane_red_rot`)
* **Scientific Name:** *Colletotrichum falcatum* Went (*Glomerella tucumanensis*)
* **Pathogen Type:** Fungal (Ascomycota)
* **Symptoms:** Known as the "Cancer of Sugarcane". Yellowing of 3rd/4th leaf, dull red internal stalk discoloration with transverse white patches, sour alcoholic odor.
* **Management:** 
  * Cultural: Rogue and incinerate infected stools; avoid ratoon crops from infected plots; 2-3 year crop rotation with paddy/legumes.
  * Biological: Sett dip with *Trichoderma viride* @ 10 g/L; soil enrichment with *Trichoderma* in FYM (5 kg/ha).
  * Chemical (CIBRC Approved): Sett dip in Carbendazim 50% WP @ 1 g/L or Thiophanate-Methyl 70% WP @ 1 g/L for 15-20 minutes before planting. (Note: Foliar spraying is ineffective once internal stalk rot develops).
* **Citations:** ICAR-SBI Technical Circular on Red Rot Management (R. Viswanathan et al.); CIBRC Approved List of Pesticides.

### 4. Common Rust (`sugarcane_rust`)
* **Scientific Name:** *Puccinia melanocephala* Syd. & P. Syd.
* **Pathogen Type:** Fungal (Basidiomycota)
* **Symptoms:** Yellowish chlorotic flecks enlarging into elongated reddish-brown pustules (*uredinia*) parallel to veins; epidermis ruptures releasing orange-brown powdery spores.
* **Management:** De-trashing old lower leaves at 150 & 210 days to increase aeration; foliar spray of Mancozeb 75% WP @ 2.5 g/L or Propiconazole 25% EC @ 1 ml/L. Repeat at 15-day intervals if cool, humid weather persists. PHI: 30 days.
* **Citations:** ICAR-SBI Pathology Guidelines Bulletin No. 36; MPKV Krishi Margadarshika.

### 5. Yellow Leaf Disease (`sugarcane_yellow_leaf`)
* **Scientific Name:** *Sugarcane yellow leaf virus* (SCYLV) / *Sugarcane yellow leaf phytoplasma* (SCYP)
* **Pathogen Type:** Viral / Phytoplasma
* **Vector:** Sugarcane aphid (*Melanaphis sacchari*)
* **Symptoms:** Prominent yellowing of the midrib on lower surface of leaves 3 to 6; leaves turn pinkish-red in advanced stages with apical internode shortening ("bunchy top").
* **Management:** Certified tissue-culture plantlets; moist hot air treatment (54°C, 2.5 hrs); aphid vector management using Imidacloprid 17.8% SL @ 0.3 ml/L or Thiamethoxam 25% WG @ 0.4 g/L.
* **Citations:** ICAR-SBI Special Technical Report on SCYLV; TNAU Agritech Portal.

---

## 4. API Endpoints Reference

The FastAPI router is mounted at [`backend/app/api/routes/diseases.py`](file:///E:/PikVaidya%20AI/backend/app/api/routes/diseases.py) and accessible via both `/api/v1/diseases` and `/api/diseases`:

### 4.1 List All Diseases
* **Route:** `GET /api/v1/diseases` (or `GET /api/diseases`)
* **Query Parameters:**
  * `crop` (optional, string): Filter by crop name (e.g. `?crop=sugarcane`)
  * `skip` (optional, integer): Pagination offset (default: 0)
  * `limit` (optional, integer): Maximum items (default: 100)
* **Response:** Array of `DiseaseResponse` objects.

### 4.2 Get Disease by ID
* **Route:** `GET /api/v1/diseases/{disease_id}` (or `GET /api/diseases/{disease_id}`)
* **Example:** `GET /api/v1/diseases/sugarcane_red_rot`
* **Response Code:** `200 OK` on success, `404 Not Found` if not registered.

### 4.3 Get Diseases by Crop
* **Route:** `GET /api/v1/diseases/crop/{crop_name}` (or `GET /api/diseases/crop/{crop_name}`)
* **Example:** `GET /api/v1/diseases/crop/sugarcane`
* **Response Code:** `200 OK` with 5 sugarcane disease profiles.

### 4.4 Multilingual Full-Text Search
* **Route:** `GET /api/v1/diseases/search?q={query}` (or `GET /api/diseases/search?q={query}`)
* **Examples:**
  * `GET /api/v1/diseases/search?q=uredinia` (Matches Rust symptom)
  * `GET /api/v1/diseases/search?q=कॅन्सर` (Matches Red Rot Marathi symptom text)
  * `GET /api/v1/diseases/search?q=धब्बे` (Matches Hindi disease description)
  * `GET /api/v1/diseases/search?q=Colletotrichum` (Matches scientific pathogen name)
* **Response:** Array of `DiseaseSearchResult` objects with matching snippet and field name.

### 4.5 RAG Document Representation
* **Route:** `GET /api/v1/diseases/{disease_id}/rag?lang={en|mr|hi}`
* **Example:** `GET /api/v1/diseases/sugarcane_mosaic/rag?lang=mr`
* **Response Payload:** Dense, formatted text chunk ready for vector embedding and LLM prompt context injection.

---

## 5. RAG Document Serialization Protocol

Every database entity implements `to_rag_document(lang="en")`:

```json
{
  "document_id": "sugarcane_red_rot_en",
  "disease_id": "sugarcane_red_rot",
  "crop": "sugarcane",
  "disease": "Red Rot",
  "language": "en",
  "content": "[CROP DISEASE KNOWLEDGE ENTRY]\nCrop: Sugarcane\nDisease Name: Red Rot\nScientific Name: Colletotrichum falcatum Went (Glomerella tucumanensis)\nPathogen Type: Fungal\nLanguage: EN\n\n1. SYMPTOMS & PATHOLOGICAL SIGNS:\nKnown as the 'Cancer of Sugarcane'...",
  "metadata": {
    "scientific_name": "Colletotrichum falcatum Went (Glomerella tucumanensis)",
    "pathogen_type": "Fungal",
    "is_verified": true,
    "last_verified": "2026-11-01"
  }
}
```

---

## 6. How to Add New Crop Diseases (Expansion Guide)

To expand PikVaidya AI to new crops (Cotton, Tomato, Soybean, Onion):

1. **Define Seed Data:** Add the crop entry dictionary in `backend/app/db/seeds/` with verified ICAR/SAU citations and CIBRC chemical dosages.
2. **Execute Database Seed / Insert:**
   ```python
   from app.services.disease_service import disease_service
   from app.db.session import SessionLocal

   db = SessionLocal()
   # Use disease_service.create_disease(db, disease_in)
   ```
3. **Verify via API:**
   Query `GET /api/v1/diseases/crop/cotton` to ensure seamless listing and search indexing.

