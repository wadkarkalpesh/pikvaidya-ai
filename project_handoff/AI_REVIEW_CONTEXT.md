# AI Review Brief: PikVaidya AI (पिकवैद्य AI)
> **Instructions for the Reviewing AI Assistant:**  
> This document is a comprehensive, standalone technical handoff brief generated from an empirical audit of the **PikVaidya AI** codebase. It contains all architectural details, verified capabilities, empirical test metrics, critical gaps, security evaluations, and agronomic risks needed to review the project. **You do not need to request the source code; the complete verified state is documented below.**

---

## 1. Project Identity & Stated Objectives

* **Project Name:** PikVaidya AI (पिकवैद्य AI — *"Crop Doctor AI"*)
* **Domain:** Explainable Multimodal Agricultural Decision Support System
* **Target Users:** Smallholder farmers in Maharashtra and across India
* **Core Value Proposition:** Intelligent crop disease diagnostics from smartphone leaf photographs, visual explainability (Grad-CAM heatmaps), and localized agronomic advisories delivered in **Marathi (`mr`)** and **English (`en`)**.
* **Target Crop Scope:** Sugarcane, Tomato, Onion, Cotton, and Soybean.
* **Repository Root:** `E:\PikVaidya AI` | **Git Branch:** `main` (Clean working tree)

---

## 2. Technical Stack & Architecture

```
                    ┌────────────────────────────────────────┐
                    │      Frontend Client (PLANNED)         │
                    │   React / Next.js / PWA [EMPTY DIR]    │
                    └───────────────────┬────────────────────┘
                                        │ HTTP REST / JSON
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       FastAPI Application Gateway                           │
│                   (Python 3.13.15, Uvicorn, Pydantic v2)                    │
├──────────────────────────────────────┬──────────────────────────────────────┤
│ Authenticated Route:                 │ Standalone Inference Route:          │
│ POST /api/v1/crops/{id}/diagnoses    │ POST /api/v1/diagnose/predict        │
│ • Validates Bearer JWT Token         │ • Unauthenticated Model Serving      │
│ • Validates MIME & Magic Bytes       │ • Validates MIME & Magic Bytes       │
│ • Calls ai_service.analyze_crop()    │ • Calls model_service.predict()      │
│ • Saves Diagnosis record to DB       │ • Generates Grad-CAM Heatmap overlay │
│ • Returns Bilingual Advisory         │ • Returns Logits & Class Scores      │
│ • (Does NOT generate Grad-CAM)       │ • (Does NOT persist to Database)     │
└──────────────────┬───────────────────┴──────────────────┬───────────────────┘
                   │                                      │
                   ▼                                      ▼
┌──────────────────────────────────────┐┌─────────────────────────────────────┐
│        Data Persistence Layer        ││         Machine Learning CV         │
│     (PostgreSQL 16 via psycopg)      ││        (PyTorch 2.14.1 on CPU)      │
│ • SQLAlchemy 2.0 ORM                 ││ • EfficientNet-B0 (48.6 MB Checkpt) │
│ • Alembic 1.20 Migrations (001, 002) ││ • MobileNetV3-Large (38.9 MB Chkpt) │
│ • Tables: users, farms, crop_cycles, ││ • Grad-CAM Layer: features[-1]      │
│   diagnoses, alembic_version         ││ • 5 Classes: Healthy, Mosaic,       │
│ • Foreign Key Cascade Deletion       ││   RedRot, Rust, Yellow              │
└──────────────────────────────────────┘└─────────────────────────────────────┘
```

* **Backend Framework:** FastAPI 0.110+ on Python 3.13.15 with Uvicorn.
* **ORM & Database:** SQLAlchemy 2.0.50 with PostgreSQL 16 (psycopg 3 binary driver).
* **Database Migrations:** Alembic 1.20.1 (Revisions: `001_initial_schema`, `002_add_diagnostics_schema`).
* **Deep Learning Framework:** PyTorch 2.14.1 + Torchvision 0.16.0 (CPU inference).
* **Testing Engine:** Pytest 9.1.1 + HTTPX TestClient (58 automated tests).
* **Containerization:** Docker Compose for PostgreSQL 16 (`infra/docker-compose.yml`). No application Dockerfile.

---

## 3. Verified Reality vs. Stated Claims

