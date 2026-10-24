# PikVaidya AI — Comprehensive Risk Register & Mitigation Roadmap

**Document:** Systemic Technical, Agronomic, and Operational Risk Register  
**Lead Evaluator:** Lead Software Engineer, Lead ML Engineer, & Agricultural AI Validation Engineer  
**Status:** **ACTIVE POST-AUDIT ACTION REGISTER**

---

## 1. Risk Matrix Summary

| Risk ID | Category | Risk Description | Severity | Likelihood | Impact | Status |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: |
| **RSK-01** | **Agronomic / AI** | Hardcoded static severity & lesion area (22% / 15%) presented as AI predictions | **CRITICAL** | High | High | Unmitigated (In Code) |
| **RSK-02** | **Safety / Liability** | Lack of confidence gating on chemical pesticide recommendations | **CRITICAL** | High | High | Action Required |
| **RSK-03** | **Expansion / Data** | Multi-crop mock endpoints returning synthetic 94% confidence for Tomato, Soybean, Onion | **HIGH** | High | High | Action Required |
| **RSK-04** | **Expansion / Data** | Soybean raw dataset contains exclusively "Healthy" samples (100% class imbalance) | **HIGH** | High | High | Data Incomplete |
| **RSK-05** | **Expansion / Data** | Cotton raw dataset completely missing from repository | **HIGH** | High | High | Data Absent |
| **RSK-06** | **Model / Field** | Out-of-Distribution (OOD) field imagery failure (shadows, background foliage, motion blur) | **MEDIUM** | High | Medium | Untested in Field |
| **RSK-07** | **Operational** | CPU Grad-CAM latency (~776 ms median / ~1.1s p95) under concurrent user spikes | **MEDIUM** | Medium | Medium | Infrastructure Need |
| **RSK-08** | **Legal / Regulatory**| Absence of statutory chemical disclaimer and Pre-Harvest Interval (PHI) guidance | **MEDIUM** | High | Low | Text Update |

---

## 2. In-Depth Risk Analyses & Mitigation Strategies

### RSK-01: Static Rule-Based Severity Estimation
* **Root Cause:** In `backend/app/services/ai_service.py`, `severity` is assigned via:
  ```python
  severity = DiagnosisSeverity.SEVERE if predicted_class == "RedRot" else DiagnosisSeverity.MODERATE
  affected_area_percentage = 22.0 if predicted_class == "RedRot" else 15.0
  ```
* **Consequence:** Misleads users into believing computer vision measured lesion coverage.
* **Mitigation Roadmap:**
  1. *Immediate (Sprint 1):* In API response schema, deprecate or rename `affected_area_percentage` to `estimated_stage_heuristic` and clearly annotate `is_heuristic: true`.
  2. *Strategic (Milestone 2):* Train a lightweight segmentation model (e.g., MobileNetV3-UNet or Otsu thresholding over Grad-CAM salient masks) to calculate true pixel-ratio lesion area.

---

### RSK-02: Absence of Confidence Gating for Pesticide Advice
* **Root Cause:** All predictions regardless of probability generate full chemical advisories.
* **Consequence:** An ambiguous image (e.g. 42% Mosaic probability) could induce a farmer to purchase and apply expensive systemic insecticides needlessly.
* **Mitigation Roadmap:**
  1. *Immediate (Sprint 1):* Enforce a hard confidence threshold in `ai_service.py`:
     * If `confidence < 0.70`, replace chemical treatments with: *"Diagnosis confidence is below verified threshold. Please do not apply chemical pesticides without physical verification by an agricultural extension specialist."*
  2. *UI Update:* Display warning banner in mobile/web frontend in yellow/amber for predictions between 50% and 70%.

---

### RSK-03 & RSK-04 & RSK-05: Multi-Crop Expansion Obstacles
* **Tomato (RSK-03):** While Tomato leaf images exist in `data/raw/tomato/`, no trained PyTorch checkpoint exists in `models/tomato/`. The backend currently returns mock data.
  * *Action:* Do not advertise Tomato support until an isolated EfficientNet-B0 checkpoint is trained, calibrated, and deployed.
* **Soybean (RSK-04):** `data/raw/soybean/` contains only a `Healthy/` folder. Zero disease classes (e.g. Soybean Rust, Frogeye Leaf Spot, Bacterial Blight) are present.
  * *Action:* Curate at least 500 images per disease class before attempting model training. Training on healthy-only data guarantees failure.
* **Cotton (RSK-05):** `data/raw/cotton/` is nonexistent.
  * *Action:* Source verified Cotton leaf pathology datasets (Bacterial Blight, Alternaria Leaf Spot, Grey Mildew) before scheduling training sprints.

---

### RSK-06: Generalization to Field Conditions (Out-of-Distribution Data)
* **Root Cause:** The 2,311 sugarcane dataset images feature relatively clean leaf cuttings or close-up photography.
* **Field Reality:** Real-world farmer uploads contain complex backgrounds (soil, weeds, hands, shadows, sunlight flare, and variable camera sensors).
* **Mitigation Roadmap:**
  1. Integrate an out-of-distribution (OOD) filter or crop/leaf detector (YOLOv8-nano crop detector) to verify the uploaded image actually contains sugarcane foliage before classifying disease.
  2. Implement test-time data augmentation (TTA) and collect feedback telemetry from initial farmer pilot deployments.

---

### RSK-07: Grad-CAM Compute Overhead & Concurrency
* **Measurement:** Single-image CPU inference takes ~141 ms, but generating and blending Grad-CAM heatmaps increases latency to ~776 ms median (1.1s at p95).
* **Impact:** 20 concurrent farmer requests could saturate single-worker Uvicorn processes and cause request queue timeouts.
* **Mitigation Roadmap:**
  1. Deploy with multiple Uvicorn workers (`--workers 4`) behind an NGINX reverse proxy.
  2. Offload Grad-CAM generation to an asynchronous background worker (Celery / Redis Queue) or only generate on demand when the farmer taps "Explain Diagnosis".

---

### RSK-08: Legal & Regulatory Disclaimer
* **Regulatory Context:** The Insecticides Act, 1968, and CIBRC regulations govern pesticide recommendations in India. An AI system prescribing scheduled pesticides without appropriate statutory warnings poses legal exposure.
* **Mitigation Roadmap:** Include the following statutory disclaimer in all API responses and farmer UI views:
  > *"Advisory Notice: Pesticide recommendations are based on standard CIBRC/ICAR agronomic literature. Dosage and efficacy vary with local soil, weather, crop phenology, and equipment. Always read pesticide container labels and consult your local Taluka Agricultural Officer or Krishi Vigyan Kendra before chemical application."*
