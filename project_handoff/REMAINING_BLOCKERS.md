# Remaining Blockers & Technical Roadmap: PikVaidya AI

**Document Version:** 1.0.0  
**Date:** October 25, 2026  
**Audience:** Lead System Architect, ML Engineering Lead, Consulting Agronomist, and Project Reviewer  

---

## 1. Executive Summary

Phases 1 & 2 resolved the critical safety liabilities of the PikVaidya AI backend:
- Fabricated multi-crop predictions and synthetic confidence scores have been eliminated.
- Unsupported crops return clear, structured rejection responses.
- Fixed heuristic severity values (22%/15%) have been replaced with honest `UNAVAILABLE` statuses.
- A confidence-aware safety layer suppresses chemical pesticide prescriptions for ambiguous or uncertain predictions.
- Diagnostic workflows have been unified under a single hardened service.
- Production security defaults for `SECRET_KEY` and CORS have been hardened.

However, several foundational blockers remain before the platform can be deployed to smallholder farmers in Maharashtra. This document details each blocker, its risk rating, and the specific technical actions required.

---

## 2. Machine Learning & Dataset Blockers

### 🚨 Blocker 1: Missing Datasets & Vision Checkpoints for 4 Commercial Crops (CRITICAL P0)
* **The Problem:** The platform is conceived to diagnose 5 major commercial crops in Maharashtra (Sugarcane, Cotton, Tomato, Soybean, Onion). Currently, **only Sugarcane has a trained model**.
* **Current Repository Dataset Inventory:**
  * **Sugarcane:** 2,521 field images across 5 classes (`Healthy`, `Mosaic`, `RedRot`, `Rust`, `Yellow`). Model checkpoint verified and working.
  * **Cotton:** **0 images** (`data/raw/cotton/` is completely empty). Zero model exists.
  * **Soybean:** 1,119 images, but **100% are Healthy** (`data/raw/soybean/Healthy/`). Zero diseased images exist. A classifier trained on this dataset cannot identify disease.
  * **Tomato & Onion:** Raw datasets exist but have not been trained, tuned, or benchmarked.
* **Resolution Strategy:**
  1. Procure annotated disease imagery for Cotton (Bacterial Blight, Leaf Curl Virus, Alternaria) from ICAR-CICR (Central Institute for Cotton Research) or open repositories (Kaggle).
  2. Procure diseased Soybean imagery (Soybean Rust, Anthracnose, Cercospora) from ICAR-IISR (Indian Institute of Soybean Research).
  3. Train separate crop-specific models (or a unified crop-conditioned vision backbone) with proper multi-epoch training, learning rate warmup, and validation splits.
  4. Only register new crops in `diagnostic_service.SUPPORTED_CROPS` once their checkpoints achieve $>85\%$ macro F1-score on held-out field test sets.

### 🚨 Blocker 2: Absence of Pixel-Level Lesion Segmentation for Severity Quantification (HIGH P1)
* **The Problem:** The system currently returns `severity: UNAVAILABLE` and `affected_area_percentage: null` for all diseased crops. While safe and honest, farmers and agronomists need accurate disease severity percentages to decide whether chemical intervention meets Economic Injury Levels (EIL).
* **The Technical Gap:** EfficientNet-B0 is an image-level classifier; it outputs logits over 5 classes, not bounding boxes or segmentation masks. Grad-CAM heatmaps highlight activated convolutional filters ($7 \times 7$), but do not provide calibrated pixel-level lesion boundary masks.
* **Resolution Strategy:**
  1. Train a lightweight semantic segmentation model (e.g. MobileNetV3-UNet or DeepLabV3+ with MobileNet backbone) on annotated foliar disease masks.
  2. Compute affected foliage area percentage via:
     $$\text{Severity \%} = \frac{\text{Pixel Area of Necrotic/Chlorotic Lesions}}{\text{Total Foliage Pixel Area}} \times 100$$
  3. Map measured area percentage to standardized agronomic scale:
     - Mild: $< 10\%$
     - Moderate: $10\% - 25\%$
     - Severe: $> 25\%$