| Subsystem | Stated / Documented Capability | Actual Inspected Reality | Audit Verdict |
| :--- | :--- | :--- | :---: |
| **Sugarcane Vision Model** | 5-class foliar pathology model | PyTorch EfficientNet-B0 checkpoint (48.6 MB) loaded in CPU memory; 93.16% test accuracy on 351 images. | **VERIFIED WORKING** |
| **Multi-Crop Expansion** | Diagnostic support for Sugarcane, Tomato, Onion, Cotton, Soybean | Only Sugarcane has a trained model. Tomato, Cotton, Soybean, and Onion bypass ML and return hardcoded mock responses. | **PARTIALLY IMPLEMENTED (MOCK)** |
| **Grad-CAM Explainability** | Visual lesion saliency overlays | Implemented via PyTorch forward/backward hooks on `features[-1]`, blended with synthetic JET colormap; zero memory leaks. | **VERIFIED WORKING** |
| **Disease Severity Estimation** | Quantitative necrosis measurement & leaf area percentage | Static hardcoded rule: RedRot = `SEVERE` (22% area); all other diseases = `MODERATE` (15% area). No segmentation network exists. | **PARTIALLY IMPLEMENTED (UNVALIDATED)** |
| **API & Database Gateway** | Multi-tenant REST API with persistent tracking | FastAPI with SQLAlchemy 2.0 ORM and Alembic migrations. Full CRUD for Users, Farms, Crops, and Diagnoses. | **VERIFIED WORKING** |
| **Security & Privacy** | OWASP Top 10 hardened, multi-tenant isolation, safe uploads | Salted `bcrypt`, HS256 JWT, magic byte validation, UUID file naming, and tenant isolation strictly verified across 58 tests. | **VERIFIED WORKING** |
| **Agricultural Advisory** | Multilingual ICAR/CIBRC advisory with weather fusion | Static dictionary lookup in `ai_service.py`. Good Marathi translations, but no confidence gating (chemical advice given at 35% confidence). | **NEEDS DOMAIN EXPERT REVIEW** |
| **Frontend User Interface** | Responsive bilingual farmer web/mobile application | Directory `frontend/` contains only `.gitkeep` and a 17-line README. No UI code exists. | **NOT IMPLEMENTED** |
| **Runtime Services** | Deployed application stack | PostgreSQL 16 is running on port 5432 with 5 tables. FastAPI backend server on port 8000 is NOT currently running. | **PARTIALLY VERIFIED** |

---

## 4. Empirical Test Results (Zero-Fabrication)

During the October 25, 2026 technical audit, the following commands were executed directly:

### 1. Full Automated Pytest Suite
```powershell
python -u -m pytest backend/tests
```
* **Result:** **58 PASSED, 0 FAILED** in 67.14 seconds (100% Pass Rate).
* **Test Isolation:** Executes against an isolated in-memory SQLite sandbox (`sqlite:///:memory:` via `StaticPool`), leaving PostgreSQL unaffected.
* **Coverage Scope:**
  * `test_auth.py` (12 tests): Registration, duplicate rejection, login JSON/form, JWT validation, expiration, signature forgery.
  * `test_farms.py` (8 tests): Farm CRUD, user tenancy validation, cross-user forbidden checks (BOLA/IDOR).
  * `test_crops.py` (6 tests): Crop cycle lifecycle and farm association.
  * `test_farmer.py` (4 tests): Profile retrieval and Marathi/English preference updates.
  * `test_diagnostics.py` (11 tests): Image upload, MIME/magic validation, telemetry recording, cascade deletion.
  * `test_model_serving.py` (10 tests): Direct prediction, Grad-CAM generation, 10MB limit, error masking.
  * `test_real_assets_integration.py` (7 tests): Real sugarcane leaf photographs evaluated end-to-end.

### 2. Standalone Model Inference Smoke Test (`scripts/verify_phase2_inference.py`)
* Evaluated held-out test leaf images from `data/raw/sugarcane/`:
  * `healthy (188).jpeg`: GT = Healthy $\rightarrow$ Predicted = **Healthy** (Conf: **0.9327**). Match: **TRUE**.
  * `mosaic (39).jpeg`: GT = Mosaic $\rightarrow$ Predicted = **Mosaic** (Conf: **0.5702**). Match: **TRUE**.
  * `redrot (380).jpeg`: GT = RedRot $\rightarrow$ Predicted = **RedRot** (Conf: **0.9445**). Match: **TRUE**.
  * `rust (423).jpeg`: GT = Rust $\rightarrow$ Predicted = **RedRot** (Conf: **0.5730**, Rust: **0.3410**). Match: **FALSE** (Misclassification).
  * `yellow (279).jpeg`: GT = Yellow $\rightarrow$ Predicted = **Yellow** (Conf: **0.4070**). Match: **TRUE**.
