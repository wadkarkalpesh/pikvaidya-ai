# PikVaidya AI — IndexedDB Database Schema Specification

## 1. Database Identification

- **Database Name**: `pikvaidya_offline_db`
- **Schema Version**: `2`
- **Engine**: W3C Indexed Database API (IndexedDB)
- **Primary Consumers**: `frontend/src/offline/db.js`, `frontend/src/offline/syncManager.js`, `frontend/src/offline/edgeInference.js`

---

## 2. Object Stores Specification

### 2.1 Store: `diagnosis_history`
Stores complete diagnostic scans, predictions, confidence metrics, and links to visual artifacts.

- **Primary Key (`keyPath`)**: `diagnosis_id` (String)
- **Indexes**:
  - `by_crop` on `crop_type` (unique: false)
  - `by_date` on `diagnosis_timestamp` (unique: false)
  - `by_sync_status` on `sync_status` (unique: false)

#### Field Definitions:
| Field | Type | Description |
| :--- | :--- | :--- |
| `diagnosis_id` | `string` | Unique record ID (e.g. `diag_1731245678_ab3f1`) |
| `crop_type` | `string` | Crop name (`sugarcane`, `tomato`, `onion`) |
| `predicted_disease`| `string` | Classified condition (e.g. `Purple Blotch`, `Healthy`) |
| `confidence` | `number` | Calibrated model probability $[0.0, 1.0]$ |
| `image_reference` | `string` | Base64 Data URL or persistent blob storage reference |
| `gradcam_reference`| `string \| null`| Path or Data URL of Grad-CAM overlay (null for edge inference) |
| `latitude` | `number \| null`| WGS84 latitude coordinate |
| `longitude` | `number \| null`| WGS84 longitude coordinate |
| `diagnosis_timestamp`| `string` | ISO 8601 creation timestamp |
| `sync_status` | `string` | `'synced'` \| `'pending_sync'` \| `'local_only'` |
| `is_local_inference`| `boolean`| `true` if diagnosed on-device; `false` if cloud PyTorch |
| `recommendations` | `Array<string>`| Actionable cultural and sanitation advisories |
| `weather_risk_assessment`| `object \| null`| Microclimate epidemiological risk evaluation |
| `risk_level` | `string` | Overall foliar risk (`LOW`, `MODERATE`, `HIGH`) |

---

### 2.2 Store: `farm_information`
Maintains agricultural plot records, farmer profiles, and growth stage metrics.

- **Primary Key (`keyPath`)**: `farm_id` (String)
- **Indexes**:
  - `by_farmer` on `farmer_id` (unique: false)
  - `by_crop` on `crop_type` (unique: false)

#### Field Definitions:
| Field | Type | Description |
| :--- | :--- | :--- |
| `farm_id` | `string` | Unique farm plot identifier |
| `farmer_id` | `string` | Farmer registration identifier |
| `farm_name` | `string` | Name of the farm plot (e.g. "Sangli Sugarcane Field 1") |
| `latitude` | `number` | Farm centroid latitude |
| `longitude` | `number` | Farm centroid longitude |
| `crop_type` | `string` | Cultivated crop (`sugarcane`, `tomato`, `onion`) |
| `crop_growth_stage`| `string` | Growth stage (`Germination`, `Vegetative`, `Flowering`, `Maturity`) |
| `updated_at` | `string` | ISO 8601 last modification timestamp |

---

### 2.3 Store: `advisory_cards`
Caches verified ICAR, VNMKV, MPKV, and CIBRC chemical prescriptions and cultural practices.

- **Primary Key (`keyPath`)**: `advisory_id` (String)
- **Indexes**:
  - `by_crop` on `crop_type` (unique: false)
  - `by_disease` on `disease` (unique: false)
  - `by_language` on `language` (unique: false)

#### Field Definitions:
| Field | Type | Description |
| :--- | :--- | :--- |
| `advisory_id` | `string` | Unique advisory identifier |
| `crop_type` | `string` | Target crop (`sugarcane`, `tomato`, `onion`, `all`) |
| `disease` | `string` | Pathology title (e.g. `Red Rot`, `Early Blight`) |
| `advisory_text` | `string` | Full textual management recommendation |
| `language` | `string` | ISO language code (`en`, `mr`, `hi`) |
| `source` | `string` | Accredited authority (`ICAR`, `VNMKV`, `MPKV Rahuri`, `CIBRC`) |
| `created_at` | `string` | ISO 8601 issuance timestamp |
| `expires_at` | `string` | ISO 8601 cache invalidation timestamp |

---

### 2.4 Store: `sync_queue`
Guarantees resilient, idempotent background synchronization for offline captures.

- **Primary Key (`keyPath`)**: `queue_id` (String)
- **Indexes**:
  - `by_status` on `sync_status` (unique: false)
  - `by_created_at` on `created_at` (unique: false)
  - `by_idempotency` on `idempotency_key` (unique: false)

#### Field Definitions:
| Field | Type | Description |
| :--- | :--- | :--- |
| `queue_id` | `string` | Unique queue item identifier |
| `operation_type` | `string` | Operation enum (`DIAGNOSIS_UPLOAD`, `FARM_UPDATE`, etc.) |
| `payload` | `object` | Image data, crop selection, coordinates, and preview |
| `created_at` | `string` | Capture timestamp |
| `retry_count` | `number` | Sequential failed attempt count (default `0`) |
| `sync_status` | `string` | `'pending'` \| `'syncing'` \| `'failed'` |
| `last_error` | `string \| null`| Error message from latest failed synchronization attempt |
| `idempotency_key`| `string` | UUID v4 string preventing duplicate server transactions |

---

## 3. Storage Quota & Error Management

- **Storage Estimation**: Monitored dynamically using `navigator.storage.estimate()`.
- **Warning Threshold**: Prompts the user if storage exceeds 80% of browser quota.
- **Quota Exceeded Recovery**: If a `QuotaExceededError` is thrown, the transaction rolls back cleanly without losing prior records.
- **Export / Backup JSON Format**:
  ```json
  {
    "exported_at": "2026-11-10T20:00:00.000Z",
    "version": 2,
    "stores": {
      "diagnosis_history": [...],
      "farm_information": [...],
      "advisory_cards": [...],
      "sync_queue": [...]
    }
  }
  ```

