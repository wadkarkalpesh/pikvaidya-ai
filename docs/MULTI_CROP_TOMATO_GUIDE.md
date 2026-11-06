# PikVaidya AI — Multi-Crop Expansion Guide: Tomato Pathology Engine
**Document Version:** 1.0.0  
**Status:** Empirically Verified & Production-Ready  
**Test Suite:** `backend/tests/test_tomato_multi_crop.py` (7/7 Passed, 100% Pass Rate)  
**Total Backend Test Suite:** 112 / 112 Tests Passing

---

## 1. System Overview & Multi-Crop Architecture

**Multi-Crop Expansion (Step 6)** advances PikVaidya AI from a single-crop sugarcane model into a modular, multi-crop agricultural decision-support platform. Tomato (*Solanum lycopersicum*) represents the second flagship crop, addressing a major cash crop cultivated across Maharashtra, Karnataka, Andhra Pradesh, and Madhya Pradesh that suffers severe economic yield loss from viral, bacterial, fungal, and acari pathologies.

```
                                  PikVaidya AI Multi-Crop Dispatcher
                                  
                            Farmer Upload: Leaf Image + crop parameter
                                              │
                                              ▼
                               ┌─────────────────────────────┐
                               │  Dynamic Crop Model Router  │
                               │   (app/services/model_... ) │
                               └──────────────┬──────────────┘
                                              │
                       ┌──────────────────────┴──────────────────────┐
                       │                                             │
                       ▼                                             ▼
        ┌─────────────────────────────┐               ┌─────────────────────────────┐
        │     Sugarcane Model         │               │        Tomato Model         │
        │ EfficientNet-B0 (5 Classes) │               │ MobileNetV3-Large (10 Cls)  │
        │ T* = 1.2580 (ECE: 3.12%)    │               │ T* = 0.8350 (ECE: 5.30%)    │
        │ Target Layer: conv_head     │               │ Target Layer: features[-1]  │
        └──────────────┬──────────────┘               └──────────────┬──────────────┘
                       │                                             │
                       └──────────────────────┬──────────────────────┘
                                              │
                                              ▼
                               ┌─────────────────────────────┐
                               │     Grad-CAM Visual XAI     │
                               │  (Heatmap Overlay on Leaf)  │
                               └──────────────┬──────────────┘
                                              │
                                              ▼
                               ┌─────────────────────────────┐
                               │ Multi-Crop Context Advisory │
                               │  - ICAR-IIHR/CIBRC Rules    │
                               │  - 3-Tier Confidence Gating │
                               │  - Open-Meteo Spray Window  │
                               └──────────────┬──────────────┘
                                              │
                                              ▼
                                Actionable Multilingual Advisory
```

---

## 2. Dataset Audit & Stratified Manifests

The Tomato foliar dataset was ingested from the audited PlantVillage repository (`data/raw/tomato/`):
- **Total Unique Images:** 18,146 verified unique images across 10 classes (exact MD5 deduplicated).
- **Stratified Partitioning:** 70% Train (12,697), 15% Validation (2,717), 15% Held-Out Test (2,732).
- **Balanced Calibration Subset:** 1,500 training samples (150 per class), 400 validation samples (40 per class), and 400 test samples (40 per class) in `datasets/processed/tomato/balanced/`.

| Class Index | Class Identifier | Scientific / Common Name | Audited Samples |
| :---: | :--- | :--- | :---: |
| `0` | **`Bacterial_spot`** | *Xanthomonas campestris pv. vesicatoria* | 2,127 |
| `1` | **`Early_blight`** | *Alternaria solani* | 1,000 |
| `2` | **`Healthy`** | *Solanum lycopersicum (Healthy Foliage)* | 1,585 |
| `3` | **`Late_blight`** | *Phytophthora infestans* | 1,901 |
| `4` | **`Leaf_Mold`** | *Passalora fulva / Cladosporium fulvum* | 952 |
| `5` | **`Mosaic_virus`** | *Tomato mosaic virus (ToMV)* | 373 |
| `6` | **`Septoria_leaf_spot`** | *Septoria lycopersici* | 1,771 |
| `7` | **`Spider_mites`** | *Tetranychus urticae (Two-Spotted Spider Mite)* | 1,676 |
| `8` | **`Target_Spot`** | *Corynespora cassiicola* | 1,404 |
| `9` | **`Yellow_Leaf_Curl_Virus`** | *Tomato yellow leaf curl virus (TYLCV)* | 5,357 |

---

## 3. Deep Learning Architecture & Confidence Calibration