* Dimension tests ($(100 \times 100)$, $(640 \times 480)$, $(1920 \times 1080)$, $(50 \times 400)$) all normalized to $(3, 224, 224)$ without crashing.

### 3. Standalone Grad-CAM Smoke Test (`scripts/verify_phase3_gradcam.py`)
* Generates $(7 \times 7)$ CAM tensor from `features[-1]`, normalizes to $[0.0000, 1.0000]$, and overlays onto $493 \times 1040$ original image via synthetic JET colormap.
* 5 consecutive inferences completed with zero hook accumulation.

### 4. Standalone Database & ORM Smoke Test (`scripts/verify_phase5_database.py`)
* Verified `users`, `farms`, `crop_cycles`, and `diagnoses` relationships and foreign-key cascade deletions on isolated SQLite sandbox.

### 5. Runtime Process & Port Verification
* **Port 5432 (PostgreSQL 16):** State `Listen` (PID 6732). Active read-only query confirmed 5 public tables (`users`, `farms`, `crop_cycles`, `diagnoses`, `alembic_version`), revision `002_add_diagnostics_schema`, with 2 users and 2 diagnoses.
* **Port 8000 (FastAPI):** No process listening. Connection refused (`WinError 10061`).

---

## 5. Machine Learning & Dataset Details

### Checkpoint Specifications
* **Primary Model (Production Target):** EfficientNet-B0 (`models/sugarcane/efficientnet_b0/best_model.pth`, 48.6 MB).
* **Edge Comparison Model:** MobileNetV3-Large (`models/sugarcane/mobilenet_v3/best_model.pth`, 38.9 MB).
* **Classifier Head:** `nn.Sequential(nn.Dropout(p=0.3), nn.Linear(1280, 5))`.
* **Classes (5):** `0: Healthy`, `1: Mosaic`, `2: RedRot`, `3: Rust`, `4: Yellow`.
* **Preprocessing:** Resize to $(224 \times 224)$, ToTensor, ImageNet normalization.
* **Training Reality:** Trained for **1 epoch** on CPU (`AdamW`, $\text{lr}=5 \times 10^{-4}$, Cosine Annealing, Cross-Entropy with 0.1 label smoothing).
* **Recorded Test Metrics (351 Held-Out Test Samples):**
  * EfficientNet-B0: Top-1 Accuracy: **93.16%**, Macro F1: **0.9286**, Macro Precision: **0.9354**, Macro Recall: **0.9274**, ECE: **0.0899**.
  * MobileNetV3-Large: Top-1 Accuracy: **84.05%**, Macro F1: **0.8342**, ECE: **0.0390**.
* **Per-Class F1 (EfficientNet-B0):** Healthy: **0.9664**, Yellow: **0.9542**, RedRot: **0.9211**, Rust: **0.9167**, Mosaic: **0.8846** (lowest recall at 80.70%, confused with early rust pustules).

### Dataset Breakdown
* **Sugarcane:** 2,521 field photographs. MD5 deduplication identified 210 exact duplicates and 225 dHash near-duplicates. Retained 2,311 unique images partitioned into 1,615 train (70%), 345 val (15%), and 351 test (15%) with **zero hash collisions**.
* **Tomato:** 18,906 images archived in `PlantVillage.zip` (lab images on neutral background). Not extracted, not trained.
* **Soybean:** 5,121 images in `PlantVillage.zip`, but **100% are Healthy foliage**. Zero disease images exist. Critical blocker for soybean modeling.
* **Onion:** 0 image files. Only a PDF research paper exists.
* **Cotton:** 0 images on disk.

---

## 6. The 5 Most Critical Risks & Blockers

### 🚨 Risk 1 (P0): Hardcoded Static Disease Severity & Necrosis Area
* **Code Provenance:** `backend/app/services/ai_service.py` (lines 170–171, 202–204).
* **The Reality:** Every Red Rot diagnosis is hardcoded as `SEVERE` (22% area); all other diseases are hardcoded as `MODERATE` (15% area). No computer vision lesion segmentation is performed.
* **Impact:** Misleads agronomists and farmers who expect quantitative necrosis measurement.

