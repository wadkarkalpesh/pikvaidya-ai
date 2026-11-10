# PikVaidya AI — Offline Progressive Web App (PWA) Architecture

## 1. Executive Summary

In rural agricultural zones across Maharashtra (e.g., Sangli, Solapur, Ahmednagar, Kolhapur, and Marathwada), cellular connectivity is frequently intermittent or unavailable. **PikVaidya AI Phase 8** transitions the platform from a cloud-reliant web application to a fully offline-first Progressive Web App (PWA).

The offline architecture combines:
1. **W3C Progressive Web App Standards**: Installable standalone application, production Service Worker, and App Shell precaching.
2. **W3C IndexedDB Storage Engine**: Persistent relational-like client storage for historical diagnoses, farm metadata, verified ICAR/CIBRC advisories, and an idempotent upload queue.
3. **Client-Side Edge AI (ONNX Runtime Web + WASM)**: Instantaneous, zero-internet leaf pathology classification using quantized INT8 MobileNetV3 neural networks executing directly on device CPU threads.
4. **Resilient Background Synchronization**: Automatic, exponential-backoff synchronization protocol that guarantees zero data loss when transitioning from offline to online states.

---

## 2. System Architecture Diagram

```mermaid
graph TD
    User([Farmer / Field Extension Worker]) --> UI[PikVaidya PWA Shell]
    
    subgraph Client Device Browser
        UI --> NetworkCheck{Network Online?}
        
        %% Offline Path
        NetworkCheck -- "No (Offline)" --> EdgeEngine[ONNX Runtime Web (WASM SIMD)]
        EdgeEngine --> ModelCache[(CacheStorage: INT8 Models)]
        EdgeEngine --> LocalInference[Classify Pathology in 2-3ms]
        LocalInference --> IDB_Diag[(IndexedDB: diagnosis_history)]
        LocalInference --> IDB_Queue[(IndexedDB: sync_queue)]
        IDB_Advisory[(IndexedDB: advisory_cards)] --> LocalInference
        
        %% Online Path
        NetworkCheck -- "Yes (Online)" --> CloudAPI[FastAPI /api/crop-health/predict]
        CloudAPI --> PyTorchGPU[PyTorch Multimodal Engine + Grad-CAM]
        PyTorchGPU --> WeatherAPI[Open-Meteo & IMD Telemetry]
        PyTorchGPU --> PDFGen[Official Advisory PDF]
        
        %% Background Sync
        SyncMgr[Background Sync Manager] --> IDB_Queue
        SyncMgr -- "Flush Queued Scans" --> CloudAPI
        CloudAPI -- "Enriched Results + Grad-CAM" --> IDB_Diag
    end
```

---

## 3. Progressive Web App Lifecycle & Service Worker

### 3.1 Service Worker Configuration
The PWA service worker is generated via `vite-plugin-pwa` and Workbox, operating with an `autoUpdate` strategy.

### 3.2 Caching Strategies by Asset Class

| Asset Class | Caching Strategy | Storage Mechanism | Expiration / Max Age |
| :--- | :--- | :--- | :--- |
| **App Shell (HTML, JS, CSS)** | Precache on install | Workbox Precache Cache | Controlled by build hash |
| **ONNX Models (`.onnx`)** | `CacheFirst` | CacheStorage (`pikvaidya-models-wasm-cache`) | 60 Days (35 MB limit) |
| **WASM Binaries (`.wasm`)** | `CacheFirst` | CacheStorage (`pikvaidya-models-wasm-cache`) | 60 Days |
| **Agricultural Knowledge API** | `StaleWhileRevalidate` | CacheStorage (`agricultural-knowledge-cache`) | 7 Days (max 50 entries) |
| **Microclimate Locations API** | `CacheFirst` | CacheStorage (`weather-locations-cache`) | 30 Days (max 10 entries) |
| **Diagnostic Submissions** | `NetworkOnly` with Queue Fallback | IndexedDB (`sync_queue`) | Infinite until synced |

---

## 4. Edge AI Execution Pipeline

1. **Input Acquisition**: Leaf photo taken from mobile camera or file input.
2. **Preprocessing**: 
   - Rendered onto offscreen canvas with bilinear interpolation to $224 \times 224$ pixels.
   - Pixels extracted in RGB planar order: shape $[1, 3, 224, 224]$.
   - ImageNet normalization:
     $$\hat{x}_{c} = \frac{x_c / 255.0 - \mu_c}{\sigma_c}$$
     where $\mu = [0.485, 0.456, 0.406]$ and $\sigma = [0.229, 0.224, 0.225]$.
3. **Execution Provider**: WebAssembly (WASM) with SIMD vectorization and multi-threading (up to 4 CPU cores via `navigator.hardwareConcurrency`).
4. **Softmax Probability Calibration**:
   $$P(y = c) = \frac{\exp(z_c - \max(z))}{\sum_{j} \exp(z_j - \max(z))}$$
5. **Offline Action**: Immediate diagnosis presented to farmer in Marathi/Hindi/English within 3ms.

---

## 5. Security & Data Integrity

- **Idempotency Keys**: Every queued capture receives an immutable UUID v4 `idempotency_key` preventing duplicate submissions when recovering from interrupted mobile network handshakes.
- **Quota Error Handling**: IndexedDB transactions catch `QuotaExceededError` gracefully and warn the user before dropping or corrupting existing scans.
- **JSON Backup Export**: Full single-click export of all local databases enables extension workers to migrate farm historical records to external storage or cloud systems.
