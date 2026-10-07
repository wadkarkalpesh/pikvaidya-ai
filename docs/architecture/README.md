# PikVaidya AI - Architecture Overview

## High-Level System Architecture

```
+-------------------------------------------------------------+
|                     Client Tier                             |
|           (Web App / Mobile PWA in Marathi & English)       |
+------------------------------+------------------------------+
                               |
                               | HTTPS / REST / WebSocket
                               v
+-------------------------------------------------------------+
|                     Backend API Tier                        |
|                    FastAPI (Python 3.11+)                   |
|  - JWT Authentication & Role-Based Access Control           |
|  - Farmer Profile & Multi-Tenant Management                 |
|  - Farm & Crop Cycle CRUD Workflows                         |
|  - OpenAPI / Swagger Integration                            |
+---------------+------------------------------+--------------+
                |                              |
                v                              v
+-------------------------------+  +--------------------------+
|       Data Storage Tier       |  |  Future AI Service Layer |
|   PostgreSQL 16 + SQLAlchemy  |  |  - Disease Detection     |
|   Alembic Migration System    |  |  - Severity Estimation   |
|                               |  |  - Multimodal Fusion     |
|                               |  |  - Explainability (XAI)  |
|                               |  |  - Agricultural RAG      |
|                               |  |  - ORI AI Orchestrator   |
+-------------------------------+  +--------------------------+
```

## Entity Relationship Model

```
+---------------------+          +---------------------+          +-----------------------+
|        User         | 1      * |        Farm         | 1      * |      CropCycle        |
+---------------------+ -------->+---------------------+ -------->+-----------------------+
| id (PK)             |          | id (PK)             |          | id (PK)               |
| name                |          | user_id (FK->User)  |          | farm_id (FK->Farm)    |
| email (Unique)      |          | name                |          | crop                  |
| password_hash       |          | area                |          | variety               |
| preferred_language  |          | soil_type           |          | sowing_date           |
| role (FARMER/ADMIN) |          | irrigation          |          | growth_stage          |
| is_active           |          | latitude            |          | status                |
| created_at          |          | longitude           |          | created_at            |
| updated_at          |          | created_at          |          | updated_at            |
+---------------------+          | updated_at          |          +-----------------------+
                                 +---------------------+
```
