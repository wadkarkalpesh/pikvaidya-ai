# PikVaidya AI (पिकवैद्य AI)

**PikVaidya AI** is an explainable multimodal agricultural decision-support platform designed to assist farmers with intelligent crop diagnostics, localized advisory in Marathi and English, and seamless expert referrals.

---

## Architecture Overview

```
pikvaidya-ai/
│
├── backend/                  # FastAPI 2.x + SQLAlchemy 2.x REST API
│   ├── alembic/              # Database migration versions and environment
│   ├── app/
│   │   ├── api/routes/       # Modular API endpoints (Auth, Farmer, Farms, Crops)
│   │   ├── core/             # Configuration & Security (JWT, bcrypt)
│   │   ├── db/               # Database session & Base metadata
│   │   ├── models/           # SQLAlchemy ORM entities (User, Farm, CropCycle)
│   │   ├── schemas/          # Pydantic v2 data validation models
│   │   ├── dependencies.py   # JWT & database dependency injection
│   │   └── main.py           # Application entrypoint & CORS setup
│   ├── tests/                # 100% automated pytest test suite
│   ├── alembic.ini           # Alembic database configuration
│   ├── requirements.txt      # Backend Python dependencies
│   └── .env.example          # Environment variable template
│
├── frontend/                 # Client UI (Planned React/Next.js/PWA)
├── ai/                       # AI/ML Computer Vision, Multimodal & RAG Services (Planned)
├── data/                     # Raw and processed datasets (Planned)
├── docs/                     # Comprehensive architecture and domain documentation
├── infra/                    # Docker Compose configuration for PostgreSQL
├── .gitignore
├── README.md
└── LICENSE
```

---

## Technology Stack (Sprint 1)

- **Language:** Python 3.11+ (Tested on Python 3.13)
- **Web Framework:** FastAPI
- **ASGI Server:** Uvicorn
- **ORM:** SQLAlchemy 2.x
- **Database Migrations:** Alembic
- **Database:** PostgreSQL 16 (psycopg 3 binary driver)
- **Data Validation:** Pydantic v2 & `pydantic-settings`
- **Security:** PyJWT & modern `bcrypt` hashing
- **Testing:** Pytest & HTTPX TestClient
- **Containerization:** Docker & Docker Compose

---

## Prerequisites

- Python 3.11 or higher
- Git
- PostgreSQL 14+ or Docker (with Docker Compose)

---

## Setup & Installation

### 1. Clone & Set Up Virtual Environment

```bash
# Clone repository
git clone https://github.com/<your-username>/pikvaidya-ai.git
cd pikvaidya-ai

# Create virtual environment
python -m venv backend/venv

# Activate virtual environment
# Windows (PowerShell):
.\backend\venv\Scripts\Activate.ps1
# Linux / macOS:
source backend/venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt
```

### 2. Configure Environment Variables

```bash
# Copy example environment configuration
cp backend/.env.example backend/.env
```

