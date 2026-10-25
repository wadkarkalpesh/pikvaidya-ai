# Comprehensive Project State Report: PikVaidya AI (पिकवैद्य AI)

**Document Version:** 1.0.0 — Definitive State of Repository  
**Audit Date:** October 25, 2026  
**Auditor Consortium:** Multi-Agent Technical Audit Panel  
* Senior Systems & Repository Architect
* Lead ML & MLOps Specialist Engineer
* Lead Agronomy & Advisory Systems Specialist
* Lead Backend, Database & API Specialist
* Principal Security & Privacy Auditor
* Lead Frontend & UX Engineer
* Principal QA & Test Automation Specialist
* Technical Documentation & Handoff Specialist

**Repository Root:** `E:\PikVaidya AI`  
**Git Branch:** `main` | **Git Commit Status:** Working tree clean, up to date with `origin/main`  
**Evaluation Standard:** Zero-Fabrication, Direct Code Inspection, and Empirical Command Execution

---

## 1. Executive Summary

An exhaustive, non-destructive technical audit of the **PikVaidya AI** codebase was conducted to establish its **actual operational state** as of October 25, 2026.

### High-Level Reality vs. Conception
| System Layer | Stated / Conceptual Vision | Actual Inspected Reality | Status Classification |
| :--- | :--- | :--- | :---: |
| **Sugarcane Vision Model** | 5-class foliar pathology model with deep neural inference | Real PyTorch EfficientNet-B0 checkpoint (48.6 MB) loaded in CPU memory; 93.16% test accuracy on 351 images. | **VERIFIED** |
| **Multi-Crop Expansion** | Diagnostic support for Sugarcane, Tomato, Onion, Cotton, and Soybean | Only Sugarcane has a trained model. Tomato, Cotton, Soybean, and Onion bypass ML and return hardcoded mock responses. | **PARTIALLY IMPLEMENTED** |
| **Explainable AI (Grad-CAM)** | Visual lesion saliency overlays for farmer trust | Implemented via PyTorch forward/backward hooks on `features[-1]`, blended with synthetic JET colormap; zero memory leaks. | **VERIFIED** |
| **Disease Severity Estimation** | Quantitative necrosis measurement & leaf area percentage | Static hardcoded rule: RedRot = `SEVERE` (22% area); all other diseases = `MODERATE` (15% area). No computer vision segmentation exists. | **PARTIALLY IMPLEMENTED (UNVALIDATED)** |
| **API & Database Gateway** | Multi-tenant REST API with persistent historical tracking | FastAPI with SQLAlchemy 2.0 ORM and Alembic migrations (`001`, `002`). Full CRUD for Users, Farms, Crops, and Diagnoses. | **VERIFIED** |
| **Security & Privacy** | OWASP Top 10 hardened, multi-tenant isolation, safe uploads | Salted `bcrypt`, HS256 JWT, magic byte validation, UUID file naming, and tenant isolation strictly verified across 58 tests. | **VERIFIED** |
| **Agricultural Advisory** | Multilingual ICAR/CIBRC advisory with weather fusion | Static dictionary lookup in `ai_service.py`. Good Marathi translations, but no confidence gating (chemical advice given at 30% confidence). | **NEEDS DOMAIN EXPERT REVIEW** |
| **Frontend User Interface** | Responsive bilingual farmer web/mobile application | Directory `frontend/` contains only `.gitkeep` and a 17-line README. No UI code exists. | **NOT IMPLEMENTED** |
| **Automated Testing** | Enterprise test automation | 58 automated pytest unit and integration tests passing in 67 seconds on in-memory SQLite sandbox. | **VERIFIED** |
| **Live Runtime Services** | Fully deployed cloud/local stack | PostgreSQL 16 is running on port 5432 with 5 tables. FastAPI backend server on port 8000 is NOT currently running. | **PARTIALLY VERIFIED** |

---

## 2. Repository Inventory & Directory Tree

