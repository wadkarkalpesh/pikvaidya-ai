# PikVaidya AI — Multimodal Agricultural Dashboard & Client Application Guide
**System Stage:** Step 7 Implementation  
**Status:** Operational & Integrated  
**Verified Environments:** Windows 11 / Node.js 18+ / Python 3.10+ / FastAPI  

---

## 1. Architectural Overview

The **PikVaidya AI Client Dashboard** is a responsive, Indic-multilingual web application built with **React 18** and bundled with **Vite 6**. It bridges field-level diagnostic deep learning, explainable AI (Grad-CAM), real-time microclimate spray advisory, and multi-turn RAG farmer assistance into a single unified workspace.

```
+---------------------------------------------------------------------------------------+
|                                    Farmer / Agronomist                                |
+-------------------------------------------+-------------------------------------------+
                                            |
                                            v
+---------------------------------------------------------------------------------------+
|                                PikVaidya Frontend (React 18)                          |
|  - Language Switcher (EN / मराठी / हिंदी)      - Dual-Crop Selector (Sugarcane / Tomato) |
|  - Drag & Drop Foliar Upload                  - Real-Time Open-Meteo Microclimate     |
|  - Side-by-Side Grad-CAM Heatmap Visualizer   - CIBRC Statutory Advisory Panel        |
|  - Interactive RAG Assistant Floating Drawer  - Follow-up Chips & Session Memory      |
+-------------------------------------------+-------------------------------------------+
                                            | (REST APIs via Vite Proxy / Direct Mount)
                                            v
+---------------------------------------------------------------------------------------+
|                                   FastAPI Backend                                    |
|  - Static Mount: /dashboard, /assets, /uploads                                        |
|  - /api/v1/diagnose/predict: Dual-crop inference + Grad-CAM generation                |
|  - /api/v1/advisory/generate: Context-aware CIBRC chemical/organic recommendations   |
|  - /api/v1/weather/current: Open-Meteo microclimate fetch & spray window assessment  |
|  - /api/v1/assistant/chat: Hybrid BM25 + dense RAG with Devanagari subwords          |
+---------------------------------------------------------------------------------------+
```

---

## 2. Core Capabilities & Feature Modules

### A. Indic Localization (`src/i18n/translations.js`)
- Full native support for **English**, **Marathi (मराठी)**, and **Hindi (हिंदी)**.
- Covers all diagnostic labels, disease nomenclature, weather telemetry, chemical safety warnings, and chat placeholders.
- Instant client-side language switching without page reloads.

### B. Foliar Diagnostic Studio
- **Multi-Crop Selector:** Seamless switching between **Sugarcane (5 classes)** and **Tomato (10 classes)**.
- **Drag-and-Drop Dropzone:** Accepts standard leaf image formats (`.jpg`, `.jpeg`, `.png`, `.webp`) up to 10MB.
- **Live Preview:** Instant client-side preview with leaf orientation check.

### C. Explainable AI (Grad-CAM) Visualizer
- **Side-by-Side Comparison:** Displays the original field leaf alongside the jet-colormap Grad-CAM heatmap overlay.
- **Class Probabilities:** Visual bar chart detailing the top predicted categories with calibrated softmax confidence scores ($T^*$).
- **Transparency Slider / Direct Static Fetch:** Served directly via `/uploads/{session_id}_gradcam.jpg` mounted on the FastAPI server.

### D. Microclimate & Spray Window Telemetry Card
- Displays live environmental parameters:
  - Ambient Temperature (°C)
  - Relative Humidity (%)
  - Wind Speed (km/h)
  - Precipitation Probability (%)
- **Spray Window Status Badge:**
  - `OPTIMAL` (Green): Wind speed < 15 km/h, no imminent rain, humidity 40–80%.
  - `POSTPONED` / `CANCELLED` (Red/Yellow): High drift risk, rain washout risk, or extreme thermal inversion.

### E. Multi-Tier Actionable Advisory Display
- **Biological & Cultural Controls:** Organic amendments, crop rotation, sanitation, resistant cultivars.
- **CIBRC Chemical Formulations:** Active ingredients, approved dosages per hectare/acre, and Pre-Harvest Intervals (PHI).
- **Personal Protective Equipment (PPE) Directives:** Mandatory protective gear notifications.
- **Statutory Disclaimers:** Strict compliance with the *Insecticides Act, 1968* and Central Insecticides Board guidelines.

### F. Slide-in RAG Assistant Chat Drawer
- Multi-turn conversation powered by the hybrid BM25 + dense semantic retrieval engine.
- **Context Auto-Injection:** Automatically captures the active diagnostic scan (e.g., *Tomato Early Blight, 92.4% confidence*) and feeds it to the RAG prompt for contextualized follow-up advice.
- **Quick-Prompt Chips:** Pre-configured farmer queries in Marathi, Hindi, and English (e.g., *"What is the exact dosage?"*, *"How to control biologically?"*).

---

## 3. Directory Layout

```
frontend/
|-- index.html                 # Single Page Application HTML shell
|-- package.json               # Node.js dependencies (React 18, Lucide React, Vite)
|-- vite.config.js             # Vite build & reverse proxy configuration
|-- dist/                      # Production compiled assets (statically served by FastAPI)
`-- src/
    |-- main.jsx               # React DOM bootstrap entry point
    |-- App.jsx                # Master agricultural dashboard layout & state machine
    |-- App.css                # Polished agricultural theme, glassmorphism, responsive grid
    `-- i18n/
        `-- translations.js    # Comprehensive English, Marathi, Hindi translation dictionaries
```

---

## 4. Serving Modes

### Mode 1: Unified Single-Process Serving (FastAPI Production)
In production, the compiled `frontend/dist` directory is statically mounted directly by the FastAPI backend:
```bash
# Build frontend bundle
npm run build --prefix frontend

# Launch unified backend + frontend server
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```
- Web Application: `http://localhost:8000/` or `http://localhost:8000/dashboard/`
- Interactive API Docs: `http://localhost:8000/docs`
- Health Telemetry: `http://localhost:8000/health`

### Mode 2: Vite Development Mode (Hot Module Replacement)
During UI development, run Vite with hot-reloading. Vite automatically proxies `/api` and `/uploads` requests to the running FastAPI server:
```bash
# Terminal 1: FastAPI Backend
uvicorn backend.app.main:app --port 8000 --reload

# Terminal 2: Vite Dev Server
npm run dev --prefix frontend
```
- Dev Dashboard: `http://localhost:3000/`

---

## 5. Verification & Testing

Verify that the dashboard and its static mounts are fully functional:
```bash
pytest backend/tests/test_frontend_serving.py -v
```
All integration tests validate:
1. `GET /` serves the React SPA HTML shell.
2. `GET /dashboard/` serves compiled static HTML.
3. `GET /uploads/` serves static media and Grad-CAM overlays.
4. `GET /health` continues serving JSON system telemetry.

