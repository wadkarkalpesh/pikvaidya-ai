# PikVaidya AI — Development Roadmap & Implementation Trajectory
**Document Version:** 2.1.0  
**Current Milestone:** Phase 13 Completed (Multimodal Crop-Health Prediction Engine)  
**Focus Region:** Maharashtra, India

---

## 1. High-Level Architectural Trajectory

```
Phase 1-6: Core Vision & Explainability (Completed)
   │
   ▼
Phase 7-10: Persistence, Agronomy, Weather & RAG Assistant (Completed)
   │
   ▼
Phase 11-12: PDF Field Report Generation & INT8 Quantization (Completed)
   │
   ▼
Phase 13: Multimodal Crop-Health Prediction Engine (Completed)
   │
   ▼
Phase 14: Unified Multi-Crop Prediction Platform & Automated Routing (Completed)
   │
   ▼
Phase 15: Full Offline PWA & Local IndexedDB Cache Engine (Completed)
   │
   ▼
Phase 16: Automated IoT Sensor Telemetry Feed (LoRaWAN / MQTT / HTTP) (Completed)
   │
   ▼
Phase 17: Expansion to Cotton & Soybean Crop Disease Pipelines (Next Active Milestone)
```

---

## 2. Phase Breakdown & Execution Details

### Completed Milestones
* **Phase 1: Project Topology & Foundations:** Standardized monorepo with clean backend/frontend decoupling.
* **Phase 2: Multi-Crop Deep Learning:** Sugarcane (EfficientNet-B0, MobileNetV3), Tomato (MobileNetV3), Onion (MobileNetV3).
* **Phase 3: Explainable AI (Grad-CAM):** Feature map gradient saliency visualization for visual lesion interpretability.
* **Phase 4: Calibration & Uncertainty Gating:** Temperature Scaling ensuring calibrated confidence scores (ECE < 0.05).
* **Phase 5: Foliar Lesion Quantification:** Excess Green (ExG) + Otsu thresholding foliar surface area estimation.
* **Phase 6: Serving Gateway:** FastAPI async server with MIME validation, rate limiting, and singleton memory management.
* **Phase 7: Relational Data Persistence:** SQLAlchemy 2.0 models with Alembic migrations for farmers, farms, and diagnoses.
* **Phase 8: Agronomic Knowledge Corpus:** CIBRC-approved chemical and ICAR-recommended cultural practices with strict PHI days and PPE.
* **Phase 9: Hyperlocal Weather Intelligence:** Open-Meteo & IMD alert telemetry for 11 Maharashtra districts, modeled soil moisture, and spray suitability gating.
* **Phase 10: Multilingual RAG Assistant:** Agricultural domain question answering with citation grounding across English, Marathi, and Hindi.
* **Phase 11: Multilingual Field Advisory PDF Generator:** Publication-quality A4 report synthesis via ReportLab 4.4.4.
* **Phase 12: Edge INT8 Model Quantization:** Dynamic INT8 weight quantization achieving $r > 0.9999$ correlation and $<35$ ms CPU latency.
* **Phase 13: Multimodal Crop-Health Prediction Engine:** Multi-window historical microclimate telemetry (24h, 3d, 7d, 14d), physiological stress quantification (heat, water deficit, waterlogging, wind), epidemiological disease-conduciveness models (Tom-Cast DSV, Wallin criteria, ICAR-SBI, ICAR-DOGR), Calibrated Bayesian evidence fusion, strict non-override guarantee ($c \ge 0.75$), environmental anomaly detection, composite crop health score (0-100), full frontend reactive UI, and dedicated pytest suites.
* **Phase 14: Unified Multi-Crop Prediction Platform & Automated Routing:** Common prediction interface `POST /api/crop-health/predict` integrating Sugarcane, Tomato, and Onion models. Fine-tuned MobileNetV3 Crop Detector with 99.67% test accuracy across 300 test leaves for automated foliar routing, full epidemiological coverage across all 19 conditions in Sugarcane, Tomato, and Onion, multilingual PWA integration (`App.jsx`), and dedicated test suite (`test_crop_health_unified.py`). 193 total passing tests.
* **Phase 15: Full Offline PWA & Local IndexedDB Cache:** Full W3C PWA with `manifest.webmanifest` and `dist/sw.js`. 4-Store IndexedDB architecture (`diagnosis_history`, `farm_information`, `advisory_cards`, `sync_queue`), QuotaExceeded error handling, JSON backup export. Edge ONNX Runtime Web WASM SIMD inference for Sugarcane, Tomato, and Onion INT8 models (2.35-2.66ms latency). Resilient background sync manager with exponential backoff and UUID idempotency.
* **Phase 16: Automated IoT Sensor Telemetry Feed (LoRaWAN / MQTT / HTTP Webhook Gateway):** Ingests live in-situ microclimate telemetry directly from farm sensor nodes (temperature, canopy humidity, leaf wetness minutes, soil moisture at 10cm/30cm, rain rate, wind speed, solar radiation). Features SHA-256 token verification, LoRaWAN webhook parsing (TTN / ChirpStack), rolling 24h canopy microclimate summary, and seamless integration with the Multimodal RAG Orchestrator to prioritize in-situ sensor data over regional open-meteo weather models. 7 dedicated tests in `backend/tests/test_iot_telemetry.py` (240 total passing tests).

---

## 3. Upcoming Milestones

### Phase 17: Cotton & Soybean Crop Expansion (Immediate Next)
* **Goal:** Expand vision dataset curation and transfer learning pipelines to Cotton (Pink Bollworm, Bacterial Blight) and Soybean (Rust, Mosaic).
* **Key Tasks:**
  1. Acquire and verify real field leaf datasets for Cotton and Soybean.
  2. Implement group-stratified train/val/test data pipelines preventing data leakage.
  3. Train, calibrate, and quantize MobileNetV3 backbones.
  4. Expand CIBRC knowledge base and multimodal Bayesian fusion rules.

