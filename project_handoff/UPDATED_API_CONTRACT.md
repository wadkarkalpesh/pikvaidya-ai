# Updated API Contract: PikVaidya AI Diagnostic System

**Document Version:** 1.1.0  
**Effective Date:** October 25, 2026  
**Base URL:** `http://localhost:8000/api/v1`  
**Authentication Standard:** Bearer JWT (HTTP Authorization Header: `Bearer <token>`)

---

## 1. Overview of Changes

Following the Phase 1 & 2 safety hardening and unification:
1. **Model Support Boundary Enforcement:** Both diagnostic endpoints now enforce that machine learning inference is executed only for crops with trained models. Unserviced crops (e.g. Cotton, Tomato, Soybean, Onion) return **HTTP 400 Bad Request** with structured explanatory error payloads instead of simulated diagnoses.
2. **Confidence-Aware Safety Status:** Responses now include `advisory_status` (`HIGH_CONFIDENCE`, `LOW_CONFIDENCE_WARNING`, `UNCERTAIN_PREDICTION`, or `HEALTHY`).
3. **Honest Severity Policy:** Disease severity is reported as `UNAVAILABLE` or `UNVALIDATED` with `affected_area_percentage = null` unless genuinely estimated.
4. **Grad-CAM Parity:** Both standalone and authenticated routes support Grad-CAM generation via `generate_gradcam=true`. Authenticated routes persist the heatmap path in the database.
5. **Security Isolation:** Standalone inference cannot read or write private farmer data.

---

## 2. Diagnostic Endpoints Specification

### 2.1 Direct Model Inference Endpoint (Standalone)

* **Route:** `POST /api/v1/diagnose/predict`
* **Alias Route:** `POST /api/v1/diagnostics/predict`
* **Authentication:** **None** (Public, Ephemeral)
* **Summary:** Evaluates genuine PyTorch model inference, applies confidence-aware safety gating, and optionally generates a Grad-CAM lesion heatmap. Does NOT persist any data to the database.

#### Request Headers:
`Content-Type: multipart/form-data`

#### Form Parameters:
| Field | Type | Required | Default | Description |
| :--- | :---: | :---: | :---: | :--- |
| `file` | UploadFile | Yes | — | Crop leaf photograph (`.jpg`, `.jpeg`, `.png`, `.webp`, max 10 MB). |
| `crop` | string | No | `"sugarcane"` | Target crop identifier. Currently, only `"sugarcane"` is supported. |
| `generate_gradcam` | boolean | No | `false` | When `true`, executes Grad-CAM activation backpropagation. |
| `save_heatmap` | boolean | No | `true` | When `true`, persists the blended RGB activation heatmap to disk. |

#### Successful Response (`HTTP 200 OK`):
```json
{
  "crop": "sugarcane",
  "predicted_class": "RedRot",
  "confidence": 0.9124,
  "class_scores": {
    "Healthy": 0.0211,
    "Mosaic": 0.0315,
    "RedRot": 0.9124,
    "Rust": 0.0238,
    "Yellow": 0.0112
  },
  "model_version": "EfficientNet-B0-v1.0",
  "explanation_status": "generated",
  "heatmap_path": "uploads/heatmaps/cam_7a8f9b2c3d4e_redrot.jpg",
  "advisory_status": "HIGH_CONFIDENCE",
  "details": {
    "safety_evaluation": "HIGH_CONFIDENCE",
    "disease_name_en": "Red Rot (Colletotrichum falcatum)",
    "disease_name_mr": "ऊसावरील तांबडे कूज / लाल सड",
    "pathogen_type": "Fungal (Colletotrichum falcatum)",
    "severity": "UNAVAILABLE",
    "affected_area_percentage": null,
    "recommendations_en": "[Agricultural Expert Verification Required: Confirm foliar symptoms with a certified Taluka Agricultural Officer or local KVK agronomist prior to chemical procurement or field spraying.]\n\n• Cultural Management: Eradicate and burn affected clumps immediately. Practice 2-3 year crop rotation...\n• Chemical Measures (ICAR-SBI): Treat seed setts prior to planting with Carbendazim 50% WP @ 1g/L...\n\nAdvisory Notice: Pesticide dosages and cultural treatments are based on standard ICAR/CIBRC agricultural packages...",
    "recommendations_mr": "[कृषी तज्ज्ञ पडताळणी आवश्यक: रासायनिक औषधे खरेदी करण्यापूर्वी स्थानिक कृषी सहाय्यक किंवा कृषी विज्ञान केंद्रातील (KVK) शास्त्रज्ञांकडून प्रत्यक्ष पानांची खात्री करून घेणे बंधनकारक आहे.]\n\n• मशागतीय व प्रतिबंधात्मक उपाय: बाधित उसाची बेटे मुळासकट उपटून जाळून टाका...\n• रासायनिक उपाययोजना: लागवडीपूर्वी बेणे प्रक्रियेसाठी कार्बेन्डाझिम ५०% डब्ल्यूपी १ ग्रॅम/लीटर...",
    "statutory_disclaimer": "Advisory Notice: Pesticide dosages and cultural treatments are based on standard ICAR/CIBRC agricultural packages..."
  }
}
```

