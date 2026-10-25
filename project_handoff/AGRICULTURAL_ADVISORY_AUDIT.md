# Agricultural Advisory & Agronomic Review: PikVaidya AI

**Document Version:** 1.0.0  
**Audit Date:** October 25, 2026  
**Lead Auditor:** Lead Agricultural AI Validation Engineer & Consulting Agronomist  
**Evaluation Standards:** Indian Council of Agricultural Research (ICAR) Crop Protection Protocols, Central Insecticides Board & Registration Committee (CIBRC) Approved Chemical Label Claims, and Insecticides Act, 1968 Compliance Guidelines  
**Current Agronomic Status:** **NEEDS DOMAIN EXPERT REVIEW (Mandatory Agronomist Sign-Off Required Prior to Field Release)**

---

## 1. Executive Summary

PikVaidya AI is intended to provide actionable foliar disease diagnostics and treatment recommendations to farmers in Maharashtra, India. This audit evaluates:
1. The scientific accuracy and regulatory compliance of embedded chemical and cultural recommendations.
2. The vernacular Marathi translation quality for smallholder peasant farmers.
3. The systemic agronomic hazards arising from automated advisory generation without confidence gating or true severity estimation.

### Key Agronomic Findings
* **Chemical Treatment Accuracy:** Sugarcane disease recommendations for Red Rot, Rust, and Mosaic align with recognized ICAR package of practices and CIBRC registered fungicides/insecticides.
* **Vernacular Translation Quality:** **EXCELLENT**. Marathi translations use authentic regional agricultural terminology (e.g., "बेणे" for seed setts, "तांबेरा" for rust, "मावा" for aphids).
* **Critical Safety Disconnect (P0 Risk):** The backend lacks **confidence-gated advisory suppression**. A low-confidence prediction (e.g. 35% probability from a poorly lit photo) triggers the exact same aggressive chemical spray instructions as a 99% confident diagnosis.
* **Pesticide Residue & Applicator Safety Gaps:** The system omits **Pre-Harvest Intervals (PHI)**, water dilution volumes per hectare, and personal protective equipment (PPE) instructions.
* **Simulated Multi-Crop Advisories:** Tomato, Cotton, Soybean, and Onion bypass machine learning entirely and return static, simulated disease advisories.

---

## 2. Advisory Generation Pipeline & Knowledge Base Architecture

Advisory generation is implemented in `backend/app/services/ai_service.py` via an in-memory dictionary `CROP_DIAGNOSTIC_KNOWLEDGE`.

```
                    Crop Leaf Image & Telemetry Ingested
                                      │
                         Normalized Crop Name Check
                                      │
            ┌─────────────────────────┴─────────────────────────┐
            ▼                                                   ▼
 Crop contains "sugarcane"                        Crop is Cotton, Tomato, Soybean, Onion
 ─────────────────────────                        ──────────────────────────────────────
 • Evaluates model_service.predict()              • Bypasses PyTorch inference completely
 • Extracted predicted_class                      • Matches substring key in dictionary
 • Queries CROP_DIAGNOSTIC_KNOWLEDGE["sugarcane"] • Returns hardcoded single disease profile
 • Hardcodes severity (RedRot=Severe, else Mod)   • Assigns simulated confidence (0.91 / 0.94)
 • Formats bilingual advisory response            • Formats bilingual advisory response
```

### Knowledge Base Profiles
The system defines 8 distinct localized disease profiles:

1. **Sugarcane — Red Rot (*Colletotrichum falcatum*):**
   * Pathogen: Fungal (Ascomycota)
   * English Symptoms: "Red discoloration of internal vascular bundles with transverse white patches, spindle-shaped lesions along leaf midrib."
   * Marathi Symptoms: "पानाच्या मधल्या शिरेवर लालसर लांबट ठिपके आणि उसाच्या कांडीच्या आत लाल रंग व पांढरे पट्टे दिसणे."
   * Chemical & Cultural Advice: "Eradicate affected clumps. Treat seed setts with Carbendazim 50% WP @ 1g/L. Practice crop rotation and avoid ratooning infected crop."
2. **Sugarcane — Common Rust (*Puccinia kuehnii*):**
   * Pathogen: Fungal (Basidiomycota)
   * English Symptoms: "Small, elongate yellowish spots that turn reddish-brown and rupture into powdery fungal pustules on leaf surface."
   * Chemical Advice: "Spray Mancozeb 75% WP @ 2g/L or Propiconazole 25% EC @ 1ml/L at onset of rust pustules."
3. **Sugarcane — Mosaic Virus (SCMV):**
   * Pathogen: Viral (Potyvirus transmitted by aphids)
   * Chemical Advice: "Control aphid vectors with Imidacloprid 17.8% SL @ 0.3ml/L. Use virus-free tissue culture planting material."
4. **Sugarcane — Yellow Leaf Disease (SCYLV):**
   * Pathogen: Viral (Luteovirus)
   * Advice: "Maintain balanced potassium/nitrogen fertigation. Control insect vectors and avoid waterlogging."
