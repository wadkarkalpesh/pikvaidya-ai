# Phase 1 & 2 Implementation Report: Diagnostic Safety, Unified Workflow & Security Hardening

**Document Version:** 1.0.0  
**Date:** October 25, 2026  
**System:** PikVaidya AI (पिकवैद्य AI) Backend  
**Git Branch:** `main`  
**Execution Team:** Multi-Agent Technical Implementation Consortium  
- **Agent 1:** Lead System Architect & Security Engineer  
- **Agent 2:** Agricultural AI & Diagnostic Safety Engineer  
- **Agent 3:** Lead Database & Backend Engineer  
- **Agent 4:** Quality Assurance & Empirical Validation Engineer  

---

## 1. Executive Summary & Verification Findings (Phase A)

Prior to implementing any modifications, a thorough source code verification of the existing codebase was conducted against the initial project handoff audit findings. Every critical finding reported in the handoff was verified against the actual source code:

1. **Two-Pathway Architecture Confirmed:**
   - `POST /api/v1/diagnose/predict` (in `backend/app/api/routes/diagnostics.py`) was an unauthenticated route running genuine PyTorch sugarcane inference with Grad-CAM, but had zero database persistence and generated no agronomic advisory.
   - `POST /api/v1/crops/{crop_id}/diagnoses` was an authenticated route persisting records, but bypassed Grad-CAM generation, hardcoded severity values, and simulated fake results for all non-sugarcane crops.
2. **Fabricated Predictions Confirmed:**
   - In `backend/app/services/ai_service.py` (lines 178–218), crops other than sugarcane (Cotton, Tomato, Soybean, Onion) bypassed machine learning entirely. The system unconditionally returned hardcoded disease names (CLCuV, Early Blight, Soybean Rust, Purple Blotch) with synthetic confidence scores (0.91 or 0.94) and unconditional chemical prescriptions.
   - In the sugarcane pathway of `ai_service.py`, if image loading or model inference threw an exception, it caught `Exception` and silently defaulted to `predicted_class = "RedRot"`, `confidence = 0.94`.
3. **Hardcoded Severity Confirmed:**
   - Neither route performed any pixel-level segmentation or contour area quantification. `ai_service.py` assigned fixed heuristic values: Red Rot = `DiagnosisSeverity.SEVERE` (22.0% affected area); all other diseases = `DiagnosisSeverity.MODERATE` (15.0% affected area).
4. **Missing Confidence Gating Confirmed:**
   - An ambiguous or out-of-focus leaf yielding 35% probability triggered the exact same aggressive chemical pesticide prescription as a 99% confident diagnosis.
5. **Configuration and Security Risks Confirmed:**
   - Hardcoded default `SECRET_KEY` in `backend/app/core/config.py`.
   - Wildcard CORS (`CORS_ORIGINS = ["*"]`) combined with `allow_credentials=True` in `backend/app/main.py`.
   - Incomplete backend dependency manifest (`backend/requirements.txt` was missing `torch`, `torchvision`, `pillow`, `numpy`, and `pyyaml`).

---

## 2. Prevention of Misleading Predictions (Phase B)

The diagnostic pipeline has been re-architected to enforce strict scientific boundaries and protect farmers from hazardous or fabricated advice:

1. **Strict Crop Model Boundary Enforcement:**
   - The diagnostic engine now explicitly checks whether a configured, genuine machine learning model exists for the target crop.
   - Currently, only `sugarcane` possesses a trained PyTorch model checkpoint (`models/sugarcane/efficientnet_b0/best_model.pth`).
   - If an inference request is submitted for any unsupported crop (e.g. Cotton, Tomato, Soybean, Onion, etc.), the system immediately rejects the request with HTTP 400 Bad Request and a structured explanation:
     > `"AI diagnosis is currently unavailable for crop '{crop_name}'. Model inference is currently only supported for: sugarcane."`
   - Simulated disease profiles and synthetic confidence scores (0.91, 0.94, 0.88) have been completely removed from the execution path.
2. **Honest Severity Reporting:**
   - Because no image segmentation model (e.g., U-Net or DeepLab) is currently deployed to measure lesion surface area, the system no longer outputs hardcoded percentages (22.0% or 15.0%).
   - `DiagnosisSeverity` has been extended with `UNAVAILABLE` and `UNVALIDATED`.
   - For diseased foliage, `severity` is reported as `UNAVAILABLE` (or `UNVALIDATED`) and `affected_area_percentage` is set to `null` (`None`).
   - For healthy foliage, `severity` is reported as `HEALTHY` with `affected_area_percentage` = `0.0`.