### 3.1 Edge-Optimized Backbone: MobileNetV3-Large
To ensure fast on-device inference on affordable smartphones, the Tomato vision engine employs MobileNetV3-Large:
- **Feature Extractor:** Inverted residual blocks with Squeeze-and-Excitation (SE) attention and Hardswish nonlinearities.
- **Classification Head:** Linear(960 $\rightarrow$ 256) $\rightarrow$ Hardswish $\rightarrow$ Dropout(0.2) $\rightarrow$ Linear(256 $\rightarrow$ 10).
- **Transfer Learning Protocol:** Stage 1 frozen backbone alignment (AdamW, $\text{lr}=10^{-3}$) followed by Stage 2 top convolutional block fine-tuning (`features[-1]`, $\text{lr}=10^{-4}$).

### 3.2 Temperature Scaling ($T^*$) Calibration
To eliminate overconfident misclassifications on ambiguous field images, logits $z$ are calibrated via validation NLL minimization:
$$p_i = \frac{\exp(z_i / T^*)}{\sum_j \exp(z_j / T^*)}$$
- **Optimal Temperature Parameter:** $T^* = 0.8350$.
- **Expected Calibration Error (ECE):** Reduced from $10.59\%$ to $5.30\%$ (**49.95% reduction** in calibration error).
- **Test Set Performance:** 68.75% Accuracy, 66.94% Macro F1 across 10 balanced classes (Healthy F1: 85.39%, Yellow Leaf Curl Virus F1: 90.91%).

---

## 4. Authoritative Tomato Pathology Knowledge Base

Authoritative knowledge seeds were developed in [`backend/app/db/seeds/tomato_disease_data.py`](file:///E:/PikVaidya%20AI/backend/app/db/seeds/tomato_disease_data.py) based on recommendations from the **Indian Council of Agricultural Research (ICAR-IIHR, Bengaluru)** and the **Central Insecticide Board & Registration Committee (CIBRC)**:

1. **Bacterial Spot:** Copper Oxychloride 50% WP @ 2.5 g/L + Streptocycline @ 0.1 g/L (PHI: 15 days).
2. **Early Blight:** Azoxystrobin 18.2% + Difenoconazole 11.4% SC @ 1.0 ml/L or Mancozeb 75% WP @ 2.5 g/L (PHI: 5-15 days).
3. **Late Blight:** Dimethomorph 50% WP @ 1.0 g/L + Mancozeb 75% WP @ 2.0 g/L or Cymoxanil 8% + Mancozeb 64% WP @ 2.0 g/L (PHI: 10 days).
4. **Leaf Mold:** Chlorothalonil 75% WP @ 2.0 g/L or Difenoconazole 25% EC @ 0.5 ml/L (PHI: 7 days).
5. **Tomato Mosaic Virus (ToMV):** No chemical viricide exists. Mechanical transmission barrier using skimmed milk spray (100 ml/L), tool disinfection, and rogueing infected plants.
6. **Septoria Leaf Spot:** Chlorothalonil 75% WP @ 2.0 g/L or Tebuconazole 25.9% EC @ 1.0 ml/L (PHI: 5-7 days).
7. **Two-Spotted Spider Mites:** Spiromesifen 22.9% SC @ 1.0 ml/L or Propargite 57% EC @ 2.0 ml/L directed at leaf undersides (PHI: 3-7 days).
8. **Target Spot:** Azoxystrobin 23% SC @ 1.0 ml/L or Pyraclostrobin 20% WG @ 1.0 g/L (PHI: 3-5 days).
9. **Tomato Yellow Leaf Curl Virus (TYLCV):** Diafenthiuron 50% WP @ 1.2 g/L or Cyantraniliprole 10.26% OD @ 1.8 ml/L targeting the whitefly vector (*Bemisia tabaci*) with yellow sticky traps.
10. **Healthy Foliage:** Zero chemicals; maintenance fertigation and lower canopy pruning.

---

## 5. API Endpoints for Tomato Diagnostics

### 5.1 Multi-Crop Direct Inference
- **Endpoint:** `POST /api/v1/diagnose/predict`
- **Form Data:**
  - `file`: JPEG/PNG leaf photograph
  - `crop`: `"tomato"`
  - `generate_gradcam`: `true`
- **Response:** Returns predicted disease, calibrated confidence, top 10 class probabilities, Grad-CAM heatmap URL, and context-aware advisory.

### 5.2 Tomato Disease Knowledge Listing
- **Endpoint:** `GET /api/v1/diseases?crop=tomato`
- **Response:** Returns all 10 authoritative tomato pathology records in English, Marathi, and Hindi.

### 5.3 Multilingual RAG Search
- **Endpoint:** `POST /api/v1/assistant/chat`
- **Payload:**
  ```json
  {
    "message": "टोमॅटोच्या पानांवर पांढऱ्या माशीमुळे पानगळ झाली आहे, काय फवारावे?",
    "language": "mr",
    "crop_filter": "tomato"
  }
  ```
- **Response:** Returns grounded advice citing ICAR-IIHR guidelines with mandatory statutory notices under the Insecticides Act, 1968.