5. **Tomato — Early Blight (*Alternaria solani*) [MOCK]:**
   * Chemical Advice: "Apply Mancozeb 75% WP @ 2.5g/L or Azoxystrobin 23% SC @ 1ml/L."
6. **Soybean — Soybean Rust (*Phakopsora pachyrhizi*) [MOCK]:**
   * Chemical Advice: "Spray Hexaconazole 5% SC @ 2ml/L or Tebuconazole 25.9% EC @ 1.5ml/L."
7. **Onion — Purple Blotch (*Alternaria porri*) [MOCK]:**
   * Chemical Advice: "Spray Difenoconazole 25% EC @ 1ml/L or Chlorothalonil 75% WP @ 2g/L along with a sticker/spreader."
8. **Cotton — Leaf Curl Virus (CLCuV) [MOCK]:**
   * Chemical Advice: "Control whitefly vectors using Neem oil (1500 ppm) @ 5ml/L or Diafenthiuron."

---

## 3. Regulatory Alignment & Chemical Verification (ICAR & CIBRC)

Every chemical recommendation in `ai_service.py` was cross-referenced with Central Insecticides Board & Registration Committee (CIBRC) approved formulations:

| Crop & Disease | Recommended Active Ingredient & Formulation | Application Rate | CIBRC / ICAR Regulatory Status | Agronomic Rating |
| :--- | :--- | :---: | :--- | :---: |
| **Sugarcane Red Rot** | **Carbendazim 50% WP** | 1 g / L water (Sett dip) | Approved for sugarcane sett dipping to suppress conidial inoculation. Clump roguing prevents air-borne spread. | **ACCURATE & SAFE** |
| **Sugarcane Rust** | **Mancozeb 75% WP**<br>**Propiconazole 25% EC** | 2 g / L water<br>1 ml / L water | Both are standard CIBRC-registered fungicides for foliar rust in sugarcane. Contact + systemic combination is sound. | **ACCURATE & SAFE** |
| **Sugarcane Mosaic** | **Imidacloprid 17.8% SL** | 0.3 ml / L water | Imidacloprid controls the aphid vector (*Rhopalosiphum maidis*). While it prevents intra-field vector spread, it does **not cure viral titers in infected plants**. | **CONDITIONALLY SOUND** (Needs vector clarification) |
| **Sugarcane Yellow Leaf** | Fertigation + Vector Management | Cultural | No registered viricide exists. Recommending potassium nutrition and vector suppression is agronomically correct. | **SAFE** |
| **Tomato Early Blight** | **Mancozeb 75% WP**<br>**Azoxystrobin 23% SC** | 2.5 g / L water<br>1 ml / L water | Registered protective and curative fungicides for *Alternaria solani*. | **ACCURATE (Untrained Model)** |
| **Soybean Rust** | **Hexaconazole 5% SC**<br>**Tebuconazole 25.9% EC** | 2 ml / L water<br>1.5 ml / L water | Standard triazole fungicides registered for soybean rust suppression. | **ACCURATE (Untrained Model)** |
| **Onion Purple Blotch** | **Difenoconazole 25% EC**<br>**Chlorothalonil 75% WP** | 1 ml / L water<br>2 g / L water | Broad-spectrum registered fungicides. Emphasizing a spreader/sticker (डिंक) is agronomically essential for waxy onion leaves. | **ACCURATE (Untrained Model)** |

---

## 4. Critical Agronomic Safety Risks & Field Liabilities

### 🚨 Risk 1: Absence of Confidence-Gated Chemical Advisories (CRITICAL P0)
* **The Problem:** The API delivers identical chemical pesticide recommendations regardless of classification confidence.
* **The Hazard:** If a farmer submits an ambiguous, backlit, or out-of-focus leaf photograph, and the model predicts Red Rot with only **38% confidence** (with 32% Mosaic and 30% Healthy), the system outputs:
  > *"Eradicate affected clumps. Treat seed setts with Carbendazim 50% WP @ 1g/L. Practice crop rotation and avoid ratooning infected crop."*
* **Agronomic Consequence:** The farmer may unnecessarily eradicate standing healthy cane, purchase expensive fungicides, or dip setts needlessly, causing severe financial distress.
* **Required Mitigation:** Implement a 3-tier confidence gateway:
  * **Confidence $\ge 75\%$:** Issue definitive diagnosis and standard chemical/cultural advisory.
  * **$50\% \le \text{Confidence} < 75\%$:** Issue provisional diagnosis with an Amber warning: *"Low Confidence — Inspect foliage with local agricultural extension worker before chemical purchase."* Suppress chemical prescriptions and recommend cultural monitoring only.
  * **Confidence $< 50\%$:** Suppress diagnosis and chemical advisory entirely; prompt farmer to retake the photo under better lighting or visit the nearest Krishi Vigyan Kendra (KVK).

