# PikVaidya AI — Production Readiness Report

**Project:** PikVaidya AI (Explainable Crop-Disease Diagnosis System)  
**Target Crop:** Sugarcane (*Saccharum officinarum*)  
**Evaluation Date:** October 2026  
**Auditor Roles:** Lead Software Engineer, Lead ML Engineer, Security Engineer, Agricultural AI Validation Engineer  
**Overall Readiness Classification:** **CONDITIONAL PASS (STAGING READY / BLOCKED FOR UNATTENDED PRODUCTION)**

---

## 1. Executive Summary & Status Scorecard

PikVaidya AI was subjected to an end-to-end, multi-phase technical, operational, security, and agronomic audit. Testing was conducted on actual repository checkpoints, real image assets, live PostgreSQL persistence, and authenticated REST endpoints without data fabrication.

| Audit Phase | Focus Area | Status | Key Justification |
| :--- | :--- | :---: | :--- |
| **Phase 1** | Baseline & Reproducibility | **PASS** | Checkpoints verified, zero data leakage across 1,615 train / 345 val / 351 test images (0 MD5 collisions). |
| **Phase 2** | Model Accuracy & Calibration | **PASS** | EfficientNet-B0 achieved **93.16% accuracy**, **0.9286 macro F1**, ECE **0.0899** on 351 held-out test samples. |
| **Phase 2 (Field)** | Independent Field Validation | **NOT TESTED** | `PlantDoc-Dataset-master.zip` contains 0 sugarcane images. No independent field dataset exists in the workspace. |
| **Phase 3** | Severity & Lesion Estimation | **FAIL** | Severity and affected area (22% / 15%) are **hardcoded static heuristics** in `ai_service.py`, not vision model outputs. |
| **Phase 4** | Grad-CAM Explainability | **PASS** | Layer `features[-1]` (1280 channels) generates aligned heatmaps with synthetic JET overlay; hooks clean up with 0 leaks. |
| **Phase 5** | API & Database Security | **PASS** | Multi-tenant isolation (HTTP 403 on IDOR), magic header byte checks, 10MB limit, token expiration/signature tests passing. |
| **Phase 6** | Agricultural Advisory Review | **NEEDS EXPERT REVIEW** | Basic CIBRC chemical treatments present in English and Marathi, but **no confidence threshold gating** exists. |
| **Phase 7** | Operational Readiness | **PASS** | Full pytest test suite passing (58/58 tests), PostgreSQL 16 migrations clean, latency ~141ms (inference) / ~776ms (Grad-CAM). |

---

## 2. Environment & System Specifications

* **Operating System:** Windows 11 Enterprise (x64)
* **Python Runtime:** Python 3.13.15 (AMD64)
* **Deep Learning Framework:** PyTorch 2.6.0+cpu, Torchvision 0.21.0+cpu
* **Web Framework:** FastAPI 0.115.11 / Starlette 0.46.1 / Uvicorn 0.34.0
* **Persistence Layer:** PostgreSQL 16 on `localhost:5432`, SQLAlchemy 2.0.40, Alembic 1.15.1
* **Database Migration Head:** `002_add_diagnostics_schema` (tables: `users`, `farms`, `crop_cycles`, `diagnoses`)
* **Primary Checkpoint:** `models/sugarcane/efficientnet_b0/best_model.pth` (48.6 MB, TorchScript / StateDict)
* **Comparison Checkpoint:** `models/sugarcane/mobilenet_v3/best_model.pth` (38.9 MB)

---

## 3. Operational Performance Benchmarks

Inference latency was benchmarked over consecutive runs on local CPU using standard sugarcane leaf imagery (1040 x 493 px):

| Metric | EfficientNet-B0 (Standard Inference) | EfficientNet-B0 + Grad-CAM Heatmap | Target SLA |
| :--- | :---: | :---: | :---: |
| **Warmup Run** | 598.66 ms | 1182.34 ms | < 2000 ms |
| **p50 (Median)** | **141.35 ms** | **776.73 ms** | < 300 ms (Std) / < 1200 ms (CAM) |
| **p95** | **190.65 ms** | **1095.74 ms** | < 500 ms (Std) / < 1500 ms (CAM) |
| **Min - Max** | 123.82 ms – 598.66 ms | 683.36 ms – 1182.34 ms | Consistent |
| **Memory Leakage** | 0 MB growth over 20 runs | 0 hook / tensor leaks | Leak-free lifecycle |

### Hook Lifecycle Integrity
Grad-CAM forward and backward hooks are encapsulated within a `try ... finally` block inside `app/services/model_service.py`. PyTorch hook handles are explicitly removed upon CAM tensor extraction, ensuring zero memory growth or lingering backward graph references across multiple diagnostic requests.

---

## 4. Key Architectural & Safety Vulnerabilities Discovered

### A. Provenance of Disease Severity (CRITICAL DEFECT)
* **Observation:** The API returns `severity: "SEVERE"` and `affected_area_percentage: 22.0%` for Red Rot, or `"MODERATE"` and `15.0%` for other diseases.
* **Audit Finding:** Traced directly to lines 170–171 and line 204 of `backend/app/services/ai_service.py`. These metrics are static hardcoded heuristics based strictly on class string matching. No segmentation mask, U-Net, or pixel lesion calculation is performed.
* **Risk:** Farmers and agronomists may assume the AI quantitatively measured leaf necrosis area.
* **Mandated Action:** Mark severity field as `"HEURISTIC_PREVIEW"` or implement a genuine leaf segmentation model before promoting severity metrics to production.

### B. Pesticide Recommendation Confidence Disconnect (HIGH RISK)
* **Observation:** When an image yields low confidence (e.g. Mosaic at 48% confidence due to visual similarity with early rust chlorosis), the backend issues the exact same definitive chemical advisory: *“Spray Imidacloprid 17.8 SL @ 0.5 ml/L...”*.
* **Audit Finding:** The system lacks an advisory confidence gating threshold.
* **Risk:** Spraying inappropriate synthetic insecticides or fungicides based on uncertain low-confidence classifications causes unnecessary input costs, soil toxicity, and pesticide resistance.
* **Mandated Action:** Enforce a minimum 70% confidence threshold. For predictions < 70%, suppress chemical recommendations and return a safe advisory prompting physical extension officer inspection.

---

## 5. Deployment Recommendation

1. **Sugarcane Staging Deployment:** **APPROVED WITH CAVEATS**. The core classification (93.16% test accuracy), Grad-CAM heatmap visualization, PostgreSQL isolation, and authenticated farmer workflows are production-grade.
2. **Multi-Crop Expansion (Tomato, Soybean, Cotton):** **BLOCKED**.
   * *Tomato:* Checkpoints do not exist in `models/tomato/`.
   * *Soybean:* Available raw dataset contains exclusively "Healthy" images (100% class imbalance).
   * *Cotton:* Dataset absent from repository.
3. **Field Generalization:** Staging must include an interactive confidence disclaimer and flag severity as heuristic until field calibration is completed.