### 🚨 Blocker 3: Empirical Field Calibration of Confidence Thresholds (HIGH P1)
* **The Problem:** The current confidence thresholds ($0.75$ for High Confidence, $0.50$ for Moderate Warning) are conservative provisional baselines.
* **The Technical Gap:** Neural network softmax probabilities are notoriously overconfident on out-of-distribution (OOD) data (e.g., weeds, soil, fingers holding a leaf, non-leaf background clutter).
* **Resolution Strategy:**
  1. Implement temperature scaling or Platt scaling on validation logits to calibrate output probabilities to true empirical accuracy.
  2. Add an OOD / Background detector (e.g., binary leaf segmentation filter or background rejection class) to reject non-foliar uploads before executing disease classification.
  3. Validate thresholds against field test datasets captured with low-end Android mobile camera sensors under diverse lighting conditions (direct midday glare, backlighting, dawn/dusk shadows).

---

## 3. Client Frontend Blockers

### 🚨 Blocker 4: Complete Absence of Client Application (HIGH P1)
* **The Problem:** The `frontend/` directory is completely empty except for a placeholder `.gitkeep` and a brief markdown note. The platform exists solely as backend REST APIs.
* **Impact on Farmers:** Smallholder farmers cannot use Swagger UI or send multipart cURL commands from their smartphones.
* **Resolution Strategy:**
  1. Develop a responsive, mobile-first web application (or PWA) using React/Next.js or Flutter.
  2. Include:
     - Direct mobile camera capture with in-frame leaf alignment guidelines.
     - Offline caching and service workers for low-connectivity rural areas.
     - Bilingual toggle (Marathi default / English secondary).
     - Interactive visual comparison slider showing the original photograph alongside the Grad-CAM activation heatmap.
     - Farmer dashboard showing historical crop cycle diagnoses and advisory cards.

---

## 4. Agronomic & Regulatory Blockers

### ⚠️ Blocker 5: Domain Expert Agronomist Sign-Off on Chemical Packages (MEDIUM P2)
* **The Problem:** Although sugarcane disease treatments for Red Rot, Rust, and Mosaic align with recognized ICAR-SBI protocols and CIBRC approved chemicals, formal sign-off from a certified agronomist or KVK specialist has not yet been recorded.
* **Missing Specifics:**
  - Pre-Harvest Intervals (PHI) in days (e.g., minimum days between spraying Mancozeb/Propiconazole and cane harvesting).
  - Water spray volume per hectare calibrated for knapsack vs power sprayers (typically 500–750 L/ha).
  - Personal protective equipment (PPE) advisory for peasant applicators.
* **Resolution Strategy:**
  1. Conduct a joint review with an agronomist from Mahatma Phule Krishi Vidyapeeth (MPKV), Rahuri or ICAR-SBI, Coimbatore.
  2. Incorporate PHI tables and knapsack sprayer dilution charts into the advisory templates.

---

## 5. Infrastructure & Operations Blockers

### ⚠️ Blocker 6: Rate Limiting & Compute Defense for Inference Routes (MEDIUM P2)
* **The Problem:** `POST /api/v1/diagnose/predict` is an unauthenticated public route. Grad-CAM backpropagation requires full backward graph computation. Rapid automated requests could exhaust CPU/GPU resources.
* **Resolution Strategy:**
  1. Integrate rate limiting middleware (e.g. `slowapi` with Redis token bucket) restricting unauthenticated IP addresses to 10 requests per minute.
  2. Ensure background cleanup cron jobs periodically purge stale heatmaps from `uploads/heatmaps/`.

---

## 6. Prioritized Remediation Roadmap

| Priority | Phase | Target Component | Action Item |
| :---: | :---: | :--- | :--- |
| **P0** | Phase 3 | `data/`, `models/` | Curate diseased Cotton and Soybean datasets; train vision models for remaining crops. |
| **P1** | Phase 3 | `src/segmentation/` | Implement U-Net semantic segmentation for empirical foliage lesion percentage calculation. |
| **P1** | Phase 4 | `frontend/` | Build mobile-responsive bilingual (Marathi/English) client UI with camera integration. |
| **P1** | Phase 4 | `backend/app/services/` | Calibrate temperature scaling on model logits to ground softmax confidence in true empirical accuracy. |
| **P2** | Phase 5 | `backend/app/services/` | Obtain agronomist sign-off; add Pre-Harvest Intervals (PHI) and knapsack dilution tables to advisories. |
| **P2** | Phase 5 | `infra/`, `backend/` | Implement IP-based rate limiting on standalone inference and automated heatmap cache pruning. |