### 🚨 Risk 2 (P0): Absence of Confidence-Gated Pesticide Advisories
* **The Reality:** The backend issues full-strength chemical pesticide advice (e.g. Carbendazim, Mancozeb, Propiconazole) regardless of classification probability. A blurry image with 35% confidence receives the exact same treatment instructions as a 99% confident diagnosis.
* **Impact:** Farmers may spray expensive, toxic chemicals unnecessarily.

### 🚨 Risk 3 (P1): Fake / Simulated Diagnoses for Tomato, Cotton, Soybean, and Onion
* **Code Provenance:** `backend/app/services/ai_service.py` (lines 178–218).
* **The Reality:** Submitting any cotton image unconditionally returns *Cotton Leaf Curl Virus*; any tomato image returns *Early Blight*; any soybean image returns *Soybean Rust*; any onion image returns *Purple Blotch*, with synthetic 91%–94% confidence.
* **Impact:** Endpoints are non-functional simulations for non-sugarcane crops.

### 🚨 Risk 4 (P1): Two Disconnected Diagnostic Ingestion Pathways
* `POST /api/v1/diagnose/predict`: Standalone, unauthenticated. Evaluates real PyTorch model & Grad-CAM. Does not persist to database, returns no advisory.
* `POST /api/v1/crops/{crop_id}/diagnoses`: Authenticated farmer route. Persists to database. Does NOT generate Grad-CAM, hardcodes severity, and mocks non-sugarcane crops.
* **Impact:** No single endpoint provides both Grad-CAM explainability and persistent advisory tracking.

### 🚨 Risk 5 (P1): Complete Absence of Frontend Client UI
* `frontend/` directory is 100% empty except for a 17-line README. No web or mobile interface exists for farmers.

---

## 7. Security & Regulatory Compliance

* **Authentication & IDOR Defense:** Salted `bcrypt` hashing, HS256 JWT tokens with UTC expiration, strict ownership checks (`user_id == current_user.id`) on all resources.
* **Upload Hardening:** Whitelist (`.jpg`, `.jpeg`, `.png`, `.webp`), magic byte inspection, Pillow raster verification, 10MB limit, date-partitioned UUID storage.
* **Security Weaknesses:** `config.py` provides a hardcoded fallback string for `SECRET_KEY` and sets `CORS_ORIGINS = ["*"]` by default.
* **Agronomic Chemical Regulatory Review:** Recommended sugarcane fungicides (Carbendazim 50% WP, Mancozeb 75% WP, Propiconazole 25% EC) match ICAR/CIBRC standards. However, Pre-Harvest Intervals (PHI), water dilution volume per hectare, and statutory disclaimers under the Insecticides Act, 1968, are omitted.
* **Marathi Translation Quality:** Agronomically authentic (uses "तांबडे कूज" / "लाल सड", "तांबेरा", "मावा", and "बेणे प्रक्रिया").

---

## 8. Prioritized Recommended Next Actions for Engineering

1. **Gate Low-Confidence Advisories (Immediate P0):** Suppress chemical pesticide recommendations when model confidence $< 70\%$.
2. **Unify Ingestion Routes (High P1):** Merge `/api/v1/diagnose/predict` into `POST /api/v1/crops/{crop_id}/diagnoses`, add `heatmap_path` to the database schema, and persist Grad-CAM overlays alongside bilingual advisories.
3. **Train Real Lesion Segmentation (High P1):** Replace static 22% / 15% severity rules with an Otsu thresholding or lightweight MobileNetV3-UNet segmentation model to calculate true lesion area.
4. **Ingest Missing Multi-Crop Datasets (High P1):** Acquire external field datasets for Cotton (Kaggle), Onion (Mendeley), and infected Soybean foliar diseases before training multi-crop models.
5. **Implement Client Frontend (High P1):** Build a responsive Progressive Web App (PWA) in `frontend/` with camera upload and Marathi/English language toggling.
6. **Synchronize Dependencies (Medium P2):** Add `torch`, `torchvision`, `pillow`, and `numpy` to `backend/requirements.txt`.
7. **Re-base Dataset Manifests (Medium P2):** Convert hardcoded Windows paths in `datasets/processed/sugarcane/*.csv` to project-relative paths.
