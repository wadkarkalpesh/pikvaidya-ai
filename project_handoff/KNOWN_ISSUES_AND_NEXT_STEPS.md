# Prioritized Issues & Remediation Roadmap: PikVaidya AI

**Document Version:** 1.0.0  
**Audit Date:** October 25, 2026  
**Auditor Consortium:** Senior Architecture, ML, Security, Agronomy & QA Panel  
**Ranking Standard:**
* **P0 — Critical:** Severe security, data-loss, legal liability, or dangerous farmer-facing pesticide advice.
* **P1 — High:** Broken core workflow, scientifically misleading diagnosis, or blocked multi-crop expansion.
* **P2 — Medium:** Significant reliability, portability, maintainability, or configuration risk.
* **P3 — Low:** Minor technical debt, training optimization, or documentation cleanup.

---

## 1. Prioritized Issue Register

| ID | Priority | Category | Finding / Defect Summary | Location in Codebase | Recommended Remediation |
| :---: | :---: | :--- | :--- | :--- | :--- |
| **ISS-01** | **P0** | **Agronomic / AI** | **Hardcoded Static Severity & Lesion Surface Area Heuristics:** The system claims to measure foliar necrosis, but assigns 22% SEVERE for Red Rot and 15% MODERATE for all other diseases via a static Python if-else rule. | `backend/app/services/ai_service.py` (lines 170-171, 202-204) | Deprecate static percentage; train an Otsu thresholding or lightweight MobileNetV3-UNet segmentation model to calculate true lesion area. |
| **ISS-02** | **P0** | **Safety / Liability**| **Absence of Confidence-Gated Pesticide Advisories:** A blurry or ambiguous photograph yielding a weak 35% probability triggers the exact same aggressive chemical pesticide prescription as a 99% confident diagnosis. | `backend/app/services/ai_service.py` (lines 161-176) | Implement a 3-tier confidence gateway: suppress chemical advice when confidence $<70\%$; prompt image re-capture when $<50\%$. |
| **ISS-03** | **P1** | **ML / Multi-Crop** | **Fake / Mock Diagnoses for 4 Out of 5 Crops:** Diagnostic requests for Cotton, Tomato, Soybean, and Onion bypass machine learning and return hardcoded single diseases with synthetic 91%–94% confidence. | `backend/app/services/ai_service.py` (lines 178-218) | Gate off non-sugarcane requests with HTTP 400 or label as demonstration until genuine multi-crop models are trained and integrated. |
| **ISS-04** | **P1** | **Architecture** | **Two Disconnected Diagnostic Ingestion Endpoints:** `/api/v1/diagnose/predict` runs real ML and Grad-CAM but cannot save to DB or return advisory; `/api/v1/crops/{id}/diagnoses` saves to DB but disables Grad-CAM and mocks non-sugarcane crops. | `backend/app/api/routes/diagnostics.py` | Unify into a single authenticated pipeline; add `heatmap_path` to `diagnoses` table and return both visual saliency and localized advisory. |
| **ISS-05** | **P1** | **Dataset Blocker** | **Severe Multi-Crop Dataset Gaps:** Soybean archive contains 100% Healthy leaves (0 disease images); Cotton dataset is completely absent (0 images); Onion dataset is an un-downloaded PDF paper. | `data/raw/` | Ingest external infected leaf datasets: Kaggle Cotton Leaf Disease, Mendeley Onion Folia, and infected Soybean Rust datasets before scheduling training. |
| **ISS-06** | **P1** | **Frontend** | **Complete Absence of Client Frontend:** The `frontend/` directory is completely empty except for a placeholder README. No web or mobile UI exists for farmers. | `frontend/` | Scaffold a modern, accessible PWA client (React/Next.js/Vite) with Marathi/English language switching and camera upload support. |
| **ISS-07** | **P2** | **Security** | **Hardcoded Fallback SECRET_KEY & Wildcard CORS:** `config.py` provides a default hardcoded secret key string and sets `CORS_ORIGINS = ["*"]` by default. | `backend/app/core/config.py` (lines 12, 30) | Remove default string; require `SECRET_KEY` in environment; restrict CORS to designated client origins. |
| **ISS-08** | **P2** | **Dependencies** | **Missing Core Dependencies in `backend/requirements.txt`:** `backend/requirements.txt` omits `torch`, `torchvision`, `pillow`, and `numpy`. Users following the README setup instructions encounter immediate import failures. | `backend/requirements.txt` | Synchronize `backend/requirements.txt` with root `requirements.txt` to include computer vision and deep learning dependencies. |
| **ISS-09** | **P2** | **Portability** | **Hardcoded Absolute Windows File Paths in Manifests:** Manifest CSVs in `datasets/processed/sugarcane/` contain absolute paths (`E:\PikVaidya AI\...`), preventing cross-platform Linux or Docker execution. | `datasets/processed/sugarcane/*.csv` | Re-generate manifests using project-relative paths (e.g. `data/raw/sugarcane/...`) and update `dataset.py` to resolve paths relative to repository root. |
| **ISS-10** | **P2** | **Code Hygiene** | **Dual Unsynchronized Grad-CAM Implementations:** `src/explainability/gradcam.py` permanently attaches PyTorch hooks without removal handles, while `backend/app/services/model_service.py` manages hooks cleanly inside `try...finally`. | `src/explainability/gradcam.py` | Refactor `src.explainability.GradCAM` to use hook handles and provide an explicit `close()` or context manager method. |
| **ISS-11** | **P2** | **Legal / Agronomy**| **Missing Statutory Disclaimers & Pre-Harvest Intervals (PHI):** System omits mandatory warnings under the Insecticides Act, 1968, as well as spray dilution volumes per hectare and Pre-Harvest withholding periods. | `backend/app/services/ai_service.py` | Append statutory legal disclaimers, PPE notices, water dilution standards (500–750 L/ha), and withholding intervals to all chemical advice. |
| **ISS-12** | **P3** | **ML Optimization** | **Single-Epoch Model Training Limitation:** Both EfficientNet-B0 and MobileNetV3 were trained for only 1 epoch on CPU, representing preliminary adaptation rather than converged weights. | `src/training/train.py`, `models/sugarcane/` | Train on GPU for 15–20 epochs with Cosine Annealing, early stopping, and heavy data augmentation (perspective shifts, color jitter, solarization). |
| **ISS-13** | **P3** | **Robustness** | **Absence of Out-of-Distribution (OOD) Foliar Validator:** Any non-leaf image (e.g. an apple, a person, a vehicle) uploaded to the API is forced into one of the 5 sugarcane classes with soft probabilities. | `backend/app/services/model_service.py` | Train a lightweight binary foliage detector or Mahalanobis OOD filter to reject non-leaf images prior to classification. |
| **ISS-14** | **P3** | **Testing** | **Starlette Deprecation Warning in Test Suite:** `StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.` | `backend/tests/conftest.py` | Migrate test client fixtures to direct `httpx.AsyncClient` with `ASGITransport`. |