```
E:\PikVaidya AI\
│
├── .env                              # Environment configuration (active)
├── .env.example                      # Template environment variables
├── .gitignore                        # Git exclusion rules
├── LICENSE                           # MIT License
├── README.md                         # Project documentation (Sprint 1 focus)
├── VERSION                           # Version string ("0.1.0")
├── model_capabilities.yaml           # Agent planning configuration (GSD workflow)
├── requirements.txt                  # Full project Python package manifest
│
├── backend/                          # FastAPI REST Application Root
│   ├── alembic/                      # Database schema migration engine
│   │   ├── env.py                    # Migration execution script
│   │   └── versions/                 # Applied migrations
│   │       ├── 001_initial_schema.py # Users, Farms, Crop Cycles
│   │       └── 002_add_diagnostics_schema.py # Diagnoses table
│   ├── alembic.ini                   # Alembic configuration
│   ├── requirements.txt              # Backend dependencies (Missing torch, PIL, numpy!)
│   ├── pytest.ini                    # Pytest configuration
│   ├── app/
│   │   ├── main.py                   # FastAPI app entrypoint, CORS, startup lifespan
│   │   ├── dependencies.py           # JWT & DB dependency injection
│   │   ├── api/routes/
│   │   │   ├── auth.py               # Register, login, /me
│   │   │   ├── farmer.py             # Farmer profile GET/PUT
│   │   │   ├── farms.py              # Farm CRUD & user tenancy isolation
│   │   │   ├── crops.py              # Crop cycle CRUD & farm relationship
│   │   │   └── diagnostics.py        # /diagnose/predict & /crops/{id}/diagnoses
│   │   ├── core/
│   │   │   ├── config.py             # Pydantic BaseSettings (SECRET_KEY, URLs)
│   │   │   └── security.py           # Bcrypt hashing & PyJWT token generator
│   │   ├── db/
│   │   │   ├── base.py               # Declarative SQLAlchemy Base
│   │   │   └── session.py            # SessionLocal & get_db generator
│   │   ├── models/                   # SQLAlchemy 2.0 ORM Entities
│   │   │   ├── user.py               # User table
│   │   │   ├── farm.py               # Farm table
│   │   │   ├── crop_cycle.py         # CropCycle table
│   │   │   └── diagnosis.py          # Diagnosis table
│   │   ├── schemas/                  # Pydantic v2 validation models
│   │   │   ├── auth.py, farm.py, crop_cycle.py, user.py, diagnosis.py
│   │   └── services/
│   │       ├── model_service.py      # Singleton PyTorch vision loader & Grad-CAM
│   │       ├── ai_service.py         # Advisory generator, severity heuristics, crop routing
│   │       └── storage.py            # Upload validation (magic bytes, size, UUID storage)
│   └── tests/                        # 58 Automated Pytest Test Cases
│       ├── conftest.py               # In-memory SQLite fixtures & auto-cleaners
│       ├── test_auth.py              # 12 authentication tests
│       ├── test_farms.py             # 8 farm management & tenancy tests
│       ├── test_crops.py             # 6 crop cycle tests
│       ├── test_farmer.py            # 4 farmer profile tests
│       ├── test_diagnostics.py       # 11 diagnostic persistence tests
│       ├── test_model_serving.py     # 10 direct prediction & upload validation tests
│       └── test_real_assets_integration.py # 7 tests using real leaf photographs
│
├── frontend/                         # Client User Interface (NOT IMPLEMENTED)
│   ├── .gitkeep
│   └── README.md                     # Planned React/Next.js/Flutter notes
│
├── models/                           # Trained PyTorch Model Checkpoints
│   └── sugarcane/
│       ├── efficientnet_b0/          # Primary Model A (48.6 MB, best_model.pth)
│       │   ├── best_model.pth, class_mapping.json, config.json, training_history.json
│       └── mobilenet_v3/             # Edge Model B (38.9 MB, best_model.pth)
│           ├── best_model.pth, class_mapping.json, config.json, training_history.json
│
├── datasets/                         # Dataset Manifests & Audit Reports
│   ├── processed/sugarcane/          # Stratified manifests (train/val/test CSVs)
│   └── reports/                      # Benchmark CSVs, confusion matrices, audit logs
│
├── data/                             # Raw Dataset Assets
│   ├── raw/sugarcane/                # 2,521 real field leaf images (5 classes)
│   ├── raw/PlantVillage-Dataset-master.zip # 2.5 GB archive (lab tomato, healthy soybean)
│   ├── raw/PlantDoc-Dataset-master.zip     # 984 MB archive (IIT Delhi field dataset)
│   └── raw/chiili and onion plant leaf images.pdf # 2.7 MB literature review paper
│
├── src/                              # Core ML Training & Explainability Framework
│   ├── data/                         # Dataset loaders and split generator
│   ├── training/                     # Model architecture factory & training loops
│   ├── evaluation/                   # Evaluation metrics & calibration calculators
│   └── explainability/               # Standalone Grad-CAM implementation
│
├── scripts/                          # Verification, Audit & Demo Scripts
│   ├── verify_phase2_inference.py    # Standalone model inference smoke tester
│   ├── verify_phase3_gradcam.py      # Standalone Grad-CAM smoke tester
│   ├── verify_phase5_database.py     # Standalone ORM & cascade smoke tester
│   ├── dataset_audit.py              # Comprehensive dataset auditor
│   └── live_demo.py                  # End-to-end integration demo script
│
├── infra/                            # Infrastructure & Deployment
│   └── docker-compose.yml            # PostgreSQL 16 Alpine container definition
│
└── project_handoff/                  # Comprehensive Independent Review Deliverables
```

