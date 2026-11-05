# PikVaidya AI — Context-Aware Agricultural Recommendation Engine Guide
**Document Version:** 1.0.0  
**Status:** Empirically Verified & Production-Ready  
**Test Coverage:** 98/98 Backend Tests Passing + 15/15 ML Root Tests Passing (113 Total Tests)

---

## 1. System Architecture & Objectives

The **Context-Aware Agricultural Recommendation Engine** represents Step 4 of the PikVaidya AI platform, bridging the gap between raw computer vision pathology classification and real-world farm decision-support.

Rather than returning isolated class probabilities, the engine synthesizes:
1. **Vision Inference:** PyTorch EfficientNet-B0 / MobileNetV3 predictions + Calibrated Confidence ($T^*$) + Grad-CAM attention.
2. **Empirical Foliar Lesion Quantification:** HSV color-space and Excess Green Index (ExG) lesion area percentage (Mild $<15\%$, Moderate $15-40\%$, Severe $>40\%$).
3. **Authoritative Pathology Knowledge:** ICAR-Sugarcane Breeding Institute (SBI) and CIBRC-approved disease management profiles.
4. **Real-Time Weather Microclimate:** Open-Meteo REST API telemetry (temperature, relative humidity, wind speed, precipitation probability).
5. **Crop Growth Stage Context:** Farm agronomic phase (Germination, Tillering, Grand Growth, Maturity).

```
   ┌──────────────────────┐         ┌──────────────────────┐
   │    ML Vision & XAI   │         │ Weather Microclimate │
   │ EfficientNet-B0 / CAM│         │ Open-Meteo REST API  │
   └──────────┬───────────┘         └──────────┬───────────┘
              │                                │
              ▼                                ▼
   ┌───────────────────────────────────────────────────────┐
   │         Context-Aware Recommendation Engine           │
   │       (app/services/recommendation_engine.py)         │
   ├───────────────────────────────────────────────────────┤
   │ 1. Confidence Safety Gate (Suppress chemical < 75%)   │
   │ 2. Severity & Stage Adaptation (Mild/Mod/Severe)      │
   │ 3. Weather Spray Window Assessment (Rain/Drift/Heat)  │
   │ 4. CIBRC Fungicide Gating & Pre-Harvest Interval (PHI)│
   │ 5. Multilingual Delivery (English, Marathi, Hindi)    │
   │ 6. Statutory Compliance (Insecticides Act, 1968)      │
   └──────────────────────────┬────────────────────────────┘
                              │
                              ▼
   ┌───────────────────────────────────────────────────────┐
   │   Actionable Multilingual Farmer Advisory Response    │
   └───────────────────────────────────────────────────────┘
```

---

## 2. Safety Gating & Confidence Rules

To eliminate the risk of automated chemical misapplication and protect farmer capital, the recommendation engine enforces three strict confidence tiers:

| Tier | Confidence Range | Diagnostic Interpretation | Agrochemical Policy |
| :--- | :--- | :--- | :--- |
| **Tier 1: High Confidence** | $\ge 75\%$ | Verified foliar pathology | CIBRC-registered chemicals permitted with dosage, dilution, PHI, and PPE warnings. |
| **Tier 2: Moderate Confidence** | $50\% \le \text{conf} < 75\%$ | Provisional/Ambiguous diagnosis | **All chemical prescriptions strictly suppressed**. Cultural practices and daylight re-photographing advised. |
| **Tier 3: Low Confidence** | $< 50\%$ | Inconclusive scan | **All chemical prescriptions strictly withheld**. Physical inspection at local KVK or Taluka Agriculture Office required. |

> [!IMPORTANT]
> **Biological Viricide Rule:** For viral pathologies (*Sugarcane Mosaic Virus - SCMV*, *Sugarcane Yellow Leaf Virus - SCYLV*), biological viruses cannot be killed with direct chemical fungicides. Prescriptions are restricted strictly to insect vector control (e.g. Dimethoate 30% EC targeting aphids) alongside cultural rogueing.