3. **Confidence-Aware Safety Gating:**
   - A conservative, 3-tier confidence gateway has been implemented in `DiagnosticService`:
     - **Tier 1: High Confidence ($\ge 75\%$):**  
       `advisory_status = "HIGH_CONFIDENCE"`. Issue verified diagnosis, cultural management, and CIBRC-registered chemical measures. Every chemical recommendation includes the mandatory ICAR/CIBRC citation, an expert review notice, and the statutory disclaimer under the Insecticides Act, 1968.
     - **Tier 2: Moderate Confidence / Ambiguous ($50\% \le \text{Confidence} < 75\%$):**  
       `advisory_status = "LOW_CONFIDENCE_WARNING"`. **All chemical prescriptions are strictly suppressed.** The response advises daylight foliar inspection, retaking a clearer in-focus close-up photograph, and physical verification with a Taluka Agricultural Officer or local KVK before chemical procurement.
     - **Tier 3: Low Confidence / High Uncertainty ($< 50\%$):**  
       `advisory_status = "UNCERTAIN_PREDICTION"`. **All specific pathology and chemical prescriptions are suppressed.** The disease name is set to `"Uncertain Foliar Symptoms"` (`"अस्पष्ट पानांवरील लक्षणे"`). The farmer is advised that the image is inconclusive and is instructed to retake the photo under natural indirect sunlight or consult a KVK agronomist.
4. **Mandatory Agricultural Disclaimers:**
   - Every advisory returned by the system carries the statutory disclaimer clarifying that model confidence alone does not establish diagnostic ground truth, and that pesticide efficacy depends on localized soil and weather conditions.

---

## 3. Unified Diagnostic Workflow Architecture (Phase C)

Both diagnostic pathways have been unified under a single coherent internal service: `app.services.diagnostic_service.diagnostic_service`:

```
                           Incoming Diagnostic Request
                                       │
                ┌──────────────────────┴──────────────────────┐
                ▼                                             ▼
  POST /api/v1/diagnose/predict                 POST /api/v1/crops/{crop_id}/diagnoses
  (Public Standalone Route)                     (Authenticated Farmer Route)
                │                                             │
                │                                    Verify Crop Ownership
                │                                    (404 if missing, 403 if unauthorized)
                │                                             │
                └──────────────────────┬──────────────────────┘
                                       ▼
                       Unified Diagnostic Service Pipeline
                       ───────────────────────────────────
                       1. Validate Image (Extension, Magic Bytes,
                          10 MB Limit, Pillow Raster Verify)
                       2. Enforce Crop Model Support Boundary
                          (Reject unsupported crops with HTTP 400)
                       3. Execute Genuine PyTorch Model Forward Pass
                       4. Generate Grad-CAM Heatmap (if requested)
                       5. Apply Confidence-Aware Safety Evaluation
                       6. Formulate CIBRC/ICAR Advisory & Disclaimers
                                       │
                ┌──────────────────────┴──────────────────────┐
                ▼                                             ▼
     Return PredictResponse                       Persist to `diagnoses` table
     (Ephemeral, no DB write,                     (User ID, Crop ID, Hash, Heatmap,
      includes safety details)                     Advisory Status, Symptoms, Recs)
                                                              │
                                                              ▼
                                                 Return DiagnosisDetailResponse
```

### Architectural Guarantees:
- **Security Isolation:** The standalone route `/api/v1/diagnose/predict` cannot read, write, or access farmer records or database sessions.
- **Explainability Parity:** The authenticated route now supports Grad-CAM generation (`generate_gradcam=True`) and stores the resulting heatmap path in the database.
- **Consistent Schemas:** Both endpoints return unified fields: `advisory_status`, `heatmap_path`, model prediction scores, and safe bilingual advisories.

---

## 4. Security & Configuration Hardening (Phase D)

1. **JWT Secret Protection:**
   - `backend/app/core/config.py` now implements environment-aware validation.
   - If `ENVIRONMENT == "production"`, a secure, non-default `SECRET_KEY` of at least 32 characters is strictly required. Any attempt to boot in production with the default placeholder raises an immediate startup configuration exception.
   - Secret key values are masked and never exposed in logs or console output.
2. **CORS Hardening:**
   - Wildcard CORS (`["*"]`) is strictly forbidden in production.
   - In development, default origins are restricted to local frontend ports (`http://localhost:3000`, `http://localhost:5173`, `http://127.0.0.1:3000`, `http://127.0.0.1:5173`).
   - `allow_credentials` is dynamically disabled if a wildcard origin is detected to prevent browser fetch policy violations.
