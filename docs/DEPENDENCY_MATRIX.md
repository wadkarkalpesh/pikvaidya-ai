# PikVaidya AI — Master Dependency Matrix & Future Architectural Roadmap
**Document Version:** 1.0.0  
**Status:** Audited, Locked & Operational  
**Test Suite Verification:** 138 / 138 Passing (100% Green)  

---

## 1. Architectural Philosophy

PikVaidya AI maintains a **zero-uncontrolled-dependency** policy. Every library across the backend, machine learning pipeline, and client dashboard is:
1. **Explicitly version-pinned** or bounded by verified semantic version constraints.
2. **Audited for multi-platform compatibility** (Windows 11, Linux Ubuntu 22.04+, Docker Alpine/Debian).
3. **Pre-provisioned for future milestones** (edge quantization, offline service workers, PDF advisory generation) to prevent runtime breaks during expansion.

---

## 2. Python Ecosystem Matrix

All Python dependencies are synchronized across [`requirements.txt`](file:///E:/PikVaidya%20AI/requirements.txt), [`backend/requirements.txt`](file:///E:/PikVaidya%20AI/backend/requirements.txt), and [`Dockerfile`](file:///E:/PikVaidya%20AI/Dockerfile).

| Category | Package | Installed Version | Semantic Bound | Architectural Purpose |
| :--- | :--- | :---: | :---: | :--- |
| **Deep Learning** | `torch` | 2.14.1 | `>=2.1.0` | Deep neural network architectures (EfficientNet-B0, MobileNetV3-Large), autograd, feature extraction. |
| **Computer Vision** | `torchvision` | 0.29.1 | `>=0.16.0` | Backbone weights initialization, affine transforms, image preprocessing tensors. |
| **Image I/O** | `pillow` | 11.3.0 | `>=10.0.0` | Foliar image loading, color-space conversion (RGB to HSV/ExG), orientation check. |
| **Numerical Math** | `numpy` | 2.5.4 | `>=1.26.0` | Array operations, Grad-CAM activation weighting, foliar lesion mask calculations. |
| **Metrics & ML** | `scikit-learn` | 1.7.2 | `>=1.4.0` | Classification metrics (Macro F1, Precision, Recall), confusion matrices. |
| **Scientific Ops** | `scipy` | 1.16.2 | `>=1.11.0` | Scientific computing, probability density, temperature scaling optimization. |
| **Edge Inference** | `onnx` | 1.23.2 | `>=1.16.0` | Neural network graph serialization for edge and mobile deployments. |
| **Edge Runtime** | `onnxruntime`| 1.31.1 | `>=1.17.0` | High-throughput, low-latency CPU runtime for running quantized models without PyTorch overhead. |
| **Web Framework** | `fastapi` | 0.141.1 | `>=0.110.0` | High-performance asynchronous REST API, OpenAPI docs generation, route handlers. |
| **ASGI Server** | `uvicorn[standard]`| 0.48.0 | `>=0.28.0` | Production ASGI multi-worker HTTP server with uvloop and websockets. |
| **Data Validation** | `pydantic` | 2.14.2 | `>=2.6.0` | Request/response schema enforcement, strict type coercion. |
| **App Settings** | `pydantic-settings`| 2.15.0| `>=2.2.0` | 12-factor environment configuration, validation of secrets and CORS. |
| **Multipart Uploads**| `python-multipart`| 0.0.29 | `>=0.0.9` | Streaming multipart/form-data upload handling for leaf photos up to 10MB. |
| **Email Validation** | `email-validator` | 2.3.0 | `>=2.0.0` | Validates farmer and agronomist account registration emails. |
| **ORM & DB Core** | `sqlalchemy` | 2.0.50 | `>=2.0.28` | Relational database mapping, connection pooling, ACID transaction support. |
| **DB Migrations** | `alembic` | 1.20.1 | `>=1.13.1` | Automated database schema evolution and version control. |
| **PostgreSQL Driver**| `psycopg[binary]`| 3.3.6 | `>=3.1.18` | Modern psycopg3 driver for PostgreSQL 16 with native binary protocol support. |
| **JWT Tokens** | `pyjwt[crypto]` | 2.13.0 | `>=2.8.0` | Cryptographic JWT token generation and verification for farmer sessions. |
| **Password Hashing** | `bcrypt` | 5.0.0 | `>=4.1.2` | Blowfish cryptographic salted password hashing for tenant credentials. |
| **Env Loading** | `python-dotenv` | 1.2.3 | `>=1.0.1` | Local development `.env` loading and environment variable parsing. |
| **Rate Limiting** | `slowapi` / `limits`| 0.1.10 | `>=0.1.9` | In-memory sliding window rate limiting for public diagnostic endpoints. |
| **PDF Reporting** | `reportlab` | 4.4.4 | `>=4.1.0` | Generates downloadable agronomic diagnosis PDF prescription sheets. |
| **Config Formats** | `pyyaml` | 6.0.3 | `>=6.0.1` | Multi-crop dataset configurations and hyperparameter specifications. |
| **Test Framework** | `pytest` | 9.1.1 | `>=8.0.0` | Automated regression test execution, fixtures, parameterization. |
| **HTTP Test Client**| `httpx` | 0.28.1 | `>=0.27.0` | Async and sync HTTP client for API testing and external weather API calls. |

---

## 3. Frontend (Node.js & npm) Ecosystem Matrix

All frontend dependencies are synchronized in [`frontend/package.json`](file:///E:/PikVaidya%20AI/frontend/package.json) and compiled via [`frontend/vite.config.js`](file:///E:/PikVaidya%20AI/frontend/vite.config.js).

| Package | Version | Purpose |
| :--- | :---: | :--- |
| `react` | `^18.3.1` | Component lifecycle, declarative UI, state machine hooks (`useState`, `useEffect`, `useCallback`). |
| `react-dom` | `^18.3.1` | Virtual DOM reconciliation and browser rendering. |
| `lucide-react` | `^1.70.0` | Clean, accessible vector icons for agricultural metrics, weather statuses, cameras, and chat drawers. |
| `vite-plugin-pwa` | `^2.0.0` | Progressive Web App engine: service worker caching, offline asset precaching, `manifest.webmanifest`. |
| `vite` (dev) | `^6.0.7` | High-speed ESM development server with Hot Module Replacement (HMR) and Rollup production bundler. |
| `@vitejs/plugin-react` (dev) | `^4.3.4` | Babel-based Fast Refresh and JSX transformation. |

---

## 4. Built Artifacts & Verification

### A. Frontend Production Bundle (`frontend/dist/`)
- Compiled via `npm run build --prefix frontend`:
  - `dist/index.html` (1.14 kB)
  - `dist/assets/index-*.css` (9.51 kB)
  - `dist/assets/index-*.js` (163.17 kB)
  - `dist/sw.js` & `dist/workbox-*.js` (Service Worker offline precache)
  - `dist/manifest.webmanifest` (PWA installability for Android/iOS mobile browsers)

### B. Machine Learning Weights (`models/`)
- **Sugarcane (5 classes):**
  - EfficientNet-B0: `models/sugarcane/efficientnet_b0/pipeline_trained/best_model.pth` (19.7 MB)
  - MobileNetV3-Large: `models/sugarcane/mobilenet_v3/pipeline_trained/best_model.pth` (15.1 MB)
- **Tomato (10 classes):**
  - MobileNetV3-Large: `models/tomato/mobilenet_v3/best_model.pth` (16.3 MB, calibrated $T^* = 0.8350$)

---

## 5. Future Roadmap Pre-Provisioning Status

The installed dependencies provide full zero-install readiness for the upcoming roadmap stages:

1. **Multi-Crop Expansion (Onion, Cotton, Soybean):**
   - Fully supported by existing `torch`, `torchvision`, `scikit-learn`, and `pyyaml`.
2. **Quantized Mobile / Edge Deployment:**
   - Supported by `onnx` and `onnxruntime` for direct FP16 / INT8 quantization without PyTorch runtime dependencies.
3. **Offline Field Mode (PWA):**
   - Service workers and Web App Manifest generated and precached via `vite-plugin-pwa`.
4. **Downloadable Agronomic PDF Prescriptions:**
   - CIBRC chemical dosages, PPE warnings, and Grad-CAM image overlays ready for compilation via `reportlab`.
