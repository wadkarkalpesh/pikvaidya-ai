# PikVaidya AI — Complete Backend API Inventory

**Document Version:** 2.0  
**Status:** Production Standard  
**Base URL:** `http://127.0.0.1:8000` (Local) / `https://api.pikvaidya.in` (Production)  
**API Prefix:** `/api/v1`  
**Total Paths:** 55  
**Total Operations:** 64 HTTP Operations across 18 Route Categories  

---

## 1. Authentication & Security Scope Overview

PikVaidya AI employs JSON Web Tokens (JWT) signed with HMAC-SHA256. Protected endpoints require the header:
```http
Authorization: Bearer <access_token>
```
Endpoints are tagged with three security scopes:
- `Public`: Unauthenticated access (registration, login, open model inference, weather lookups).
- `Bearer JWT (Farmer)`: Authenticated farmer access to personal farms, crops, history, and notifications.
- `Bearer JWT (Expert / Admin)`: Elevated access for agricultural specialists and system telemetry auditors.

---

## 2. Complete Endpoint Inventory Table

| Category | Method | Endpoint Path | Summary / Purpose | Auth Scope | Key Parameters / Request Body | Response Model / Output |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Authentication** | `POST` | `/api/v1/auth/register` | Register new farmer account | Public | `name`, `email`, `password`, `preferred_language` | `UserResponse` (`id`, `email`, `role`) |
| **Authentication** | `POST` | `/api/v1/auth/login` | Authenticate farmer / expert | Public | Form: `username` (email), `password` | `Token` (`access_token`, `token_type`) |
| **Authentication** | `GET` | `/api/v1/auth/me` | Read active user session | Farmer / Admin | None (Bearer Token) | `UserResponse` with full profile |
| **Farmer Profile** | `GET` | `/api/v1/farmer/profile` | Retrieve farmer account metadata | Farmer | None | `FarmerProfileResponse` |
| **Farmer Profile** | `PUT` | `/api/v1/farmer/profile` | Update phone or language | Farmer | `name`, `phone_number`, `preferred_language` | Updated `FarmerProfileResponse` |
| **Farm Management** | `GET` | `/api/v1/farms` | List all farm parcels owned by farmer | Farmer | Query: `skip`, `limit` | `List[FarmResponse]` |
| **Farm Management** | `POST` | `/api/v1/farms` | Register new cadastral farm plot | Farmer | `name`, `area`, `soil_type`, `irrigation`, `lat`, `lon` | `FarmResponse` (`id`, acreage, GPS) |
| **Farm Management** | `GET` | `/api/v1/farms/{farm_id}` | Get farm parcel specifications | Farmer | Path: `farm_id` | `FarmResponse` |
| **Farm Management** | `PUT` | `/api/v1/farms/{farm_id}` | Update farm boundary / irrigation | Farmer | Path: `farm_id`, Body: `FarmUpdate` | Updated `FarmResponse` |
| **Farm Management** | `DELETE`| `/api/v1/farms/{farm_id}` | Remove farm parcel | Farmer | Path: `farm_id` | Status 204 No Content |
| **Crop-Cycle** | `GET` | `/api/v1/farms/{farm_id}/crops` | List crop cycles for farm | Farmer | Path: `farm_id` | `List[CropCycleResponse]` |
| **Crop-Cycle** | `POST` | `/api/v1/farms/{farm_id}/crops` | Register new crop cycle | Farmer | `crop`, `variety`, `sowing_date`, `growth_stage` | `CropCycleResponse` |
| **Crop-Cycle** | `GET` | `/api/v1/crops/{crop_id}` | Get crop cycle details | Farmer | Path: `crop_id` | `CropCycleResponse` |
| **Crop-Cycle** | `PUT` | `/api/v1/crops/{crop_id}` | Update crop growth stage | Farmer | Path: `crop_id`, Body: `CropCycleUpdate` | Updated `CropCycleResponse` |
| **Crop-Cycle** | `DELETE`| `/api/v1/crops/{crop_id}` | Terminate crop cycle | Farmer | Path: `crop_id` | Status 204 No Content |
| **AI Models** | `GET` | `/api/v1/models` | List all deployed AI models & specs | Public | None | `ModelCatalogResponse` (4 models) |
| **AI Models** | `GET` | `/api/v1/models/{crop}` | Crop-specific model metadata & weights | Public | Path: `crop` (sugarcane, tomato, onion) | `ModelMetadataResponse` |
| **Crop Diagnostics**| `POST` | `/api/v1/diagnose/predict` | Standalone unauthenticated foliar diagnosis | Public | Multipart: `file` (image), `crop`, `generate_gradcam` | `PredictionResponse` |
| **Crop Diagnostics**| `POST` | `/api/v1/crops/{crop_id}/diagnoses` | Authenticated crop diagnosis + DB storage | Farmer | Multipart: `file`, `generate_gradcam`, `notes` | `DiagnosisResponse` (ID, Class, Heatmap) |
| **Crop Diagnostics**| `GET` | `/api/v1/crops/{crop_id}/diagnoses` | List historical diagnoses for crop | Farmer | Path: `crop_id` | `List[DiagnosisResponse]` |
| **Crop Diagnostics**| `GET` | `/api/v1/diagnostics` | List all historical diagnoses for farmer | Farmer | Query: `skip`, `limit` | `List[DiagnosisResponse]` |
| **Crop Diagnostics**| `GET` | `/api/v1/diagnostics/{diagnosis_id}` | Detailed diagnosis record | Farmer | Path: `diagnosis_id` | `DiagnosisDetailResponse` |
| **Crop Diagnostics**| `DELETE`| `/api/v1/diagnostics/{diagnosis_id}` | Purge diagnosis & image artifact | Farmer | Path: `diagnosis_id` | Status 204 No Content |
| **Crop Diagnostics**| `GET` | `/api/v1/diagnose/{diagnosis_id}/pdf` | Download official field PDF certificate | Farmer | Path: `diagnosis_id` | `application/pdf` binary stream |
| **Multimodal Fusion**| `POST` | `/api/v1/multimodal/predict` | Bayesian multimodal foliar + weather diagnosis | Public | Multipart: `file`, `crop`, `district`, `growth_stage` | `MultimodalPredictionResponse` |
| **Multimodal Fusion**| `POST` | `/api/v1/multimodal/weather-risk` | Standalone microclimate risk evaluation | Public | `crop`, `district`, `growth_stage` | `WeatherRiskResponse` |
| **Multimodal Fusion**| `GET` | `/api/v1/multimodal/crops` | List supported crops & growth stages | Public | None | Supported crops list |
| **Unified Crop Health**| `POST` | `/api/v1/crop-health/predict` | Unified multi-crop health gateway | Public | Multipart: `file`, `crop_type` | `UnifiedPredictionResponse` |
| **Unified Crop Health**| `POST` | `/api/crop-health/predict` | Unversioned alias for frontend parity | Public | Multipart: `file`, `crop_type` | `UnifiedPredictionResponse` |
| **Weather Telemetry**| `GET` | `/api/v1/weather/current` | Real-time weather for coordinates | Public | Query: `latitude`, `longitude`, `district` | `CurrentWeatherResponse` |
| **Weather Telemetry**| `GET` | `/api/v1/weather/forecast` | 7-day agricultural weather forecast | Public | Query: `latitude`, `longitude`, `district` | `ForecastWeatherResponse` |
| **Weather Telemetry**| `GET` | `/api/v1/weather/historical` | Past 14-day rainfall and temperature | Public | Query: `latitude`, `longitude`, `days` | `HistoricalWeatherResponse` |
| **Weather Telemetry**| `GET` | `/api/v1/weather/district/{district_name}` | District weather summary | Public | Path: `district_name` | `DistrictWeatherResponse` |
| **Weather Telemetry**| `GET` | `/api/v1/weather/locations` | List pre-configured Maharashtra districts | Public | None | `List[DistrictLocation]` |
| **Weather Telemetry**| `GET` | `/api/v1/weather/alerts` | Active meteorological warnings | Public | Query: `district` | `List[WeatherAlert]` |
| **Environmental Risk**| `POST` | `/api/v1/risk/environmental` | Assess microclimate disease conduciveness | Public | `crop`, `district`, `latitude`, `longitude` | `EnvironmentalRiskResponse` |
| **Environmental Risk**| `GET` | `/api/v1/risk/districts` | List monitored Western Maharashtra districts | Public | None | List of monitored districts |
| **Advisory Engine** | `POST` | `/api/v1/advisory/generate` | Generate CIBRC-compliant spray advisory | Public | `crop`, `disease_name`, `language`, `weather` | `AdvisoryResponse` |
| **Advisory Engine** | `POST` | `/api/v1/advisory/pdf` | Generate standalone advisory PDF | Public | `AdvisoryGenerateRequest` | `application/pdf` binary stream |
| **Advisory Engine** | `GET` | `/api/v1/advisory/weather` | Retrieve spray window safety window | Public | Query: `latitude`, `longitude` | `SprayWindowResponse` |
| **RAG Assistant** | `POST` | `/api/v1/assistant/chat` | Multi-turn RAG chat with conversation memory | Public | `message`, `session_id`, `crop`, `language` | `ChatQueryResponse` |
| **RAG Assistant** | `POST` | `/api/v1/assistant/query` | Single-turn RAG retrieval and answer | Public | `message`, `crop`, `language` | `ChatQueryResponse` |
| **RAG Assistant** | `GET` | `/api/v1/assistant/chunks` | Inspect indexed knowledge chunks | Public | Query: `skip`, `limit` | `List[KnowledgeChunkResponse]` |
| **Disease Knowledge**| `GET` | `/api/v1/diseases` | Browse complete disease catalog | Public | Query: `skip`, `limit` | `List[DiseaseResponse]` |
| **Disease Knowledge**| `GET` | `/api/v1/diseases/{disease_id}` | Detailed disease symptoms & biology | Public | Path: `disease_id` | `DiseaseResponse` |
| **Disease Knowledge**| `GET` | `/api/v1/diseases/crop/{crop_name}` | List diseases for specific crop | Public | Path: `crop_name` | `List[DiseaseResponse]` |
| **Disease Knowledge**| `GET` | `/api/v1/diseases/search` | Search pathology terms | Public | Query: `q` | `List[DiseaseResponse]` |
| **Disease Knowledge**| `GET` | `/api/v1/diseases/{disease_id}/rag` | RAG-ready markdown disease representation | Public | Path: `disease_id` | Markdown text string |
| **Notifications** | `GET` | `/api/v1/notifications` | List user in-app notifications | Farmer | Query: `unread_only` | `List[NotificationResponse]` |
| **Notifications** | `GET` | `/api/v1/notifications/unread-count` | Retrieve unread badge count | Farmer | None | `{"unread_count": int}` |
| **Notifications** | `POST` | `/api/v1/notifications/{id}/read` | Mark alert as acknowledged | Farmer | Path: `id` | Updated `NotificationResponse` |
| **Notifications** | `POST` | `/api/v1/notifications/create` | Dispatch system alert | Admin | `user_id`, `title`, `message`, `severity` | Created `NotificationResponse` |
| **Expert Review** | `POST` | `/api/v1/experts/request-review` | Request agronomist second opinion | Farmer | `diagnosis_id`, `farmer_notes` | `ExpertReviewResponse` (`PENDING`) |
| **Expert Review** | `GET` | `/api/v1/experts/pending-reviews` | Review queue for agronomists | Expert / Admin | Query: `skip`, `limit` | `List[ExpertReviewDetailResponse]` |
| **Expert Review** | `POST` | `/api/v1/experts/reviews/{id}/submit` | Agronomist diagnosis confirmation / override | Expert / Admin | Path: `id`, Body: `confirmed_disease`, `notes` | `ExpertReviewResponse` (`REVIEWED`) |
| **System Admin** | `GET` | `/api/v1/admin/telemetry` | Process CPU, RAM, and model status | Admin | None | `TelemetryResponse` |
| **System Admin** | `GET` | `/api/v1/admin/summary` | Aggregate platform entity counts | Admin | None | `AdminSummaryResponse` |
| **System Admin** | `GET` | `/api/v1/admin/audit-logs` | Query security & sync audit logs | Admin | Query: `skip`, `limit` | `List[AuditLogResponse]` |
| **System Admin** | `GET` | `/api/v1/admin/users` | List platform user directory | Admin | Query: `skip`, `limit` | `List[UserResponse]` |
| **Offline Sync** | `POST` | `/api/v1/sync/push` | Push offline captured diagnoses & records | Farmer | `client_timestamp`, `diagnoses`, `farms` | `SyncPushResponse` |
| **Offline Sync** | `GET` | `/api/v1/sync/pull` | Pull delta updates & catalog hashes | Farmer | Query: `since` | `SyncPullResponse` |
| **System Health** | `GET` | `/api/v1/health` | Versioned service health check | Public | None | `{"status": "healthy"}` |
| **System Health** | `GET` | `/health` | Root unversioned health probe | Public | None | `{"status": "healthy"}` |
| **Root UI** | `GET` | `/` | Application index / PWA bootstrap | Public | None | PWA HTML or JSON root |
