# PikVaidya AI — Agricultural Advisory & Agronomic Review

**Domain:** Agricultural Pathology, CIBRC/ICAR Chemical Safety, Bilingual Translation  
**Target Crop:** Sugarcane (*Saccharum officinarum*) with Multi-Crop Assessment (Tomato, Soybean, Onion)  
**Lead Evaluator:** Lead Agricultural AI Validation Engineer & Consulting Agronomist  
**Review Status:** **NEEDS EXPERT REVIEW (Mandatory Agronomist Sign-Off Required Prior to Field Release)**

---

## 1. Disease Profile & Regulatory Chemical Alignment

PikVaidya AI contains an embedded knowledge base (`CROP_DIAGNOSTIC_KNOWLEDGE`) in `backend/app/services/ai_service.py`. Below is the technical and regulatory evaluation against Indian Council of Agricultural Research (ICAR) guidelines and Central Insecticides Board & Registration Committee (CIBRC) approved label claims.

### A. Sugarcane Pathology Evaluation

| Disease | Causal Organism & Classification | Embedded Recommendation in System | ICAR / CIBRC Technical Validation | Agronomic Risk Rating |
| :--- | :--- | :--- | :--- | :---: |
| **Red Rot** | *Colletotrichum falcatum* (Fungal, Ascomycota) | "Eradicate affected clumps. Treat seed setts with Carbendazim 50% WP @ 1g/L. Practice crop rotation and avoid ratooning infected crop." (Marathi: बेणे प्रक्रियेसाठी कार्बेन्डाझिम ५०% डब्ल्यूपी १ ग्रॅम/लीटर वापरा) | **Accurate.** Sett dip treatment with Carbendazim 50% WP @ 0.1% or Thiophanate-methyl 70% WP @ 0.1% is the recognized prophylactic standard. Clump roguing prevents air-borne conidial spread. | **LOW (Safe)** |
| **Mosaic** | Sugarcane Mosaic Virus (SCMV / Potyvirus) | "Control aphid vectors with Imidacloprid 17.8% SL @ 0.3ml/L. Use virus-free tissue culture planting material." (Marathi: मावा किडीच्या नियंत्रणासाठी इमिडाक्लोप्रिड १७.८% एसएल ०.३ मिली/लीटर फवारा) | **Technically Sound.** Mosaic is non-persistently transmitted by aphids (*Rhopalosiphum maidis*). While foliar insecticides do not eliminate viral titers already in plants, vector management reduces intra-field transmission. | **MEDIUM** (Must clarify that insecticide treats aphids, not the virus directly) |
| **Rust** | *Puccinia kuehnii* / *P. melanocephala* (Fungal, Basidiomycota) | "Spray Mancozeb 75% WP @ 2g/L or Propiconazole 25% EC @ 1ml/L at onset of rust pustules." (Marathi: मॅन्कोझेब ७५% डब्ल्यूपी २ ग्रॅम/लीटर किंवा प्रोपिकोनाझोल २५% ईसी १ मिली/लीटर फवारा) | **Accurate.** Mancozeb (contact) and Propiconazole (systemic triazole) are standard CIBRC-registered fungicides for foliar rust suppression. | **LOW (Safe)** |
| **Yellow Leaf** | Sugarcane Yellow Leaf Virus (SCYLV / Luteovirus) | "Maintain balanced potassium/nitrogen fertigation. Control insect vectors and avoid waterlogging." (Marathi: संतुलित पोटॅश आणि नत्र खतांचा वापर करा) | **Partially Sound.** Vector control (*Melanaphis sacchari*) and potassium nutrition mitigate systemic stunting. However, no curative chemical spray exists for luteoviruses. | **LOW (Safe)** |
| **Healthy** | None | "Continue standard nutritional fertigation and routine pest scouting. Maintain optimal soil moisture." | **Safe.** Encourages standard agronomic practices without introducing synthetic inputs. | **NONE** |

---

## 2. Bilingual Quality Audit (English vs. Marathi)

Maharashtra is one of India's top sugarcane-producing states. Vernacular Marathi (`mr`) translations were evaluated for dialectal clarity, scientific accuracy, and peasant farmer comprehension:

1. **Red Rot (तांबडे कूज / लाल सड):**
   * *Assessment:* The terminology "तांबडे कूज" or "लाल सड" perfectly matches local usage in Western Maharashtra and Marathwada regions.
   * *Sett Treatment Translation:* "बेणे प्रक्रियेसाठी कार्बेन्डाझिम ५०% डब्ल्यूपी १ ग्रॅम/लीटर वापरा" correctly employs the localized term "बेणे" (setts/seedcane) rather than generic "बियाणे" (botanical seeds). **Grade: EXCELLENT.**
2. **Rust (तांबेरा):**
   * *Assessment:* "तांबेरा" is the standard vernacular term across MPKV Rahuri and state agricultural universities. Translation correctly instructs applying fungicide at the onset of symptoms ("लक्षणे दिसताच"). **Grade: EXCELLENT.**
3. **Mosaic (मोझॅक विषाणू रोग):**
   * *Assessment:* "मावा किडीच्या नियंत्रणासाठी" correctly identifies aphids as "मावा". **Grade: GOOD.**

---

## 3. Critical Safety Disconnects & Agronomic Hazards

### A. Lack of Confidence-Gated Advisories (CRITICAL RISK)
* **Hazard:** If a farmer submits an ambiguous, blurry, or backlit photo where the model returns a borderline 42% confidence for Red Rot, the backend returns the exact same urgent chemical treatment plan as a 99% confident diagnosis.
* **Agronomic Consequence:** Unnecessary sett-dip preparation, unnecessary eradication of healthy standing cane, or improper fungicide application incurring financial distress for smallholder farmers.
* **Required Mitigation:** Introduce a 3-tier confidence gateway:
  * **Confidence $\ge 75\%$:** Issue standard disease diagnosis and chemical/cultural advisory.
  * **$50\% \le \text{Confidence} < 75\%$:** Issue provisional diagnosis marked with cautionary label *"Low Confidence — Verify with Extension Worker"* and recommend non-chemical cultural scouts first.
  * **Confidence $< 50\%$:** Suppress chemical treatment completely; prompt farmer to retake the photo with better lighting or consult a local Krishi Vigyan Kendra (KVK).

### B. Unvalidated Static Severity & Area Assignment (HIGH RISK)
* **Hazard:** As proven in Phase 3, `severity` is unconditionally marked `SEVERE` for Red Rot and `MODERATE` for all others, with hardcoded lesion areas (22% / 15%).
* **Agronomic Consequence:** In precision agriculture, chemical application volumes and economic injury levels (EIL) depend heavily on disease stage. Prescribing identical measures regardless of whether 1 leaf or 80% of the canopy is affected undermines agronomic efficacy.

### C. Absence of Pre-Harvest Interval (PHI) & Water Volume Instructions (MEDIUM RISK)
* **Hazard:** Recommending Propiconazole 25% EC or Mancozeb 75% WP without specifying water spray volume (typically 500–750 L/ha) or Pre-Harvest Intervals (PHI) risks chemical residue violations if applied near cane harvest.
* **Required Mitigation:** Append standard applicator safety notices (PPE, spray volume per acre, and withholding periods).

---

## 4. Multi-Crop Expansion Audit (Tomato, Soybean, Onion)

* **Finding:** In `backend/app/services/ai_service.py` (lines 178–218), diagnostic requests for tomato, soybean, or onion bypass deep learning inference completely and return **simulated hardcoded responses** (e.g. Early Blight for tomato, Rust for soybean) with synthetic 91%–94% confidence.
* **Audit Directive:** These endpoints are non-functional simulations and must be gated off in production staging until actual multi-crop neural networks are trained, validated, and loaded.

---

## 5. Formal Agronomic Sign-Off Requirement

Before releasing PikVaidya AI to farmers in the field, this advisory matrix must receive written formal endorsement from:
1. Certified Plant Pathologist from an ICAR-affiliated State Agricultural University (e.g., MPKV Rahuri or Vasantdada Sugar Institute - VSI).
2. Agricultural Extension Officer ensuring compliance with Maharashtra State Department of Agriculture pesticide advisory guidelines.