3. **Unified Media Ingestion:**
   - Centralized in `storage_service.validate_upload_content`:
     - Whitelist check against `.jpg`, `.jpeg`, `.png`, `.webp`.
     - Magic bytes verification (`\xff\xd8\xff`, `\x89PNG`, `RIFF...WEBP`).
     - 10 MB maximum size cap (returns HTTP 413).
     - Pillow raster decodability check (`Image.open().verify()`, returns HTTP 400 for corrupted or truncated files).
4. **Dependency Manifest Synchronization:**
   - `backend/requirements.txt` was synchronized with the active code implementation, adding `torch>=2.1.0`, `torchvision>=0.16.0`, `pillow>=10.0.0`, `numpy>=1.26.0`, and `pyyaml>=6.0.1`.

---

## 5. Record of Changed Files

| File Path | Type | Reason for Modification |
| :--- | :---: | :--- |
| `backend/app/core/config.py` | Modified | Added `ENVIRONMENT`, diagnostic confidence thresholds, production `SECRET_KEY` validation, and safe CORS defaults. |
| `backend/app/main.py` | Modified | Made CORS credential handling safe when wildcard origins are present. |
| `backend/app/models/diagnosis.py` | Modified | Added `UNAVAILABLE` and `UNVALIDATED` to `DiagnosisSeverity`; added `heatmap_path` and `advisory_status` columns. |
| `backend/app/schemas/diagnosis.py` | Modified | Added `heatmap_path` and `advisory_status` to `DiagnosisDetailResponse` and `PredictResponse`. |
| `backend/app/services/storage.py` | Modified | Added `validate_upload_content` with Pillow raster verification; updated `save_diagnostic_image` to use unified validation. |
| `backend/app/services/diagnostic_service.py` | **Created** | Core unified diagnostic service with genuine model boundaries, confidence gating, CIBRC/ICAR knowledge base, and Grad-CAM. |
| `backend/app/services/ai_service.py` | Modified | Refactored to delegate to `diagnostic_service`, removed simulated fake predictions for unsupported crops, preserved educational knowledge base. |
| `backend/app/services/__init__.py` | Modified | Exported `diagnostic_service` and `DiagnosticService`. |
| `backend/app/api/routes/diagnostics.py` | Modified | Unified both endpoints to delegate to `diagnostic_service`, added Grad-CAM support to authenticated route, hardened error handling. |
| `backend/alembic/versions/003_add_diagnostic_metadata.py` | **Created** | Non-destructive database migration adding `heatmap_path` and `advisory_status` columns to `diagnoses` table. |
| `backend/requirements.txt` | Modified | Added required runtime ML dependencies (`torch`, `torchvision`, `pillow`, `numpy`, `pyyaml`). |
| `backend/tests/conftest.py` | Modified | Updated `test_crop` fixture to `Sugarcane` and added `unsupported_crop` fixture (`Cotton`). |
| `backend/tests/test_diagnostics.py` | Modified | Added tests for unsupported crop rejection, Grad-CAM generation, confidence gating tiers, and unvalidated severity. |
| `backend/tests/test_diagnostic_service.py` | **Created** | Comprehensive unit test suite for `DiagnosticService` methods and threshold evaluations. |
| `scripts/verify_live_postgres.py` | **Created** | Live PostgreSQL integration verification script. |
| `project_handoff/PHASE_1_2_IMPLEMENTATION_REPORT.md` | **Created** | This comprehensive implementation report. |
| `project_handoff/UPDATED_API_CONTRACT.md` | **Created** | Updated API specification document. |
| `project_handoff/UPDATED_TEST_RESULTS.md` | **Created** | Complete test execution report covering SQLite and live PostgreSQL. |
| `project_handoff/REMAINING_BLOCKERS.md` | **Created** | Detailed accounting of remaining ML, dataset, and agronomic blockers. |

---

## 6. Verification Summary

- **Automated Unit & API Test Suite:** 71 tests passing on in-memory SQLite (0 failures, 100% pass rate in 18.40s).
- **Live PostgreSQL Integration Verification:** 100% passed against live PostgreSQL 16 on port 5432. All pre-existing database rows (2 records) were preserved completely without destruction or resets.
- **Git State:** Clean working tree on branch `main` with all changes tracked and zero untracked artifacts outside of `project_handoff/` and `scripts/`.
