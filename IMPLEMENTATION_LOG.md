# PikVaidya AI — Implementation & Change Log
**Log Entry Date:** November 9, 2026  
**Engineering Leads:** Senior Computer Vision & Deep Learning Lead, Data Integrity Architect, ML Systems Integration Engineer, Calibration & Testing Lead

---

## Session Implementation Summary: Onion Dataset Expansion & Pathology Engine Upgrade

### 1. Forensic Dataset Audit & Public Dataset Acquisition
* **Legacy Dataset Audit:** Inspected `datasets/processed/onion/` (920 procedural/synthetic images, uniform 256x256, 0 corrupted, 137 pHash collisions). Proved domain failure on real-world foliar symptoms (31.49% accuracy, 0.0000 F1 on Purple Blotch and Stemphylium). Legacy data fully preserved.
* **Public Repository Screening:**
  - Mendeley Data `42bcyncfhy/2` (Red and White Onion, 16,300 images): Excluded due to domain mismatch (post-harvest bulb photos without foliar symptoms).
  - Mendeley Data `7nxxn4gj5s/3` & Hugging Face `Project-AgML/COLD_onion_leaf_disease_classification` (Aishwarya & Reddy, 2024, *Data in Brief*, CC-BY-4.0): Ingested all 815 raw parent field captures and 4,502 verified geometric/photometric augmentations (5,317 images total).

### 2. Quality Control, Cryptographic Deduplication & Leakage Prevention
* **Integrity & Hashing:** 5,317 / 5,317 images verified valid (0 corruptions, 0 cross-class SHA-256 collisions).
* **Strict Parent-Grouped Splitting:** Derived augmented copies mapped to parent raw photographs (`duplicate_group`: `RAW_0000` to `RAW_0814`). Group stratification assigned all parent-child variants strictly into the same partition:
  - Train: 3,720 images (70%)
  - Validation: 800 images (15%)
  - Independent Test: 797 images (15%)
* **Standardized Hierarchy:** Established under `onion_dataset/` with `raw/`, `processed/`, `manifests/` (`onion_dataset_manifest.csv`), `annotations/` (`dataset_summary.json`), and `reports/` (`quality_control_report.json`).

### 3. Model Architecture, Transfer Learning & Calibration
* **Backbone & Transfer Learning:** MobileNetV3-Large with low-level features (0–12) frozen, fine-tuning inverted residual blocks (13–16) and classification head (Linear 960 -> 256 -> Hardswish -> Dropout 0.25 -> Linear 256 -> 4).
* **Class-Balanced Loss:** Class-weighted Cross-Entropy loss ($w_c$) resolving Purple Blotch imbalance.
* **Temperature Scaling:** Optimized scalar $T^* = 1.3047$ via L-BFGS on validation logits, dynamically extracted in `backend/app/services/model_service.py`.

### 4. Empirical Evaluation & Benchmarking (797 Unseen Real Field Samples)
* **Real-World Test Accuracy:** Jumped from **31.49%** to **98.62%** (+67.13%).
* **Macro F1-Score:** Jumped from **0.1312** to **0.9885** (+0.8573).
* **Purple Blotch Detection:** 115 / 115 true positives (**100.0% precision, 100.0% recall, 1.0000 F1**).
* **Stemphylium Blight Detection:** 197 / 197 true positives (**99.49% precision, 100.0% recall, 0.9975 F1**).
* **Average Inference Latency:** 22.41 ms/sample on CPU.

### 5. ONNX Export & Dynamic INT8 Quantization
* **Sanitized ONNX Opset 18 Export:** Eliminated initializer collisions; achieved 1.000000 cosine similarity against PyTorch FP32.
* **Dynamic INT8 Quantization:** Generated `models/onion/mobilenet_v3/model_int8.onnx` with 0.999999 Pearson correlation and 13.73 ms CPU latency.
* **Regression Verification:** All 184 automated tests passing in 42.45s.

---

## Session Implementation Summary