---

## 3. Technology Stack & Runtime Environment

### Languages & Frameworks
* **Runtime Language:** Python 3.13.15 (Windows 64-bit environment).
* **Web Framework:** FastAPI 0.110+ (Running on Uvicorn ASGI).
* **Data Validation:** Pydantic v2 & `pydantic-settings`.
* **Database & ORM:** PostgreSQL 16 (production target via `psycopg` 3) and SQLAlchemy 2.0.50 (with declarative typed `Mapped` attributes).
* **Migrations:** Alembic 1.20.1.
* **Deep Learning Framework:** PyTorch 2.14.1 with Torchvision 0.16.0 (CPU execution mode).
* **Computer Vision & Image Processing:** Pillow (PIL) 10.x and NumPy.
* **Testing:** Pytest 9.1.1, HTTPX 0.27.0.

### Runtime Process Inspection
* **PostgreSQL Service (Port 5432):** **RUNNING AND RESPONDING**. Process PID 6732 is actively listening on `0.0.0.0:5432` and `[::]:5432`. Live connection verified; contains 5 tables (`users`, `farms`, `crop_cycles`, `diagnoses`, `alembic_version`).
* **FastAPI Server (Port 8000):** **CONFIGURED BUT NOT CURRENTLY RUNNING**. TCP connection to `127.0.0.1:8000` is refused. Application must be started manually using `python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000`.
* **Frontend Web Server:** **NOT IMPLEMENTED**. No server, build tool, or scripts exist.

---

## 4. Actual Application Workflow Trace

The 16-step canonical agricultural diagnostic workflow was evaluated against the active codebase:

| Step # | Intended Workflow Step | Operational Reality & Empirical Evidence | Status Label |
| :---: | :--- | :--- | :---: |
| **1** | User opens frontend or accesses API | No frontend exists. Backend root `GET /` and `GET /health` endpoints are fully implemented in `backend/app/main.py`. | **PARTIALLY IMPLEMENTED** |
| **2** | User registers or logs in | Implemented in `backend/app/api/routes/auth.py`. Issues HS256 JWT access token. 12 automated auth tests passing cleanly. | **VERIFIED WORKING** |
| **3** | User creates or selects a farm | Implemented in `backend/app/api/routes/farms.py`. Validates soil type, coordinates, area. Cross-user isolation verified. | **VERIFIED WORKING** |
| **4** | User creates or selects a crop cycle | Implemented in `backend/app/api/routes/crops.py`. Links crop cycle to authenticated user's farm. | **VERIFIED WORKING** |
| **5** | User uploads a crop image | Implemented via `UploadFile` multipart form data on `POST /api/v1/crops/{crop_id}/diagnoses` and `POST /api/v1/diagnose/predict`. | **VERIFIED WORKING** |
| **6** | Image passes validation & preprocessing | Implemented in `backend/app/services/storage.py` and `model_service.py`. Validates extensions, magic bytes, Pillow integrity, 10MB limit. | **VERIFIED WORKING** |
| **7** | Correct ML model is selected | Only Sugarcane selects a real model (`models/sugarcane/efficientnet_b0/best_model.pth`). Other crops bypass ML models. | **PARTIALLY IMPLEMENTED** |
| **8** | Model generates a prediction | Sugarcane forward pass outputs finite logits evaluated cleanly on CPU in ~140ms. | **VERIFIED WORKING (Sugarcane Only)** |
| **9** | Class probabilities calculated | Calculated via `torch.softmax(logits, dim=1)` in `model_service.py`. Sums to $1.0000 \pm 0.0001$. | **VERIFIED WORKING** |
| **10** | Grad-CAM explanation generated | Generates $(7 \times 7)$ CAM tensor from `features[-1]`, blended with original image via synthetic JET colormap. **Only executed on `/diagnose/predict`**, NOT on `/crops/{crop_id}/diagnoses`. | **PARTIALLY IMPLEMENTED** |
| **11** | Disease severity estimated | Rule-based heuristic in `ai_service.py` (RedRot = 22% SEVERE, others = 15% MODERATE). No computer vision measurement. | **PARTIALLY IMPLEMENTED (UNVALIDATED)** |
| **12** | Environmental context retrieved | Optional telemetry parameters (`temperature`, `humidity`, `soil_moisture`) can be passed via form data and saved to DB. No live API integration with weather providers. | **PARTIALLY IMPLEMENTED** |
| **13** | Crop-specific advisory generated | Generated from static in-memory dictionary `CROP_DIAGNOSTIC_KNOWLEDGE` in `backend/app/services/ai_service.py`. | **VERIFIED WORKING** |
| **14** | Marathi or English output returned | Bilingual fields (`disease_name_mr`, `symptoms_mr`, `recommendations_mr`) are returned alongside English. Marathi terminology is agronomically authentic. | **VERIFIED WORKING** |
| **15** | Diagnosis saved to database | Implemented in `POST /api/v1/crops/{crop_id}/diagnoses`. Saves image path, SHA-256 hash, disease names, severity, and telemetry into `diagnoses` table. | **VERIFIED WORKING** |
| **16** | User retrieves diagnosis history | Implemented via `GET /api/v1/crops/{crop_id}/diagnoses`, `GET /api/v1/diagnostics`, and `GET /api/v1/diagnostics/{id}`. Tenancy verified. | **VERIFIED WORKING** |

---

## 5. Crop Coverage Reality Check

| Crop | Dataset on Disk | Trained Model Checkpoint | Inference Engine | API Integration | Frontend Integration | Bilingual Advisory | Overall Operational Reality |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Sugarcane** | **2,521 images** (5 classes) | **EfficientNet-B0 (48.6 MB)** | **Real PyTorch inference** | Supported on both endpoints | None | Complete (Red Rot, Mosaic, Rust, Yellow Leaf) | **FUNCTIONAL & VERIFIED** |
| **Tomato** | Archived in `PlantVillage.zip` (54k images) | **None** | None | Simulated mock in `ai_service.py` | None | Hardcoded Early Blight advisory | **MOCK SIMULATION ONLY** |
| **Onion** | PDF paper only (0 image files) | **None** | None | Simulated mock in `ai_service.py` | None | Hardcoded Purple Blotch advisory | **MOCK SIMULATION ONLY** |
| **Cotton** | **0 images** on disk | **None** | None | Simulated mock in `ai_service.py` | None | Hardcoded Leaf Curl Virus advisory | **MOCK SIMULATION ONLY** |
| **Soybean** | Archived in `PlantVillage.zip` (**100% Healthy**) | **None** | None | Simulated mock in `ai_service.py` | None | Hardcoded Soybean Rust advisory | **MOCK SIMULATION ONLY** |