#### Error Responses:
* `HTTP 400 Bad Request` (Unsupported Crop):
  ```json
  {
    "detail": "AI diagnosis is currently unavailable for crop 'Cotton'. Model inference is currently only supported for: sugarcane. Model currently only serves sugarcane crop pathology. Received: 'Cotton'."
  }
  ```
* `HTTP 400 Bad Request` (Corrupted File or Invalid Format):
  ```json
  {
    "detail": "File content header does not match a valid image format (JPEG, PNG, WEBP)."
  }
  ```
* `HTTP 413 Payload Too Large`:
  ```json
  {
    "detail": "File exceeds maximum allowed size of 10MB."
  }
  ```
* `HTTP 503 Service Unavailable`:
  ```json
  {
    "detail": "Model serving error: Diagnostic model is currently unavailable."
  }
  ```

---

### 2.2 Authenticated Crop Diagnosis Submission Endpoint

* **Route:** `POST /api/v1/crops/{crop_id}/diagnoses`
* **Authentication:** **Bearer JWT Required**
* **Summary:** Submits a crop foliage image for an authenticated farmer's crop cycle. Verifies ownership, validates image integrity, executes genuine model inference with confidence gating, optionally generates Grad-CAM, and persists the diagnostic record to the database.

#### Request Headers:
```
Authorization: Bearer <jwt_access_token>
Content-Type: multipart/form-data
```

#### Path Parameters:
* `crop_id` (integer, required): Unique identifier of the target `CropCycle`.

#### Form Parameters:
| Field | Type | Required | Default | Description |
| :--- | :---: | :---: | :---: | :--- |
| `file` | UploadFile | Yes | — | Crop foliage image (`.jpg`, `.jpeg`, `.png`, `.webp`, max 10 MB). |
| `notes` | string | No | `null` | Farmer's field observations. |
| `temperature` | float | No | `null` | Ambient temperature in °C. |
| `humidity` | float | No | `null` | Relative humidity percentage (0–100%). |
| `soil_moisture` | float | No | `null` | Soil moisture percentage (0–100%). |
| `generate_gradcam` | boolean | No | `false` | When `true`, computes and persists Grad-CAM activation heatmap. |

#### Successful Response (`HTTP 201 Created`):
```json
{
  "id": 42,
  "user_id": 1,
  "crop_cycle_id": 5,
  "crop_name": "Sugarcane",
  "image_path": "diagnostics/2026-10/4a7f92b18c0e41239ab7cd45e6f1234a.jpg",
  "image_filename": "field_leaf.jpg",
  "image_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "heatmap_path": "uploads/heatmaps/cam_7a8f9b2c3d4e_redrot.jpg",
  "disease_name_en": "Red Rot (Colletotrichum falcatum)",
  "disease_name_mr": "ऊसावरील तांबडे कूज / लाल सड",
  "pathogen_type": "Fungal (Colletotrichum falcatum)",
  "confidence": 0.9124,
  "severity": "UNAVAILABLE",
  "affected_area_percentage": null,
  "advisory_status": "HIGH_CONFIDENCE",
  "symptoms_en": "Red discoloration of internal vascular bundles with transverse white patches...",
  "symptoms_mr": "पानाच्या मधल्या शिरेवर लालसर लांबट ठिपके आणि उसाच्या कांडीच्या आत लाल रंग...",
  "recommendations_en": "[Agricultural Expert Verification Required: Confirm foliar symptoms with a certified Taluka Agricultural Officer or local KVK agronomist prior to chemical procurement or field spraying.]\n\n• Cultural Management: Eradicate and burn affected clumps immediately...\n• Chemical Measures (ICAR-SBI): Treat seed setts prior to planting with Carbendazim 50% WP @ 1g/L...\n\nAdvisory Notice: Pesticide dosages and cultural treatments are based on standard ICAR/CIBRC agricultural packages...",
  "recommendations_mr": "[कृषी तज्ज्ञ पडताळणी आवश्यक: रासायनिक औषधे खरेदी करण्यापूर्वी स्थानिक कृषी सहाय्यक किंवा कृषी विज्ञान केंद्रातील (KVK) शास्त्रज्ञांकडून प्रत्यक्ष पानांची खात्री करून घेणे बंधनकारक आहे.]\n\n• मशागतीय व प्रतिबंधात्मक उपाय: बाधित उसाची बेटे मुळासकट उपटून जाळून टाका...\n• रासायनिक उपाययोजना: लागवडीपूर्वी बेणे प्रक्रियेसाठी कार्बेन्डाझिम ५०% डब्ल्यूपी १ ग्रॅम/लीटर...",
  "temperature": 29.5,
  "humidity": 82.0,
  "soil_moisture": 45.0,
  "status": "COMPLETED",
  "notes": "Spotted on lower leaves after rain",
  "created_at": "2026-10-25T15:30:00Z",
  "updated_at": "2026-10-25T15:30:00Z"
}
```

