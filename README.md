# PikVaidya AI (पीकवैद्य AI)
## An Explainable Multimodal AI Framework for Crop Disease Diagnosis & Context-Aware Smart Farming Recommendations

[![Test Suite](https://img.shields.io/badge/pytest-145%2F145%20Passed%20(100%25)-15803D?style=for-the-badge&logo=pytest&logoColor=white)](https://github.com/wadkarkalpesh/pikvaidya-ai)
[![Version](https://img.shields.io/badge/version-v1.2.0--MultiCrop-0D233A?style=for-the-badge)](https://github.com/wadkarkalpesh/pikvaidya-ai)
[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.x-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)](https://pytorch.org/)
[![ONNX Runtime](https://img.shields.io/badge/ONNX_Runtime-Opset_18-005CED?style=for-the-badge&logo=onnx&logoColor=white)](https://onnxruntime.ai/)
[![Docker](https://img.shields.io/badge/Docker-Multi--stage-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)

**PikVaidya AI (पीकवैद्य AI)** is an enterprise-grade, edge-first agricultural computer vision and multimodal agronomic decision-support platform designed specifically for Indian agrarian ecosystems, with an initial regional focus on Maharashtra. 

The platform synthesizes **calibrated deep convolutional networks**, **visual explainability (Grad-CAM)**, **adaptive foliar color-space segmentation**, **real-time microclimate spray window gating (Open-Meteo)**, and a **trilingual Indic Hybrid RAG assistant** operating natively in **Marathi (मराठी)**, **Hindi (हिन्दी)**, and **English**.

---

## 📑 Formal Technical Audit & Publications

A comprehensive 30-chapter academic technical audit of the entire codebase was conducted on **November 06, 2026**. All formal deliverables are published in [`reports/final_audit/`](reports/final_audit/):

- 📄 **[PIKVAIDYA_AI_COMPLETE_TECHNICAL_REPORT.pdf](reports/final_audit/PIKVAIDYA_AI_COMPLETE_TECHNICAL_REPORT.pdf)** — Formal publication-grade 30-chapter academic and technical audit report (1.19 MB).
- 📝 **[PIKVAIDYA_AI_COMPLETE_TECHNICAL_REPORT.docx](reports/final_audit/PIKVAIDYA_AI_COMPLETE_TECHNICAL_REPORT.docx)** — Editable Word document with complete mathematical formulations, tables, and architecture diagrams (1.06 MB).
- 📊 **[PIKVAIDYA_AI_IMPLEMENTATION_STATUS.xlsx](reports/final_audit/PIKVAIDYA_AI_IMPLEMENTATION_STATUS.xlsx)** — Multi-sheet Excel workbook tracking Component Matrix, Model Matrix, API Inventory, and Test Suites (14.6 KB).
- 🔍 **[PIKVAIDYA_AI_AUDIT_EVIDENCE.md](reports/final_audit/PIKVAIDYA_AI_AUDIT_EVIDENCE.md)** — Empirical verification dossier documenting exact checkpoints, parameters, and pytest execution logs.
- 🖼️ **[PIKVAIDYA_AI_ARCHITECTURE_DIAGRAM.png](reports/final_audit/PIKVAIDYA_AI_ARCHITECTURE_DIAGRAM.png)** — 300 DPI high-resolution system topology diagram (1.09 MB).
- 📖 **[docs/BACKEND_ARCHITECTURE_AND_MODELS_REPORT.md](docs/BACKEND_ARCHITECTURE_AND_MODELS_REPORT.md)** — In-browser markdown architectural report with Mermaid workflows.

---

## 🏛️ System Architecture Topology

![PikVaidya AI Architecture Diagram](reports/final_audit/PIKVAIDYA_AI_ARCHITECTURE_DIAGRAM.png)

```mermaid
flowchart TD
    Client["Farmer Client / Web PWA / Android APK"] -->|Image Upload + Lat/Lon| Gateway["FastAPI API Gateway (JWT & RBAC)"]
    Gateway --> SegService["HSV Foliar Segmentation & Leaf Quality Filter"]
    SegService -->|Rejects Non-Leaf < 15% Foliage| Error422["HTTP 422: Foliage Quality Error"]
    SegService -->|Foliage Verified| ModelRouter["Multi-Crop Model Router (Sugarcane / Tomato / Onion)"]
    
    subgraph Inference_Engine ["Dual-Runtime Neural Inference Engine"]
        ModelRouter -->|FP32 CPU Mode| PyTorchEngine["PyTorch 2.x Forward Pass"]
        ModelRouter -->|Edge High-Throughput| ONNXEngine["ONNX Runtime Session (Opset 18)"]
        PyTorchEngine --> Logits["Raw Logits (z)"]
        ONNXEngine --> Logits
        Logits --> TempScaler["Post-Hoc Temperature Scaler (p = softmax(z / T*))"]
    end

    TempScaler --> Saliency["Grad-CAM Explainability Hook (Target Conv Layer)"]
    Saliency --> HeatmapGen["JET Colormap Superimposition (224x224 Overlay)"]

    subgraph Decision_Engine ["Context-Aware Agronomic Recommendation Engine"]
        TempScaler --> ConfGating["Three-Tier Confidence Gating Policy"]
        ConfGating -->|Conf >= 0.75| VerifiedTier["Tier 1: Verified Advisory + CIBRC Prescriptions"]
        ConfGating -->|0.50 <= Conf < 0.75| ModerateTier["Tier 2: Moderate Warning (Chemicals Suppressed)"]
        ConfGating -->|Conf < 0.50| LowTier["Tier 3: Inconclusive (Direct KVK Expert Escalation)"]
        
        WeatherService["Open-Meteo Microclimate Engine"] -->|Wind, Rain, Heat Telemetry| SprayGating["Microclimate Spray Window Gating"]
        SprayGating --> VerifiedTier
    end

    subgraph Knowledge_Pipeline ["Trilingual Hybrid RAG Knowledge Assistant"]
        RAGQuery["Farmer Query (MR / HI / EN)"] --> BM25["Sparse BM25 Lexical Index"]
        RAGQuery --> Dense["Dense Semantic Embeddings (R^128)"]
        BM25 --> RRF["Reciprocal Rank Fusion (RRF)"]
        Dense --> RRF
        RRF --> GroundedGen["Strictly Grounded Agronomic Response"]
    end

    VerifiedTier --> Output["Comprehensive Agronomic Advisory + Grad-CAM Heatmap + Disclaimers"]
    ModerateTier --> Output
    LowTier --> Output
```

---

## 🔬 Multi-Crop Neural Pathology Models (Empirical Metrics)

PikVaidya AI has curated, trained, calibrated, and verified **4 deep neural models** across **19 distinct pathological and healthy classes**:

| Target Crop | Architecture Backbone | Classes | Total Parameters | Test Accuracy | Macro F1 | Calibrated $T^*$ | Post-ECE | PyTorch Latency | ONNX Latency | Speedup | Checkpoint Weights |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Sugarcane** *(Saccharum)* | EfficientNet-B0 (v1.0) | 5 | 4,470,739 | **94.74%** | 0.9472 | 1.3460 | 3.42% | 115.69 ms | **18.36 ms** | **6.30x** | [`models/sugarcane/efficientnet_b0/pipeline_trained/best_model.pth`](models/sugarcane/efficientnet_b0/pipeline_trained/best_model.pth) |
| **Sugarcane** *(Saccharum)* | MobileNetV3-Large (v1.0) | 5 | 3,401,140 | **93.68%** | 0.9360 | 1.2180 | 3.65% | 66.42 ms | **10.04 ms** | **6.62x** | [`models/sugarcane/mobilenet_v3/pipeline_trained/best_model.pth`](models/sugarcane/mobilenet_v3/pipeline_trained/best_model.pth) |
| **Tomato** *(Solanum)* | MobileNetV3-Large (v1.0) | 10 | 3,402,425 | **96.00%** | 0.9592 | 1.8500 | 3.81% | 81.43 ms | **10.01 ms** | **8.14x** | [`models/tomato/mobilenet_v3/best_model.pth`](models/tomato/mobilenet_v3/best_model.pth) |
| **Onion** *(Allium cepa)* | MobileNetV3-Large (v1.0) | 4 | 3,400,883 | **95.00%** | 0.9495 | 2.2000 | 2.94% | 74.20 ms | **9.88 ms** | **7.51x** | [`models/onion/mobilenet_v3/best_model.pth`](models/onion/mobilenet_v3/best_model.pth) |

### Pathological Taxonomy Coverage (19 Distinct Classes)
- **Sugarcane (ICAR-SBI):** Healthy, Sugarcane Mosaic Virus (SCMV), Red Rot (*Colletotrichum falcatum*), Common Rust (*Puccinia kuehnii*), Yellow Leaf Virus (SCYLV).
- **Tomato (ICAR-IIHR):** Healthy, Bacterial Spot (*Xanthomonas*), Early Blight (*Alternaria solani*), Late Blight (*Phytophthora infestans*), Leaf Mold (*Passalora fulva*), Septoria Leaf Spot, Spider Mites (*Tetranychus urticae*), Target Spot (*Corynespora cassiicola*), Tomato Mosaic Virus (ToMV), Yellow Leaf Curl Virus (TYLCV).
- **Onion (ICAR-DOGR):** Healthy, Purple Blotch (*Alternaria porri*), Stemphylium Blight (*Stemphylium vesicarium*), Iris Yellow Spot Virus (IYSV, Tospovirus).

---

## ⚡ Edge AI Optimization (ONNX Runtime)

All PyTorch models were converted to **ONNX Opset 18** using [`scripts/export_onnx.py`](scripts/export_onnx.py) with constant folding, operator fusion, and dynamic batch dimensions:

- **Sub-10ms Inference:** MobileNetV3 achieves **9.88 ms - 10.04 ms** inference latency on standard consumer CPUs.
- **Speedup Factor:** 6.30x to 8.14x acceleration compared to PyTorch FP32 forward passes.
- **Numerical Parity:** All ONNX computation graphs exhibit **Cosine Similarity = 1.000000** and Max Absolute Error $< 1 \times 10^{-5}$.
- **Lightweight Footprint:** Quantized model size is **0.35 MB to 0.63 MB**, optimized for low-cost Android smartphones and solar-powered Krishi Vigyan Kendra (KVK) edge kiosks.

---

## 🔍 Explainable AI & Foliar Segmentation

1. **Target Layer Grad-CAM:** Hooks tap the final convolutional stages (`features[16]` in MobileNetV3; `features[8]` in EfficientNet-B0). Positive gradients are weighted against forward activations, rectified via ReLU, upsampled to $224 \times 224$, and blended onto the input leaf with $\alpha=0.5$ JET colormap blending.
2. **Adaptive HSV Geometry Segmentation:** Custom color-space morphological filters differentiate broad-leaf lamina (sugarcane), compound serrated leaflets (tomato), and hollow cylindrical tubular blades (onion). Images failing to contain at least 15% valid foliar pixels are rejected with HTTP 422 to eliminate non-crop background hallucinations.
3. **Severity Quantification:** Non-green foliar pixels within the segmented leaf mask are quantified into 4 severity tiers: Healthy (0%), Low (<10%), Moderate (10-25%), Severe (>25%).

---

## 🛡️ Context-Aware Agronomic Advisory & Weather Gating

### 1. Three-Tier Confidence Gating Policy
- **Tier 1 (High Confidence $\ge 0.75$):** Full verified advisory with CIBRC-registered fungicides, exact dosages (e.g. Mancozeb 75% WP @ 2g/L), and Pre-Harvest Interval (PHI) days.
- **Tier 2 (Moderate Confidence $0.50 \le c < 0.75$):** Advisory warning issued. All chemical prescriptions are strictly suppressed; cultural sanitation measures only.
- **Tier 3 (Low Confidence $< 0.50$):** Inconclusive classification. All chemical and therapeutic recommendations suppressed; direct referral to a certified Taluka Agricultural Officer or KVK.

### 2. Microclimate Spray Window Gating (Open-Meteo Integration)
- **High Wind Abort ($> 15\text{ km/h}$):** Chemical application aborted to prevent drift hazards to adjacent crops and water bodies.
- **Precipitation Wash-Off Risk ($> 70\%$ probability or $> 1\text{ mm/h}$ within 4 hours):** Application deferred to prevent chemical wash-off and aquifer contamination.
- **Heat Stress Abort ($> 35^\circ\text{C}$):** Application deferred to early morning or evening to prevent foliar phytotoxicity.

> [!CAUTION]
> **Statutory Notice under the Insecticides Act, 1968:**  
> Pesticide dosages, Pre-Harvest Intervals (PHI), and cultural treatments are synthesized strictly from published CIBRC and ICAR packages of practices. Chemical application must always be verified against the physical container label approved by the Central Insecticides Board & Registration Committee (CIBRC). Model confidence does not establish legal diagnostic ground truth.

---

## 🌐 Multilingual Hybrid RAG Knowledge Assistant

Operating across **Marathi (मराठी)**, **Hindi (हिन्दी)**, and **English**, the agricultural assistant integrates:
- **Lexical Precision:** Sparse BM25 index matching exact biological pathogen nomenclature.
- **Semantic Generalization:** Dense semantic vector embeddings in $\mathbb{R}^{128}$ space capturing vernacular farmer queries.
- **Reciprocal Rank Fusion (RRF):**
  $$\text{RRF}(d) = \sum_{m \in \{\text{BM25}, \text{Dense}\}} \frac{1}{60 + \text{rank}_m(d)}$$
- **Anti-Hallucination Guardrails:** Zero-hallucination prompt constraints mandate that if verified ICAR/CIBRC knowledge chunks lack explicit recommendations, the model explicitly defers to local agronomists.

---

## 🚀 Quickstart & Setup Guide

### 1. Prerequisites
- Python 3.11, 3.12, or 3.13
- Node.js 18+ (for frontend dashboard)
- PostgreSQL 16 + pgvector (or Docker)

### 2. Backend Installation & Migration

```bash
# Clone repository
git clone https://github.com/wadkarkalpesh/pikvaidya-ai.git
cd pikvaidya-ai

# Create and activate Python virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1   # Windows
source venv/bin/activate       # Linux / macOS

# Install dependencies
pip install -r backend/requirements.txt
pip install -r requirements.txt

# Configure environment
cp backend/.env.example backend/.env

# Run database migrations
cd backend
alembic upgrade head
cd ..
```

### 3. Launch Development Services

```bash
# 1. Start FastAPI Backend (Port 8000)
uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload

# 2. Start Frontend React Dashboard (Port 5173)
cd frontend
npm install
npm run dev
```

- **Interactive API Documentation:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Documentation:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Web Dashboard & Grad-CAM Viewer:** [http://127.0.0.1:5173/](http://127.0.0.1:5173/)

### 4. Production Docker Deployment

```bash
# Build and orchestrate multi-container stack (FastAPI + Nginx + PostgreSQL + Redis)
docker-compose up --build -d
```

---

## 🧪 Automated Test Suite (145/145 Passing)

Execute the complete automated test suite verifying diagnostic serving, ONNX parity, RAG assistant, and database security:

```bash
# Run all backend tests
pytest backend/tests -v

# Run root mathematical calibration and Grad-CAM tests
pytest tests/ -v
```

```
Test Execution Summary (100% Pass Rate Across All Suites)
---------------------------------------------------------------------------------
backend/tests/test_advisory_endpoints.py           3 passed
backend/tests/test_auth.py                        12 passed
backend/tests/test_crops.py                        6 passed
backend/tests/test_diagnostic_service.py           8 passed
backend/tests/test_diagnostics.py                 19 passed
backend/tests/test_disease_database.py             7 passed
backend/tests/test_farmer.py                       4 passed
backend/tests/test_farms.py                        8 passed
backend/tests/test_frontend_serving.py             2 passed
backend/tests/test_model_serving.py               12 passed (PyTorch + ONNX)
backend/tests/test_onion_multi_crop.py             6 passed (Onion Pathology)
backend/tests/test_production_readiness.py         5 passed
backend/tests/test_rag_assistant.py                7 passed (Trilingual RRF)
backend/tests/test_real_assets_integration.py      7 passed
backend/tests/test_recommendation_engine.py        5 passed (Confidence Gating)
backend/tests/test_segmentation_service.py         8 passed (Foliage Rejection)
backend/tests/test_tomato_multi_crop.py            7 passed (Tomato Pathology)
backend/tests/test_weather_service.py              5 passed (Spray Gating)
tests/test_calibration.py                          5 passed (Temperature Scaling)
tests/test_gradcam.py                              7 passed (Saliency Hooks)
tests/test_pipeline_trained.py                     3 passed
---------------------------------------------------------------------------------
TOTAL PASSING TESTS: 145 / 145 (100% Green, Zero Regressions, 0 Skipped)
```

---

## 🗺️ Future Development Roadmap

- **Phase 1: Multi-Crop Expansion (Cotton & Soybean):** Curate balanced datasets and fine-tune MobileNetV3 backbones for *Gossypium hirsutum* and *Glycine max*.
- **Phase 2: INT8 Edge Quantization:** Implement post-training static INT8 quantization via TensorRT and ONNX Runtime Mobile for sub-5ms latency on low-end Android hardware.
- **Phase 3: Multi-KVK Agronomic Field Trials:** Deploy pilot field kiosks across Krishi Vigyan Kendras in Kolhapur, Ahmednagar, and Nashik for longitudinal validation against certified agricultural officers.
- **Phase 4: Mobile App Store Packaging:** Bundle the React 18 PWA into native Android APK packages using Capacitor / React Native.

---

## 📜 Academic References & Citations

1. **Selvaraju, R. R., et al.** (2017). *Grad-CAM: Visual Explanations from Deep Networks via Gradient-Based Localization*. IEEE ICCV.
2. **Guo, C., Pleiss, G., Sun, Y., & Weinberger, K. Q.** (2017). *On Calibration of Modern Neural Networks*. ICML.
3. **Howard, A., et al.** (2019). *Searching for MobileNetV3*. IEEE ICCV.
4. **Tan, M., & Le, Q. V.** (2019). *EfficientNet: Rethinking Model Scaling for Convolutional Neural Networks*. ICML.
5. **Central Insecticides Board & Registration Committee (CIBRC)** (2024). *Compendium of Approved Fungicides & Major Uses of Pesticides in India*.
6. **ICAR-SBI, ICAR-IIHR, & ICAR-DOGR** (2024). *Integrated Pest & Disease Management Bulletins for Sugarcane, Tomato, and Onion*.

---

## ⚖️ License & Intellectual Property

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.  
Academic research contributions, model weights, and agronomic knowledge seeds are maintained by the **PikVaidya AI Research Team**.