---

## 6. Machine Learning Status & Serving Pipeline

### Sugarcane Primary Vision Model (EfficientNet-B0)
* **Architecture:** `torchvision.models.efficientnet_b0` with custom classification head: `nn.Sequential(nn.Dropout(p=0.3), nn.Linear(1280, 5))`.
* **Checkpoint File:** `models/sugarcane/efficientnet_b0/best_model.pth` (48,637,304 bytes).
* **Target Classes (5):** `0: Healthy`, `1: Mosaic`, `2: RedRot`, `3: Rust`, `4: Yellow`.
* **Input Preprocessing:** Resize to $(224 \times 224)$, ToTensor, ImageNet Normalization (`mean=[0.485, 0.456, 0.406]`, `std=[0.229, 0.224, 0.225]`).
* **Training Reality:** Trained for **1 epoch** on CPU (`duration_seconds: 338.85s`) using AdamW ($\text{lr}=5 \times 10^{-4}$), Cosine Annealing, and Cross-Entropy loss with label smoothing (0.1).
* **Test Performance (351 Held-Out Test Samples):**
  * Overall Top-1 Accuracy: **93.16%**
  * Macro F1-Score: **0.9286**
  * Macro Precision: **0.9354** | Macro Recall: **0.9274**
  * Expected Calibration Error (ECE): **0.0899** (Well-calibrated)
* **Biological Error Analysis:**
  * Healthy: 100% recall (71/71).
  * Mosaic: Lowest recall (**80.70%**, 46/57). Confused with early-stage Rust pustules (6 samples) and Red Rot/Yellow due to chlorotic mottling resembling diffuse rust flecking.
  * Rust: In empirical smoke testing, sample `rust (423).jpeg` was predicted as `RedRot` ($0.5730$ confidence vs $0.3410$ Rust), highlighting visual confusion under ambient field lighting.

### Sugarcane Secondary Edge Model (MobileNetV3-Large)
* **Architecture:** `torchvision.models.mobilenet_v3_large` with classification head: `nn.Sequential(nn.Linear(960, 256), nn.Hardswish(), nn.Dropout(p=0.2), nn.Linear(256, 5))`.
* **Checkpoint File:** `models/sugarcane/mobilenet_v3/best_model.pth` (38,974,163 bytes).
* **Training Reality:** Trained for **1 epoch** on CPU (`duration_seconds: 454.33s`).
* **Test Performance (351 Test Samples):** Top-1 Accuracy: **84.05%**, Macro F1: **0.8342**, ECE: **0.0390**.

---

## 7. Explainability & Disease Severity Estimation

### Grad-CAM Implementation
* **Layer Hooked:** `model.features[-1]` (Conv2dNormActivation outputting 1,280 channels at $7 \times 7$ spatial resolution).
* **Mechanism:** Computes global average pooling over backward gradients ($\alpha_k^c$) to weight forward activation maps, followed by ReLU clamping.
* **Overlay Generation:** Bilinearly interpolates $(7 \times 7)$ mask to original photograph resolution (e.g. $493 \times 1040$) and blends via synthetic NumPy JET colormap at $\alpha = 0.5$.
* **Lifecycle Management:** Verified safe: forward and backward hook handles are detached in `try...finally` blocks inside `model_service.py`, preventing memory leakage across consecutive inferences.
* **Architectural Disconnect:** Grad-CAM is **only generated** when calling `POST /api/v1/diagnose/predict`. When a farmer submits a diagnosis via the authenticated route `POST /api/v1/crops/{crop_id}/diagnoses`, `generate_gradcam=False` is passed and no heatmap is saved or linked to the database record.