### 🚨 Risk 2: Hardcoded Disease Severity & Lesion Surface Heuristics (HIGH P1)
* **The Problem:** Severity is statically hardcoded in `ai_service.py`:
  * Red Rot $\rightarrow$ `DiagnosisSeverity.SEVERE` ($22.0\%$ affected area).
  * All other diseases $\rightarrow$ `DiagnosisSeverity.MODERATE` ($15.0\%$ affected area).
* **Agronomic Consequence:** Chemical spray volumes and economic injury levels (EIL) depend heavily on disease stage and canopy coverage. Advising identical measures regardless of whether a leaf has 1 minor spot or 70% necrotic collapse undermines precision agriculture.

### 🚨 Risk 3: Absence of Pre-Harvest Intervals (PHI) & Water Spray Volumes (HIGH P1)
* **The Problem:** Prescribing Propiconazole 25% EC or Mancozeb 75% WP without specifying withholding periods (Pre-Harvest Intervals) creates pesticide residue violation risks if applied near cane harvesting.
* **Missing Details:** Chemical spray volume per hectare (typically 500–750 L/ha for field crops using knapsack sprayers) is not specified, leading to improper dilution rates in the field.

### 🚨 Risk 4: Missing Statutory Legal Disclaimer (MEDIUM P2)
* Under the **Insecticides Act, 1968**, prescribing scheduled chemical pesticides without statutory warnings creates legal liability.
* **Required Action:** Display this mandatory disclaimer on every advisory card:
  > *"Advisory Notice: Pesticide dosages are based on standard ICAR/CIBRC agricultural recommendations. Actual field effectiveness depends on local weather, soil, and crop stage. Always read the pesticide container label and consult your Taluka Agricultural Officer or local Krishi Vigyan Kendra (KVK) before chemical application."*

---

## 5. Vernacular Marathi (`mr`) Quality Audit

Maharashtra represents over 2.5 million hectares of sugarcane cultivation. Vernacular Marathi translations in `ai_service.py` were audited for agronomic precision:

| English Term | System Marathi Translation | Agronomic Assessment & Regional Context | Quality Grade |
| :--- | :--- | :--- | :---: |
| **Red Rot** | **ऊसावरील तांबडे कूज / लाल सड** | Highly accurate regional terminology used throughout Western Maharashtra and Marathwada. | **EXCELLENT** |
| **Seed Setts** | **बेणे (बेणे प्रक्रिया)** | Agronomically authentic. Uses the exact Marathi term "बेणे" (stem cuttings/setts) rather than the generic botanical term "बियाणे" (seeds). | **EXCELLENT** |
| **Sugarcane Rust** | **ऊसावरील तांबेरा रोग** | Standard vernacular term used by MPKV Rahuri and state agricultural universities. | **EXCELLENT** |
| **Aphid Vectors** | **मावा किडीच्या नियंत्रणासाठी** | Accurately identifies aphid vectors as "मावा" in vernacular Marathi. | **EXCELLENT** |
| **Early Symptoms** | **रोगाची लक्षणे दिसताच** | Crucial prophylactic advice ("at the first appearance of symptoms") correctly translated. | **EXCELLENT** |
| **Spreader / Sticker**| **स्टिकर (डिंक) मिसळून** | Appropriately conveys the necessity of using agricultural surfactant/gum for waxy onion foliage. | **EXCELLENT** |

---

## 6. Multi-Crop Expansion Audit

In `backend/app/services/ai_service.py` (lines 178–218):
* Any diagnostic request for **Cotton**, **Tomato**, **Soybean**, or **Onion** bypasses deep learning models and triggers a substring search in `CROP_DIAGNOSTIC_KNOWLEDGE`.
* The API returns a static, unvarying response with synthetic confidence ($0.94$ if humidity $> 75\%$, otherwise $0.91$).
* **Audit Directive:** These endpoints are non-functional simulations and must be gated off with `HTTP 400 Unsupported Crop` or clearly labeled as *"Demonstration Advisory (Model Under Training)"* until verified PyTorch checkpoints are integrated.

---

## 7. Mandatory Agronomist Sign-Off Protocol

Before PikVaidya AI can be deployed in a farmer-facing pilot:
1. **ICAR / State Agricultural University (SAU) Review:** Formal written review and sign-off by a certified Plant Pathologist from an accredited institution (e.g., Mahatma Phule Krishi Vidyapeeth - MPKV Rahuri, or Vasantdada Sugar Institute - VSI, Pune).
2. **Maharashtra Department of Agriculture Alignment:** Verification of pesticide dosages with the current *Krishi Darshani* (कृषी दर्शनी) advisory manual published by Maharashtra agricultural universities.
3. **Organic & Biological Control Priority:** Expand recommendations to prioritize biological controls (e.g. *Trichoderma viride*, *Pseudomonas fluorescens*, and Neem formulations) as first-line defenses before chemical pesticides are prescribed.