---

## 3. Microclimate Weather Integration & Spray Window Rules

The weather service evaluates ambient microclimate to determine whether agrochemical foliar application is agronomically safe:

| Parameter | Threshold | Safety Classification | Operational Guidance |
| :--- | :--- | :--- | :--- |
| **Rain Hazard** | Precip $\ge 0.8$ mm or Rain Prob $\ge 50\%$ (next 6h) | `UNFAVOURABLE_RAIN_RISK` | **Postpone spraying.** Active ingredients will wash off before foliar absorption, polluting watercourses and causing economic loss. |
| **Wind Drift** | Wind Speed $> 15.0$ km/h | `UNFAVOURABLE_DRIFT_RISK` | **Avoid spraying.** High winds cause droplet drift to non-target adjacent crops, violating Insecticides Rules, 1971. |
| **Thermal Scorch** | Temperature $> 35.0^\circ$C | `UNFAVOURABLE_HEAT_STRESS` | **Avoid mid-day spraying.** High temperatures cause rapid droplet evaporation and foliar phytotoxicity (leaf burn). Spray 6:00-8:30 AM or late afternoon. |
| **Optimal Window** | Wind $\le 15$ km/h, Rain $< 50\%$, Temp $\le 35^\circ$C | `OPTIMAL` | **Conditions suitable.** Ensure uniform upper and lower leaf coverage with neutral pH water. |
| **Fungal Index** | Temp $20-32^\circ$C & Relative Humidity $\ge 75\%$ | `HIGH_FUNGAL_RISK` | Ambient microclimate accelerates fungal spore germination. Intensive scouting of adjacent rows mandated. |

---

## 4. API Endpoints

### 4.1 Generate Context-Aware Advisory
- **Endpoint:** `POST /api/v1/advisory/generate`
- **Payload:**
```json
{
  "crop_name": "sugarcane",
  "predicted_disease": "RedRot",
  "confidence": 0.91,
  "severity": "MODERATE",
  "affected_area_percentage": 22.5,
  "latitude": 16.7050,
  "longitude": 74.2433,
  "crop_stage": "grand_growth",
  "preferred_language": "mr"
}
```

### 4.2 Live Weather Microclimate & Spray Status
- **Endpoint:** `GET /api/v1/advisory/weather?lat=16.7050&lon=74.2433`
- **Response:**
```json
{
  "temperature_c": 28.5,
  "relative_humidity_pct": 68.0,
  "wind_speed_kmh": 9.0,
  "precipitation_mm": 0.0,
  "precipitation_probability_6h": 15.0,
  "weather_condition": "Partly cloudy",
  "is_live": true,
  "spray_suitability": "OPTIMAL",
  "is_safe_to_spray": true,
  "fungal_risk_level": "MODERATE",
  "spray_guidance": {
    "en": "Optimal Spray Conditions (28.5°C, 68.0% RH, Wind: 9.0 km/h).",
    "mr": "फवारणीसाठी अनुकूल हवामान (28.5°C, 68.0% आर्द्रता, वारा: 9.0 किमी/तास).",
    "hi": "छिड़काव के लिए अनुकूल मौसम (28.5°C, 68.0% नमी, हवा: 9.0 किमी/घंटा)।"
  }
}
```

---

## 5. Verification & Test Evidence

All components have been tested with pytest across unit, integration, and real-asset scenarios:
- `backend/tests/test_weather_service.py`: 5 passed
- `backend/tests/test_recommendation_engine.py`: 5 passed
- `backend/tests/test_advisory_endpoints.py`: 3 passed
- `backend/tests/` (Full backend suite): **98 passed in 53.92s**
- `tests/` (ML core suite): **15 passed in 14.66s**
- **Total Test Success:** **113 / 113 Tests Passed (0 Failures, 0 Errors)**