Edit `backend/.env`:
```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/pikvaidya
SECRET_KEY=your-secure-random-secret-key-here-min-32-chars
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

### 3. Start PostgreSQL Database

Using Docker:
```bash
docker-compose -f infra/docker-compose.yml up -d
```

Or connect to an existing local PostgreSQL instance with database `pikvaidya`.

### 4. Apply Database Migrations (Alembic)

```bash
cd backend
alembic upgrade head
cd ..
```

---

## Running the Application

Start the FastAPI development server:

```bash
# From workspace root
uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```

- **Root Info Endpoint:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Health Check:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- **Interactive Swagger UI:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc API Documentation:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## API Endpoints (Sprint 1)

| Module | Method | Endpoint | Description | Auth Required |
|---|---|---|---|---|
| **System** | `GET` | `/` | API system status and root information | No |
| **System** | `GET` | `/health` | Application healthcheck probe | No |
| **Auth** | `POST` | `/api/v1/auth/register` | Register a new farmer account (defaults to `FARMER` role) | No |
| **Auth** | `POST` | `/api/v1/auth/login` | Login with credentials and receive JWT access token | No |
| **Auth** | `GET` | `/api/v1/auth/me` | Retrieve authenticated user profile | Yes (Bearer) |
| **Farmer** | `GET` | `/api/v1/farmer/profile` | Retrieve farmer details and preferred language | Yes (Bearer) |
| **Farmer** | `PUT` | `/api/v1/farmer/profile` | Update farmer profile (`name`, `preferred_language`) | Yes (Bearer) |
| **Farms** | `POST` | `/api/v1/farms` | Create a new farm owned by authenticated user | Yes (Bearer) |
| **Farms** | `GET` | `/api/v1/farms` | List all farms owned by authenticated user | Yes (Bearer) |
| **Farms** | `GET` | `/api/v1/farms/{farm_id}` | Get specific farm details (Owner protected) | Yes (Bearer) |
| **Farms** | `PUT` | `/api/v1/farms/{farm_id}` | Update farm details (Owner protected) | Yes (Bearer) |
| **Farms** | `DELETE` | `/api/v1/farms/{farm_id}` | Delete farm and cascade crop cycles (Owner protected) | Yes (Bearer) |
| **Crops** | `POST` | `/api/v1/farms/{farm_id}/crops` | Add a crop cycle to a farm (Farm owner protected) | Yes (Bearer) |
| **Crops** | `GET` | `/api/v1/farms/{farm_id}/crops` | List crop cycles for a farm (Farm owner protected) | Yes (Bearer) |
| **Crops** | `GET` | `/api/v1/crops/{crop_id}` | Get crop cycle details (Ownership protected) | Yes (Bearer) |
| **Crops** | `PUT` | `/api/v1/crops/{crop_id}` | Update crop cycle details (Ownership protected) | Yes (Bearer) |
| **Crops** | `DELETE` | `/api/v1/crops/{crop_id}` | Delete crop cycle (Ownership protected) | Yes (Bearer) |

---

## Running Automated Tests

Run the full automated test suite:

```bash
# Windows PowerShell
$env:PYTHONPATH="backend"; .\backend\venv\Scripts\pytest.exe backend\tests -v

# Linux / macOS
PYTHONPATH=backend pytest backend/tests -v
```

All 26 test cases cover:
- Authentication, token issuance, password security, duplicate detection
- Multi-tenant farm creation, isolation, and access control
- Crop cycle lifecycle management and ownership validation

---

## Sprint 1 Completion Checklist

- [x] Monorepo structure with clear boundaries (`backend`, `frontend`, `ai`, `data`, `docs`, `infra`)
- [x] PostgreSQL schema with SQLAlchemy 2.x models (`User`, `Farm`, `CropCycle`)
- [x] Alembic migration configuration and initial version (`001_initial_schema.py`)
- [x] Secure JWT authentication, OAuth2 compatibility, and `bcrypt` password hashing
- [x] Farmer profile management API (`GET /profile`, `PUT /profile`)
- [x] Farm management API with ownership verification (`POST`, `GET`, `PUT`, `DELETE /farms`)
- [x] Crop cycle management API with cross-user isolation (`POST`, `GET`, `PUT`, `DELETE /crops`)
- [x] 26 automated unit and integration tests with pytest passing cleanly
- [x] Docker Compose definition for PostgreSQL with persistent volumes
- [x] Comprehensive documentation and environment templates

---

## Future Development Roadmap

- **Sprint 2:** AI Computer Vision models for foliar disease detection & severity rating
- **Sprint 3:** Multimodal fusion layer (imagery + soil telemetry + weather APIs) & Explainable AI (Grad-CAM / SHAP)
- **Sprint 4:** Retrieval-Augmented Generation (RAG) agronomy advisory in Marathi and English
- **Sprint 5:** ORI Multi-Agent orchestration and agricultural expert referral network