#### Moderate Confidence Response Example (`50% <= Confidence < 75%`):
```json
{
  "disease_name_en": "Provisional: Red Rot (Colletotrichum falcatum)",
  "confidence": 0.6215,
  "severity": "UNAVAILABLE",
  "affected_area_percentage": null,
  "advisory_status": "LOW_CONFIDENCE_WARNING",
  "recommendations_en": "CHEMICAL PRESCRIPTION SUPPRESSED DUE TO DIAGNOSTIC UNCERTAINTY (Model confidence 62.2% is below the safe threshold of 75%).\n\nAutomated chemical recommendations are withheld to prevent misdiagnosis, crop injury, and unnecessary expense.\n\nRecommended Next Steps:\n1. Cultural Inspection: Eradicate and burn affected clumps immediately...\n2. Retake Photograph: Capture a well-lit, sharp close-up photo of symptomatic leaves in natural indirect daylight.\n3. Expert Consultation: Take a fresh leaf sample to your nearest Krishi Vigyan Kendra (KVK)...",
  "recommendations_mr": "निदानाच्या अनिश्चिततेमुळे रासायनिक औषध शिफारस तात्पुरती स्थगित करण्यात आली आहे (मॉडेल विश्वासार्हता ६२.२% ही सुरक्षित मर्यादेपेक्षा कमी आहे (७५%))...\n१. मशागतीय दक्षता...\n२. नवीन फोटो घ्या...\n३. तज्ज्ञ सल्ला..."
}
```

#### Low Confidence Response Example (`Confidence < 50%`):
```json
{
  "disease_name_en": "Uncertain Foliar Symptoms",
  "disease_name_mr": "अस्पष्ट पानांवरील लक्षणे",
  "pathogen_type": "Indeterminate",
  "confidence": 0.3842,
  "severity": "UNAVAILABLE",
  "affected_area_percentage": null,
  "advisory_status": "UNCERTAIN_PREDICTION",
  "symptoms_en": "Image analysis is inconclusive (Highest class probability: 38.4%). The model cannot reliably distinguish whether the symptoms stem from biotic infection, nutritional deficiency, insect feeding, or environmental stress.",
  "recommendations_en": "DIAGNOSIS UNCERTAIN — CHEMICAL PRESCRIPTION WITHHELD.\n\nThe image provided does not show distinct pathological features with sufficient probabilistic confidence. Do NOT apply chemical pesticides based on this automated scan...",
  "recommendations_mr": "निदान अत्यंत अनिश्चित — रासायनिक औषध सल्ला रोखण्यात आला आहे..."
}
```

#### Error Responses:
* `HTTP 400 Bad Request` (Unsupported Crop on CropCycle):
  ```json
  {
    "detail": "AI diagnosis is currently unavailable for crop 'Cotton'. Model inference is currently only supported for: sugarcane. Model currently only serves sugarcane crop pathology. Received: 'Cotton'."
  }
  ```
* `HTTP 401 Unauthorized`: Missing, expired, or invalid JWT token.
* `HTTP 403 Forbidden`: Authenticated user does not own the farm associated with `crop_id`.
* `HTTP 404 Not Found`: `crop_id` does not exist in the database.
* `HTTP 413 Payload Too Large`: Uploaded file exceeds 10 MB.

---

### 2.3 Additional Diagnostic Endpoints Inventory

| Method | Endpoint | Auth | Purpose | Response Model |
| :---: | :--- | :---: | :--- | :--- |
| `GET` | `/api/v1/crops/{crop_id}/diagnoses` | Bearer JWT | List historical diagnoses for a crop cycle | `List[DiagnosisSummaryResponse]` |
| `GET` | `/api/v1/diagnostics` | Bearer JWT | List all diagnoses submitted by authenticated farmer | `List[DiagnosisSummaryResponse]` |
| `GET` | `/api/v1/diagnostics/{diagnosis_id}` | Bearer JWT | Retrieve full diagnostic report by ID (Owner protected) | `DiagnosisDetailResponse` |
| `DELETE`| `/api/v1/diagnostics/{diagnosis_id}` | Bearer JWT | Delete diagnostic record and delete image file from disk | `HTTP 204 No Content` |
