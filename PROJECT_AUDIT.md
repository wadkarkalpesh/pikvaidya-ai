# PikVaidya AI — Comprehensive Project Audit (PROJECT_AUDIT.md)
**Document Version:** 1.0.0  
**Audit Timestamp:** October 22, 2026  
**Auditor Roles:** Senior Software Architect, Lead ML Engineer, DevOps Engineer, Codebase Auditor  
**Project Objective:** Explainable Multimodal Crop-Disease Diagnosis & Smart-Farming Recommendation System for Indian Farmers  

---

## 1. Executive Summary

An exhaustive repository inspection was performed across all **2,745 visible files** in `e:\PikVaidya AI`. The codebase consists of:
* A production-ready **FastAPI** backend supporting JWT authentication, farmer profiles, farm management, crop cycle tracking, and ML diagnostic serving.
* A deep learning vision pipeline for **Sugarcane Crop Pathology** (5 audited classes: *Healthy*, *Mosaic*, *RedRot*, *Rust*, *Yellow*) trained with transfer learning on PyTorch.
* **Explainable AI (Grad-CAM)** integrated to provide visual lesion validation.
* **PostgreSQL** persistence configured with **SQLAlchemy 2.0** ORM and **Alembic** migrations.
* **Empirical test suite** comprising **47 automated unit and integration tests** passing with 100% success rate.
* Future multi-crop dataset archives (Tomato: 18,906 images; Soybean: 5,121 images; Onion research literature: 4,502 field images).

This audit identifies all repository components, traces their operational connectivity, records all suspicious, redundant, or orphaned items, and specifies clear preservation rules.

---

## 2. Complete Repository Inventory

The repository is structured into 10 primary functional zones:

```
PikVaidya AI/
├── backend/                     # FastAPI async microservice, routes, models, schemas, tests
│   ├── alembic/                 # Database migrations (001_initial_schema, 002_add_diagnostics)
│   ├── app/
│   │   ├── api/routes/          # API endpoints (auth, farmer, farms, crops, diagnostics)
│   │   ├── core/                # Configuration (Pydantic Settings) and security (JWT, bcrypt)
│   │   ├── db/                  # SQLAlchemy DeclarativeBase and session generators
│   │   ├── models/              # ORM entities (User, Farm, CropCycle, Diagnosis)
│   │   ├── schemas/             # Pydantic validation models
│   │   └── services/            # Storage, AI knowledge base adapter, ModelServingService
│   ├── tests/                   # Pytest automated test suite (47 tests)
│   ├── requirements.txt         # Backend service dependencies
│   └── alembic.ini              # Alembic configuration
├── configs/                     # Experiment configurations (experiment_config.yaml)
├── data/raw/                    # Raw research data assets (sugarcane/, PlantVillage.zip, PlantDoc.zip)
├── datasets/                    # Processed manifests and empirical benchmark reports
│   ├── processed/sugarcane/     # Deduplicated train (1615), val (345), test (351) manifests
│   └── reports/                 # Confusion matrices, ECE calibration, Grad-CAM overlays
├── docs/                        # Architecture documentation, ER models, sprint specifications
├── models/                      # Trained PyTorch checkpoints and metadata
│   └── sugarcane/
│       ├── efficientnet_b0/     # Primary Model A (48.6 MB best_model.pth, 93.16% test accuracy)
│       └── mobilenet_v3/        # Edge Model B (38.9 MB best_model.pth, 84.05% test accuracy)
├── scripts/                     # Operational automation (dataset_audit.py, run_experiments.py, GSD)
├── src/                         # Core ML engineering library (data, training, evaluation, XAI)
├── adapters/                    # GSD Assistant personality adapters (Claude, Gemini, GPT)
└── .agent/ & .agents/           # GSD workflows, validation routines, and specialized skills
```

---

## 3. End-to-End Operational Connectivity Trace

To ensure no critical links are broken, the end-to-end operational pipeline was traced:

```
[Leaf Image Upload (JPEG/PNG/WebP)]
       │
       ▼
[Route: POST /api/v1/diagnose/predict]  (app/api/routes/diagnostics.py)
       │
       ├─► 1. Extension Validation (.jpg, .jpeg, .png, .webp)
       ├─► 2. Magic Header Bytes Check (\xff\xd8\xff, \x89PNG, RIFF...WEBP)
       ├─► 3. Size Limit Check (<= 10 MB)
       ├─► 4. PIL Decodability & Color Format Verification (RGB)
       └─► 5. Target Crop Verification (sugarcane)
       │
       ▼
[Singleton: model_service]  (app/services/model_service.py)
       │
       ├─► Preprocessing: Resize((224, 224)) -> ToTensor() -> Normalize(IMAGENET_MEAN, IMAGENET_STD)
       ├─► Forward Pass: EfficientNet-B0 (In-memory PyTorch instance, 4.01M params)
       ├─► Softmax Probabilities: [Healthy, Mosaic, RedRot, Rust, Yellow]
       ├─► Prediction & Confidence Extraction: argmax + score distribution
       │
       ├─► Optional: Grad-CAM Saliency Computation
       │     └─► Hooks into features[-1] (1280-channel final conv block)
       │     └─► Gradient backpropagation of predicted class
       │     └─► Synthetic JET Colormap Blending (50% alpha overlay)
       │     └─► Persist to uploads/heatmaps/cam_{uuid}_{class}.jpg
       │     └─► Guaranteed Hook Removal in finally block
       │
       ▼
[API Response Payload (PredictResponse)]
       │
       ├─► crop: "sugarcane"
       ├─► predicted_class: "RedRot"
       ├─► confidence: 0.9452
       ├─► class_scores: { "Healthy": 0.0051, "Mosaic": 0.0123, "RedRot": 0.9452, "Rust": 0.0211, "Yellow": 0.0163 }
       ├─► model_version: "EfficientNet-B0-v1.0"
       ├─► explanation_status: "generated"
       └─► heatmap_path: "uploads/heatmaps/cam_...jpg"
```

* **Status of Pipeline**: 100% connected, operational, and covered by automated tests.

---

## 4. Suspicious, Redundant, Obsolete, and Disconnected Components

The table below catalogs every component evaluated during the audit:

| Item Path | Purpose | Active Usage | Evidence | Dependencies Affected | Recommended Action |
| :--- | :--- | :---: | :--- | :--- | :---: |
| `uploads/diagnostics/2026-10/*.jpg` (24 files) | Test image uploads saved by historical pytest runs | **NO** (Orphaned test data) | Files generated during test suite execution; unlinked from database | None | **REMOVE (Clean)** |
| `src/__init__.py` (missing) | Package boundary for core ML source library | **NO** (Omission) | Implicit namespace package used; brittle import paths | `src.training`, `src.data`, `src.explainability` | **ADD (Refactor)** |
| `src/data/__init__.py` (missing) | Package boundary for data module | **NO** (Omission) | `from src.data.dataset import ...` | Dataset loaders | **ADD (Refactor)** |
| `src/training/__init__.py` (missing) | Package boundary for training module | **NO** (Omission) | `from src.training.models import ...` | Model factory | **ADD (Refactor)** |
| `src/evaluation/__init__.py` (missing) | Package boundary for evaluation module | **NO** (Omission) | `from src.evaluation.metrics import ...` | Metric evaluators | **ADD (Refactor)** |
| `src/explainability/__init__.py` (missing) | Package boundary for XAI module | **NO** (Omission) | `from src.explainability.gradcam import ...` | Grad-CAM generator | **ADD (Refactor)** |
| `backend/app/schemas/__init__.py` | Schemas module exports | **PARTIAL** | `PredictResponse` is defined in `diagnosis.py` but omitted from `__all__` | Schema consumers | **REFACTOR** |
| `requirements.txt` (root missing) | Unified project dependencies | **NO** (Omission) | Only `backend/requirements.txt` existed, omitting PyTorch, torchvision, Pillow, ReportLab | Deployment & developers | **ADD (Refactor)** |
| `adapters/CLAUDE.md`, `GEMINI.md`, `GPT_OSS.md` | GSD AI personality adapters | **STANDBY** | Part of installed Antigravity agent configuration | GSD workflows | **KEEP** |
| `scripts/validate-*.ps1` / `*.sh` (16 files) | GSD validation scripts | **STANDBY** | Used by `.agent/` and `.gsd/` tools | Agent workflows | **KEEP** |
| `configs/experiment_config.yaml` | Experiment hyperparameter registry | **YES** | Used by `scripts/run_experiments.py` | Experiment reproducibility | **KEEP** |
| `data/raw/sugarcane/` (2,521 JPEGs) | Raw sugarcane image dataset | **YES** | Source for deduplication and dataset manifests | Model training | **KEEP (Protected)** |
| `data/raw/PlantVillage-Dataset-master.zip` (861 MB) | Raw multi-crop laboratory images | **FUTURE** | Planned Phase 2 training data for Tomato & Soybean | Future crop expansion | **KEEP (Protected)** |
| `data/raw/PlantDoc-Dataset-master.zip` (18.1 MB) | Raw Indian in-field leaf images | **FUTURE** | In-field benchmark data for Tomato & Soybean | Future field validation | **KEEP (Protected)** |
| `data/raw/chiili and onion plant leaf images.pdf` | Research paper with Mendeley provenance | **FUTURE** | Academic reference for 4,502 field images (Onion) | Phase 3 onion ingestion | **KEEP (Protected)** |
| `models/sugarcane/efficientnet_b0/best_model.pth` | Primary model weights (48.6 MB) | **YES** | Active serving checkpoint loaded at FastAPI startup | Production inference | **KEEP (Protected)** |
| `models/sugarcane/mobilenet_v3/best_model.pth` | Secondary edge model weights (38.9 MB) | **FUTURE** | Candidate for Android ONNX/TFLite edge export | Rural offline edge | **KEEP (Protected)** |
| `datasets/reports/` (all CSV, JSON, PNGs) | Empirical benchmark and XAI evidence | **YES** | Backing evidence for accuracy, F1, ECE, confusion matrices | Auditability | **KEEP (Protected)** |
| `Pikvaidya_AI_Synopsis.pdf` | Academic synopsis document | **YES** | Project reference documentation | Institutional compliance | **KEEP (Protected)** |
| `__pycache__` directories | Python bytecode caches | **NO** (Auto-regenerated) | Temporary compilation caches | None | **REMOVE (Clean)** |

---

## 5. Protected Assets Confirmation

In strict compliance with Section 5 of the audit directive, the following critical assets are permanently protected from deletion:
1. `models/sugarcane/efficientnet_b0/best_model.pth` (Primary weights)
2. `models/sugarcane/mobilenet_v3/best_model.pth` (Secondary weights)
3. `models/sugarcane/*/class_mapping.json` & `config.json`
4. `datasets/processed/sugarcane/*.csv` (Deduplicated manifests)
5. `datasets/reports/*.csv`, `*.json`, `gradcam_*/*.png` (Empirical research proof)
6. `data/raw/*` (Raw imagery, archives, and research papers)
7. `backend/alembic/versions/*.py` (Database schema migration lineage)
8. `backend/.env.example` (Configuration contract)

---

## 6. Audit Verdict & Proposed Safe Changes

* **Architecture Status**: Healthy, modular, and empirically sound.
* **Redundancies to Clean**:
  1. Purge 24 orphaned test files in `uploads/diagnostics/2026-10/` created during previous test runs.
  2. Purge stale `.pyc` and `__pycache__` artifacts across the repository.
* **Structural Improvements to Apply**:
  1. Add standard `__init__.py` files to `src/`, `src/data/`, `src/training/`, `src/evaluation/`, `src/explainability/`.
  2. Export `PredictResponse` in `backend/app/schemas/__init__.py`.
  3. Create a unified root `requirements.txt` capturing both Backend and Machine Learning dependencies.
  4. Create a dedicated Git branch `refactor/safe-clean-audit` to preserve history.