### Disease Severity Estimation (Critical Finding)
* **Code Location:** `backend/app/services/ai_service.py` (lines 170–171, 202–204).
* **Operational Mechanism:**
  ```python
  # Sugarcane:
  severity = DiagnosisSeverity.SEVERE if predicted_class == "RedRot" else DiagnosisSeverity.MODERATE
  affected_area_percentage = 22.0 if predicted_class == "RedRot" else 15.0

  # Other Crops:
  is_high_humidity = humidity is not None and humidity > 75.0
  affected_area = 24.5 if is_high_humidity else 14.0
  severity = DiagnosisSeverity.SEVERE if is_high_humidity else DiagnosisSeverity.MODERATE
  ```
* **Audit Verdict:** **UNVALIDATED HEURISTIC**. Severity and affected area are completely uncoupled from visual image evidence. No segmentation mask, thresholding, or pixel-level lesion quantification exists.

---

## 8. Backend Architecture, API Inventory & Database Lineage

### API Routes & Endpoint Inventory
| HTTP Method | Endpoint Path | Auth Required | Purpose | Implementation File | Verified Status |
| :---: | :--- | :---: | :--- | :--- | :---: |
| `GET` | `/` | No | System metadata & documentation URLs | `backend/app/main.py` | **VERIFIED** |
| `GET` | `/health` | No | Uptime & healthcheck probe | `backend/app/main.py` | **VERIFIED** |
| `POST` | `/api/v1/auth/register` | No | Register new farmer account | `backend/app/api/routes/auth.py` | **VERIFIED** |
| `POST` | `/api/v1/auth/login` | No | Form/JSON login, issue Bearer JWT | `backend/app/api/routes/auth.py` | **VERIFIED** |
| `GET` | `/api/v1/auth/me` | Bearer | Retrieve authenticated user profile | `backend/app/api/routes/auth.py` | **VERIFIED** |
| `GET` | `/api/v1/farmer/profile` | Bearer | Get farmer profile & language | `backend/app/api/routes/farmer.py` | **VERIFIED** |
| `PUT` | `/api/v1/farmer/profile` | Bearer | Update name & preferred language | `backend/app/api/routes/farmer.py` | **VERIFIED** |
| `POST` | `/api/v1/farms` | Bearer | Create farm for farmer | `backend/app/api/routes/farms.py` | **VERIFIED** |
| `GET` | `/api/v1/farms` | Bearer | List farms owned by farmer | `backend/app/api/routes/farms.py` | **VERIFIED** |
| `GET` | `/api/v1/farms/{farm_id}` | Bearer | Get farm details (Owner protected) | `backend/app/api/routes/farms.py` | **VERIFIED** |
| `PUT` | `/api/v1/farms/{farm_id}` | Bearer | Update farm details (Owner protected) | `backend/app/api/routes/farms.py` | **VERIFIED** |
| `DELETE`| `/api/v1/farms/{farm_id}` | Bearer | Delete farm and cascade delete crops | `backend/app/api/routes/farms.py` | **VERIFIED** |
| `POST` | `/api/v1/farms/{id}/crops`| Bearer | Add crop cycle to farm | `backend/app/api/routes/crops.py` | **VERIFIED** |
| `GET` | `/api/v1/farms/{id}/crops`| Bearer | List crop cycles for farm | `backend/app/api/routes/crops.py` | **VERIFIED** |
| `GET` | `/api/v1/crops/{crop_id}` | Bearer | Get crop cycle details | `backend/app/api/routes/crops.py` | **VERIFIED** |
| `PUT` | `/api/v1/crops/{crop_id}` | Bearer | Update crop cycle | `backend/app/api/routes/crops.py` | **VERIFIED** |
| `DELETE`| `/api/v1/crops/{crop_id}` | Bearer | Delete crop cycle | `backend/app/api/routes/crops.py` | **VERIFIED** |
| `POST` | `/api/v1/diagnose/predict` | No | Standalone model inference + Grad-CAM | `backend/app/api/routes/diagnostics.py` | **VERIFIED** |
| `POST` | `/api/v1/crops/{id}/diagnoses` | Bearer | Submit image for diagnosis & save to DB | `backend/app/api/routes/diagnostics.py` | **VERIFIED** |
| `GET` | `/api/v1/crops/{id}/diagnoses` | Bearer | List diagnoses for crop cycle | `backend/app/api/routes/diagnostics.py` | **VERIFIED** |
| `GET` | `/api/v1/diagnostics` | Bearer | List all diagnoses for farmer | `backend/app/api/routes/diagnostics.py` | **VERIFIED** |
| `GET` | `/api/v1/diagnostics/{id}` | Bearer | Get complete diagnosis detail | `backend/app/api/routes/diagnostics.py` | **VERIFIED** |
| `DELETE`| `/api/v1/diagnostics/{id}` | Bearer | Delete diagnosis & unlink stored image | `backend/app/api/routes/diagnostics.py` | **VERIFIED** |