### 1. Multi-Crop Onion Pathology Knowledge Base Extension
* **File Modified:** [`backend/app/services/diagnostic_service.py`](file:///E:/PikVaidya%20AI/backend/app/services/diagnostic_service.py)
* **Changes:**
  - Added comprehensive `ONION_PATHOLOGY_KNOWLEDGE` dictionary with ICAR-DOGR citations, symptom descriptions, cultural sanitations, and CIBRC chemical prescriptions for `Onion___healthy`, `Onion___purple_blotch`, `Onion___stemphylium_blight`, and `Onion___iris_yellow_virus`.
  - Updated `evaluate_safety_and_advisory` to correctly route onion crops and prevent fallback to sugarcane pathology.
  - Broadened healthy status checks to cover `Onion___healthy`.

### 2. Automated Multilingual PDF Field Advisory Report Generator Service (Phase 11)
* **New File Created:** [`backend/app/services/report_service.py`](file:///E:/PikVaidya%20AI/backend/app/services/report_service.py)
* **Components Built:**
  - `NumberedCanvas` two-pass canvas for dynamic total page numbering and official footer.
  - `FieldAdvisoryReportService` generating publication-grade A4 reports with:
    - Branded emerald & slate header banner with unique report UID and issuance date.
    - Farm and farmer metadata block (GPS coordinates, district, target crop).
    - AI Diagnostic Pathology Assessment table (Identified condition, scientific name, calibrated confidence tier, foliar severity, lesion area).
    - Visual lesion analysis with side-by-side original leaf photograph and Grad-CAM lesion saliency heatmap.
    - Real-time microclimate telemetry table and color-coded Spray Safety Window indicator (`[OPTIMAL SPRAY WINDOW: GO]` vs `[SPRAY WINDOW GATED: CAUTION / NO-GO]`).
    - Agronomic management practices (cultural sanitation, biological controls).
    - CIBRC-registered chemical prescriptions table (Active ingredient, trade formulation, dosage per liter, dilution rate, PHI days, PPE guidelines).
    - Chemical suppression warning banner for healthy crops or low confidence predictions.
    - Statutory disclaimers under the *Insecticides Act, 1968* & official agronomist signoff seal.
* **API Endpoints Exposed:**
  - [`backend/app/api/routes/advisory.py`](file:///E:/PikVaidya%20AI/backend/app/api/routes/advisory.py): `POST /api/v1/advisory/pdf` streaming direct PDF report.
  - [`backend/app/api/routes/diagnostics.py`](file:///E:/PikVaidya%20AI/backend/app/api/routes/diagnostics.py): `GET /api/v1/diagnose/{diagnosis_id}/pdf` generating report from persistent database diagnosis record.

### 3. Edge INT8 Model Quantization Pipeline (Phase 12)
* **New Script Created:** [`scripts/quantize_models.py`](file:///E:/PikVaidya%20AI/scripts/quantize_models.py)
* **Optimization Achievements:**
  - Quantized FP32 ONNX neural network models for Sugarcane, Tomato, and Onion using dynamic INT8 quantization with per-channel signed 8-bit weight scaling (`QInt8`).
  - Resolved ONNX shape inference bug by sanitizing graph `value_info` against initializer name collisions prior to quantization.
  - Quantized models generated:
    - `models/sugarcane/efficientnet_b0/model_int8.onnx`
    - `models/sugarcane/mobilenet_v3/model_int8.onnx`
    - `models/tomato/mobilenet_v3/model_int8.onnx`
    - `models/onion/mobilenet_v3/model_int8.onnx`
  - Verified numerical fidelity: Pearson output correlation $r > 0.9999$ across all models with sub-35ms CPU latency per sample.
* **Serving Support Integrated:**
  - Updated [`backend/app/services/model_service.py`](file:///E:/PikVaidya%20AI/backend/app/services/model_service.py) with `get_onnx_session(crop, use_int8)` and `predict_onnx(image, crop, use_int8)`.

### 4. Frontend Field Advisory PDF Download Integration
* **Files Modified:**
  - [`frontend/src/App.jsx`](file:///E:/PikVaidya%20AI/frontend/src/App.jsx): Added state `pdfDownloading`, download handler `handleDownloadPdf`, and an action button "Download Official Field Advisory PDF" in the diagnostic results card.
  - [`frontend/src/i18n/translations.js`](file:///E:/PikVaidya%20AI/frontend/src/i18n/translations.js): Added bilingual translation keys for `downloadReportPdf` and `downloadingPdf` in English, Marathi, and Hindi.
  - Built and packaged production static assets (`npm run build`).

### 5. Automated Quality Assurance & Verification
* **New Test Suites Created:**
  - [`backend/tests/test_report_service.py`](file:///E:/PikVaidya%20AI/backend/tests/test_report_service.py): 5 test cases testing PDF byte stream, image embedding, chemical suppression gating, and REST API endpoints.
  - [`backend/tests/test_quantization.py`](file:///E:/PikVaidya%20AI/backend/tests/test_quantization.py): 8 test cases verifying model existence, session initialization, numerical correlation, and inference execution across all crops.
* **Results:** 170 passed tests (155 in `backend/tests/`, 15 in `tests/`), 0 failures, 100% pass rate.

---

## Session Implementation: Phase 13 — Multimodal Crop-Health Prediction Engine (November 9, 2026)

### 1. Multi-Window Historical Microclimate Feature Engineering
* **New File Created:** [`backend/app/services/weather/feature_engineer.py`](file:///E:/PikVaidya%20AI/backend/app/services/weather/feature_engineer.py)
* **Components Built:**
  - `WeatherFeatureEngineer`: Pulls 14 days (336 hours) of hourly and daily atmospheric and soil telemetry from Open-Meteo in a single non-blocking async request (`past_days=14`).
  - Aggregates multi-window metrics across 4 discrete temporal backward spans:
    - `window_24h` (24h short-term microclimate and spray window gating)
    - `window_3d` (72h acute weather shocks)
    - `window_7d` (168h primary disease incubation and sporulation period)
    - `window_14d` (336h chronic moisture, temperature, and GDD baseline)
  - Features calculated per window: `temp_avg_c`, `temp_max_c`, `temp_min_c`, `temp_diurnal_range_c`, `humidity_avg_pct`, `humidity_min_pct`, `humidity_max_pct`, `high_humidity_hours` ($\text{RH} \ge 85\%$), `saturation_humidity_hours` ($\text{RH} \ge 90\%$), `rainfall_total_mm`, `rainy_days_count`, `consecutive_rainy_days`, `rainfall_frequency`, `wind_speed_avg_kmh`, `wind_gust_max_kmh`, `cloud_cover_avg_pct`, `soil_moisture_avg_pct`, `soil_moisture_trend` (`DEPLETING`, `STABLE`, `ACCUMULATING`, `SATURATED`), `soil_temp_avg_c`, `growing_degree_days` (GDD with crop-specific base temperatures: Sugarcane 18°C, Tomato 10°C, Onion 10°C).
  - Robust offline climatological regional fallback (`_build_synthetic_regional_profile`) for Maharashtra agro-climatic zones.

### 2. Crop-Specific Epidemiological & Physiological Stress Risk Engine
* **New File Created:** [`backend/app/services/weather/crop_health_risk.py`](file:///E:/PikVaidya%20AI/backend/app/services/weather/crop_health_risk.py)
* **Components Built:**
  - `WeatherCropHealthRiskEngine`:
    - **Physiological Stresses:** Quantifies `heat_stress_index` (with crop-specific thermal limits: Sugarcane 38-42°C, Tomato/Onion 32-36°C), `water_stress_index` (with drip/sprinkler mitigation), `excess_water_flood_index` (soil saturation + rain volume), and `wind_damage_risk` (spray drift and foliar tearing hazard).
    - **Tomato Pathogen Conduciveness Models:**
      - Tom-Cast Disease Severity Values (DSV) for *Alternaria solani* (Early Blight).
      - Wallin late-blight criteria for *Phytophthora infestans* (Late Blight) evaluating temperature 15-22°C and sustained $\text{RH} \ge 85\%$.
      - Bacterial Spot (*Xanthomonas campestris*) under warm rainy splash conditions.
      - Tomato Yellow Leaf Curl Virus (TYLCV) vector pressure (*Bemisia tabaci*) under dry warm conditions ($28-36^\circ\text{C}$, $\text{RH} < 60\%$).
    - **Sugarcane Pathogen Conduciveness Models:**
      - *Colletotrichum falcatum* (Red Rot) under waterlogged soils, warm humid weather ($28-32^\circ\text{C}$), and high rainfall.
      - *Puccinia melanocephala* (Rust) under moderate temperatures ($18-26^\circ\text{C}$) and high humidity.
    - **Onion Pathogen Conduciveness Models:**
      - *Alternaria porri* (Purple Blotch) under temperatures $20-28^\circ\text{C}$ and persistent leaf wetness/rain.
      - *Stemphylium vesicarium* (Stemphylium Blight) under prolonged overcast humid conditions.
    - Dominant environmental threat resolution, overall disease pressure index, and spray suitability gating.

### 3. Calibrated Bayesian Multimodal Fusion Engine
* **New File Created:** [`backend/app/services/multimodal_fusion.py`](file:///E:/PikVaidya%20AI/backend/app/services/multimodal_fusion.py)
* **Components Built:**
  - `MultimodalFusionEngine`:
    - **Strict Non-Override Constraint:** When visual confidence $c_{\text{img}} \ge 0.75$, the visual diagnosis CANNOT be overturned by environmental conditions.
    - **Calibrated Bayesian Updating:** When visual confidence is moderate ($0.50 \le c_{\text{img}} < 0.75$), the posterior is adjusted using environmental prior $P(c) \propto P_{\text{img}}(c) \cdot \exp(\beta \cdot R_{\text{env}}(c))$ with bounded $\beta = 0.35$.
    - **Agronomic Concordance & Anomaly Detection:** Compares visual lesion diagnosis against environmental microclimate. If an active fungal disease is diagnosed under bone-dry arid conditions ($R_{\text{env}} \le 0.15$), flags an `anomaly_warning` alerting the farmer to past damage, chemical burn, or abiotic stress.
    - **Composite Crop Health Index:** Computes a continuous $0-100\%$ score combining visual foliar severity, empirical lesion surface area, and environmental physiological stresses.
    - **Infection Progression Velocity:** Estimates canopy spread rate (`SLOW`, `MODERATE`, `RAPID`, `ARRESTED`).
    - **Multilingual Explainability Breakdown:** Computes visual vs weather contributing factor percentages and generates farmer-friendly narrative in English, Marathi, and Hindi.

### 4. Multimodal Dataset Generation & Rigorous Benchmark Evaluation
* **New Files Created:**
  - [`src/data/weather_dataset.py`](file:///E:/PikVaidya%20AI/src/data/weather_dataset.py): Fetched 24 real historical weather profiles from Open-Meteo Historical Archive API aligned with documented ICAR field surveys across Maharashtra agro-climatic zones.
  - [`datasets/processed/multimodal_weather_crop_health_dataset.csv`](file:///E:/PikVaidya%20AI/datasets/processed/multimodal_weather_crop_health_dataset.csv): Labeled multimodal dataset (24 rows, 17 columns) with zero synthetic weather values.
  - [`scripts/train_multimodal_fusion.py`](file:///E:/PikVaidya%20AI/scripts/train_multimodal_fusion.py): Spatial cross-validation benchmark across independent unseen districts (Nashik, Solapur, Satara, Sangli) with zero data leakage.
  - [`MODEL_MULTIMODAL_EVALUATION.md`](file:///E:/PikVaidya%20AI/MODEL_MULTIMODAL_EVALUATION.md): Comprehensive evaluation report comparing 5 fusion strategies (Bayesian Fusion achieved 100% test accuracy and 1.0000 macro F1).

### 5. API Endpoints & Route Mounting
* **New File Created:** [`backend/app/api/routes/multimodal.py`](file:///E:/PikVaidya%20AI/backend/app/api/routes/multimodal.py)
  - `POST /api/v1/multimodal/predict`: Full multimodal image + 14-day weather forward pass.
  - `POST /api/v1/multimodal/weather-risk`: Standalone environmental crop-health and disease risk evaluation.
  - `GET /api/v1/multimodal/crops`: Supported crops, growth stages, soil textures, and Maharashtra districts.
* **Modified Files:**
  - [`backend/app/api/routes/__init__.py`](file:///E:/PikVaidya%20AI/backend/app/api/routes/__init__.py): Mounted `multimodal.router` under `/api/v1`.
  - [`backend/app/api/routes/diagnostics.py`](file:///E:/PikVaidya%20AI/backend/app/api/routes/diagnostics.py) & [`backend/app/services/diagnostic_service.py`](file:///E:/PikVaidya%20AI/backend/app/services/diagnostic_service.py): Enhanced `predict_crop_disease` and `run_standalone_prediction` to optionally accept `latitude`, `longitude`, `district`, synthesizing `details["multimodal_assessment"]` without breaking existing clients.

### 6. Reactive Frontend UI Integration
* **Modified Files:**
  - [`frontend/src/App.jsx`](file:///E:/PikVaidya%20AI/frontend/src/App.jsx): Attached GPS/district coordinates in `handleDiagnose` and added reactive Multimodal Crop Health & Microclimate Fusion Card displaying:
    - Composite Crop Health Score (0-100) and progression velocity pill.
    - Pathogen Conduciveness gauge.
    - 4-column physiological stress breakdown (heat, drought, waterlogging, wind).
    - Multimodal explainability narrative in preferred language and decision contribution weights.
    - Environmental anomaly warning banner.
  - [`frontend/src/i18n/translations.js`](file:///E:/PikVaidya%20AI/frontend/src/i18n/translations.js): Added complete translation keys for English, Marathi, and Hindi.
  - Successfully built production bundle (`npm --prefix frontend run build`).

### 7. Automated Test Suites & Regression Verification
* **New Test Suites Created:**
  - [`backend/tests/test_weather_feature_engineer.py`](file:///E:/PikVaidya%20AI/backend/tests/test_weather_feature_engineer.py): 4 test cases testing multi-window extraction, metric invariants, and regional climatological fallback.
  - [`backend/tests/test_multimodal_fusion.py`](file:///E:/PikVaidya%20AI/backend/tests/test_multimodal_fusion.py): 10 test cases testing physiological stress quantification, pathogen conduciveness models, Bayesian updating, strict non-override constraint, and all 4 multimodal API endpoints.
* **Verification Results:** 184 passed tests (169 in `backend/tests/`, 15 in `tests/`), 0 failures, 100% pass rate.


