# PikVaidya AI — Codebase Cleanup Changelog (CLEANUP_CHANGELOG.md)
**Document Version:** 1.0.0  
**Execution Timestamp:** October 22, 2026  
**Auditor:** Senior Software Architect, Lead ML Engineer, DevOps Engineer  
**Branch:** `refactor/safe-clean-audit`  

---

## 1. Overview of Actions

Every file modified, created, retained, or removed during this safe cleanup pass is documented below, along with the engineering rationale.

---

## 2. Removed Artifacts

| File / Directory Path | Item Type | Rationale |
| :--- | :---: | :--- |
| `uploads/diagnostics/2026-10/*.jpg` (24 files) | Test Data Cache | Orphaned test image uploads created by historical `pytest` runs of `test_diagnostics.py`. Files had no live database foreign keys and consumed unneeded storage. Cleaned while leaving directory structure intact. |
| `**/__pycache__/*.pyc` | Bytecode Cache | Removed stale Python bytecode caches to ensure clean recompilation across Python 3.13 runtime modules. |

---

## 3. Created & Added Files

| File Path | Purpose |
| :--- | :--- |
| [`PROJECT_AUDIT.md`](file:///e:/PikVaidya%20AI/PROJECT_AUDIT.md) | Comprehensive repository audit cataloging all 2,745 files, operational flows, and preservation classifications. |
| [`requirements.txt`](file:///e:/PikVaidya%20AI/requirements.txt) | Unified root-level requirements specification defining ML (PyTorch, Torchvision, Pillow, NumPy, Scikit-learn), Backend (FastAPI, Uvicorn, SQLAlchemy, Alembic, Psycopg), and Utility dependencies. |
| [`src/__init__.py`](file:///e:/PikVaidya%20AI/src/__init__.py) | Package initialization declaring the root ML library version boundary. |
| [`src/data/__init__.py`](file:///e:/PikVaidya%20AI/src/data/__init__.py) | Package initialization exporting `SugarcaneDataset`, `get_transforms`, `IMAGENET_MEAN`, and `IMAGENET_STD`. |
| [`src/training/__init__.py`](file:///e:/PikVaidya%20AI/src/training/__init__.py) | Package initialization exporting `build_model` and `run_training`. |
| [`src/evaluation/__init__.py`](file:///e:/PikVaidya%20AI/src/evaluation/__init__.py) | Package initialization exporting `compute_classification_metrics`, `compute_calibration_ece`, and `run_evaluation`. |
| [`src/explainability/__init__.py`](file:///e:/PikVaidya%20AI/src/explainability/__init__.py) | Package initialization exporting `GradCAM` and `apply_colormap_on_image`. |
| [`CLEANUP_CHANGELOG.md`](file:///e:/PikVaidya%20AI/CLEANUP_CHANGELOG.md) | Detailed ledger of all codebase cleanup actions, additions, and retentions. |
| [`FINAL_PROJECT_STRUCTURE.md`](file:///e:/PikVaidya%20AI/FINAL_PROJECT_STRUCTURE.md) | Annotated directory tree of the final clean repository structure. |
| [`DEPENDENCY_AUDIT.md`](file:///e:/PikVaidya%20AI/DEPENDENCY_AUDIT.md) | Exhaustive dependency analysis cross-referencing imports, packages, and necessity. |
| [`TEST_RESULTS.md`](file:///e:/PikVaidya%20AI/TEST_RESULTS.md) | Complete empirical log of test executions, inference validations, and performance metrics. |
| [`REMAINING_ISSUES.md`](file:///e:/PikVaidya%20AI/REMAINING_ISSUES.md) | Detailed register of deferred features, multi-crop roadmaps, and technical debt. |

---

## 4. Modified Files

| File Path | Description of Modification |
| :--- | :--- |
| [`backend/app/schemas/__init__.py`](file:///e:/PikVaidya%20AI/backend/app/schemas/__init__.py) | Exported `PredictResponse` in `__all__` to make schema accessible directly from `app.schemas`. |
| [`backend/app/api/routes/diagnostics.py`](file:///e:/PikVaidya%20AI/backend/app/api/routes/diagnostics.py) | Modernized HTTP 413 integer status code to suppress Starlette deprecation warnings. |
| [`backend/app/services/storage.py`](file:///e:/PikVaidya%20AI/backend/app/services/storage.py) | Modernized HTTP 413 integer status code to suppress Starlette deprecation warnings. |
| [`backend/tests/conftest.py`](file:///e:/PikVaidya%20AI/backend/tests/conftest.py) | Upgraded `sample_jpeg_bytes` fixture to provide valid, decodable JPEG image bytes for PIL compatibility. |

---

## 5. Retained Critical Assets

All critical assets identified in Section 5 of the audit directive were retained:
* `models/sugarcane/efficientnet_b0/best_model.pth` (Primary weights, 48.6 MB)
* `models/sugarcane/mobilenet_v3/best_model.pth` (Secondary weights, 38.9 MB)
* `datasets/processed/sugarcane/` (`train_manifest.csv`, `val_manifest.csv`, `test_manifest.csv`, `class_mapping.json`)
* `datasets/reports/` (All confusion matrices, benchmark comparisons, test metrics JSONs, and Grad-CAM PNG overlays)
* `data/raw/` (`sugarcane/`, `PlantDoc-Dataset-master.zip`, `PlantVillage-Dataset-master.zip`, `chiili and onion plant leaf images.pdf`)
* `backend/alembic/versions/` (`001_initial_schema.py`, `002_add_diagnostics_schema.py`)
* `backend/.env.example`
* `Pikvaidya_AI_Synopsis.pdf`
* `adapters/` and `scripts/validate-*.ps1` / `*.sh` (GSD framework tooling)