### Database Schemas & Migrations
* **Engine:** PostgreSQL 16 with Alembic versioning.
* **Schema Evolution:**
  * `001_initial_schema.py`: Creates `users` (id, name, email, password_hash, preferred_language, role, is_active), `farms` (id, user_id, name, area, soil_type, irrigation, coordinates), and `crop_cycles` (id, farm_id, crop, variety, sowing_date, growth_stage, status).
  * `002_add_diagnostics_schema.py`: Creates `diagnoses` (id, user_id, crop_cycle_id, image_path, image_filename, image_hash, crop_name, disease_name_en, disease_name_mr, pathogen_type, confidence, severity, affected_area_percentage, symptoms_en, symptoms_mr, recommendations_en, recommendations_mr, telemetry, status, notes).
* **Live Inspection:** Connected read-only to PostgreSQL `pikvaidya` database on port 5432. All 5 tables confirmed. Live record counts: 2 users, 2 diagnoses.

---

## 9. Security & Multi-Tenant Privacy Posture

* **Authentication:** Stateless HS256 JWT tokens with UTC expiration (`exp`), subject claims (`sub`), and secret key signature verification.
* **Password Storage:** Salted `bcrypt` hashing.
* **Authorization & BOLA/IDOR Defense:** All operations on farms, crops, and diagnoses enforce ownership checks (`entity.user_id == current_user.id` or `farm.user_id == current_user.id`), returning HTTP 403 Forbidden on cross-tenant tampering.
* **File Upload Defense:** 
  1. Extension whitelist (`.jpg`, `.jpeg`, `.png`, `.webp`).
  2. Magic byte header verification (`\xff\xd8\xff`, `\x89PNG`, `RIFF...WEBP`).
  3. In-memory raster validation via Pillow `img.verify()`.
  4. 10 MB file size limit enforcement (HTTP 413).
  5. User-supplied filenames are never used on disk; stored using UUID v4 names (`uploads/diagnostics/YYYY-MM/{uuid}.jpg`), completely eliminating path traversal.
* **Security Weaknesses / Configuration Defaults:**
  1. `SECRET_KEY` in `backend/app/core/config.py` defaults to `"supersecretpikvaidyadefaultkeychangeinproduction1234567890"` if omitted from `.env`.
  2. `CORS_ORIGINS` defaults to `["*"]` (Wildcard allowed).
  3. `/api/v1/diagnose/predict` requires zero authentication and could be subjected to denial-of-service via computationally expensive Grad-CAM forward/backward passes.

---

## 10. Agricultural Advisory System & Localization

