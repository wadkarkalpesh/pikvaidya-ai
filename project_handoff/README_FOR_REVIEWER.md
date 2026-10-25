# Reviewer Guide: PikVaidya AI (पिकवैद्य AI)
**Target Audience:** Independent AI Technical Reviewer / Senior Software Architect / ML Reviewer  
**Audit Date:** October 25, 2026  
**Project Root:** `E:\PikVaidya AI`  
**Git Branch & Status:** `main` (clean working tree, commit state synchronized with `origin/main`)  
**Audit Conducted By:** Multi-Agent Technical Audit Consortium (Senior Software Architect, Lead ML/MLOps Engineer, Backend & DB Architect, Security Reviewer, Agricultural Validation Engineer, QA Engineer)

---

## 1. What PikVaidya AI Is Intended to Do

**PikVaidya AI** is envisioned as an explainable, multimodal, bilingual (Marathi & English) agricultural decision-support platform for smallholder farmers in India (with primary focus on Maharashtra). Its conceptual end-to-end mission includes:
1. Enabling farmers to register, configure their farms (location, acreage, soil, irrigation), and track crop cycles.
2. Ingesting field photographs of foliage from mobile cameras.
3. Classifying crop diseases across 5 key commercial crops: **Sugarcane**, **Tomato**, **Onion**, **Cotton**, and **Soybean**.
4. Providing visual explainability via **Grad-CAM saliency heatmaps** to verify pathological focus.
5. Quantifying disease severity (percentage of leaf necrosis/chlorosis).
6. Fusing environmental telemetry (temperature, relative humidity, soil moisture) to assess disease pressure.
7. Delivering agronomic recommendations (cultural, biological, and CIBRC/ICAR-approved chemical treatments) in both **Marathi (`mr`)** and **English (`en`)**.
8. Storing historical diagnoses and connecting farmers to agricultural experts and Krishi Vigyan Kendras (KVK).

---

## 2. Current Architecture & Technology Stack

The project repository is structured as a monorepo consisting of:
* **Backend API Gateway (`backend/app/`):** Built with **FastAPI 0.110+**, **Python 3.13**, and **Uvicorn**. Employs **SQLAlchemy 2.0+** ORM for relational persistence and **Alembic 1.20+** for database schema migrations.
* **Database Layer (`backend/alembic/`, `backend/app/models/`):** **PostgreSQL 16** with `psycopg` 3 binary driver. 4 relational entities: `User`, `Farm`, `CropCycle`, and `Diagnosis`. (Docker Compose service configured in `infra/docker-compose.yml`).
* **Deep Learning Computer Vision Backbone (`src/`, `models/`):** **PyTorch 2.1+** and **Torchvision 0.16+**. Contains transfer learning implementations for **EfficientNet-B0** (Primary Model A) and **MobileNetV3-Large** (Edge Model B).
* **Explainable AI Engine (`src/explainability/`, `backend/app/services/model_service.py`):** **Grad-CAM** hooked into the final convolutional feature extractor (`model.features[-1]`) with synthetic RGB JET colormap blending.
* **Testing Infrastructure (`backend/tests/`):** **Pytest 9.1+** with **HTTPX TestClient** and in-memory SQLite isolation. 58 automated unit, security, and real-asset regression tests.
* **Client Frontend (`frontend/`):** **NOT IMPLEMENTED**. Only a placeholder `.gitkeep` and a 17-line README exist.

---

## 3. Current Verified Capabilities (What Genuinely Works Today)

Through direct code execution and runtime empirical verification, the following capabilities are **VERIFIED WORKING**:
1. **Sugarcane Vision Model Inference:** The PyTorch checkpoint at `models/sugarcane/efficientnet_b0/best_model.pth` loads cleanly into memory without missing keys. Evaluates test leaf images across 5 classes (`Healthy`, `Mosaic`, `RedRot`, `Rust`, `Yellow`) with finite confidence scores summing to $1.0000 \pm 0.0001$.
2. **Grad-CAM Lesion Heatmap Generation:** Hooks `model.features[-1]`, extracts $(7 \times 7)$ activation maps, normalizes to $[0.0, 1.0]$, resizes via bilinear interpolation to original photograph dimensions, blends at $\alpha = 0.5$ with JET colormap, and safely detaches hooks without memory leaks across consecutive requests.
3. **Standalone ML Prediction Route (`POST /api/v1/diagnose/predict`):** Validates image MIME headers (magic bytes for JPEG, PNG, WEBP), enforces a 10 MB size limit, decodes with Pillow, executes EfficientNet-B0 inference, and returns class scores and heatmap file paths.
4. **JWT Authentication & Multi-Tenant Authorization:** Farmer registration (`POST /api/v1/auth/register`), OAuth2/JSON login (`POST /api/v1/auth/login`), profile retrieval (`GET /me`, `GET/PUT /farmer/profile`). Password hashing uses salted `bcrypt`. Multi-tenant farm and crop cycle isolation is enforced (BOLA/IDOR protected).
5. **Database Schemas & Persistence:** PostgreSQL migrations up to revision `002_add_diagnostics_schema` are applied and verified. Foreign-key cascading deletions cleanly unlink crop cycles and diagnoses when a farm is removed.
6. **Automated Test Suite:** 58 tests in `backend/tests/` execute and pass with a 100% success rate (0 failures) in under 70 seconds.