---

## 2. Actionable Step-by-Step Remediation Roadmap

### Phase 1: Agronomic Safety & Security Hardening (Immediate Priority)
1. **Confidence Gating in `ai_service.py` (Fix for ISS-02):**
   * Introduce a confidence filter:
     ```python
     if confidence < 0.70:
         recommendations_en = (
             "Diagnosis confidence is below verified threshold. Please do not apply chemical "
             "pesticides without physical verification by an agricultural extension worker."
         )
         recommendations_mr = (
             "निदानाची खात्री कमी आहे. कृषी सहाय्यक किंवा तज्ञांच्या सल्ल्याशिवाय कोणतीही रासायनिक "
             "कीटकनाशके फवारू नका."
         )
     ```
2. **Statutory Legal Disclaimer (Fix for ISS-11):**
   * Append standard disclaimer to all diagnostic responses advising verification with local Krishi Vigyan Kendras (KVK).
3. **Environment Security Hardening (Fix for ISS-07):**
   * In `backend/app/core/config.py`, remove the default hardcoded string for `SECRET_KEY` and validate that a strong key exists in `.env`.
   * Restrict `CORS_ORIGINS` to trusted frontend domains.
4. **Synchronize Dependencies (Fix for ISS-08):**
   * Update `backend/requirements.txt` to include `torch`, `torchvision`, `pillow`, and `numpy`.

### Phase 2: Architectural Unification & Diagnostic Pipeline Merge (High Priority)
1. **Unify Ingestion Routes (Fix for ISS-04):**
   * Consolidate `/api/v1/diagnose/predict` into `POST /api/v1/crops/{crop_id}/diagnoses`.
   * Add a `heatmap_path` column to the `Diagnosis` SQLAlchemy model and generate Alembic revision `003_add_heatmap_column.py`.
   * Automatically generate and persist Grad-CAM heatmaps for authenticated diagnoses.
2. **Path Portability Fix (Fix for ISS-09):**
   * Re-generate manifest CSV files in `datasets/processed/sugarcane/` using relative paths (`data/raw/sugarcane/...`).
3. **Refactor Standalone GradCAM (Fix for ISS-10):**
   * Update `src/explainability/gradcam.py` to store hook handles and remove them upon completion to prevent memory accumulation.

### Phase 3: Dataset Ingestion & Computer Vision Maturation
1. **Ingest Missing Crop Datasets (Fix for ISS-05):**
   * Download the Kaggle Cotton Leaf Disease dataset.
   * Download the Mendeley Onion Foliar Disease dataset.
   * Procure infected Soybean foliar imagery (Soybean Rust, Frogeye Leaf Spot).
2. **Train Multi-Epoch Models on GPU (Fix for ISS-12):**
   * Train EfficientNet-B0 and MobileNetV3 for 15–20 epochs with early stopping on validation macro-F1.
   * Train dedicated models for Tomato, Onion, Cotton, and Soybean, removing the simulated mock code in `ai_service.py` (Fix for ISS-03).
3. **Implement Real Lesion Segmentation (Fix for ISS-01):**
   * Replace the hardcoded 22% / 15% rule with an adaptive Otsu thresholding or U-Net segmentation model operating on leaf contours to compute genuine necrosis surface area.
4. **Implement Out-of-Distribution Foliage Filter (Fix for ISS-13):**
   * Deploy a lightweight binary classifier to verify that uploaded imagery represents valid crop foliage.

### Phase 4: Frontend Development & Farmer Deployment (Fix for ISS-06)
1. **Client UI Implementation:**
   * Build a lightweight, responsive Progressive Web App (PWA) using Vite + React or Next.js.
   * Implement bilingual Marathi/English toggling.
   * Integrate camera capture, offline caching, and interactive Grad-CAM heatmap visualization.
2. **Field Trials & Agronomist Endorsement:**
   * Conduct pilot field trials across 50 smallholder sugarcane farms in Western Maharashtra.
   * Obtain written certification from MPKV Rahuri or Vasantdada Sugar Institute (VSI).
