# PikVaidya AI — REST API Documentation

**Document Version:** 3.0.0  
**Base URL:** `http://localhost:8000` (Local) / `https://api.pikvaidya.ai` (Production)  
**Authentication:** Ephemeral / Unauthenticated diagnostic endpoints; Bearer JWT for farmer profile management.  
**Rate Limiting:** 30 requests/minute per IP address on diagnostic endpoints.

---

## 1. Unified Multi-Crop Health Prediction Endpoint

### `POST /api/crop-health/predict`
*(Also available under the versioned alias: `POST /api/v1/crop-health/predict`)*

Integrates automated crop identification, deep learning vision pathology, 14-day microclimate telemetry, physiological stress evaluation, and calibrated Bayesian evidence fusion into a single forward pass.

#### Request Headers
```http
Content-Type: multipart/form-data
Accept: application/json
```

#### Request Parameters (Multipart Form-Data)

| Field Name | Type | Required | Default | Description |
| :--- | :---: | :---: | :---: | :--- |
| `file` | File (Binary) | **Yes** | — | Crop foliage photograph. Allowed MIME: `image/jpeg`, `image/png`, `image/webp`. Max size: 10MB. |
| `crop_type` | String | No | `"auto"` | Target crop: `sugarcane`, `tomato`, `onion`, or `auto` (auto-detects from foliage). |
| `crop` | String | No | — | Alias for `crop_type`. |
| `latitude` | Float | No | `null` | Farm latitude coordinate (e.g. `18.5204` for Pune). |
| `longitude` | Float | No | `null` | Farm longitude coordinate (e.g. `73.8567` for Pune). |
| `district` | String | No | `null` | Maharashtra district name (e.g. `Pune`, `Nashik`, `Kolhapur`, `Solapur`). |
| `crop_variety`| String | No | `null` | Cultivar / variety (e.g. `Co 86032`, `Abhinav`, `Bhima Kiran`). |
| `growth_stage`| String | No | `"unknown"`| Developmental stage: `germination`, `vegetative`, `tillering`, `flowering_fruiting`, `grand_growth`, `bulb_development`, `maturity`. |
| `soil_type` | String | No | `"unknown"`| Soil classification: `black_cotton`, `loamy`, `clay_loam`, `sandy_loam`, `red_soil`, `laterite`. |
| `irrigation_method` | String | No | `"unknown"` | `drip`, `sprinkler`, `flood_furrow`, `rainfed`. |
| `strategy` | String | No | `"CALIBRATED_BAYESIAN"` | Fusion method: `CALIBRATED_BAYESIAN` or `RULE_BASED_GATE`. |
| `generate_gradcam` | Boolean | No | `true` | Generates Grad-CAM visual lesion saliency overlay. |

---

#### Response Schema (`UnifiedCropHealthPredictResponse`)

```json
{
  "crop_type": "onion",
  "crop_detection_method": "auto_detected_classifier",
  "crop_detection_confidence": 0.9950,
  "predicted_disease": "Onion___purple_blotch",
  "disease_name_multilingual": {
    "en": "Purple Blotch (Alternaria porri)",
    "mr": "कांद्यावरील जांभळा करपा",
    "hi": "प्याज का बैंगनी धब्बा"
  },
  "model_confidence": 0.9892,
  "weather_summary": {
    "location": "Nashik",
    "temp_avg_7d": 26.4,
    "rainfall_7d_mm": 28.5,
    "humidity_avg_7d": 82.1,
    "high_humidity_hours_7d": 38,
    "soil_moisture_trend": "ACCUMULATING"
  },
  "environmental_risk": {
    "overall_disease_pressure": 0.85,
    "dominant_weather_risk": "Fungal Conduciveness: Purple Blotch",
    "spray_suitability": "GATED_UNFAVOURABLE",
    "is_safe_to_spray": false,
    "spray_guidance": {
      "en": "Foliar spraying restricted: Rain event forecasted within next 24 hours.",
      "mr": "फवारणी पुढे ढकला: पुढील २४ तासांत पावसाची शक्यता आहे.",
      "hi": "छिड़काव स्थगित रखें: 24 घंटे में बारिश का पूर्वानुमान है।"
    }
  },
  "combined_assessment": {
    "primary_diagnosis": "Onion___purple_blotch",
    "fused_confidence": 0.9892,
    "crop_health_index": 22.4,
    "health_status_label": "MODERATELY_INFECTED",
    "disease_progression_velocity": "RAPID",
    "is_environmentally_concordant": true,
    "anomaly_warning": null
  },
  "gradcam_image_url": "uploads/heatmaps/cam_f8a92b_onion_purple_blotch.jpg",
  "advisory_recommendations": {
    "actionable_advice": {
      "en": "Targeted therapeutic intervention recommended once rain clears.",
      "mr": "पाऊस थांबल्यानंतर योग्य बुरशीनाशकाची फवारणी करावी.",
      "hi": "बारिश रुकने के बाद अनुशंसित फफूंदनाशक का छिड़काव करें।"
    },
    "cultural_measures": [
      "Improve furrow drainage to prevent prolonged foliar wetness.",
      "Remove and incinerate severely blighted leaf tips."
    ],
    "chemical_measures": [
      {
        "chemical_name": "Mancozeb 75% WP",
        "dosage_per_acre": "600-800 g",
        "dilution_per_liter": "2.5 g/L",
        "phi_days": 15,
        "cibrc_status": "APPROVED"
      }
    ]
  },
  "data_source": "PikVaidya Multimodal v2.2.0 | open-meteo-historical",
  "timestamp": "2026-11-09T12:05:00Z"
}
```

---

## 2. Example Code Snippets

### Python (using `httpx` or `requests`)
```python
import requests

url = "http://localhost:8000/api/crop-health/predict"
files = {"file": open("field_onion_leaf.jpg", "rb")}
data = {
    "crop_type": "auto",       # Let PikVaidya AI auto-detect crop
    "district": "Nashik",
    "generate_gradcam": "true"
}

response = requests.post(url, files=files, data=data)
result = response.json()

print(f"Detected Crop: {result['crop_type']} ({result['crop_detection_method']})")
print(f"Diagnosis: {result['disease_name_multilingual']['en']}")
print(f"Confidence: {result['model_confidence'] * 100:.1f}%")
print(f"Spray Status: {result['environmental_risk']['spray_suitability']}")
```

### cURL
```bash
curl -X POST "http://localhost:8000/api/crop-health/predict" \
  -H "Accept: application/json" \
  -F "file=@sample_tomato_leaf.jpg" \
  -F "crop_type=auto" \
  -F "district=Pune" \
  -F "generate_gradcam=true"
```

---

## 3. HTTP Error Codes

| Status Code | Description | Resolution |
| :--- | :--- | :--- |
| `400 Bad Request` | Unsupported file type, empty file, or invalid crop name. | Ensure image is JPEG/PNG/WEBP under 10MB and crop is sugarcane, tomato, onion, or auto. |
| `422 Unprocessable Entity`| Out-of-Distribution foliage check failed (e.g. non-leaf image uploaded). | Ensure photo contains clear green crop foliage covering $\ge 15\%$ of frame. |
| `429 Too Many Requests` | Rate limit exceeded (>30 req/min). | Wait 60 seconds before submitting subsequent requests. |
| `500 Internal Error` | Forward pass or Grad-CAM computation failure. | Check server logs; verify model checkpoint file integrity. |