---

## 4. Important Missing Components & Critical Architectural Gaps

An independent reviewer must be aware of the following disconnects and limitations:

### 🚨 Critical Disconnect 1: Two Disconnected Diagnostic Ingestion Pathways
There are two separate endpoints in `backend/app/api/routes/diagnostics.py`:
1. `POST /api/v1/diagnose/predict`: Unauthenticated standalone route. Calls `model_service.predict()`. Actually executes the trained PyTorch Sugarcane model and Grad-CAM. **Does NOT save anything to the database and returns NO agronomic advisory.**
2. `POST /api/v1/crops/{crop_id}/diagnoses`: Authenticated farmer route. Calls `ai_service.analyze_crop_image()`. Persists record to the database. **Does NOT generate Grad-CAM heatmaps, hardcodes disease severity, and simulates mock data for non-sugarcane crops.**

### 🚨 Critical Disconnect 2: Fake/Mock Diagnoses for 4 Out of 5 Crops
While the platform advertises multi-crop diagnostic support:
* **Sugarcane:** Uses real trained PyTorch vision model.
* **Cotton, Tomato, Soybean, Onion:** **Zero machine learning is executed.** In `backend/app/services/ai_service.py` (lines 178–218), any request for cotton unconditionally returns *Cotton Leaf Curl Virus*; any tomato request unconditionally returns *Early Blight*; any soybean request unconditionally returns *Soybean Rust*; any onion request unconditionally returns *Purple Blotch*. Confidence is hardcoded to $0.94$ (high humidity) or $0.91$ (normal).

### 🚨 Critical Disconnect 3: Static Heuristic "Severity Estimation"
The system claims to measure disease severity and affected foliage area percentage, but executes a **hardcoded binary heuristic** in `ai_service.py`:
```python
severity = DiagnosisSeverity.SEVERE if predicted_class == "RedRot" else DiagnosisSeverity.MODERATE
affected_area_percentage = 22.0 if predicted_class == "RedRot" else 15.0
```
No image segmentation (U-Net, DeepLab, Mask R-CNN, or contour thresholding) is performed.

### 🚨 Critical Disconnect 4: Complete Absence of Frontend Client
`frontend/` contains no HTML, CSS, JavaScript, TypeScript, React, Next.js, or Flutter code. It is 100% empty except for a markdown placeholder. The complete farmer experience currently exists only as backend HTTP endpoints.

### 🚨 Critical Disconnect 5: Lack of Confidence Gating on Pesticide Advice
If an ambiguous or low-quality photo produces a weak 38% or 45% model prediction, the backend returns the exact same full-strength chemical pesticide prescription (e.g. Carbendazim, Mancozeb, Propiconazole) as it would for a 99% confident diagnosis, creating agronomic and economic risk for farmers.

---

## 5. How the Reviewer Should Approach This Project

As an independent technical reviewer, follow this systematic approach:
1. **Start with [`AI_REVIEW_CONTEXT.md`](file:///e:/PikVaidya%20AI/project_handoff/AI_REVIEW_CONTEXT.md):** This self-contained file provides the executive summary and technical baseline needed to conduct a full review without needing the repository source code pasted into your session.
2. **Review [`PROJECT_STATE_REPORT.md`](file:///e:/PikVaidya%20AI/project_handoff/PROJECT_STATE_REPORT.md):** Trace the 16-step real application workflow to understand the boundary between working backend endpoints and unimplemented frontend/mock components.
3. **Inspect [`ML_AND_DATASET_AUDIT.md`](file:///e:/PikVaidya%20AI/project_handoff/ML_AND_DATASET_AUDIT.md):** Review the training methodology (1 epoch CPU training), dataset provenance (2,521 sugarcane field images, 210 pruned duplicates), and the critical dataset blockers for Cotton (0 images) and Soybean (100% healthy images).
4. **Inspect [`API_DATABASE_AND_SECURITY.md`](file:///e:/PikVaidya%20AI/project_handoff/API_DATABASE_AND_SECURITY.md):** Verify the schema definitions, OWASP Top 10 security audit results, and endpoint specifications.
5. **Inspect [`AGRICULTURAL_ADVISORY_AUDIT.md`](file:///e:/PikVaidya%20AI/project_handoff/AGRICULTURAL_ADVISORY_AUDIT.md):** Review the regulatory compliance of pesticide recommendations against ICAR/CIBRC standards, vernacular Marathi translation quality, and missing statutory disclaimers.
6. **Consult [`KNOWN_ISSUES_AND_NEXT_STEPS.md`](file:///e:/PikVaidya%20AI/project_handoff/KNOWN_ISSUES_AND_NEXT_STEPS.md):** Use the prioritized (P0 to P3) roadmap to guide code enhancements and milestone planning.
