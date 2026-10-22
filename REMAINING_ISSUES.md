# PikVaidya AI — Disconnected Features, Missing Dependencies & Unresolved Risks (REMAINING_ISSUES.md)
**Document Version:** 1.0.0  
**Date:** October 22, 2026  
**Auditor:** Senior Software Architect, Lead ML Engineer, DevOps Engineer  

---

## 1. Executive Summary

This document registers all planned future features, data gaps identified during empirical audits, and architectural technical debt.

Crucially, **no components have been classified as defects simply because they belong to future milestones**. The table below establishes a clear roadmap distinguishing current working capabilities from deferred capabilities.

---

## 2. Feature & Subsystem Status Matrix

| Subsystem / Feature | Current Implementation State | Status Classification | Dependencies / Blocker | Recommended Action |
| :--- | :--- | :---: | :--- | :--- |
| **Sugarcane Vision Model** | 93.16% test accuracy, 0.9286 Macro F1 on 5 classes | **COMPLETE (Production Ready)** | `models/sugarcane/efficientnet_b0/best_model.pth` | Retain as authoritative primary diagnostic model. |
| **Grad-CAM XAI Engine** | Features layer hook, synthetic JET colormap, safe cleanup | **COMPLETE (Production Ready)** | Integrated into `model_service.py` & `/diagnose/predict` | Retain as mandatory explainability layer for farmer trust. |
| **FastAPI Backend Gateway** | Auth, Farms, Crops, Diagnostics, Predict endpoints | **COMPLETE (Production Ready)** | FastAPI, SQLAlchemy 2.0, Pydantic 2 | Retain; 47 automated tests passing. |
| **Tomato Multi-Crop Expansion** | Raw archives present (18,906 images across 10 classes) | **PLANNED (Phase 2)** | Requires unzipping `data/raw/PlantVillage-Dataset-master.zip` | Queue for Phase 2 training with focal loss. |
| **Soybean Disease Pathology** | Archive present (5,121 images), but **100% are Healthy** | **DATA GAP (Phase 3 Blocker)** | Zero local disease classes in PlantVillage & PlantDoc | **Critical Action**: Ingest external Kaggle/Mendeley infected Soybean leaf datasets before training. |
| **Onion Disease Pathology** | Research publication present describing 4,502 field images | **PLANNED (Phase 3)** | Mendeley Data API download pending | Implement automated download script from Mendeley Data. |
| **Cotton Disease Pathology** | 0 local images | **DATA GAP (Phase 3 Blocker)** | Missing raw imagery | Ingest Kaggle Cotton Disease Dataset. |
| **Offline Rural Edge Quantization** | MobileNetV3 weights trained (84.05% test acc, 0.0390 ECE) | **PLANNED (Edge Export)** | ONNX Runtime / TensorFlow Lite INT8 Quantizer | Export MobileNetV3 checkpoint to ONNX & TFLite for Android APK. |
| **Multilingual Voice/Text Assistance** | English & Marathi advisory strings in `ai_service.py` | **PARTIAL (Phase 4)** | Regional audio synthesis (Vosk/Whisper/TTS) | Expand localized Marathi agronomy advisory rules into agricultural RAG. |
| **Frontend Farmer Application** | Documentation & API contracts complete | **PLANNED (Phase 5)** | React Native or Flutter mobile client | Implement mobile PWA client consuming `/api/v1/diagnose/predict`. |

---

## 3. Data Gaps & Dataset Recommendations

1. **Soybean Healthy-Only Blocker**:
   - The empirical dataset audit revealed that all 5,090 Soybean images in PlantVillage and all 31 Soybean images in PlantDoc are exclusively **Healthy leaves**.
   - Training a classifier on this archive would cause massive catastrophic bias (100% false healthy classifications).
   - *Resolution*: Do not train Soybean until external infected datasets (e.g. Soybean Rust, Frogeye Leaf Spot) are downloaded and audited.
2. **Cotton Zero-Sample Blocker**:
   - The local `data/raw/` folder has zero cotton images.
   - *Resolution*: Download the Kaggle Cotton Leaf Disease dataset (Bacterial Blight, Curl Virus, Fusarium Wilt).

---

## 4. Technical Debt & Upstream Notices

1. **Starlette TestClient Notice**:
   - `StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.`
   - This warning originates from Starlette 1.7 internal test client wrappers and does not impact API execution or test validity.
   - *Resolution*: Monitor Starlette releases for migration to standard httpx client fixtures.
2. **PostgreSQL Production Environment Provisioning**:
   - Local unit tests run on in-memory SQLite (`sqlite:///:memory:`) via `StaticPool`.
   - Production deployments must supply a real PostgreSQL 16 database matching `postgresql+psycopg://` in `backend/.env`.
   - *Resolution*: Maintain standard `docker-compose.yml` defining PostgreSQL 16 container for production staging.