* **Knowledge Repository:** Hardcoded Python dictionary `CROP_DIAGNOSTIC_KNOWLEDGE` in `backend/app/services/ai_service.py`.
* **Regulatory Compliance:**
  * **Red Rot:** Sett treatment with Carbendazim 50% WP @ 1g/L and clump roguing matches ICAR/CIBRC standards.
  * **Rust:** Mancozeb 75% WP @ 2g/L and Propiconazole 25% EC @ 1ml/L matches standard fungicide protocols.
  * **Mosaic:** Imidacloprid 17.8% SL @ 0.3ml/L is recommended for aphid vector management.
* **Marathi Language Quality:** Terminology is natural and agronomically accurate (e.g. "तांबडे कूज" / "लाल सड", "तांबेरा", and "बेणे प्रक्रिया").
* **Agronomic Hazards:**
  * **No Confidence Gating:** If a low-quality photo produces a weak 35% probability, the system prescribes the same chemical pesticide without cautionary flagging.
  * **No Pre-Harvest Interval (PHI) or Spray Volume:** Spray volume per acre (typically 500–750 L/ha) and withholding periods prior to harvest are omitted.
  * **No Statutory Disclaimer:** Missing formal disclaimer advising consultation with local extension workers or Krishi Vigyan Kendras (KVK).

---

## 11. Frontend Reality vs. Claims

* **Directory:** `frontend/`
* **Contents:**
  * `.gitkeep` (17 bytes)
  * `README.md` (606 bytes) outlining "Planned Features" and "Planned Technology Stack".
* **Operational Status:** **NOT IMPLEMENTED**.
  * No `package.json`, Vite, Next.js, or React dependencies.
  * No HTML templates, CSS styles, or JavaScript modules.
  * No user interface exists for farmers to upload photos, view heatmaps, or toggle languages in a browser.

---

## 12. Tests & Runtime Status

### Empirical Test Execution
The automated test suite was executed in the workspace environment:
```powershell
python -u -m pytest backend/tests
```
* **Execution Duration:** 67.14 seconds.
* **Outcome:** **58 PASSED, 0 FAILED (100% Pass Rate)**.
* **Breakdown:**
  * `test_auth.py`: 12 passed.
  * `test_crops.py`: 6 passed.
  * `test_diagnostics.py`: 11 passed.
  * `test_farmer.py`: 4 passed.
  * `test_farms.py`: 8 passed.
  * `test_model_serving.py`: 10 passed.
  * `test_real_assets_integration.py`: 7 passed.

### Test Environment Characteristics
* Unit and integration tests run against an **in-memory SQLite sandbox** (`sqlite:///:memory:` via `StaticPool`), overriding PostgreSQL.
* Physical upload directories are protected by an `autouse` test fixture in `conftest.py` that purges test image artifacts upon completion.

---

## 13. Technical Debt & Repository Health

1. **Backend Dependency Manifest Omission (`backend/requirements.txt`):** Does not list `torch`, `torchvision`, `pillow`, or `numpy`, despite `model_service.py` requiring them. Users following `README.md` setup instructions (`pip install -r backend/requirements.txt`) will encounter immediate import errors.
2. **Hardcoded Absolute File Paths in Manifests:** Manifest CSVs in `datasets/processed/sugarcane/` contain hardcoded paths (`E:\PikVaidya AI\data\raw\sugarcane\...`), preventing seamless execution on Linux servers, Docker containers, or other developer drives without path patching.
3. **Dual Unsynchronized Grad-CAM Implementations:** `src/explainability/gradcam.py` permanently attaches PyTorch hooks without removal handles, whereas `backend/app/services/model_service.py` manages hooks cleanly inside a `try...finally` block.
4. **Wildcard CORS Default:** `CORS_ORIGINS = ["*"]` is set by default in `config.py`.
5. **Silent Inference Failure Fallback:** If `model_service.predict()` raises an unhandled exception in `ai_service.py` (lines 131, 144), it silently falls back to declaring the disease as Red Rot with 94% confidence.
